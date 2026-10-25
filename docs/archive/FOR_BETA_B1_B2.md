# Beta Team (B1 + B2) — Unblocked. Start Now.

Phase 0 is complete on priyanshu branch. Pull it and start.

---

## What A1 (Priyanshu) has done — your inputs are ready

- `contracts/event_schema.py` — the schema you import ✅
- `api/main.py` — server running on port 8000 ✅
- `GET /sse/events` — SSE stream ready for your map ✅
- `POST /ingest` — accepts events, returns `{cell, risk, ...}` ✅
- `contracts/scenario_format.yaml` — already done by A2 ✅
- `contracts/ground_truth_format.yaml` — already done by A2 ✅

## What A2 (Kanak) has done — also your inputs

- Full `CanonicalEvent` schema with enums (Domain, EventType, SourceType)
- PII rejection with Aadhaar, phone, email patterns
- Scenario format + ground truth format YAML

---

## Step 1: Pull priyanshu branch (B1 + B2, do this NOW)

```bash
git fetch --all
git checkout priyanshu
```

---

## B1 Tasks (React + MapLibre frontend)

### B1.1 — Scaffold React app (30 min)

```bash
cd web
npm create vite@latest . -- --template react
npm install
npm install maplibre-gl @deck.gl/core h3-js
```

### B1.2 — Map shell with H3 hexagons (90 min)

File: `web/src/App.tsx`

```tsx
import { useEffect, useRef, useState } from 'react'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'

// Risk colour map
const RISK_COLOUR: Record<string, string> = {
  low:     '#22c55e',  // green
  medium:  '#eab308',  // yellow
  high:    '#ef4444',  // red
  unknown: '#9ca3af',  // grey
}

function riskLabel(risk: number): string {
  if (risk < 0.4)  return 'low'
  if (risk < 0.65) return 'medium'
  if (risk >= 0.65) return 'high'
  return 'unknown'
}

// Colour hex cells as GeoJSON
function buildHexLayer(cells: Record<string, number>) {
  // cells = { h3_cell: risk_score }
  // Convert to GeoJSON features — h3-js cellToBoundary
  const h3 = (window as any).h3
  const features = Object.entries(cells).map(([cell, risk]) => {
    const boundary = h3.cellToBoundary(cell)
    return {
      type: 'Feature',
      properties: { cell, risk, label: riskLabel(risk), colour: RISK_COLOUR[riskLabel(risk)] },
      geometry: {
        type: 'Polygon',
        coordinates: [[...boundary.map(([lat, lng]: number[]) => [lng, lat]), boundary.map(([lat, lng]: number[]) => [lng, lat])[0]]]
      }
    }
  })
  return { type: 'FeatureCollection', features }
}

const API = 'http://localhost:8000'

export default function App() {
  const mapRef = useRef<HTMLDivElement>(null)
  const mapInstance = useRef<maplibregl.Map | null>(null)
  const [cells, setCells] = useState<Record<string, number>>({})
  const [connected, setConnected] = useState(false)

  // Init map
  useEffect(() => {
    if (!mapRef.current) return
    const map = new maplibregl.Map({
      container: mapRef.current,
      style: 'https://demotiles.maplibre.org/style.json',
      center: [79.0882, 21.1458],  // Nagpur
      zoom: 11,
    })
    mapInstance.current = map
    map.on('load', () => {
      map.addSource('cells', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } })
      map.addLayer({
        id: 'cells-fill',
        type: 'fill',
        source: 'cells',
        paint: { 'fill-color': ['get', 'colour'], 'fill-opacity': 0.6 }
      })
      map.addLayer({
        id: 'cells-outline',
        type: 'line',
        source: 'cells',
        paint: { 'line-color': '#fff', 'line-width': 0.5, 'line-opacity': 0.4 }
      })
    })
    return () => map.remove()
  }, [])

  // Update map when cells change
  useEffect(() => {
    const map = mapInstance.current
    if (!map || !map.getSource('cells')) return
    const source = map.getSource('cells') as maplibregl.GeoJSONSource
    source.setData(buildHexLayer(cells) as any)
  }, [cells])

  // Subscribe to SSE
  useEffect(() => {
    const es = new EventSource(`${API}/sse/events`)
    es.addEventListener('connected', () => setConnected(true))
    es.addEventListener('cell_updated', (e: MessageEvent) => {
      const data = JSON.parse(e.data)
      setCells(prev => ({ ...prev, [data.cell]: data.risk }))
    })
    es.onerror = () => setConnected(false)
    return () => es.close()
  }, [])

  return (
    <div style={{ width: '100vw', height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Map */}
      <div ref={mapRef} style={{ flex: 1 }} />

      {/* Footer — NEVER remove this */}
      <div style={{ padding: '6px 12px', background: '#1e293b', color: '#94a3b8', fontSize: 12, display: 'flex', justifyContent: 'space-between' }}>
        <span>Baseline data: real (OSM, WorldPop, Census 2011) | Live feeds: <strong style={{color:'#fbbf24'}}>SIMULATED</strong></span>
        <span style={{ color: connected ? '#22c55e' : '#ef4444' }}>{connected ? '● Live' : '○ Reconnecting…'}</span>
      </div>
    </div>
  )
}
```

### B1.3 — Connect to SSE and update cell colours

Already done in App.tsx above — EventSource connects to `http://localhost:8000/sse/events`.

When A1 posts an event to `/ingest`, SSE fires → cell turns red/yellow/green automatically. No refresh.

### B1.9 — Footer (already in App.tsx)

The footer "Baseline data: real | Live feeds: SIMULATED" is in the component.

---

## B2 Tasks (Data pipeline + simulators)

### B2.1 — Download Nagpur ward boundaries (30 min)

File: `data/download_scripts/download_wards.py`

```python
import json, requests, os

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Nagpur ward boundaries (admin_level=10 under Nagpur Municipal Corporation)
QUERY = """
[out:json][timeout:60];
area["name"="Nagpur"]["admin_level"="6"]->.nagpur;
(
  relation["admin_level"="10"](area.nagpur);
  way["admin_level"="10"](area.nagpur);
);
out geom;
"""

print("Downloading Nagpur ward boundaries from OSM Overpass...")
r = requests.post(OVERPASS_URL, data={"data": QUERY}, timeout=120)
r.raise_for_status()

os.makedirs("data", exist_ok=True)
with open("data/nagpur_wards_raw.json", "w") as f:
    json.dump(r.json(), f)

print(f"✅ Saved raw OSM data: {len(r.json().get('elements', []))} elements")
print("Run the H3 grid script next.")
```

Run: `python data/download_scripts/download_wards.py`

### B2.2 — Generate H3 res-9 grid for Nagpur (45 min)

File: `data/download_scripts/generate_h3_grid.py`

```python
import json, h3, os

# Nagpur bounding box (approximate)
# lat: 20.85 - 21.35, lon: 78.85 - 79.35
NAGPUR_BBOX = {
    "min_lat": 20.85, "max_lat": 21.35,
    "min_lon": 78.85, "max_lon": 79.35
}

# Create a GeoJSON polygon for the bbox
bbox_polygon = {
    "type": "Polygon",
    "coordinates": [[
        [NAGPUR_BBOX["min_lon"], NAGPUR_BBOX["min_lat"]],
        [NAGPUR_BBOX["max_lon"], NAGPUR_BBOX["min_lat"]],
        [NAGPUR_BBOX["max_lon"], NAGPUR_BBOX["max_lat"]],
        [NAGPUR_BBOX["min_lon"], NAGPUR_BBOX["max_lat"]],
        [NAGPUR_BBOX["min_lon"], NAGPUR_BBOX["min_lat"]],
    ]]
}

# Get all H3 res-9 cells covering the bbox
cells = list(h3.geo_to_cells(bbox_polygon, res=9))
print(f"H3 res-9 cells in Nagpur bbox: {len(cells)}")

# Convert to GeoJSON
features = []
for cell in cells:
    boundary = h3.cell_to_boundary(cell)
    features.append({
        "type": "Feature",
        "properties": {"cell": cell, "resolution": 9},
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [lng, lat] for lat, lng in boundary
            ] + [[boundary[0][1], boundary[0][0]]]]
        }
    })

geojson = {"type": "FeatureCollection", "features": features}

os.makedirs("data", exist_ok=True)
with open("data/nagpur_h3_res9.geojson", "w") as f:
    json.dump(geojson, f)

print(f"✅ Saved: data/nagpur_h3_res9.geojson ({len(cells)} cells)")
print("Share this path with B1 — they load it in the map.")
```

Run: `python data/download_scripts/generate_h3_grid.py`

**This file is the shared grid. Commit it. A1 + B1 both use it.**

---

## Integration Test (Phase 0 exit — DO THIS NOW)

1. A1's server is running on `http://localhost:8000`
2. B1: run `npm run dev` in `web/` — opens map in browser
3. B2: run the generate_h3_grid.py script, then B1 loads `nagpur_h3_res9.geojson` in map
4. Post a test event from any terminal:

```bash
# Windows PowerShell
$body = '{"event_id":"550e8400-e29b-41d4-a716-446655440099","domain":"power","event_type":"blackout","entity_id":"feeder-F12","h3_cell":"890c1d2cf37ffff","severity":1.0,"source_type":"official","source_reliability":0.9,"event_timestamp":"2026-10-25T14:30:00Z","ingestion_timestamp":"2026-10-25T14:30:02Z","parse_confidence":1.0}'
Invoke-RestMethod -Uri "http://localhost:8000/ingest" -Method POST -Body $body -ContentType "application/json"
```

5. Watch the cell turn red on the map. No refresh.

**That is Phase 0 exit. ✅**

---

## What's next after integration test passes

Tell A1 (Priyanshu) — he starts Phase 1 (Dijkstra + cell state engine).
B2 starts B1.5 (VIIRS download) and B1.6 (power domain simulator).
B1 starts the sector panel (click cell → side panel).
