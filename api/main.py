"""
UrbanPulse FastAPI Backend
===========================
Authors : Priyanshu (A1) — base structure, DB, SSE, routes
          Kanak (A2)      — ENGINE.process_event() wired in (Day 2)

Phase 0 : /ingest stub + /sse/events mock
Phase 1 : cell_state + risk_model + engine orchestrator live
Phase 3 : zone builder, driver contributions, dispatch log
Phase 4 : CORS locked to frontend origin
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
    allow_origins=[os.getenv("CORS_ORIGIN", "*")],   # Day 4: set CORS_ORIGIN env var
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
async def health_feeds():
    """Per-domain feed freshness — used by the frontend status bar."""
    now = datetime.now(timezone.utc)
    domain_last: dict = {}
    for cell in all_cells().values():
        for domain, ts in cell.last_updated.items():
            if domain not in domain_last or ts > domain_last[domain]:
                domain_last[domain] = ts

    feeds = {}
    for domain in ["power", "transit", "water", "health", "comms", "road"]:
        if domain in domain_last:
            lag = round((now - domain_last[domain]).total_seconds())
            feeds[domain] = {
                "status":      "ok" if lag < 3600 else "stale",
                "lag_seconds": lag,
            }
        else:
            feeds[domain] = {"status": "missing", "lag_seconds": None}
    return {"feeds": feeds}


# ── Ingest ────────────────────────────────────────────────────────────────────
@app.post("/ingest")
async def ingest(request: Request):
    """
    Accept a canonical event.
    1. Validate schema + reject PII (Pydantic)
    2. Log to SQLite (append-only)
    3. ENGINE.process_event() — updates cell state, recomputes risk
    4. Broadcast result to SSE stream
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
        pii = any("PII" in str(e.get("msg", "")) or "Forbidden" in str(e.get("msg", ""))
                  for e in errors)
        return JSONResponse(
            status_code=422,
            content={
                "status":  "rejected",
                "reason":  "PII detected" if pii else "Schema validation failed",
                "details": [e["msg"] for e in errors],
            },
        )

    # Append-only event log
    conn = _get_db()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO events VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                event.event_id,
                event.domain,
                event.event_type,
                event.entity_id,
                event.h3_cell,
                event.severity,
                event.source_type,
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

    # Engine processes the event (cell state + risk score + confidence)
    result = ENGINE.process_event(event)

    # SSE broadcast
    await _broadcast({
        "event":      "cell_updated",
        "cell":       result.cell,
        "domain":     result.domain,
        "severity":   result.severity,
        "risk":       result.risk,
        "label":      "unknown" if result.is_unknown else result.label,
        "interval":   list(result.interval),
        "confidence": result.confidence,
        "is_unknown": result.is_unknown,
        "timestamp":  result.timestamp,
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
async def get_zones(risk_min: float = 0.65):
    """
    Return all High-risk cells as zone objects.
    Applies k-merge before returning (privacy enforcement).
    """
    from engine.risk_model import MODEL

    raw_zones = []
    contributor_counts: dict[str, int] = {}

    for cell in all_cells().values():
        if cell.risk >= risk_min and not cell.is_unknown:
            baseline = ENGINE._get_baseline_dict(cell.h3_cell)
            drivers  = MODEL.driver_contributions(cell.decayed_stress, baseline)
            raw_zones.append({
                "cell_id":    cell.h3_cell,
                "risk_score": cell.risk,
                "label":      cell.risk_label,
                "interval":   list(cell.risk_interval),
                "confidence": cell.confidence,
                "driver_contributions": drivers,
                "stress":     cell.decayed_stress,
            })
            contributor_counts[cell.h3_cell] = len(cell.source_types)

    # Apply k-merge privacy enforcement
    privacy_k = int(os.getenv("PRIVACY_K", "5"))
    zones = apply_k_merge(raw_zones, contributor_counts, k=privacy_k)

    zones_out = sorted(
        [z.__dict__ if hasattr(z, "__dict__") else z for z in zones],
        key=lambda z: z.get("risk_score", 0),
        reverse=True,
    )
    return {"zones": zones_out, "count": len(zones_out)}


# ── SSE stream ────────────────────────────────────────────────────────────────
@app.get("/sse/events")
async def sse_events(request: Request):
    """
    Server-Sent Events stream.
    Frontend subscribes here; /ingest pushes updates in real time.
    Heartbeat every 15s keeps the connection alive.
    Ring buffer: queue size 200 (in-memory reconnect replay).
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
                    yield f"id: {event_id}\nevent: cell_updated\ndata: {json.dumps(payload)}\n\n"
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
