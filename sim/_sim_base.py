"""
Shared event-builder for all B2 domain simulators.

Outputs events using the 'cell' field name (team convention).
contracts/event_schema.py maps 'cell' → 'h3_cell' transparently before validation,
so all events are accepted by the /ingest endpoint without any teammate changes.

Determinism: callers seed random.Random(seed) before calling generators;
this module does not touch the global RNG state.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

# Mirrors SOURCE_RELIABILITY in contracts/event_schema.py — keep in sync.
_RELIABILITY: dict[str, float] = {
    "official":     0.9,
    "sensor":       0.7,
    "crowdsourced": 0.5,
    "crowd":        0.5,   # normalised alias
    "anonymous":    0.3,
}


def _make_event(
    domain: str,
    event_type: str,
    entity_id: str,
    h3_cell: str,
    severity: float,
    source_type: str,
    scenario_tag: str | None = None,
    ts: datetime | None = None,
) -> dict:
    """
    Build one event dict.  Uses 'cell' (team convention).
    The CanonicalEvent validator maps cell → h3_cell automatically.
    severity is clamped to [0.0, 1.0].
    """
    src = "crowdsourced" if source_type == "crowd" else source_type
    if src not in _RELIABILITY:
        raise ValueError(f"Unknown source_type {source_type!r}")

    now = ts or datetime.now(timezone.utc)
    return {
        "event_id":            str(uuid.uuid4()),
        "domain":              domain,
        "event_type":          event_type.lower(),
        "entity_id":           entity_id,
        "cell":                h3_cell,          # team convention; schema maps to h3_cell
        "severity":            round(max(0.0, min(1.0, severity)), 3),
        "source_type":         src,
        "source_reliability":  _RELIABILITY[src],
        "event_timestamp":     now.isoformat(),
        "ingestion_timestamp": now.isoformat(),
        "parse_confidence":    1.0,
        "scenario_tag":        scenario_tag,
    }
