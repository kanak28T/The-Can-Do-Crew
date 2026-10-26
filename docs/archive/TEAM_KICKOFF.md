# UrbanPulse Team Kickoff

**Date:** 2026-10-25  
**Status:** Ready for Day 1  
**Branch:** `priyanshu` (A1 working here)

---

## What's Been Delivered

Three specification documents are **ready for approval**:

1. **`.kiro/requirements.md`** — 7 user stories with EARS acceptance criteria; 13 locked decisions; MUST/SHOULD/COULD scope
2. **`.kiro/design.md`** — System architecture, data models, API contracts (6 REST endpoints), sequence diagrams, privacy model
3. **`.kiro/tasks.md`** — Ordered task breakdown for Phases 0–8; A1 checklist; cut order

**Summary:** `SPEC_SUMMARY.md` (read this first as a team)

---

## Team Roles (Confirmed in Spec)

| Person | Role | Phases | Key Responsibility |
|--------|------|--------|---|
| **A1** (Priyanshu) | Backend Core + Spatial Engine | 0–8 | Events → `/ingest` → cell state → scoring → SSE. Docker, APIs, Dijkstra, FedAvg, deploy. |
| **A2** | Modeling + Security + Evaluation | 0–8 | Logistic risk model, confidence, reliability fusion, drivers, PII, Red-Team, calibration. |
| **B1** | Frontend + UI + Explainability | 0–8 | React + MapLibre, sector panel, causal graph, dispatch log, stress console, privacy panel, demo video. |
| **B2** | Data Pipeline + Simulation | 0–8 | Simulators (power, transit, water, health, comms, road), mapping tables, scenarios, blind scenario owner. |

---

## THE BLOCKER: Day 1 Task A0.3

**Nothing else starts until `contracts/event_schema.py` is committed.**

This file is the contract between all 4 team members. It defines:
- Which fields are allowed (no PII)
- Data types (Pydantic model, strict validation)
- What `/ingest` accepts
- What drives the entire event flow

**Timeline:**
- **00:00 UTC Day 1:** A1 registers OpenCellID (5 min; async approval)
- **00:15 UTC Day 1:** A1 + A2 start writing `contracts/event_schema.py` together
- **01:00 UTC Day 1:** **COMMIT** `event_schema.py` to `priyanshu` branch
- **01:00 UTC Day 1 onwards:** All other Phase 0 tasks unblock and run in parallel

---

## Quick Reference: A1 Day 1 Checklist

- [ ] **A0.1** Register OpenCellID (5 min, start immediately)
- [ ] **A0.2** Docker Compose: FastAPI container + SQLite volume (45 min)
- [ ] **A0.3** (with A2) Write `contracts/event_schema.py` → COMMIT THIS (45 min) ⚠️ **BLOCKER**
- [ ] **A0.5** `/ingest` endpoint stub (30 min)
- [ ] **A0.6** `/sse/events` mock stream (30 min)
- [ ] **A0.10** k-merge signature stub (15 min)
- [ ] (background) Start OSM road graph download with osmnx (30 min)

**Total Day 1 for A1:** ~3–4 hours active, ~30 min background download

---

## Day 1 Success Criteria (Phase 0 Exit)

**For the entire team:**
- [ ] `event_schema.py` committed (BLOCKER lifted)
- [ ] `/ingest` accepts valid events, rejects PII, logs to SQLite
- [ ] `/sse/events` emits mock events
- [ ] React map shell renders H3 hexes (mock data)
- [ ] SSE stream subscribed by frontend
- [ ] **Integration test:** Post valid event to `/ingest` → cell colour changes on map

---

## Spec Highlights (Key Decisions)

### The 13 Locked Decisions (Non-Negotiable)

| ID | Decision | Impact on A1 |
|----|----------|---|
| D1 | Nagpur, Maharashtra | Search OSM for Nagpur coords; H3 bbox fixed |
| D2 | H3 res-9 for scoring; res-8 for k-merge | About 2,000 cells per city; dictates grid size |
| D3 | In-memory engine + append-only SQLite log | Your event_schema → SQLite schema; replay from log |
| D4 | FastAPI + asyncio (no Streamlit) | Your `/ingest` is FastAPI route; async event handlers |
| D6 | Logistic model (β, γ ≥ 0); not hand-weighted | You implement sigmoid scoring; no linear sum |
| D8 | FedAvg: 5 in-process nodes, custom 40-line loop | Day 4 task for you; no Flower or external framework |
| D9 | Blind scenario owner; held-out untouched | Your IoU harness never sees D, E, adversarial until Day 4 |
| D12 | Population = dispatch priority only, NOT risk driver | Don't use pop density as stress input; only for triage |

---

## API Contracts You'll Build (Day 1–2)

### POST /ingest (Day 1 stub; Day 2 wire to engine)

**Accept:**
```json
{
  "event_id": "evt-123",
  "domain": "power",
  "event_type": "blackout",
  "entity_id": "feeder-F12",
  "h3_cell": "890c1d2cf37ffff",
  "severity": 1.0,
  "source_type": "official",
  "source_reliability": 0.9,
  "event_timestamp": "2026-10-25T14:30:00Z",
  "ingestion_timestamp": "2026-10-25T14:30:02Z",
  "parse_confidence": 1.0
}
```

**Reject if:**
- PII detected (phone, name, device_id)
- Any required field missing
- Severity outside [0, 1]
- domain not in {power, transit, water, health, comms, road}

**Response (200 / 422):**
```json
{
  "status": "accepted" | "rejected",
  "event_id": "evt-123",
  "cell": "890c1d2cf37ffff",
  "risk_updated": true,
  "new_risk": 0.73,
  "timestamp": "2026-10-25T14:30:02.123Z"
}
```

### GET /sse/events (Day 1 mock; Day 2 real engine)

**Stream:** Server-Sent Events
```
id: evt-001
event: cell_updated
data: {"cell": "890c1d...", "risk": 0.73, "interval": [0.65, 0.81], "drivers": {...}}
```

---

## Evaluation Metrics (Day 4, Phase 7)

Your IoU harness will compute:
- **Primary:** IoU per scenario (mean ± 95% bootstrap CI)
- **Resilience:** IoU at 0%, 10%, 30%, 60%, 80% feed loss (3 patterns)
- **Baselines:** 4 ablations (census-only, v1, no-road, full v2)
- **Zero-shot:** IoU on held-out scenarios (D, E, adversarial) vs. trained (A–C)

**You never see D, E, adversarial scenarios until Day 4.** B2 keeps them locked.

---

## Critical Dates & Handoffs

| Date | Milestone | Blocker | Owner |
|------|-----------|---------|-------|
| Day 1 01:00 UTC | `event_schema.py` committed | Everything | A1 + A2 |
| Day 1 16:00 UTC | Phase 0 exit: event → map update works | Phase 1 | A1 + B1 |
| Day 2 12:00 UTC | Baseline map renders; road closure changes hospital_isolation | Phase 2 | A1 + A2 |
| Day 3 12:00 UTC | All 6 domains scoring; 60% loss → grey | Phase 3 exit | A1 + A2 |
| Day 3 16:00 UTC | IoU A–C printed; demo rehearsal works | Phase 4 | All |
| Day 4 12:00 UTC | FedAvg trained; Red-Team scored; coefficients fitted | Phase 7 | A1 + A2 |
| Day 4 18:00 UTC | Backend + frontend live; demo video recorded | Exit | All |

---

## Questions Before Day 1?

**Does everyone agree on:**
1. The 13 locked decisions (section 4 of requirements.md)?
2. The 6 REST API contracts (section 3 of design.md)?
3. The Day 1 blocker is A0.3 (event_schema.py)?
4. The A1 checklist and task sizes are realistic?
5. The cut order (NEVER CUT: k-merge, 60% loss, drivers, IoU on ≥4 scenarios)?

**If yes:** Proceed to Day 1 kickoff.  
**If no:** Flag before 00:00 UTC Day 1; we adjust.

---

## Repo Structure (Pre-Day 1)

```
urbanpulse/
├── .kiro/
│   ├── requirements.md      ✅ Created
│   ├── design.md           ✅ Created
│   └── tasks.md            ✅ Created
├── contracts/              (will create Day 1)
│   ├── event_schema.py     ← BLOCKER: A0.3
│   ├── scenario_format.yaml
│   └── ground_truth_format.yaml
├── engine/                 (will create Day 2)
│   ├── cell_state.py
│   ├── risk_model.py
│   └── privacy.py
├── api/                    (will create Day 1)
│   └── main.py             (FastAPI app)
├── sim/                    (will create Day 2–3)
│   ├── power_sim.py
│   ├── transport_sim.py
│   └── ...
├── web/                    (will create Day 1)
│   └── src/
│       └── App.tsx
├── data/                   (will populate Day 1–3)
│   ├── nagpur_roads.graphml
│   ├── nagpur_h3_res9.geojson
│   ├── worldpop_nagpur.tif
│   └── mapping_tables/
├── eval/                   (will create Day 2–7)
│   ├── harness.py
│   └── scenarios/
│       ├── A-train.yaml
│       ├── ...
│       └── holdout/        ← B2's blind folder (locked)
├── docker-compose.yml      (will create Day 1)
├── SPEC_SUMMARY.md        ✅ Created
├── README.md              (will create Day 4)
└── requirements.txt       (will create Day 1)
```

---

## Approval Checklist (Stakeholder Sign-Off)

**Before Day 1 00:00 UTC, confirm:**

- [ ] Requirements spec approved (requirements.md)
- [ ] Design spec approved (design.md)
- [ ] Task breakdown approved (tasks.md)
- [ ] Team roles assigned (A1, A2, B1, B2 confirmed)
- [ ] MUST-HAVE scope locked (k-merge, 60% loss, drivers, IoU, footer label)
- [ ] Cut order approved (Isolation Forest first; NEVER CUT list honored)
- [ ] All 13 locked decisions (D1–D13) confirmed non-negotiable
- [ ] Pilot city = Nagpur (immutable)
- [ ] Evaluation independence = blind scenario owner (immutable)
- [ ] 4-day timeline feasible with 2×2 team (confirm or re-scope)

**Approver signature:**  
_________________________________

**Date:** __________________

---

**Next:** Day 1 kickoff at 00:00 UTC  
**First action:** A1 registers OpenCellID (5 min)  
**Blocker:** A0.3 event_schema.py must commit by 01:00 UTC

---

Good luck! 🚀

