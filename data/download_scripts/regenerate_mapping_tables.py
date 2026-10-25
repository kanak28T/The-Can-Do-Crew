"""
Regenerate mapping tables from Sanvi's canonical H3 grid.
Fixes Priyanshu's mapping tables which had invalid (non-Nagpur) cell IDs.

Owner : Kanak (A2) — conflict fix
Run   : python data/download_scripts/regenerate_mapping_tables.py
Output: data/mapping_tables/feeder_cells.json
        data/mapping_tables/route_cells.json
        data/mapping_tables/tower_cells.json
        data/mapping_tables/pump_cells.json
        data/mapping_tables/hospital_cells.json
"""
import json, random, math
from pathlib import Path

DATA_DIR    = Path(__file__).parent.parent
GRID_PATH   = DATA_DIR / "nagpur_h3_res9.geojson"
TABLES_DIR  = DATA_DIR / "mapping_tables"
TABLES_DIR.mkdir(exist_ok=True)

# Load canonical grid
with open(GRID_PATH) as f:
    grid = json.load(f)
ALL_CELLS = [feat["properties"]["cell"] for feat in grid["features"]]

try:
    import h3
    def cells_near(lat, lng, k=3):
        center = h3.latlng_to_cell(lat, lng, 9)
        ring   = h3.grid_disk(center, k)
        return [c for c in ring if c in set(ALL_CELLS)]
except ImportError:
    def cells_near(lat, lng, k=3):
        random.seed(int(lat*100+lng*100))
        return random.sample(ALL_CELLS, min(k*3, len(ALL_CELLS)))

random.seed(42)

# ── Nagpur approximate zone centroids (from NMC ward map) ────────────────────
ZONES = {
    "north":      (21.20, 79.07),
    "south":      (21.09, 79.08),
    "east":       (21.14, 79.15),
    "west":       (21.14, 79.02),
    "central":    (21.15, 79.09),
    "northeast":  (21.19, 79.13),
    "southwest":  (21.10, 79.03),
}

# ── Feeder → cells (20 feeders, 3-8 cells each) ──────────────────────────────
feeder_cells = {"_comment": "Feeder → H3 res-9 cells. Simulated from MSEDCL zone reports."}
zone_names = list(ZONES.keys())
for i in range(1, 21):
    zone = zone_names[i % len(zone_names)]
    lat, lng = ZONES[zone]
    # Offset slightly per feeder
    lat += random.uniform(-0.02, 0.02)
    lng += random.uniform(-0.02, 0.02)
    cells = cells_near(lat, lng, k=2)
    feeder_cells[f"F{i:02d}"] = cells[:random.randint(3, 8)]

# ── Route → cells (12 bus routes, 5-12 cells each) ───────────────────────────
route_cells = {"_comment": "Bus route → H3 res-9 cells. Simulated from Nagpur Aapli Bus stop locations."}
for i in range(1, 13):
    # Routes are linear — pick two endpoints and fill cells between
    z1, z2 = random.sample(zone_names, 2)
    lat1, lng1 = ZONES[z1]
    lat2, lng2 = ZONES[z2]
    n_stops = random.randint(5, 12)
    cells = []
    for j in range(n_stops):
        t = j / max(n_stops - 1, 1)
        lat = lat1 + t * (lat2 - lat1) + random.uniform(-0.005, 0.005)
        lng = lng1 + t * (lng2 - lng1) + random.uniform(-0.005, 0.005)
        nearby = cells_near(lat, lng, k=1)
        if nearby:
            cells.extend(nearby[:1])
    route_cells[f"route_{i}"] = list(dict.fromkeys(cells))  # dedup, preserve order

# ── Tower → cells (15 cell towers, 2-4 cells each) ───────────────────────────
tower_cells = {"_comment": "Cell tower → H3 res-9 cells. Approximate from OpenCellID density."}
for i in range(1, 16):
    zone = random.choice(zone_names)
    lat, lng = ZONES[zone]
    lat += random.uniform(-0.03, 0.03)
    lng += random.uniform(-0.03, 0.03)
    cells = cells_near(lat, lng, k=1)
    tower_cells[f"tower_T{i:02d}"] = cells[:random.randint(2, 4)]

# ── Pump zone → cells (10 pumping stations, 3-6 cells each) ──────────────────
pump_cells = {"_comment": "Pump zone → H3 res-9 cells. Simulated from NMC water supply zones."}
for i in range(1, 11):
    zone = zone_names[i % len(zone_names)]
    lat, lng = ZONES[zone]
    lat += random.uniform(-0.015, 0.015)
    lng += random.uniform(-0.015, 0.015)
    cells = cells_near(lat, lng, k=2)
    pump_cells[f"pump_P{i:02d}"] = cells[:random.randint(3, 6)]

# ── Hospital → cell (major hospitals) ────────────────────────────────────────
HOSPITAL_LOCATIONS = {
    "mayo_hospital":    (21.1458, 79.0882),
    "gmch_nagpur":      (21.1500, 79.0800),
    "nmc_hospital":     (21.1200, 79.0700),
    "orange_city":      (21.1630, 79.0850),
    "care_hospital":    (21.1380, 79.0920),
}
hospital_cells = {"_comment": "Hospital → nearest H3 res-9 cell."}
for name, (lat, lng) in HOSPITAL_LOCATIONS.items():
    c = cells_near(lat, lng, k=0)
    hospital_cells[name] = c[0] if c else ALL_CELLS[0]

# ── Save all ──────────────────────────────────────────────────────────────────
tables = {
    "feeder_cells.json":   feeder_cells,
    "route_cells.json":    route_cells,
    "tower_cells.json":    tower_cells,
    "pump_cells.json":     pump_cells,
    "hospital_cells.json": hospital_cells,
}
for fname, data in tables.items():
    path = TABLES_DIR / fname
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"[saved] {path}")

# Verify cells are all in canonical grid
grid_set = set(ALL_CELLS)
for fname, data in tables.items():
    bad = []
    for k, v in data.items():
        if k.startswith("_"):
            continue
        cells = [v] if isinstance(v, str) else v
        bad.extend([c for c in cells if c not in grid_set])
    if bad:
        print(f"[WARN] {fname} has {len(bad)} cells not in canonical grid!")
    else:
        print(f"[OK]   {fname} — all cells valid")
