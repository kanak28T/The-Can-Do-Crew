"""Communications domain simulator — cell tower outages and network issues."""
import json, random, uuid
from datetime import datetime, timezone
from typing import List

with open("data/mapping_tables/tower_cells.json") as f:
    TOWER_CELLS: dict = json.load(f)
TOWERS = [k for k in TOWER_CELLS if not k.startswith("_")]


from sim._sim_base import _make_event as _event


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
    rng = random.Random(seed) if seed is not None else random
    events = []
    for _ in range(n):
        tower = rng.choice(TOWERS)
        event_type = rng.choice(["tower_down", "signal_degraded", "network_congestion", "maintenance"])
        if event_type == "tower_down":
            events.extend(tower_down(tower))
        elif event_type == "signal_degraded":
            events.extend(signal_degraded(tower))
        elif event_type == "network_congestion":
            events.extend(network_congestion(tower))
        else:
            events.extend(tower_maintenance(tower))
    return events
