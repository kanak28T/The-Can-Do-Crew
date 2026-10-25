
"""B2 privacy enforcement: H3 k-merge and population floor.

Apply this before publishing /zones responses.

Input records contain:
    h3_cell, contributors, population, risk, confidence

Contributors are distinct transient tokens in the time bucket, not population.

If any resolution-9 child of a resolution-8 parent fails k, the entire
parent group is merged. The merged group is suppressed if it still fails
the contributor threshold or the population floor.

Risk and confidence use population-weighted averages as placeholders.
Alpha owns the final risk aggregation policy. Noise and privacy-budget
accounting are not implemented here.
"""

from collections import defaultdict

import h3

REQUIRED = ("h3_cell", "contributors", "population", "risk", "confidence")
K_DEFAULT = 5


def apply_privacy(records, k, pop_floor, parent_res=8):
    if k < 1:
        raise ValueError("k must be >= 1")
    if pop_floor < 0:
        raise ValueError("pop_floor must be >= 0")

    by_parent = defaultdict(list)

    for record in records:
        missing = [key for key in REQUIRED if key not in record]
        if missing:
            raise KeyError(
                f"record {record.get('h3_cell')!r} missing {missing}"
            )

        cell = record["h3_cell"]
        if h3.get_resolution(cell) != parent_res + 1:
            raise ValueError(
                f"{cell!r} must be resolution {parent_res + 1}"
            )
        if record["contributors"] < 0 or record["population"] < 0:
            raise ValueError("contributors and population must be nonnegative")

        by_parent[h3.cell_to_parent(cell, parent_res)].append(record)

    published = []
    suppressed = 0

    for parent in sorted(by_parent):
        children = sorted(by_parent[parent], key=lambda r: r["h3_cell"])

        # If any child fails k, merge the entire parent group.
        if all(r["contributors"] >= k for r in children):
            groups = [(r["h3_cell"], [r]) for r in children]
        else:
            groups = [(parent, children)]

        for cell, members in groups:
            contributors = sum(r["contributors"] for r in members)
            population = sum(r["population"] for r in members)

            if contributors < k or population < pop_floor:
                suppressed += 1
                continue

            weights = [max(r["population"], 1e-9) for r in members]
            total_weight = sum(weights)

            published.append({
                "h3_cell": cell,
                "resolution": h3.get_resolution(cell),
                "contributors": contributors,
                "population": population,
                "risk": sum(
                    r["risk"] * w for r, w in zip(members, weights)
                ) / total_weight,
                "confidence": sum(
                    r["confidence"] * w for r, w in zip(members, weights)
                ) / total_weight,
                "merged_from": len(members) if len(members) > 1 else 0,
            })

    return published, suppressed


def merge_subcell(cell: str, k: int = K_DEFAULT,
                  contributor_count: int = 999) -> str:
    """Compatibility helper: return the r8 parent when this cell fails k."""
    if k < 1:
        raise ValueError("k must be >= 1")
    if h3.get_resolution(cell) != 9:
        raise ValueError("cell must be H3 resolution 9")
    if contributor_count < 0:
        raise ValueError("contributor_count must be nonnegative")

    return h3.cell_to_parent(cell, 8) if contributor_count < k else cell


def apply_k_merge(
    cells: list[dict],
    contributor_counts: dict[str, int],
    k: int = K_DEFAULT,
) -> list[dict]:
    """Compatibility wrapper around apply_privacy.

    Each cell must contain population, risk and confidence. Entries without
    these fields cannot be safely aggregated and will raise a clear error.
    """
    records = []

    for item in cells:
        cell = item.get("h3_cell", item.get("cell_id"))
        if not cell:
            raise ValueError("Each cell requires h3_cell or cell_id")

        missing = [key for key in ("population", "risk", "confidence")
                   if key not in item]
        if missing:
            raise ValueError(
                f"Cell {cell!r} lacks fields required for safe aggregation: "
                f"{missing}"
            )

        records.append({
            **item,
            "h3_cell": cell,
            "contributors": contributor_counts.get(
                cell, item.get("contributors", 0)
            ),
        })

    published, _suppressed = apply_privacy(
        records, k=k, pop_floor=0, parent_res=8
    )

    result = []
    for item in published:
        result.append({
            **item,
            "cell_id": item["h3_cell"],
            "was_merged": item["resolution"] == 8,
        })
    return result
