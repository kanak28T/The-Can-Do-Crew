# UrbanPulse: Design Specification

**Document Version:** 1.0  
**Status:** Ready for Approval  
**Generated:** 2026-10-25

---

## 1. System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                       URBANPULSE SYSTEM                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  [DATA SOURCES]  [PRIVACY GATEWAY]  [ENGINE]      [API]  [FRONTEND]│
│      ↓                  ↓               ↓            ↓         ↓    │
│  • OSM roads      • PII scrubber  • Cell state    /ingest  React    │
│  • Simulators     • k-merge stub  • Decay        /sse      MapLibre │
│  • Real feeds     • Rate limiter  • Logistic     /zones    Causal   │
│                                   • Isolation    /dispatch  Dispatch│
│                                   • Drivers      /health    Privacy  │
│                                   • Planner      /eval              │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ APPEND-ONLY EVENT LOG (SQLite / Parquet)                     │  │
│  │ event_id, domain, type, cell, severity, timestamp, source_id│  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ FEDERATED LEARNING (Phase 6)                                 │  │
│  │ • 5 in-process zone nodes                                    │  │
│  │ • Custom FedAvg: noise, clipping, median agg                 │  │
│  │ • Shared coefficients only (β, γ ≥ 0)                        │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Data Models

### 2.1 Canonical Event Schema (Pydantic)

```python
# contracts/event_schema.py
class CanonicalEvent(BaseModel):
    event_id: str                    # UUID
    domain: Literal[
        "power", "transit", "water", "health", "comms", "road"
    ]
    event_type: str                  # e.g., "voltage_drop", "blackout", 
                                     # "route_suspension", "closure"
    entity_id: str                   # route/feeder/tower/road/pump ID
    h3_cell: str                     # H3 res-9 hex ID
    severity: float                  # 0.0 to 1.0
    source_type: Literal[
        "official", "sensor", "crowd", "anonymous"
    ]
    source_reliability: float        # 0.9 / 0.7 / 0.5 / 0.3 (static tier)
    event_timestamp: datetime        # UTC
    ingestion_timestamp: datetime    # UTC
    parse_confidence: float          # 0.0 to 1.0
    scenario_tag: Optional[str]      # For evaluation only; never in prod
    
    class Config:
        strict = True
        validate_assignment = True
```

**ADDED:** No `name`, `phone`, `device_id`, or free-text fields. Parser scrubs content before creating event.

### 2.2 Cell State Model

```python
# engine/cell_state.py
@dataclass
class CellState:
    h3_cell: str
    baseline_risk: float             # From historical baseline
    domain_stress: Dict[str, float]  # power, transit, water, health, comms, road
    confidence: float                # coverage × freshness × agreement
    last_updated: datetime
    source_count: int                # Number of sources in current window
    is_unknown: bool                 # True if confidence < 0.3 or stale >12h
    risk_interval: Tuple[float, float]  # (lower, upper) 90% bootstrap
    event_log: List[CanonicalEvent]  # Last 48h for replay

StateRegistry = Dict[str, CellState]  # Keyed by h3_cell
```

### 2.3 Risk Model: Logistic Scoring

```
Inputs per cell (all 0.0–1.0 with confidence):
  x_h = hospital_isolation (travel-time index)
  x_t = transit_loss (distance to nearest stop)
  x_p = power_stress (feeder voltage/outage rate)
  x_w = water_loss (pump/pressure failure)
  x_c = comms_loss (call-drop rate, tower down)
  x_r = road_stress (closure, congestion)

Baseline features (fixed per cell, updated daily):
  x_b_h = baseline hospital distance
  x_b_t = baseline transit deficit
  x_b_p = historical grid-failure rate
  x_b_e = economic-constraint proxy

Linear predictor:
  z = β₀ 
      + β₁·x_h + β₂·x_t + β₃·x_p + β₄·x_w + β₅·x_c + β₆·x_r
      + γ₁₂·(x_p × x_w)  [power×water cascade]
      + γ₁₃·(x_r × x_t)  [closure×transit loss]
      + γ₂₃·(x_c × x_h)  [comms dead-zone × isolation]
      + δ·(x_b_p + x_b_e)  [baseline term]

Risk score:
  p = sigmoid(z) ∈ [0, 1]

Labels:
  p < 0.4         → Low (green)
  0.4 ≤ p < 0.65  → Medium (yellow)
  0.65 ≤ p        → High (red)
  confidence<0.3  → Unknown (grey)

Hand-set seed values (Day 2); fitted on A–C families (Day 4):
  β = [0.5, 0.3, 0.6, 0.4, 0.2, 0.35]  # ≥ 0
  γ = {(1,2): 0.2, (3,1): 0.15, (5,0): 0.1}  # ≥ 0
  δ = 0.3
```

---

## 3. API Contracts

### 3.1 POST /ingest

**Request:**
```json
{
  "event_id": "evt-001",
  "domain": "power",
  "event_type": "blackout",
  "entity_id": "feeder-F12",
  "h3_cell": "890c1d2cf37ffff",
  "severity": 1.0,
  "source_type": "official",
  "source_reliability": 0.9,
  "event_timestamp": "2026-10-25T14:30:00Z",
  "ingestion_timestamp": "2026-10-25T14:30:02Z",
  "parse_confidence": 1.0,
  "scenario_tag": "scenario_A_seed_42"
}
```

**Response (200):**
```json
{
  "status": "accepted",
  "event_id": "evt-001",
  "cell": "890c1d2cf37ffff",
  "risk_updated": true,
  "new_risk": 0.73,
  "risk_interval": [0.65, 0.81],
  "timestamp": "2026-10-25T14:30:02.123Z"
}
```

**Response (422):**
```json
{
  "status": "rejected",
  "reason": "PII detected: phone number in entity_id field",
  "field": "entity_id",
  "details": "Regex match: +1-555-..."
}
```

### 3.2 GET /sse/events

**Headers:**
```
Accept: text/event-stream
```

**Stream (server-sent events):**
```
id: evt-001
event: cell_updated
data: {"cell": "890c1d2cf37ffff", "risk": 0.73, "interval": [0.65, 0.81], "drivers": {...}}

id: evt-002
event: zone_formed
data: {"zone_id": "Z_07", "cells": [...], "risk": 0.78, "polygon": [...]}

id: evt-003
event: feed_loss
data: {"pattern": "random", "loss_pct": 60, "unknown_cells": 450}
```

**Reconnect behavior:** Client includes `Last-Event-ID` header; server replays last 200 events from memory buffer.

### 3.3 GET /zones (ADDED)

**Query params:** `?risk_min=0.65&confidence_min=0.3&limit=100`

**Response:**
```json
{
  "zones": [
    {
      "zone_id": "Z_07",
      "cells": ["890c1d2cf37ffff", ...],
      "polygon": {...GeoJSON...},
      "risk": 0.78,
      "risk_interval": [0.71, 0.85],
      "confidence": 0.72,
      "drivers": [
        {"name": "Hospital isolation", "contribution_pct": -0.31},
        {"name": "Power stress", "contribution_pct": -0.19},
        {"name": "Closure×transit", "contribution_pct": -0.12}
      ],
      "sources": {
        "official": 0.40,
        "sensor": 0.35,
        "crowd": 0.25
      },
      "population": 12500,
      "k_merged": false
    }
  ]
}
```

**Note:** Cells with `k_merged=true` are aggregated to res-8; not individual cells.

### 3.4 GET /dispatch (ADDED)

**Response:**
```json
{
  "queue": [
    {
      "priority": "HIGH",
      "zone_id": "Z_07",
      "action": "mobile_generator",
      "trigger_evidence": [
        "feeder F-12 down (4 outages in 5 months)",
        "hospital isolation +0.31"
      ],
      "expected_risk_drop": 0.35,
      "drop_interval": [0.25, 0.43],
      "status": "proposed",
      "timestamp": "2026-10-25T14:35:00Z"
    }
  ]
}
```

### 3.5 POST /dispatch/{dispatch_id}/approve (ADDED)

**Request:**
```json
{
  "approval_note": "Approved by duty officer"
}
```

**Response:**
```json
{
  "dispatch_id": "disp-001",
  "status": "dispatched",
  "zone_id": "Z_07",
  "eta_minutes": 45,
  "log_entry": "..."
}
```

After approval, engine re-scores affected cells with the action applied (e.g., feeder power restored).

### 3.6 GET /health, GET /health/feeds (ADDED)

**Response:**
```json
{
  "status": "ok",
  "uptime_seconds": 86400,
  "events_ingested": 5420,
  "cells_active": 1847,
  "zones": 23,
  "feeds": {
    "power": {"status": "ok", "last_event": "2026-10-25T14:29:50Z", "lag_sec": 10},
    "transit": {"status": "degraded", "last_event": "2026-10-25T14:15:00Z", "lag_sec": 1050},
    "water": {"status": "ok", ...},
    "health": {"status": "ok", ...},
    "comms": {"status": "missing", "last_event": null, "lag_sec": null},
    "road": {"status": "ok", ...}
  }
}
```

### 3.7 GET /eval/results (ADDED)

**Response:**
```json
{
  "eval_timestamp": "2026-10-25T20:00:00Z",
  "scenarios": {
    "A_road_transit": {
      "family": "A",
      "held_out": false,
      "seeds_count": 20,
      "iou_mean": 0.72,
      "iou_ci_lower": 0.68,
      "iou_ci_upper": 0.76,
      "cell_precision": 0.81,
      "cell_recall": 0.68,
      "zone_hit_rate": 0.85
    },
    ...
    "D_construction_site": {
      "family": "D",
      "held_out": true,
      "iou_mean": 0.58,
      "iou_ci_lower": 0.51,
      "iou_ci_upper": 0.65,
      "zero_shot_gap": 0.14
    }
  },
  "resilience": {
    "feed_loss": {
      "pattern_random": [
        {"loss_pct": 10, "iou_mean": 0.71},
        {"loss_pct": 30, "iou_mean": 0.68},
        {"loss_pct": 60, "iou_mean": 0.61},
        {"loss_pct": 80, "iou_mean": 0.44}
      ]
    }
  },
  "ablations": {
    "census_only": 0.45,
    "v1_additive": 0.52,
    "v2_no_road": 0.64,
    "v2_full": 0.72
  }
}
```

### 3.8 GET /privacy/redteam (ADDED)

**Response:**
```json
{
  "attacks": {
    "membership_inference": {
      "auc_noise_off": 0.82,
      "auc_noise_on": 0.58,
      "threshold_used": 0.5,
      "interpretation": "Attacker only marginally better than random guessing with noise enabled"
    },
    "differencing": {
      "time_windows": 10,
      "max_cell_change": 0.12,
      "mean_cell_change": 0.03
    },
    "linkage": {
      "unique_identified_pct": 3.2,
      "synthetic_population": 50000,
      "attack_assumption": "Attacker has census + risk scores"
    }
  },
  "privacy_parameters": {
    "k": 5,
    "noise_stddev": 0.08,
    "dp_budget": "10 events/cell/hour"
  },
  "curves": {
    "k_vs_auc_vs_iou": [
      {"k": 3, "auc": 0.70, "iou": 0.75},
      {"k": 5, "auc": 0.58, "iou": 0.72},
      {"k": 10, "auc": 0.52, "iou": 0.68}
    ]
  }
}
```

---

## 4. Data Flow Sequence Diagrams

### 4.1 Event Ingest → Map Update

```
User/Simulator          API                Engine              SSE           Browser
    |                    |                   |                  |              |
    |--POST /ingest----->|                   |                  |              |
    |  (CanonicalEvent)  |                   |                  |              |
    |                    |--Validate PII---->|                  |              |
    |                    |  & schema         |                  |              |
    |                    |<--OK/Reject-------|                  |              |
    |                    |                   |                  |              |
    |                    |--Log to SQLite--->|                  |              |
    |                    |                   |                  |              |
    |                    |--Update cell----->|                  |              |
    |                    |  state (decay,    |                  |              |
    |                    |   accumulate)     |                  |              |
    |                    |                   |                  |              |
    |                    |--Recompute risk-->|                  |              |
    |                    |  (logistic)       |                  |              |
    |                    |                   |                  |              |
    |                    |--Check zones---->|                  |              |
    |                    |  (DBSCAN)        |                  |              |
    |                    |                   |                  |              |
    |                    |--Emit SSE--------|--cell_updated--->|--Update----->|
    |                    |  event           |                  | cell color  |
    |<--200 OK-----------|                  |                  |              |
    |  (cell,risk,...)   |                  |                  |              |
```

**Latency target:** ≤2 sec p95 from POST to browser update.

### 4.2 Road Closure → Dijkstra Recompute

```
Event: "Road R-14 closed"
    |
    v
Ingested as: domain=road, entity_id=R-14, severity=1.0
    |
    v
Engine identifies affected cells (within 2 km of R-14)
    |
    v
Runs multi-source Dijkstra on subgraph (reversed, R-14 removed)
    |
    v
Updates hospital_isolation for affected cells
    |
    v
Re-scores all affected cells
    |
    v
Emits SSE: zone_updated for new High zones
    |
    v
Browser: cells turn red/yellow, new zone polygon appears
```

**Latency target:** ≤100 ms recompute.

### 4.3 Scenario Replay (Deterministic)

```
Scenario YAML (seed=42)
    |
    v
Load seed into random generator
    |
    v
For each event in scenario (ordered by timestamp):
    |
    +--Replay event → /ingest
    |
    +--Engine applies deterministically
    |    (no randomness in scoring, only in noise/FedAvg)
    |
    +--Log event + new cell state to SQLite
    |
    v
Compute IoU against ground-truth polygon
    |
    v
Report IoU ± 95% CI
```

---

## 5. Baseline Data & Mapping Tables

### 5.1 Real Baseline (Downloaded, Licensed)

| Dataset | Source | Format | Usage | ADDED Note |
|---------|--------|--------|-------|------|
| Road network | OSM via OSMnx | GraphML | Hospital travel time, closure impact | Cached; verify license |
| Hospitals + clinics | OSM + HOTOSM/HDX | GeoJSON | Hospital proximity, capacity | Dedup by location |
| WorldPop 100m | NASA | GeoTIFF | Population per cell, k-floor | Clipped to Nagpur bbox |
| VIIRS Black Marble | NASA LAADS DAAC | GeoTIFF | Economic proxy layer 1 | Annual composite |
| Nagpur wards | OSM admin boundaries | GeoJSON | Display labels; verify ~143 wards | 2011 vintage |
| OSM transit | OSM public transport | GeoJSON | Stop/route locations | Sparse; no GTFS found |
| Slum/building data | data.gov.in or OSM | shapefile/CSV | Economic proxy layer 2 | May be partial |
| Census 2011 amenities | Census + data.gov.in | CSV | Dated economic proxy | Label as "2011" in UI |
| Cell towers | OpenCellID | CSV | Call-drop attribution | Register on Day 1; patchy |

### 5.2 Simulated Mapping Tables (Authored by Team)

| Mapping | Domains | Purpose | ADDED Note |
|---------|---------|---------|------|
| feeder → H3 cells | Power | Power stress per cell | ~20 feeders; manual author |
| pump_zone → cells | Water | Water loss attribution | Author from feeder + pump locations |
| bus_route → cells | Transit | Transit loss per cell | Author from OSM transit |
| tower → cells | Comms | Call-drop attribution | Author from OpenCellID or synthetic |
| hospital → cell | Health | Hospital load attribution | One-to-one; from OSM |
| road_segment → cells | Road | Closure impact per cell | From OSM edges + buffer |

---

## 6. ADDED: Frontend Component Architecture

```
App.tsx
├── MapContainer
│   ├── MapLibre GL canvas (H3 hexes, wards, polygons)
│   └── Legend (green/yellow/red/grey, sources)
├── SectorPanel (click cell)
│   ├── Risk score + interval
│   ├── Confidence + source breakdown
│   ├── Top 3 drivers (+ counterfactual)
│   └── Dispatch action queue
├── CausalGraphView
│   ├── Cytoscape.js graph
│   ├── Nodes (domains + zone)
│   ├── Edges (drivers as weights)
│   └── Editable mode (expert annotations)
├── DispatchLog
│   ├── Priority color
│   ├── Zone + action + evidence
│   ├── Risk drop prediction
│   └── Status toggles (proposed→approved→dispatched)
├── StressConsole
│   ├── Feed-cut slider (0–100%)
│   ├── Loss-pattern selector (random/domain/area)
│   ├── Conflict injector (type contradicting report)
│   └── Node dropper (toggle zone node on/off)
├── PrivacyPanel
│   ├── k-threshold display
│   ├── Red-Team results (AUC, curves)
│   └── Tradeoff chart (k vs. AUC vs. IoU)
└── SSEStream
    ├── Reconnect buffer (last 200 events)
    └── Keep-alive ping (if server sleeps)
```

---

## 7. ADDED: Evaluation Harness

```python
# eval/harness.py
def run_scenario(scenario_yaml, engine):
    """
    1. Load seed, ground-truth polygon
    2. Replay events in order
    3. Compute IoU per time step
    4. Bootstrap confidence intervals
    5. Return: iou_mean, iou_ci, precision, recall, latency
    """

def compute_iou(predicted_zone, ground_truth):
    """
    predicted_zone: set of H3 res-9 cells with risk >= threshold
    ground_truth: set of cells from scenario YAML
    return: |intersection| / |union|
    """

def resilience_test(engine, scenario, feed_loss_pct, pattern):
    """
    pattern in: "random", "domain", "area"
    Drop feeds, re-run scenario, measure IoU drop
    """
```

---

## 8. ADDED: Privacy Implementation Details

### 8.1 k-Merge Aggregation

```python
def merge_subcell(cell: str, k: int) -> str:
    """
    If expected_contributors[cell] < k:
        return h3.h3_to_parent(cell, resolution=8)
    else:
        return cell
    """
```

### 8.2 Noise Calibration

```
For each published count:
  noised_count = count + Laplace(0, scale=b)
  where scale=b is chosen so that membership-inference AUC ≤ 0.60
  (tuned empirically on Red-Team attack)
```

---

## 9. Approval Gate

**Sign-off required before Phase 0 code begins:**

- [ ] API contracts locked (section 3)
- [ ] Data models correct (section 2)
- [ ] Locked decisions understood (requirements.md section 4)
- [ ] Sequence diagrams make sense (section 4)
- [ ] Evaluation metrics acceptable (requirements.md section 5)

---

**Next:** `tasks.md` (ordered, dependency-aware tasks for Phases 0–8)
