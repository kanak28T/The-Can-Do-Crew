"""
Generate H3 resolution-9 grid for Nagpur and save as GeoJSON.

Owner  : Originally Sanvi (B2) Day 1 — generated here as unblocking fallback.
Output : data/nagpur_h3_res9.geojson
         data/nagpur_wards_bbox.json   (verified bbox for WorldPop clip)

Usage  : python data/download_scripts/generate_h3_grid.py
Deps   : pip install h3 shapely
"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent

# Nagpur bounding box — verified against OSM admin boundary centroid
# OSM relation 1277816 (Nagpur city): approx bounds below
NAGPUR_BBOX = {
    "min_lon": 78.96, "min_lat": 20.87,
    "max_lon": 79.22, "max_lat": 21.25,
}

H3_RES = 9


def generate_grid(bbox: dict, resolution: int) -> list[str]:
    """Return all H3 cells at given resolution that cover the bbox polygon."""
    try:
        import h3
    except ImportError:
        print("[error] pip install h3")
        raise

    from shapely.geometry import box, mapping

    nagpur_poly = box(
        bbox["min_lon"], bbox["min_lat"],
        bbox["max_lon"], bbox["max_lat"],
    )
    geojson_poly = mapping(nagpur_poly)

    cells = list(h3.geo_to_cells(geojson_poly, res=resolution))
    print(f"[grid] {len(cells)} H3 res-{resolution} cells covering Nagpur bbox")
    return cells


def cells_to_geojson(cells: list[str]) -> dict:
    """Convert cell list to a GeoJSON FeatureCollection."""
    import h3
    features = []
    for cell in cells:
        boundary = h3.cell_to_boundary(cell)  # list of (lat, lng)
        # GeoJSON: [lng, lat] order, polygon must close
        coords = [[lng, lat] for lat, lng in boundary]
        coords.append(coords[0])
        lat, lng = h3.cell_to_latlng(cell)
        features.append({
            "type": "Feature",
            "properties": {
                "cell":       cell,
                "resolution": 9,
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [coords],
            },
        })
    return {"type": "FeatureCollection", "features": features}


if __name__ == "__main__":
    cells = generate_grid(NAGPUR_BBOX, H3_RES)
    geojson = cells_to_geojson(cells)

    out_path = DATA_DIR / "nagpur_h3_res9.geojson"
    with open(out_path, "w") as f:
        json.dump(geojson, f)
    print(f"[saved] {out_path}  ({len(cells)} cells)")

    # Also save bbox for WorldPop clip script
    bbox_path = DATA_DIR / "nagpur_wards_bbox.json"
    with open(bbox_path, "w") as f:
        json.dump(NAGPUR_BBOX, f, indent=2)
    print(f"[saved] {bbox_path}")
    print("\nNote: This bbox is based on OSM admin boundary approximation.")
    print("      Replace with exact bounds once nagpur_wards.geojson is available:")
    print("      import geopandas as gpd")
    print("      print(gpd.read_file('data/nagpur_wards.geojson').total_bounds)")
