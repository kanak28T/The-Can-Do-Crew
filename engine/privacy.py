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

DEFAULT_POPULATION_FLOOR = 500.0  # Cells with fewer than 500 people merge to protect anonymity


def merge_subcell(
    cell: str,
    k: int = K_DEFAULT,
    contributor_count: int = 999,
    population: float = 5000.0,
    min_population: float = DEFAULT_POPULATION_FLOOR,
) -> tuple[str, bool, str | None]:
    """
    If contributor_count < k OR population < min_population,
    return (parent_res8, True, reason). Otherwise return (cell, False, None).

    Args:
        cell              : H3 res-9 cell ID
        k                 : minimum contributors threshold
        contributor_count : how many unique source tokens contributed this hour
        population        : WorldPop population count for this cell
        min_population    : population floor threshold

    Returns:
        (resulting_cell_id, was_merged: bool, merge_reason: str | None)
    """
    if contributor_count < k:
        return h3.cell_to_parent(cell, 8), True, "contributor_count_below_k"
    if population < min_population:
        return h3.cell_to_parent(cell, 8), True, "population_below_floor"
    return cell, False, None


def apply_k_merge(
    cells: list[dict],
    contributor_counts: dict[str, int],
    populations: dict[str, float] = None,
    k: int = K_DEFAULT,
    min_population: float = DEFAULT_POPULATION_FLOOR,
) -> list[dict]:
    """
    Apply k-merge and population floor privacy enforcement to a list of zone cells.

    Args:
        cells              : list of dicts with at least {"cell_id": str, ...}
        contributor_counts : {h3_cell: contributor_count} for the current hour
        populations        : {h3_cell: population} from WorldPop lookup
        k                  : merge threshold
        min_population     : population floor

    Returns:
        Same list with cell_id replaced by parent where k or pop floor not met,
        and "was_merged": True, "merge_reason": reason added.
    """
    populations = populations or {}
    result = []
    for cell_data in cells:
        cid = cell_data.get("cell_id", "")
        count = contributor_counts.get(cid, 999)
        pop = populations.get(cid, 5000.0)
        merged_id, was_merged, reason = merge_subcell(
            cid,
            k=k,
            contributor_count=count,
            population=pop,
            min_population=min_population,
        )
        result.append({
            **cell_data,
            "cell_id": merged_id,
            "was_merged": was_merged,
            "merge_reason": reason,
        })
    return result

