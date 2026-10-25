"""
Logistic vulnerability risk model.
z = b0 + Σ(β_k · x_k) + Σ(γ_jk · x_j · x_k) + δ · baseline
p = sigmoid(z)

All β and γ ≥ 0 (D6 — locked).
Phase 1: hand-set coefficients. Phase 6: fitted by FedAvg.
"""

import math
from dataclasses import dataclass, field
from typing import Dict, Tuple

# ── Hand-set seed coefficients ─────────────────────────────────────────────────
DEFAULT_BETA: Dict[str, float] = {
    "hospital_isolation": 0.50,
    "transit_loss":       0.30,
    "power_stress":       0.60,
    "water_loss":         0.40,
    "comms_loss":         0.20,
    "road_stress":        0.35,
}

DEFAULT_GAMMA: Dict[Tuple[str, str], float] = {
    ("power_stress",  "water_loss"):         0.20,   # feeder → pump cascade
    ("road_stress",   "transit_loss"):       0.15,   # closure × transit
    ("comms_loss",    "hospital_isolation"): 0.10,   # dead zone × isolation
}

DEFAULT_DELTA = 0.30    # baseline feature weight
DEFAULT_BIAS  = -1.20   # intercept (most cells start Low)

# Risk label thresholds
HIGH_THRESHOLD   = 0.65
MEDIUM_THRESHOLD = 0.40


def sigmoid(z: float) -> float:
    # Clamp to avoid overflow
    z = max(-500.0, min(500.0, z))
    return 1.0 / (1.0 + math.exp(-z))


@dataclass
class RiskModel:
    beta:  Dict[str, float]             = field(default_factory=lambda: dict(DEFAULT_BETA))
    gamma: Dict[Tuple[str, str], float] = field(default_factory=lambda: dict(DEFAULT_GAMMA))
    delta: float = DEFAULT_DELTA
    bias:  float = DEFAULT_BIAS

    def _build_x(self, domain_stress: Dict[str, float], baseline: Dict[str, float]) -> Dict[str, float]:
        """Map domain stresses + baseline to model input features."""
        x = {
            "hospital_isolation": min(1.0, domain_stress.get("health", 0.0)   + baseline.get("hospital_isolation", 0.0) * 0.5),
            "transit_loss":       min(1.0, domain_stress.get("transit", 0.0)  + baseline.get("transit_deficit",    0.0) * 0.3),
            "power_stress":       domain_stress.get("power",   0.0),
            "water_loss":         domain_stress.get("water",   0.0),
            "comms_loss":         domain_stress.get("comms",   0.0),
            "road_stress":        domain_stress.get("road",    0.0),
        }
        return {k: max(0.0, min(1.0, v)) for k, v in x.items()}

    def score(
        self,
        domain_stress: Dict[str, float],
        baseline: Dict[str, float],
    ) -> Tuple[float, str]:
        """
        Returns (p, label).
        p in [0,1]; label in {low, medium, high}
        """
        x = self._build_x(domain_stress, baseline)

        z = self.bias
        for k, v in x.items():
            z += self.beta.get(k, 0.0) * v

        for (j, k), g in self.gamma.items():
            z += g * x.get(j, 0.0) * x.get(k, 0.0)

        baseline_score = (
            baseline.get("grid_failure_rate", 0.0) +
            baseline.get("economic_constraint", 0.0)
        ) / 2.0
        z += self.delta * baseline_score

        p = sigmoid(z)
        label = "high" if p >= HIGH_THRESHOLD else "medium" if p >= MEDIUM_THRESHOLD else "low"
        return round(p, 4), label

    def bootstrap_interval(
        self,
        domain_stress: Dict[str, float],
        baseline: Dict[str, float],
        n: int = 200,
        perturb: float = 0.25,
    ) -> Tuple[float, float]:
        """
        Approximate 90% CI by perturbing coefficients ±25%.
        Fast version: perturb once, report (min, max) across n draws.
        """
        import random
        scores = []
        orig_beta = dict(self.beta)
        orig_gamma = dict(self.gamma)
        for _ in range(n):
            self.beta  = {k: max(0.0, v * (1 + random.uniform(-perturb, perturb))) for k, v in orig_beta.items()}
            self.gamma = {k: max(0.0, v * (1 + random.uniform(-perturb, perturb))) for k, v in orig_gamma.items()}
            p, _ = self.score(domain_stress, baseline)
            scores.append(p)
        self.beta  = orig_beta
        self.gamma = orig_gamma
        scores.sort()
        lo = scores[int(0.05 * n)]
        hi = scores[int(0.95 * n)]
        return round(lo, 3), round(hi, 3)

    def driver_contributions(
        self,
        domain_stress: Dict[str, float],
        baseline: Dict[str, float],
    ) -> Dict[str, float]:
        """
        Counterfactual: set each driver to 0, re-score, report risk drop.
        Returns {driver: -drop} sorted by magnitude.
        """
        base_p, _ = self.score(domain_stress, baseline)
        domain_map = {
            "hospital_isolation": "health",
            "transit_loss":  "transit",
            "power_stress":  "power",
            "water_loss":    "water",
            "comms_loss":    "comms",
            "road_stress":   "road",
        }
        contributions = {}
        for driver in list(self.beta.keys()) + ["baseline"]:
            ms = dict(domain_stress)
            mb = dict(baseline)
            if driver == "baseline":
                mb = {k: 0.0 for k in mb}
            else:
                d = domain_map.get(driver)
                if d:
                    ms[d] = 0.0
            cf_p, _ = self.score(ms, mb)
            drop = round(base_p - cf_p, 4)
            if drop > 0.005:
                contributions[driver] = round(-drop, 4)
        return dict(sorted(contributions.items(), key=lambda x: x[1]))


# Global singleton — shared across all requests; updated by FedAvg in Phase 6
MODEL = RiskModel()
