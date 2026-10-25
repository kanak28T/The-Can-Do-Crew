"""Unit tests for engine/privacy.py. Lives at: urbanpulse/tests/b2/test_privacy.py"""
import pytest

import h3
from engine.privacy import apply_privacy


def rec(lat, lng, contributors, pop=500.0, risk=0.5, conf=0.8):
    return {"h3_cell": h3.latlng_to_cell(lat, lng, 9), "contributors": contributors,
            "population": pop, "risk": risk, "confidence": conf}


def siblings():
    """Two r9 cells with the same r8 parent, found by search so this works with real or stand-in h3."""
    a = h3.latlng_to_cell(21.1, 79.05, 9)
    pa = h3.cell_to_parent(a, 8)
    la, ga = h3.cell_to_latlng(a)
    for dlat in (0, 0.0018, -0.0018, 0.0036):
        for dlng in (0, 0.0018, -0.0018, 0.0036):
            b = h3.latlng_to_cell(la + dlat, ga + dlng, 9)
            if b != a and h3.cell_to_parent(b, 8) == pa:
                return a, b, pa
    raise AssertionError("no sibling found")


def test_all_children_meet_k_publish_at_r9():
    a, b, _ = siblings()
    recs = [{"h3_cell": a, "contributors": 6, "population": 400, "risk": 0.2, "confidence": 0.9},
            {"h3_cell": b, "contributors": 7, "population": 600, "risk": 0.8, "confidence": 0.7}]
    out, sup = apply_privacy(recs, k=5, pop_floor=100)
    assert sup == 0 and {o["h3_cell"] for o in out} == {a, b}
    assert all(o["resolution"] == 9 and o["merged_from"] == 0 for o in out)


def test_one_failing_child_merges_whole_parent_no_subtraction_leak():
    a, b, parent = siblings()
    recs = [{"h3_cell": a, "contributors": 9, "population": 400, "risk": 0.2, "confidence": 0.9},
            {"h3_cell": b, "contributors": 1, "population": 600, "risk": 0.8, "confidence": 0.7}]
    out, sup = apply_privacy(recs, k=5, pop_floor=100)
    assert len(out) == 1 and out[0]["h3_cell"] == parent and out[0]["resolution"] == 8
    assert out[0]["merged_from"] == 2 and out[0]["contributors"] == 10
    assert not any(o["h3_cell"] in (a, b) for o in out)       # no child published beside parent
    assert abs(out[0]["risk"] - (0.2 * 400 + 0.8 * 600) / 1000) < 1e-9


def test_merged_group_still_below_k_is_suppressed():
    a, b, _ = siblings()
    recs = [{"h3_cell": a, "contributors": 1, "population": 400, "risk": 0.2, "confidence": 0.9},
            {"h3_cell": b, "contributors": 2, "population": 600, "risk": 0.8, "confidence": 0.7}]
    out, sup = apply_privacy(recs, k=5, pop_floor=0)
    assert out == [] and sup == 1


def test_population_floor_checked_after_merge():
    a, b, parent = siblings()
    recs = [{"h3_cell": a, "contributors": 9, "population": 30, "risk": 0.2, "confidence": 0.9},
            {"h3_cell": b, "contributors": 9, "population": 30, "risk": 0.8, "confidence": 0.7}]
    out, sup = apply_privacy(recs, k=5, pop_floor=100)          # each child < floor individually
    assert out == [] and sup == 2
    recs[1]["contributors"] = 1                                 # force merge: parent pop = 60 < 100
    out, sup = apply_privacy(recs, k=5, pop_floor=100)
    assert out == [] and sup == 1
    out, sup = apply_privacy(recs, k=5, pop_floor=50)           # 60 >= 50 -> published at r8
    assert len(out) == 1 and out[0]["h3_cell"] == parent


def test_never_returns_sub_k_and_validates_input():
    recs = [rec(21.1 + i * 0.01, 79.05, c) for i, c in enumerate([0, 1, 2, 3, 4, 5, 6, 8])]
    out, _ = apply_privacy(recs, k=5, pop_floor=0)
    assert all(o["contributors"] >= 5 for o in out)
    with pytest.raises(ValueError):
        apply_privacy(recs, k=0, pop_floor=0)
    with pytest.raises(KeyError):
        apply_privacy([{"h3_cell": recs[0]["h3_cell"]}], k=1, pop_floor=0)


def test_deterministic_regardless_of_input_order():
    recs = [rec(21.1 + i * 0.01, 79.05, 9) for i in range(6)]
    o1, _ = apply_privacy(recs, 5, 0)
    o2, _ = apply_privacy(list(reversed(recs)), 5, 0)
    assert o1 == o2


def test_merge_subcell_helper():
    from engine.privacy import merge_subcell
    cell = h3.latlng_to_cell(21.1, 79.05, 9)
    parent = h3.cell_to_parent(cell, 8)

    # Below k -> merged to r8 parent
    assert merge_subcell(cell, k=5, contributor_count=4) == parent
    # At or above k -> remains r9 cell
    assert merge_subcell(cell, k=5, contributor_count=5) == cell
    assert merge_subcell(cell, k=5, contributor_count=10) == cell

    # Validations
    with pytest.raises(ValueError):
        merge_subcell(cell, k=0)
    with pytest.raises(ValueError):
        merge_subcell(cell, contributor_count=-1)
    with pytest.raises(ValueError):
        merge_subcell(parent, k=5)  # must be res 9


def test_apply_k_merge_wrapper():
    from engine.privacy import apply_k_merge
    a, b, parent = siblings()
    cells = [
        {"cell_id": a, "population": 400.0, "risk": 0.2, "confidence": 0.9},
        {"cell_id": b, "population": 600.0, "risk": 0.8, "confidence": 0.7},
    ]

    # When all meet k
    counts_ok = {a: 6, b: 7}
    res_ok = apply_k_merge(cells, counts_ok, k=5)
    assert len(res_ok) == 2
    assert all(not r["was_merged"] for r in res_ok)

    # When one fails k -> whole parent merged to r8
    counts_fail = {a: 9, b: 2}
    res_merged = apply_k_merge(cells, counts_fail, k=5)
    assert len(res_merged) == 1
    assert res_merged[0]["cell_id"] == parent
    assert res_merged[0]["was_merged"] is True
    assert res_merged[0]["resolution"] == 8
