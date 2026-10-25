"""
UrbanPulse — IoU Evaluation Harness
====================================
Owner : Priyanshu (A1) — Phase 2/3 / Phase 7

Evaluates system predictions against ground-truth isolation zones:
  - Intersection over Union (IoU): |A ∩ B| / |A ∪ B|
  - Precision: |A ∩ B| / |A|
  - Recall: |A ∩ B| / |B|
  - Zone Hit Rate: 1 if IoU >= 0.5 else 0
  - Bootstrap Confidence Intervals (95% CI)
  - Detection Latency (seconds from first causal event to first High prediction)

Adheres strictly to contracts/ground_truth_format.yaml and contracts/scenario_format.yaml.
The engine never imports this file.
"""

from __future__ import annotations

import json
import os
import random
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml

# Add repo root to sys.path so modules can be imported
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from contracts.event_schema import CanonicalEvent
from engine.cell_state import all_cells, get_cell
from engine.engine import ENGINE

HIGH_RISK_THRESHOLD = 0.65


@dataclass
class EvaluationMetrics:
    scenario_id: str
    scenario_name: str
    iou: float
    iou_ci: Tuple[float, float]
    precision: float
    recall: float
    f1_score: float
    zone_hit: bool
    predicted_count: int
    ground_truth_count: int
    intersection_count: int
    union_count: int
    detection_latency_seconds: Optional[float] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "scenario_name": self.scenario_name,
            "iou": round(self.iou, 4),
            "iou_ci_95": [round(self.iou_ci[0], 4), round(self.iou_ci[1], 4)],
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1_score": round(self.f1_score, 4),
            "zone_hit": self.zone_hit,
            "predicted_count": self.predicted_count,
            "ground_truth_count": self.ground_truth_count,
            "intersection_count": self.intersection_count,
            "union_count": self.union_count,
            "detection_latency_seconds": round(self.detection_latency_seconds, 2) if self.detection_latency_seconds else None,
            "timestamp": self.timestamp,
        }


def compute_iou(
    predicted_cells: Set[str],
    ground_truth_cells: Set[str],
    iou_hit_threshold: float = 0.5,
) -> Dict[str, Any]:
    """
    Computes spatial IoU and classification metrics between two cell sets.
    """
    intersection = predicted_cells & ground_truth_cells
    union = predicted_cells | ground_truth_cells

    iou = len(intersection) / len(union) if union else 1.0 if not predicted_cells and not ground_truth_cells else 0.0
    precision = len(intersection) / len(predicted_cells) if predicted_cells else 0.0
    recall = len(intersection) / len(ground_truth_cells) if ground_truth_cells else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "iou": iou,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "zone_hit": iou >= iou_hit_threshold,
        "intersection": len(intersection),
        "union": len(union),
    }


def bootstrap_ci(
    predicted_cells: Set[str],
    ground_truth_cells: Set[str],
    n_draws: int = 200,
    alpha: float = 0.05,
    seed: int = 42,
) -> Tuple[float, float]:
    """
    Bootstrap 95% confidence interval for IoU.
    """
    if not predicted_cells and not ground_truth_cells:
        return (1.0, 1.0)
    if not predicted_cells or not ground_truth_cells:
        return (0.0, 0.0)

    rng = random.Random(seed)
    all_items = list(predicted_cells | ground_truth_cells)
    n = len(all_items)

    ious: List[float] = []
    for _ in range(n_draws):
        sample = rng.choices(all_items, k=n)
        sample_set = set(sample)
        p_sub = predicted_cells & sample_set
        g_sub = ground_truth_cells & sample_set
        inter = len(p_sub & g_sub)
        un = len(p_sub | g_sub)
        ious.append(inter / un if un > 0 else 0.0)

    ious.sort()
    low_idx = int((alpha / 2) * n_draws)
    high_idx = int((1 - alpha / 2) * n_draws)
    return (ious[low_idx], ious[min(high_idx, n_draws - 1)])


def load_scenario_yaml(path: str | Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def evaluate_scenario(
    scenario_path: str | Path,
    ground_truth_path: Optional[str | Path] = None,
) -> EvaluationMetrics:
    """
    Replays a scenario through the engine and scores predicted High-risk zones.
    """
    scenario = load_scenario_yaml(scenario_path)
    scenario_id = scenario.get("scenario_id", "UNKNOWN")
    scenario_name = scenario.get("name", scenario_id)

    # 1. Resolve Ground Truth cells
    gt_cells: Set[str] = set()
    if ground_truth_path and Path(ground_truth_path).exists():
        gt_data = load_scenario_yaml(ground_truth_path)
        gt_cells = set(gt_data.get("ground_truth", {}).get("polygon_h3_cells", []))
    elif "ground_truth" in scenario:
        gt_cells = set(scenario["ground_truth"].get("polygon_h3_cells", []))

    # 2. Reset engine cells / state for isolated replay
    ENGINE.load_baseline()

    # 3. Replay scenario events
    events = scenario.get("events", [])
    first_causal_time = None
    first_high_prediction_time = None

    t0 = time.time()
    for ev in events:
        domain = ev.get("domain", "power")
        # Map scenario domain aliases
        if domain == "transport":
            domain = "transit" if "transit" in ev.get("event_type", "") else "road"

        src = ev.get("source_type", "sensor")
        if src == "crowd":
            src = "crowdsourced"

        now_iso = datetime.now(timezone.utc).isoformat()
        event_dict = {
            "event_id": f"scn-ev-{random.randint(10000, 99999)}",
            "domain": domain,
            "event_type": ev.get("event_type", "incident"),
            "entity_id": ev.get("entity_id", "sim_entity"),
            "h3_cell": ev.get("h3_cell"),
            "severity": float(ev.get("severity", 0.5)),
            "source_type": src,
            "source_reliability": 0.9 if src == "official" else 0.7 if src == "sensor" else 0.5,
            "event_timestamp": now_iso,
            "ingestion_timestamp": now_iso,
            "parse_confidence": 1.0,
            "scenario_tag": scenario_id,
        }

        try:
            canonical = CanonicalEvent(**event_dict)
            res = ENGINE.process_event(canonical)

            if first_causal_time is None:
                first_causal_time = time.time()

            if res.risk >= HIGH_RISK_THRESHOLD and not res.is_unknown and first_high_prediction_time is None:
                first_high_prediction_time = time.time()
        except Exception as e:
            # Skip invalid test events if schema rejects
            continue

    # 4. Collect predicted High-risk cells (risk >= 0.65 and not is_unknown)
    predicted_high: Set[str] = {
        cell_id for cell_id, cell in all_cells().items()
        if cell.risk >= HIGH_RISK_THRESHOLD and not cell.is_unknown
    }

    # 5. Compute metrics
    metrics_dict = compute_iou(predicted_high, gt_cells)
    ci = bootstrap_ci(predicted_high, gt_cells, n_draws=200)

    latency = None
    if first_causal_time and first_high_prediction_time:
        latency = max(0.01, first_high_prediction_time - first_causal_time)

    return EvaluationMetrics(
        scenario_id=scenario_id,
        scenario_name=scenario_name,
        iou=metrics_dict["iou"],
        iou_ci=ci,
        precision=metrics_dict["precision"],
        recall=metrics_dict["recall"],
        f1_score=metrics_dict["f1"],
        zone_hit=metrics_dict["zone_hit"],
        predicted_count=len(predicted_high),
        ground_truth_count=len(gt_cells),
        intersection_count=metrics_dict["intersection"],
        union_count=metrics_dict["union"],
        detection_latency_seconds=latency,
    )


def print_report(m: EvaluationMetrics) -> None:
    print("\n" + "=" * 70)
    print(f"  URBANPULSE EVALUATION REPORT — {m.scenario_id}")
    print(f"  Scenario: {m.scenario_name}")
    print("=" * 70)
    print(f"  Primary Metric (IoU):          {m.iou * 100:.2f}%")
    print(f"  IoU 95% Bootstrap CI:          [{m.iou_ci[0]*100:.2f}%, {m.iou_ci[1]*100:.2f}%]")
    print(f"  Precision:                     {m.precision * 100:.2f}%")
    print(f"  Recall:                        {m.recall * 100:.2f}%")
    print(f"  F1 Score:                      {m.f1_score:.4f}")
    print(f"  Zone Detected (IoU >= 0.5):    {'✅ YES' if m.zone_hit else '❌ NO'}")
    print(f"  Predicted High Cells:          {m.predicted_count}")
    print(f"  Ground Truth High Cells:       {m.ground_truth_count}")
    print(f"  Intersection:                  {m.intersection_count}")
    print(f"  Union:                         {m.union_count}")
    if m.detection_latency_seconds:
        print(f"  Detection Latency:             {m.detection_latency_seconds:.3f}s")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    scenario_arg = sys.argv[1] if len(sys.argv) > 1 else str(REPO_ROOT / "contracts" / "scenario_format.yaml")
    gt_arg = sys.argv[2] if len(sys.argv) > 2 else None
    res = evaluate_scenario(scenario_arg, gt_arg)
    print_report(res)
