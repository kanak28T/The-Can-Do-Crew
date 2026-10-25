"""
Baseline (static) feature vector per H3 res-9 cell.
Loaded once at startup. Updated when data files arrive.
A2 (Kanak) fills population + econ; A1 fills hospital_isolation.
"""
import json, os
from dataclasses import dataclass


@dataclass
class BaselineFeatures:
    h3_cell:             str
    hospital_isolation:  float = 0.5   # from Dijkstra (A1)
    transit_deficit:     float = 0.3   # from road graph (A1)
    grid_failure_rate:   float = 0.1   # from MSEDCL reports (simulated)
    economic_constraint: float = 0.3   # from B2 econ proxy
    population:          float = 5000.0

    def to_dict(self) -> dict:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}


def load_baseline_features(grid_path: str = "data/nagpur_h3_res9.geojson") -> dict:
    if not os.path.exists(grid_path):
        print(f"Grid not found ({grid_path}) — baseline empty")
        return {}

    with open(grid_path) as f:
        grid = json.load(f)
    cells = [feat["properties"]["cell"] for feat in grid["features"]]

    pop  = _load_json("data/population_per_cell.json")
    econ = _load_json("data/econ_proxy_per_cell.json")
    hosp_raw = _load_json("data/hospital_travel_times.json")

    # Normalise hospital travel time → [0, 1]
    max_t = max(hosp_raw.values(), default=1.0)
    hosp = {k: min(v / max_t, 1.0) for k, v in hosp_raw.items()}

    return {
        cell: BaselineFeatures(
            h3_cell=cell,
            hospital_isolation=hosp.get(cell, 0.5),
            economic_constraint=econ.get(cell, 0.3),
            population=pop.get(cell, 5000.0),
        )
        for cell in cells
    }


def _load_json(path: str) -> dict:
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}
