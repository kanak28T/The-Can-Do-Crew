"""
UrbanPulse — Privacy Enforcement Layer
========================================
Implements the k-merge rule and WorldPop population floor before any cell-level
risk data is published via the API.

Rules (plan section 7):
  1. k-merge:         If a cell has fewer than k expected contributors in the
                      current time bucket, merge it upward to its H3 res-8 parent
                      and repeat until k is met or we hit res-8.
  2. Population floor: Never publish a risk score for a cell whose WorldPop
                       population estimate is below MIN_POPULATION. Merge to parent.
  3. Time bucketing:  Published counts are rounded to 1-hour buckets.
  4. Count noise:     A small calibrated Gaussian noise is added to published
                      event counts before they leave the API layer.

k is a configurable setting (default 5). It can be changed via the /admin/privacy
endpoint (not implemented in Phase 0 — stub only).

IMPORTANT: This module is called by api/ ONLY, not by engine/. The engine works
on raw cell data. Privacy enforcement is the last step before the response leaves
the server.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ── Configuration ─────────────────────────────────────────────────────────────

@dataclass
class PrivacyConfig:
    k: int = 5                        # Minimum contributor count per published cell
    min_population: int = 10          # WorldPop minimum population floor
    count_noise_scale: float = 0.5    # Gaussian noise std for published counts
    max_merge_depth: int = 1          # Max times we go up one H3 resolution level
                                      # (res 9 -> res 8 is depth 1)


DEFAULT_CONFIG = PrivacyConfig()


# ── Cell publication result ────────────────────────────────────────────────────

@dataclass
class PublishableCell:
    """The privacy-safe version of a cell's risk data, ready to send to the frontend."""
    cell_id: str                       # H3 cell (may be res-8 parent after merge)
    resolution: int                    # 8 or 9
    risk_score: float
    confidence: float
    label: str                         # "Low" | "Medium" | "High" | "Unknown"
    was_merged: bool = False           # True if this cell was merged to a parent
    suppressed: bool = False           # True if below population floor — return Unknown
    driver_contributions: dict = field(default_factory=dict)
    interval: tuple[float, float] = (0.0, 1.0)


# ── k-merge ────────────────────────────────────────────────────────────────────

def k_merge(
    cell_id: str,
    contributor_count: int,
    population: float,
    cell_risk_data: dict,
    population_lookup: dict[str, float],
    config: PrivacyConfig = DEFAULT_CONFIG,
) -> PublishableCell:
    """
    Apply the k-merge rule and population floor to a single cell before publication.

    Parameters
    ----------
    cell_id : str
        H3 res-9 cell to evaluate.
    contributor_count : int
        Number of distinct event sources (by source_type + time bucket token)
        that contributed to this cell in the current time window.
        NOT a device count — see plan section 7.
    population : float
        WorldPop estimated population for this cell.
    cell_risk_data : dict
        The engine's output for this cell: keys = risk_score, confidence, label,
        driver_contributions, interval.
    population_lookup : dict[str, float]
        WorldPop population for any H3 cell (res 8 or 9). Used when merging.
    config : PrivacyConfig
        k, population floor, noise settings.

    Returns
    -------
    PublishableCell
        Privacy-safe cell data. If merged, cell_id is the res-8 parent.
        If suppressed, label is "Unknown" regardless of engine output.

    TODO (Phase 6 — Day 4):
        - Implement actual k check against contributor_count.
        - Implement H3 res-8 parent lookup using h3.cell_to_parent(cell_id, 8).
        - Aggregate risk data from all res-9 children when returning a merged parent.
        - Add calibrated Gaussian noise to published event counts.
        - Enforce daily privacy budget with simple composition accounting.
    """
    # ── STUB — full implementation in Phase 6 (Day 4) ─────────────────────────
    # For now: pass through the engine's output unchanged.
    # The TODO block above describes exactly what to add.

    label = cell_risk_data.get("label", "Unknown")
    risk  = cell_risk_data.get("risk_score", 0.0)
    conf  = cell_risk_data.get("confidence", 0.0)
    contrib = cell_risk_data.get("driver_contributions", {})
    interval = cell_risk_data.get("interval", (0.0, 1.0))

    # Basic population floor — suppress very small cells
    if population < config.min_population:
        return PublishableCell(
            cell_id=cell_id,
            resolution=9,
            risk_score=0.0,
            confidence=0.0,
            label="Unknown",
            suppressed=True,
            driver_contributions={},
            interval=(0.0, 1.0),
        )

    return PublishableCell(
        cell_id=cell_id,
        resolution=9,
        risk_score=risk,
        confidence=conf,
        label=label,
        was_merged=False,
        suppressed=False,
        driver_contributions=contrib,
        interval=interval,
    )


def apply_privacy_to_zone_response(
    cells: list[dict],
    population_lookup: dict[str, float],
    contributor_counts: dict[str, int],
    config: PrivacyConfig = DEFAULT_CONFIG,
) -> list[PublishableCell]:
    """
    Apply k-merge and population floor to a list of cells before returning
    them from GET /zones.

    Parameters
    ----------
    cells : list[dict]
        Raw engine output, one dict per H3 res-9 cell.
    population_lookup : dict[str, float]
        WorldPop population per cell.
    contributor_counts : dict[str, int]
        Current contributor count per cell (from the token store).
    config : PrivacyConfig
        Privacy settings.

    Returns
    -------
    list[PublishableCell]
        Privacy-enforced cells. Sub-k cells are merged; sub-population cells
        are suppressed. Never returns individual-level data.

    TODO (Phase 6 — Day 4): Wire in the real k_merge logic above.
    """
    result = []
    for cell_data in cells:
        cid = cell_data.get("cell_id", "")
        pop = population_lookup.get(cid, 0.0)
        contributors = contributor_counts.get(cid, 0)
        result.append(
            k_merge(
                cell_id=cid,
                contributor_count=contributors,
                population=pop,
                cell_risk_data=cell_data,
                population_lookup=population_lookup,
                config=config,
            )
        )
    return result
