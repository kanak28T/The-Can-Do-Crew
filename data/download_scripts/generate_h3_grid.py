"""
Generate H3 res-9 grid for Nagpur bounding box.
Output: data/nagpur_h3_res9.geojson
Run: python data/download_scripts/generate_h3_grid.py
"""
import json, h3, os, sys

NAGPUR_POLYGON = {
    "type": "Polygon",
    "coordinates": [[
        [78.85, 20.85],
        [79.35, 20.85],
        [79.35, 21.35],
        [78.85, 21.35],
        [78.85, 20.85],
    ]]
}

def generate():
    cells = list(h3.geo_to_cells(NAGPUR_POLYGON, res=9))
    print(f"H3 res-9 cells: {len(cells)}")

    features = []
    for cell in cells:
        boundary = h3.cell_to_boundary(cell)
        coords = [[lng, lat] for lat, lng in boundary]
        coords.append(coords[0])   # close ring
        features.append({
            "type": "Feature",
            "properties": {"cell": cell, "resolution": 9},
            "geometry": {"type": "Polygon", "coordinates": [coords]}
        })

    geojson = {"type": "FeatureCollection", "features": features}
    os.makedirs("data", exist_ok=True)
    with open("data/nagpur_h3_res9.geojson", "w") as f:
        json.dump(geojson, f)
    print(f"✅ Saved data/nagpur_h3_res9.geojson ({len(cells)} cells)")
    return cells

if __name__ == "__main__":
    generate()
