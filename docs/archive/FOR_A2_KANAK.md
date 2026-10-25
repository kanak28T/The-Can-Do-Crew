# A2 (Kanak) — Your Phase 1 Tasks

Your schema work is excellent. Phase 0 is done on both branches.

---

## What you've already done ✅
- `contracts/event_schema.py` (full enums, PII validator, dedup_signature)
- `contracts/scenario_format.yaml`
- `contracts/ground_truth_format.yaml`
- `engine/privacy.py` (k-merge stub)
- `data/download_scripts/download_worldpop.py`

---

## Merge status

Your branch `kanak` has work that A1 needs. Priyanshu will merge your
`contracts/event_schema.py` into `priyanshu` because yours is more complete.

For now: **continue on your `kanak` branch** and create these Phase 1 files.

---

## A2 Phase 1 Tasks (Day 2)

### A2.3 — WorldPop population per cell (45 min)

You already have `download_worldpop.py`. After it downloads, run this:

File: `data/download_scripts/worldpop_to_cells.py`

```python
"""
Aggregate WorldPop 100m raster to H3 res-9 cells.
Output: data/population_per_cell.json  {h3_cell: population_count}
"""
import json, os

def aggregate_worldpop_to_h3(raster_path: str, h3_cells: list[str]) -> dict[str, float]:
    """
    For each H3 cell, sum WorldPop pixels that fall inside it.
    Returns {cell_id: population}.
    """
    try:
        import rasterio
        import numpy as np
        import h3
        from rasterio.mask import mask
        from shapely.geometry import shape

        result = {}
        with rasterio.open(raster_path) as src:
            for cell in h3_cells:
                boundary = h3.cell_to_boundary(cell)
                polygon = {
                    "type": "Polygon",
                    "coordinates": [[[lng, lat] for lat, lng in boundary] + [[boundary[0][1], boundary[0][0]]]]
                }
                try:
                    out_image, _ = mask(src, [polygon], crop=True, nodata=0)
                    pop = float(np.nansum(out_image[out_image > 0]))
                    result[cell] = round(pop, 2)
                except Exception:
                    result[cell] = 0.0
        return result
    except ImportError:
        print("rasterio not installed — returning mock population data")
        return {cell: 5000.0 for cell in h3_cells}

if __name__ == "__main__":
    # Load H3 grid
    with open("data/nagpur_h3_res9.geojson") as f:
        grid = json.load(f)
    cells = [feat["properties"]["cell"] for feat in grid["features"]]

    raster = "data/worldpop_nagpur.tif"
    if not os.path.exists(raster):
        print("WorldPop raster not downloaded yet — using mock data")
        pop_data = {cell: 5000.0 for cell in cells}
    else:
        pop_data = aggregate_worldpop_to_h3(raster, cells)

    with open("data/population_per_cell.json", "w") as f:
        json.dump(pop_data, f, indent=2)

    print(f"✅ Saved data/population_per_cell.json ({len(pop_data)} cells)")
```

### A2.4 — Baseline feature vector per cell (45 min)

File: `engine/baseline_features.py`

```python
"""
Baseline (static) feature vector per H3 res-9 cell.
Loaded once at startup; updated daily via seed script.
"""
import json, os
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class BaselineFeatures:
    h3_cell: str
    hospital_isolation: float = 0.5   # filled by Dijkstra (Phase 1 A1 task)
    transit_deficit: float = 0.3      # placeholder; filled after road graph
    grid_failure_rate: float = 0.1    # from MSEDCL reports (simulated)
    economic_constraint: float = 0.3  # filled by B2 econ proxy
    population: float = 5000.0        # from WorldPop

    def to_dict(self) -> dict:
        return {
            "h3_cell": self.h3_cell,
            "hospital_isolation": self.hospital_isolation,
            "transit_deficit": self.transit_deficit,
            "grid_failure_rate": self.grid_failure_rate,
            "economic_constraint": self.economic_constraint,
            "population": self.population,
        }


def load_baseline_features(grid_path: str = "data/nagpur_h3_res9.geojson") -> dict[str, BaselineFeatures]:
    """
    Load baseline features for all cells.
    Merges: population_per_cell.json + econ_proxy_per_cell.json + hospital_travel_times.json
    Missing files → use defaults (will be filled progressively).
    """
    # Load H3 grid
    with open(grid_path) as f:
        grid = json.load(f)
    cells = [feat["properties"]["cell"] for feat in grid["features"]]

    # Population
    pop = {}
    if os.path.exists("data/population_per_cell.json"):
        with open("data/population_per_cell.json") as f:
            pop = json.load(f)

    # Economic constraint proxy (B2 produces this)
    econ = {}
    if os.path.exists("data/econ_proxy_per_cell.json"):
        with open("data/econ_proxy_per_cell.json") as f:
            econ = json.load(f)

    # Hospital travel times (A1 produces this via Dijkstra)
    hosp = {}
    if os.path.exists("data/hospital_travel_times.json"):
        with open("data/hospital_travel_times.json") as f:
            raw = json.load(f)
            # Normalise: max travel time → 1.0
            max_t = max(raw.values()) if raw else 1
            hosp = {k: min(v / max_t, 1.0) for k, v in raw.items()}

    baseline = {}
    for cell in cells:
        baseline[cell] = BaselineFeatures(
            h3_cell=cell,
            hospital_isolation=hosp.get(cell, 0.5),
            economic_constraint=econ.get(cell, 0.3),
            population=pop.get(cell, 5000.0),
        )
    return baseline
```

### A2.6 — Logistic risk scoring model (60 min)

File: `engine/risk_model.py`

```python
"""
Logistic vulnerability risk model.
z = b0 + sum(beta_k * x_k) + sum(gamma_jk * x_j * x_k) + delta * baseline
p = sigmoid(z)

All beta and gamma >= 0 (non-negative coefficients, plan D6).
"""
import math
from dataclasses import dataclass, field
from typing import Dict, Tuple

# Hand-set seed coefficients (fit via FedAvg in Phase 6)
DEFAULT_BETA = {
    "hospital_isolation": 0.50,
    "transit_loss":       0.30,
    "power_stress":       0.60,
    "water_loss":         0.40,
    "comms_loss":         0.20,
    "road_stress":        0.35,
}

DEFAULT_GAMMA = {
    ("power_stress",  "water_loss"):      0.20,  # cascade: feeder → pump
    ("road_stress",   "transit_loss"):    0.15,  # closure × transit loss
    ("comms_loss",    "hospital_isolation"): 0.10,
}

DEFAULT_DELTA = 0.30   # weight of baseline features
DEFAULT_BIAS  = -1.20  # intercept (keeps most cells Low by default)

THRESHOLDS = {
    "low":     0.40,
    "medium":  0.65,
    "high":    1.01,  # >= 0.65
}


def sigmoid(z: float) -> float:
    return 1.0 / (1.0 + math.exp(-z))


@dataclass
class RiskModel:
    beta:  Dict[str, float]              = field(default_factory=lambda: dict(DEFAULT_BETA))
    gamma: Dict[Tuple[str,str], float]   = field(default_factory=lambda: dict(DEFAULT_GAMMA))
    delta: float                          = DEFAULT_DELTA
    bias:  float                          = DEFAULT_BIAS

    def score(
        self,
        domain_stress: Dict[str, float],
        baseline: Dict[str, float],
    ) -> Tuple[float, str]:
        """
        Compute risk score for one cell.

        Args:
            domain_stress: {domain_name: stress_0_to_1}
            baseline: {feature_name: value_0_to_1}

        Returns:
            (p, label) where p in [0,1] and label in {low, medium, high}
        """
        x = {
            "hospital_isolation": domain_stress.get("health", 0.0) + baseline.get("hospital_isolation", 0.0) * 0.5,
            "transit_loss":       domain_stress.get("transit", 0.0) + baseline.get("transit_deficit", 0.0) * 0.3,
            "power_stress":       domain_stress.get("power", 0.0),
            "water_loss":         domain_stress.get("water", 0.0),
            "comms_loss":         domain_stress.get("comms", 0.0),
            "road_stress":        domain_stress.get("road", 0.0),
        }
        # Clamp to [0, 1]
        x = {k: max(0.0, min(1.0, v)) for k, v in x.items()}

        # Linear terms
        z = self.bias
        for k, v in x.items():
            z += self.beta.get(k, 0.0) * v

        # Interaction terms
        for (j, k), gamma_jk in self.gamma.items():
            z += gamma_jk * x.get(j, 0.0) * x.get(k, 0.0)

        # Baseline term
        baseline_score = (
            baseline.get("grid_failure_rate", 0.0) +
            baseline.get("economic_constraint", 0.0)
        ) / 2.0
        z += self.delta * baseline_score

        p = sigmoid(z)
        label = "high" if p >= 0.65 else "medium" if p >= 0.40 else "low"
        return round(p, 4), label

    def driver_contributions(
        self,
        domain_stress: Dict[str, float],
        baseline: Dict[str, float],
    ) -> Dict[str, float]:
        """
        Counterfactual driver contributions.
        For each driver: set it to 0, re-score, report the risk drop.
        """
        base_p, _ = self.score(domain_stress, baseline)
        contributions = {}

        for driver in list(self.beta.keys()) + ["baseline"]:
            modified_stress = dict(domain_stress)
            modified_baseline = dict(baseline)

            if driver == "baseline":
                modified_baseline = {k: 0.0 for k in modified_baseline}
            else:
                # Map driver name back to domain key
                domain_map = {
                    "hospital_isolation": "health",
                    "transit_loss": "transit",
                    "power_stress": "power",
                    "water_loss": "water",
                    "comms_loss": "comms",
                    "road_stress": "road",
                }
                d = domain_map.get(driver)
                if d:
                    modified_stress[d] = 0.0

            counterfactual_p, _ = self.score(modified_stress, modified_baseline)
            drop = round(base_p - counterfactual_p, 4)
            if drop > 0.01:  # only report meaningful contributions
                contributions[driver] = -drop  # negative = risk reduction

        return dict(sorted(contributions.items(), key=lambda x: x[1]))


# Global model instance (shared; updated by FedAvg in Phase 6)
MODEL = RiskModel()
```

### A2.8 — Unknown (grey) state (20 min)

Already handled in `engine/cell_state.py` which A1 is building.
You own the confidence formula. File: `engine/confidence.py`

```python
"""
Confidence formula: coverage × freshness × source_agreement
"""
from datetime import datetime, timezone
from typing import List

def compute_confidence(
    source_types: List[str],
    last_updated: datetime,
    source_stresses: List[float],
    stale_threshold_hours: float = 12.0,
) -> float:
    """
    coverage   = fraction of expected domains reporting
    freshness  = 1 - (hours_since_update / stale_threshold)
    agreement  = 1 - std(stresses) / 0.5  (normalised disagreement)
    """
    # Coverage: at least 1 source = 0.5; 3+ = 1.0
    coverage = min(1.0, len(source_types) / 3.0)

    # Freshness
    hours_old = (datetime.now(timezone.utc) - last_updated).total_seconds() / 3600
    freshness = max(0.0, 1.0 - hours_old / stale_threshold_hours)

    # Agreement (lower std = higher agreement)
    if len(source_stresses) > 1:
        mean = sum(source_stresses) / len(source_stresses)
        std = (sum((x - mean)**2 for x in source_stresses) / len(source_stresses)) ** 0.5
        agreement = max(0.0, 1.0 - std / 0.5)
    else:
        agreement = 1.0

    confidence = coverage * freshness * agreement
    return round(confidence, 4)
```

---

## Your Phase 1 exit criteria

- [ ] `data/population_per_cell.json` committed
- [ ] `engine/baseline_features.py` committed
- [ ] `engine/risk_model.py` committed
- [ ] `engine/confidence.py` committed
- [ ] Test: `python -c "from engine.risk_model import MODEL; print(MODEL.score({'power': 1.0}, {}))"`
  - Expected output: something like `(0.45, 'medium')` or higher

Push to `kanak` branch after each file.
