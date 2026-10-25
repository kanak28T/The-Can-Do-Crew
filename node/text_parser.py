"""
UrbanPulse — Unstructured Exhaust Text Parser
Task: B2.7 (Team Beta)
==============================================
Parses noisy, free-text municipal exhaust and citizen reports into strict,
privacy-preserving CanonicalEvent objects.

Rules:
- PII scrubbing/rejection: zero phone numbers, emails, names, or device IDs
- Regex adapters for exact brief examples ("Bus route 4 suspended", "Substation C voltage dropping", etc.)
- Fallback keyword detection for general multi-domain stress reports
"""

import re
import uuid
from datetime import datetime, timezone
from typing import Optional, Tuple

import sys
from pathlib import Path

# Ensure root is in python path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from contracts.event_schema import CanonicalEvent, SOURCE_RELIABILITY, has_pii

# Default central Nagpur H3 res-9 cell (Zero Mile / Sitabuldi) if none provided
DEFAULT_NAGPUR_H3 = "89609612d47ffff"

# ── Domain Pattern Rules ───────────────────────────────────────────────────────
# Each rule: (regex_pattern, domain, event_type, entity_prefix, default_severity)
ADAPTER_RULES = [
    # Transit patterns
    (
        re.compile(r"bus\s+route\s+([A-Za-z0-9_-]+)\s+(?:suspended|cancelled|halted|stopped|delayed)", re.IGNORECASE),
        "transit",
        "bus_suspended",
        "route_",
        0.80,
    ),
    (
        re.compile(r"route\s+([A-Za-z0-9_-]+)\s+(?:suspended|cancelled|halted|interrupted)", re.IGNORECASE),
        "transit",
        "bus_suspended",
        "route_",
        0.75,
    ),
    # Power patterns
    (
        re.compile(r"substation\s+([A-Za-z0-9_-]+)\s+(?:voltage\s+dropping|voltage\s+drop|blackout|tripped|offline|outage)", re.IGNORECASE),
        "power",
        "voltage_drop",
        "substation_",
        0.85,
    ),
    (
        re.compile(r"feeder\s+([A-Za-z0-9_-]+)\s+(?:down|blackout|tripped|low\s+voltage|failure)", re.IGNORECASE),
        "power",
        "feeder_failure",
        "feeder_",
        0.80,
    ),
    (
        re.compile(r"(?:total\s+)?power\s+outage|blackout|grid\s+failure", re.IGNORECASE),
        "power",
        "grid_failure",
        "grid_substation",
        0.90,
    ),
    # Road / infrastructure patterns
    (
        re.compile(r"(?:road|street|bridge|highway)\s+([A-Za-z0-9_-]+)\s+(?:closed|blocked|closure|shut|impassable)", re.IGNORECASE),
        "road",
        "road_closure",
        "road_",
        0.90,
    ),
    (
        re.compile(r"construction\s+(?:site\s+)?trapping|choke\s+point|waterlogging\s+on\s+([A-Za-z0-9_-]+)", re.IGNORECASE),
        "road",
        "road_blocked",
        "road_",
        0.75,
    ),
    # Communications / emergency call drops
    (
        re.compile(r"(?:(\d+)\s+)?(?:anonymized\s+)?(?:emergency\s+)?call\s+drops?", re.IGNORECASE),
        "comms",
        "call_drop",
        "tower_cluster",
        0.70,
    ),
    (
        re.compile(r"(?:cell\s+)?tower\s+([A-Za-z0-9_-]+)?\s*(?:down|offline|signal\s+loss|dead\s+zone)", re.IGNORECASE),
        "comms",
        "tower_offline",
        "tower_",
        0.80,
    ),
    # Water patterns
    (
        re.compile(r"(?:water\s+)?pump\s+([A-Za-z0-9_-]+)?\s*(?:failure|offline|tripped|broken|stopped)", re.IGNORECASE),
        "water",
        "pump_failure",
        "pump_",
        0.75,
    ),
    (
        re.compile(r"water\s+pressure\s+(?:drop|loss|falling|depleted)", re.IGNORECASE),
        "water",
        "pressure_drop",
        "pump_network",
        0.65,
    ),
    # Health patterns
    (
        re.compile(r"hospital\s+([A-Za-z0-9_-]+)?\s*(?:overload|critical|capacity\s+reached|ambulance\s+divert)", re.IGNORECASE),
        "health",
        "hospital_overload",
        "hospital_",
        0.85,
    ),
    (
        re.compile(r"(?:clinic|primary\s+health\s+centre|phc)\s+(?:closed|shut|unreachable)", re.IGNORECASE),
        "health",
        "clinic_isolation",
        "clinic_network",
        0.75,
    ),
]


class TextParseError(ValueError):
    """Raised when text cannot be scrubbed or parsed into an event."""
    pass


def parse_exhaust_text(
    text: str,
    h3_cell: Optional[str] = None,
    source_type: str = "crowdsourced",
    timestamp: Optional[datetime] = None,
    scenario_tag: Optional[str] = None,
) -> CanonicalEvent:
    """
    Parse an unstructured text string into a strict CanonicalEvent.

    Raises:
        TextParseError: if PII is detected and cannot be scrubbed, or if text matches no recognized domain.
    """
    if not text or not text.strip():
        raise TextParseError("Input text is empty.")

    # 1. PII Check — Privacy First (D11 & plan section 7)
    if has_pii(text):
        raise TextParseError(f"PII detected in incoming report: '{text[:40]}...'. Scrubbing rejected.")

    clean_text = text.strip()
    cell = (h3_cell or DEFAULT_NAGPUR_H3).lower()
    ts = timestamp or datetime.now(timezone.utc)
    source = "crowdsourced" if source_type == "crowd" else source_type
    reliability = SOURCE_RELIABILITY.get(source, 0.5)

    # 2. Rule-based regex pattern matching
    matched = False
    domain: str = ""
    event_type: str = ""
    entity_id: str = ""
    severity: float = 0.5
    confidence: float = 0.85

    for pattern, d_dom, d_type, d_prefix, d_sev in ADAPTER_RULES:
        m = pattern.search(clean_text)
        if m:
            domain = d_dom
            event_type = d_type
            severity = d_sev
            # Extract captured entity ID if present
            groups = m.groups()
            if groups and groups[0]:
                raw_entity = groups[0].lower().strip()
                entity_id = f"{d_prefix}{raw_entity}" if not raw_entity.startswith(d_prefix) else raw_entity
            else:
                entity_id = f"{d_prefix}general"
            matched = True
            confidence = 0.92
            break

    # 3. Fallback keyword heuristic if exact pattern didn't fire
    if not matched:
        lower = clean_text.lower()
        if "bus" in lower or "transit" in lower or "metro" in lower:
            domain = "transit"
            event_type = "transit_disruption"
            entity_id = "transit_general"
            severity = 0.60
            confidence = 0.65
        elif "voltage" in lower or "electric" in lower or "power" in lower or "light" in lower:
            domain = "power"
            event_type = "power_stress"
            entity_id = "power_general"
            severity = 0.65
            confidence = 0.65
        elif "water" in lower or "pipe" in lower or "tanker" in lower:
            domain = "water"
            event_type = "water_stress"
            entity_id = "water_general"
            severity = 0.60
            confidence = 0.65
        elif "road" in lower or "traffic" in lower or "jam" in lower or "closed" in lower:
            domain = "road"
            event_type = "road_hazard"
            entity_id = "road_general"
            severity = 0.70
            confidence = 0.65
        elif "hospital" in lower or "doctor" in lower or "clinic" in lower or "medical" in lower:
            domain = "health"
            event_type = "health_stress"
            entity_id = "health_general"
            severity = 0.70
            confidence = 0.65
        elif "network" in lower or "phone" in lower or "signal" in lower or "call" in lower:
            domain = "comms"
            event_type = "comms_stress"
            entity_id = "comms_general"
            severity = 0.60
            confidence = 0.65
        else:
            raise TextParseError(f"Unable to extract urban domain from text: '{clean_text}'")

    # 4. Construct and validate CanonicalEvent
    event = CanonicalEvent(
        event_id=str(uuid.uuid4()),
        domain=domain,
        event_type=event_type,
        entity_id=entity_id,
        h3_cell=cell,
        severity=severity,
        source_type=source,
        source_reliability=reliability,
        event_timestamp=ts,
        ingestion_timestamp=datetime.now(timezone.utc),
        parse_confidence=confidence,
        scenario_tag=scenario_tag,
    )
    return event


if __name__ == "__main__":
    # Test brief benchmark examples
    test_cases = [
        "Bus route 4 suspended",
        "Substation C voltage dropping",
        "300 anonymized emergency call drops over 48 hours",
        "Road R-14 closed",
        "Water pump station 2 failure",
        "Hospital Sadar capacity reached",
    ]

    print("Running Text Parser Verification...")
    for text in test_cases:
        ev = parse_exhaust_text(text)
        print(f"[OK] '{text}' -> Domain: {ev.domain:7} | Type: {ev.event_type:18} | Entity: {ev.entity_id:15} | Sev: {ev.severity}")

    print("\nAll benchmark test cases parsed into valid CanonicalEvents successfully!")
