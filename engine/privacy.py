"""B2 task B4.1: k-merge + population floor for published risk scores.

Lives at: urbanpulse/engine/privacy.py
Call it from the /zones response path (B4.2) so no sub-k cell ever leaves the API.

records: list of dicts with h3_cell (res 9), contributors, population, risk, confidence.
  contributors = distinct transient tokens in the 1-hour bin (NOT population).

Rules
  * If ANY child r9 cell of an r8 parent has contributors < k, the WHOLE parent is merged and
    published once at r8. This avoids publishing a child next to its parent (leak by subtraction).
  * After merging, a group is suppressed if contributors < k or population < pop_floor.
  * Merged risk/confidence are population-weighted averages. That is a PLACEHOLDER; Alpha owns
    how risk should really combine.
  * Noise on published counts is not applied here.
"""
from collections import defaultdict

import h3

REQUIRED = ("h3_cell", "contributors", "population", "risk", "confidence")


def apply_privacy(records, k, pop_floor, parent_res=8):
    if k < 1:
        raise ValueError("k must be >= 1")
    for r in records:
        missing = [key for key in REQUIRED if key not in r]
        if missing:
            raise KeyError(f"record {r.get('h3_cell')!r} missing {missing}")

    by_parent = defaultdict(list)
    for r in sorted(records, key=lambda x: x["h3_cell"]):
        by_parent[h3.cell_to_parent(r["h3_cell"], parent_res)].append(r)

    published, suppressed = [], 0
    for parent in sorted(by_parent):
        kids = by_parent[parent]
        if all(r["contributors"] >= k for r in kids):
            groups = [(r["h3_cell"], [r]) for r in kids]   # publish at r9
        else:
            groups = [(parent, kids)]                        # merge whole parent to r8
        for cell, members in groups:
            contrib = sum(m["contributors"] for m in members)
            pop = sum(m["population"] for m in members)
            if contrib < k or pop < pop_floor:
                suppressed += 1
                continue
            w = [max(m["population"], 1e-9) for m in members]
            tot = sum(w)
            published.append({
                "h3_cell": cell,
                "resolution": h3.get_resolution(cell),
                "contributors": contrib,
                "population": pop,
                "risk": sum(m["risk"] * wi for m, wi in zip(members, w)) / tot,
                "confidence": sum(m["confidence"] * wi for m, wi in zip(members, w)) / tot,
                "merged_from": len(members) if len(members) > 1 else 0,
            })
    return published, suppressed