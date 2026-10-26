# UrbanPulse: Requirements Specification

**Document Version:** 1.0  
**Status:** Ready for Approval  
**Generated:** 2026-10-25

---

## 1. Overview

UrbanPulse is an autonomous, privacy-preserving spatial intelligence engine that fuses fragmented urban data (transit, power grid, water, health, comms, roads) into causal geographic vulnerability maps. The engine must identify hidden community vulnerabilities, explain risk drivers numerically, and remain operational when 60% of data streams fail or contradict.

**Pilot:** Nagpur, Maharashtra  
**Evaluation:** IoU against hidden ground-truth zones (9+ scenarios: 4 fit, 4 held-out, 2 adversarial)  
**Team:** 4 people (2 backend A1/A2, 2 frontend B1/B2), 4 days  

---

## 2. User Stories with EARS Acceptance Criteria

### Story 1: Identify Hidden Vulnerability Zones

**As a** municipal disaster coordinator  
**I want to** see neighborhoods at highest risk when infrastructure fails  
**So that** I can pre-position resources before cascading failures trap residents.

| Given | When | Then |
|-------|------|------|
| Road closure + bus suspension in adjacent cells | Both events ingested within 5 sec | Zone polygon forms (risk ≥ 0.65); drivers show: "(1) road -0.25, (2) transit -0.15" |
| Hospital 2 km, clinic 5 km (isolated) | Feeder blackout occurs | Risk → High; driver: "Hospital isolation +0.31 (feeder F-12 down; road R-14 closed)" |
| 4 low-income wards, baseline grid-failure rate >15% | No recent events | Cells yellow (Medium); driver: "Baseline 0.45 (grid 0.15 + econ 0.30)" |

---

### Story 2: Maintain Accuracy Despite Data Chaos

**As a** data engineer  
**I want to** the engine to work when 60% of feeds are unavailable or contradictory  
**So that** the system never goes dark.

| Given | When | Then |
|-------|------|------|
| All crowd feeds cut (simulated failure) | 60% random feed loss | Cells missing >X sources → grey Unknown; cells with official/sensor data → green/yellow/red; IoU drop <15% |
| Entire power domain offline 2 hours | 60% domain-wide loss | Power stress decays toward baseline at domain-specific rate; dependent water/pump cells show uncertainty; no crash |
| Official says "no closure", crowd says "blocked" | Disagreement >0.4 stress | Fused belief = official; confidence 0.60; "verify" dispatch action added |

---

### Story 3: Preserve Privacy Against Attackers

**As a** privacy officer  
**I want to** guarantee no individual can be re-identified  
**So that** the system complies with data protection law.

| Given | When | Then |
|-------|------|------|
| Cell has only 2 residents; H3 res-9 too fine | System computes scores | Cell suppressed; merged to H3 res-8 parent until ≥k (k≥5) expected contributors |
| Synthetic attacker has 24h of releases | Runs membership-inference attack | Attacker AUC ≤ 0.60 (noise-on); without noise ~0.80 (noise-off tradeoff shown) |
| Attacker has census + public risk scores | Tries de-anonymization linkage | <5% of synthetic individuals uniquely identified |

---

### Story 4: Explain Risk Drivers

**As a** field coordinator  
**I want to** click a red zone and see exactly which failures caused it  
**So that** I can dispatch the right resources.

| Given | When | Then |
|-------|------|------|
| Zone risk 0.82 | Click zone | Side panel: (1) Hospital isolation -0.31 (R-14 closed; route 4 suspended); (2) Power stress -0.19 (F-12 low); (3) Interaction -0.12; interval 0.71–0.91 (90%) |
| Driver shows "Hospital isolation -0.31" | Hover/click driver | Tooltip: "Normal 2.1 km → 4.8 km with R-14 closed (isolation +0.40)" |
| Causal graph visible | New road closure reported | Graph highlights: closure → transit loss → isolation; re-score predicts +0.31 drop if reopened |

---

### Story 5: Allocate Resources Efficiently

**As a** dispatcher with 3 generators, 2 tankers  
**I want to** the system to recommend zones by risk reduction per resource  
**So that** I save the most lives per unit.

| Given | When | Then |
|-------|------|------|
| 5 High zones (0.70–0.90 risk); 3 generators available | Open dispatch panel | Ranked by risk drop: Zone A (0.35), C (0.28), E (0.18); suggested: "Send to A, B, C" |
| Approve generator dispatch to Zone A | System logs action and re-scores | Log: priority, zone, action, trigger evidence, expected drop (0.35, interval 0.25–0.43), status (approved → dispatched) |
| 45 min later, zone risk 0.82→0.51 | Click zone | Sector panel: "Post-dispatch" label; causal graph updated (feeder stress 0.19→0.05) |

---

### Story 6: Trust Data Provenance

**As a** system operator  
**I want to** see which sources contributed and how trustworthy they are  
**So that** I know when to demand ground verification.

| Given | When | Then |
|-------|------|------|
| Cell risk from official (0.9), sensor (0.7), crowd (0.5) | Hover risk score | Tooltip: "Risk 0.68: official 40%, sensor 35%, crowd 25% (weighted). Confidence 0.72 (coverage good, freshness 8h, agreement moderate)" |
| 15 crowd reports in 1 hour from same account | Spam cap triggers | Only first 10 count; 11–15 dropped; audit log: "Rate limit: 10/hour per (source, cell)" |
| Official "no closure" vs 20 crowd "blocked" | Disagreement detected | Confidence 0.80→0.50; "verify" dispatch auto-added |

---

### Story 7: Detect Novel Patterns

**As a** system designer  
**I want to** flag cells with correlated multi-domain stress (no single event explains it)  
**So that** experts can investigate hidden failures.

| Given | When | Then |
|-------|------|------|
| Cell: normal power/transit, water -2.5σ, hospital +1.8σ | No single event logged | "Unexplained" flag in driver panel; zone → Watch; "investigate" action queued for analyst |
| Road isolation jumps 50% (edge marked closed) | No closure event in logs | Flag "Isolation jump detected"; system checks for parse error/data gap; surfaces verification task |

---

## 3. Non-Functional Requirements

| Aspect | Target |
|--------|--------|
| **Latency** | p95 ingest→map update ≤2 sec; Dijkstra subgraph ≤100 ms; FedAvg round ≤10 sec |
| **Map rendering** | 60 FPS (MapLibre GL) for 2,000 H3 cells |
| **Uptime** | 99% during hackathon |
| **Feed tolerance** | 0–80% loss; Unknown state for insufficient coverage |
| **Data determinism** | Same seed → identical replay (within fp epsilon) |
| **Privacy** | Zero PII; k≥5 anonymity; membership-inference AUC ≤0.60 (with noise) |
| **Accuracy** | IoU primary metric; ≥4 scenarios scored; 95% bootstrap confidence intervals |

---

## 4. Locked Decisions (Non-Negotiable)

| ID | Decision | Rationale |
|----|----|---|
| D1 | Pilot: Nagpur, Maharashtra | Consistent evaluation baseline |
| D2 | H3 res-9 for scoring (~2K cells); res-8 for k-merge | Granularity–privacy tradeoff |
| D3 | In-memory state + append-only event log (Parquet/SQLite) | Deterministic replay; auditability |
| D4 | FastAPI + asyncio; no Streamlit | Production-grade backend; real-time SSE |
| D5 | React + MapLibre GL | Standard GIS stack; no single-framework dependency |
| D6 | Logistic model (β, γ ≥ 0) + road-graph isolation | Interpretability; causality |
| D7 | Counterfactual re-scoring + numeric drivers + expert causal graph | Explainability; domain knowledge |
| D8 | 5 in-process federated nodes; custom 40-line FedAvg | Simulation ≠ production; transparency |
| D9 | Blind scenario owner; held-out families untouched | Evaluation rigor |
| D10 | Static source tiers (0.9/0.7/0.5/0.3) + weighted fusion + spam cap | Reliability fusion; not learned yet |
| D11 | Regex/keyword parsers; optional LLM fallback | Determinism; no external API calls for MVP |
| D12 | Population exposure = dispatch priority only; NOT a risk driver | Small hidden clusters not drowned by dense wards |
| D13 | Backend on persistent platform (Railway/Fly.io); frontend Vercel/Netlify | Stateful sessions; cold-start cost |

---

## 5. ADDED: Evaluation Metrics

The following metrics will be computed at the end of Phase 7:

- **Primary:** IoU per scenario (mean ± 95% bootstrap CI)
- **Secondary:** Cell precision/recall, zone hit rate (IoU ≥ 0.5), detection latency, calibration (Brier score, reliability curve)
- **Resilience:** IoU at 10%, 30%, 60%, 80% feed loss (3 patterns: random, domain, area)
- **Baselines:** Census-only, v1 additive rule, v2 no-road-graph, v2 full
- **Privacy:** Membership-inference AUC (noise off vs. on), differencing attack, linkage uniqueness %
- **Zero-shot:** IoU gap on held-out (D, E, adversarial) vs. training (A–C)

---

## 6. ADDED: Scope & Cut Order

**MUST-HAVE (Phases 0–5, priority):**
- PII scrubbing + k-merge anonymization
- 60% feed-loss handling + Unknown state
- Driver contributions + causal graph
- Dispatch log
- IoU on ≥4 scenarios
- Real-vs-simulated footer label

**SHOULD-HAVE (Phase 6, if time):**
- Federated learning live demo + Red-Team script
- 3 loss patterns + calibration
- Phase 7 results table

**COULD-HAVE (cut if necessary):**
- Isolation Forest anomaly layer
- Graph imputation; structure learning
- Per-node Docker containers
- LLM parsing fallback
- PostGIS

**NEVER CUT:** The MUST-HAVE list.

---

## 7. Approval Gate

**Sign-off required before Phase 0 begins:**

- [ ] All 7 user stories accepted
- [ ] All locked decisions (D1–D13) confirmed non-negotiable
- [ ] MUST-HAVE scope approved
- [ ] Team assignment confirmed (2×2 with A1/A2/B1/B2 roles)

---

**Next:** `design.md` (architecture, data models, API contracts, sequence diagrams)
