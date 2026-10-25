"""
UrbanPulse — Privacy Enforcement (k-merge)
==========================================
Phase 0: stub — signature + basic logic.
Phase 6 (Day 4): add population floor, Gaussian noise, budget accounting.

Rule (plan section 7):
  If a cell has fewer than k expected contributors in the current time bucket,
  merge it upward to its H3 res-8 parent until k is met or res-8 is reached.

k is a configurable setting (default 5).
This is called by api/ ONLY — never by engine/ internals.
"""

import h3

K_DEFAULT = 5  # configurable; expose via /admin/privacy in Phase 6


def merge_subcell(cell: str, k: int = K_DEFAULT, contributor_count: int = 999) -> str:
    """
    If contributor_count < k, return the H3 res-8 parent.
    Otherwise return the cell unchanged.

    Args:
        cell              : H3 res-9 cell ID
        k                 : minimum contributors threshold
        contributor_count : how many unique source tokens contributed this hour
                            (NOT a device count — see plan section 7)
    Returns:
        original cell if k is met, else its H3 res-8 parent
    """
    if contributor_count < k:
        return h3.cell_to_parent(cell, 8)
    return cell


def apply_k_merge(
    cells: list[dict],
    contributor_counts: dict[str, int],
    k: int = K_DEFAULT,
) -> list[dict]:
    """
    Apply k-merge to a list of cell dicts before returning from GET /zones.

    Args:
        cells              : list of dicts with at least {"cell_id": str, ...}
        contributor_counts : {h3_cell: contributor_count} for the current hour
        k                  : merge threshold

    Returns:
        Same list with cell_id replaced by parent where k not met,
        and "was_merged": True added to those entries.

    TODO (Phase 6 — Day 4):
        - Aggregate risk scores from all res-9 children into the merged parent.
        - Add WorldPop population floor (suppress cells below min_population).
        - Add calibrated Gaussian noise to published event counts.
        - Track daily privacy budget with simple composition.
    """
    result = []
    for cell_data in cells:
        cid = cell_data.get("cell_id", "")
        count = contributor_counts.get(cid, 0)
        merged_id = merge_subcell(cid, k=k, contributor_count=count)
        was_merged = merged_id != cid
        result.append({**cell_data, "cell_id": merged_id, "was_merged": was_merged})
    return result
