"""
Aggregate WorldPop 100m raster to H3 res-9 cells.
Output: data/population_per_cell.json  →  {h3_cell: population_count}

Owner  : Kanak (A2) — Day 2
Input  : data/worldpop_nagpur.tif  (from download_worldpop.py)
         data/nagpur_h3_res9.geojson  (from generate_h3_grid.py)
Output : data/population_per_cell.json  {h3_cell: population_count}

Usage:
    python data/download_scripts/worldpop_to_cells.py
"""

import json
import os
import sys
from pathlib import Path

DATA_DIR    = Path(__file__).parent.parent
RASTER_PATH = DATA_DIR / "worldpop_nagpur.tif"
GRID_PATH   = DATA_DIR / "nagpur_h3_res9.geojson"
OUT_PATH    = DATA_DIR / "population_per_cell.json"


def aggregate_worldpop_to_h3(
    raster_path: str | Path,
    h3_cells: list[str],
) -> dict[str, float]:
    """
    For each H3 cell, sum WorldPop pixels that fall inside it.
    """
    try:
        import h3
        import numpy as np
        import rasterio
        from rasterio.mask import mask as rio_mask
    except ImportError as exc:
        print(f"⚠ Optional dependency missing ({exc}) — returning mock data.")
        return {cell: 5000.0 for cell in h3_cells}

    result: dict[str, float] = {}

    with rasterio.open(raster_path) as src:
        for cell in h3_cells:
            boundary = h3.cell_to_boundary(cell)
            ring = [[lng, lat] for lat, lng in boundary]
            ring.append(ring[0])
            polygon = {
                "type": "Polygon",
                "coordinates": [ring],
            }
            try:
                out_image, _ = rio_mask(src, [polygon], crop=True, nodata=0)
                pop = float(np.nansum(out_image[out_image > 0]))
                result[cell] = round(pop, 2)
            except Exception:
                result[cell] = 0.0

    return result


def _mock_population(h3_cells: list[str]) -> dict[str, float]:
    """Return uniform mock population (5 000/cell) for testing."""
    return {cell: 5000.0 for cell in h3_cells}


def main(
    grid_path: Path = GRID_PATH,
    raster_path: Path = RASTER_PATH,
    output_path: Path = OUT_PATH,
) -> None:
    if not grid_path.exists():
        print(f"❌ H3 grid not found: {grid_path}")
        print("   Run: python data/download_scripts/generate_h3_grid.py")
        sys.exit(1)

    with open(grid_path) as f:
        grid = json.load(f)
    cells: list[str] = [feat["properties"]["cell"] for feat in grid["features"]]
    print(f"Grid loaded: {len(cells)} H3 res-9 cells")

    if not raster_path.exists():
        print(f"⚠ WorldPop raster not found ({raster_path}) — using mock data (5 000/cell)")
        pop_data = _mock_population(cells)
    else:
        print(f"Aggregating WorldPop raster: {raster_path}")
        pop_data = aggregate_worldpop_to_h3(raster_path, cells)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(pop_data, f, indent=2)

    total_pop = sum(pop_data.values())
    print(f"✅ Saved {output_path} ({len(pop_data)} cells, total population ≈ {total_pop:,.0f})")


if __name__ == "__main__":
    main()
