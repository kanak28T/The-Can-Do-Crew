"""B2 task B1.4/B1.5 (grid part): study polygon + H3 res-9 grid.

Lives at: urbanpulse/data/scripts/01_build_grid.py
Run from repo root:   python data/scripts/01_build_grid.py
Outputs: data/nagpur_study_polygon.geojson, data/nagpur_h3_res9.geojson
Needs:   pip install h3 shapely geopandas osmnx   (network access to OSM Nominatim)

If OSM returns the district instead of the city (area check below), draw the city
boundary at geojson.io, save it as data/nagpur_study_polygon.geojson and re-run with
--polygon data/nagpur_study_polygon.geojson. Agree on ONE polygon file with Alpha.
"""
import argparse

import b2lib


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--polygon", help="use this GeoJSON instead of geocoding OSM")
    ap.add_argument("--max-area-km2", type=float, default=500.0,
                    help="abort above this (NMC city is roughly 220 km2; the district is ~10,000)")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    import geopandas as gpd
    from shapely.ops import unary_union

    out_poly = b2lib.DATA / "nagpur_study_polygon.geojson"
    if args.polygon:
        gdf = gpd.read_file(args.polygon).to_crs(4326)
        source = f"local file {args.polygon}"
    else:
        import osmnx as ox
        gdf = ox.geocode_to_gdf("Nagpur, Maharashtra, India")
        gdf = gdf[gdf.geometry.type.isin(["Polygon", "MultiPolygon"])]
        if gdf.empty:
            raise SystemExit("Nominatim returned no polygon. Draw the boundary at geojson.io and use --polygon.")
        gdf = gdf.iloc[[0]]
        print("OSM match:", gdf["display_name"].iloc[0])
        source = "OSM Nominatim via OSMnx"

    area = float(gdf.to_crs(b2lib.UTM_EPSG).area.iloc[0]) / 1e6 if len(gdf) == 1 else \
        float(gdf.to_crs(b2lib.UTM_EPSG).area.sum()) / 1e6
    print(f"study polygon area: {area:.1f} km2")
    if area > args.max_area_km2 and not args.force:
        raise SystemExit(f"{area:.0f} km2 looks like the district, not the city. "
                         "Draw the city boundary and pass --polygon (or --force).")

    poly = unary_union(gdf.geometry)
    assert poly.geom_type in ("Polygon", "MultiPolygon"), poly.geom_type
    if not args.polygon:
        gdf[["geometry"]].to_file(out_poly, driver="GeoJSON")

    cells = b2lib.polygon_to_cells(poly, b2lib.H3_RES)
    assert cells, "no cells produced"
    assert len(set(cells)) == len(cells)
    b2lib.write_json(b2lib.DATA / "nagpur_h3_res9.geojson", b2lib.build_grid_geojson(cells))
    print(f"{len(cells)} r9 cells -> data/nagpur_h3_res9.geojson")
    print("Tell B1 + Alpha: property name is 'cell' (resolution: 'resolution', parent r8 computed via h3.cell_to_parent). Verify the cell count.")

    b2lib.register_source("Study polygon (NMC boundary)",
                          "https://nominatim.openstreetmap.org" if not args.polygon else args.polygon,
                          "ODbL 1.0 (OpenStreetMap contributors)" if not args.polygon else "own work",
                          "OSM live extract" if not args.polygon else "hand-drawn",
                          "data/nagpur_study_polygon.geojson", f"{source}; area {area:.1f} km2")
    b2lib.register_source("H3 res-9 grid", "https://h3geo.org", "derived (Apache-2.0 h3 library)",
                          "generated", "data/nagpur_h3_res9.geojson", f"{len(cells)} cells")


if __name__ == "__main__":
    main()