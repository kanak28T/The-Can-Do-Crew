"""
UrbanPulse FastAPI Backend
Phase 0: /ingest + /sse/events
Phase 1: wired to cell_state + risk_model
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

load_dotenv()

from contracts.event_schema import CanonicalEvent, SCHEMA_VERSION, SOURCE_RELIABILITY
from engine.cell_state import get_cell, snapshot as cell_snapshot
from engine.risk_model import MODEL

OPENCELLID_KEY = os.getenv("OPENCELLID_API_KEY", "")

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="UrbanPulse API", version=SCHEMA_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Day 4: lock to frontend origin
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
            source_reliability  REAL NOT NULL,
            event_timestamp     TEXT NOT NULL,
            ingestion_timestamp TEXT NOT NULL,
            parse_confidence    REAL NOT NULL,
            scenario_tag        TEXT,
            inserted_at         TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

# ── Baseline features (loaded once at startup) ────────────────────────────────
_baseline: dict = {}

def _load_baseline():
    global _baseline
    try:
        from engine.baseline_features import load_baseline_features
        _baseline = {k: v.to_dict() for k, v in load_baseline_features().items()}
        print(f"Baseline features loaded: {len(_baseline)} cells")
    except Exception as e:
        print(f"Baseline features not ready yet ({e}) — using defaults")
        _baseline = {}

@app.on_event("startup")
async def startup():
    _init_db()
    _load_baseline()

# ── SSE broadcast ─────────────────────────────────────────────────────────────
_sse_clients: list[asyncio.Queue] = []

async def _broadcast(payload: dict):
    dead = []
    for q in _sse_clients:
        try:
            q.put_nowait(payload)
        except asyncio.QueueFull:
            dead.append(q)
    for q in dead:
        _sse_clients.remove(q)

# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status":    "ok",
        "version":   SCHEMA_VERSION,
        "cells":     len(cell_snapshot()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

@app.get("/health/feeds")
async def health_feeds():
    """Per-domain feed freshness."""
    from engine.cell_state import all_cells
    from datetime import datetime, timezone
    domain_last: dict = {}
    for cell in all_cells().values():
        for domain, ts in cell.last_updated.items():
            if domain not in domain_last or ts > domain_last[domain]:
                domain_last[domain] = ts
    now = datetime.now(timezone.utc)
    feeds = {}
    for domain in ["power", "transit", "water", "health", "comms", "road"]:
        if domain in domain_last:
            lag = round((now - domain_last[domain]).total_seconds())
            feeds[domain] = {"status": "ok" if lag < 3600 else "stale", "lag_seconds": lag}
        else:
            feeds[domain] = {"status": "missing", "lag_seconds": None}
    return {"feeds": feeds}


@app.post("/ingest")
async def ingest(request: Request):
    """Accept a canonical event, update cell state, push to SSE."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"status": "rejected", "reason": "Invalid JSON"})

    # Schema + PII validation
    try:
        event = CanonicalEvent(**body)
    except ValidationError as exc:
        errors = exc.errors()
        pii = any("PII" in str(e.get("msg", "")) for e in errors)
        return JSONResponse(
            status_code=422,
            content={
                "status":  "rejected",
                "reason":  "PII detected" if pii else "Schema validation failed",
                "details": [e["msg"] for e in errors],
            },
        )

    # Strip scenario_tag on production path
    domain_val = event.domain if isinstance(event.domain, str) else event.domain.value

    # Append-only log
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
                event.source_type if isinstance(event.source_type, str) else event.source_type.value,
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

    # Update cell state
    cell = get_cell(event.h3_cell)
    src  = event.source_type if isinstance(event.source_type, str) else event.source_type.value
    cell.update(domain_val, event.severity, src)
    cell.check_unknown()

    # Re-score
    baseline = _baseline.get(event.h3_cell, {})
    risk, label = MODEL.score(cell.decayed_stress, baseline)
    lo, hi = MODEL.bootstrap_interval(cell.decayed_stress, baseline, n=100)
    cell.risk = risk
    cell.risk_label = label
    cell.risk_interval = (lo, hi)

    # Broadcast
    sse_payload = {
        "event":    "cell_updated",
        "cell":     event.h3_cell,
        "domain":   domain_val,
        "severity": event.severity,
        "risk":     risk,
        "label":    "unknown" if cell.is_unknown else label,
        "interval": [lo, hi],
        "confidence": cell.confidence,
        "timestamp": event.ingestion_timestamp.isoformat(),
    }
    await _broadcast(sse_payload)

    return {
        "status":     "accepted",
        "event_id":   event.event_id,
        "cell":       event.h3_cell,
        "risk":       risk,
        "label":      label,
        "interval":   [lo, hi],
        "risk_updated": True,
        "timestamp":  datetime.now(timezone.utc).isoformat(),
    }


@app.get("/zones")
async def get_zones(risk_min: float = 0.65):
    """Return all cells above risk threshold as zone objects."""
    from engine.cell_state import all_cells
    zones = []
    for cell in all_cells().values():
        if cell.risk >= risk_min and not cell.is_unknown:
            baseline = _baseline.get(cell.h3_cell, {})
            drivers = MODEL.driver_contributions(cell.decayed_stress, baseline)
            zones.append({
                "cell":       cell.h3_cell,
                "risk":       cell.risk,
                "label":      cell.risk_label,
                "interval":   list(cell.risk_interval),
                "confidence": cell.confidence,
                "drivers":    drivers,
                "stress":     cell.decayed_stress,
            })
    zones.sort(key=lambda z: z["risk"], reverse=True)
    return {"zones": zones, "count": len(zones)}


@app.get("/sse/events")
async def sse_events(request: Request):
    """Server-Sent Events stream — live cell updates."""
    queue: asyncio.Queue = asyncio.Queue(maxsize=200)
    _sse_clients.append(queue)

    async def generate() -> AsyncGenerator[str, None]:
        yield "event: connected\ndata: {\"msg\": \"connected\"}\n\n"
        event_id = 0
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=15)
                    data = json.dumps(payload)
                    yield f"id: {event_id}\nevent: cell_updated\ndata: {data}\n\n"
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
            "Cache-Control":    "no-cache",
            "X-Accel-Buffering": "no",
            "Connection":       "keep-alive",
        },
    )
