"""
Cell state registry — in-memory, per H3 res-9 cell.
Updated on every /ingest event. Decays over 48h.
Phase 1: A1 owns this file.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional
import math

# ── Decay rates per domain (half-life in hours) ───────────────────────────────
# Power outages linger; crowd reports fade fast
DECAY_HALF_LIFE_HOURS: Dict[str, float] = {
    "power":   24.0,
    "water":   18.0,
    "road":    12.0,
    "transit":  6.0,
    "health":   8.0,
    "comms":    4.0,
}
DEFAULT_HALF_LIFE = 12.0

STALE_THRESHOLD_HOURS  = 12.0   # no update → confidence drops
UNKNOWN_CONFIDENCE_THRESHOLD = 0.30   # below this → grey Unknown


@dataclass
class CellState:
    h3_cell: str

    # Per-domain live stress (0–1), decayed toward 0 over time
    domain_stress: Dict[str, float] = field(default_factory=dict)

    # Confidence: coverage × freshness × agreement
    confidence: float = 1.0

    # When was each domain last updated
    last_updated: Dict[str, datetime] = field(default_factory=dict)

    # How many unique sources contributed this window
    source_count: int = 0

    # Cached risk score (updated after each ingest)
    risk: float = 0.0
    risk_label: str = "low"
    risk_interval: tuple = (0.0, 1.0)

    # True when confidence < threshold OR no update in stale window
    is_unknown: bool = False

    @property
    def decayed_stress(self) -> Dict[str, float]:
        """Return domain stresses after applying time decay."""
        now = datetime.now(timezone.utc)
        result = {}
        for domain, stress in self.domain_stress.items():
            last = self.last_updated.get(domain)
            if last is None:
                result[domain] = stress
                continue
            hours_elapsed = (now - last).total_seconds() / 3600
            half_life = DECAY_HALF_LIFE_HOURS.get(domain, DEFAULT_HALF_LIFE)
            # Exponential decay: s(t) = s0 * 0.5^(t / half_life)
            decay_factor = math.pow(0.5, hours_elapsed / half_life)
            result[domain] = round(stress * decay_factor, 4)
        return result

    def update(self, domain: str, stress: float, source_type: str):
        """Apply a new event stress to this cell."""
        now = datetime.now(timezone.utc)
        # Weighted update: new stress blends with decayed existing stress
        current = self.decayed_stress.get(domain, 0.0)
        # Take max (worst case) — can be changed to weighted avg later
        self.domain_stress[domain] = max(current, stress)
        self.last_updated[domain] = now
        self.source_count += 1

    def check_unknown(self):
        """Mark cell Unknown if stale or low confidence."""
        now = datetime.now(timezone.utc)
        any_recent = any(
            (now - t).total_seconds() / 3600 < STALE_THRESHOLD_HOURS
            for t in self.last_updated.values()
        )
        if not any_recent and self.last_updated:
            self.is_unknown = True
        elif self.confidence < UNKNOWN_CONFIDENCE_THRESHOLD:
            self.is_unknown = True
        else:
            self.is_unknown = False


# ── Global in-memory registry ─────────────────────────────────────────────────
_registry: Dict[str, CellState] = {}


def get_cell(h3_cell: str) -> CellState:
    if h3_cell not in _registry:
        _registry[h3_cell] = CellState(h3_cell=h3_cell)
    return _registry[h3_cell]


def all_cells() -> Dict[str, CellState]:
    return _registry


def snapshot() -> list[dict]:
    """Return all cells as a list of dicts for SSE broadcast."""
    return [
        {
            "cell":       c.h3_cell,
            "risk":       c.risk,
            "label":      "unknown" if c.is_unknown else c.risk_label,
            "confidence": c.confidence,
            "stress":     c.decayed_stress,
        }
        for c in _registry.values()
    ]
