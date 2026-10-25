"""B2 tasks B2.5 / B3.1 / B3.5: authored (SYNTHETIC) mapping tables + optional OSM hospitals.

Lives at: urbanpulse/data/scripts/06_mapping_tables.py
Reads:    data/nagpur_h3_res9.geojson, Alpha's data/population_per_cell.json (A2.2)
Writes:   data/mapping_tables/feeder_cells.json      (20 synthetic feeders)
          data/mapping_tables/pump_zone_cells.json   (10 synthetic pump zones + feeder dependency)
          data/mapping_tables/route_cells.json       (6 SYNTHETIC bus routes, ids "1".."6")
          data/mapping_tables/hospital_cells.json    (only with --osm)

All of these are SIMULATED infrastructure and say so in their meta block. The demo phrase
"Bus route 4 suspended" needs route "4" to exist: it does here. If OSM has real route
relations with ref=4 you may prefer them; run the --osm discovery print and decide.

    python data/scripts/06_mapping_tables.py                # no network
    python data/scripts/06_mapping_tables.py --osm          # hospitals/clinics + bus-route refs from OSM
"""
import argparse

import b2lib

SYN = "SYNTHETIC: authored by the team, not real infrastructure"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pop", default=str(b2lib.DATA / "population_per_cell.json"),
                    help="Alpha's population file (flat {cell: pop}, or wrapped)")
    ap.add_argument("--osm", action="store_true")
    ap.add_argument("--endpoint", help="Overpass API endpoint URL (or set OVERPASS_URL env var)")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    cells = b2lib.load_grid_cells()
    cellset = set(cells)
    try:
        pop = b2lib.extract_population(b2lib.read_json(args.pop))
    except FileNotFoundError:
        print(f"WARNING: {args.pop} not found; clustering unweighted. Re-run once Alpha commits A2.2.")
        pop = {}

    feeders = b2lib.cluster_cells(cells, pop, 20, seed=args.seed, prefix="FDR")
    pumps = b2lib.cluster_cells(cells, pop, 10, seed=args.seed + 1, prefix="PMP")
    deps = b2lib.pump_zone_dependencies(pumps, feeders)
    routes = b2lib.synthetic_routes(cells, seed=args.seed)

    for name, table in (("feeders", feeders), ("pump zones", pumps),
                        ("routes", {k: v["cells"] for k, v in routes.items()})):
        b2lib.assert_mapping_in_grid(table, cellset)
    covered = {c for cs in feeders.values() for c in cs}
    assert covered == cellset, "every cell must belong to exactly one feeder"

    m = b2lib.MAPPING
    b2lib.write_json(m / "feeder_cells.json", {"meta": {"note": SYN, "n": 20, "method": "population-weighted KMeans on cell centroids", "seed": args.seed}, "feeders": feeders})
    b2lib.write_json(m / "pump_zone_cells.json", {"meta": {"note": SYN, "n": 10, "method": "population-weighted KMeans", "seed": args.seed + 1}, "pump_zones": {k: {"cells": v, "feeder": deps[k]} for k, v in pumps.items()}})
    b2lib.write_json(m / "route_cells.json", {"meta": {"note": SYN + " (straight-line routes between far-apart cells; NOT OSM)", "seed": args.seed}, "routes": routes})
    print(f"feeders={len(feeders)} pump_zones={len(pumps)} routes={len(routes)} -> data/mapping_tables/")

    if args.osm:
        osm_part(cells, cellset, endpoint=args.endpoint)


def osm_part(cells, cellset, endpoint=None):
    import geopandas as gpd
    import osmnx as ox
    from shapely.ops import unary_union

    b2lib.configure_osmnx(endpoint=endpoint)
    area = unary_union(gpd.read_file(b2lib.DATA / "nagpur_study_polygon.geojson").to_crs(4326).geometry)
    try:
        h = ox.features_from_polygon(area, tags={"amenity": ["hospital", "clinic"]})
    except Exception as exc:
        print(b2lib.classify_overpass_error(exc, endpoint=endpoint))
        raise SystemExit(1)
    hu = h.to_crs(b2lib.UTM_EPSG)
    cen = hu.geometry.centroid.to_crs(4326)
    rows = []
    for idx, (_, r), pt in zip(h.index, h.iterrows(), cen):
        cell = b2lib.h3.latlng_to_cell(pt.y, pt.x, b2lib.H3_RES)
        if cell not in cellset:
            continue
        osm_id = "/".join(str(x) for x in idx) if isinstance(idx, tuple) else str(idx)
        rows.append({"osm_id": osm_id, "name": r.get("name") if hasattr(r, "get") else None,
                     "amenity": r.get("amenity"), "h3_cell": cell})
    rows.sort(key=lambda x: x["osm_id"])
    b2lib.write_json(b2lib.MAPPING / "hospital_cells.json",
                     {"meta": {"source": "OpenStreetMap amenity=hospital|clinic", "license": "ODbL 1.0",
                               "caveat": "cross-check with HOTOSM/HDX exports; OSM coverage varies"}, "hospitals": rows})
    print(f"{len(rows)} hospitals/clinics inside the grid -> data/mapping_tables/hospital_cells.json")

    try:
        rt = ox.features_from_polygon(area, tags={"route": "bus"})
        refs = sorted({str(x) for x in rt["ref"].dropna()}) if "ref" in rt.columns else []
        print(f"OSM bus route relations with a ref tag: {len(refs)} -> {refs[:40]}")
        print("Is there a real route '4'? ", "4" in refs, "(if not, keep the synthetic route and label it)")
    except Exception as e:  # no route relations is a normal outcome
        print("No OSM bus routes found or query failed:", e)

    b2lib.register_source("OSM hospitals/clinics", "https://www.openstreetmap.org", "ODbL 1.0 (OpenStreetMap contributors)",
                          "OSM live extract", "data/mapping_tables/hospital_cells.json", "")


if __name__ == "__main__":
    main()