# UrbanPulse — Repo Ownership

## Team Alpha (Backend & Intelligence)

| Member | Branch | Primary Folders |
|--------|--------|-----------------|
| **Priyanshu** (A1) | `priyanshu` | `api/`, `engine/cell_state.py`, `engine/isolation_index.py`, `engine/zone_builder.py`, `deploy/` |
| **Kanak** (A2) | `kanak` | `engine/risk_model.py`, `engine/explainer.py`, `engine/planner.py`, `fed/`, `eval/` |

## Team Beta (Data & Frontend)

| Member | Branch | Primary Folders |
|--------|--------|-----------------|
| **Ashlesha** (B1) | `ashlesha` | `web/`, `contracts/scenario_format.yaml` (read-only) |
| **Sanvi** (B2) | `sanvi` | `sim/`, `data/`, `node/text_parser.py` |

## Shared Contract (never break without agreement from all four)

- `contracts/event_schema.py` — Pydantic canonical event model
- `contracts/scenario_format.yaml` — scenario YAML template
- `contracts/ground_truth_format.yaml` — ground-truth YAML template

## Branch → Main Flow

1. Each person works on their named branch.
2. PRs go to `main` only after the day's exit gate is met.
3. Schema changes require all four members to approve.

## Interface Boundary

`contracts/event_schema.py` is the ONLY file Alpha and Beta both import.
Any change = bump `SCHEMA_VERSION` + notify all four members.
