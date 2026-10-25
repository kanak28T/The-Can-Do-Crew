"""B2 tasks B1.6 + B2.2: VIIRS night-time lights (NASA VNP46A4, yearly) sampled per H3 cell.

Lives at: urbanpulse/data/scripts/03_viirs_per_cell.py
Output:   data/viirs_per_cell.json   (+ raw file under data/raw_viirs/, do not commit it)

Caveat to document in the README: a VNP46A4 pixel is 15 arc-seconds (~0.2 km2 here) while an
r9 cell is ~0.105 km2, so neighbouring cells share pixels and some cells contain no pixel
centre. We sample the pixel under each cell centroid and record pixel_id. The light proxy is
effectively coarser than the grid. Never fill missing values by hand.

Needs a free NASA Earthdata account (earthaccess.login() prompts, or uses ~/.netrc / env vars).
pip install earthaccess h5py numpy h3

Usage
  1. python data/scripts/03_viirs_per_cell.py --download --year 2024
  2. python data/scripts/03_viirs_per_cell.py --discover --file data/raw_viirs/<file>.h5
  3. python data/scripts/03_viirs_per_cell.py --file data/raw_viirs/<file>.h5 --year 2024
       (add --layer "<path>" --qual "<path>" if auto-detection refuses to guess)
"""
import argparse
from pathlib import Path

import numpy as np

import b2lib

PRODUCT = "VNP46A4"
BASE = "NearNadir_Composite_Snow_Free"
NAGPUR_BBOX = (78.9, 21.0, 79.3, 21.3)  # west, south, east, north


def download(year):
    import earthaccess
    earthaccess.login()
    res = earthaccess.search_data(short_name=PRODUCT, temporal=(f"{year}-01-01", f"{year}-12-31"),
                                  bounding_box=NAGPUR_BBOX)
    print(len(res), "granule(s) found (expect 1 for a single tile). Downloading...")
    out = Path(b2lib.DATA / "raw_viirs")
    out.mkdir(parents=True, exist_ok=True)
    files = earthaccess.download(res, str(out))
    for f in files:
        print("  ", f)
    b2lib.register_source("NASA Black Marble VNP46A4", "https://www.earthdata.nasa.gov/data/catalog/lpcloud-vnp46a4-001",
                          "NASA open data (cite per LP DAAC guidance)", f"year {year}",
                          "data/raw_viirs/", "downloaded via earthaccess")


def list_datasets(h5):
    import h5py
    found = []
    h5.visititems(lambda n, o: found.append((n, o)) if isinstance(o, h5py.Dataset) else None)
    return found


def attr_scalar(ds, key):
    if key not in ds.attrs:
        return None
    v = np.atleast_1d(ds.attrs[key])
    return v[0].item() if hasattr(v[0], "item") else v[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--download", action="store_true")
    ap.add_argument("--discover", action="store_true")
    ap.add_argument("--file")
    ap.add_argument("--year", type=int)
    ap.add_argument("--layer")
    ap.add_argument("--qual")
    args = ap.parse_args()

    if args.download:
        if not args.year:
            raise SystemExit("--year required")
        return download(args.year)
    if not args.file:
        raise SystemExit("--file required (or use --download)")

    import h5py
    with h5py.File(args.file, "r") as h:
        dsets = list_datasets(h)
        if args.discover:
            print("root attributes mentioning bounds/tile (confirm tile h25v06 here):")
            for k, v in h.attrs.items():
                if any(s in k.lower() for s in ("bound", "tile", "horizontal", "vertical")):
                    print("  ", k, "=", v)
            for n, o in dsets:
                if BASE in n:
                    print(f"{n}  shape={o.shape} dtype={o.dtype} scale={attr_scalar(o, 'scale_factor')} "
                          f"fill={attr_scalar(o, '_FillValue')}")
            return

        layer, qual = args.layer, args.qual
        if not layer:
            exact = [n for n, _ in dsets if n.split("/")[-1] == BASE]
            quals = [n for n, _ in dsets if n.split("/")[-1].startswith(BASE) and "Quality" in n.split("/")[-1]]
            if len(exact) != 1 or len(quals) != 1:
                raise SystemExit(f"Cannot auto-pick layers (found value={exact}, quality={quals}). "
                                 "Run --discover and pass --layer/--qual.")
            layer, qual = exact[0], quals[0]
        if not qual:
            raise SystemExit("--qual required when --layer is given")

        ds = h[layer]
        ntl = ds[()]
        q = h[qual][()]
        fill, scale, offset = attr_scalar(ds, "_FillValue"), attr_scalar(ds, "scale_factor"), attr_scalar(ds, "add_offset")
        if ntl.shape != (2400, 2400):
            raise SystemExit(f"unexpected tile shape {ntl.shape}; expected (2400, 2400)")

    tile = b2lib.parse_tile(args.file)
    lon_min, lat_max = b2lib.tile_origin(*tile)
    print(f"tile h{tile[0]:02d}v{tile[1]:02d}: lon {lon_min}..{lon_min + 10}, lat {lat_max - 10}..{lat_max}")
    cells = b2lib.load_grid_cells()
    recs, summary = b2lib.sample_viirs(cells, ntl, q, tile, fill=fill,
                                       scale=1.0 if scale is None else scale,
                                       offset=0.0 if offset is None else offset,
                                       product=PRODUCT, year=args.year)
    meta = {"product": PRODUCT, "year": args.year, "layer": layer, "quality_layer": qual,
            "tile": f"h{tile[0]:02d}v{tile[1]:02d}", "fill_value": fill, "scale_factor": scale,
            "add_offset": offset, "method": "pixel under H3 cell centroid; no imputation",
            "note": "pixel (15 arc-sec, ~0.2 km2) is coarser than an r9 cell (~0.105 km2); cells can share pixels",
            **summary}
    b2lib.write_json(b2lib.DATA / "viirs_per_cell.json", {"meta": meta, "cells": recs})
    print(summary)
    if summary["n_missing"]:
        print("WARNING: missing cells are left as missing. Do not fill by hand.")


if __name__ == "__main__":
    main()