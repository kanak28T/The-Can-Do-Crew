"""Power domain simulator — feeder voltage drops and blackouts.

Deterministic: pass seed to random_stream(); same seed → same events.
Uses 'cell' field (team convention). CanonicalEvent maps it to h3_cell.
"""
import json
import random as _random
from datetime import datetime
from typing import List, Optional
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sim._sim_base import _make_event

with open("data/mapping_tables/feeder_cells.json") as f:
    FEEDER_CELLS: dict = json.load(f)
FEEDERS = [k for k in FEEDER_CELLS if not k.startswith("_")]


def voltage_drop(feeder_id: str = None, severity: float = None,
                 scenario_tag: str = None, rng: _random.Random = None,
                 ts: datetime = None) -> List[dict]:
    rng = rng or _random.Random()
    feeder = feeder_id or rng.choice(FEEDERS)
    sev = severity if severity is not None else rng.uniform(0.3, 0.7)
    cells = FEEDER_CELLS.get(feeder, [])
    return [_make_event("power", "voltage_drop", feeder, cell, sev, "sensor", scenario_tag, ts)
            for cell in cells]


def blackout(feeder_id: str = None, scenario_tag: str = None,
             rng: _random.Random = None, ts: datetime = None) -> List[dict]:
    rng = rng or _random.Random()
    feeder = feeder_id or rng.choice(FEEDERS)
    cells = FEEDER_CELLS.get(feeder, [])
    return [_make_event("power", "blackout", feeder, cell, 1.0, "official", scenario_tag, ts)
            for cell in cells]


def power_restored(feeder_id: str, scenario_tag: str = None,
                   ts: datetime = None) -> List[dict]:
    cells = FEEDER_CELLS.get(feeder_id, [])
    return [_make_event("power", "power_restored", feeder_id, cell, 0.0, "official", scenario_tag, ts)
            for cell in cells]


def random_stream(n: int = 5, seed: Optional[int] = None,
                  scenario_tag: str = None) -> List[dict]:
    """Deterministic when seed is set. Same seed + same n → identical events."""
    rng = _random.Random(seed)
    events = []
    for _ in range(n):
        feeder = rng.choice(FEEDERS)
        if rng.random() < 0.3:
            events.extend(blackout(feeder, scenario_tag=scenario_tag, rng=rng))
        else:
            events.extend(voltage_drop(feeder, scenario_tag=scenario_tag, rng=rng))
    return events
