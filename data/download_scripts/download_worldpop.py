"""
Download WorldPop India 100m population raster and clip to Nagpur bounding box.

Source : https://www.worldpop.org/geodata/listing?id=29
Licence: CC BY 4.0 — must credit WorldPop in the app footer.

Usage:
    python data/download_scripts/download_worldpop.py

Output:
    data/worldpop_nagpur.tif   — clipped GeoTIFF (population count per 100 m pixel)
"""

import os
import urllib.request
from pathlib import Path

# ---------------------------------------------------------------------------
# Nagpur bounding box (WGS84)
# SW corner: 78.96°E, 20.87°N   NE corner: 79.22°E, 21.25°N
# Padded slightly so cells on the boundary are fully covered.
#
# ⚠️  VERIFY this bbox after Sanvi (B2) downloads nagpur_wards.geojson:
#     import geopandas as gpd
#     wards = gpd.read_file("data/nagpur_wards.geojson")
#     print(wards.total_bounds)   # (min_lon, min_lat, max_lon, max_lat)
# Update NAGPUR_BBOX to match, then re-run this script.
# ---------------------------------------------------------------------------
NAGPUR_BBOX = (78.90, 20.80, 79.30, 21.35)   # (min_lon, min_lat, max_lon, max_lat)

# WorldPop constrained individual countries, UN-adjusted, 2020
# India 100m resolution — ppp = persons per pixel
WORLDPOP_URL = (
    "https://data.worldpop.org/GIS/Population/Global_2000_2020_Constrained/"
    "2020/BSGM/IND/ind_ppp_2020_UNadj_constrained.tif"
)

DATA_DIR = Path(__file__).parent.parent          # …/data/
OUT_FULL = DATA_DIR / "worldpop_india_full.tif"
OUT_CLIP = DATA_DIR / "worldpop_nagpur.tif"


def download(url: str, dest: Path) -> None:
    if dest.exists():
        print(f"[skip] {dest.name} already exists.")
        return
    print(f"[download] {url}")
    print("  This file is ~600 MB. It will take a few minutes on a fast connection.")
    urllib.request.urlretrieve(url, dest, reporthook=_progress)
    print()


def _progress(count, block_size, total_size):
    pct = min(count * block_size * 100 // total_size, 100)
    print(f"\r  {pct}% ", end="", flush=True)


def clip_to_nagpur(src: Path, dst: Path, bbox: tuple) -> None:
    """Clip the full India raster to the Nagpur bbox using rasterio."""
    try:
        import rasterio
        from rasterio.mask import mask
        from shapely.geometry import box
        import json
    except ImportError:
        print(
            "[error] rasterio and shapely are required to clip the raster.\n"
            "        Install: pip install rasterio shapely\n"
            "        Then re-run this script."
        )
        return

    if dst.exists():
        print(f"[skip] {dst.name} already clipped.")
        return

    min_lon, min_lat, max_lon, max_lat = bbox
    geom = box(min_lon, min_lat, max_lon, max_lat)
    geom_json = [json.loads(geom.__geo_interface__.__str__().replace("'", '"'))]

    print(f"[clip] Clipping to Nagpur bbox {bbox} …")
    with rasterio.open(src) as dataset:
        out_image, out_transform = mask(dataset, geom_json, crop=True)
        out_meta = dataset.meta.copy()
        out_meta.update(
            driver="GTiff",
            height=out_image.shape[1],
            width=out_image.shape[2],
            transform=out_transform,
            compress="lzw",
        )
        with rasterio.open(dst, "w", **out_meta) as dest_file:
            dest_file.write(out_image)
    print(f"[done] Saved clipped raster → {dst}")


if __name__ == "__main__":
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    download(WORLDPOP_URL, OUT_FULL)
    clip_to_nagpur(OUT_FULL, OUT_CLIP, NAGPUR_BBOX)
    print("\nAttribution (required by CC BY 4.0):")
    print("  WorldPop (www.worldpop.org) — School of Geography and Environmental Science,")
    print("  University of Southampton. India 100m Population, 2020.")
