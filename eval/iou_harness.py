"""
UrbanPulse — IoU Evaluation Harness
=====================================
Owner  : Kanak (A2) — Day 3

Reads ground-truth YAML files (eval/scenarios/holdout/ — scenario owner only)
and compares against engine predictions to compute IoU and other metrics.

The engine NEVER reads ground-truth files. Only this harness does.

Metrics:
    iou              : Intersection over Union on H3 cell sets (primary)
    precision        : TP / (TP + FP)
    recall           : TP / (TP + FN)
    zone_hit_rate    : 1 if IoU >= 0.5, else 0
    detection_latency: seconds from first causal event to first High prediction
    calibration      : Brier score + reliability curve (Phase 7)

Usage:
    python eval/iou_harness.py --scenario eval/scenarios/SCN-A-001.yaml
    python eval/iou_harness.py --all         # runs all non-holdout scenarios
    python eval/iou_harness.py --holdout     # runs holdout (scenario owner only)
"""

from __future__ import annotations

import json
import time
import argparse
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

SCENARIOS_DIR = Path("eval/scenarios")
HOLDOUT_DIR   = SCENARIOS_DIR / "holdout"
RESULTS_DIR   = Path("eval/results")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

HIGH_THRESHOLD = 0.65   # must match risk_model.py


# ── IoU computation ───────────────────────────────────────────────────────────

def compute_iou(predicted: set[str], ground_truth: set[str]) -> float:
    """Intersection over Union on H3 cell ID sets."""
    if not predicted and not ground_truth:
        return 1.0   # both empty = perfect match
    if not predicted or not ground_truth:
        return 0.0
    intersection = len(predicted & ground_truth)
    union        = len(predicted | ground_truth)
    return round(intersection / union, 4)


def compute_precision_recall(
    predicted: set[str], ground_truth: set[str]
) -> tuple[float, float]:
    if not predicted:
        return 0.0, 0.0
    tp = len(predicted & ground_truth)
    precision = tp / len(predicted) if predicted else 0.0
    recall    = tp / len(ground_truth) if ground_truth else 0.0
    return round(precision, 4), round(recall, 4)


# ── Scenario result ────────────────────────────────────────────────────────────

@dataclass
class ScenarioResult:
    scenario_id:        str
    family:             str
    iou:                float
    precision:          float
    recall:             float
    zone_hit_rate:      int           # 1 if IoU >= 0.5
    detection_latency:  Optional[float]  # seconds; None if never detected
    predicted_cells:    set[str]      = field(default_factory=set, repr=False)
    ground_truth_cells: set[str]      = field(default_factory=set, repr=False)
    notes:              str           = ""

    def to_dict(self) -> dict:
        return {
            "scenario_id":       self.scenario_id,
            "family":            self.family,
            "iou":               self.iou,
            "precision":         self.precision,
            "recall":            self.recall,
            "zone_hit_rate":     self.zone_hit_rate,
            "detection_latency": self.detection_latency,
            "predicted_count":   len(self.predicted_cells),
            "truth_count":       len(self.ground_truth_cells),
            "notes":             self.notes,
        }


# ── Scenario runner ────────────────────────────────────────────────────────────

def run_scenario(scenario_path: Path, verbose: bool = False) -> ScenarioResult:
    """
    Run one scenario through the engine and measure IoU.
    
    1. Load scenario YAML
    2. Reset engine state (fresh for each scenario)
    3. Inject events via ENGINE.process_event()
    4. Compare High-risk cells with ground truth
    """
    try:
        import yaml
    except ImportError:
        raise ImportError("pip install pyyaml")

    with open(scenario_path) as f:
        scenario = yaml.safe_load(f)

    scenario_id = scenario.get("scenario_id", scenario_path.stem)
    family      = scenario.get("family", "?")
    gt_cells    = set(scenario.get("ground_truth", {}).get("polygon_h3_cells", []))

    if verbose:
        print(f"\n[scenario] {scenario_id} (family {family})")
        print(f"  Ground truth: {len(gt_cells)} cells")

    # Import engine (fresh state per scenario by resetting cell registry)
    from engine.engine import ENGINE
    from engine.cell_state import _registry
    _registry.clear()

    # Make sure baseline is loaded
    if not ENGINE.baseline:
        ENGINE.load_baseline()

    from contracts.event_schema import CanonicalEvent
    from pydantic import ValidationError

    events    = scenario.get("events", [])
    decoys    = scenario.get("decoys", [])
    all_events = events + decoys

    first_event_time = None
    first_detection_time = None

    for ev_def in all_events:
        try:
            ts = datetime.now(timezone.utc)
            event = CanonicalEvent(
                domain             = ev_def["domain"],
                event_type         = ev_def["event_type"],
                entity_id          = ev_def["entity_id"],
                h3_cell            = ev_def["h3_cell"],
                severity           = ev_def["severity"],
                source_type        = ev_def.get("source_type", "official"),
                source_reliability = float({"official":0.9,"sensor":0.7,"crowdsourced":0.5,"anonymous":0.3}.get(ev_def.get("source_type","official"), 0.5)),
                event_timestamp    = ts,
                ingestion_timestamp= ts,
                parse_confidence   = 1.0,
            )
            result = ENGINE.process_event(event)

            if first_event_time is None:
                first_event_time = time.monotonic()

            # Check if we've detected a High-risk cell
            if result.label == "high" and first_detection_time is None:
                first_detection_time = time.monotonic()

        except (ValidationError, Exception) as e:
            if verbose:
                print(f"  [skip] event {ev_def.get('entity_id','?')}: {e}")

    # Collect predicted High cells
    from engine.cell_state import all_cells
    predicted = {
        cell_id
        for cell_id, cell in all_cells().items()
        if not cell.is_unknown and cell.risk >= HIGH_THRESHOLD
    }

    iou = compute_iou(predicted, gt_cells)
    precision, recall = compute_precision_recall(predicted, gt_cells)
    latency = (
        round(first_detection_time - first_event_time, 2)
        if first_detection_time and first_event_time else None
    )

    if verbose:
        print(f"  Predicted High: {len(predicted)} cells")
        print(f"  IoU: {iou}  Precision: {precision}  Recall: {recall}")
        print(f"  Detection latency: {latency}s")

    return ScenarioResult(
        scenario_id=scenario_id,
        family=family,
        iou=iou,
        precision=precision,
        recall=recall,
        zone_hit_rate=1 if iou >= 0.5 else 0,
        detection_latency=latency,
        predicted_cells=predicted,
        ground_truth_cells=gt_cells,
    )


# ── Batch runner ──────────────────────────────────────────────────────────────

def run_all(include_holdout: bool = False, verbose: bool = False) -> list[ScenarioResult]:
    dirs = [SCENARIOS_DIR]
    if include_holdout:
        dirs.append(HOLDOUT_DIR)

    scenario_files = []
    for d in dirs:
        scenario_files.extend(sorted(d.glob("SCN-*.yaml")))

    if not scenario_files:
        print("[warn] No scenario files found. Create YAML files in eval/scenarios/")
        return []

    results = []
    for path in scenario_files:
        result = run_scenario(path, verbose=verbose)
        results.append(result)
        print(f"  {result.scenario_id:<15} IoU={result.iou:.3f}  "
              f"P={result.precision:.3f}  R={result.recall:.3f}  "
              f"hit={'✓' if result.zone_hit_rate else '✗'}  "
              f"latency={result.detection_latency}s")

    return results


def print_summary(results: list[ScenarioResult]) -> None:
    if not results:
        return
    ious = [r.iou for r in results]
    hits = [r.zone_hit_rate for r in results]
    print(f"\n{'='*55}")
    print(f"  Scenarios run : {len(results)}")
    print(f"  Mean IoU      : {sum(ious)/len(ious):.3f}")
    print(f"  Min / Max IoU : {min(ious):.3f} / {max(ious):.3f}")
    print(f"  Zone hit rate : {sum(hits)}/{len(hits)} ({100*sum(hits)//len(hits)}%)")
    print(f"{'='*55}")


def save_results(results: list[ScenarioResult], tag: str = "") -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out = RESULTS_DIR / f"iou_results_{tag}_{ts}.json"
    with open(out, "w") as f:
        json.dump([r.to_dict() for r in results], f, indent=2)
    print(f"[saved] {out}")
    return out


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UrbanPulse IoU evaluation harness")
    parser.add_argument("--scenario", help="Path to single scenario YAML file")
    parser.add_argument("--all",      action="store_true", help="Run all non-holdout scenarios")
    parser.add_argument("--holdout",  action="store_true", help="Run holdout scenarios (scenario owner only)")
    parser.add_argument("--verbose",  action="store_true")
    parser.add_argument("--save",     action="store_true", help="Save results to JSON")
    args = parser.parse_args()

    if args.scenario:
        result = run_scenario(Path(args.scenario), verbose=True)
        print(result.to_dict())
    elif args.all or args.holdout:
        results = run_all(include_holdout=args.holdout, verbose=args.verbose)
        print_summary(results)
        if args.save and results:
            save_results(results, tag="holdout" if args.holdout else "all")
    else:
        parser.print_help()
