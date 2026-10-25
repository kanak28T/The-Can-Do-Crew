# Day 0 Setup Guide (Before Phase 0 Begins)

**When:** Before Day 1 00:00 UTC  
**Duration:** ~30–45 minutes for the entire team  
**Outcome:** Everyone synced, repo ready, no surprises on Day 1

---

## Checklist for Everyone

### Step 1: Read the Spec (15 min each)

**All team members:**
1. Read `TEAM_KICKOFF.md` (5 min) — understand roles, blocker, success criteria
2. Read `SPEC_SUMMARY.md` (5 min) — understand what was delivered
3. Skim `.kiro/requirements.md` sections 2–4 (5 min) — understand user stories + locked decisions

**Your role-specific read (5 min):**
- **A1:** `.kiro/tasks.md` Phase 0 + Phase 1 Alpha rows
- **A2:** `.kiro/tasks.md` Phase 0 + Phase 1 Alpha rows (shared with A1)
- **B1:** `.kiro/tasks.md` Phase 0 + Phase 1 Beta rows
- **B2:** `.kiro/tasks.md` Phase 0 + Phase 1 Beta rows (shared with B1)

---

### Step 2: Alignment Meeting (15 min synchronous)

**Entire team (A1, A2, B1, B2):**

1. **A1 speaks (2 min):** "Here's what I'm building Day 1–4: backend APIs, event ingestion, scoring engine, deployment. The blocker is the event schema—we need that committed by 01:00 UTC Day 1."

2. **A2 speaks (2 min):** "I'm owning the risk model, security, and evaluation. I'll pair with A1 on the schema. Then I'm building the logistic scoring, confidence formula, driver contributions."

3. **B1 speaks (2 min):** "I'm building the frontend: React + MapLibre map shell, sector panel, causal graph, dispatch log, stress console. I wait for Alpha's `/ingest` and `/sse/events` endpoints."

4. **B2 speaks (2 min):** "I'm building all simulators and mapping tables, and I'm the blind scenario owner. My scenarios D, E, and adversarial stay locked until Day 4. I also download real baseline data (roads, WorldPop, wards, etc.)."

5. **Team alignment (7 min):**
   - Confirm the 13 locked decisions: "Anyone disagree with any? Now or never."
   - Confirm Day 1 blocker: "A1 + A2, you both understand event_schema.py must commit by 01:00 UTC?"
   - Confirm data sharing: "B1/B2, you know A2 will create `data/population_per_cell.json`? A1 will create `data/hospital_travel_times.json`?"
   - Confirm API contracts: "Everyone agrees with the 6 REST endpoints in design.md section 3?"
   - Confirm evaluation rigor: "B2 understands you never show D/E/adversarial to Alpha until Day 4?"

---

### Step 3: Environment Setup (10 min)

**Everyone:**

1. **Clone the repo (if not already):**
   ```bash
   cd ~
   git clone https://github.com/kanak28T/The-Can-Do-Crew.git
   cd The-Can-Do-Crew
   git checkout priyanshu  # A1's working branch
   ```

2. **Create your local .env file (if needed):**
   - A1: no secrets yet (Day 1 stub)
   - A2: no secrets yet
   - B1: no secrets yet
   - B2: Optional—keep OpenCellID key locally, don't commit

3. **Install base tools:**
   ```bash
   # Python (all)
   python --version  # >= 3.10

   # Node (B1)
   node --version   # >= 16
   npm install -g yarn vite

   # Docker (A1)
   docker --version
   docker-compose --version
   ```

4. **Verify you can push to `priyanshu`:**
   ```bash
   git config user.name "Your Name"
   git config user.email "your.email@example.com"
   git remote -v  # confirm origin points to GitHub
   git branch -a  # confirm priyanshu exists
   ```

---

### Step 4: Stakeholder Sign-Off

**Before 00:00 UTC Day 1, get approval from organizer / team lead:**

**Organizer/Lead reads and approves:**
- ✅ All 3 spec docs (requirements.md, design.md, tasks.md)
- ✅ Team kickoff doc
- ✅ Day 0 setup checklist
- ✅ MUST-HAVE scope (k-merge, 60% loss, drivers, IoU, footer)
- ✅ Cut order (Isolation Forest first)
- ✅ Timeline (4 days, 2×2 team)

**Sign-off:**
```
Approved by: _________________________
Role:        _________________________
Date/Time:   _________________________
```

---

## Day 0 Timeline (Recommended)

| Time | Action | Owner | Duration |
|------|--------|-------|----------|
| T-24h | All read spec docs | Everyone | 15 min |
| T-12h | Alignment meeting | A1, A2, B1, B2 | 15 min |
| T-6h | Environment setup | Everyone | 10 min |
| T-2h | Stakeholder sign-off | Lead | 5 min |
| T-0h | Kickoff: A1 registers OpenCellID | A1 | 5 min |
| T+0:15h | A1+A2 start event_schema.py | A1, A2 | 45 min |
| T+01:00h | **COMMIT event_schema.py** (blocker lifts) | A1 | 2 min |
| T+01:05h | All other Phase 0 tasks unblock | All | Parallel |

---

## Common Questions (FAQ)

### Q: What if OpenCellID approval takes >24 hours?

**A:** It probably will. That's OK. A1 can still do all other Day 1 tasks in parallel. On Day 2, if OpenCellID is approved, use it for tower mapping. If not, B2 generates synthetic tower locations based on population density. No blocker.

---

### Q: What if my local environment is missing something?

**A:** Flag it now. Examples:
- Don't have Python 3.10? Install before Day 1.
- Don't have Node 16? Install before Day 1.
- Don't have Docker? Buy time with A1 to set up Docker on Day 0 evening.

---

### Q: Can I start coding before stakeholder sign-off?

**A:** No. The spec is a contract. Once everyone signs off, the 13 locked decisions are final. Changing them mid-implementation = chaos. Wait for approval.

---

### Q: What if I finish my Day 1 tasks early?

**A:** Don't start Day 2 tasks. Instead:
1. Code review your Day 1 work (check logic, docstrings, error handling)
2. Write unit tests for your components
3. Help the other team member with their Day 1 tasks (pair programming)
4. Read ahead in the spec to understand Day 2 dependencies

---

### Q: What if I find a bug in the spec?

**A:** Document it immediately in the repo (create a GitHub issue or a comment in the spec doc). Alert the team on Slack/Discord. If it's critical, escalate to the organizer. Don't silently change the spec.

---

### Q: Who do I ask if I'm stuck?

**A:** In priority order:
1. **Your pair:** A1 ↔ A2, B1 ↔ B2
2. **Other team:** A1/A2 ↔ B1/B2 (cross-team question)
3. **Organizer/Lead:** Only for scope/timeline changes

---

### Q: Can I use a different library than what's specified?

**A:** No. The locked decisions include tech choices:
- Backend = FastAPI (not Flask, Django, etc.)
- Frontend = React + MapLibre (not Vue, Svelte, Leaflet)
- Federated learning = custom 40-line loop (not Flower, TensorFlow Federated)

If you find a critical blocker, ask A1/organizer ASAP. Don't switch stacks mid-project.

---

## Night Before Checklist (A1 Specifically)

**Evening before Day 1:**

- [ ] Clone repo + switch to `priyanshu` branch
- [ ] Verify you can push to GitHub
- [ ] Read TEAM_KICKOFF.md + your A1 checklist
- [ ] Read design.md section 3 (API contracts)
- [ ] Skim requirements.md section 4 (13 locked decisions)
- [ ] Get 8 hours sleep! 😴

**First thing Day 1 (00:00 UTC):**
- [ ] Register OpenCellID (5 min)
- [ ] Open PR: start writing `contracts/event_schema.py` with A2
- [ ] Goal: commit by 01:00 UTC

---

## Success = Everyone Reads + Understands

This is not a waterfall doc. It's a living spec. Your job on Day 0:
1. **Read the spec** → understand what you're building
2. **Align with teammates** → confirm shared understanding
3. **Get approval** → lock the contract
4. **Set up environment** → remove Day 1 surprises

If you're confused about anything, ask now. Day 0 is the time to clarify.

---

**Day 0 Goal:** Everyone reads, aligns, approves. No coding yet.  
**Day 1 Goal:** A1 + A2 commit event_schema.py by 01:00 UTC; unblock all other tasks.

---

Last updated: 2026-10-25  
Branch: `priyanshu`  
Status: Ready for Day 0 kickoff

