"""
k-merge: cells with < k expected contributors merge to H3 res-8 parent.
Phase 6: implement full logic. Stub for Phase 0.
"""
import h3


def merge_subcell(cell: str, k: int = 5, contributor_count: int = 999) -> str:
    """
    If contributor_count < k, return the H3 res-8 parent cell.
    Otherwise return the cell unchanged.

    Args:
        cell: H3 res-9 cell ID
        k: Minimum contributors threshold (default 5)
        contributor_count: How many unique contributors for this cell

    Returns:
        cell if k met, else H3 res-8 parent
    """
    if contributor_count < k:
        return h3.cell_to_parent(cell, 8)
    return cell
