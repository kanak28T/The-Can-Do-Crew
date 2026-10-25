"""
UrbanPulse — Explainer
=======================
Owner  : Kanak (A2) — Day 4 (Phase 5)

Produces three explanation artefacts for every High-risk zone:

1. Driver contributions  — exact counterfactual re-scoring per domain
2. Causal graph          — expert-drawn hypothesis as a node/edge dict
3. Counterfactuals       — top-3 "what if" risk reductions

Plan D7 (locked):
  Exact counterfactual re-scoring: set one driver to normal, re-score,
  report the drop. Edge weights = driver contributions.
  Causal graph is an expert-drawn editable hypothesis — NOT discovered
  from data. State this clearly in the UI.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ── Driver contribution result ─────────────────────────────────────────────

@dataclass
class DriverContribution:
    driver:       str     # e.g. "hospital_isolation"
    domain:       str     # e.g. "roads"
    contribution: float   # risk drop when this driver is zeroed (positive = harmful)
    pct:          float   # % of total explained risk
    evidence:     list[str] = field(default_factory=list)  # human-readable causes


@dataclass
class ExplanationResult:
    zone_id:          str
    risk:             float
    interval:         tuple[float, float]
    confidence:       float
    drivers:          list[DriverContribution]
    counterfactuals:  list[dict]   # top-3 what-ifs
    causal_graph:     dict         # nodes + edges


# ── Causal graph definition (expert-drawn, plan D7) ───────────────────────
# This is a static hypothesis — not discovered from data.
# Edge weights are filled in at runtime from driver contributions.

CAUSAL_GRAPH_TEMPLATE = {
    "nodes": [
        {"id": "power_stress",       "label": "Grid Stress",          "domain": "power"},
        {"id": "water_loss",         "label": "Water Loss",           "domain": "water"},
        {"id": "road_stress",        "label": "Road Closure",         "domain": "roads"},
        {"id": "transit_loss",       "label": "Transit Loss",         "domain": "transit"},
        {"id": "hospital_isolation", "label": "Hospital Isolation",   "domain": "health"},
        {"id": "comms_loss",         "label": "Comms Dead Zone",      "domain": "comms"},
        {"id": "vulnerability",      "label": "Zone Vulnerability",   "domain": "output"},
    ],
    "edges": [
        # Cascade: power → water (feeder → pump)
        {"source": "power_stress",       "target": "water_loss",
         "label": "feeder → pump",       "weight": 0.0},
        # Cascade: power → comms (tower power loss)
        {"source": "power_stress",       "target": "comms_loss",
         "label": "tower power",         "weight": 0.0},
        # Isolation: road closure → transit loss
        {"source": "road_stress",        "target": "transit_loss",
         "label": "blocks routes",       "weight": 0.0},
        # Isolation: road + transit → hospital unreachable
        {"source": "road_stress",        "target": "hospital_isolation",
         "label": "blocks road access",  "weight": 0.0},
        {"source": "transit_loss",       "target": "hospital_isolation",
         "label": "cuts transit access", "weight": 0.0},
        # Warning failure: comms + hospital isolation
        {"source": "comms_loss",         "target": "hospital_isolation",
         "label": "warning dead zone",   "weight": 0.0},
        # All drivers → vulnerability output
        {"source": "power_stress",       "target": "vulnerability", "weight": 0.0},
        {"source": "water_loss",         "target": "vulnerability", "weight": 0.0},
        {"source": "road_stress",        "target": "vulnerability", "weight": 0.0},
        {"source": "transit_loss",       "target": "vulnerability", "weight": 0.0},
        {"source": "hospital_isolation", "target": "vulnerability", "weight": 0.0},
        {"source": "comms_loss",         "target": "vulnerability", "weight": 0.0},
    ],
    "note": "Expert-drawn causal hypothesis. Not discovered from data. Edge weights = driver contributions.",
}

# Domain → model input name mapping
_DOMAIN_TO_INPUT = {
    "power":   "power_stress",
    "transit": "transit_loss",
    "water":   "water_loss",
    "health":  "hospital_isolation",
    "comms":   "comms_loss",
    "roads":   "road_stress",
}

_INPUT_TO_DOMAIN = {v: k for k, v in _DOMAIN_TO_INPUT.items()}

# Human-readable evidence templates per driver
_EVIDENCE_TEMPLATES = {
    "power_stress":       "Feeder {entity} low voltage / blackout",
    "water_loss":         "Pump station failure — linked to power loss",
    "road_stress":        "Road {entity} closed",
    "transit_loss":       "Route {entity} suspended",
    "hospital_isolation": "Nearest open hospital > {value:.1f} km travel time",
    "comms_loss":         "Tower {entity} down — call-drop spike in area",
}


def explain_zone(
    zone_id:       str,
    h3_cells:      list[str],
    risk:          float,
    interval:      tuple[float, float],
    confidence:    float,
    domain_stress: dict[str, float],
    baseline:      dict[str, float],
    recent_events: list[dict] | None = None,
) -> ExplanationResult:
    """
    Produce full explanation for a High-risk zone.

    Args:
        zone_id       : e.g. "Z07"
        h3_cells      : list of H3 res-9 cell IDs in the zone
        risk          : current risk score (0-1)
        interval      : 90% bootstrap CI
        confidence    : coverage × freshness × agreement
        domain_stress : {domain: stress_0_to_1} for the zone centroid cell
        baseline      : {feature: value} from BaselineFeatures
        recent_events : recent CanonicalEvent dicts for evidence building

    Returns:
        ExplanationResult with drivers, counterfactuals, causal graph
    """
    from engine.risk_model import MODEL

    # ── 1. Driver contributions ─────────────────────────────────────────────
    contributions = MODEL.driver_contributions(domain_stress, baseline)

    total = sum(abs(v) for v in contributions.values()) or 1.0
    drivers = []

    for input_name, drop in contributions.items():
        domain = _INPUT_TO_DOMAIN.get(input_name, "unknown")
        pct    = round(abs(drop) / total * 100, 1)
        evidence = _build_evidence(input_name, domain_stress, baseline, recent_events)

        drivers.append(DriverContribution(
            driver=input_name,
            domain=domain,
            contribution=round(drop, 4),
            pct=pct,
            evidence=evidence,
        ))

    # Sort by magnitude descending
    drivers.sort(key=lambda d: abs(d.contribution), reverse=True)

    # ── 2. Counterfactuals (top-3 drivers) ─────────────────────────────────
    counterfactuals = []
    for driver in drivers[:3]:
        domain = _INPUT_TO_DOMAIN.get(driver.driver, "unknown")
        modified_stress = {**domain_stress, domain: 0.0}
        cf_p, _ = MODEL.score(modified_stress, baseline)
        drop_abs = round(risk - cf_p, 3)
        if drop_abs > 0.02:
            counterfactuals.append({
                "driver":      driver.driver,
                "action":      _action_label(driver.driver),
                "risk_before": round(risk, 3),
                "risk_after":  round(cf_p, 3),
                "risk_drop":   drop_abs,
                "label_after": "high" if cf_p >= 0.65 else "medium" if cf_p >= 0.40 else "low",
            })

    # ── 3. Causal graph with weights from contributions ─────────────────────
    causal_graph = _build_causal_graph(contributions)

    return ExplanationResult(
        zone_id=zone_id,
        risk=risk,
        interval=interval,
        confidence=confidence,
        drivers=drivers,
        counterfactuals=counterfactuals,
        causal_graph=causal_graph,
    )


def _build_evidence(
    input_name: str,
    domain_stress: dict[str, float],
    baseline: dict[str, float],
    recent_events: list[dict] | None,
) -> list[str]:
    """Build human-readable evidence strings for a driver."""
    evidence = []

    if input_name == "hospital_isolation":
        iso = baseline.get("hospital_isolation", 0.5)
        # Convert normalised isolation back to approximate km (rough)
        approx_km = iso * 5.0
        evidence.append(f"Nearest open clinic ~{approx_km:.1f} km travel time")
        if domain_stress.get("roads", 0) > 0.3:
            evidence.append("Road closure reducing access routes")
        if domain_stress.get("transit", 0) > 0.3:
            evidence.append("Transit suspension cutting public transport access")

    elif input_name == "power_stress":
        stress = domain_stress.get("power", 0)
        evidence.append(f"Grid stress at {round(stress * 100)}%")
        hist = baseline.get("grid_failure_rate", 0)
        if hist > 0.2:
            evidence.append(f"Historical failure rate: {round(hist * 100)}% of past months")

    elif input_name == "water_loss":
        evidence.append("Pump station failure — cascades from power stress")
        evidence.append(f"Water stress at {round(domain_stress.get('water', 0) * 100)}%")

    elif input_name == "transit_loss":
        stress = domain_stress.get("transit", 0)
        evidence.append(f"Transit stress at {round(stress * 100)}%")
        deficit = baseline.get("transit_deficit", 0)
        if deficit > 0.4:
            evidence.append("Area already has low transit coverage (baseline deficit)")

    elif input_name == "road_stress":
        stress = domain_stress.get("roads", 0)
        evidence.append(f"Road network stress at {round(stress * 100)}%")

    elif input_name == "comms_loss":
        stress = domain_stress.get("comms", 0)
        evidence.append(f"Communications stress at {round(stress * 100)}%")
        evidence.append("Warning systems may be unreachable in this area")

    elif input_name == "baseline":
        econ = baseline.get("economic_constraint", 0)
        evidence.append(f"Economic constraint index: {round(econ * 100)}%")
        evidence.append("Low-income area — limited self-evacuation capacity")

    # Add entity IDs from recent events if available
    if recent_events:
        domain = _INPUT_TO_DOMAIN.get(input_name, "")
        for ev in recent_events[-5:]:
            if ev.get("domain") == domain and ev.get("entity_id"):
                evidence.append(f"Event: {ev['event_type']} on {ev['entity_id']}")

    return evidence[:4]  # cap at 4 evidence items


def _action_label(input_name: str) -> str:
    """Human-readable remediation action for each driver."""
    return {
        "power_stress":       "Restore grid / deploy mobile generator",
        "water_loss":         "Restore pump station",
        "road_stress":        "Reopen road / clear blockage",
        "transit_loss":       "Restore bus service / deploy shuttle",
        "hospital_isolation": "Deploy mobile clinic or clear access route",
        "comms_loss":         "Deploy emergency comms relay",
        "baseline":           "Increase resource allocation for this area",
    }.get(input_name, "Investigate and restore service")


def _build_causal_graph(contributions: dict[str, float]) -> dict:
    """Fill edge weights in the causal graph template from driver contributions."""
    import copy
    graph = copy.deepcopy(CAUSAL_GRAPH_TEMPLATE)

    for edge in graph["edges"]:
        src = edge["source"]
        # Weight = contribution of the source driver (if it's a terminal driver)
        if src in contributions:
            edge["weight"] = round(abs(contributions[src]), 4)
        # For cascade edges, use the smaller of the two driver contributions
        elif src == "power_stress" and edge["target"] in ("water_loss", "comms_loss"):
            pw = abs(contributions.get("power_stress", 0))
            tw = abs(contributions.get(edge["target"], 0))
            edge["weight"] = round(min(pw, tw), 4)

    return graph


def explanation_to_dict(result: ExplanationResult) -> dict:
    """Serialise ExplanationResult to a JSON-safe dict for the API."""
    return {
        "zone_id":    result.zone_id,
        "risk":       result.risk,
        "interval":   list(result.interval),
        "confidence": result.confidence,
        "drivers": [
            {
                "driver":       d.driver,
                "domain":       d.domain,
                "contribution": d.contribution,
                "pct":          d.pct,
                "evidence":     d.evidence,
            }
            for d in result.drivers
        ],
        "counterfactuals": result.counterfactuals,
        "causal_graph":    result.causal_graph,
    }
