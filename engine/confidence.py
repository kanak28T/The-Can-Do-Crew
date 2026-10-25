"""
UrbanPulse — Confidence Formula
=================================
Owner  : Kanak (A2) — Day 2

confidence = coverage × freshness × source_agreement   (plan section 6)

Used by cell_state.py (Priyanshu A1) to set the confidence of each cell.
A cell with confidence < UNKNOWN_THRESHOLD is shown as grey Unknown on the map.
"""

from datetime import datetime, timezone

UNKNOWN_THRESHOLD = 0.25   # below this → grey Unknown state
STALE_HOURS       = 12.0   # no update in 12h → freshness drops to 0


def compute_confidence(
    source_types: list[str],
    last_updated: datetime,
    source_stresses: list[float],
    stale_threshold_hours: float = STALE_HOURS,
) -> float:
    """
    Args:
        source_types      : list of source_type strings that reported this cell
        last_updated      : datetime of the most recent event for this cell (UTC)
        source_stresses   : list of severity values from each source
        stale_threshold_hours: hours until a cell is considered fully stale

    Returns:
        confidence in [0.0, 1.0]
    """
    # Coverage: 1 source = 0.33, 2 = 0.67, 3+ = 1.0
    coverage = min(1.0, len(source_types) / 3.0)

    # Freshness: linear decay from 1.0 → 0.0 over stale_threshold_hours
    hours_old = (datetime.now(timezone.utc) - last_updated).total_seconds() / 3600
    freshness = max(0.0, 1.0 - hours_old / stale_threshold_hours)

    # Source agreement: lower std → higher agreement
    if len(source_stresses) > 1:
        mean = sum(source_stresses) / len(source_stresses)
        variance = sum((x - mean) ** 2 for x in source_stresses) / len(source_stresses)
        std = variance ** 0.5
        agreement = max(0.0, 1.0 - std / 0.5)
    else:
        agreement = 1.0

    return round(coverage * freshness * agreement, 4)


def is_unknown(confidence: float) -> bool:
    """Return True if confidence is too low to show a risk score (show grey instead)."""
    return confidence < UNKNOWN_THRESHOLD


def confidence_label(confidence: float) -> str:
    """Human-readable label for confidence value."""
    if confidence >= 0.7:
        return "high"
    if confidence >= 0.4:
        return "medium"
    if confidence > 0.0:
        return "low"
    return "unknown"

