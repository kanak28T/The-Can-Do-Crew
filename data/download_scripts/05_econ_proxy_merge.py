"""B2 task B2.4: merge the economic proxies into one `economic_constraint` score per cell.

Lives at: urbanpulse/data/scripts/05_econ_proxy_merge.py
Reads:    data/nagpur_h3_res9.geojson, data/viirs_per_cell.json, data/building_density_per_cell.json
Writes:   data/econ_proxy_per_cell.json   <- the file Alpha reads in A2.6

The combination is a HEURISTIC, not a validated index (see b2lib.merge_econ). Weights and the
sign of the density term are flags so the team can document or change them.

    python data/scripts/05_econ_proxy_merge.py [--w-light 0.6 --w-built 0.4 --built-sign 1]
"""
import argparse

import b2lib


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--w-light", type=float, default=0.6)
    ap.add_argument("--w-built", type=float, default=0.4)
    ap.add_argument("--built-sign", type=int, choices=(-1, 1), default=1)
    args = ap.parse_args()

    cells = b2lib.load_grid_cells()
    viirs = b2lib.read_json(b2lib.DATA / "viirs_per_cell.json")
    bld = b2lib.read_json(b2lib.DATA / "building_density_per_cell.json")
    merged = b2lib.merge_econ(cells, viirs["cells"], bld["cells"], args.w_light, args.w_built, args.built_sign)
    meta = {"name": "economic_constraint", "range": "0..1, higher = more constrained",
            "status": "HEURISTIC, not a validated income or poverty index",
            "rule": "(w_light*(1-pct(viirs)) + w_built*sign_adjusted_pct(built_fraction)) / sum(weights present)",
            "w_light": args.w_light, "w_built": args.w_built, "built_sign": args.built_sign,
            "inputs": {"viirs": viirs["meta"], "buildings": bld["meta"]}}
    b2lib.write_json(b2lib.DATA / "econ_proxy_per_cell.json", {"meta": meta, "cells": merged})
    n_missing = sum(1 for v in merged.values() if v["missing"])
    print(f"{len(merged)} cells; {n_missing} with no usable component (left as null) -> data/econ_proxy_per_cell.json")


if __name__ == "__main__":
    main()