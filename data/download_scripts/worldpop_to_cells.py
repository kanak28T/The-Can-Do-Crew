"""
Aggregate WorldPop 100m raster to H3 res-9 cells.

Owner  : Kanak (A2) — Day 2
Input  : data/worldpop_nagpur.tif  (from download_worldpop.py)
         data/nagpur_h3_res9.geojson  (from Sanvi B2 — must exist first)
Output : data/population_per_cell.json  {h3_cell: population_count}

Usage:
    python data/download_scripts/worldpop_to_cells.py
"""

import json
import os
from pathlib import Path

DATA_DIR    = Path(__file__).parent.parent
RASTER_PATH = DATA_DIR / "worldpop_nagpur.tif"
GRID_PATH   = DATA_DIR / "nagpur_h3_res9.geojson"
OUT_PATH    = DATA_DIR / "population_per_cell.json"


def aggregate(raster_path: Path, cells: list[str]) -> dict[str, float]:
    """Sum WorldPop pixels inside each H3 res-9 cell polygon."""
    try:
        import rasterio
        import numpy as np
        import h3
        from rasterio.mask import mask as rio_mask
    except ImportError:
        print("[warn] rasterio/numpy/h3 not installed — using mock population (5000 per cell)")
        return {cell: 5000.0 for cell in cells}

    result = {}
    with rasterio.open(raster_path) as src:
        for cell in cells:
            boundary = h3.cell_to_boundary(cell)  # list of (lat, lng)
            polygon = {
                "type": "Polygon",
                "coordinates": [
                    [[lng, lat] for lat, lng in boundary]
                    + [[boundary[0][1], boundary[0][0]]]  # close the ring
                ],
            }
            try:
                out_image, _ = rio_mask(src, [polygon], crop=True, nodata=0)
                pop = float(np.nansum(out_image[out_image > 0]))
            except Exception:
                pop = 0.0
            result[cell] = round(pop, 2)
    return result


if __name__ == "__main__":
    if not GRID_PATH.exists():
        print(f"[error] {GRID_PATH} not found — Sanvi (B2) must commit nagpur_h3_res9.geojson first.")
        raise SystemExit(1)

    with open(GRID_PATH) as f:
        grid = json.load(f)
    cells = [feat["properties"]["cell"] for feat in grid["features"]]
    print(f"[info] {len(cells)} H3 res-9 cells loaded.")

    if not RASTER_PATH.exists():
        print("[warn] WorldPop raster not downloaded yet — using mock data (5000 per cell).")
        pop_data = {cell: 5000.0 for cell in cells}
    else:
        print(f"[aggregate] Summing WorldPop pixels per cell ...")
        pop_data = aggregate(RASTER_PATH, cells)

    with open(OUT_PATH, "w") as f:
        json.dump(pop_data, f, indent=2)
    print(f"[done] {OUT_PATH} — {len(pop_data)} cells.")
