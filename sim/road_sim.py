"""Road domain simulator — road closures, accidents, flooding."""
import json, random, uuid
from datetime import datetime, timezone
from typing import List
import h3

# Load H3 grid to generate random road closures
with open("data/nagpur_h3_res9.geojson") as f:
    grid = json.load(f)
ALL_CELLS = [feat["properties"]["cell"] for feat in grid["features"]]


from sim._sim_base import _make_event as _event


def road_closed(cell: str = None, reason: str = "construction", severity: float = None, scenario_tag=None) -> List[dict]:
    """Major road closure blocking traffic."""
    cell = cell or random.choice(ALL_CELLS)
    sev = severity if severity is not None else 1.0
    entity_id = f"road-{cell}-{reason}"
    return [_event("road", "road_closed", entity_id, cell, sev, "official", scenario_tag)]


def accident_reported(cell: str = None, severity: float = None, scenario_tag=None) -> List[dict]:
    """Traffic accident blocking lanes."""
    cell = cell or random.choice(ALL_CELLS)
    sev = severity if severity is not None else random.uniform(0.5, 0.9)
    entity_id = f"accident-{cell}"
    return [_event("road", "accident", entity_id, cell, sev, ("crowdsourced"), scenario_tag)]


def flooding(cell: str = None, severity: float = None, scenario_tag=None) -> List[dict]:
    """Road flooding after heavy rain."""
    cell = cell or random.choice(ALL_CELLS)
    sev = severity if severity is not None else random.uniform(0.6, 1.0)
    entity_id = f"flood-{cell}"
    return [_event("road", "flooding", entity_id, cell, sev, "sensor", scenario_tag)]


def heavy_congestion(cell: str = None, severity: float = None, scenario_tag=None) -> List[dict]:
    """Severe traffic congestion (not closure, just slow)."""
    cell = cell or random.choice(ALL_CELLS)
    sev = severity if severity is not None else random.uniform(0.4, 0.7)
    entity_id = f"congestion-{cell}"
    return [_event("road", "congestion", entity_id, cell, sev, ("crowdsourced"), scenario_tag)]


def road_cleared(cell: str, scenario_tag=None) -> List[dict]:
    """Road reopened, traffic flowing."""
    entity_id = f"road-{cell}"
    return [_event("road", "road_cleared", entity_id, cell, 0.0, "official", scenario_tag)]


def random_stream(n: int = 5, seed: int = None) -> List[dict]:
    rng = random.Random(seed) if seed is not None else random
    events = []
    for _ in range(n):
        cell = rng.choice(ALL_CELLS)
        event_type = rng.choice(["closed", "accident", "flooding", "congestion"])
        if event_type == "closed":
            events.extend(road_closed(cell))
        elif event_type == "accident":
            events.extend(accident_reported(cell))
        elif event_type == "flooding":
            events.extend(flooding(cell))
        else:
            events.extend(heavy_congestion(cell))
    return events
