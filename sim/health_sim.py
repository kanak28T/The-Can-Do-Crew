"""Health domain simulator — hospital capacity and emergency events."""
import json, random, uuid
from datetime import datetime, timezone
from typing import List

with open("data/mapping_tables/hospital_cells.json") as f:
    HOSPITAL_CELLS: dict = json.load(f)
HOSPITALS = [k for k in HOSPITAL_CELLS if not k.startswith("_")]


from sim._sim_base import _make_event as _event


def capacity_critical(hospital_id: str = None, severity: float = None, scenario_tag=None) -> List[dict]:
    """Hospital at or over capacity, cannot accept new patients."""
    hospital = hospital_id or random.choice(HOSPITALS)
    sev = severity if severity is not None else random.uniform(0.8, 1.0)
    cells = HOSPITAL_CELLS.get(hospital, [])
    return [_event("health", "capacity_critical", hospital, cell, sev, "official", scenario_tag) for cell in cells]


def capacity_high(hospital_id: str = None, severity: float = None, scenario_tag=None) -> List[dict]:
    """Hospital near capacity (70-90%)."""
    hospital = hospital_id or random.choice(HOSPITALS)
    sev = severity if severity is not None else random.uniform(0.5, 0.7)
    cells = HOSPITAL_CELLS.get(hospital, [])
    return [_event("health", "capacity_high", hospital, cell, sev, "official", scenario_tag) for cell in cells]


def equipment_failure(hospital_id: str = None, severity: float = None, scenario_tag=None) -> List[dict]:
    """Critical medical equipment failure (ICU, ventilators, etc.)."""
    hospital = hospital_id or random.choice(HOSPITALS)
    sev = severity if severity is not None else random.uniform(0.6, 0.9)
    cells = HOSPITAL_CELLS.get(hospital, [])
    return [_event("health", "equipment_failure", hospital, cell, sev, "official", scenario_tag) for cell in cells]


def staff_shortage(hospital_id: str = None, severity: float = None, scenario_tag=None) -> List[dict]:
    """Insufficient medical staff available."""
    hospital = hospital_id or random.choice(HOSPITALS)
    sev = severity if severity is not None else random.uniform(0.4, 0.7)
    cells = HOSPITAL_CELLS.get(hospital, [])
    return [_event("health", "staff_shortage", hospital, cell, sev, "official", scenario_tag) for cell in cells]


def outbreak_suspected(hospital_id: str = None, severity: float = None, scenario_tag=None) -> List[dict]:
    """Disease outbreak suspected in area."""
    hospital = hospital_id or random.choice(HOSPITALS)
    sev = severity if severity is not None else random.uniform(0.5, 0.8)
    cells = HOSPITAL_CELLS.get(hospital, [])
    return [_event("health", "outbreak_suspected", hospital, cell, sev, "sensor", scenario_tag) for cell in cells]


def capacity_normal(hospital_id: str, scenario_tag=None) -> List[dict]:
    """Hospital back to normal operations."""
    cells = HOSPITAL_CELLS.get(hospital_id, [])
    return [_event("health", "capacity_normal", hospital_id, cell, 0.0, "official", scenario_tag) for cell in cells]


def random_stream(n: int = 5, seed: int = None) -> List[dict]:
    rng = random.Random(seed) if seed is not None else random
    events = []
    for _ in range(n):
        hospital = rng.choice(HOSPITALS)
        event_type = rng.choice(["capacity_critical", "capacity_high", "equipment_failure", "staff_shortage", "outbreak_suspected"])
        if event_type == "capacity_critical":
            events.extend(capacity_critical(hospital))
        elif event_type == "capacity_high":
            events.extend(capacity_high(hospital))
        elif event_type == "equipment_failure":
            events.extend(equipment_failure(hospital))
        elif event_type == "staff_shortage":
            events.extend(staff_shortage(hospital))
        else:
            events.extend(outbreak_suspected(hospital))
    return events
