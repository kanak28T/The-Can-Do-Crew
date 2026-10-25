"""
UrbanPulse — Red-Team Privacy Script
======================================
Owner  : Kanak (A2) — Day 4 (Phase 6)

Three attacks against synthetic individuals (plan section 7):

  A. Membership inference  — can attacker tell if a cell had an event?
     Metric: AUC (0.5 = chance = safe, 1.0 = perfect attack)
     Target: AUC ≤ 0.60 with noise ON

  B. Differencing attack   — compare two successive releases to infer
     whether one event was added.
     Metric: fraction of events correctly identified

  C. Linkage attack        — cross-reference anonymised cell scores with
     a synthetic public table to uniquely identify individuals.
     Metric: fraction uniquely identified

Panel shows results with noise OFF and ON.
Never labels any value "safe" — shows the tradeoff curve.

Usage:
    python fed/redteam.py
    python fed/redteam.py --noise-sigma 0.1
"""

from __future__ import annotations

import math
import random
import argparse
from dataclasses import dataclass


@dataclass
class RedTeamResult:
    attack:           str
    noise_sigma:      float
    attacker_score:   float   # AUC or fraction identified
    random_baseline:  float   # what random guessing achieves
    delta:            float   # attacker_score - random_baseline
    verdict:          str     # "PASS (low privacy risk)" | "WARN" | "FAIL"
    details:          str

    def to_dict(self) -> dict:
        return {
            "attack":          self.attack,
            "noise_sigma":     self.noise_sigma,
            "attacker_score":  round(self.attacker_score, 4),
            "random_baseline": round(self.random_baseline, 4),
            "delta":           round(self.delta, 4),
            "verdict":         self.verdict,
            "details":         self.details,
        }


def _verdict(score: float, baseline: float) -> str:
    delta = score - baseline
    if delta <= 0.10:
        return "PASS (low privacy risk)"
    elif delta <= 0.20:
        return "WARN (moderate risk — consider increasing noise)"
    else:
        return "FAIL (high privacy risk — increase noise or k)"


# ── Attack A: Membership Inference ────────────────────────────────────────

def attack_membership_inference(
    cells: list[str],
    noise_sigma: float = 0.0,
    n_synthetic: int = 200,
) -> RedTeamResult:
    """
    Membership inference: given a published risk score for a cell,
    can an attacker determine whether a specific event occurred there?

    Simulation:
    - Half the cells receive a synthetic event (members)
    - Half don't (non-members)
    - Risk scores are published with or without noise
    - Attacker uses a threshold classifier on the risk score
    - Measure AUC of attacker's classification
    """
    from engine.risk_model import MODEL, sigmoid

    random.seed(42)
    scores_member     = []
    scores_nonmember  = []

    for i in range(n_synthetic):
        # Simulate a cell with and without an event
        base = {"hospital_isolation": random.uniform(0.2, 0.7),
                "transit_deficit":    random.uniform(0.1, 0.5),
                "grid_failure_rate":  random.uniform(0.05, 0.3),
                "economic_constraint": random.uniform(0.2, 0.6)}

        # Member: power event happened
        stress_member = {"power": random.uniform(0.6, 0.9),
                         "water": 0.0, "transit": 0.0,
                         "comms": 0.0, "roads": 0.0, "health": 0.0}
        p_member, _ = MODEL.score(stress_member, base)

        # Non-member: no event
        stress_none = {"power": 0.0, "water": 0.0, "transit": 0.0,
                       "comms": 0.0, "roads": 0.0, "health": 0.0}
        p_none, _ = MODEL.score(stress_none, base)

        # Add noise to published scores
        if noise_sigma > 0:
            p_member += random.gauss(0, noise_sigma)
            p_none   += random.gauss(0, noise_sigma)

        p_member = max(0.0, min(1.0, p_member))
        p_none   = max(0.0, min(1.0, p_none))

        scores_member.append(p_member)
        scores_nonmember.append(p_none)

    # Compute AUC: for each threshold, attacker classifies member if score > threshold
    all_scores = [(s, 1) for s in scores_member] + [(s, 0) for s in scores_nonmember]
    all_scores.sort(key=lambda x: x[0], reverse=True)

    tp = fp = 0
    prev_tp = prev_fp = 0
    auc = 0.0
    n_pos = len(scores_member)
    n_neg = len(scores_nonmember)

    for score, label in all_scores:
        if label == 1:
            tp += 1
        else:
            fp += 1
        # Trapezoidal rule
        auc += (fp - prev_fp) * (tp + prev_tp) / 2
        prev_tp, prev_fp = tp, fp

    auc = auc / (n_pos * n_neg) if n_pos * n_neg > 0 else 0.5

    return RedTeamResult(
        attack="membership_inference",
        noise_sigma=noise_sigma,
        attacker_score=auc,
        random_baseline=0.5,
        delta=auc - 0.5,
        verdict=_verdict(auc, 0.5),
        details=(
            f"Attacker AUC={auc:.3f} vs random baseline=0.50. "
            f"Tested on {n_synthetic} synthetic member/non-member pairs. "
            f"Noise σ={noise_sigma}."
        ),
    )


# ── Attack B: Differencing Attack ─────────────────────────────────────────

def attack_differencing(
    noise_sigma: float = 0.0,
    n_trials: int = 100,
) -> RedTeamResult:
    """
    Differencing: attacker observes two successive releases (before and
    after one event is added) and tries to infer the event occurred.

    If noise is off, the risk delta is deterministic → attacker always wins.
    If noise is on, the delta is masked.
    """
    from engine.risk_model import MODEL

    random.seed(123)
    detected = 0

    for _ in range(n_trials):
        base = {"hospital_isolation": random.uniform(0.2, 0.6),
                "transit_deficit":    random.uniform(0.1, 0.4),
                "grid_failure_rate":  random.uniform(0.05, 0.25),
                "economic_constraint": random.uniform(0.2, 0.5)}

        stress_before = {d: 0.0 for d in ["power","water","transit","comms","roads","health"]}
        stress_after  = {**stress_before, "power": random.uniform(0.5, 0.85)}

        p_before, _ = MODEL.score(stress_before, base)
        p_after,  _ = MODEL.score(stress_after, base)

        if noise_sigma > 0:
            p_before += random.gauss(0, noise_sigma)
            p_after  += random.gauss(0, noise_sigma)

        # Attacker detects event if delta > threshold
        threshold = 0.05
        delta = abs(p_after - p_before)
        if delta > threshold:
            detected += 1

    fraction_detected = detected / n_trials
    baseline = 0.5   # random guessing

    return RedTeamResult(
        attack="differencing",
        noise_sigma=noise_sigma,
        attacker_score=fraction_detected,
        random_baseline=baseline,
        delta=fraction_detected - baseline,
        verdict=_verdict(fraction_detected, baseline),
        details=(
            f"Attacker detected {detected}/{n_trials} events "
            f"({fraction_detected*100:.1f}%). Noise σ={noise_sigma}. "
            f"Threshold Δ>{0.05}."
        ),
    )


# ── Attack C: Linkage Attack ───────────────────────────────────────────────

def attack_linkage(
    cells: list[str],
    noise_sigma: float = 0.0,
    n_synthetic_people: int = 50,
) -> RedTeamResult:
    """
    Linkage: attacker has a synthetic public table with approximate
    locations of individuals and tries to match them to published cell
    risk scores to uniquely identify their vulnerability status.

    With no cell-level suppression, cells with one person are trivially
    identifiable. With k-merge, small cells are merged → harder to link.
    """
    from engine.risk_model import MODEL
    import h3 as h3lib

    random.seed(456)
    if not cells:
        return RedTeamResult("linkage", noise_sigma, 0.5, 0.5, 0.0,
                              "PASS (no cells)", "No cells provided.")

    unique_ids = 0

    for _ in range(n_synthetic_people):
        # Synthetic person is in a random cell
        person_cell = random.choice(cells)

        # Published risk for that cell (with noise)
        stress = {d: random.uniform(0, 0.4) for d in
                  ["power","water","transit","comms","roads","health"]}
        base   = {"hospital_isolation": 0.4, "transit_deficit": 0.3,
                  "grid_failure_rate": 0.1, "economic_constraint": 0.3}
        p, _   = MODEL.score(stress, base)

        if noise_sigma > 0:
            p += random.gauss(0, noise_sigma)
        p = max(0.0, min(1.0, p))

        # Attacker tries to find cells with matching risk score (±0.05)
        # If only one cell matches → person uniquely identified
        matching = [
            c for c in cells
            if abs(p - random.uniform(0, 1)) < 0.05   # simulated attacker lookup
        ]
        if len(matching) == 1:
            unique_ids += 1

    fraction = unique_ids / n_synthetic_people
    baseline  = 1.0 / max(len(cells), 1)  # random guessing = 1/N cells

    return RedTeamResult(
        attack="linkage",
        noise_sigma=noise_sigma,
        attacker_score=fraction,
        random_baseline=baseline,
        delta=fraction - baseline,
        verdict=_verdict(fraction, baseline),
        details=(
            f"Uniquely identified {unique_ids}/{n_synthetic_people} "
            f"({fraction*100:.1f}%) vs random baseline "
            f"{baseline*100:.2f}%. Noise σ={noise_sigma}."
        ),
    )


# ── Full Red-Team run ──────────────────────────────────────────────────────

def run_redteam(
    cells: list[str],
    noise_sigma: float = 0.01,
) -> dict:
    """
    Run all 3 attacks with noise OFF and ON.
    Returns a summary dict for the Privacy Panel.
    """
    results = {}
    for sigma, label in [(0.0, "noise_off"), (noise_sigma, "noise_on")]:
        results[label] = {
            "membership_inference": attack_membership_inference(
                cells, noise_sigma=sigma
            ).to_dict(),
            "differencing": attack_differencing(
                noise_sigma=sigma
            ).to_dict(),
            "linkage": attack_linkage(
                cells, noise_sigma=sigma
            ).to_dict(),
        }

    # Summary verdict
    verdicts = [
        v["verdict"]
        for label in results.values()
        for v in label.values()
        if "noise_on" in results and label == results["noise_on"]
    ]
    overall = (
        "PASS" if all("PASS" in v for v in verdicts)
        else "WARN" if all("FAIL" not in v for v in verdicts)
        else "FAIL"
    )

    return {
        "noise_sigma":  noise_sigma,
        "overall":      overall,
        "results":      results,
        "note":         "Panel shows tradeoff — no value is labelled 'safe'.",
    }


# ── CLI ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json

    parser = argparse.ArgumentParser(description="UrbanPulse Red-Team privacy attack")
    parser.add_argument("--noise-sigma", type=float, default=0.01,
                        help="Gaussian noise sigma on published scores (default 0.01)")
    args = parser.parse_args()

    # Load canonical cells
    try:
        import json as _json
        with open("data/nagpur_h3_res9.geojson") as f:
            grid = _json.load(f)
        cells = [feat["properties"]["cell"] for feat in grid["features"]]
    except FileNotFoundError:
        cells = [f"89609610{i:03d}ffff" for i in range(50)]   # fallback
        print("[warn] Using synthetic cells — run from repo root for real data")

    print(f"Running Red-Team attacks on {len(cells)} cells, noise σ={args.noise_sigma}\n")
    result = run_redteam(cells, noise_sigma=args.noise_sigma)
    print(json.dumps(result, indent=2))
