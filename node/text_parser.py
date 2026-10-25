"""
UrbanPulse — Node Text Parser
==============================
Owner  : Kanak (A2) — Day 3 (A3.11 / plan D11)

Converts unstructured urban-exhaust text into a CanonicalEvent.
Two-tier: regex/keyword rules first (fast, deterministic),
          optional LLM fallback (COULD tier — not used in production path).

Handles the exact example strings from the problem brief:
  "Bus route 4 suspended"
  "Bus route 4 suspended until further notice"
  "Route 7 cancelled"
  "Substation C voltage dropping"
  "Road X closed"
  "Water pressure drop in sector 4"
  "300 emergency call drops over 48 hours"

PII scrubbing happens HERE before the event leaves the node.
The canonical event returned contains ZERO free text.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

# ── PII scrubber (same patterns as event_schema.py) ──────────────────────────
_SCRUB_PATTERNS = [
    (re.compile(r"\b[6-9]\d{9}\b"),               "***"),   # Indian mobile
    (re.compile(r"\b\d{10}\b"),                    "***"),   # 10-digit phone
    (re.compile(r"\b\d{12}\b"),                    "***"),   # Aadhaar
    (re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"),        "***"),   # PAN
    (re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"), "***"),
    (re.compile(r"\b(Mr|Mrs|Ms|Dr|Sir|Prof)\s+\w+", re.I), "***"),
]


def scrub_pii(text: str) -> str:
    for pattern, replacement in _SCRUB_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


# ── Regex rule definitions ────────────────────────────────────────────────────
# Each rule: (pattern, domain, event_type, entity_extractor_fn, severity_fn)
# entity_extractor returns (entity_id, severity) from the match

def _route_entity(m: re.Match) -> tuple[str, float]:
    num = m.group("num") or m.group("name") or "unknown"
    return f"route_{num.strip()}", 0.85

def _road_entity(m: re.Match) -> tuple[str, float]:
    name = (m.group("road") or "unknown").strip()
    return f"road_{name[:20]}", 0.90

def _feeder_entity(m: re.Match) -> tuple[str, float]:
    name = (m.group("feeder") or "unknown").strip()
    return f"feeder_{name[:10]}", 0.80

def _tower_entity(m: re.Match) -> tuple[str, float]:
    name = (m.group("tower") or "unknown").strip()
    return f"tower_{name[:10]}", 0.70

def _pump_entity(m: re.Match) -> tuple[str, float]:
    name = (m.group("zone") or "unknown").strip()
    return f"pump_{name[:10]}", 0.75

def _hospital_entity(m: re.Match) -> tuple[str, float]:
    name = (m.group("name") or "hospital").strip()
    return f"hospital_{name[:15]}", 0.80


_RULES: list[tuple] = [
    # Transit suspensions / cancellations
    (re.compile(
        r"(bus\s+)?route\s+(?P<num>\w+)\s+(suspended|cancelled|canceled|cancelled\s+until|closed)",
        re.I),
     "transit", "transit_suspension", _route_entity),

    (re.compile(
        r"(bus\s+)?route\s+(?P<num>\w+)\s+(delayed|delay|minor\s+delay|severe\s+delay)",
        re.I),
     "transit", "transit_suspension", lambda m: (f"route_{(m.group('num') or 'unknown').strip()}", 0.50)),

    (re.compile(
        r"(bus\s+)?route\s+(?P<name>[A-Za-z0-9\s\-]+?)\s+(suspended|cancelled|canceled)",
        re.I),
     "transit", "transit_suspension", _route_entity),

    # Road closures
    (re.compile(
        r"road\s+(?P<road>[A-Za-z0-9\-]+)\s+(closed|blocked|closure)",
        re.I),
     "roads", "road_closure", _road_entity),

    (re.compile(
        r"(?P<road>[A-Za-z0-9\s\-]+?)\s+road\s+(closed|blocked|under\s+construction)",
        re.I),
     "roads", "road_closure", lambda m: (f"road_{(m.group('road') or 'unknown').strip()[:20]}", 0.90)),

    (re.compile(r"construction\s+(on|at|near)\s+(?P<road>[A-Za-z0-9\s\-]+)", re.I),
     "roads", "road_closure",
     lambda m: (f"road_{(m.group('road') or 'unknown').strip()[:20]}", 0.70)),

    # Power — voltage drop / blackout
    (re.compile(
        r"substation\s+(?P<feeder>[A-Za-z0-9\-]+)\s+(voltage\s+drop|voltage\s+dropp|low\s+voltage|dropping)",
        re.I),
     "power", "voltage_drop", _feeder_entity),

    (re.compile(
        r"feeder\s+(?P<feeder>[A-Za-z0-9\-]+)\s+(voltage|failure|fault|tripped)",
        re.I),
     "power", "voltage_drop", _feeder_entity),

    (re.compile(
        r"(power\s+)?(blackout|outage|cut)\s+(in|at|near)?\s*(?P<feeder>[A-Za-z0-9\s\-]+)",
        re.I),
     "power", "blackout",
     lambda m: (f"feeder_{(m.group('feeder') or 'unknown').strip()[:10]}", 0.95)),

    # Water
    (re.compile(
        r"water\s+(pressure\s+)?(drop|failure|outage|loss)\s+(in|at|near)?\s*(?P<zone>[A-Za-z0-9\s\-]+)?",
        re.I),
     "water", "pressure_drop", _pump_entity),

    (re.compile(
        r"pump\s+(failure|fault|down)\s+(in|at|near)?\s*(?P<zone>[A-Za-z0-9\s\-]+)?",
        re.I),
     "water", "pump_failure", _pump_entity),

    # Communications — call drops
    (re.compile(
        r"(\d+)\s+(emergency\s+)?call\s+drop[s]?\s+(over|in|per|during)?",
        re.I),
     "comms", "call_drop_spike",
     lambda m: (f"tower_area", min(1.0, int(m.group(1)) / 500))),

    (re.compile(
        r"(tower|cell\s+tower)\s+(?P<tower>[A-Za-z0-9\-]+)\s+(down|offline|failure)",
        re.I),
     "comms", "tower_down", _tower_entity),

    # Health
    (re.compile(
        r"(?P<name>[A-Za-z\s]+?)\s+(hospital|clinic|dispensary)\s+(full|overloaded|at\s+capacity)",
        re.I),
     "health", "hospital_load_high", _hospital_entity),

    (re.compile(
        r"(hospital|clinic|dispensary)\s+(?P<name>[A-Za-z0-9\s\-]+?)\s+(closed|shutdown)",
        re.I),
     "health", "clinic_closed", _hospital_entity),
]


# ── Parser result ─────────────────────────────────────────────────────────────

class ParseResult:
    __slots__ = ("domain", "event_type", "entity_id", "severity",
                 "parse_confidence", "matched_rule", "scrubbed_text")

    def __init__(self, domain, event_type, entity_id, severity,
                 parse_confidence, matched_rule, scrubbed_text):
        self.domain          = domain
        self.event_type      = event_type
        self.entity_id       = entity_id
        self.severity        = severity
        self.parse_confidence = parse_confidence
        self.matched_rule    = matched_rule
        self.scrubbed_text   = scrubbed_text

    def __repr__(self):
        return (f"ParseResult(domain={self.domain!r}, type={self.event_type!r}, "
                f"entity={self.entity_id!r}, severity={self.severity}, "
                f"confidence={self.parse_confidence})")


def parse(
    raw_text: str,
    h3_cell: str,
    source_type: str = "crowdsourced",
    event_timestamp: Optional[datetime] = None,
) -> Optional[dict]:
    """
    Parse raw unstructured text into a canonical event dict.

    Args:
        raw_text        : The unstructured input string
        h3_cell         : H3 res-9 cell where this report came from
        source_type     : "official" | "sensor" | "crowdsourced" | "anonymous"
        event_timestamp : UTC datetime (defaults to now)

    Returns:
        dict compatible with CanonicalEvent, or None if no rule matched.
        The returned dict has NO free text fields — scrubbing is done here.
    """
    if not raw_text or not raw_text.strip():
        return None

    # Scrub PII before any processing
    clean_text = scrub_pii(raw_text.strip())

    # Try each rule
    for pattern, domain, event_type, entity_fn in _RULES:
        m = pattern.search(clean_text)
        if m:
            entity_id, severity = entity_fn(m)
            # entity_id must be safe — strip any residual special chars
            entity_id = re.sub(r"[^A-Za-z0-9_\-]", "_", entity_id)[:64]
            if not entity_id:
                entity_id = f"{domain}_unknown"

            ts = event_timestamp or datetime.now(timezone.utc)
            from contracts.event_schema import SOURCE_RELIABILITY
            reliability = SOURCE_RELIABILITY.get(source_type, 0.5)

            return {
                "event_id":            str(uuid.uuid4()),
                "domain":              domain,
                "event_type":          event_type,
                "entity_id":           entity_id,
                "h3_cell":             h3_cell,
                "severity":            round(severity, 3),
                "source_type":         source_type,
                "source_reliability":  reliability,
                "event_timestamp":     ts.isoformat(),
                "ingestion_timestamp": datetime.now(timezone.utc).isoformat(),
                "parse_confidence":    0.80,   # regex match = good confidence
                "scenario_tag":        None,
            }

    # No rule matched — return unknown event with low confidence
    # Still useful for anomaly detection layer
    entity_hash = hashlib.sha256(clean_text.encode()).hexdigest()[:8]
    ts = event_timestamp or datetime.now(timezone.utc)
    from contracts.event_schema import SOURCE_RELIABILITY
    return {
        "event_id":            str(uuid.uuid4()),
        "domain":              "comms",        # safest default domain
        "event_type":          "unknown",
        "entity_id":           f"unmatched_{entity_hash}",
        "h3_cell":             h3_cell,
        "severity":            0.30,
        "source_type":         source_type,
        "source_reliability":  SOURCE_RELIABILITY.get(source_type, 0.3),
        "event_timestamp":     ts.isoformat(),
        "ingestion_timestamp": datetime.now(timezone.utc).isoformat(),
        "parse_confidence":    0.20,   # low — no rule matched
        "scenario_tag":        None,
    }
