"""B2 task B2.3 (economic proxy layer 2): OSM building density per H3 cell.

Lives at: urbanpulse/data/scripts/04_building_density.py
Output:   data/building_density_per_cell.json

Label this a "built-up density proxy", NOT income: dense areas can be wealthy or poor.

TEST ON A SMALL AREA FIRST (download size is unknown):
  python data/scripts/04_building_density.py --bbox 79.06,21.13,79.10,21.16
Then the full study polygon:
  python data/scripts/04_building_density.py

Needs: pip install osmnx geopandas shapely h3
"""
import argparse

import b2lib


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bbox", help="west,south,east,north for a small test run")
    ap.add_argument("--endpoint", help="Overpass API endpoint URL (or set OVERPASS_URL env var)")
    args = ap.parse_args()

    import geopandas as gpd
    import osmnx as ox
    from shapely.geometry import box
    from shapely.ops import unary_union

    b2lib.configure_osmnx(endpoint=args.endpoint)
    cells = b2lib.load_grid_cells()
    cellset = set(cells)
    if args.bbox:
        w, s, e, n = (float(x) for x in args.bbox.split(","))
        area = box(w, s, e, n)
        out_name = "building_density_per_cell.TEST.json"
    else:
        area = unary_union(gpd.read_file(b2lib.DATA / "nagpur_study_polygon.geojson").to_crs(4326).geometry)
        out_name = "building_density_per_cell.json"

    try:
        b = ox.features_from_polygon(area, tags={"building": True})
    except Exception as exc:
        print(b2lib.classify_overpass_error(exc, endpoint=args.endpoint))
        raise SystemExit(1)
    b = b[b.geometry.type.isin(["Polygon", "MultiPolygon"])]
    print(len(b), "building polygons downloaded")
    bu = b.to_crs(b2lib.UTM_EPSG)
    cen = bu.geometry.centroid.to_crs(4326)
    per_cell, outside = b2lib.aggregate_buildings(list(zip(cen.y, cen.x)), bu.geometry.area, cellset)
    meta = {"source": "OpenStreetMap buildings", "license": "ODbL 1.0", "method": "building centroid -> r9 cell",
            "built_fraction": "sum(footprint m2) / 105332.5 m2 (average r9 area), capped at 1",
            "n_buildings": int(len(b)), "n_outside_grid": outside,
            "caveat": "OSM building completeness varies across the city; a cell with no record may be unmapped, not empty"}
    b2lib.write_json(b2lib.DATA / out_name, {"meta": meta, "cells": per_cell})
    print(f"{len(per_cell)} of {len(cells)} cells have >=1 building; {outside} buildings outside the grid -> data/{out_name}")
    if not args.bbox:
        b2lib.register_source("OSM buildings", "https://www.openstreetmap.org", "ODbL 1.0 (OpenStreetMap contributors)",
                              "OSM live extract", "data/building_density_per_cell.json", "built-up density proxy; not income")


if __name__ == "__main__":
    main()