"""
UrbanPulse — Intervention Planner
===================================
Owner  : Kanak (A2) — Day 4 (Phase 5)

Greedy resource allocation: assigns limited response assets to High-risk
zones by maximising risk reduction per resource unit.

Plan section 8 (locked):
  Actions: shuttle, mobile_generator, water_tanker, road_crew,
           alert_relay, verify_report.
  Each action is a change to model inputs → benefit = re-scored risk drop
  weighted by population exposure, subject to resource counts.
  Greedy by benefit per resource unit.
  A human approves — the system never dispatches itself.
  After dispatch the zone is re-scored with the action applied.

Log entry fields: priority, zone, action, resource, trigger_evidence,
  expected_risk_drop (with interval), eta_minutes, status.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
import uuid


# ── Action definitions ─────────────────────────────────────────────────────

@dataclass
class ActionSpec:
    action_type:    str
    resource_name:  str
    domain_target:  str           # which domain stress it reduces
    stress_reduction: float       # how much it drops that domain's stress
    cost_units:     int = 1       # resource units consumed
    eta_minutes:    int = 20      # expected arrival time


ACTION_CATALOGUE: list[ActionSpec] = [
    ActionSpec("mobile_generator", "Mobile Generator 250kVA", "power",   0.80, cost_units=1, eta_minutes=25),
    ActionSpec("shuttle",          "Emergency Shuttle",        "transit", 0.75, cost_units=1, eta_minutes=15),
    ActionSpec("road_crew",        "PWD Road Clearance Crew",  "roads",   0.85, cost_units=1, eta_minutes=20),
    ActionSpec("water_tanker",     "Water Tanker 10kL",        "water",   0.70, cost_units=1, eta_minutes=30),
    ActionSpec("alert_relay",      "Emergency Comms Relay",    "comms",   0.80, cost_units=1, eta_minutes=10),
    ActionSpec("verify_report",    "Field Verification Team",  "health",  0.20, cost_units=1, eta_minutes=10),
]

# Default resource pool
DEFAULT_RESOURCES: dict[str, int] = {
    "mobile_generator": 3,
    "shuttle":          4,
    "road_crew":        3,
    "water_tanker":     3,
    "alert_relay":      4,
    "verify_report":    5,
}


# ── Dispatch log entry ─────────────────────────────────────────────────────

@dataclass
class DispatchEntry:
    dispatch_id:       str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    priority:          str = "P2"         # P1 | P2 | P3
    zone_id:           str = ""
    h3_cells:          list[str] = field(default_factory=list)
    action_type:       str = ""
    resource:          str = ""
    trigger_evidence:  list[str] = field(default_factory=list)
    risk_before:       float = 0.0
    risk_after:        float = 0.0
    expected_risk_drop: float = 0.0
    interval_before:   tuple[float, float] = (0.0, 1.0)
    eta_minutes:       int = 20
    status:            str = "proposed"   # proposed | approved | dispatched | expired
    created_at:        str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    population_exposed: float = 0.0

    def to_dict(self) -> dict:
        return {
            "dispatch_id":        self.dispatch_id,
            "priority":           self.priority,
            "zone_id":            self.zone_id,
            "action_type":        self.action_type,
            "resource":           self.resource,
            "trigger_evidence":   self.trigger_evidence,
            "risk_before":        self.risk_before,
            "risk_after":         self.risk_after,
            "expected_risk_drop": self.expected_risk_drop,
            "eta_minutes":        self.eta_minutes,
            "status":             self.status,
            "created_at":         self.created_at,
            "population_exposed": self.population_exposed,
        }


# ── In-memory dispatch log ─────────────────────────────────────────────────

_dispatch_log: list[DispatchEntry] = []


def get_dispatch_log() -> list[dict]:
    return [e.to_dict() for e in _dispatch_log]


def update_dispatch_status(dispatch_id: str, status: str) -> bool:
    """Update status of a dispatch entry. Returns True if found."""
    for entry in _dispatch_log:
        if entry.dispatch_id == dispatch_id:
            entry.status = status
            return True
    return False


# ── Planner ────────────────────────────────────────────────────────────────

def plan_interventions(
    zones: list[dict],
    population_lookup: dict[str, float] | None = None,
    resources: dict[str, int] | None = None,
) -> list[DispatchEntry]:
    """
    Greedy resource allocation across all High-risk zones.

    Args:
        zones            : list of zone dicts from zone_builder or /zones API.
                           Each must have: zone_id, cells, risk_max, risk_mean,
                           confidence, label, driver_contributions (optional).
        population_lookup: {h3_cell: population} — used for exposure weighting.
        resources        : available resource counts per action type.
                           Defaults to DEFAULT_RESOURCES.

    Returns:
        list[DispatchEntry] — sorted by priority (P1 first).
        Also appended to the global _dispatch_log.
    """
    from engine.risk_model import MODEL

    if resources is None:
        resources = dict(DEFAULT_RESOURCES)
    if population_lookup is None:
        population_lookup = {}

    # Only plan for High and Watch zones
    active_zones = [
        z for z in zones
        if z.get("label") in ("high", "watch") and not z.get("is_unknown", False)
    ]
    # Sort by risk descending
    active_zones.sort(key=lambda z: z.get("risk_max", z.get("risk", 0)), reverse=True)

    new_entries: list[DispatchEntry] = []

    for zone in active_zones:
        zone_id     = zone.get("zone_id", "Z??")
        cells       = zone.get("cells", [])
        risk        = float(zone.get("risk_max", zone.get("risk", 0)))
        interval    = tuple(zone.get("interval", [0.0, 1.0]))
        drivers     = zone.get("driver_contributions", {})
        domain_stress = zone.get("stress", {})
        baseline    = zone.get("baseline", {})

        # Population exposure for this zone
        pop = sum(population_lookup.get(c, 5000.0) for c in cells)

        # Find the best available action for this zone
        best_entry: Optional[DispatchEntry] = None
        best_benefit = 0.0

        for action in ACTION_CATALOGUE:
            if resources.get(action.action_type, 0) < action.cost_units:
                continue   # out of this resource

            # Counterfactual: apply action → re-score
            modified = {**domain_stress, action.domain_target: max(0.0,
                domain_stress.get(action.domain_target, 0) * (1 - action.stress_reduction)
            )}
            try:
                cf_p, _ = MODEL.score(modified, baseline)
            except Exception:
                cf_p = risk * 0.6   # fallback estimate

            drop = round(risk - cf_p, 4)
            # Benefit = risk drop × population (normalised)
            benefit = drop * (pop / 10000)

            if benefit > best_benefit:
                best_benefit = benefit
                # Build evidence from drivers
                evidence = []
                for drv, contrib in sorted(
                    drivers.items(), key=lambda x: abs(x[1]), reverse=True
                )[:3]:
                    evidence.append(f"{drv}: {round(abs(contrib)*100)}% contribution")

                best_entry = DispatchEntry(
                    priority          = "P1" if risk >= 0.75 else "P2" if risk >= 0.55 else "P3",
                    zone_id           = zone_id,
                    h3_cells          = cells,
                    action_type       = action.action_type,
                    resource          = action.resource_name,
                    trigger_evidence  = evidence,
                    risk_before       = round(risk, 3),
                    risk_after        = round(cf_p, 3),
                    expected_risk_drop= drop,
                    interval_before   = interval,
                    eta_minutes       = action.eta_minutes,
                    status            = "proposed",
                    population_exposed= round(pop),
                )

        if best_entry:
            # Deduct resource
            resources[best_entry.action_type] -= 1
            new_entries.append(best_entry)
            _dispatch_log.append(best_entry)

        # Also add verify action if there's a conflict flag
        if zone.get("conflict_flag") and resources.get("verify_report", 0) > 0:
            verify = DispatchEntry(
                priority         = "P2",
                zone_id          = zone_id,
                h3_cells         = cells[:1],
                action_type      = "verify_report",
                resource         = "Field Verification Team",
                trigger_evidence = ["Conflicting official vs crowd report"],
                risk_before      = round(risk, 3),
                risk_after       = round(risk, 3),
                expected_risk_drop = 0.0,
                eta_minutes      = 10,
                status           = "proposed",
            )
            resources["verify_report"] -= 1
            new_entries.append(verify)
            _dispatch_log.append(verify)

    new_entries.sort(key=lambda e: e.priority)
    return new_entries


def rescore_after_dispatch(
    dispatch_id: str,
    zone_cells: list[str],
    domain_stress: dict[str, float],
    baseline: dict[str, float],
) -> dict:
    """
    Re-score a zone after a dispatch is approved, applying the action.
    Called when status changes to 'dispatched'.

    Returns updated risk score for the zone.
    """
    from engine.risk_model import MODEL

    for entry in _dispatch_log:
        if entry.dispatch_id != dispatch_id:
            continue
        for action in ACTION_CATALOGUE:
            if action.action_type == entry.action_type:
                modified = {
                    **domain_stress,
                    action.domain_target: max(0.0,
                        domain_stress.get(action.domain_target, 0)
                        * (1 - action.stress_reduction)
                    ),
                }
                new_risk, new_label = MODEL.score(modified, baseline)
                return {
                    "dispatch_id": dispatch_id,
                    "risk_before": entry.risk_before,
                    "risk_after":  round(new_risk, 3),
                    "label_after": new_label,
                }
    return {}
