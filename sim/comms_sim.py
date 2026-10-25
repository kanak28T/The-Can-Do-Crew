"""Communications domain simulator — cell tower outages and network issues."""
import json, random, uuid
from datetime import datetime, timezone
from typing import List

with open("data/mapping_tables/tower_cells.json") as f:
    TOWER_CELLS: dict = json.load(f)
TOWERS = [k for k in TOWER_CELLS if not k.startswith("_")]


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


def tower_down(tower_id: str = None, scenario_tag=None) -> List[dict]:
    """Cell tower completely offline — no service."""
    tower = tower_id or random.choice(TOWERS)
    cells = TOWER_CELLS.get(tower, [])
    return [_event("comms", "tower_down", tower, cell, 1.0, "official", scenario_tag) for cell in cells]


def signal_degraded(tower_id: str = None, severity: float = None, scenario_tag=None) -> List[dict]:
    """Weak signal strength, dropped calls."""
    tower = tower_id or random.choice(TOWERS)
    sev = severity if severity is not None else random.uniform(0.4, 0.7)
    cells = TOWER_CELLS.get(tower, [])
    return [_event("comms", "signal_degraded", tower, cell, sev, "sensor", scenario_tag) for cell in cells]


def network_congestion(tower_id: str = None, severity: float = None, scenario_tag=None) -> List[dict]:
    """Network overloaded, slow data speeds."""
    tower = tower_id or random.choice(TOWERS)
    sev = severity if severity is not None else random.uniform(0.5, 0.8)
    cells = TOWER_CELLS.get(tower, [])
    return [_event("comms", "network_congestion", tower, cell, sev, ("crowdsourced"), scenario_tag) for cell in cells]


def tower_maintenance(tower_id: str = None, severity: float = None, scenario_tag=None) -> List[dict]:
    """Planned tower maintenance, reduced capacity."""
    tower = tower_id or random.choice(TOWERS)
    sev = severity if severity is not None else random.uniform(0.3, 0.6)
    cells = TOWER_CELLS.get(tower, [])
    return [_event("comms", "tower_maintenance", tower, cell, sev, "official", scenario_tag) for cell in cells]


def service_restored(tower_id: str, scenario_tag=None) -> List[dict]:
    """Tower back online, full service."""
    cells = TOWER_CELLS.get(tower_id, [])
    return [_event("comms", "service_restored", tower_id, cell, 0.0, "official", scenario_tag) for cell in cells]


def random_stream(n: int = 5, seed: int = None) -> List[dict]:
    if seed: random.seed(seed)
    events = []
    for _ in range(n):
        tower = random.choice(TOWERS)
        event_type = random.choice(["tower_down", "signal_degraded", "network_congestion", "maintenance"])
        if event_type == "tower_down":
            events.extend(tower_down(tower))
        elif event_type == "signal_degraded":
            events.extend(signal_degraded(tower))
        elif event_type == "network_congestion":
            events.extend(network_congestion(tower))
        else:
            events.extend(tower_maintenance(tower))
    return events
