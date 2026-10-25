"""
UrbanPulse — Cell State Registry
==================================
Owner  : Priyanshu (A1) — base structure
         Kanak (A2) — confidence formula wired in (Day 2)

In-memory per-H3-res-9-cell state. Updated on every /ingest event.
Domain stresses decay exponentially over 48h toward zero.
Confidence = coverage × freshness × source_agreement  (engine/confidence.py)
Cells with confidence < UNKNOWN_THRESHOLD show as grey Unknown on the map.
"""

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List

from engine.confidence import compute_confidence, is_unknown, UNKNOWN_THRESHOLD

# ── Decay half-lives per domain (hours) ───────────────────────────────────────
# Power outages linger; crowd reports fade fast
DECAY_HALF_LIFE_HOURS: Dict[str, float] = {
    "power":   24.0,
    "water":   18.0,
    "road":    12.0,
    "transit":  6.0,
    "health":   8.0,
    "comms":    4.0,
}
DEFAULT_HALF_LIFE    = 12.0
STALE_THRESHOLD_HOURS = 12.0


@dataclass
class CellState:
    h3_cell: str

    # Per-domain live stress (0–1), decayed toward 0 over time
    domain_stress:  Dict[str, float]   = field(default_factory=dict)
    # When each domain was last updated
    last_updated:   Dict[str, datetime] = field(default_factory=dict)
    # Source types that reported in the current window (for coverage calc)
    source_types:   List[str]           = field(default_factory=list)
    # Raw stress values from each source (for agreement calc)
    source_stresses: List[float]        = field(default_factory=list)

    # Confidence: set by update_confidence() after each ingest
    confidence:  float = 1.0
    # Cached risk score — set by engine.py after re-scoring
    risk:        float  = 0.0
    risk_label:  str    = "low"
    risk_interval: tuple = (0.0, 1.0)
    # Grey Unknown state
    is_unknown:  bool   = False

    @property
    def decayed_stress(self) -> Dict[str, float]:
        """Return domain stresses after applying exponential time decay."""
        now = datetime.now(timezone.utc)
        result = {}
        for domain, stress in self.domain_stress.items():
            last = self.last_updated.get(domain)
            if last is None:
                result[domain] = stress
                continue
            hours = (now - last).total_seconds() / 3600
            half_life = DECAY_HALF_LIFE_HOURS.get(domain, DEFAULT_HALF_LIFE)
            result[domain] = round(stress * math.pow(0.5, hours / half_life), 4)
        return result

    def update(self, domain: str, stress: float, source_type: str) -> None:
        """
        Apply a new event to this cell.
        Takes the max of current decayed stress and new stress (worst-case).
        Records source metadata for confidence computation.
        """
        now = datetime.now(timezone.utc)
        current = self.decayed_stress.get(domain, 0.0)
        self.domain_stress[domain] = max(current, stress)
        self.last_updated[domain]  = now
        self.source_types.append(source_type)
        self.source_stresses.append(stress)
        # Keep only the last 20 sources to bound memory
        self.source_types    = self.source_types[-20:]
        self.source_stresses = self.source_stresses[-20:]

    def update_confidence(self) -> None:
        """
        Recompute confidence using the formula from engine/confidence.py.
        Called by engine.py after every update().
        Sets is_unknown when confidence is too low.
        """
        if not self.last_updated:
            self.confidence = 0.0
            self.is_unknown = True
            return

        most_recent = max(self.last_updated.values())
        self.confidence = compute_confidence(
            source_types=self.source_types,
            last_updated=most_recent,
            source_stresses=self.source_stresses,
        )
        self.is_unknown = is_unknown(self.confidence)

    def to_dict(self) -> dict:
        """Snapshot for SSE broadcast and API response."""
        return {
            "cell":       self.h3_cell,
            "risk":       self.risk,
            "label":      "unknown" if self.is_unknown else self.risk_label,
            "interval":   list(self.risk_interval),
            "confidence": self.confidence,
            "stress":     self.decayed_stress,
            "is_unknown": self.is_unknown,
        }


# ── Global in-memory registry ─────────────────────────────────────────────────
_registry: Dict[str, CellState] = {}


def get_cell(h3_cell: str) -> CellState:
    if h3_cell not in _registry:
        _registry[h3_cell] = CellState(h3_cell=h3_cell)
    return _registry[h3_cell]


def all_cells() -> Dict[str, CellState]:
    return _registry


def snapshot() -> list[dict]:
    """All cells as a list of dicts — used by SSE broadcast."""
    return [c.to_dict() for c in _registry.values()]
