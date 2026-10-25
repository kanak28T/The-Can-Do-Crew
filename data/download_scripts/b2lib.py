"""Shared helpers for Team Beta (B2) data scripts.

Lives at: urbanpulse/data/scripts/b2lib.py

Pure logic only (no network). Network/IO lives in the numbered scripts next to it,
so everything here can be unit-tested (tests/b2/).

Requires h3 >= 4.0  (pip install h3).
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import math
import os
import random
import re
import time
from pathlib import Path

import h3
import numpy as np

DEFAULT_OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# data/scripts/b2lib.py -> parents[0]=scripts, [1]=data, [2]=repo root
REPO_ROOT = Path(__file__).resolve().parents[2]
DATA = REPO_ROOT / "data"
MAPPING = DATA / "mapping_tables"
METADATA = REPO_ROOT / "metadata"

H3_RES = 9
PARENT_RES = 8
UTM_EPSG = 32644  # UTM 44N covers 78E-84E; Nagpur is ~79.09E
AVG_R9_AREA_M2 = 105_332.5  # H3 average hexagon area at res 9 (0.1053 km2)

SOURCE_COLUMNS = ["name", "url", "access_date", "license", "vintage", "local_file", "notes"]


# --------------------------------------------------------------------------- provenance
def register_source(name, url, license, vintage, local_file, notes=""):
    """Append one row to metadata/source_register.csv (creates it with the header)."""
    METADATA.mkdir(parents=True, exist_ok=True)
    path = METADATA / "source_register.csv"
    is_new = not path.exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if is_new:
            w.writerow(SOURCE_COLUMNS)
        w.writerow([name, url, dt.date.today().isoformat(), license, vintage, local_file, notes])


def write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=None, separators=(",", ":"), sort_keys=True)


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# --------------------------------------------------------------------------- grid
def polygon_to_cells(geo, res=H3_RES):
    """geo: anything with __geo_interface__ (a shapely Polygon/MultiPolygon) or a GeoJSON dict."""
    fn = getattr(h3, "geo_to_cells", None)
    if fn is None:
        raise RuntimeError("h3 >= 4.0 required (h3.geo_to_cells not found). pip install -U h3")
    return sorted(fn(geo, res))


def cell_ring_lnglat(cell):
    """Closed GeoJSON ring. h3 returns (lat, lng); GeoJSON wants (lng, lat)."""
    ring = [(lng, lat) for lat, lng in h3.cell_to_boundary(cell)]
    ring.append(ring[0])
    return ring


def build_grid_geojson(cells):
    feats = []
    for c in cells:
        feats.append({
            "type": "Feature",
            "properties": {"h3_cell": c, "h3_parent_r8": h3.cell_to_parent(c, PARENT_RES)},
            "geometry": {"type": "Polygon", "coordinates": [cell_ring_lnglat(c)]},
        })
    return {"type": "FeatureCollection", "features": feats}


def load_grid_cells(path=None):
    path = Path(path) if path else DATA / "nagpur_h3_res9.geojson"
    gj = read_json(path)
    cells = [f["properties"]["h3_cell"] for f in gj["features"]]
    if len(set(cells)) != len(cells):
        raise ValueError("duplicate h3_cell in grid file")
    return sorted(cells)


def geojson_bounds(gj):
    """(west, south, east, north) of any GeoJSON dict, without shapely."""
    xs, ys = [], []

    def walk(c):
        if c and isinstance(c[0], (int, float)):
            xs.append(c[0]); ys.append(c[1])
        else:
            for x in c:
                walk(x)

    def geoms(o):
        t = o.get("type")
        if t == "FeatureCollection":
            for f in o["features"]:
                yield from geoms(f)
        elif t == "Feature":
            yield from geoms(o["geometry"])
        elif t == "GeometryCollection":
            for g in o["geometries"]:
                yield from geoms(g)
        else:
            yield o

    for g in geoms(gj):
        walk(g["coordinates"])
    return min(xs), min(ys), max(xs), max(ys)


# --------------------------------------------------------------------------- VIIRS (VNP46A4)
_TILE_RE = re.compile(r"\.h(\d{2})v(\d{2})\.")


def parse_tile(filename):
    m = _TILE_RE.search(str(filename))
    if not m:
        raise ValueError(f"no .hXXvYY. tile id in file name: {filename}")
    return int(m.group(1)), int(m.group(2))


def tile_origin(h, v):
    """Black Marble tiles are 10x10 deg: upper-left corner (lon_min, lat_max)."""
    return -180.0 + 10.0 * h, 90.0 - 10.0 * v


def pixel_index(lat, lng, lon_min, lat_max, n=2400, size_deg=10.0):
    """Row/col of the pixel containing (lat, lng), or None if outside the tile.
    15 arc-second grid: size_deg / n = 1/240 degree per pixel."""
    px = size_deg / n
    row = int(math.floor((lat_max - lat) / px))
    col = int(math.floor((lng - lon_min) / px))
    if 0 <= row < n and 0 <= col < n:
        return row, col
    return None


def sample_viirs(cells, ntl, qual, tile_hv, fill=None, scale=1.0, offset=0.0,
                 product="VNP46A4", year=None):
    """Sample the pixel under each cell centroid. Never fills or imputes values.

    ntl/qual: 2D arrays (qual may be None). Returns (records, summary).
    A missing pixel is reported as missing=True with viirs=None.
    """
    n = ntl.shape[0]
    lon_min, lat_max = tile_origin(*tile_hv)
    recs, pixels, n_missing = {}, set(), 0
    for c in cells:
        lat, lng = h3.cell_to_latlng(c)
        idx = pixel_index(lat, lng, lon_min, lat_max, n=n)
        if idx is None:
            recs[c] = {"viirs": None, "quality_flag": None, "pixel_id": None, "missing": True,
                       "reason": "outside_tile", "product": product, "year": year}
            n_missing += 1
            continue
        r, col = idx
        raw = ntl[r, col]
        bad = (isinstance(raw, (float, np.floating)) and np.isnan(raw)) or (fill is not None and raw == fill)
        q = None if qual is None else int(qual[r, col])
        pixels.add(idx)
        if bad:
            n_missing += 1
        recs[c] = {"viirs": None if bad else float(raw) * scale + offset,
                   "quality_flag": q, "pixel_id": f"{r}_{col}", "missing": bool(bad),
                   "reason": "fill_value" if bad else None, "product": product, "year": year}
    summary = {"n_cells": len(cells), "n_unique_pixels": len(pixels), "n_missing": n_missing,
               "cells_per_pixel": round(len(cells) / max(len(pixels), 1), 3)}
    return recs, summary


# --------------------------------------------------------------------------- buildings
def aggregate_buildings(points_latlng, areas_m2, cellset=None, res=H3_RES):
    """points_latlng: iterable of (lat, lng) building centroids; areas in m2.
    Returns (per_cell, n_outside_grid)."""
    out, outside = {}, 0
    for (lat, lng), a in zip(points_latlng, areas_m2):
        c = h3.latlng_to_cell(lat, lng, res)
        if cellset is not None and c not in cellset:
            outside += 1
            continue
        d = out.setdefault(c, {"building_count": 0, "footprint_m2": 0.0})
        d["building_count"] += 1
        d["footprint_m2"] += float(a)
    for d in out.values():
        d["built_fraction"] = min(d["footprint_m2"] / AVG_R9_AREA_M2, 1.0)
    return out, outside


# --------------------------------------------------------------------------- economic proxy
def percentile_ranks(values):
    """values: dict key -> float. Tie-aware rank in [0,1]. Returns dict."""
    keys = list(values)
    if not keys:
        return {}
    arr = np.array([values[k] for k in keys], dtype=float)
    n = len(arr)
    if n == 1:
        return {keys[0]: 0.5}
    s = np.sort(arr)
    lo = np.searchsorted(s, arr, side="left")
    hi = np.searchsorted(s, arr, side="right")
    pct = (lo + hi - 1) / 2.0 / (n - 1)
    return dict(zip(keys, pct.tolist()))


def merge_econ(cells, viirs, buildings, w_light=0.6, w_built=0.4, built_sign=+1):
    """HEURISTIC economic-constraint score in [0,1] (higher = more constrained).

    NOT a validated income index.
      light component = 1 - percentile(VIIRS)          (darker -> more constrained)
      built component = percentile(built_fraction)     (built_sign=+1: denser -> more constrained;
                                                         use -1 to flip)
    A component that is missing for a cell is dropped and the remaining weight is
    renormalised; components_used records which ones counted. If none -> None.
    """
    light = {c: r["viirs"] for c, r in viirs.items() if r.get("viirs") is not None}
    built = {c: buildings.get(c, {}).get("built_fraction", 0.0) for c in cells}
    p_light, p_built = percentile_ranks(light), percentile_ranks(built)
    out = {}
    for c in cells:
        comps, wsum, acc = [], 0.0, 0.0
        if c in p_light:
            acc += w_light * (1.0 - p_light[c]); wsum += w_light; comps.append("viirs")
        if built:
            b = p_built[c] if built_sign >= 0 else 1.0 - p_built[c]
            acc += w_built * b; wsum += w_built; comps.append("built_fraction")
        out[c] = {
            "economic_constraint": (acc / wsum) if wsum > 0 else None,
            "components_used": comps,
            "viirs": viirs.get(c, {}).get("viirs"),
            "built_fraction": buildings.get(c, {}).get("built_fraction", 0.0),
            "no_osm_buildings": c not in buildings,
            "missing": wsum == 0,
        }
    return out


# --------------------------------------------------------------------------- mapping tables (SYNTHETIC)
def extract_population(obj):
    """Accept {'cell': pop} or {'population': {...}} or {'cells': {'cell': pop or {'population': x}}}."""
    if "population" in obj and isinstance(obj["population"], dict):
        obj = obj["population"]
    elif "cells" in obj and isinstance(obj["cells"], dict):
        obj = obj["cells"]
    out = {}
    for c, v in obj.items():
        out[c] = float(v["population"] if isinstance(v, dict) else v)
    return out


def cluster_cells(cells, pop, n, seed=0, prefix="FDR"):
    """Population-weighted KMeans over cell centroids -> {id: sorted cell list}.
    Clusters are named north-to-south, then west-to-east, so ids are stable."""
    from sklearn.cluster import KMeans

    cells = sorted(cells)
    if n > len(cells):
        raise ValueError("more clusters than cells")
    ll = np.array([h3.cell_to_latlng(c) for c in cells], dtype=float)
    w = np.array([pop.get(c, 0.0) + 1.0 for c in cells], dtype=float)
    km = KMeans(n_clusters=n, random_state=seed, n_init=10).fit(ll, sample_weight=w)
    order = sorted(range(n), key=lambda i: (-km.cluster_centers_[i][0], km.cluster_centers_[i][1]))
    rank = {old: new for new, old in enumerate(order)}
    out = {f"{prefix}-{i + 1:02d}": [] for i in range(n)}
    for c, lab in zip(cells, km.labels_):
        out[f"{prefix}-{rank[int(lab)] + 1:02d}"].append(c)
    return {k: sorted(v) for k, v in out.items()}


def pump_zone_dependencies(pump_zones, feeders):
    """Each pump zone depends on the feeder that overlaps it most (tie -> lowest id)."""
    owner = {c: f for f, cs in feeders.items() for c in cs}
    dep = {}
    for pz, cs in pump_zones.items():
        counts = {}
        for c in cs:
            f = owner.get(c)
            if f:
                counts[f] = counts.get(f, 0) + 1
        dep[pz] = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
    return dep


def synthetic_routes(cells, seed=0, n_routes=6, samples=80, min_sep_deg=0.06):
    """SYNTHETIC bus routes ('1'..'n'): straight line between two far-apart grid cells,
    sampled and converted to the ordered, de-duplicated cells that exist in the grid.
    These are NOT OSM routes and must be labelled as such."""
    rng = random.Random(seed)
    cells = sorted(cells)
    cellset = set(cells)
    latlng = {c: h3.cell_to_latlng(c) for c in cells}
    routes = {}
    for i in range(1, n_routes + 1):
        sep = min_sep_deg
        for attempt in range(400):
            a, b = rng.choice(cells), rng.choice(cells)
            d = math.hypot(latlng[a][0] - latlng[b][0], latlng[a][1] - latlng[b][1])
            if d >= sep:
                break
            if attempt and attempt % 100 == 0:
                sep *= 0.7  # grid smaller than expected: relax
        (la, ga), (lb, gb) = latlng[a], latlng[b]
        seq = []
        for s in range(samples + 1):
            t = s / samples
            c = h3.latlng_to_cell(la + (lb - la) * t, ga + (gb - ga) * t, H3_RES)
            if c in cellset and (not seq or seq[-1] != c):
                seq.append(c)
        routes[str(i)] = {"cells": seq, "synthetic": True, "origin_cell": a, "destination_cell": b}
    return routes


def assert_mapping_in_grid(mapping, cellset):
    """Run on EVERY mapping table before saving."""
    bad = [c for cs in mapping.values() for c in cs if c not in cellset]
    if bad:
        raise AssertionError(f"{len(bad)} mapped cells are not in the H3 grid, e.g. {bad[:3]}")
    return True


# --------------------------------------------------------------------------- wards (Overpass discovery)
def summarise_overpass_tags(payload):
    """payload: parsed Overpass JSON from an `out tags;` query."""
    from collections import Counter

    items = []
    for el in payload.get("elements", []):
        t = el.get("tags", {})
        items.append({"osm_id": f"{el.get('type', 'relation')}/{el.get('id')}",
                      "name": t.get("name"), "admin_level": t.get("admin_level"), "ref": t.get("ref")})
    return {"count": len(items),
            "by_admin_level": dict(Counter(i["admin_level"] for i in items)),
            "items": sorted(items, key=lambda i: (str(i["admin_level"]), str(i["name"])))}


# --------------------------------------------------------------------------- Overpass API helpers
def resolve_overpass_endpoint(endpoint: str | None = None) -> str:
    """Resolve Overpass endpoint from argument, OVERPASS_URL env var, or default.
    Default: https://overpass-api.de/api/interpreter
    """
    if endpoint and str(endpoint).strip():
        return str(endpoint).strip()
    env_url = os.environ.get("OVERPASS_URL", "").strip()
    if env_url:
        return env_url
    return DEFAULT_OVERPASS_URL


def overpass_post(
    query: str,
    endpoint: str | None = None,
    retries: int = 3,
    backoff_factor: float = 2.0,
    initial_delay: float = 1.0,
):
    """Send an HTTP POST query to Overpass API with timeout=(15, 120) and exponential backoff.

    Endpoint resolution:
      1. endpoint argument
      2. OVERPASS_URL environment variable
      3. default: https://overpass-api.de/api/interpreter
    """
    import requests

    raw_ep = resolve_overpass_endpoint(endpoint)
    url = raw_ep.rstrip("/")
    if url.endswith("/api"):
        url += "/interpreter"

    delay = initial_delay
    last_exc = None

    for attempt in range(1, retries + 1):
        try:
            resp = requests.post(url, data={"data": query}, timeout=(15, 120))
            if resp.status_code in (429, 502, 503, 504):
                if attempt < retries:
                    time.sleep(delay)
                    delay *= backoff_factor
                    continue
            resp.raise_for_status()
            return resp
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
            last_exc = exc
            if attempt < retries:
                time.sleep(delay)
                delay *= backoff_factor
                continue
            raise
        except requests.exceptions.HTTPError as exc:
            last_exc = exc
            if resp.status_code in (429, 502, 503, 504) and attempt < retries:
                time.sleep(delay)
                delay *= backoff_factor
                continue
            raise

    if last_exc is not None:
        raise last_exc


def configure_osmnx(endpoint: str | None = None, timeout: int = 300):
    """Configure osmnx overpass endpoint and longer timeout.

    Note: osmnx appends '/interpreter' internally to settings.overpass_url,
    so we set settings.overpass_url to the base URL (without /interpreter).
    """
    import osmnx as ox

    ep = resolve_overpass_endpoint(endpoint)
    base_url = ep
    if base_url.endswith("/interpreter"):
        base_url = base_url[:-len("/interpreter")].rstrip("/")

    ox.settings.overpass_url = base_url
    ox.settings.requests_timeout = timeout
    return ox.settings


def classify_overpass_error(exc: Exception, endpoint: str | None = None) -> str:
    """Format a clear, actionable message distinguishing network blocked vs server busy."""
    import requests

    ep = resolve_overpass_endpoint(endpoint)
    msg = str(exc)
    err_type = type(exc).__name__

    is_connect_error = (
        isinstance(exc, (requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError))
        or "ConnectTimeout" in err_type
        or "ConnectionError" in err_type
        or "ConnectionRefused" in msg
        or "Failed to establish a new connection" in msg
        or ("timed out" in msg.lower() and "connect" in msg.lower())
    )
    is_server_busy = (
        isinstance(exc, requests.exceptions.ReadTimeout)
        or "ReadTimeout" in err_type
        or "504" in msg
        or "502" in msg
        or "429" in msg
        or getattr(getattr(exc, "response", None), "status_code", None) in (429, 502, 503, 504)
    )

    if is_connect_error:
        return (
            f"[NETWORK BLOCKED / CONNECTION FAILED]\n"
            f"Endpoint: {ep}\n"
            f"Error: {exc}\n\n"
            f"Diagnosis: Network connection to the Overpass API server failed or timed out.\n"
            f"Your network/ISP or firewall is likely blocking connections to overpass-api.de.\n\n"
            f"Actionable Fix: Provide an alternative working Overpass mirror via --endpoint or OVERPASS_URL.\n"
            f"Official public instances from OpenStreetMap Wiki (https://wiki.openstreetmap.org/wiki/Overpass_API):\n"
            f"  --endpoint https://overpass.kumi.systems/api/interpreter\n"
            f"  --endpoint https://maps.mail.ru/osm/tools/overpass/api/interpreter\n"
            f"  --endpoint https://overpass.private.coffee/api/interpreter"
        )
    elif is_server_busy:
        return (
            f"[SERVER BUSY / OVERLOADED]\n"
            f"Endpoint: {ep}\n"
            f"Error: {exc}\n\n"
            f"Diagnosis: The Overpass API server accepted the connection but timed out processing the query\n"
            f"or returned rate-limit / gateway errors (429 / 502 / 504).\n\n"
            f"Actionable Fix: Wait a minute before retrying, reduce your query bounding box, or switch to\n"
            f"an alternate mirror via --endpoint or OVERPASS_URL."
        )
    else:
        return (
            f"[OVERPASS REQUEST FAILED]\n"
            f"Endpoint: {ep}\n"
            f"Error: {exc}\n\n"
            f"Diagnosis: Query failed or returned invalid response.\n"
            f"Actionable Fix: Check your query syntax or try a different endpoint via --endpoint."
        )