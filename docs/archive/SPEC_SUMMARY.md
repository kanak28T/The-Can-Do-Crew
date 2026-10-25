# UrbanPulse: Spec Package Summary

**Status:** Ready for Review & Approval  
**Generated:** 2026-10-25  
**For:** Team Alpha (A1 Priyanshu + A2), Team Beta (B1 + B2)

---

## Three Spec Documents Created

All documents are in `.kiro/` and are ready for stakeholder approval.

### 1. **requirements.md** (~400 lines)
User stories with EARS acceptance criteria covering:
- 7 critical user stories (identify zones, handle chaos, preserve privacy, explain drivers, allocate resources, trust provenance, detect patterns)
- Non-functional requirements (latency, reliability, privacy, usability, data quality)
- 13 locked decisions (D1–D13) that are non-negotiable
- Scope tiers (MUST, SHOULD, COULD) with cut order
- Approval gate before Phase 0

**Key Points for A1:**
- You own backend, engine, risk model, eval
- Core responsibility: making events flow through `/ingest` → scoring → SSE output
- Privacy is mandatory (not optional)

---

### 2. **design.md** (~500 lines)
System architecture, data models, API contracts, and sequences covering:
- System architecture diagram (data sources → privacy gateway → engine → API → frontend)
- Canonical event schema (Pydantic, strict, no PII)
- Cell state model (domain stresses, confidence, risk intervals)
- Risk model (logistic regression: β, γ ≥ 0 with baseline + interaction terms)
- **6 REST API contracts** (POST /ingest, GET /sse/events, GET /zones, GET /dispatch, POST /dispatch/{id}/approve, GET /health, GET /eval/results, GET /privacy/redteam)
- Data flow diagrams (ingest → map, road closure → Dijkstra, scenario replay)
- Baseline data table (real downloads + simulated mapping tables)
- Frontend component architecture
- Evaluation harness sketch
- Privacy implementation (k-merge, noise, FedAvg)

**Key Points for A1:**
- `/ingest` must validate schema, reject PII, log to SQLite, update cell state, emit SSE
- Event latency target: p95 ≤ 2 sec (posted to map update)
- Dijkstra recompute target: ≤ 100 ms for 2 km radius
- FedAvg: 5 in-process nodes, custom 40-line loop, no Flower

---

### 3. **tasks.md** (~600 lines)
**Ordered, dependency-aware task breakdown for Phases 0–8** with:
- **Dependency map** showing Phase 0 is blocked on `event_schema.py` (A0.3)
- **Phase 0 (Day 1):** 10 Alpha tasks, 9 Beta tasks; exit: schema locked, schema commit is BLOCKER
- **Phase 1 (Day 2):** 10 Alpha tasks, 9 Beta tasks; exit: baseline map renders, road closure changes hospital_isolation
- **Phases 2–8:** Condensed summaries (full details in Phase 0–1)
- **A1-specific checklist** (~21 hours across 4 days)
- **Cut order** (Isolation Forest first, never cut k-merge + PII + 60% loss + drivers + IoU)

**Key A1 Milestones:**
- **Day 1:** Docker + schema (BLOCKER) + `/ingest` stub + SSE mock (4–5 hrs)
- **Day 2:** Dijkstra + cell state + logistic scoring + wire to API (4–5 hrs)
- **Day 3:** Multi-domain + road recompute + 60% loss + IoU A–C (4–5 hrs)
- **Day 4:** FedAvg + Red-Team + deploy + eval endpoints (4–5 hrs)

---

## What You (A1) Do Next

### Immediate (Before Spec Approval)

1. **Review the 3 spec documents** (`.kiro/requirements.md`, `design.md`, `tasks.md`)
   - Confirm the 13 locked decisions (D1–D13 in requirements.md) are non-negotiable
   - Confirm the A1-specific task checklist is realistic for you
   - Confirm API contracts (design.md section 3) are clear

2. **Share with A2 + B1 + B2** for alignment meeting
   - Confirm role ownership (A1 backend/engine, A2 modeling/security, B1 frontend, B2 data/sim)
   - Confirm Day 1 dependency: all work blocked on A0.3 (event_schema.py)
   - Confirm data locations and format

3. **Stakeholder sign-off** (team lead / organizer)
   - Approval on all MUST-HAVE requirements
   - Approval on cut order (especially: NEVER CUT list)

---

### Day 1 Start (After Approval)

**First task (literally first):** A1.1 Register OpenCellID (5 min, async approval wait)  
**Blocking task (do ASAP):** A0.3 Write `contracts/event_schema.py` with A2 (45 min, BLOCKER for entire team)

---

## Key Assumptions Baked Into Spec

1. **Team size:** Exactly 2×2 people (A1, A2, B1, B2)
2. **Available time:** Exactly 4 working days (~8–10 hours/day)
3. **Pilot city:** Nagpur, Maharashtra (fixed; not changeable)
4. **Spatial resolution:** H3 res-9 for scoring (~2,000 cells); res-8 for k-merge (fixed)
5. **Backend:** FastAPI + asyncio; in-memory + SQLite append-only log (fixed)
6. **Frontend:** React + MapLibre GL (fixed)
7. **Risk model:** Logistic (β, γ ≥ 0) with interactions; not hand-weighted linear sum (fixed)
8. **Evaluation:** Blind scenario owner; held-out families never fitted (fixed)
9. **Privacy:** k-anonymity ≥ 5 + noise; membership-inference AUC ≤ 0.60 (fixed)
10. **FedAvg:** 5 in-process nodes, custom 40-line loop (fixed, not Flower or other framework)

---

## MUST-HAVE Checklist (Never Cut)

- [ ] k-merge + PII scrubbing (Phases 0, 6)
- [ ] 60% feed-loss handling + Unknown state (Phase 3)
- [ ] Driver contributions + causal graph (Phases 3, 5)
- [ ] Dispatch log (Phases 5–8)
- [ ] IoU on ≥4 scenarios (Phase 7)
- [ ] Real-vs-simulated footer label (Phase 0, always visible)

---

## How to Use This Spec

**For implementation:**
- Reference `tasks.md` for your daily task list
- Reference `design.md` for API contracts and data models
- Reference `requirements.md` for acceptance criteria

**For Q&A during development:**
- "What's the event schema?" → `design.md` section 2.1
- "What's the /ingest contract?" → `design.md` section 3.1
- "What's my task for Day 2?" → `tasks.md` Phase 1 table
- "What happens if we cut Isolation Forest?" → `tasks.md` cut order

**For integration gates:**
- Phase 0 exit: Post event to `/ingest` → cell colour changes on map ✓
- Phase 1 exit: Road closure → hospital_isolation change measurable ✓
- Phase 3 exit: All 6 domains score; 60% loss → grey cells ✓
- Day 4 exit: Public URL live; demo video recorded ✓

---

## Files to Create Next (Pending Approval)

After stakeholder approves this spec, create:

1. **`contracts/event_schema.py`** (Pydantic model, strict)
2. **`contracts/scenario_format.yaml`** (template)
3. **`contracts/ground_truth_format.yaml`** (template)
4. **`docker-compose.yml`** (FastAPI + SQLite)
5. **`.gitignore`** (Python, Node, data/, secrets)
6. **`README.md`** (architecture, setup, demo)

---

## Contact & Clarifications

If anything in the spec is unclear or conflicts with your understanding:
1. Flag it before Day 1 starts
2. Document the conflict in a comment in the spec file
3. Get alignment with A2, B1, B2 before proceeding

**Do NOT silently change the spec.** If you think a locked decision should change, say so first.

---

**Spec Status:** ✅ Ready for approval  
**Next:** Stakeholder sign-off → Day 1 begins → Phase 0 implementation

---

Last updated: 2026-10-25  
Branch: `priyanshu`  
Commit: See git log for `event_schema.py` blocker message
