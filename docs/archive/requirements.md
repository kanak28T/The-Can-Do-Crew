# UrbanPulse: Requirements Specification

**Document Version:** 1.0  
**Date:** 2026-10-25  
**Status:** Pending Approval  

---

## 1. Executive Summary

UrbanPulse is an autonomous, privacy-preserving spatial intelligence engine that fuses fragmented, noisy urban exhaust (transit disruptions, grid failures, emergency calls, health records) into a causal geographic vulnerability map. The system must:

- Preserve privacy strictly (zero PII, survive red-team re-identification attacks)
- Fuse 6 domains (transit, power grid, water, health, communications, road closures)
- Find unprogrammed patterns (e.g., construction sites trapping low-income blocks)
- Explain causes numerically (e.g., "80% grid failure history + >2 km to nearest clinic")
- Keep working when 60% of data streams are unavailable or contradictory
- Learn shared coefficients through federated learning across 5 municipal zones
- Be scored by Intersection-over-Union (IoU) against hidden ground-truth vulnerability zones

**Pilot:** Nagpur, Maharashtra. **Evaluation:** IoU on 9+ scenarios (4 fit, 4 held-out, 2 adversarial).

---

## 2. User Stories & EARS Acceptance Criteria

### 2.1 Critical User Story: **Identify Hidden Vulnerability Zones**

**As a** municipal disaster-response coordinator  
**I want to** see which neighborhoods are at highest risk when infrastructure fails  
**So that** I can pre-position resources and alerts before cascading failures trap residents.

**EARS Criteria:**

| Given | When | Then |
|-------|------|------|
| A road closure and a bus-line suspension occur in adjacent cells | The system ingests both events within 5 seconds | A polygon zone forms covering both cells with risk ≥ 0.65 and a causal explanation showing "(1) road closure -0.25 risk points, (2) bus loss -0.15 risk points" |
| A hospital is 2 km away and the nearest clinic is 5 km away (isolated) | A feeder blackout occurs in that cell | Risk jumps to High and the driver panel shows "Hospital isolation +0.31 (feeder F-12 down; road R-14 closed)" |
| The baseline data shows 4 low-income wards with historical grid-failure rates >15% | No recent events occur in those wards | The map colors those cells yellow (Medium) and the driver shows "Baseline: 0.45 (historical grid stress 0.15 + economic constraint 0.30)" |

---

### 2.2 Critical User Story: **Maintain Accuracy Despite Data Chaos**

**As a** data engineer for the system  
**I want to** the engine to work when 60% of feeds are unavailable or contradictory  
**So that** the system never goes dark and the user trusts the remaining signals.

**EARS Criteria:**

| Given | When | Then |
|-------|------|------|
| All crowd-sourced event streams are cut (simulated network failure) | 60% of feeds are randomly suppressed | Cells missing too many data sources show grey "Unknown" instead of a false green; cells with sufficient official/sensor data still show green/yellow/red; IoU drops by <15% compared to all-feeds-on baseline |
| A whole power domain goes offline for 2 hours | 60% domain-wide feed loss occurs | Power-stress values for affected cells decay toward baseline at an event-specific rate; confidence drops; dependent water/pump cells show increased uncertainty (wider intervals); no crash |
| A construction-area reports a road closure but no crowd source confirms it | Official source (confidence 0.9) and crowd sources (confidence 0.5 avg) disagree by >0.4 on stress | The fused belief takes the official status, but confidence is lowered to 0.6 and a "verify" dispatch action is added to the queue |

---

### 2.3 Critical User Story: **Preserve Privacy Against Attackers**

**As a** privacy officer  
**I want to** guarantee that no individual can be re-identified from published risk scores or the federated learning process  
**So that** the system complies with data-protection law and community trust.

**EARS Criteria:**

| Given | When | Then |
|-------|------|------|
| A cell has only 2 residents; H3 resolution 9 is too fine | The system computes risk scores | That cell is suppressed (merged to H3 res-8 parent) until ≥k expected contributors (k ≥ 5 by default); the parent score is published instead |
| A synthetic attacker has the public releases from 24 successive hours | The attacker runs a membership-inference model comparing successive releases | Attacker AUC ≤ 0.60 (only marginally better than random guessing); with noise off AUC is ~0.80, so noise is calibrated to reduce leakage without destroying signal |
| A synthetic attacker has census data and can link it to published risk scores | The attacker tries to de-anonymize individuals by cross-referencing | <5% of synthetic individuals are uniquely identified; the system shows this tradeoff in the privacy panel without claiming "safe" |

---

### 2.4 User Story: **Explain Risk Drivers in Human Terms**

**As a** field coordinator  
**I want to** click on a red zone and see exactly which infrastructure failures caused the high risk  
**So that** I can dispatch the right resources (road crew for closures, mobile generator for power loss, etc.).

**EARS Criteria:**

| Given | When | Then |
|-------|------|------|
| A zone is colored red with risk 0.82 | I click the zone | A side panel shows: (1) Hospital isolation -0.31 (road R-14 closed; bus route 4 suspended); (2) Power stress -0.19 (feeder F-12 low); (3) Interaction term (closure × transit) -0.12; (4) 90% confidence interval 0.71–0.91 |
| The driver panel shows "Hospital isolation -0.31" | I hover over or click the driver label | A tooltip or inline note explains "This cell's nearest hospital is normally 2.1 km by road; with road R-14 closed, it becomes 4.8 km (isolation index +0.40)" |
| The causal graph is visible (expert-drawn hypothesis) | A field team reports a new road closure | The graph highlights the path: closure → transit loss → hospital isolation, and the system re-scores to show the predicted +0.31 risk drop if the road reopens |

---

### 2.5 User Story: **Allocate Resources Efficiently**

**As a** resource dispatcher with 3 mobile generators and 2 water tankers available  
**I want to** the system to recommend which zones to serve first  
**So that** I save the most lives per resource unit.

**EARS Criteria:**

| Given | When | Then |
|-------|------|------|
| There are 5 High-risk zones (risk 0.70–0.90); I have 3 mobile generators | I open the dispatch panel | The system ranks zones by expected risk reduction per generator (e.g., Zone A: 0.35 risk drop, Zone C: 0.28, Zone E: 0.18); a suggested allocation shows "Send generator to A, B, C" with expected post-dispatch scores |
| I approve the dispatch of a mobile generator to Zone A | The system logs the action and re-scores | The dispatch log entry shows: priority (High), zone (A), action (mobile generator), trigger evidence (feeder F-12 down, 4 outages in 5 months), expected risk drop (0.35, interval 0.25–0.43), status (approved → dispatched), and arrival time (estimated) |
| 45 minutes later, the zone risk drops from 0.82 to 0.51 | I click the zone again | The sector panel shows a "Post-dispatch" confidence-interval label and the causal graph reflects the updated state (feeder power stress now 0.05 instead of 0.19) |

---

### 2.6 User Story: **Trust Data Provenance**

**As a** system operator  
**I want to** see which data sources contributed to each risk score and how much I should trust them  
**So that** I know when to demand ground verification.

**EARS Criteria:**

| Given | When | Then |
|-------|------|------|
| A cell's risk is based on 3 sources: official (reliability 0.9), sensor (0.7), crowd (0.5) | I hover over the risk score | A tooltip shows "Risk 0.68 from 3 sources: official 40%, sensor 35%, crowd 25% (weighted by reliability). Confidence: 0.72 (coverage good, freshness 8h, agreement moderate)" |
| A cell receives 15 crowd reports in one hour from the same user account | The spam cap triggers | Only the first 10 reports count; the 11–15 are dropped; a note in the data audit log says "Rate limit: 10 crowd events per (source, cell, hour)" |
| Official status says "no closure" but 20 crowd reports say "road blocked" | Disagreement is detected | The fused belief lowers confidence from 0.80 to 0.50; a "verify" dispatch action is auto-added to check the road manually |

---

### 2.7 User Story: **Detect Novel Patterns**

**As a** system designer  
**I want to** flag cells where multiple domains are stressed together even if no single event explains it  
**So that** human experts can investigate hidden failures (e.g., a construction site nobody reported).

**EARS Criteria:**

| Given | When | Then |
|-------|------|------|
| A cell has normal power, normal transit, but water pressure is -2.5σ and hospital load is +1.8σ | No single event is ingested for that cell | A "novel pattern" or "unexplained" flag appears in the driver panel; the zone is labeled Medium or Watch instead of Low; the system routes a "investigate" action to a human analyst |
| Road graph isolation jumps by 50% (e.g., an edge is marked closed) | No closure event is logged for that edge | A flag "Isolation jump detected" appears; the system checks if a parsing error or data gap is present and surfaces it as a verification task |

---

## 3. Non-Functional Requirements

### 3.1 Performance

- **Event ingest to map update:** p95 latency ≤ 2 seconds (event posted to `/ingest` → cell colour changes on browser map)
- **Dijkstra subgraph recompute:** ≤ 100 ms for a 2 km radius after a road-closure event
- **FedAvg round:** ≤ 10 seconds for 5 in-process nodes
- **Map rendering (MapLibre GL):** 60 FPS for panning/zooming 2,000 H3 cells

### 3.2 Reliability

- **Uptime:** 99% during the hackathon (target; not SLA-binding)
- **Feed loss tolerance:** System remains operational and produces sensible scores when 0–80% of feeds are unavailable
- **No data loss:** All ingested events logged to append-only event store (Parquet or SQLite); replay from seed is deterministic

### 3.3 Privacy

- **Zero PII:** No name, phone, device ID, or free text leaves the privacy gateway
- **k-anonymity:** Cells with <k expected contributors merge to parent; k ≥ 5 default
- **Differential privacy:** Published counts are noised; Red-Team membership-inference AUC ≤ 0.60 with noise
- **Federated learning:** Shared coefficients only; node-local cell data never leaves the node

### 3.4 Usability

- **Dashboard panels:** Sector detail, causal graph, dispatch log, stress console, privacy stats—all live-updating via SSE
- **Mobile-friendly:** React dashboard renders on desktop and tablet; interactive causal graph on screen ≤1500px wide
- **Explainability:** Every risk score is accompanied by top 3 drivers, confidence interval, and source breakdown

### 3.5 Data Quality

- **Scenario replay:** Identical seed → identical event sequence → identical final scores (within floating-point epsilon)
- **Baseline validation:** Road-graph changes are unit-tested; Dijkstra correctness is spot-checked against manual tour times
- **Ground-truth separation:** Held-out scenarios (D, E, adversarial) never used for model fitting; scenario owner is blind to engine internals

---

## 4. Constraints & Locked Decisions

1. **Pilot city:** Nagpur, Maharashtra (D1)
2. **Spatial resolution:** H3 resolution 9 (~2,000 cells for Nagpur); resolution 8 for k-merge dedup (D2)
3. **Backend:** FastAPI + asyncio; in-memory engine state + append-only event log (D3, D4)
4. **Frontend:** React + MapLibre GL; no Streamlit (D5)
5. **Risk model:** Logistic regression (β, γ ≥ 0) with road-graph isolation index; not hand-weighted linear sum (D6)
6. **Explanation:** Exact counterfactual re-scoring + numeric driver contributions + expert causal graph (D7)
7. **Federated learning:** 5 simulated in-process nodes, custom 40-line FedAvg, no Flower (D8)
8. **Evaluation:** Blind scenario owner; held-out families never used for fitting; IoU primary metric (D9)
9. **Reliability fusion:** Static source tiers (official 0.9, sensor 0.7, crowd 0.5, anon 0.3); weighted + spam-capped (D10)
10. **Parsing:** Regex/keyword adapters by default; optional LLM fallback (D11)
11. **Population exposure:** Dispatch priority only; NOT a driver of cell vulnerability (D12)
12. **Hosting:** Persistent backend (Railway/Fly.io); frontend on Vercel/Netlify; baked baseline data or seed step (D13)

---

## 5. Acceptance & Approval Gate

**Exit criteria for Phase 0–1 (Day 1–2):**

- [ ] Schema locked: `/ingest` accepts valid canonical events, rejects PII
- [ ] Map shell: H3 grid renders; mock SSE updates change cell colours in real time
- [ ] Repo: Docker Compose runs; data downloads (roads, WorldPop) complete
- [ ] Baseline features: Hospital travel times, population per cell computed
- [ ] Integration: Post a valid event → cell colour changes on map

**Exit criteria for Phase 2–5 (Day 3–4):**

- [ ] All 6 domains ingesting and scoring
- [ ] IoU harness: scores scenarios A–C
- [ ] 60% feed loss: cells go grey; no crash; IoU drop <15%
- [ ] Driver panel + causal graph: click zone → see top 3 drivers + numeric contributions
- [ ] Dispatch log: approve action → re-score and log entry appears

**Exit criteria for Phase 6–8 (Supplementary):**

- [ ] k-merge + noise: cells <k suppressed; AUC ≤ 0.60 with noise
- [ ] FedAvg: 1 node offline → training completes; coefficients converge
- [ ] Red-Team: attack AUC and privacy parameter curve shown
- [ ] Deploy: Public URL live; README reproducible from fresh clone
- [ ] Evaluation: IoU table filled; ablations shown; ≥4 scenarios scored

---

## 6. Document Change History

| Version | Date | Author | Change |
|---------|------|--------|--------|
| 1.0 | 2026-10-25 | Kiro (generated) | Initial spec from plan v3 |

**Status:** Awaiting stakeholder approval before Phase 0 implementation begins.

---

**Next Steps:**

1. Review EARS acceptance criteria for alignment with team expectations
2. Confirm all 7 locked decisions are non-negotiable
3. Approve or request changes to requirements
4. Proceed to `design.md` and `tasks.md` for detailed implementation planning
