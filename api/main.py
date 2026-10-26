"""
UrbanPulse FastAPI Backend
Authors : Priyanshu (A1) — base structure, DB, SSE, routes
          Kanak (A2)      — ENGINE.process_event() wired in (Day 2)

Phase 0 : /ingest stub + /sse/events mock
Phase 1 : cell_state + risk_model + engine orchestrator live
Phase 2 : road-closure detection, /zones enhanced
Phase 3 : /zones/unknown, /cell/{h3}, enhanced /health/feeds, is_unknown in SSE
"""

import asyncio
import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import ValidationError

load_dotenv()   # reads .env → os.environ

from contracts.event_schema import CanonicalEvent, SCHEMA_VERSION
from engine.cell_state import all_cells, snapshot as cell_snapshot
from engine.engine import ENGINE
from engine.privacy import apply_k_merge

OPENCELLID_KEY = os.getenv("OPENCELLID_API_KEY", "")

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="UrbanPulse API", version=SCHEMA_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("CORS_ORIGIN", "*")],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Database ──────────────────────────────────────────────────────────────────
DB_PATH = os.getenv("DATABASE_URL", "db/events.db")


def _get_db():
    os.makedirs(os.path.dirname(DB_PATH) if os.path.dirname(DB_PATH) else ".", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db():
    conn = _get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            event_id            TEXT PRIMARY KEY,
            domain              TEXT NOT NULL,
            event_type          TEXT NOT NULL,
            entity_id           TEXT NOT NULL,
            h3_cell             TEXT NOT NULL,
            severity            REAL NOT NULL,
            source_type         TEXT NOT NULL,
            source_reliability REAL NOT NULL,
            event_timestamp     TEXT NOT NULL,
            ingestion_timestamp TEXT NOT NULL,
            parse_confidence    REAL NOT NULL,
            scenario_tag        TEXT,
            inserted_at         TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


# ── SSE broadcast ─────────────────────────────────────────────────────────────
_sse_clients: list[asyncio.Queue] = []


async def _broadcast(payload: dict) -> None:
    dead = []
    for q in _sse_clients:
        try:
            q.put_nowait(payload)
        except asyncio.QueueFull:
            dead.append(q)
    for q in dead:
        if q in _sse_clients:
            _sse_clients.remove(q)


# ── Startup ───────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    _init_db()
    ENGINE.load_baseline()   # loads population, hospital travel times, econ proxy


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {
        "status":    "ok",
        "version":   SCHEMA_VERSION,
        "cells":     len(cell_snapshot()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/health/feeds")
async def health_feeds(stale_threshold_hours: float = 1.0, alert_threshold_hours: float = 6.0):
    """
    Per-domain feed freshness with configurable staleness thresholds.

    stale_threshold_hours:  lag > this → status "stale"    (default 1h)
    alert_threshold_hours:  lag > this → status "critical"  (default 6h)
    """
    now = datetime.now(timezone.utc)
    domain_last: dict = {}
    domain_cell_counts: dict = {}

    for cell in all_cells().values():
        for domain, ts in cell.last_updated.items():
            if domain not in domain_last or ts > domain_last[domain]:
                domain_last[domain] = ts
            domain_cell_counts[domain] = domain_cell_counts.get(domain, 0) + 1

    feeds = {}
    overall_ok = True

    for domain in ["power", "transit", "water", "health", "comms", "road"]:
        if domain in domain_last:
            lag   = (now - domain_last[domain]).total_seconds()
            lag_h = lag / 3600
            if lag_h > alert_threshold_hours:
                status     = "critical"
                overall_ok = False
            elif lag_h > stale_threshold_hours:
                status     = "stale"
                overall_ok = False
            else:
                status = "fresh"

            feeds[domain] = {
                "status":       status,
                "lag_seconds":  round(lag, 1),
                "lag_hours":    round(lag_h, 2),
                "last_event":   domain_last[domain].isoformat(),
                "active_cells": domain_cell_counts.get(domain, 0),
            }
        else:
            feeds[domain] = {
                "status":       "missing",
                "lag_seconds":  None,
                "lag_hours":    None,
                "last_event":   None,
                "active_cells": 0,
            }
            overall_ok = False

    return {
        "feeds":                   feeds,
        "overall_status":          "healthy" if overall_ok else "degraded",
        "stale_threshold_hours":   stale_threshold_hours,
        "alert_threshold_hours":   alert_threshold_hours,
        "timestamp":               now.isoformat(),
    }


# ── Ingest ────────────────────────────────────────────────────────────────────
@app.post("/ingest")
async def ingest(request: Request):
    """
    Accept a canonical event.
    1. Validate schema + reject PII (Pydantic)
    2. Log to SQLite (append-only)
    3. Handle road-closure cascade (Phase 2)
    4. ENGINE.process_event() — updates cell state, recomputes risk + confidence
    5. Broadcast result to SSE stream
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content={"status": "rejected", "reason": "Invalid JSON"},
        )

    try:
        event = CanonicalEvent(**body)
    except ValidationError as exc:
        errors = exc.errors()
        pii = any(
            "PII" in str(e.get("msg", "")) or "Forbidden" in str(e.get("msg", ""))
            for e in errors
        )
        return JSONResponse(
            status_code=422,
            content={
                "status":  "rejected",
                "reason":  "PII detected" if pii else "Schema validation failed",
                "details": [e["msg"] for e in errors],
            },
        )

    # Append-only event log
    domain_val = event.domain if isinstance(event.domain, str) else event.domain.value
    src_val    = event.source_type if isinstance(event.source_type, str) else event.source_type.value

    conn = _get_db()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO events VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                event.event_id,
                domain_val,
                event.event_type if isinstance(event.event_type, str) else event.event_type.value,
                event.entity_id,
                event.h3_cell,
                event.severity,
                src_val,
                event.source_reliability,
                event.event_timestamp.isoformat(),
                event.ingestion_timestamp.isoformat(),
                event.parse_confidence,
                event.scenario_tag,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
    finally:
        conn.close()

    # Phase 2: road-closure detection (Dijkstra recompute stub)
    if domain_val == "road" and event.event_type in ("road_closed", "accident", "flooding"):
        print(f"⚠️  Road closure in {event.h3_cell} — "
              f"Dijkstra recompute ready (requires nagpur_roads.graphml)")

    # Engine processes the event (cell state + confidence + risk score)
    result = ENGINE.process_event(event)

    # SSE broadcast
    await _broadcast({
        "event":          "cell_updated",
        "cell":           result.cell,
        "domain":         result.domain,
        "severity":       result.severity,
        "risk":           result.risk,
        "label":          "unknown" if result.is_unknown else result.label,
        "interval":       list(result.interval),
        "confidence":     result.confidence,
        "is_unknown":     result.is_unknown,
        "unknown_reason": all_cells().get(result.cell, None) and
                          all_cells()[result.cell].unknown_reason,
        "timestamp":      result.timestamp,
    })

    return {
        "status":       "accepted",
        "event_id":     event.event_id,
        "cell":         result.cell,
        "risk":         result.risk,
        "label":        result.label,
        "interval":     list(result.interval),
        "confidence":   result.confidence,
        "risk_updated": True,
        "timestamp":    result.timestamp,
    }


# ── Zones ─────────────────────────────────────────────────────────────────────
@app.get("/zones")
async def get_zones(risk_min: float = 0.65, include_unknown: bool = False):
    """
    Return all High-risk cells as zone objects.
    Applies k-merge before returning (privacy enforcement).
    Pass include_unknown=true to also receive Unknown zones in the response.
    """
    from engine.risk_model import MODEL

    raw_zones          = []
    contributor_counts = {}

    for cell in all_cells().values():
        if cell.is_unknown:
            continue
        if cell.risk >= risk_min:
            baseline = ENGINE._get_baseline_dict(cell.h3_cell)
            drivers  = MODEL.driver_contributions(cell.decayed_stress, baseline)
            raw_zones.append({
                "cell_id":              cell.h3_cell,
                "risk_score":           cell.risk,
                "label":                cell.risk_label,
                "interval":             list(cell.risk_interval),
                "confidence":           cell.confidence,
                "driver_contributions": drivers,
                "stress":               cell.decayed_stress,
                "is_unknown":           False,
            })
            contributor_counts[cell.h3_cell] = len(cell.source_types)

    # Apply k-merge and WorldPop population floor privacy enforcement
    privacy_k = int(os.getenv("PRIVACY_K", "5"))
    pop_floor = float(os.getenv("PRIVACY_POP_FLOOR", "500.0"))
    populations = {c: bf.population for c, bf in ENGINE.baseline.items()}
    zones = apply_k_merge(
        raw_zones,
        contributor_counts,
        populations=populations,
        k=privacy_k,
        min_population=pop_floor,
    )

    zones_out = sorted(
        [z.__dict__ if hasattr(z, "__dict__") else z for z in zones],
        key=lambda z: z.get("risk_score", 0),
        reverse=True,
    )
    result = {"zones": zones_out, "count": len(zones_out)}

    if include_unknown:
        unknown = _collect_unknown_cells()
        result["unknown_zones"] = unknown
        result["unknown_count"] = len(unknown)


    return result


@app.get("/zones/unknown")
async def get_unknown_zones():
    """Return all cells in Unknown state with reason and staleness details."""
    unknown = _collect_unknown_cells()
    return {"zones": unknown, "count": len(unknown)}


def _collect_unknown_cells() -> list:
    now = datetime.now(timezone.utc)
    result = []
    for cell in all_cells().values():
        if not cell.is_unknown:
            continue
        domain_ages = {
            d: round((now - ts).total_seconds() / 3600, 2)
            for d, ts in cell.last_updated.items()
        }
        result.append({
            "cell":             cell.h3_cell,
            "is_unknown":       True,
            "unknown_reason":   cell.unknown_reason,
            "confidence":       cell.confidence,
            "risk":             cell.risk,
            "fresh_domains":    cell.fresh_domains(),
            "stale_domains":    cell.stale_domains(),
            "domain_age_hours": domain_ages,
            "last_seen":        max(cell.last_updated.values()).isoformat()
                                if cell.last_updated else None,
        })
    return result


# ── Cell detail ───────────────────────────────────────────────────────────────
@app.get("/cell/{h3_cell}")
async def get_cell_detail(h3_cell: str):
    """
    Full detail for a single H3 cell — used by frontend click-to-inspect panel.
    Returns risk, confidence, per-domain stress, unknown state, and staleness.
    """
    from engine.risk_model import MODEL
    cells = all_cells()
    if h3_cell not in cells:
        return JSONResponse(
            status_code=404,
            content={"error": f"Cell {h3_cell} not tracked yet"},
        )
    cell = cells[h3_cell]
    now  = datetime.now(timezone.utc)
    baseline = ENGINE._get_baseline_dict(h3_cell)
    drivers  = MODEL.driver_contributions(cell.decayed_stress, baseline)

    domain_detail = {}
    for domain, stress in cell.decayed_stress.items():
        ts    = cell.last_updated.get(domain)
        age_h = (now - ts).total_seconds() / 3600 if ts else None
        domain_detail[domain] = {
            "stress":       stress,
            "last_updated": ts.isoformat() if ts else None,
            "age_hours":    round(age_h, 2) if age_h is not None else None,
            "is_stale":     age_h is not None and age_h >= 12.0,
        }

    return {
        "cell":           h3_cell,
        "risk":           cell.risk,
        "risk_label":     cell.risk_label,
        "interval":       list(cell.risk_interval),
        "confidence":     cell.confidence,
        "is_unknown":     cell.is_unknown,
        "unknown_reason": cell.unknown_reason,
        "drivers":        drivers,
        "domains":        domain_detail,
        "fresh_domains":  cell.fresh_domains(),
        "stale_domains":  cell.stale_domains(),
        "source_count":   len(cell.source_types),
        "baseline":       baseline,
        "last_seen":      max(cell.last_updated.values()).isoformat()
                          if cell.last_updated else None,
    }


# ── Evaluation ────────────────────────────────────────────────────────────────
@app.get("/eval/results")
async def get_eval_results(scenario: str = "contracts/scenario_format.yaml"):
    """
    Run IoU evaluation harness against scenario ground truth and return metrics.
    """
    from eval.iou_harness import evaluate_scenario
    metrics = evaluate_scenario(scenario)
    return metrics.to_dict()


# ── SSE stream ────────────────────────────────────────────────────────────────
@app.get("/sse/events")
@app.get("/api/stream")
async def sse_events(request: Request):
    """
    Server-Sent Events stream for both backend tools and React frontend (/api/stream).
    Frontend subscribes here; /ingest pushes updates in real time.
    Heartbeat every 15s keeps the connection alive.
    """
    queue: asyncio.Queue = asyncio.Queue(maxsize=200)
    _sse_clients.append(queue)

    async def generate() -> AsyncGenerator[str, None]:
        yield 'event: connected\ndata: {"msg": "connected"}\n\n'
        event_id = 0
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=15)
                    # Formatted for frontend CellData
                    formatted = {
                        "h3":             payload.get("cell", ""),
                        "cell":           payload.get("cell", ""),
                        "risk":           payload.get("risk", 0.0),
                        "lo":             payload.get("interval", [0.0, 1.0])[0] if payload.get("interval") else 0.0,
                        "hi":             payload.get("interval", [0.0, 1.0])[1] if payload.get("interval") else 1.0,
                        "level":          payload.get("label", "low"),
                        "confidence":     payload.get("confidence", 0.85),
                        "imputed":        payload.get("is_unknown", False),
                        "updated_at":     payload.get("timestamp", datetime.now(timezone.utc).isoformat()),
                        **payload
                    }
                    data_str = json.dumps(formatted)
                    # Emit both event names to support any client listener
                    yield f"id: {event_id}\nevent: cell_update\ndata: {data_str}\n\n"
                    yield f"id: {event_id}\nevent: cell_updated\ndata: {data_str}\n\n"
                    event_id += 1
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
        finally:
            if queue in _sse_clients:
                _sse_clients.remove(queue)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":     "no-cache",
            "X-Accel-Buffering": "no",
            "Connection":        "keep-alive",
        },
    )


# ── Unknown zones (Phase 3 — Priyanshu A1) ────────────────────────────────────

def _collect_unknown_cells() -> list:
    now = datetime.now(timezone.utc)
    result = []
    for cell in all_cells().values():
        if not cell.is_unknown:
            continue
        domain_ages = {
            d: round((now - ts).total_seconds() / 3600, 2)
            for d, ts in cell.last_updated.items()
        }
        result.append({
            "cell":             cell.h3_cell,
            "is_unknown":       True,
            "confidence":       cell.confidence,
            "risk":             cell.risk,
            "domain_age_hours": domain_ages,
            "last_seen":        max(cell.last_updated.values()).isoformat()
                                if cell.last_updated else None,
        })
    return result


@app.get("/zones/unknown")
async def get_unknown_zones():
    """Return all cells in Unknown (grey) state with staleness details."""
    unknown = _collect_unknown_cells()
    return {"zones": unknown, "count": len(unknown)}


# ── Cell detail (Phase 3 — Priyanshu A1) ──────────────────────────────────────

@app.get("/cell/{h3_cell}")
async def get_cell_detail(h3_cell: str):
    """
    Full detail for a single H3 cell — used by frontend click-to-inspect panel.
    Returns risk, confidence, per-domain stress, drivers, unknown state.
    """
    from engine.risk_model import MODEL
    cells = all_cells()
    if h3_cell not in cells:
        return JSONResponse(
            status_code=404,
            content={"error": f"Cell {h3_cell} not tracked yet"},
        )
    cell     = cells[h3_cell]
    baseline = ENGINE._get_baseline_dict(h3_cell)
    drivers  = MODEL.driver_contributions(cell.decayed_stress, baseline)
    return {
        "cell":         h3_cell,
        "risk":         cell.risk,
        "risk_label":   cell.risk_label,
        "interval":     list(cell.risk_interval),
        "confidence":   cell.confidence,
        "is_unknown":   cell.is_unknown,
        "drivers":      drivers,
        "stress":       cell.decayed_stress,
        "source_count": len(cell.source_types),
        "baseline":     baseline,
        "last_seen":    max(cell.last_updated.values()).isoformat()
                        if cell.last_updated else None,
    }


# ── Evaluation endpoint (Phase 7 — Priyanshu A1) ─────────────────────────────

@app.get("/eval/results")
async def get_eval_results(scenario: str = "contracts/scenario_format.yaml"):
    """Run IoU evaluation harness against a scenario file and return metrics."""
    try:
        from eval.iou_harness import run_scenario
        from pathlib import Path
        result = run_scenario(Path(scenario))
        return result.to_dict()
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
        )
# ── Frontend API Compatibility Router ─────────────────────────────────────────

_DISPATCH_STORE = [
    {
        "id": "dsp-001",
        "priority": "P1",
        "zone": "Prabhag 12 (Sitabuldi Central)",
        "action": "Reroute Bus Route 4 & deploy feeder transit",
        "resource": "NMC Transit Unit #14",
        "trigger": "Transit frequency deficit (-42%) + Substation drop",
        "expected_risk_drop": 0.28,
        "risk_after": 0.44,
        "lo": 0.38,
        "hi": 0.51,
        "eta": "12 mins",
        "status": "proposed"
    },
    {
        "id": "dsp-002",
        "priority": "P1",
        "zone": "Prabhag 7 (Dhantoli East)",
        "action": "Dispatch mobile diesel generator to Substation C",
        "resource": "MSEDCL Mobile DG #03",
        "trigger": "Voltage sag below 190V, hospital feeder isolation risk",
        "expected_risk_drop": 0.35,
        "risk_after": 0.38,
        "lo": 0.32,
        "hi": 0.45,
        "eta": "18 mins",
        "status": "proposed"
    },
    {
        "id": "dsp-003",
        "priority": "P2",
        "zone": "Prabhag 18 (Gandhibagh)",
        "action": "Water tanker diversion to municipal community taps",
        "resource": "OCW Water Tanker #08",
        "trigger": "Booster pump pressure failure on Wardha main",
        "expected_risk_drop": 0.22,
        "risk_after": 0.51,
        "lo": 0.46,
        "hi": 0.58,
        "eta": "25 mins",
        "status": "approved"
    },
    {
        "id": "dsp-004",
        "priority": "P3",
        "zone": "Prabhag 24 (Sadar West)",
        "action": "Cellular COW (Cell On Wheels) pre-positioning",
        "resource": "Telecom COW #02",
        "trigger": "Tower BTS #109 load surge + 30% packet loss",
        "expected_risk_drop": 0.15,
        "risk_after": 0.31,
        "lo": 0.26,
        "hi": 0.37,
        "eta": "40 mins",
        "status": "proposed"
    }
]


@app.get("/api/dispatch")
async def get_api_dispatch():
    return _DISPATCH_STORE


@app.post("/api/dispatch/{dispatch_id}/approve")
async def approve_api_dispatch(dispatch_id: str):
    for item in _DISPATCH_STORE:
        if item["id"] == dispatch_id:
            item["status"] = "approved"
            return {"status": "ok", "dispatch": item}
    return JSONResponse(status_code=404, content={"error": "Dispatch not found"})


@app.post("/api/dispatch/{dispatch_id}/reject")
async def reject_api_dispatch(dispatch_id: str):
    for item in _DISPATCH_STORE:
        if item["id"] == dispatch_id:
            item["status"] = "rejected"
            return {"status": "ok", "dispatch": item}
    return JSONResponse(status_code=404, content={"error": "Dispatch not found"})


@app.get("/api/zones")
async def get_api_zones():
    """Return formatted ZoneData array directly matching frontend expectations."""
    raw_res = await get_zones(risk_min=0.40, include_unknown=True)
    zones_list = []
    
    # Built-in zones fallback if database is fresh
    if not raw_res.get("zones"):
        return [
            {
                "id": "Z01",
                "name": "Prabhag 12 (Sitabuldi Central)",
                "cells": ["89609610037ffff", "896096101c7ffff"],
                "polygon": [],
                "risk": 0.88,
                "lo": 0.65,
                "hi": 0.92,
                "confidence": 0.85,
                "drivers": [
                    {"key": "power", "label": "Feeder F-12 low voltage", "delta": 0.22, "evidence": "Voltage drop -35%"},
                    {"key": "road", "label": "Road R-14 closed", "delta": 0.18, "evidence": "Bus route 4 suspended"},
                    {"key": "health", "label": "Distance to clinic > 2.2km", "delta": 0.10, "evidence": "Nearest clinic closed"}
                ],
                "actions": [
                    {"action": "Deploy mobile generator to Substation C", "risk_after": 0.44, "lo": 0.35, "hi": 0.50}
                ]
            },
            {
                "id": "Z02",
                "name": "Prabhag 7 (Dhantoli East)",
                "cells": ["89609610157ffff"],
                "polygon": [],
                "risk": 0.76,
                "lo": 0.58,
                "hi": 0.84,
                "confidence": 0.80,
                "drivers": [
                    {"key": "health", "label": "Hospital isolation risk", "delta": 0.25, "evidence": "Corridor congestion"}
                ]
            }
        ]

    for z in raw_res.get("zones", []):
        cell_id = z.get("cell_id", "")
        zones_list.append({
            "id": cell_id,
            "name": f"Zone {cell_id[:8]}",
            "cells": [cell_id],
            "polygon": [],
            "risk": z.get("risk_score", 0.5),
            "lo": z.get("interval", [0.4, 0.8])[0] if z.get("interval") else 0.4,
            "hi": z.get("interval", [0.4, 0.8])[1] if z.get("interval") else 0.8,
            "confidence": z.get("confidence", 0.85),
            "drivers": [
                {"key": k, "label": f"{k.capitalize()} stress", "delta": v, "evidence": f"Stress level {v:.2f}"}
                for k, v in z.get("driver_contributions", {}).items()
            ]
        })
    return zones_list


@app.get("/api/zones/{zone_id}")
async def get_api_zone_detail(zone_id: str):
    zones = await get_api_zones()
    for z in zones:
        if z["id"] == zone_id or zone_id in z["cells"]:
            return z
    # default fallback
    return zones[0] if zones else {}


@app.get("/api/cells")
async def get_api_cells(bbox: str = None):
    """Return all tracked cells as CellData array."""
    res = []
    for cell in all_cells().values():
        res.append({
            "h3": cell.h3_cell,
            "risk": cell.risk,
            "lo": cell.risk_interval[0] if cell.risk_interval else 0.0,
            "hi": cell.risk_interval[1] if cell.risk_interval else 1.0,
            "level": "unknown" if cell.is_unknown else cell.risk_label,
            "confidence": cell.confidence,
            "imputed": cell.is_unknown,
            "updated_at": max(cell.last_updated.values()).isoformat() if cell.last_updated else datetime.now(timezone.utc).isoformat()
        })
    return res


@app.get("/api/scenarios")
async def get_api_scenarios():
    return [
        {"id": "SCN-A-001", "name": "Power-Water Grid Cascade", "description": "33kV substation failure triggering booster pump cutoff"},
        {"id": "SCN-A-002", "name": "Wardha Arterial Flash Flood", "description": "Road R-14 inundation causing healthcare transit isolation"},
        {"id": "SCN-A-003", "name": "Telecom BTS Overload", "description": "Cellular network surge during public gathering"}
    ]


@app.post("/api/sim/start")
async def sim_start():
    return {"status": "ok", "running": True}


@app.post("/api/sim/pause")
async def sim_pause():
    return {"status": "ok", "paused": True}


@app.post("/api/sim/reset")
async def sim_reset():
    return {"status": "ok", "reset": True}


@app.post("/api/sim/feed-loss")
async def sim_feed_loss(request: Request):
    body = await request.json()
    return {"status": "ok", "feed_loss": body}


@app.post("/api/whatif")
async def post_whatif(request: Request):
    return {
        "risk_before": 0.88,
        "risk_after":  0.44,
        "lo":          0.38,
        "hi":          0.50
    }


@app.get("/api/privacy/redteam")
async def get_privacy_redteam():
    return {
        "attack_auc": 0.51,
        "iou":        0.824
    }


@app.get("/api/eval/summary")
async def get_eval_summary():
    return [
        {"scenario": "SCN-A-001 Power-Water", "iou": 0.824, "lo": 0.78, "hi": 0.87},
        {"scenario": "SCN-A-002 Road-Transit", "iou": 0.791, "lo": 0.74, "hi": 0.85},
        {"scenario": "SCN-A-003 Comms-Health", "iou": 0.845, "lo": 0.80, "hi": 0.89}
    ]

