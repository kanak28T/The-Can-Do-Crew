"""
Download WorldPop India 100m population raster and clip to Nagpur bounding box.

Owner  : Kanak (A2) — Day 1
Source : https://www.worldpop.org/geodata/listing?id=29
Licence: CC BY 4.0 — attribution required in app footer and README.
Output : data/worldpop_nagpur.tif  (clipped GeoTIFF, population count per 100 m pixel)

Usage:
    pip install rasterio shapely
    python data/download_scripts/download_worldpop.py
"""

import urllib.request
from pathlib import Path

# ⚠️  Verify this bbox after Sanvi downloads nagpur_wards.geojson:
#     import geopandas as gpd
#     print(gpd.read_file("data/nagpur_wards.geojson").total_bounds)
#     Then update NAGPUR_BBOX and re-run.
NAGPUR_BBOX = (78.90, 20.80, 79.30, 21.35)  # (min_lon, min_lat, max_lon, max_lat)

WORLDPOP_URL = (
    "https://data.worldpop.org/GIS/Population/Global_2000_2020_Constrained/"
    "2020/BSGM/IND/ind_ppp_2020_UNadj_constrained.tif"
)

DATA_DIR  = Path(__file__).parent.parent
OUT_FULL  = DATA_DIR / "worldpop_india_full.tif"
OUT_CLIP  = DATA_DIR / "worldpop_nagpur.tif"


def _progress(count, block_size, total_size):
    pct = min(count * block_size * 100 // total_size, 100)
    print(f"\r  {pct}%", end="", flush=True)


def download(url: str, dest: Path) -> None:
    if dest.exists():
        print(f"[skip] {dest.name} already exists.")
        return
    print(f"[download] {url}")
    print("  ~600 MB — takes a few minutes on a fast connection.")
    urllib.request.urlretrieve(url, dest, reporthook=_progress)
    print()


def clip_to_nagpur(src: Path, dst: Path, bbox: tuple) -> None:
    if dst.exists():
        print(f"[skip] {dst.name} already clipped.")
        return
    try:
        import rasterio
        from rasterio.mask import mask
        from shapely.geometry import box, mapping
    except ImportError:
        print("[error] pip install rasterio shapely")
        return

    geom = [mapping(box(*bbox))]
    print(f"[clip] Clipping to Nagpur bbox {bbox} ...")
    with rasterio.open(src) as ds:
        out_image, out_transform = mask(ds, geom, crop=True)
        out_meta = {**ds.meta, "driver": "GTiff",
                    "height": out_image.shape[1],
                    "width": out_image.shape[2],
                    "transform": out_transform,
                    "compress": "lzw"}
        with rasterio.open(dst, "w", **out_meta) as f:
            f.write(out_image)
    print(f"[done] {dst}")


if __name__ == "__main__":
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    download(WORLDPOP_URL, OUT_FULL)
    clip_to_nagpur(OUT_FULL, OUT_CLIP, NAGPUR_BBOX)
    print("\nAttribution (CC BY 4.0):")
    print("  WorldPop (worldpop.org) — University of Southampton, India 100m Population 2020.")
