"""Unit tests for data/scripts/b2lib.py. Lives at: urbanpulse/tests/b2/test_b2_data.py
Run from repo root:  pytest tests/b2 -v
"""
import json

import numpy as np
import pytest

import b2lib
from conftest import REAL_H3


def make_cells(n_lat=8, n_lng=10):
    import h3
    base_lat, base_lng = 21.10, 79.05
    return sorted({h3.latlng_to_cell(base_lat + i * 0.0021, base_lng + j * 0.0021, 9)
                   for i in range(n_lat) for j in range(n_lng)})


# ---------------- VIIRS
def test_tile_math_for_h25v06():
    assert b2lib.parse_tile("VNP46A4.A2024001.h25v06.002.2025123.h5") == (25, 6)
    assert b2lib.tile_origin(25, 6) == (70.0, 30.0)
    # Nagpur is ~21.15N, 79.09E -> h=(79.09+180)/10=25.9, v=(90-21.15)/10=6.88
    assert (int((79.09 + 180) // 10), int((90 - 21.15) // 10)) == (25, 6)


def test_pixel_index_and_outside():
    assert b2lib.pixel_index(21.1060, 79.0900, 70.0, 30.0) == (2134, 2181)
    assert b2lib.pixel_index(31.0, 79.0, 70.0, 30.0) is None
    assert b2lib.pixel_index(25.0, 69.0, 70.0, 30.0) is None


def test_parse_tile_rejects_bad_name():
    with pytest.raises(ValueError):
        b2lib.parse_tile("nothing.h5")


def test_sample_viirs_fill_scale_shared_pixels():
    cells = make_cells()
    ntl = np.full((2400, 2400), 100, dtype=np.uint16)
    qual = np.full((2400, 2400), 1, dtype=np.uint8)
    # poison the pixel under the first cell with the fill value
    import h3
    lat, lng = h3.cell_to_latlng(cells[0])
    r, c = b2lib.pixel_index(lat, lng, 70.0, 30.0)
    ntl[r, c] = 65535
    recs, s = b2lib.sample_viirs(cells, ntl, qual, (25, 6), fill=65535, scale=0.1, year=2024)
    assert recs[cells[0]]["missing"] and recs[cells[0]]["viirs"] is None
    ok = [v for k, v in recs.items() if not v["missing"]]
    assert ok and all(abs(v["viirs"] - 10.0) < 1e-9 for v in ok)
    assert s["n_cells"] == len(cells) and s["n_unique_pixels"] <= len(cells)
    assert s["cells_per_pixel"] >= 1.0
    assert all(v["quality_flag"] == 1 for v in ok)


def test_sample_viirs_outside_tile_is_missing_not_filled():
    import h3
    far = h3.latlng_to_cell(35.0, 79.0, 9)
    recs, s = b2lib.sample_viirs([far], np.zeros((2400, 2400)), None, (25, 6))
    assert recs[far]["missing"] and recs[far]["reason"] == "outside_tile" and s["n_missing"] == 1


# ---------------- buildings + econ
def test_aggregate_buildings():
    import h3
    c = h3.latlng_to_cell(21.1, 79.05, 9)
    lat, lng = h3.cell_to_latlng(c)
    pts = [(lat, lng), (lat, lng), (50.0, 50.0)]
    out, outside = b2lib.aggregate_buildings(pts, [100.0, 50.0, 10.0], cellset={c})
    assert outside == 1 and out[c]["building_count"] == 2 and out[c]["footprint_m2"] == 150.0
    assert 0 < out[c]["built_fraction"] < 1


def test_percentile_ranks_ties_and_edges():
    p = b2lib.percentile_ranks({"a": 1, "b": 2, "c": 2, "d": 9})
    assert p["a"] == 0.0 and p["d"] == 1.0 and p["b"] == p["c"]
    assert b2lib.percentile_ranks({"x": 5}) == {"x": 0.5}
    assert b2lib.percentile_ranks({}) == {}


def test_merge_econ_missing_handling_and_direction():
    cells = ["A", "B", "C", "D"]
    viirs = {"A": {"viirs": 1.0}, "B": {"viirs": 50.0}, "C": {"viirs": None}, "D": {"viirs": 10.0}}
    bld = {"A": {"built_fraction": 0.9}, "B": {"built_fraction": 0.1}, "C": {"built_fraction": 0.5}}
    out = b2lib.merge_econ(cells, viirs, bld)
    assert out["A"]["economic_constraint"] > out["B"]["economic_constraint"]  # dark+dense vs bright+sparse
    assert out["C"]["components_used"] == ["built_fraction"]                  # no light -> renormalised
    assert out["D"]["no_osm_buildings"] is True
    assert all(0.0 <= v["economic_constraint"] <= 1.0 for v in out.values())
    flipped = b2lib.merge_econ(cells, viirs, bld, built_sign=-1)
    assert flipped["A"]["economic_constraint"] < out["A"]["economic_constraint"]


def test_merge_econ_missing_light_and_empty_inputs():
    out = b2lib.merge_econ(["A"], {"A": {"viirs": None}}, {})
    # light missing; a cell with no OSM buildings still gets built_fraction 0.0 (flagged no_osm_buildings)
    assert out["A"]["components_used"] == ["built_fraction"]
    out2 = b2lib.merge_econ([], {}, {})
    assert out2 == {}


# ---------------- mapping tables
def test_feeders_partition_deterministic_and_named():
    cells = make_cells()
    pop = {c: float(i % 7) for i, c in enumerate(cells)}
    f1 = b2lib.cluster_cells(cells, pop, 5, seed=0)
    f2 = b2lib.cluster_cells(cells, pop, 5, seed=0)
    assert f1 == f2
    assert list(f1) == [f"FDR-{i:02d}" for i in range(1, 6)]
    flat = [c for v in f1.values() for c in v]
    assert sorted(flat) == cells and len(flat) == len(set(flat))
    assert b2lib.assert_mapping_in_grid(f1, set(cells))


def test_assert_mapping_in_grid_catches_strays():
    with pytest.raises(AssertionError):
        b2lib.assert_mapping_in_grid({"X": ["nope"]}, {"a"})


def test_pump_zone_dependency_and_routes():
    cells = make_cells()
    feeders = b2lib.cluster_cells(cells, {}, 4, seed=0)
    pumps = b2lib.cluster_cells(cells, {}, 3, seed=1, prefix="PMP")
    dep = b2lib.pump_zone_dependencies(pumps, feeders)
    assert set(dep) == set(pumps) and set(dep.values()) <= set(feeders)
    r1 = b2lib.synthetic_routes(cells, seed=3, n_routes=6, min_sep_deg=0.01)
    r2 = b2lib.synthetic_routes(cells, seed=3, n_routes=6, min_sep_deg=0.01)
    assert r1 == r2 and "4" in r1 and r1["4"]["synthetic"] is True
    assert all(len(v["cells"]) >= 1 for v in r1.values())
    b2lib.assert_mapping_in_grid({k: v["cells"] for k, v in r1.items()}, set(cells))


def test_extract_population_shapes():
    assert b2lib.extract_population({"a": 1, "b": 2}) == {"a": 1.0, "b": 2.0}
    assert b2lib.extract_population({"meta": {}, "population": {"a": 3}}) == {"a": 3.0}
    assert b2lib.extract_population({"cells": {"a": {"population": 4}}}) == {"a": 4.0}


# ---------------- wards / geojson helpers
def test_overpass_summary_and_bounds():
    payload = {"elements": [
        {"type": "relation", "id": 1, "tags": {"name": "B", "admin_level": "10"}},
        {"type": "relation", "id": 2, "tags": {"name": "A", "admin_level": "9", "ref": "7"}}]}
    s = b2lib.summarise_overpass_tags(payload)
    assert s["count"] == 2 and s["by_admin_level"] == {"10": 1, "9": 1}
    gj = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {},
          "geometry": {"type": "Polygon", "coordinates": [[[79.0, 21.0], [79.2, 21.0], [79.2, 21.3], [79.0, 21.0]]]}}]}
    assert b2lib.geojson_bounds(gj) == (79.0, 21.0, 79.2, 21.3)


def test_grid_geojson_contract():
    cells = make_cells(2, 2)
    gj = b2lib.build_grid_geojson(cells)
    f = gj["features"][0]
    assert set(f["properties"]) == {"h3_cell", "h3_parent_r8"}
    ring = f["geometry"]["coordinates"][0]
    assert ring[0] == ring[-1]
    json.dumps(gj)


@pytest.mark.skipif(not REAL_H3, reason="needs the real h3 package")
def test_real_h3_polygon_fill_and_resolution():
    import h3
    poly = {"type": "Polygon", "coordinates": [[[79.05, 21.10], [79.10, 21.10], [79.10, 21.15], [79.05, 21.15], [79.05, 21.10]]]}
    cells = b2lib.polygon_to_cells(poly, 9)
    assert 100 < len(cells) < 5000
    assert {h3.get_resolution(c) for c in cells} == {9}
    # ring is (lng, lat) and inside the box
    lng, lat = b2lib.cell_ring_lnglat(cells[0])[0]
    assert 79.0 < lng < 79.2 and 21.0 < lat < 21.2