"""Water domain simulator — pump failures and water shortages.

All events use the team's 'cell' property via the shared _make_event helper.
Deterministic RNG: pass a seed to random_stream() or provide rng to generators.
"""

import json
import random as _random
from datetime import datetime
from typing import List, Optional
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sim._sim_base import _make_event as _event

with open("data/mapping_tables/pump_cells.json") as f:
    PUMP_CELLS: dict = json.load(f)
PUMPS = [k for k in PUMP_CELLS if not k.startswith("_")]


def pump_failure(
    pump_id: str = None,
    scenario_tag: str = None,
    rng: _random.Random = None,
    ts: datetime = None,
) -> List[dict]:
    rng = rng or _random.Random()
    pump = pump_id or rng.choice(PUMPS)
    cells = PUMP_CELLS.get(pump, [])
    return [_event("water", "pump_failure", pump, cell, 1.0, "official", scenario_tag, ts) for cell in cells]


def pressure_drop(
    pump_id: str = None,
    severity: float = None,
    scenario_tag: str = None,
    rng: _random.Random = None,
    ts: datetime = None,
) -> List[dict]:
    rng = rng or _random.Random()
    pump = pump_id or rng.choice(PUMPS)
    sev = severity if severity is not None else rng.uniform(0.4, 0.8)
    cells = PUMP_CELLS.get(pump, [])
    return [_event("water", "pressure_drop", pump, cell, sev, "sensor", scenario_tag, ts) for cell in cells]


def contamination_detected(
    pump_id: str = None,
    severity: float = None,
    scenario_tag: str = None,
    rng: _random.Random = None,
    ts: datetime = None,
) -> List[dict]:
    rng = rng or _random.Random()
    pump = pump_id or rng.choice(PUMPS)
    sev = severity if severity is not None else rng.uniform(0.6, 0.9)
    cells = PUMP_CELLS.get(pump, [])
    return [_event("water", "contamination", pump, cell, sev, "sensor", scenario_tag, ts) for cell in cells]


def water_restored(
    pump_id: str,
    scenario_tag: str = None,
    ts: datetime = None,
) -> List[dict]:
    cells = PUMP_CELLS.get(pump_id, [])
    return [_event("water", "water_restored", pump_id, cell, 0.0, "official", scenario_tag, ts) for cell in cells]


def random_stream(
    n: int = 5,
    seed: Optional[int] = None,
    scenario_tag: str = None,
) -> List[dict]:
    """Deterministic when seed is set. Same seed + n → identical events."""
    rng = _random.Random(seed) if seed is not None else _random.Random()
    events: List[dict] = []
    for _ in range(n):
        pump = rng.choice(PUMPS)
        choice = rng.choice(["failure", "pressure_drop", "contamination"])
        if choice == "failure":
            events.extend(pump_failure(pump, scenario_tag=scenario_tag, rng=rng))
        elif choice == "pressure_drop":
            events.extend(pressure_drop(pump, scenario_tag=scenario_tag, rng=rng))
        else:
            events.extend(contamination_detected(pump, scenario_tag=scenario_tag, rng=rng))
    return events
