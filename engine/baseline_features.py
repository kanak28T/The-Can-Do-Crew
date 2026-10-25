"""
UrbanPulse — Baseline Feature Vector per H3 Cell
==================================================
Owner  : Kanak (A2) — Day 2
Loaded once at startup. Updated by seed script when new data arrives.

Merges four data files (all in data/):
  population_per_cell.json      — from worldpop_to_cells.py (A2)
  econ_proxy_per_cell.json      — from Sanvi (B2) Day 2
  hospital_travel_times.json    — from Priyanshu (A1) Day 2 Dijkstra
  nagpur_h3_res9.geojson        — H3 grid from Sanvi (B2) Day 1

Missing files → safe defaults used (will be filled progressively across days).
"""

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Union

DATA_DIR = Path(__file__).parent.parent / "data"


@dataclass
class BaselineFeatures:
    h3_cell:            str
    hospital_isolation: float = 0.5   # 0=good access, 1=isolated; from Dijkstra
    transit_deficit:    float = 0.3   # 0=good transit, 1=no transit
    grid_failure_rate:  float = 0.1   # historical outage probability (MSEDCL)
    economic_constraint: float = 0.3  # 0=wealthy, 1=constrained; from VIIRS+slum
    population:         float = 5000.0  # WorldPop count for dispatch weighting

    def to_dict(self) -> dict:
        return {
            "h3_cell":             self.h3_cell,
            "hospital_isolation":  self.hospital_isolation,
            "transit_deficit":     self.transit_deficit,
            "grid_failure_rate":   self.grid_failure_rate,
            "economic_constraint": self.economic_constraint,
            "population":          self.population,
        }


def _load_json(path: Union[str, Path]) -> dict:
    p = Path(path)
    if p.exists():
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return {}


def load_baseline_features(
    grid_path: Union[str, Path] = DATA_DIR / "nagpur_h3_res9.geojson",
) -> dict[str, BaselineFeatures]:
    """
    Load baseline features for every cell in the H3 grid.
    Returns {h3_cell: BaselineFeatures}.
    """
    p = Path(grid_path)
    if not p.exists():
        print(f"[warn] {p} not found — no baseline features loaded.")
        return {}

    with open(p, encoding="utf-8") as f:
        grid = json.load(f)
    cells = [feat["properties"]["cell"] for feat in grid["features"]]

    # Load each data file — missing = use defaults
    pop  = _load_json(DATA_DIR / "population_per_cell.json")
    econ = _load_json(DATA_DIR / "econ_proxy_per_cell.json")

    # Hospital travel times: normalise to [0, 1] (max travel time → 1.0)
    raw_hosp = _load_json(DATA_DIR / "hospital_travel_times.json")
    if raw_hosp:
        max_t = max(raw_hosp.values()) or 1.0
        hosp = {k: min(v / max_t, 1.0) for k, v in raw_hosp.items()}
    else:
        hosp = {}

    baseline: dict[str, BaselineFeatures] = {}
    for cell in cells:
        baseline[cell] = BaselineFeatures(
            h3_cell=cell,
            hospital_isolation=hosp.get(cell, 0.5),
            economic_constraint=econ.get(cell, 0.3),
            population=pop.get(cell, 5000.0),
        )

    print(f"[baseline] Loaded features for {len(baseline)} cells.")
    return baseline
