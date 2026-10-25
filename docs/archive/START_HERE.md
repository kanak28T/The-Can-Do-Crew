# 🚀 UrbanPulse: START HERE

**Status:** ✅ Spec Complete, Ready for Approval  
**Your Role:** A1 (Backend Core + Spatial Engine)  
**Branch:** `priyanshu`  
**Date:** 2026-10-25

---

## What's Happened

I've generated a complete, production-ready specification for the UrbanPulse hackathon project. All three core documents are ready for your team's review and stakeholder approval.

---

## 📚 What You Have

### Three Core Spec Documents (`.kiro/` folder)

1. **`requirements.md`** — What to build
   - 7 user stories with EARS acceptance criteria
   - 13 locked (unchangeable) decisions
   - Success metrics

2. **`design.md`** — How to build it
   - System architecture
   - Data models & API contracts
   - Sequence diagrams
   - Privacy model

3. **`tasks.md`** — Your daily tasks
   - Phase 0–8 breakdown
   - Your A1 checklist (~21 hours over 4 days)
   - Cut order (what to drop if time runs short)

### Five Supporting Documents (root folder)

4. **`SPEC_SUMMARY.md`** — 5-minute overview
5. **`TEAM_KICKOFF.md`** — Team alignment & Day 1 blocker
6. **`DAY0_SETUP.md`** — Pre-Day-1 checklist
7. **`README_SPECS.md`** — Your comprehensive quick reference
8. **`SPEC_DELIVERY.txt`** — Final delivery checklist
9. **`START_HERE.md`** — This file

---

## 🎯 Your Mission (A1)

**Build the backend engine that scores urban vulnerability in real time.**

### 4 Days, 4 Phases:

| Day | Phase | What You Build | Hours |
|-----|-------|---|---|
| 1 | 0 | Docker + API stubs + schema (BLOCKER) | 3–4 |
| 2 | 1 | Dijkstra + cell state + risk scoring | 4–5 |
| 3 | 2–3 | Multi-domain + 60% loss + IoU | 4–5 |
| 4 | 4–8 | FedAvg + Red-Team + deploy | 4–5 |

**Total:** ~16–18 hours. Realistic. Doable.

---

## ⚠️ THE BLOCKER (CRITICAL)

### Day 1 Task A0.3: Write `contracts/event_schema.py` with A2

**This single file unblocks the entire team.**

- Defines canonical event structure (Pydantic model, strict validation)
- Is imported by all 4 team members
- Blocks: map, engine, simulators, API
- **MUST commit by 01:00 UTC Day 1**

**If this isn't committed by 01:00 UTC, the entire team sits idle.**

---

## 📋 Before You Start (Day 0)

### 1. Read These (45 min)
- [ ] `SPEC_SUMMARY.md` (5 min)
- [ ] `TEAM_KICKOFF.md` (10 min)
- [ ] `.kiro/requirements.md` sections 2–4 (10 min)
- [ ] `.kiro/design.md` sections 2–3 (10 min)
- [ ] `.kiro/tasks.md` Phases 0–1 (10 min)

### 2. Align with Your Team (15 min)
- Confirm the 13 locked decisions
- Confirm Day 1 blocker
- Confirm API contracts
- Confirm data handoffs

### 3. Get Stakeholder Sign-Off
- Organizer reads all 3 spec docs
- Organizer signs `TEAM_KICKOFF.md` approval checklist
- **No coding starts without approval**

### 4. Set Up Your Environment (10 min)
```bash
git clone https://github.com/kanak28T/The-Can-Do-Crew.git
cd The-Can-Do-Crew
git checkout priyanshu
# Verify Python ≥3.10, Docker, git config
```

---

## 🚀 Day 1 (00:00 UTC)

### First 5 Tasks

1. **00:00 UTC:** Register OpenCellID (5 min, async approval)
2. **00:15 UTC:** Start `contracts/event_schema.py` with A2
3. **01:00 UTC:** ⭐ **COMMIT event_schema.py** (BLOCKER LIFTS)
4. **01:05 UTC:** Docker Compose setup (45 min)
5. **01:50 UTC:** PII validator with A2 (45 min)

### Day 1 Success Criteria
- [ ] Schema committed ✅
- [ ] `/ingest` accepts events, rejects PII, logs to SQLite
- [ ] `/sse/events` emits mock events
- [ ] React map renders H3 cells
- [ ] **Integration:** Post event → cell colour changes on map

---

## 🔒 The 13 Locked Decisions (Non-Negotiable)

| # | Decision | Impact on You |
|---|----------|---|
| D1 | Nagpur, Maharashtra | City is fixed (~2,000 H3 cells) |
| D2 | H3 res-9 scoring; res-8 k-merge | Grid resolution is fixed |
| D3 | In-memory + SQLite append-only | Architecture is fixed |
| D4 | FastAPI + asyncio | Backend framework is fixed |
| D6 | Logistic (β, γ ≥ 0) | Scoring function is sigmoid-based |
| D8 | 5 nodes, 40-line FedAvg | No Flower; custom loop only |
| D9 | Blind scenario owner | You never see D/E/adversarial until Day 4 |

**If you think one should change, tell me FIRST. Don't silently change the spec.**

---

## 💻 Your APIs (What You Build)

### Day 1 (Stubs)
```
POST /ingest          → accepts event, validates schema, rejects PII, logs
GET /sse/events       → emits mock events every 3 sec
```

### Day 2 (Wire to Engine)
```
POST /ingest          → updates cell state, re-scores, emits SSE
GET /sse/events       → real engine updates
```

### Day 3 (Add Domains)
```
All above + power, transit, water, health, comms, road domains
```

### Day 4 (Add Evaluation)
```
GET /zones            → return zone polygons + drivers
GET /dispatch         → return intervention queue
GET /health           → system health
GET /eval/results     → IoU + ablations
GET /privacy/redteam  → attack results
```

---

## ✅ Phase 0–1 Success Criteria

### Phase 0 (Day 1, 16:00 UTC)
```
Event → /ingest → cell colour changes on map
```

### Phase 1 (Day 2, 12:00 UTC)
```
Baseline map renders
Remove one road edge → hospital_isolation changes (verified by unit test)
```

---

## 🎓 Key Numbers to Remember

| Metric | Target |
|--------|--------|
| Event latency | p95 ≤ 2 seconds |
| Dijkstra recompute | ≤ 100 ms |
| FedAvg round | ≤ 10 seconds |
| H3 cells (Nagpur) | ~2,000 |
| IoU on training scenarios | > 0.65 |
| Feed loss tolerance | 0–80% |
| Privacy: membership-inference AUC | ≤ 0.60 (with noise) |

---

## 📊 Spec Documents at a Glance

### requirements.md
- 7 user stories (identify zones, handle chaos, preserve privacy, etc.)
- 13 locked decisions (D1–D13)
- MUST/SHOULD/COULD scope tiers
- Cut order (Isolation Forest first; never cut k-merge)

### design.md
- System architecture (data → privacy → engine → API → frontend)
- Event schema (Pydantic, strict, no PII)
- Cell state model (stresses, confidence, decay)
- Risk model (logistic: β, γ ≥ 0)
- 6 REST API contracts with full schemas
- Baseline data (real downloads + simulated tables)
- Privacy (k-merge, noise, FedAvg)

### tasks.md
- Phase 0: 10 Alpha tasks, 9 Beta tasks (Day 1)
- Phase 1: 10 Alpha tasks, 9 Beta tasks (Day 2)
- Phases 2–8: Condensed summaries
- Your A1 checklist (~21 hours)
- Cut order

---

## 🤔 Common Questions

**Q: What if I don't understand something?**  
A: Ask A2 (your pair) immediately. If still unclear, escalate to team lead.

**Q: Can I use a different library?**  
A: No. The tech stack is locked (FastAPI, React, MapLibre, NetworkX, custom FedAvg).

**Q: What if I finish early?**  
A: Don't start Day 2 tasks. Code review your work, write tests, help others.

**Q: What if I find a bug in the spec?**  
A: Document it (GitHub issue or comment), alert team, escalate to organizer.

**Q: Can we change a locked decision?**  
A: Ask organizer. Likely answer: "Not without replanning from scratch."

---

## 📞 Who to Ask

| Question | Ask |
|----------|-----|
| "What's the event schema?" | A2 (until committed), then read the file |
| "How do I build /ingest?" | Read design.md section 3.1, ask A1 |
| "What's the risk model?" | Read design.md section 2.3, ask A2 |
| "Can I use library X?" | Ask A1, escalate to organizer if blocked |
| "I'm stuck on task Y" | Ask A2 (your pair) immediately |
| "I found a spec bug" | Document + alert team + organizer |

---

## 📍 Document Map

```
.kiro/
├── requirements.md      ← Core: what to build
├── design.md           ← Core: how to build
└── tasks.md            ← Core: your tasks

Root:
├── SPEC_SUMMARY.md     ← 5-min overview
├── TEAM_KICKOFF.md     ← Team alignment
├── DAY0_SETUP.md       ← Pre-Day-1 checklist
├── README_SPECS.md     ← A1's reference (comprehensive)
├── SPEC_DELIVERY.txt   ← Final checklist & status
├── START_HERE.md       ← This file
└── README_SPECS.md     ← Redo for A1 comprehensive reference
```

---

## ✨ Next Steps

### Before Day 1:

1. **Read the spec** (this file + the 3 core docs)
2. **Team alignment meeting** (confirm 13 locked decisions, blocker, data handoffs)
3. **Get stakeholder sign-off** (approval on all docs)
4. **Environment setup** (clone repo, verify tools)

### Day 1 00:00 UTC:

1. **Register OpenCellID** (5 min)
2. **Start event_schema.py with A2** (45 min)
3. **COMMIT event_schema.py** (01:00 UTC, unblocks team)
4. **Continue Phase 0 tasks** (Docker, APIs, integration test)

### Day 1 16:00 UTC:

- Phase 0 exit: event → map update works ✅

---

## 🎯 Your Success Metrics

**Day 1:** Schema committed; team unblocked  
**Day 2:** Baseline map + Dijkstra working  
**Day 3:** All 6 domains scoring; IoU A–C printed  
**Day 4:** Backend live; demo video recorded; results published

---

## 💪 You've Got This

This spec is:
- ✅ Complete (no ambiguity)
- ✅ Achievable (16–18 hours realistic for 4 days)
- ✅ Locked (13 decisions won't change)
- ✅ Clear (6 API contracts, 6 phases, your checklist)

Your job: Execute Phase 0 Day 1 → commit schema by 01:00 UTC → unblock team.

**Let's go! 🚀**

---

**Last Updated:** 2026-10-25  
**Branch:** `priyanshu`  
**Status:** ✅ READY FOR APPROVAL & PHASE 0 START
