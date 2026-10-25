"""Water domain simulator — pump failures and water shortages."""
import json, random, uuid
from datetime import datetime, timezone
from typing import List

with open("data/mapping_tables/pump_cells.json") as f:
    PUMP_CELLS: dict = json.load(f)
PUMPS = [k for k in PUMP_CELLS if not k.startswith("_")]


def _event(domain, event_type, entity_id, h3_cell, severity, source_type, scenario_tag=None):
    now = datetime.now(timezone.utc)
    return {
        "event_id": str(uuid.uuid4()),
        "domain": domain,
        "event_type": event_type,
        "entity_id": entity_id,
        "cell": h3_cell,
        "severity": round(severity, 3),
        "source_type": source_type,
        "source_reliability": {"official": 0.9, "sensor": 0.7, "crowdsourced": 0.5, "anonymous": 0.3}[source_type],
        "event_timestamp": now.isoformat(),
        "ingestion_timestamp": now.isoformat(),
        "parse_confidence": 1.0,
        "scenario_tag": scenario_tag,
    }


def pump_failure(pump_id: str = None, scenario_tag=None) -> List[dict]:
    """Complete pump failure → no water supply."""
    pump = pump_id or random.choice(PUMPS)
    cells = PUMP_CELLS.get(pump, [])
    return [_event("water", "pump_failure", pump, cell, 1.0, "official", scenario_tag) for cell in cells]


def pressure_drop(pump_id: str = None, severity: float = None, scenario_tag=None) -> List[dict]:
    """Partial water pressure reduction."""
    pump = pump_id or random.choice(PUMPS)
    sev = severity if severity is not None else random.uniform(0.4, 0.8)
    cells = PUMP_CELLS.get(pump, [])
    return [_event("water", "pressure_drop", pump, cell, sev, "sensor", scenario_tag) for cell in cells]


def contamination_detected(pump_id: str = None, severity: float = None, scenario_tag=None) -> List[dict]:
    """Water quality issue detected."""
    pump = pump_id or random.choice(PUMPS)
    sev = severity if severity is not None else random.uniform(0.6, 0.9)
    cells = PUMP_CELLS.get(pump, [])
    return [_event("water", "contamination", pump, cell, sev, "sensor", scenario_tag) for cell in cells]


def water_restored(pump_id: str, scenario_tag=None) -> List[dict]:
    """Pump back online."""
    cells = PUMP_CELLS.get(pump_id, [])
    return [_event("water", "water_restored", pump_id, cell, 0.0, "official", scenario_tag) for cell in cells]


def random_stream(n: int = 5, seed: int = None) -> List[dict]:
    if seed: random.seed(seed)
    events = []
    for _ in range(n):
        pump = random.choice(PUMPS)
        event_type = random.choice(["failure", "pressure_drop", "contamination"])
        if event_type == "failure":
            events.extend(pump_failure(pump))
        elif event_type == "pressure_drop":
            events.extend(pressure_drop(pump))
        else:
            events.extend(contamination_detected(pump))
    return events
