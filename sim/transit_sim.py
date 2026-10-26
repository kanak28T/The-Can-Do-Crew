"""Transit domain simulator — bus route delays and cancellations."""
import json, random, uuid
from datetime import datetime, timezone
from typing import List

with open("data/mapping_tables/route_cells.json") as f:
    ROUTE_CELLS: dict = json.load(f)
ROUTES = [k for k in ROUTE_CELLS if not k.startswith("_")]


from sim._sim_base import _make_event as _event


def route_cancelled(route_id: str = None, scenario_tag=None) -> List[dict]:
    """Bus route completely cancelled."""
    route = route_id or random.choice(ROUTES)
    cells = ROUTE_CELLS.get(route, [])
    return [_event("transit", "route_cancelled", route, cell, 1.0, "official", scenario_tag) for cell in cells]


def severe_delay(route_id: str = None, severity: float = None, scenario_tag=None) -> List[dict]:
    """Route experiencing major delays (30+ minutes)."""
    route = route_id or random.choice(ROUTES)
    sev = severity if severity is not None else random.uniform(0.6, 0.9)
    cells = ROUTE_CELLS.get(route, [])
    return [_event("transit", "severe_delay", route, cell, sev, "sensor", scenario_tag) for cell in cells]


def minor_delay(route_id: str = None, severity: float = None, scenario_tag=None) -> List[dict]:
    """Route experiencing minor delays (10-20 minutes)."""
    route = route_id or random.choice(ROUTES)
    sev = severity if severity is not None else random.uniform(0.3, 0.5)
    cells = ROUTE_CELLS.get(route, [])
    return [_event("transit", "minor_delay", route, cell, sev, ("crowdsourced"), scenario_tag) for cell in cells]


def overcrowding(route_id: str = None, severity: float = None, scenario_tag=None) -> List[dict]:
    """Bus overcrowded, denying boarding."""
    route = route_id or random.choice(ROUTES)
    sev = severity if severity is not None else random.uniform(0.5, 0.8)
    cells = ROUTE_CELLS.get(route, [])
    return [_event("transit", "overcrowding", route, cell, sev, ("crowdsourced"), scenario_tag) for cell in cells]


def service_resumed(route_id: str, scenario_tag=None) -> List[dict]:
    """Route back to normal service."""
    cells = ROUTE_CELLS.get(route_id, [])
    return [_event("transit", "service_resumed", route_id, cell, 0.0, "official", scenario_tag) for cell in cells]


def random_stream(n: int = 5, seed: int = None) -> List[dict]:
    rng = random.Random(seed) if seed is not None else random
    events = []
    for _ in range(n):
        route = rng.choice(ROUTES)
        event_type = rng.choice(["cancelled", "severe_delay", "minor_delay", "overcrowding"])
        if event_type == "cancelled":
            events.extend(route_cancelled(route))
        elif event_type == "severe_delay":
            events.extend(severe_delay(route))
        elif event_type == "minor_delay":
            events.extend(minor_delay(route))
        else:
            events.extend(overcrowding(route))
    return events
