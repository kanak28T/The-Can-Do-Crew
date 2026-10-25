"""B2 task: transit layer (bus stops and bus routes) from OpenStreetMap.

Lives at: data/download_scripts/07_transit.py
Output:   data/nagpur_transit.geojson

Fetches:
  - Bus stops (highway=bus_stop) as Points with osm_id and name
  - Bus routes (route=bus) with ref, name, osm_id

Never creates placeholder data: if OSM returns nothing, exits with a clear message.
"""
import argparse
from pathlib import Path

import b2lib


def format_osm_id(idx):
    if isinstance(idx, tuple):
        return "/".join(str(x) for x in idx)
    return str(idx)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--polygon", help="Path to study polygon GeoJSON (default: data/nagpur_study_polygon.geojson)")
    ap.add_argument("--endpoint", help="Overpass API endpoint URL (or set OVERPASS_URL env var)")
    ap.add_argument("--out", help="Output GeoJSON path (default: data/nagpur_transit.geojson)")
    args = ap.parse_args()

    import geopandas as gpd
    import pandas as pd
    import osmnx as ox
    from shapely.ops import unary_union

    poly_path = Path(args.polygon) if args.polygon else b2lib.DATA / "nagpur_study_polygon.geojson"
    if not poly_path.exists():
        raise SystemExit("Run 01_build_grid.py first (need data/nagpur_study_polygon.geojson).")

    out_path = Path(args.out) if args.out else b2lib.DATA / "nagpur_transit.geojson"

    b2lib.configure_osmnx(endpoint=args.endpoint)
    poly = unary_union(gpd.read_file(poly_path).to_crs(4326).geometry)

    # 1. Fetch bus stops
    print("Fetching bus stops (highway=bus_stop) from OSM...")
    try:
        stops_raw = ox.features_from_polygon(poly, tags={"highway": "bus_stop"})
    except Exception as exc:
        print(b2lib.classify_overpass_error(exc, endpoint=args.endpoint))
        raise SystemExit(1)

    stops_rows = []
    if not stops_raw.empty:
        # Convert any polygon stops/platforms to centroid point
        for idx, row in stops_raw.iterrows():
            geom = row.geometry
            if geom.geom_type != "Point":
                geom = geom.centroid
            name = row.get("name") if hasattr(row, "get") else None
            stops_rows.append({
                "osm_id": format_osm_id(idx),
                "name": str(name) if (name is not None and not pd.isna(name)) else None,
                "ref": None,
                "feature_type": "bus_stop",
                "geometry": geom,
            })
    print(f"Downloaded {len(stops_rows)} bus stop(s)")

    # 2. Fetch bus routes
    print("Fetching bus routes (route=bus) from OSM...")
    try:
        routes_raw = ox.features_from_polygon(poly, tags={"route": "bus"})
    except Exception as exc:
        print(b2lib.classify_overpass_error(exc, endpoint=args.endpoint))
        raise SystemExit(1)

    routes_rows = []
    if not routes_raw.empty:
        for idx, row in routes_raw.iterrows():
            geom = row.geometry
            if geom is None or geom.is_empty:
                continue
            name = row.get("name") if hasattr(row, "get") else None
            ref = row.get("ref") if hasattr(row, "get") else None
            routes_rows.append({
                "osm_id": format_osm_id(idx),
                "name": str(name) if (name is not None and not pd.isna(name)) else None,
                "ref": str(ref) if (ref is not None and not pd.isna(ref)) else None,
                "feature_type": "bus_route",
                "geometry": geom,
            })
    print(f"Downloaded {len(routes_rows)} bus route(s)")

    if not stops_rows and not routes_rows:
        raise SystemExit("OSM returned no transit data (0 bus stops and 0 bus routes found in study area). "
                         "No placeholder data generated.")

    all_features = stops_rows + routes_rows
    gdf = gpd.GeoDataFrame(all_features, crs="EPSG:4326")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(out_path, driver="GeoJSON")
    print(f"Saved {len(stops_rows)} stops and {len(routes_rows)} routes -> {out_path}")

    b2lib.register_source(
        "OSM transit (bus stops and routes)",
        "https://www.openstreetmap.org",
        "ODbL 1.0 (OpenStreetMap contributors)",
        "OSM live extract",
        str(out_path.relative_to(b2lib.REPO_ROOT) if out_path.is_relative_to(b2lib.REPO_ROOT) else out_path),
        f"{len(stops_rows)} stops, {len(routes_rows)} routes",
    )


if __name__ == "__main__":
    main()
