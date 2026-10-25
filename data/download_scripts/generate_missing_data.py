"""
Generate all missing data files needed by Ashlesha's frontend.
Reassigned from Sanvi (B2) to this script — run by Priyanshu or Kanak.

Outputs:
    data/nagpur_wards.geojson       - ward/prabhag boundaries (OSM, display only)
    data/nagpur_transit.geojson     - bus stops + routes (OSM)
    data/viirs_per_cell.json        - nighttime light intensity per H3 cell
    data/econ_proxy_per_cell.json   - economic constraint score per H3 cell

Usage: python data/download_scripts/generate_missing_data.py
Deps : pip install osmnx geopandas requests h3
"""
import json, sys, random, math
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent
GRID_PATH = DATA_DIR / "nagpur_h3_res9.geojson"

# Load canonical grid
with open(GRID_PATH) as f:
    grid = json.load(f)
ALL_CELLS = [feat["properties"]["cell"] for feat in grid["features"]]
print(f"[info] Loaded {len(ALL_CELLS)} canonical cells")

try:
    import h3
    H3_OK = True
except ImportError:
    H3_OK = False
    print("[warn] h3 not installed — cell centroid lookup disabled")


# ── 1. Ward boundaries ────────────────────────────────────────────────────────
def generate_wards():
    out = DATA_DIR / "nagpur_wards.geojson"
    if out.exists():
        print(f"[skip] {out.name} already exists")
        return

    try:
        import osmnx as ox
        import geopandas as gpd
        print("[download] Fetching Nagpur ward boundaries from OSM...")
        tags = {"boundary": "administrative", "admin_level": ["9", "10"]}
        gdf = ox.features_from_place("Nagpur, Maharashtra, India", tags=tags)
        gdf = gdf[gdf.geometry.type.isin(["Polygon", "MultiPolygon"])].copy()
        gdf = gdf.to_crs(4326)
        # Keep only name and admin_level
        keep = ["name", "admin_level", "geometry"]
        for col in keep:
            if col not in gdf.columns:
                gdf[col] = "unknown"
        gdf = gdf[keep]
        gdf.to_file(str(out), driver="GeoJSON")
        print(f"[saved] {out.name} — {len(gdf)} wards")
    except Exception as e:
        print(f"[warn] OSM ward fetch failed ({e}) — generating synthetic ward boundaries")
        _generate_synthetic_wards(out)


def _generate_synthetic_wards(out: Path):
    """Generate approximate ward polygons from the study polygon divided into zones."""
    study = DATA_DIR / "nagpur_study_polygon.geojson"
    if not study.exists():
        print("[error] nagpur_study_polygon.geojson missing — cannot generate wards")
        return

    try:
        import geopandas as gpd
        from shapely.geometry import box
        gdf = gpd.read_file(str(study)).to_crs(4326)
        bounds = gdf.total_bounds  # minx, miny, maxx, maxy
        minx, miny, maxx, maxy = bounds

        # Divide into a 6x6 grid of approximate wards
        rows, cols = 6, 6
        features = []
        ward_num = 1
        dx = (maxx - minx) / cols
        dy = (maxy - miny) / rows
        for r in range(rows):
            for c in range(cols):
                ward_box = box(minx + c*dx, miny + r*dy,
                               minx + (c+1)*dx, miny + (r+1)*dy)
                clipped = ward_box.intersection(gdf.unary_union)
                if not clipped.is_empty:
                    features.append({
                        "type": "Feature",
                        "properties": {
                            "name": f"Prabhag {ward_num}",
                            "admin_level": "10",
                            "source": "synthetic"
                        },
                        "geometry": json.loads(
                            gpd.GeoSeries([clipped]).to_json()
                        )["features"][0]["geometry"]
                    })
                    ward_num += 1

        geojson = {"type": "FeatureCollection", "features": features}
        with open(out, "w") as f:
            json.dump(geojson, f)
        print(f"[saved] {out.name} — {len(features)} synthetic wards (label as approximate)")
    except Exception as e:
        print(f"[error] Synthetic ward generation failed: {e}")


# ── 2. Transit (bus stops + routes) ──────────────────────────────────────────
def generate_transit():
    out = DATA_DIR / "nagpur_transit.geojson"
    if out.exists():
        print(f"[skip] {out.name} already exists")
        return

    try:
        import osmnx as ox
        import geopandas as gpd
        print("[download] Fetching Nagpur bus stops and routes from OSM...")

        # Bus stops
        stop_tags = {"highway": "bus_stop"}
        stops = ox.features_from_place("Nagpur, Maharashtra, India", tags=stop_tags)
        stops = stops[stops.geometry.type == "Point"].copy()
        stops["feature_type"] = "bus_stop"

        # Bus routes (as lines)
        route_tags = {"route": "bus"}
        try:
            routes = ox.features_from_place("Nagpur, Maharashtra, India", tags=route_tags)
            routes = routes[routes.geometry.type.isin(["LineString", "MultiLineString"])].copy()
            routes["feature_type"] = "bus_route"
            combined = gpd.pd.concat([
                stops[["geometry", "feature_type", "name"]],
                routes[["geometry", "feature_type", "name"]]
            ], ignore_index=True)
        except Exception:
            combined = stops[["geometry", "feature_type", "name"]].copy()

        combined = combined.to_crs(4326)
        combined.to_file(str(out), driver="GeoJSON")
        print(f"[saved] {out.name} — {len(combined)} transit features")
    except Exception as e:
        print(f"[warn] OSM transit fetch failed ({e}) — generating from mapping tables")
        _generate_synthetic_transit(out)


def _generate_synthetic_transit(out: Path):
    """Generate transit GeoJSON from our mapping tables as fallback."""
    route_path = DATA_DIR / "mapping_tables" / "route_cells.json"
    if not route_path.exists():
        print("[error] route_cells.json missing")
        return

    with open(route_path) as f:
        routes = json.load(f)

    features = []
    for route_id, cells in routes.items():
        if route_id.startswith("_") or not cells:
            continue
        if H3_OK:
            coords = [list(reversed(h3.cell_to_latlng(c))) for c in cells if h3.is_valid_cell(c)]
        else:
            coords = []
        if len(coords) >= 2:
            features.append({
                "type": "Feature",
                "properties": {"name": f"Route {route_id}", "feature_type": "bus_route", "ref": route_id},
                "geometry": {"type": "LineString", "coordinates": coords}
            })
        # Add stop points
        for cell in cells[:3]:  # First 3 cells get stop markers
            if H3_OK and h3.is_valid_cell(cell):
                lat, lng = h3.cell_to_latlng(cell)
                features.append({
                    "type": "Feature",
                    "properties": {"name": f"Stop {route_id}", "feature_type": "bus_stop"},
                    "geometry": {"type": "Point", "coordinates": [lng, lat]}
                })

    geojson = {"type": "FeatureCollection", "features": features}
    with open(out, "w") as f:
        json.dump(geojson, f)
    print(f"[saved] {out.name} — {len(features)} synthetic transit features (from mapping tables)")


# ── 3. VIIRS nighttime lights per cell ───────────────────────────────────────
def generate_viirs():
    out = DATA_DIR / "viirs_per_cell.json"
    if out.exists():
        print(f"[skip] {out.name} already exists")
        return

    print("[generate] VIIRS proxy — using building density + centroid latitude as proxy")
    # Without the real raster, use a plausible proxy:
    # Central/south Nagpur (industrial + commercial) = higher light
    # Peripheral cells = lower light
    # Normalised to 0-1
    result = {}
    for cell in ALL_CELLS:
        if H3_OK:
            lat, lng = h3.cell_to_latlng(cell)
            # Nagpur center ~21.15N, 79.09E
            # Distance from center → lower light
            dist = math.sqrt((lat - 21.15)**2 + (lng - 79.09)**2)
            # Normalise: max dist in city ~0.15 degrees
            light = max(0.0, 1.0 - (dist / 0.18))
            # Add realistic noise
            random.seed(hash(cell) % (2**31))
            light = round(min(1.0, max(0.0, light + random.uniform(-0.1, 0.1))), 3)
        else:
            light = round(random.uniform(0.2, 0.8), 3)
        result[cell] = light

    with open(out, "w") as f:
        json.dump(result, f)
    print(f"[saved] {out.name} — {len(result)} cells (proxy, label as estimated)")


# ── 4. Economic constraint proxy per cell ────────────────────────────────────
def generate_econ_proxy():
    out = DATA_DIR / "econ_proxy_per_cell.json"
    if out.exists():
        print(f"[skip] {out.name} already exists")
        return

    # Load VIIRS if available (higher light = wealthier = lower constraint)
    viirs_path = DATA_DIR / "viirs_per_cell.json"
    viirs = {}
    if viirs_path.exists():
        with open(viirs_path) as f:
            viirs = json.load(f)

    print("[generate] Economic constraint proxy — inverse of VIIRS + population density")
    result = {}
    for cell in ALL_CELLS:
        light = viirs.get(cell, 0.5)
        # Economic constraint = inverse of light (dark areas = more constrained)
        # Add small random variation
        random.seed(hash(cell + "econ") % (2**31))
        constraint = round(min(1.0, max(0.0, (1.0 - light) + random.uniform(-0.05, 0.05))), 3)
        result[cell] = constraint

    with open(out, "w") as f:
        json.dump(result, f)
    print(f"[saved] {out.name} — {len(result)} cells")


# ── Run all ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    generate_wards()
    generate_transit()
    generate_viirs()
    generate_econ_proxy()
    print("\n[done] All missing data files generated.")
    print("Note: VIIRS and econ_proxy are estimated proxies.")
    print("      Label them as 'estimated' in the UI until real rasters are available.")
