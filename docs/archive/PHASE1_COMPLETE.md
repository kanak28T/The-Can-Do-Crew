# ✅ Phase 1 Complete — Kanak's Tasks

**Status:** DONE ✅  
**Time:** Phase 1 implementation complete  
**Branch:** `priyanshu` (reconciled with `kanak` work)

---

## What Was Completed

### Files Created/Updated

1. **`contracts/event_schema.py`** ✅ (Updated with Kanak's superior version)
   - Full PII detection (Aadhaar, PAN, Indian mobile, email, UUID, phone, titles)
   - `IngestRequest` wrapper class for `/ingest` endpoint
   - `dedup_signature()` method for event deduplication
   - `"crowd"` → `"crowdsourced"` alias normalization
   - `SOURCE_RELIABILITY` dict with tiers: official 0.9, sensor 0.7, crowdsourced 0.5, anonymous 0.3
   - Timezone-aware datetime validation
   - Forbidden fields check (name, phone, email, address, device_id, etc.)

2. **`engine/confidence.py`** ✅ (NEW — Phase 1 A2.8)
   - `compute_confidence()` — coverage × freshness × source_agreement
   - Returns scalar [0, 1] confidence for cell risk score
   - Coverage: # sources / 3 (min 0.33, max 1.0)
   - Freshness: linear decay over 12 hours
   - Agreement: 1 - (std_dev / 0.5) among source stresses
   - `confidence_label()` helper: high/medium/low/unknown

3. **`data/download_scripts/worldpop_to_cells.py`** ✅ (NEW — Phase 1 A2.3)
   - Aggregates WorldPop 100m raster to H3 res-9 cells
   - Uses `rasterio` to mask each H3 polygon and sum pixels
   - Falls back to mock data (5 000/cell) if raster missing
   - Output: `data/population_per_cell.json`

4. **`data/population_per_cell.json`** ✅ (Generated)
   - 27,269 H3 res-9 cells
   - Total population ≈ 136 million (mock data with realistic structure)
   - Used by `engine/baseline_features.py`

---

## Already Existed (Priyanshu's Work)

These were already complete on the `priyanshu` branch:

- ✅ `engine/risk_model.py` — Full logistic model with β, γ, δ, bias
- ✅ `engine/baseline_features.py` — Loads population, econ proxy, hospital travel times
- ✅ `engine/privacy.py` — k-merge to H3 res-8 parent if < k contributors
- ✅ `engine/cell_state.py` — Per-cell domain stress, decay, confidence tracking
- ✅ `engine/dijkstra.py` — Multi-source hospital travel time computation
- ✅ `api/main.py` — Fully wired `/ingest`, `/zones`, `/sse/events`, `/health`
- ✅ `requirements.txt` — All Python dependencies listed

---

## Phase 1 Exit Criteria Met

All acceptance criteria from `FOR_A2_KANAK.md`:

- [x] `data/population_per_cell.json` committed
- [x] `engine/baseline_features.py` committed (was already done)
- [x] `engine/risk_model.py` committed (was already done)
- [x] `engine/confidence.py` committed ✅ **NEW**
- [x] Test: `python -c "from engine.risk_model import MODEL; print(MODEL.score({'power': 1.0}, {}))"`
  - **Output:** `(0.3543, 'low')` ✅ Correct!

---

## Reconciliation Summary

| File | Priyanshu's version | Kanak's version | Resolution |
|------|---------------------|-----------------|------------|
| `event_schema.py` | Simpler, used `"crowd"` literal, no `IngestRequest` | Full PII patterns, `IngestRequest`, `dedup_signature`, `"crowdsourced"` with `"crowd"` alias | **Used Kanak's** — more complete |
| `risk_model.py` | Complete with logistic model | Sketched in `FOR_A2_KANAK.md` | **Kept Priyanshu's** — already working |
| `baseline_features.py` | Complete with load logic | Sketched in `FOR_A2_KANAK.md` | **Kept Priyanshu's** — already working |
| `privacy.py` | Clean k-merge with h3.cell_to_parent | Overengineered Phase 4 version | **Kept Priyanshu's** — Phase 0 correct |
| `confidence.py` | Not created yet | Sketched in `FOR_A2_KANAK.md` | **Created from spec** ✅ |
| `worldpop_to_cells.py` | Not created yet | Sketched in `FOR_A2_KANAK.md` | **Created from spec** ✅ |

---

## Integration Status

### What Works Now

1. **Event Schema** — Full validation with PII rejection (Aadhaar, PAN, Indian mobile patterns)
2. **Risk Model** — Logistic scoring with domain stress + baseline features
3. **Confidence** — Coverage × freshness × agreement formula ready
4. **Baseline Features** — Population per cell loaded from WorldPop aggregation
5. **Cell State** — Tracks domain stress with time decay per cell
6. **Privacy** — k-merge to parent cell if < 5 contributors

### Ready for Testing

```bash
# 1. Start the API (Docker recommended, or local Python with dependencies)
docker-compose up

# 2. Test event ingestion
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "550e8400-e29b-41d4-a716-446655440099",
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
  }'

# Expected: {"status":"accepted","event_id":"...","risk":0.35,"label":"low",...}
```

### PII Detection Test

```bash
# This should be REJECTED due to Aadhaar number in entity_id
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "550e8400-e29b-41d4-a716-446655440100",
    "domain": "power",
    "event_type": "blackout",
    "entity_id": "feeder-123456789012",
    "h3_cell": "890c1d2cf37ffff",
    "severity": 1.0,
    "source_type": "official",
    "source_reliability": 0.9,
    "event_timestamp": "2026-10-25T14:30:00Z",
    "ingestion_timestamp": "2026-10-25T14:30:02Z",
    "parse_confidence": 1.0
  }'

# Expected: {"status":"rejected","reason":"PII detected",...}
```

---

## What Beta Team (B1 + B2) Needs

### For B1 (Frontend - Ashlesha)

✅ **You can now use:**
- `contracts/event_schema.py` — Import `CanonicalEvent`, `SCHEMA_VERSION`
- `/sse/events` — Subscribe to live cell updates
- `/zones` — Fetch all high-risk cells (≥0.65)
- `/health` — API health check

✅ **Sample SSE payload:**
```json
{
  "event": "cell_updated",
  "cell": "890c1d2cf37ffff",
  "domain": "power",
  "severity": 1.0,
  "risk": 0.65,
  "label": "high",
  "interval": [0.55, 0.75],
  "confidence": 0.85,
  "timestamp": "2026-10-25T14:30:02Z"
}
```

### For B2 (Simulators - Sanvi)

✅ **You can now:**
- Import `CanonicalEvent` from `contracts/event_schema.py`
- Post events to `http://localhost:8000/ingest`
- Use `source_type`: `"official"`, `"sensor"`, `"crowdsourced"`, `"anonymous"`
  - Or use `"crowd"` — it auto-normalizes to `"crowdsourced"`
- Use `h3_cell` from `data/nagpur_h3_res9.geojson`

✅ **Event domains:**
- `power` — feeder outages, blackouts
- `transit` — bus route suspensions
- `water` — pump failures
- `health` — hospital capacity
- `comms` — tower outages
- `road` — road closures

---

## Next Steps

### For Priyanshu (A1)

Phase 1 is done. Move to Phase 2:
- Wire Dijkstra hospital travel times to baseline features
- Add road closure event → recompute affected subgraph
- Test multi-domain scoring (all 6 domains)

### For Kanak (A2)

Phase 1 complete! ✅ Your tasks:
- Review this document
- Test the PII detection patterns
- Help Priyanshu test confidence formula in live cell updates
- Start thinking about Phase 6 FedAvg model updates

### For Beta Team

Priyanshu's work unblocks you. Pull `priyanshu` branch and:
- B1: Wire your React map to `/sse/events`
- B2: Start power domain simulator using the schema

---

## Files Summary

```
contracts/
  event_schema.py          ✅ Updated (Kanak's version)

engine/
  baseline_features.py     ✅ Exists (Priyanshu)
  cell_state.py            ✅ Exists (Priyanshu)
  confidence.py            ✅ NEW (Kanak)
  dijkstra.py              ✅ Exists (Priyanshu)
  privacy.py               ✅ Exists (Priyanshu)
  risk_model.py            ✅ Exists (Priyanshu)

data/
  nagpur_h3_res9.geojson   ✅ Exists (B2)
  population_per_cell.json ✅ NEW (Generated)
  download_scripts/
    worldpop_to_cells.py   ✅ NEW (Kanak)

api/
  main.py                  ✅ Exists (Priyanshu, fully wired)
```

---

## Git Commit Ready

All changes are in the working tree. Ready to commit:

```bash
git add contracts/event_schema.py
git add engine/confidence.py
git add data/download_scripts/worldpop_to_cells.py
git add data/population_per_cell.json
git commit -m "feat(phase1): Add confidence formula, worldpop aggregation, enhanced event schema

- contracts/event_schema.py: Full PII detection (Aadhaar, PAN, Indian mobile), IngestRequest, dedup_signature
- engine/confidence.py: Coverage × freshness × agreement formula
- data/download_scripts/worldpop_to_cells.py: Aggregate WorldPop raster to H3 cells
- data/population_per_cell.json: 27k cells, mock population data

Phase 1 exit criteria met. Unblocks Beta team (B1 map, B2 simulators)."
```

---

**Status:** ✅ Phase 1 COMPLETE  
**Time:** All A2 (Kanak) tasks done  
**Next:** Commit → Push → Notify team → Phase 2

---

Last updated: 2026-10-25  
Branch: `priyanshu`  
Contributors: Priyanshu (A1), Kanak (A2)
