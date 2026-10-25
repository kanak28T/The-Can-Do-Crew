"""
Confidence Degradation Analysis — Phase 3 (A2)

Provides:
  decay_curve()         Confidence vs hours-old for each domain
  coverage_impact()     Confidence vs number of sources
  agreement_sensitivity() std_dev threshold that triggers Unknown
  recovery_time()       How long to recover from Unknown state

All functions return plain dicts/lists suitable for JSON serialisation.
Run standalone for a human-readable report:
    python engine/confidence_analysis.py
"""

from datetime import datetime, timezone, timedelta
from typing import List, Dict

from engine.confidence import compute_confidence, confidence_label
from engine.cell_state import STALE_THRESHOLD_HOURS, UNKNOWN_CONFIDENCE_THRESHOLD


# ── 1. Decay curve ─────────────────────────────────────────────────────────────

def decay_curve(
    source_type: str = "official",
    stress: float = 0.8,
    max_hours: float = 24.0,
    step_hours: float = 1.0,
) -> List[Dict]:
    """
    Compute confidence at each hour from 0 → max_hours with a single source.

    Returns:
        List of {"hours_old": float, "confidence": float, "label": str}
    """
    now = datetime.now(timezone.utc)
    results = []
    h = 0.0
    while h <= max_hours:
        ts = now - timedelta(hours=h)
        conf = compute_confidence(
            source_types=[source_type],
            last_updated=ts,
            source_stresses=[stress],
            stale_threshold_hours=STALE_THRESHOLD_HOURS,
        )
        results.append({
            "hours_old":  round(h, 2),
            "confidence": conf,
            "label":      confidence_label(conf),
        })
        h += step_hours
    return results


def decay_curve_all_sources() -> Dict[str, List[Dict]]:
    """Decay curves for each source type side-by-side."""
    return {
        src: decay_curve(source_type=src)
        for src in ["official", "sensor", "crowd", "anonymous"]
    }


# ── 2. Coverage impact ─────────────────────────────────────────────────────────

def coverage_impact(stress: float = 0.8) -> List[Dict]:
    """
    Confidence as a function of source count (1–5), all fresh.

    Returns:
        List of {"sources": int, "confidence": float, "label": str}
    """
    now = datetime.now(timezone.utc)
    results = []
    for n in range(1, 6):
        source_types = ["official"] * min(n, 1) + ["sensor"] * max(n - 1, 0)
        stresses = [stress] * n
        conf = compute_confidence(
            source_types=source_types,
            last_updated=now,
            source_stresses=stresses,
            stale_threshold_hours=STALE_THRESHOLD_HOURS,
        )
        results.append({
            "sources":    n,
            "confidence": conf,
            "label":      confidence_label(conf),
        })
    return results


def minimum_sources_for_known() -> int:
    """Return minimum source count that keeps confidence above Unknown threshold."""
    now = datetime.now(timezone.utc)
    for n in range(1, 10):
        conf = compute_confidence(
            source_types=["official"] * n,
            last_updated=now,
            source_stresses=[0.8] * n,
            stale_threshold_hours=STALE_THRESHOLD_HOURS,
        )
        if conf >= UNKNOWN_CONFIDENCE_THRESHOLD:
            return n
    return -1  # should never happen


# ── 3. Agreement sensitivity ───────────────────────────────────────────────────

def agreement_sensitivity(num_sources: int = 3) -> List[Dict]:
    """
    Confidence vs std_dev of source stresses (0 → 0.5).
    Shows the std_dev that causes confidence to drop below Unknown threshold.

    Returns:
        List of {"std_dev": float, "confidence": float, "triggers_unknown": bool}
    """
    now = datetime.now(timezone.utc)
    results = []
    for i in range(11):  # std from 0.0 to 0.50
        std = i * 0.05
        mean = 0.6
        # Construct stresses with desired std_dev
        if num_sources >= 2:
            import math
            half = std * math.sqrt(num_sources / (num_sources - 1))
            stresses = [mean + half] * (num_sources // 2) + [mean - half] * (num_sources - num_sources // 2)
        else:
            stresses = [mean]
        conf = compute_confidence(
            source_types=["official"] * num_sources,
            last_updated=now,
            source_stresses=stresses,
            stale_threshold_hours=STALE_THRESHOLD_HOURS,
        )
        results.append({
            "std_dev":         round(std, 3),
            "confidence":      conf,
            "label":           confidence_label(conf),
            "triggers_unknown": conf < UNKNOWN_CONFIDENCE_THRESHOLD,
        })
    return results


def std_dev_unknown_threshold(num_sources: int = 3) -> float:
    """Return the std_dev value at which confidence drops below the Unknown threshold."""
    rows = agreement_sensitivity(num_sources)
    for row in rows:
        if row["triggers_unknown"]:
            return row["std_dev"]
    return float("inf")  # never triggers


# ── 4. Recovery time analysis ──────────────────────────────────────────────────

def recovery_time(
    recovery_source: str = "official",
    stress: float = 0.8,
    unknown_hours: float = 14.0,   # how long cell was unknown before recovery event
) -> Dict:
    """
    Simulate adding a fresh event after a cell has been Unknown for `unknown_hours`.
    Returns confidence immediately after the recovery event.
    """
    # Fresh event right now
    now = datetime.now(timezone.utc)
    conf_after = compute_confidence(
        source_types=[recovery_source],
        last_updated=now,
        source_stresses=[stress],
        stale_threshold_hours=STALE_THRESHOLD_HOURS,
    )
    return {
        "recovery_source":    recovery_source,
        "was_unknown_hours":  unknown_hours,
        "confidence_after":   conf_after,
        "label_after":        confidence_label(conf_after),
        "is_known_after":     conf_after >= UNKNOWN_CONFIDENCE_THRESHOLD,
        "message": (
            "✅ Single fresh event recovers cell to Known state"
            if conf_after >= UNKNOWN_CONFIDENCE_THRESHOLD
            else "⚠️  Single event insufficient — need more sources or time"
        ),
    }


def recovery_comparison() -> List[Dict]:
    """Compare recovery speed for each source type."""
    return [
        recovery_time(recovery_source=src)
        for src in ["official", "sensor", "crowd", "anonymous"]
    ]


# ── 5. Full report ─────────────────────────────────────────────────────────────

def full_report() -> Dict:
    """All analyses bundled — call once, log or serialise."""
    return {
        "decay_curves":         decay_curve_all_sources(),
        "coverage_impact":      coverage_impact(),
        "min_sources_for_known": minimum_sources_for_known(),
        "agreement_sensitivity": agreement_sensitivity(num_sources=3),
        "std_dev_trigger":       std_dev_unknown_threshold(num_sources=3),
        "recovery_comparison":   recovery_comparison(),
        "constants": {
            "stale_threshold_hours":  STALE_THRESHOLD_HOURS,
            "unknown_conf_threshold": UNKNOWN_CONFIDENCE_THRESHOLD,
        },
    }


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json
    report = full_report()

    print("=" * 72)
    print("   CONFIDENCE DEGRADATION ANALYSIS REPORT")
    print("=" * 72)

    # 1. Decay curves summary
    print("\n── 1. Freshness Decay (official source, stress=0.8) ──────────────")
    print(f"{'Hours':>7}  {'Confidence':>12}  {'Label':>10}")
    for row in report["decay_curves"]["official"]:
        marker = " ← Unknown threshold" if row["confidence"] < UNKNOWN_CONFIDENCE_THRESHOLD and row["hours_old"] > 0 and report["decay_curves"]["official"][max(0, report["decay_curves"]["official"].index(row)-1)]["confidence"] >= UNKNOWN_CONFIDENCE_THRESHOLD else ""
        print(f"{row['hours_old']:>7.1f}  {row['confidence']:>12.4f}  {row['label']:>10}{marker}")

    # 2. Coverage impact
    print("\n── 2. Coverage Impact (fresh sources, stress=0.8) ───────────────")
    print(f"{'Sources':>8}  {'Confidence':>12}  {'Label':>10}")
    for row in report["coverage_impact"]:
        print(f"{row['sources']:>8}  {row['confidence']:>12.4f}  {row['label']:>10}")
    print(f"\n  Min sources for Known state: {report['min_sources_for_known']}")

    # 3. Agreement sensitivity
    print("\n── 3. Agreement Sensitivity (3 sources, mean=0.6) ───────────────")
    print(f"{'Std Dev':>8}  {'Confidence':>12}  {'Label':>10}  {'Unknown?':>9}")
    for row in report["agreement_sensitivity"]:
        flag = " ← !" if row["triggers_unknown"] else ""
        print(f"{row['std_dev']:>8.3f}  {row['confidence']:>12.4f}  {row['label']:>10}  "
              f"{'YES' if row['triggers_unknown'] else 'no':>9}{flag}")
    print(f"\n  std_dev that triggers Unknown: {report['std_dev_trigger']}")

    # 4. Recovery comparison
    print("\n── 4. Recovery Time (after 14h Unknown) ─────────────────────────")
    print(f"{'Source':>12}  {'Conf After':>12}  {'Label':>10}  {'Known?':>7}")
    for row in report["recovery_comparison"]:
        print(f"{row['recovery_source']:>12}  {row['confidence_after']:>12.4f}  "
              f"{row['label_after']:>10}  {'YES' if row['is_known_after'] else 'no':>7}")

    print("\n" + "=" * 72)
    print("CONSTANTS")
    print(f"  stale_threshold_hours:   {STALE_THRESHOLD_HOURS}h")
    print(f"  unknown_conf_threshold:  {UNKNOWN_CONFIDENCE_THRESHOLD}")
    print("=" * 72)
