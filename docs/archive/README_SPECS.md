# UrbanPulse: Spec Package Complete ✅

**Status:** Ready for Approval & Phase 0 Start  
**Date Generated:** 2026-10-25  
**Your Branch:** `priyanshu` (A1 Priyanshu working here)

---

## 📦 What's Delivered

### The Three Core Spec Documents

1. **`.kiro/requirements.md`** (400 lines)
   - 7 user stories with EARS acceptance criteria
   - 13 locked decisions (D1–D13)
   - Non-functional requirements (latency, privacy, reliability)
   - Scope tiers (MUST/SHOULD/COULD) + cut order
   - **Read this if:** You want to know what success looks like

2. **`.kiro/design.md`** (500 lines)
   - System architecture diagram
   - Data models (CanonicalEvent, CellState, RiskModel)
   - 6 REST API contracts (POST /ingest, GET /sse/events, GET /zones, etc.)
   - Sequence diagrams (event flow, road closure, scenario replay)
   - Baseline data table (real datasets + simulated mapping tables)
   - Frontend component architecture
   - Privacy model (k-merge, noise, FedAvg)
   - **Read this if:** You need to know HOW to build it

3. **`.kiro/tasks.md`** (600 lines)
   - Ordered, dependency-aware tasks for Phases 0–8
   - Each phase has Alpha and Beta task tables
   - A1-specific checklist (~21 hours across 4 days)
   - Cut order (Isolation Forest first; NEVER CUT list)
   - **Read this if:** You need your daily task list

### Supporting Documents (Root)

4. **`SPEC_SUMMARY.md`** (200 lines)
   - 30-second overview of what was delivered
   - Key assumptions baked into spec
   - How to use the spec during development
   - **Read this first for context**

5. **`TEAM_KICKOFF.md`** (300 lines)
   - Team roles & responsibilities
   - **The Day 1 Blocker:** event_schema.py must commit by 01:00 UTC
   - Quick reference for A1 checklist
   - Day 1 success criteria
   - API contracts you'll build
   - Evaluation metrics you'll measure
   - Critical dates & handoffs
   - Approval checklist
   - **Read this as the team for alignment**

6. **`DAY0_SETUP.md`** (250 lines)
   - Pre-Day-1 setup checklist (30–45 min for everyone)
   - Alignment meeting script (15 min synchronous)
   - Environment setup steps (Python, Node, Docker)
   - Stakeholder sign-off template
   - FAQ
   - **Do this before Day 1 00:00 UTC**

---

## 🎯 What You (A1) Need to Know

### Your Role: Backend Core + Spatial Engine

| Phase | Days | Focus | Hours |
|-------|------|-------|-------|
| **0** | Day 1 | Docker + schema (BLOCKER) + API stubs | 3–4 h |
| **1** | Day 2 | Dijkstra + cell state + scoring + integration | 4–5 h |
| **2–3** | Day 3 | Multi-domain + recompute + 60% loss + IoU | 4–5 h |
| **4–8** | Day 4 | FedAvg + Red-Team + deploy + eval | 4–5 h |

**Total:** ~16–18 hours over 4 days (realistic for parallel work + coordination)

---

### Your Day 1 Blocker (Critical)

**Task A0.3:** Write `contracts/event_schema.py` with A2

This file:
- Defines the canonical event structure (Pydantic model, strict validation)
- Is imported by all 4 team members
- Blocks `/ingest` endpoint, SSE stream, engine scoring, scenario replay
- Must be committed by **01:00 UTC Day 1** so everyone else can proceed

**Why it's the blocker:**
- Beta can't build the map without knowing the event structure
- Alpha can't build the engine without knowing the event structure
- The entire system data flow depends on this contract

---

### Your Key APIs (Day 1–2)

```python
# Day 1: Stubs (accept schema, return mock response)
POST /ingest
  ↓ (validates PII, logs to SQLite)
GET /sse/events

# Day 2: Wire to engine
POST /ingest → cell state update → risk re-score → emit SSE

# Day 3: Add domain inputs & multi-domain scoring
POST /ingest (all 6 domains: power, transit, water, health, comms, road)

# Day 4: Add evaluation + federated + deployment
GET /eval/results
GET /privacy/redteam
GET /health
```

---

### Your Deliverables by Day 4

1. **Backend (FastAPI + asyncio)**
   - `/ingest` endpoint (validate, log, score)
   - `/sse/events` stream (push updates live)
   - `/zones` list (return zone polygons + drivers)
   - `/dispatch` queue (greedy allocation)
   - `/health`, `/eval/results`, `/privacy/redteam` (operations)

2. **Engine (In-Memory + SQLite Log)**
   - Cell state with time decay (48h window)
   - Logistic risk model (β, γ ≥ 0)
   - Multi-domain stress aggregation
   - Road-graph isolation index (Dijkstra)
   - Driver contributions (counterfactuals)
   - 60% feed-loss resilience

3. **Federated Learning (Day 4)**
   - 5 in-process zone nodes
   - Custom FedAvg loop (~40 lines)
   - Noise + clipping + dropout + median agg

4. **Evaluation (Day 4)**
   - IoU harness
   - Red-Team attack script
   - Results table (IoU, ablations, privacy tradeoffs)

5. **Deployment (Day 4)**
   - Docker image + Compose
   - Deploy to Railway/Fly.io (TLS, CORS, secrets)
   - Keep-warm ping

---

## 🚀 Before You Start (Day 0)

### 1. Read the Docs
- [ ] Read `SPEC_SUMMARY.md` (5 min)
- [ ] Read `TEAM_KICKOFF.md` (10 min)
- [ ] Read `.kiro/requirements.md` sections 2–4 (10 min)
- [ ] Read `.kiro/design.md` sections 2–3 (10 min)
- [ ] Read `.kiro/tasks.md` Phases 0–1 (10 min)

**Total:** 45 min. Do this before the alignment meeting.

### 2. Alignment Meeting (Day 0, 15 min)
- Confirm the 13 locked decisions (D1–D13)
- Confirm Day 1 blocker (event_schema.py)
- Confirm data handoffs (roads, WorldPop, mapping tables)
- Confirm API contracts
- Confirm evaluation rigor (blind scenario owner)

### 3. Get Stakeholder Sign-Off (Day 0, before 00:00 UTC Day 1)
- Approver reads all 3 spec docs
- Approver confirms MUST-HAVE scope
- Approver signs TEAM_KICKOFF.md approval checklist
- **No coding starts without approval**

### 4. Environment Setup (Day 0, 10 min)
- Clone repo + switch to `priyanshu` branch
- Verify Python ≥ 3.10, Docker, git config
- Create `.env` file (if needed)
- Verify push access to GitHub

---

## 📋 The Day 1 Blocker (Repeat for Emphasis)

**Nothing else starts until this is done:**

```bash
# Day 1 00:00 UTC
A1: Register OpenCellID (5 min; async approval)

# Day 1 00:15 UTC
A1 + A2: Start writing contracts/event_schema.py
         (Pydantic model, strict validation, no PII)

# Day 1 01:00 UTC ← **CRITICAL**
A1: COMMIT event_schema.py to priyanshu branch
    This unblocks: B1's map, A2's scoring, B2's simulators

# Day 1 01:05 UTC
All other Phase 0 tasks run in parallel
```

If `event_schema.py` is not committed by 01:00 UTC, the entire team sits idle.

---

## ✅ Phase 0 Success Criteria (Day 1 Exit)

- [ ] `event_schema.py` committed (BLOCKER lifted)
- [ ] `/ingest` accepts valid events, rejects PII, logs to SQLite
- [ ] `/sse/events` emits mock events every 3 seconds
- [ ] React map shell renders H3 hexagons (mock data)
- [ ] Map subscribes to SSE stream
- [ ] **Integration test:** Post event to `/ingest` → cell colour changes on map
- [ ] Footer displays: "Baseline data: real | Live feeds: simulated"
- [ ] Docker Compose runs without errors

---

## 📊 Key Numbers to Remember

| Metric | Target | Owner | When |
|--------|--------|-------|------|
| Event ingest latency | p95 ≤ 2 sec | A1 | Day 2–4 |
| Dijkstra recompute | ≤ 100 ms | A1 | Day 3 |
| FedAvg round time | ≤ 10 sec | A1 | Day 4 |
| Map FPS | 60 FPS | B1 | Day 3–4 |
| H3 cells (Nagpur) | ~2,000 cells | B2 | Day 1 |
| IoU on A–C scenarios | Target >0.65 | A1 | Day 4 |
| Feed loss tolerance | 0–80% | A1 | Day 3 |
| Membership-inference AUC (with noise) | ≤ 0.60 | A2 | Day 4 |
| k-anonymity threshold | k ≥ 5 | A2 | Day 4 |

---

## 🔒 The 13 Locked Decisions (You Can't Change These)

| ID | Decision | Why It Matters to You |
|----|----------|---|
| D1 | Pilot: Nagpur, Maharashtra | H3 bbox is fixed; ~2,000 cells |
| D2 | H3 res-9 scoring; res-8 k-merge | Dictates grid size + k-merge logic |
| D3 | In-memory + append-only SQLite | Your event_schema → SQLite schema |
| D4 | FastAPI + asyncio | Your `/ingest` is FastAPI async route |
| D5 | React + MapLibre | B1's stack is fixed |
| D6 | Logistic (β, γ ≥ 0); no linear sum | Your scoring function is sigmoid-based |
| D7 | Counterfactual drivers | You compute driver drops numerically |
| D8 | 5 in-process nodes; 40-line FedAvg | No Flower; custom loop only |
| D9 | Blind scenario owner | You never see D, E, adversarial until Day 4 |
| D10 | Static source tiers (0.9/0.7/0.5/0.3) | Your reliability fusion is weighted |
| D11 | Regex parsers (LLM optional) | Your parser is deterministic |
| D12 | Population = priority only | Don't use pop density as risk driver |
| D13 | Persistent backend (Railway/Fly.io) | You deploy to a platform with state |

---

## 🚨 If You Find a Problem

**Don't silently change the spec.** Instead:

1. **Document it:** Create a GitHub issue or add a comment to the spec file
2. **Alert the team:** Message A2, B1, B2 immediately (Slack/Discord)
3. **Escalate if critical:** Ask organizer if it blocks Day 1
4. **Proceed with old spec** while waiting for approval

---

## 📞 Who to Ask for What

| Question | Ask | Expected Response Time |
|----------|-----|---|
| "What's the event schema?" | A2 (until A0.3 commits), then read `contracts/event_schema.py` | Immediate |
| "How do I build /ingest?" | Read `design.md` section 3.1, then ask A1 | 5 min |
| "What's the risk model?" | Read `design.md` section 2.3, then ask A2 | 5 min |
| "Can I use a different library?" | Ask A1 (for backend) or B1 (for frontend); escalate to organizer if blocked | 15 min |
| "I found a bug in the spec" | Document + alert organizer + team | 30 min |
| "I'm stuck on X task" | Ask your pair (A1↔A2, B1↔B2) | Immediate |
| "Can we change a locked decision?" | Ask organizer; answer is "not without replanning" | 1 hour |

---

## 📅 Timeline Summary

| Time | Event | Owner |
|------|-------|-------|
| Day 0 (before 00:00 UTC Day 1) | Read spec + alignment meeting + stakeholder sign-off | All |
| Day 1 00:00 UTC | OpenCellID registration (async) | A1 |
| Day 1 00:15 UTC | Start event_schema.py | A1 + A2 |
| **Day 1 01:00 UTC** | **COMMIT event_schema.py** (BLOCKER LIFTS) | A1 |
| Day 1 16:00 UTC | Phase 0 exit: event → map works | All |
| Day 2 12:00 UTC | Phase 1 exit: baseline map + road closure impact | A1, A2, B1, B2 |
| Day 3 12:00 UTC | Phase 3 exit: all 6 domains + 60% loss resilience | A1, A2 |
| Day 3 16:00 UTC | Integration demo (all systems working) | All |
| Day 4 12:00 UTC | FedAvg + Red-Team + eval complete | A1, A2 |
| Day 4 18:00 UTC | Backend + frontend live; demo video; results published | All |

---

## 🎓 How to Use This Spec During Development

### For Daily Standups
- "What's my task today?" → Check `tasks.md` for your phase
- "Am I on track?" → Cross-check your actual hours vs. estimated hours

### For Technical Decisions
- "Should I use library X?" → Check `design.md` for the spec'd choice
- "What's the API contract?" → Check `design.md` section 3

### For Acceptance Testing
- "How do I know if it works?" → Check `requirements.md` for user stories + EARS criteria

### For Integration
- "What does the other team need from me?" → Check the phase exit criteria

### For Cut Decisions
- "What should we drop if we're behind?" → Check `tasks.md` cut order (Isolation Forest first; never cut k-merge)

---

## 📝 Document Locations

```
Repository Root
├── .kiro/
│   ├── requirements.md      ← Core spec: what to build
│   ├── design.md           ← Core spec: how to build it
│   └── tasks.md            ← Core spec: your daily tasks
├── SPEC_SUMMARY.md         ← Quick overview (read first)
├── TEAM_KICKOFF.md         ← Team alignment + blocker
├── DAY0_SETUP.md           ← Pre-Day-1 checklist
└── README_SPECS.md         ← This file (you are here)
```

---

## ✨ Final Checklist Before You Start

- [ ] Read all 3 core spec docs (`.kiro/requirements.md`, `design.md`, `tasks.md`)
- [ ] Read `SPEC_SUMMARY.md` + `TEAM_KICKOFF.md`
- [ ] Alignment meeting with A2, B1, B2 complete
- [ ] Stakeholder sign-off obtained
- [ ] Environment set up (Python, Docker, git)
- [ ] Can push to `priyanshu` branch
- [ ] Understand the Day 1 blocker (event_schema.py)
- [ ] Understand your A1 checklist
- [ ] Understand the 13 locked decisions
- [ ] Know who to ask if stuck

---

**🚀 You're Ready for Day 1!**

At **00:00 UTC Day 1:**
1. Register OpenCellID (5 min)
2. Open PR with A2 on `contracts/event_schema.py`
3. Target: Commit by 01:00 UTC to unblock the team

Good luck! 💪

---

Last updated: 2026-10-25  
Branch: `priyanshu`  
Status: **READY FOR APPROVAL & PHASE 0 START**
