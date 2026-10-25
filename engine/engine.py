"""
UrbanPulse — Engine Orchestrator
==================================
Owner  : Kanak (A2) — Day 2

This is the single entry point for the API.
Priyanshu's api/main.py calls process_event() on every /ingest hit.

Flow:
    CanonicalEvent
        → cell_state.update()             # store + decay domain stress
        → cell_state.update_confidence()  # coverage × freshness × agreement
        → risk_model.score()              # logistic p + label
        → risk_model.bootstrap_interval() # 90% CI (fast, 200 draws)
        → cell_state cached (risk, label, interval)
        → returns CellUpdateResult        # sent to SSE stream
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from contracts.event_schema import CanonicalEvent
from engine.baseline_features import BaselineFeatures, load_baseline_features
from engine.cell_state import CellState, get_cell, snapshot
from engine.risk_model import MODEL, RiskModel


# ── Engine singleton ──────────────────────────────────────────────────────────

@dataclass
class CellUpdateResult:
    """Returned by process_event() and forwarded to the SSE stream."""
    cell:       str
    risk:       float
    label:      str
    interval:   tuple[float, float]
    confidence: float
    is_unknown: bool
    domain:     str
    severity:   float
    timestamp:  str


class UrbanPulseEngine:
    """
    Stateful engine. One instance lives for the lifetime of the API process.
    Holds baseline features (loaded at startup) and the risk model.
    """

    def __init__(self, model: RiskModel = MODEL):
        self.model     = model
        self.baseline: dict[str, BaselineFeatures] = {}
        self._loaded   = False

    def load_baseline(self, grid_path: str = "data/nagpur_h3_res9.geojson") -> None:
        """
        Load static baseline features for all H3 cells.
        Called once at API startup (api/main.py @startup event).
        Safe to call again to refresh after new data files arrive.
        """
        self.baseline = load_baseline_features(grid_path)
        self._loaded  = True
        print(f"[engine] Baseline loaded: {len(self.baseline)} cells.")

    def _get_baseline_dict(self, h3_cell: str) -> dict:
        """Return baseline feature dict for a cell, or safe defaults."""
        bf = self.baseline.get(h3_cell)
        return bf.to_dict() if bf else {}

    def process_event(self, event: CanonicalEvent) -> CellUpdateResult:
        """
        Main entry point. Called by api/main.py on every valid /ingest hit.

        1. Strip scenario_tag (production path — never used in scoring)
        2. Update cell state (stress + confidence)
        3. Re-score with risk model
        4. Cache result on cell state
        5. Return CellUpdateResult for SSE broadcast
        """
        # Production path: never let scenario_tag influence scoring
        if hasattr(event, 'for_production'):
            event = event.for_production()

        cell: CellState = get_cell(event.h3_cell)

        # 1. Update domain stress
        domain_val = event.domain if isinstance(event.domain, str) else event.domain.value
        src_val    = event.source_type if isinstance(event.source_type, str) else event.source_type.value
        cell.update(
            domain=domain_val,
            stress=event.severity,
            source_type=src_val,
        )

        # 2. Recompute confidence
        cell.update_confidence()

        # 3. Score
        baseline_dict = self._get_baseline_dict(event.h3_cell)
        stress        = cell.decayed_stress

        if cell.is_unknown:
            # Not enough data — show grey, don't score
            p, label = 0.0, "unknown"
            interval = (0.0, 1.0)
        else:
            p, label = self.model.score(stress, baseline_dict)
            interval = self.model.bootstrap_interval(stress, baseline_dict, n=200)

        # 4. Cache on cell state
        cell.risk          = p
        cell.risk_label    = label
        cell.risk_interval = interval

        return CellUpdateResult(
            cell=event.h3_cell,
            risk=p,
            label=label,
            interval=interval,
            confidence=cell.confidence,
            is_unknown=cell.is_unknown,
            domain=domain_val,
            severity=event.severity,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def apply_reliability_weight(
        self,
        event: CanonicalEvent,
        current_stress: float,
    ) -> float:
        """
        Reliability-weighted fusion (plan D10).
        Blends new event stress with existing cell stress using source reliability.

        official(0.9) dominates crowd(0.5); anonymous(0.3) barely moves the needle.
        Spam cap is enforced upstream in api/main.py before this is called.
        """
        w_new      = event.source_reliability
        w_existing = 1.0 - w_new
        return round(w_new * event.severity + w_existing * current_stress, 4)

    def handle_conflict(
        self,
        official_stress: float,
        crowd_stress: float,
        threshold: float = 0.4,
    ) -> tuple[float, bool]:
        """
        Conflict detection (plan section 6).
        If official and crowd disagree by > threshold, fuse but flag for verify.

        Returns:
            (fused_stress, conflict_detected: bool)
        """
        fused    = 0.9 * official_stress + 0.5 * crowd_stress / (0.9 + 0.5)
        conflict = abs(official_stress - crowd_stress) > threshold
        return round(fused, 4), conflict


# ── Global engine instance (imported by api/main.py) ─────────────────────────
ENGINE = UrbanPulseEngine()
