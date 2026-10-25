"""B2 task B1.4: ward / prabhag display layer (DISPLAY LABELS ONLY, never used for scoring).

Lives at: urbanpulse/data/scripts/02_wards.py

Step 1 (discovery, small):  python data/scripts/02_wards.py
    Lists what OSM actually has (names, admin_level, count) for the study-polygon bbox
    and writes metadata/ward_discovery.json. Do NOT validate against a fixed ward count:
    Nagpur's 2026 election used 38 prabhags (151 councillors); a 2022 draft had 52;
    the 2011 layer has other numbers. OSM may carry any of them.

Step 2 (geometry):          python data/scripts/02_wards.py --export --levels 10
    Exports only the admin levels you choose to data/nagpur_wards.geojson.
    If nothing usable exists, skip the ward overlay and note why in the source register.

Needs: pip install requests geopandas osmnx   (Step 2 also needs shapely)
"""
import argparse

import b2lib


def discovery_query(bbox, levels):
    w, s, e, n = bbox
    lv = "|".join(str(x) for x in levels)
    # Overpass bbox order is (south, west, north, east)
    return (f'[out:json][timeout:60];'
            f'relation["boundary"="administrative"]["admin_level"~"^({lv})$"]({s},{w},{n},{e});'
            f'out tags;')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--levels", default="9,10", help="comma-separated OSM admin_level values")
    ap.add_argument("--export", action="store_true")
    ap.add_argument("--endpoint", help="Overpass API endpoint URL (or set OVERPASS_URL env var)")
    args = ap.parse_args()
    levels = [x.strip() for x in args.levels.split(",") if x.strip()]

    poly_path = b2lib.DATA / "nagpur_study_polygon.geojson"
    if not poly_path.exists():
        raise SystemExit("Run 01_build_grid.py first (need data/nagpur_study_polygon.geojson).")

    if not args.export:
        bbox = b2lib.geojson_bounds(b2lib.read_json(poly_path))
        q = discovery_query(bbox, levels)
        try:
            r = b2lib.overpass_post(q, endpoint=args.endpoint)
        except Exception as exc:
            print(b2lib.classify_overpass_error(exc, endpoint=args.endpoint))
            raise SystemExit(1)
        summary = b2lib.summarise_overpass_tags(r.json())
        b2lib.write_json(b2lib.METADATA / "ward_discovery.json", summary)
        print("admin_level counts:", summary["by_admin_level"], "| total:", summary["count"])
        for it in summary["items"][:60]:
            print(" ", it["admin_level"], it["name"], it["osm_id"])
        print("Pick which levels look like prabhags/wards, then re-run with --export --levels N")
        return

    import geopandas as gpd
    import osmnx as ox
    from shapely.ops import unary_union

    b2lib.configure_osmnx(endpoint=args.endpoint)
    poly = unary_union(gpd.read_file(poly_path).to_crs(4326).geometry)
    try:
        g = ox.features_from_polygon(poly, tags={"boundary": "administrative"})
    except Exception as exc:
        print(b2lib.classify_overpass_error(exc, endpoint=args.endpoint))
        raise SystemExit(1)
    g = g[g["admin_level"].astype(str).isin(levels)]
    g = g[g.geometry.type.isin(["Polygon", "MultiPolygon"])]
    if g.empty:
        raise SystemExit("No polygon admin boundaries at those levels. Drop the ward overlay; "
                         "record that in metadata/source_register.csv.")
    keep = [c for c in ("name", "admin_level", "ref") if c in g.columns]
    g = g.reset_index(drop=True)[keep + ["geometry"]]
    g.to_file(b2lib.DATA / "nagpur_wards.geojson", driver="GeoJSON")
    print(f"{len(g)} features -> data/nagpur_wards.geojson (count is whatever OSM has; not checked vs any fixed number)")
    b2lib.register_source("Ward/prabhag boundaries (display only)", "https://www.openstreetmap.org",
                          "ODbL 1.0 (OpenStreetMap contributors)", "OSM live extract",
                          "data/nagpur_wards.geojson", f"admin_level in {levels}; vintage unverified")


if __name__ == "__main__":
    main()