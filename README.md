# UrbanPulse

**Hackathon: Theme 2, Problem 3 — "The Critical 1%: Hidden Community Vulnerability"**

A privacy-preserving spatial intelligence engine that detects emerging vulnerability zones
in Nagpur, Maharashtra before they become full emergencies.

---

## Team

| Name | Role | Branch |
|------|------|--------|
| Priyanshu | Backend / API / Infra | `priyanshu` |
| Kanak | Engine / Risk Model / Federated | `kanak` |
| Ashlesha | Frontend / Dashboard | `ashlesha` |
| Sanvi | Data / Simulators / Scenarios | `sanvi` |

---

## Repo Layout

```
contracts/      Shared schemas (event, scenario, ground-truth) — DO NOT break
data/           Download scripts + mapping tables (large files gitignored)
sim/            Event generators, messy-text writer, scenario YAML files
node/           Per-zone parser and privacy gateway
engine/         Cell state, isolation index, risk model, explainer, planner
fed/            FedAvg trainer, Red-Team script
api/            FastAPI: ingest, SSE, zones, dispatch, health
web/            React + MapLibre dashboard
eval/           IoU harness, feed-loss tests, ablations, calibration
deploy/         Docker Compose, cloud config
```

---

## Data Sources

| Dataset | Type | Licence |
|---------|------|---------|
| OSM road network | Real baseline | ODbL |
| OSM hospitals/clinics | Real baseline | ODbL |
| WorldPop India 100m | Real baseline | CC BY 4.0 |
| Nagpur ward boundaries | Real baseline | ODbL |
| VIIRS nighttime lights | Real baseline | Public domain (NASA) |
| Census 2011 ward data | Real baseline (dated) | Government open data |
| OpenCellID towers | Real baseline | CC BY |
| All live feeds (transit, power, water, etc.) | **Simulated** | N/A |
| Ground-truth zones | **Simulated** | N/A |

> Live feeds are simulated. This is clearly labelled in the app footer.

---

## Quickstart

```bash
# 1. Clone
git clone https://github.com/kanak28T/The-Can-Do-Crew.git
cd The-Can-Do-Crew

# 2. Download baseline data
python data/download_scripts/download_all.py

# 3. Start backend
docker compose up --build

# 4. Start frontend
cd web && npm install && npm run dev
```

---

## Privacy

- Zero PII. No names, phone numbers, device IDs or individual location traces.
- k-merge: cells with fewer than k contributors merge to H3 res-8 parent.
- All federated updates are clipped and noised before sharing.
- Red-Team results shown in the Privacy panel.
