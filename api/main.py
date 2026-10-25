"""
UrbanPulse FastAPI Backend
Phase 0: /ingest + /sse/events (mock stream)
Phase 1: wire to engine
"""

import asyncio
import json
import sqlite3
import os
from datetime import datetime
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import ValidationError

from contracts.event_schema import CanonicalEvent, SCHEMA_VERSION

# ── App ─────────────────────────────────────────────────────────────────────
app = FastAPI(title="UrbanPulse API", version=SCHEMA_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Day 4: lock to frontend origin
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Database ─────────────────────────────────────────────────────────────────
DB_PATH = os.getenv("DATABASE_URL", "db/events.db")

def _get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
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

@app.on_event("startup")
async def startup():
    _init_db()

# ── SSE broadcast queue ───────────────────────────────────────────────────────
_sse_clients: list[asyncio.Queue] = []

async def _broadcast(payload: dict):
    for q in _sse_clients:
        await q.put(payload)

# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": SCHEMA_VERSION,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/ingest")
async def ingest(request: Request):
    """
    Accept a canonical event.
    1. Validate schema (Pydantic)
    2. Reject PII
    3. Log to SQLite
    4. Push to SSE stream
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"status": "rejected", "reason": "Invalid JSON"})

    # Schema + PII validation (Pydantic raises ValueError for PII via validators)
    try:
        event = CanonicalEvent(**body)
    except ValidationError as exc:
        errors = exc.errors()
        pii_errors = [e for e in errors if "PII" in str(e.get("msg", ""))]
        return JSONResponse(
            status_code=422,
            content={
                "status": "rejected",
                "reason": "PII detected" if pii_errors else "Schema validation failed",
                "details": [e["msg"] for e in errors]
            }
        )

    # Append-only log to SQLite
    conn = _get_db()
    try:
        conn.execute("""
            INSERT OR IGNORE INTO events VALUES
            (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
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
            datetime.utcnow().isoformat(),
        ))
        conn.commit()
    finally:
        conn.close()

    # Broadcast to SSE clients
    sse_payload = {
        "event": "cell_updated",
        "cell":  event.h3_cell,
        "domain": event.domain,
        "severity": event.severity,
        "risk": round(0.2 + event.severity * 0.6, 3),  # placeholder; Day 2: real engine
        "interval": [0.1, 0.9],
        "timestamp": event.ingestion_timestamp.isoformat(),
    }
    await _broadcast(sse_payload)

    return {
        "status": "accepted",
        "event_id": event.event_id,
        "cell": event.h3_cell,
        "risk_updated": True,   # Day 2: will be real engine score
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/sse/events")
async def sse_events(request: Request):
    """
    Server-Sent Events stream.
    Browser subscribes here; any /ingest call pushes an update.
    """
    queue: asyncio.Queue = asyncio.Queue()
    _sse_clients.append(queue)

    async def generate() -> AsyncGenerator[str, None]:
        # Send a heartbeat immediately so the browser knows connection is alive
        yield "event: connected\ndata: {\"msg\": \"connected\"}\n\n"

        event_id = 0
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=15)
                    data    = json.dumps(payload)
                    yield f"id: {event_id}\nevent: cell_updated\ndata: {data}\n\n"
                    event_id += 1
                except asyncio.TimeoutError:
                    # Heartbeat every 15s to keep connection alive
                    yield ": heartbeat\n\n"
        finally:
            _sse_clients.remove(queue)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
