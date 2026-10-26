# UrbanPulse: Implementation Tasks (Phase 0–8)

**Document Version:** 1.0  
**Status:** Ready for Approval  
**Generated:** 2026-10-25

---

## Task Dependency Map

```
Phase 0: Contracts + Shell
├── A1.1: OpenCellID registration (start immediately; async approval)
├── A1.2: Docker Compose setup
├── A1.3+A2.1: event_schema.py (BLOCKER: all other tasks wait)
├── A2.2: PII validator
├── A1.4: /ingest stub
├── A1.5: /sse/events mock
├── A2.3: Scenario + ground-truth formats
├── B1.1: React + MapLibre scaffold
├── B1.2: H3 hex rendering (mock data)
├── B2.1: Ward boundaries download
├── B2.2: H3 res-9 grid generator
└── Integration: Post event → cell colour changes

Phase 1: Baseline Data + Engine Core
├── A1.6+A2.3: OSM road graph download (start Day 1, background)
├── A1.7: Dijkstra hospital travel times
├── A2.4: WorldPop population per cell
├── A2.5: Baseline feature vector
├── A2.6: Logistic score model (hand-set β, γ)
├── A1.8: Cell state engine with decay
├── A1.9: Integrate engine into /ingest + SSE
├── B2.3: VIIRS + slum economic proxy
├── B2.4: Text parser (regex adapters)
├── B2.5: Power domain simulator
├── B2.6: Transport domain simulator
├── B2.7: Scenario runner stub
├── B1.3: Connect map to SSE
└── Integration: Baseline map renders; road closure → hospital_isolation changes

Phase 2: Full Simulator + Scenarios
├── B2.8: Water, health, comms, road simulators
├── B2.9: All mapping tables (feeders, pumps, towers, routes)
├── B2.10: Author scenarios A–I + blind holdout (D, E, adversarial)
├── A1.10: IoU harness
└── Integration: Scenarios replay identically from seed

Phase 3: Engine Core (Resilience)
├── A1.11: Multi-domain inputs (water, comms, health, road)
├── A1.12: Pairwise interaction terms (γ)
├── A2.7: Confidence formula (coverage × freshness × agreement)
├── A2.8: Reliability-weighted fusion + spam cap
├── A2.9: Conflict detection + "verify" action
├── A1.13: Dynamic Dijkstra subgraph recompute
├── A1.14: DBSCAN zone builder
├── A2.10: Driver contributions + counterfactuals
├── A1.15: 60% feed-loss handling (all 3 patterns)
├── A2.11: Greedy intervention planner
├── A1.16: Run IoU A–C
└── Integration: All 6 domains score; 60% loss → grey cells; IoU printed

Phase 4: Real-Time Dashboard
├── B1.4: Wire sector panel to API
├── B1.5: Causal graph view (Cytoscape)
├── B1.6: Dispatch log panel
├── B1.7: Stress console (sliders + injectors)
├── B1.8: Privacy panel placeholder
├── B1.9: SSE reconnect + ring buffer
└── Integration: Typing stress command → zone changes → no page refresh

Phase 5: Explain + Dispatch
├── A2.12: Driver panel UI integration
├── A2.13: Counterfactual what-if top-3
├── B1.10: Causal graph expert annotations
├── B1.11: Dispatch log approve/reject workflow
├── A2.14: Resource-limited planner UI
├── A2.15: Post-dispatch re-score + log
└── Integration: Click zone → drivers visible; approve action → re-score visible

Phase 6: Privacy + Federated Learning
├── A1.17: k-merge with WorldPop floor
├── A2.16: Noise calibration (Laplace)
├── A2.17: Custom FedAvg loop (40 lines)
├── A2.18: Red-Team script (3 attacks)
├── B2.11: Wire k-merge to API response
├── B1.12: Red-Team results to privacy panel
└── Integration: Attack AUC shown; FedAvg trains with 1 node offline

Phase 7: Evaluation
├── A2.19: Fit logistic coefficients on A–C
├── A2.20: Sensitivity analysis (1000 draws)
├── A2.21: Receive & score D, E, adversarial
├── A2.22: Feed-loss IoU at 10%, 30%, 60%, 80%
├── A2.23: Ablations (4 baselines)
├── A1.18: REST endpoints /eval/results, /privacy/redteam
└── Exit: Section 9 table filled

Phase 8: Deploy + Documentation
├── A1.19: Deploy to Railway/Fly.io (TLS, CORS, secrets)
├── A1.20: Keep-warm ping
├── B1.13: Deploy frontend to Vercel
├── B1.14: README with arch diagram, licences, real-vs-sim
├── B1.15: Demo video (<3 min)
├── B1.16: Verify from fresh browser
└── Exit: Public URL live; demo recorded; README reproducible

---

## Phase 0: Contracts & Shell (Day 1, ~8h per team)

### **Team Alpha (A1 + A2)**

| # | Task | Owner | Est. | Status | Notes |
|---|------|-------|------|--------|-------|
| A0.1 | **Register OpenCellID** (do first; takes 24h to approve) | A1 | 5 min | BLOCKER | Needed for Day 2 tower mapping |
| A0.2 | Init repo, Docker Compose: FastAPI container + SQLite volume | A1 | 45 min | PHASE0 | `docker-compose.yml` with services: api, db |
| A0.3 | Write `contracts/event_schema.py` — full Pydantic model (strict) | A1 + A2 | 45 min | PHASE0 | **BLOCKER:** Nothing starts until this commits |
| A0.4 | PII rejection: field-level validator + regex scrubber | A2 | 45 min | PHASE0 | Reject phone, name, device ID; flag and drop event |
| A0.5 | Stub `POST /ingest` — validate schema, write SQLite, return 200/422 | A1 | 30 min | PHASE0 | Log all events append-only |
| A0.6 | Stub `GET /sse/events` — hardcoded mock stream (event every 3s) | A1 | 30 min | PHASE0 | Will wire to engine Day 2 |
| A0.7 | Start background: download OSM road graph, cache as `data/nagpur_roads.graphml` | A2 | 30 min (bg) | PHASE0 | Use `osmnx.graph_from_place("Nagpur, India")` |
| A0.8 | Start background: download WorldPop India 100m raster, clip to bbox | A2 | 30 min (bg) | PHASE0 | Save as `data/worldpop_nagpur.tif` |
| A0.9 | Write `contracts/scenario_format.yaml` + `contracts/ground_truth_format.yaml` templates | A2 | 30 min | PHASE0 | Scenario: events list + seed; ground_truth: polygon + family name |
| A0.10 | k-merge stub: `merge_subcell(cell, k) -> cell_or_parent` signature only | A1 | 15 min | PHASE0 | Implement logic Phase 6 |

**Alpha Phase 0 Exit Criteria:**
- ✅ `/ingest` endpoint accepts valid event, rejects PII, logs to SQLite
- ✅ `/sse/events` emits mock events
- ✅ `event_schema.py` committed (BLOCKER for Beta)
- ✅ OSM roads + WorldPop downloads complete (bg)

---

### **Team Beta (B1 + B2)**

| # | Task | Owner | Est. | Status | Notes |
|---|------|-------|------|--------|-------|
| B0.1 | **Wait for A0.3:** Pull `contracts/event_schema.py` from Alpha | B1 | — | BLOCKER | Cannot start until schema committed |
| B0.2 | Scaffold React + Vite + MapLibre GL under `web/` | B1 | 30 min | PHASE0 | Standard create-vite setup |
| B0.3 | MapLibre shell: render H3 res-9 hexagons, mock GeoJSON, colour-coded green/yellow/red/grey | B1 | 90 min | PHASE0 | Use `h3-js` library for cell rendering |
| B0.4 | Download Nagpur ward boundaries (OSM admin_level=10 or Geofabrik) → `data/nagpur_wards.geojson` | B2 | 30 min | PHASE0 | Verify ~143 wards; label vintage |
| B0.5 | Build H3 res-9 grid for Nagpur bbox using `h3` Python → `data/nagpur_h3_res9.geojson` (commit to repo) | B2 | 45 min | PHASE0 | Shared data; verify cell count ~2000 |
| B0.6 | Start background: Download VIIRS nighttime lights (NASA Black Marble annual) → `data/viirs_nagpur.tif` | B2 | 30 min (bg) | PHASE0 | Register for data.laads.eosdis.nasa.gov |
| B0.7 | Start background: Overpass query for transit stops + routes → `data/nagpur_transit.geojson` | B2 | 20 min (bg) | PHASE0 | OSM public transport tags |
| B0.8 | Connect map to Alpha's SSE: subscribe to `/sse/events`, update cell colour on event received | B1 | 60 min | PHASE0 | Use EventSource API (browser) |
| B0.9 | Add footer: "Baseline data: real (OSM, WorldPop, Census 2011) \| Live feeds: simulated" (always visible) | B1 | 15 min | PHASE0 | MUST be on-screen for demo |

**Beta Phase 0 Exit Criteria:**
- ✅ MapLibre shell renders Nagpur H3 cells, colour-coded by mock data
- ✅ Subscribes to Alpha's `/sse/events`; cell colour changes in real time
- ✅ Ward boundaries overlay visible
- ✅ Real-vs-simulated footer on-screen

**Phase 0 Integration Gate:**
1. Post sample valid event to Alpha's `/ingest`
2. Confirm it appears in Beta's map as a colour change (green → yellow, etc.)
3. Both teams see the same schema version in logs

---

## Phase 1: Baseline Data + Engine Core (Day 2, ~8h per team)

### **Team Alpha (A1 + A2)**

| # | Task | Owner | Est. | Status | Notes |
|---|------|-------|------|--------|-------|
| A1.1 | Load `nagpur_roads.graphml` into NetworkX; verify ~5k edges | A1 | 15 min | PHASE1 | Spot-check: Nagpur central → airport distance reasonable? |
| A1.2 | Multi-source reverse Dijkstra from all hospital nodes; generate `data/hospital_travel_times.json` | A1 | 75 min | PHASE1 | Edge times: normal + 50% congested. Output: cell → min travel time (min) |
| A1.3 | Load WorldPop raster → population per H3 res-9 cell lookup; save as `data/population_per_cell.json` | A2 | 45 min | PHASE1 | Use `rasterio` for zonal stats; units = people per cell |
| A1.4 | Load OpenCellID (if approved by Day 2; else generate synthetic towers) → tower-to-cell mapping | A2 | 45 min | PHASE1 | Save as `data/tower_cell_map.json` |
| A1.5 | Build `engine/cell_state.py`: Python dict keyed by H3; holds stress per domain, confidence, last_updated | A1 | 60 min | PHASE1 | Dataclass: `CellState(h3_cell, domain_stress: Dict, confidence, last_updated, ...)` |
| A1.6 | Implement time-decay: stress decays toward baseline over 48h; domain-specific rates (power slower, crowd faster) | A1 | 45 min | PHASE1 | Stale cells (>6h no update) → confidence drops. Use exponential decay. |
| A1.7 | Implement baseline feature vector: `hospital_isolation` (from A1.2), `grid_failure_rate` (MSEDCL published rates), `transit_deficit` (placeholder), `economic_proxy` (Beta fills Day 2) | A2 | 45 min | PHASE1 | Hand-set or load from config; historical baseline only |
| A1.8 | Implement logistic risk score: `z = b + Σβₖxₖ + Σγⱼₖxⱼxₖ; p = sigmoid(z)` with hand-set coefficients (all β, γ ≥ 0) | A2 | 60 min | PHASE1 | Start with [0.5, 0.3, 0.6, ...]; fit Day 4 |
| A1.9 | Implement Unknown (grey) state: trigger when confidence < 0.3 OR no event in 12h | A2 | 20 min | PHASE1 | Simple flag in CellState |
| A1.10 | Wire engine into `/ingest`: on event, update cell state, re-score, push to SSE stream | A1 | 45 min | PHASE1 | Synchronous path: ingest → cell update → score → SSE emit |

**Alpha Phase 1 Exit Criteria:**
- ✅ Post power-domain event → cell's `power_stress` updates, overall risk re-scores
- ✅ Event appears in SSE stream with new risk value
- ✅ Unit test: remove road edge from NetworkX → affected cell's `hospital_isolation` increases
- ✅ `hospital_travel_times.json` committed

---

### **Team Beta (B1 + B2)**

| # | Task | Owner | Est. | Status | Notes |
|---|------|-------|------|--------|-------|
| B1.1 | Replace mock H3 GeoJSON in map with real `nagpur_h3_res9.geojson` + ward overlay | B1 | 45 min | PHASE1 | Load from `data/`; pin to component state |
| B1.2 | Compute VIIRS nighttime lights intensity per H3 cell (rasterio zonal stats) → economic proxy layer 1 | B2 | 60 min | PHASE1 | Save as `data/viirs_per_cell.json` (normalized 0–1) |
| B1.3 | Download slum data from data.gov.in Nagpur; if unavailable, use OSM `landuse=residential` building density → economic proxy layer 2 | B2 | 60 min | PHASE1 | Save as `data/econ_proxy_per_cell.json` |
| B1.4 | Merge econ proxies: (VIIRS + slum_density) / 2 → single `economic_constraint` score per cell; commit to `data/` | B2 | 30 min | PHASE1 | Alpha reads this file in A1.7 |
| B1.5 | Build **power domain simulator** (`sim/power_sim.py`): feeder → H3 cells table (author ~20 feeders for Nagpur) | B2 | 60 min | PHASE1 | Generate voltage-drop (0–1) and blackout (1.0) events; output canonical events |
| B1.6 | Build **transport domain simulator** (`sim/transport_sim.py`): bus route → cells (author from OSM transit) | B1 | 60 min | PHASE1 | Generate route suspension events + messy-text strings like `"Bus route 4 suspended"` |
| B1.7 | Write regex/keyword text parser (`node/text_parser.py`): handles `"Bus route N suspended"`, `"Substation X voltage"`, `"Road X closed"` → canonical event | B1 | 45 min | PHASE1 | Parser emits event_type, entity_id, severity; confidence 0.8 (regex) |
| B1.8 | Write **scenario generator stub** (`sim/scenario_runner.py`): loads YAML, replays events in order (seeded), posts each to `/ingest` with time compression | B2 | 45 min | PHASE1 | Replay speed = 100x (1 hour sim = 36 sec real time) |
| B1.9 | Build **sector panel** in React: click H3 cell → side panel shows risk, confidence, domain stresses (mock data for now) | B1 | 60 min | PHASE1 | Hardcoded values until Day 3 API integration |

**Beta Phase 1 Exit Criteria:**
- ✅ Scenario runner plays power-outage scenario end-to-end
- ✅ Each event hits `/ingest`, cell colour updates on map
- ✅ 3+ cells change from green → yellow/red
- ✅ Sector panel shows mock risk scores
- ✅ `econ_proxy_per_cell.json` committed

**Phase 1 Integration Gate:**
1. Run power scenario end-to-end
2. Hospital travel time for closed-road cell is higher than neighbours (Alpha's unit test)
3. All baseline data files committed and versioned

---

## Phase 2: Full Simulator + Scenarios (Day 3 early, ~4h Alpha, ~4h Beta)

### **Team Beta (B1 + B2)**

| # | Task | Owner | Est. | Status | Notes |
|---|------|-------|------|--------|-------|
| B2.1 | Build **water domain simulator** (`sim/water_sim.py`): pump-zone → cells table; pump failures linked to power events (dependency graph) | B2 | 45 min | PHASE2 | Cascade logic: if feeder down → pump stress up |
| B2.2 | Build **health domain simulator** (`sim/health_sim.py`): hospital load events (patient arrival surge, capacity threshold) | B2 | 30 min | PHASE2 | Map hospital → cells; generate severity 0–1 |
| B2.3 | Build **communications domain simulator** (`sim/comms_sim.py`): call-drop counts per tower per time bin → canonical events | B2 | 30 min | PHASE2 | Use tower_cell_map from Alpha |
| B2.4 | Build **road closure simulator** (`sim/road_sim.py`): pick OSM edges, generate closure events (structured + messy-text) | B2 | 30 min | PHASE2 | Parse and emit as canonical; severity 0.5–1.0 |
| B2.5 | Author all **mapping tables**: `feeder→cells`, `pump_zone→cells`, `tower→cells`, `route→cells`, `hospital→cell` | B2 | 60 min | PHASE2 | Save as JSON in `data/mapping_tables/`. Verify consistency. |
| B2.6 | Write **scenarios A–I + 2 adversarial** as YAML files (seed, events list, ground-truth polygon, family) | B2 | 90 min | PHASE2 | Scenario owner (B2) keeps D, E, adversarial in `eval/scenarios/holdout/` (locked from Alpha) |
| B2.7 | (optional Day 3) Implement census 2011 ward data → `economic_constraint` proxy layer 3 (literacy + amenities as dated proxy) | B2 | 45 min | PHASE2-optional | Label as "Census 2011 — dated"; commit |

**Beta Phase 2 Exit:**
- ✅ All 6 domain simulators emit canonical events
- ✅ Mapping tables JSON committed
- ✅ Scenarios A–I authored; D, E, adversarial in `eval/scenarios/holdout/`
- ✅ Scenario replay still deterministic from seed

---

### **Team Alpha (A1)**

| # | Task | Owner | Est. | Status | Notes |
|---|------|-------|------|--------|-------|
| A2.1 | Build IoU harness (`eval/harness.py`): load scenario, replay, compute IoU with ground truth, bootstrap CI | A1 | 60 min | PHASE2 | Returns: iou_mean, iou_ci, precision, recall, latency |
| A2.2 | Implement `compute_iou()` function: cell_threshold-based (risk > 0.65 → predicted; compare to ground truth) | A1 | 30 min | PHASE2 | Basic: |intersection| / |union|. Robust over threshold choices. |

**Alpha Phase 2 Exit:**
- ✅ `eval/harness.py` ready for scenarios A–C (Phase 3)

---

## Phase 3: Engine Core + Resilience (Day 3, ~8h per team)

### **Team Alpha (A1 + A2)**

| # | Task | Owner | Est. | Status | Notes |
|---|------|-------|------|--------|-------|
| A3.1 | Add domain inputs: water, comms, health load, road closure stress to cell state | A1 | 60 min | PHASE3 | Wire each domain's event to cell stress; initialize to 0 |
| A3.2 | Implement pairwise interaction terms γⱼₖ for high-impact pairs: (power×water), (road×transit), (comms×health) | A1 | 45 min | PHASE3 | Hand-set γ ≥ 0; fit Day 4 |
| A3.3 | Implement confidence formula: `confidence = coverage × freshness × source_agreement`; wire to cell state | A2 | 45 min | PHASE3 | coverage = % of expected sources present; freshness = 1 - (hours_since_last / 12); agreement = pairwise Pearson ρ of sources |
| A3.4 | Implement reliability-weighted fusion: static tiers (official 0.9, sensor 0.7, crowd 0.5, anon 0.3) + weighted sum + spam cap (≤10 events per (source_type, H3_res8, hour)) | A2 | 45 min | PHASE3 | If >10 crowd events, cap aggregate; log dropped events |
| A3.5 | Implement conflict detection: if official stress and crowd stress differ by >0.4, lower confidence by 0.3 and add "verify" dispatch action | A2 | 30 min | PHASE3 | Flag in cell_state; queue action |
| A3.6 | Implement road-graph subgraph recompute: on road-closure event, identify cells within 2 km, rerun reverse Dijkstra on subgraph only; measure recompute time | A1 | 60 min | PHASE3 | Log latency; target ≤100 ms |
| A3.7 | Implement DBSCAN zone builder: cluster adjacent High-risk cells (risk > 0.65) into named polygon zones; push via SSE | A1 | 45 min | PHASE3 | DBSCAN eps = 1 H3 res-9 cell; min_samples = 2 |
| A3.8 | Implement driver contributions: for each High zone, re-score with each driver set to baseline, compute drop; output `{driver: contribution_pct}` | A2 | 45 min | PHASE3 | Store in zone object; query via API |
| A3.9 | Implement counterfactual re-scoring (top-3 drivers only): "if driver X returns to baseline, risk drops from P to Q" | A2 | 30 min | PHASE3 | Compute for sector panel display |
| A3.10 | Implement 60% feed-loss handler: support 3 patterns (random streams, whole domain, contiguous cell area); stale cells decay to Unknown | A1 | 60 min | PHASE3 | Add `/stress/feed-loss` endpoint to accept parameters |
| A3.11 | Implement intervention planner: actions = {shuttle, mobile_gen, water_tanker, road_crew, alert_relay, verify}; greedy allocation by risk-drop per unit; output dispatch log entries | A2 | 60 min | PHASE3 | Dispatcher queues actions; never auto-dispatch |
| A3.12 | Run IoU harness on scenarios A, B, C; print results (mean, CI, precision, recall) | A1 | 30 min | PHASE3 | Benchmark: no loss case |

**Alpha Phase 3 Exit Criteria:**
- ✅ All 6 domains score live
- ✅ Stress console cuts 60% of feeds → affected cells go grey, no crash
- ✅ IoU reported for A, B, C (no feed loss): mean + 95% CI
- ✅ Driver panel wired (not yet UI; API responses ready)

---

### **Team Beta (B1 + B2)**

| # | Task | Owner | Est. | Status | Notes |
|---|------|-------|------|--------|-------|
| B3.1 | Wire sector panel to real API: `GET /zones/{cell_id}` returns live risk, confidence, drivers, sources | B1 | 45 min | PHASE3 | Replace mock data with real API calls |
| B3.2 | Build causal graph view (Cytoscape.js): nodes = domains + zone; edges = driver contributions from API; editable | B1 | 90 min | PHASE3 | Weights = contributions; layout = hierarchical |
| B3.3 | Build dispatch log panel: table of entries, priority colour, zone, action, trigger evidence, expected drop, status toggle (proposed → approved → dispatched) | B1 | 45 min | PHASE3 | No approval workflow yet; just display |
| B3.4 | Build **stress console**: feed-cut slider (0–100%), loss-pattern selector (random/domain/area), conflict injector (type contradicting report), node dropper | B1 | 60 min | PHASE3 | UI controls; POST to `/stress/...` endpoints |
| B3.5 | Add SSE reconnect with in-memory ring buffer (last 200 events); keep last map state on screen if connection drops | B1 | 30 min | PHASE3 | Browser-side: EventSource.onopen, onerror, onclose handlers |
| B3.6 | Add privacy panel placeholder: k-threshold display (hardcoded 5 for now), Red-Team badge ("pending" until Day 4) | B1 | 20 min | PHASE3 | Will be populated Day 4 |

**Beta Phase 3 Exit Criteria:**
- ✅ Typing `"Bus route 4 suspended"` into stress console → zone turns High → driver panel shows transit + isolation contributions
- ✅ Feed-cut slider drops 60% → grey cells appear
- ✅ No page refresh during any of the above
- ✅ Causal graph renders with edge weights

**Phase 3 Integration Gate:**
1. Full end-to-end demo rehearsal
2. Run scenario A (road + transit)
3. All panels update live
4. Feed loss → grey cells appear as expected
5. Driver contributions visible in side panel

---

## Phase 4–8: [Condensed Summary]

### Phase 4: Real-Time Dashboard (continued work on Day 3–4)
- Wire all sector panel fields to API
- Polish dispatch log workflow (approve → re-score visible)
- Add confidence intervals to risk scores

### Phase 5: Explain + Dispatch (Day 4 early)
- Implement what-if counterfactual in driver panel
- Implement post-dispatch re-score logic
- Dispatch log logs actions + results

### Phase 6: Privacy + Federated (Day 4 mid)
- A1 writes k-merge aggregator (`engine/privacy.py`)
- A2 builds FedAvg loop (40 lines), Red-Team script
- B2 wires k-merge to API; B1 populates privacy panel

### Phase 7: Evaluation (Day 4 late)
- A2 fits coefficients on A–C with FedAvg
- A2 runs sensitivity, ablations, feed-loss curves
- A2 scores D, E, adversarial (held-out)
- Fill results table

### Phase 8: Deploy + Documentation (Day 4 final)
- A1 deploys backend to Railway/Fly.io
- B1 deploys frontend to Vercel
- B1 writes README, records demo video
- All team: verify from fresh browser

---

## Cut Order (if time runs short)

| Priority | Cut First | Rationale | Replacement |
|----------|-----------|-----------|-------------|
| 1 | Isolation Forest anomaly layer | Low bang-for-buck; already have z-score | Keep robust z-score flag only |
| 2 | Structure learning on simulator data | Advanced; expert graph sufficient | Remove from results section |
| 3 | Per-node Docker containers | Simulation ≠ production | Keep in-process nodes |
| 4 | Counterfactuals for all drivers, keep top-3 only | Reduced complexity | Keep driver % contributions |
| 5 | Calibration metrics (Brier, ECE) | Keep IoU + feed-loss | Report only IoU + intervals |
| 6 | FedAvg live demo; keep concept slide | Single-node simulation enough | Show architecture slide instead |
| 7 | Red-Team script; keep written analysis | Code is time-intensive | Written attack analysis in README |

**NEVER CUT:**
- k-merge + PII scrubbing
- 60% feed-loss + Unknown state
- Driver contributions + causal graph
- Dispatch log
- IoU on ≥4 scenarios
- Real-vs-simulated footer label

---

## A1-Specific Task Checklist (Your Role)

**Day 1 (Phase 0):**
- [ ] Register OpenCellID (5 min, start first)
- [ ] Docker Compose setup (45 min)
- [ ] Pair on event_schema.py (45 min with A2; you write Pydantic model)
- [ ] `/ingest` stub endpoint (30 min)
- [ ] `/sse/events` mock stream (30 min)
- [ ] k-merge signature stub (15 min)
- [ ] Start OSM road graph download (bg)

**Day 2 (Phase 1):**
- [ ] Multi-source Dijkstra from hospitals (75 min)
- [ ] Time-decay logic in cell_state.py (45 min)
- [ ] Logistic scoring function (60 min)
- [ ] Wire engine to `/ingest` + SSE (45 min)
- [ ] Run unit test: road closure → hospital_isolation change (15 min)

**Day 3 (Phases 2–3):**
- [ ] Multi-domain stress inputs (60 min)
- [ ] Road-graph subgraph recompute (60 min)
- [ ] 60% feed-loss handler (60 min)
- [ ] DBSCAN zone builder (45 min)
- [ ] IoU harness + run scenarios A–C (90 min)

**Day 4 (Phases 6–8):**
- [ ] FedAvg loop implementation (90 min)
- [ ] Red-Team attack script (90 min)
- [ ] Deploy backend to Railway (60 min)
- [ ] REST endpoints for eval + privacy (30 min)
- [ ] Keep-warm ping (15 min)

**Total for A1:** ~21 hours across 4 days ✓

---

## Approval Gate

**Sign-off required before Phase 0 tasks begin:**

- [ ] Task breakdowns accepted for Phases 0–8
- [ ] A1 & A2 role assignments understood
- [ ] B1 & B2 role assignments understood
- [ ] Day 1 blocking on A0.3 (schema) confirmed
- [ ] Cut order acceptable (MUST-HAVE list honored)
- [ ] All deliverables clear

---

**Next Steps:**

1. Stakeholder approval on requirements.md + design.md + tasks.md
2. Team alignment meeting: confirm roles, data locations, API contracts
3. **Day 1 00:00 UTC:** A1 registers OpenCellID; A1+A2 write event_schema.py
4. **Day 1 01:30 UTC:** All tasks unblocked; parallel work begins

---

**Document History:**

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-10-25 | Initial spec generated from plan v3 |

