"""
UrbanPulse — Logistic Vulnerability Risk Model
================================================
Owner  : Kanak (A2) — Day 2

Formula (plan D6):
    z = bias + Σ(beta_k * x_k) + Σ(gamma_jk * x_j * x_k) + delta * baseline_score
    p = sigmoid(z)

Constraints: all beta and gamma >= 0 (non-negative coefficients).

Coefficients are hand-set seeds here.
Phase 6 (Day 4): FedAvg fits them on training scenario families A–C.
"""

import math
from dataclasses import dataclass, field


# ── Hand-set seed coefficients (plan D6) ──────────────────────────────────────
# These are starting points. Sensitivity: perturb ±25% × 1000 draws on Day 4.

DEFAULT_BETA: dict[str, float] = {
    "hospital_isolation": 0.50,   # most impactful — isolation from care
    "power_stress":       0.60,   # grid failure drives cascades
    "water_loss":         0.40,   # pump failure compounds power outage
    "transit_loss":       0.30,   # cuts evacuation routes
    "road_stress":        0.35,   # road closure → isolation index
    "comms_loss":         0.20,   # warning dead zone
}

DEFAULT_GAMMA: dict[tuple[str, str], float] = {
    ("power_stress",  "water_loss"):         0.20,  # feeder → pump cascade
    ("road_stress",   "transit_loss"):       0.15,  # closure × route suspension
    ("comms_loss",    "hospital_isolation"): 0.10,  # dead zone + no care access
}

DEFAULT_DELTA = 0.30   # weight of static baseline features
DEFAULT_BIAS  = -1.20  # intercept — keeps most cells Low at baseline

# Risk label thresholds
HIGH_THRESHOLD   = 0.65
MEDIUM_THRESHOLD = 0.40


def sigmoid(z: float) -> float:
    # Clamp to prevent overflow on extreme z values
    z = max(-500.0, min(500.0, z))
    return 1.0 / (1.0 + math.exp(-z))


@dataclass
class RiskModel:
    """
    Logistic risk model. One global instance shared across all cells.
    Updated by FedAvg trainer (fed/fedavg.py) on Day 4.
    """
    beta:  dict[str, float]              = field(default_factory=lambda: dict(DEFAULT_BETA))
    gamma: dict[tuple[str, str], float]  = field(default_factory=lambda: dict(DEFAULT_GAMMA))
    delta: float                          = DEFAULT_DELTA
    bias:  float                          = DEFAULT_BIAS

    # Domain name → model input name mapping
    _DOMAIN_TO_INPUT: dict[str, str] = field(default_factory=lambda: {
        "health":   "hospital_isolation",
        "transit":  "transit_loss",
        "power":    "power_stress",
        "water":    "water_loss",
        "comms":    "comms_loss",
        "road":     "road_stress",
    }, repr=False)

    def _build_inputs(
        self,
        domain_stress: dict[str, float],
        baseline: dict[str, float],
    ) -> dict[str, float]:
        """Combine live domain stress with baseline features into model inputs."""
        x: dict[str, float] = {}
        for domain, input_name in self._DOMAIN_TO_INPUT.items():
            live = domain_stress.get(domain, 0.0)
            # Baseline contributes a fraction; live stress is the main signal
            base_key = {
                "hospital_isolation": "hospital_isolation",
                "transit_loss":       "transit_deficit",
            }.get(input_name)
            base = baseline.get(base_key, 0.0) * 0.3 if base_key else 0.0
            x[input_name] = max(0.0, min(1.0, live + base))
        return x

    def score(
        self,
        domain_stress: dict[str, float],
        baseline: dict[str, float],
    ) -> tuple[float, str]:
        """
        Compute risk score for one cell.

        Args:
            domain_stress : {domain: stress_0_to_1}  e.g. {"power": 0.8}
            baseline      : {feature: value_0_to_1}  from BaselineFeatures.to_dict()

        Returns:
            (p, label) where p in [0,1] and label in {"low","medium","high"}
        """
        x = self._build_inputs(domain_stress, baseline)

        z = self.bias

        # Linear terms
        for name, val in x.items():
            z += self.beta.get(name, 0.0) * val

        # Interaction terms
        for (j, k), g in self.gamma.items():
            z += g * x.get(j, 0.0) * x.get(k, 0.0)

        # Baseline term: grid failure rate + economic constraint
        baseline_score = (
            baseline.get("grid_failure_rate", 0.0)
            + baseline.get("economic_constraint", 0.0)
        ) / 2.0
        z += self.delta * baseline_score

        p = sigmoid(z)
        label = "high" if p >= HIGH_THRESHOLD else "medium" if p >= MEDIUM_THRESHOLD else "low"
        return round(p, 4), label

    def bootstrap_interval(
        self,
        domain_stress: dict[str, float],
        baseline: dict[str, float],
        n: int = 200,
        perturb: float = 0.25,
    ) -> tuple[float, float]:
        """
        Approximate 90% confidence interval by perturbing coefficients ±25%.
        Used for the risk interval shown in the UI (plan section 5).
        Fast: n=200 draws, report 5th/95th percentile.
        Phase 7: replace with proper bootstrap on scenario seeds.
        """
        import random
        orig_beta  = dict(self.beta)
        orig_gamma = dict(self.gamma)
        scores = []
        for _ in range(n):
            self.beta  = {k: max(0.0, v * (1 + random.uniform(-perturb, perturb)))
                          for k, v in orig_beta.items()}
            self.gamma = {k: max(0.0, v * (1 + random.uniform(-perturb, perturb)))
                          for k, v in orig_gamma.items()}
            p, _ = self.score(domain_stress, baseline)
            scores.append(p)
        self.beta  = orig_beta
        self.gamma = orig_gamma
        scores.sort()
        return round(scores[int(0.05 * n)], 3), round(scores[int(0.95 * n)], 3)

    def driver_contributions(
        self,
        domain_stress: dict[str, float],
        baseline: dict[str, float],
    ) -> dict[str, float]:
        """
        Exact counterfactual driver contributions (plan D7).
        For each driver: set it to zero, re-score, report the risk drop.

        Returns:
            {driver_name: risk_drop}  sorted by magnitude descending.
            Only drivers with drop > 0.01 are returned.
        """
        base_p, _ = self.score(domain_stress, baseline)
        contributions: dict[str, float] = {}

        # Per-domain drivers
        domain_map = {v: k for k, v in self._DOMAIN_TO_INPUT.items()}
        for input_name in self.beta:
            domain = domain_map.get(input_name)
            if not domain:
                continue
            modified = dict(domain_stress)
            modified[domain] = 0.0
            cf_p, _ = self.score(modified, baseline)
            drop = round(base_p - cf_p, 4)
            if drop > 0.01:
                contributions[input_name] = drop

        # Baseline driver (grid history + economic constraint)
        cf_p, _ = self.score(domain_stress, {})
        drop = round(base_p - cf_p, 4)
        if drop > 0.01:
            contributions["baseline"] = drop

        return dict(sorted(contributions.items(), key=lambda kv: kv[1], reverse=True))


# ── Global model instance (updated by FedAvg trainer on Day 4) ────────────────
MODEL = RiskModel()
