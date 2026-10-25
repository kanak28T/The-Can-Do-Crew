"""Power domain simulator — feeder voltage drops and blackouts."""
import json, random, uuid
from datetime import datetime, timezone, timedelta
from typing import List

with open("data/mapping_tables/feeder_cells.json") as f:
    FEEDER_CELLS: dict = json.load(f)
FEEDERS = [k for k in FEEDER_CELLS if not k.startswith("_")]


def _event(domain, event_type, entity_id, h3_cell, severity, source_type, scenario_tag=None):
    now = datetime.now(timezone.utc)
    return {
        "event_id": str(uuid.uuid4()),
        "domain": domain,
        "event_type": event_type,
        "entity_id": entity_id,
        "h3_cell": h3_cell,
        "severity": round(severity, 3),
        "source_type": source_type,
        "source_reliability": {"official": 0.9, "sensor": 0.7, "crowd": 0.5, "anonymous": 0.3}[source_type],
        "event_timestamp": now.isoformat(),
        "ingestion_timestamp": now.isoformat(),
        "parse_confidence": 1.0,
        "scenario_tag": scenario_tag,
    }


def voltage_drop(feeder_id: str = None, severity: float = None, scenario_tag=None) -> List[dict]:
    feeder = feeder_id or random.choice(FEEDERS)
    sev = severity if severity is not None else random.uniform(0.3, 0.7)
    cells = FEEDER_CELLS.get(feeder, [])
    return [_event("power", "voltage_drop", feeder, cell, sev, "sensor", scenario_tag) for cell in cells]


def blackout(feeder_id: str = None, scenario_tag=None) -> List[dict]:
    feeder = feeder_id or random.choice(FEEDERS)
    cells = FEEDER_CELLS.get(feeder, [])
    return [_event("power", "blackout", feeder, cell, 1.0, "official", scenario_tag) for cell in cells]


def power_restored(feeder_id: str, scenario_tag=None) -> List[dict]:
    cells = FEEDER_CELLS.get(feeder_id, [])
    return [_event("power", "power_restored", feeder_id, cell, 0.0, "official", scenario_tag) for cell in cells]


def random_stream(n: int = 5, seed: int = None) -> List[dict]:
    if seed: random.seed(seed)
    events = []
    for _ in range(n):
        feeder = random.choice(FEEDERS)
        if random.random() < 0.3:
            events.extend(blackout(feeder))
        else:
            events.extend(voltage_drop(feeder))
    return events
