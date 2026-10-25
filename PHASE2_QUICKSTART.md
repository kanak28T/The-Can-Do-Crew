# Phase 2 Quick Start Guide 🚀

**Status:** ✅ Complete  
**Updated:** October 25, 2026

---

## 🎯 What You Can Do Now

### 1. Test All Simulators (1 minute)
```bash
python sim/master_sim.py --mode test
```
**Generates:** One event from each of the 6 domains (power, water, transit, health, comms, road)

### 2. Test Cascade Scenario (2 minutes)
```bash
python sim/master_sim.py --mode cascade --scenario power_water
```
**Shows:** Power outage → Water pump failure (cascade bonus in risk score)

### 3. Run Realistic Simulation (1 minute)
```bash
python sim/master_sim.py --mode realistic --duration 60
```
**Generates:** ~10-15 events with realistic timing and frequencies

### 4. Watch Live SSE Stream
```bash
# Terminal 1
curl -N http://localhost:8000/sse/events

# Terminal 2
python sim/master_sim.py --mode random --count 10 --interval 3
```
**Shows:** Real-time cell updates as events flow through system

---

## 📚 Simulator Reference

### Individual Simulators

```python
# Power domain
import sim.power_sim as power_sim
events = power_sim.blackout("feeder-F01")
events = power_sim.voltage_drop(severity=0.8)

# Water domain
import sim.water_sim as water_sim
events = water_sim.pump_failure("pump-P05")
events = water_sim.pressure_drop(severity=0.6)

# Transit domain
import sim.transit_sim as transit_sim
events = transit_sim.route_cancelled("route-R03")
events = transit_sim.severe_delay(severity=0.8)

# Health domain
import sim.health_sim as health_sim
events = health_sim.capacity_critical("hospital-H01")
events = health_sim.equipment_failure(severity=0.9)

# Comms domain
import sim.comms_sim as comms_sim
events = comms_sim.tower_down("tower-T12")
events = comms_sim.signal_degraded(severity=0.5)

# Road domain
import sim.road_sim as road_sim
events = road_sim.road_closed(cell="890c1d2cf37ffff")
events = road_sim.accident_reported(severity=0.7)
```

### Master Simulator Modes

| Mode | Command | Use Case |
|------|---------|----------|
| **test** | `--mode test` | Quick validation, one event per domain |
| **random** | `--mode random --count 20 --interval 5` | Stress testing, N events with delays |
| **cascade** | `--mode cascade --scenario power_water` | Test cascading failures |
| **realistic** | `--mode realistic --duration 3600` | Demo scenarios, realistic timing |

### Cascade Scenarios

- `power_water` — Power outage causes water pump failure
- `road_transit_health` — Road closure → transit delays → hospital access issues
- `comms_health` — Cell tower down → hospital coordination failure

---

## 🔍 How to Check Results

### API Endpoints

```bash
# Check system health
curl http://localhost:8000/health

# Get high-risk zones (risk ≥ 0.65)
curl http://localhost:8000/zones

# Check per-domain feed status
curl http://localhost:8000/health/feeds

# Watch live updates (SSE)
curl -N http://localhost:8000/sse/events
```

### Database Queries

```bash
# Check event log
sqlite3 db/events.db "SELECT COUNT(*) FROM events;"
sqlite3 db/events.db "SELECT domain, COUNT(*) FROM events GROUP BY domain;"
sqlite3 db/events.db "SELECT * FROM events ORDER BY inserted_at DESC LIMIT 5;"
```

---

## 🧪 Testing

### Run Phase 2 Tests
```bash
python test_phase2.py
```

**Tests:**
1. ✅ All 6 simulators generate valid events
2. ✅ Risk model scores all domains correctly
3. ✅ Cascade interactions show amplification bonus
4. ✅ Confidence formula weights coverage/freshness/agreement
5. ✅ Multi-domain stress aggregates properly
6. ✅ PII patterns still rejected
7. ✅ Baseline features load correctly

### Manual Test Sequence

```bash
# 1. Start API
docker-compose up -d

# 2. Generate power outage
python -c "import sim.power_sim as ps; import requests; 
events = ps.blackout('feeder-F01'); 
[requests.post('http://localhost:8000/ingest', json=e) for e in events]"

# 3. Check affected cells
curl http://localhost:8000/zones

# 4. Add water failure in same cells
python -c "import sim.water_sim as ws; import requests;
events = ws.pump_failure('pump-P05');
[requests.post('http://localhost:8000/ingest', json=e) for e in events]"

# 5. Check risk increase (cascade bonus)
curl http://localhost:8000/zones
# Risk should be higher than power + water individually
```

---

## 📊 Event Schema

All simulators generate events matching this schema:

```json
{
  "event_id": "uuid-here",
  "domain": "power|water|transit|health|comms|road",
  "event_type": "domain_specific_type",
  "entity_id": "feeder-F01",
  "h3_cell": "890c1d2cf37ffff",
  "severity": 0.0-1.0,
  "source_type": "official|sensor|crowd|anonymous",
  "source_reliability": 0.3-0.9,
  "event_timestamp": "2026-10-25T14:30:00Z",
  "ingestion_timestamp": "2026-10-25T14:30:02Z",
  "parse_confidence": 1.0,
  "scenario_tag": "optional"
}
```

---

## 🎨 For Frontend Developers

### SSE Event Format

```javascript
const eventSource = new EventSource('http://localhost:8000/sse/events');

eventSource.addEventListener('cell_updated', (e) => {
  const data = JSON.parse(e.data);
  /*
  {
    event: "cell_updated",
    cell: "890c1d2cf37ffff",
    domain: "power",
    severity: 1.0,
    risk: 0.72,
    label: "high",
    interval: [0.68, 0.76],
    confidence: 0.85,
    timestamp: "2026-10-25T14:30:00Z"
  }
  */
  updateHexColor(data.cell, data.label);
});
```

### Risk Labels

| Label | Risk Score | Color | Meaning |
|-------|-----------|-------|---------|
| **low** | 0.00-0.40 | 🟢 Green | Minor issues, no action needed |
| **medium** | 0.40-0.65 | 🟡 Yellow | Monitor, prepare resources |
| **high** | ≥0.65 | 🔴 Red | Dispatch resources immediately |
| **unknown** | N/A | ⚫ Grey | Stale/low-confidence data |

### Confidence Interpretation

| Confidence | Label | Meaning |
|-----------|-------|---------|
| ≥0.70 | **high** | Multiple fresh sources, high agreement |
| 0.40-0.70 | **medium** | Some sources, moderate freshness |
| <0.40 | **low** | Few sources, stale, or disagreement |
| 0.00 | **unknown** | No data or >12h stale |

---

## 📁 Key Files

```
sim/
├── master_sim.py      ← Main entry point (4 modes)
├── power_sim.py       ← Power domain events
├── water_sim.py       ← Water domain events
├── transit_sim.py     ← Transit domain events
├── health_sim.py      ← Health domain events
├── comms_sim.py       ← Comms domain events
└── road_sim.py        ← Road domain events

api/
└── main.py            ← Enhanced with road closure handling

test_phase2.py         ← Integration test suite
PHASE2_COMPLETE.md     ← Detailed completion report
PHASE2_QUICKSTART.md   ← This file
```

---

## 🐛 Troubleshooting

### Issue: "No module named 'sim.power_sim'"
**Solution:** Run from project root: `cd d:\IIITN\The-Can-Do-Crew`

### Issue: API connection refused
**Solution:** Start API: `docker-compose up -d` or `uvicorn api.main:app --reload`

### Issue: "File not found: feeder_cells.json"
**Solution:** Mapping tables already exist in `data/mapping_tables/` (created by Beta team)

### Issue: Simulator events rejected with PII error
**Solution:** Check entity_id doesn't match PII patterns (Aadhaar/PAN/mobile/email)

---

## 🚀 Next Steps: Phase 3

After Phase 2, move to:

1. **Feed Loss Simulation** — Drop 60% of events, test resilience
2. **Unknown State Handling** — Grey hex rendering when confidence <0.30
3. **Stale Data Detection** — Alert when feeds >12h old
4. **Confidence Analysis** — Document decay curves, recovery times

See `PROJECT_STATUS.md` → "What's Next: Phase 3" for details.

---

**Questions?** Check `PHASE2_COMPLETE.md` for full technical details.

**Found an issue?** All simulators tested and working as of 2026-10-25.
