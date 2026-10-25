"""
Feed Loss Simulator — Phase 3 (A1.1)

Simulates 60 % data-feed drop to test system resilience, confidence
degradation, and Unknown-state transitions.

Modes
-----
filter_wrapper  Wraps any simulator stream; drops events randomly.
domain_loss     Drops all events for specific domains.
source_loss     Drops events from specific source types.
partial         Drops a fraction, forwards the rest to POST /ingest.
replay_log      Reads db/events.db, replays with dropout, measures impact.

Usage
-----
    # Drop 60 % of crowd-source events
    python sim/feed_loss.py --mode source --drop crowd --rate 0.60

    # Drop 60 % of transit events
    python sim/feed_loss.py --mode domain --drop transit --rate 0.60

    # Generic 60 % random dropout
    python sim/feed_loss.py --mode random --rate 0.60 --count 40

    # Replay stored events with dropout (confidence analysis)
    python sim/feed_loss.py --mode replay --rate 0.60
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import argparse
import json
import random
import sqlite3
import time
import requests
from datetime import datetime, timezone
from typing import List, Dict, Optional

import sim.power_sim as power_sim
import sim.water_sim as water_sim
import sim.transit_sim as transit_sim
import sim.health_sim as health_sim
import sim.comms_sim as comms_sim
import sim.road_sim as road_sim

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")
DB_PATH = os.getenv("DATABASE_URL", "db/events.db")


# ── Core filter ───────────────────────────────────────────────────────────────

def apply_dropout(
    events: List[dict],
    drop_rate: float = 0.60,
    drop_source: Optional[str] = None,
    drop_domain: Optional[str] = None,
) -> tuple[List[dict], List[dict]]:
    """
    Split events into (forwarded, dropped).

    drop_rate:   Fraction to drop from the targeted set (0.0–1.0).
    drop_source: Only drop events with this source_type. None = all sources.
    drop_domain: Only drop events with this domain.   None = all domains.
    """
    forwarded, dropped = [], []
    for ev in events:
        targeted = True
        if drop_source and ev.get("source_type") != drop_source:
            targeted = False
        if drop_domain and ev.get("domain") != drop_domain:
            targeted = False

        if targeted and random.random() < drop_rate:
            dropped.append(ev)
        else:
            forwarded.append(ev)

    return forwarded, dropped


# ── HTTP helper ───────────────────────────────────────────────────────────────

def post_event(event: dict) -> dict:
    try:
        r = requests.post(f"{API_BASE}/ingest", json=event, timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"status": "error", "error": str(e)}


def post_batch(events: List[dict], label: str = "", delay_ms: int = 80) -> List[dict]:
    results = []
    for ev in events:
        res = post_event(ev)
        results.append(res)
        status = res.get("status", "?")
        risk   = res.get("risk", "N/A")
        conf   = res.get("confidence", "N/A")
        tag    = f"[{label}] " if label else ""
        print(f"  {tag}{ev['domain']:8} | {ev['event_type']:22} | "
              f"status={status} risk={risk} conf={conf}")
        if delay_ms > 0:
            time.sleep(delay_ms / 1000)
    return results


# ── Simulation modes ──────────────────────────────────────────────────────────

SIMULATORS = {
    "power":   power_sim,
    "water":   water_sim,
    "transit": transit_sim,
    "health":  health_sim,
    "comms":   comms_sim,
    "road":    road_sim,
}


def mode_random(rate: float, count: int, seed: Optional[int]):
    """Randomly drop `rate` fraction of all events."""
    if seed is not None:
        random.seed(seed)

    print(f"\n🎲 RANDOM DROPOUT MODE  rate={rate*100:.0f}%  count={count}\n")

    all_events = []
    for sim in SIMULATORS.values():
        all_events.extend(sim.random_stream(n=1, seed=seed))

    # Generate `count` events total
    events = []
    for _ in range(count):
        sim_name = random.choice(list(SIMULATORS))
        events.extend(SIMULATORS[sim_name].random_stream(n=1))

    forwarded, dropped = apply_dropout(events, drop_rate=rate)
    drop_pct = len(dropped) / max(len(events), 1) * 100

    print(f"Generated: {len(events)} | Forwarded: {len(forwarded)} | "
          f"Dropped: {len(dropped)} ({drop_pct:.1f}%)\n")

    print("── Forwarding to API ──")
    post_batch(forwarded, delay_ms=50)
    _print_confidence_summary()


def mode_source(source: str, rate: float, count: int, seed: Optional[int]):
    """Drop `rate` fraction of events from a specific source type."""
    if seed is not None:
        random.seed(seed)

    print(f"\n🔌 SOURCE DROPOUT MODE  source={source}  rate={rate*100:.0f}%  count={count}\n")

    events = []
    for _ in range(count):
        sim_name = random.choice(list(SIMULATORS))
        events.extend(SIMULATORS[sim_name].random_stream(n=1))

    forwarded, dropped = apply_dropout(events, drop_rate=rate, drop_source=source)
    targeted  = [e for e in events if e.get("source_type") == source]
    drop_pct  = len(dropped) / max(len(targeted), 1) * 100

    print(f"Generated: {len(events)} | Targeted ({source}): {len(targeted)} | "
          f"Dropped: {len(dropped)} ({drop_pct:.1f}%)\n")

    post_batch(forwarded, delay_ms=50)
    _print_confidence_summary()


def mode_domain(domain: str, rate: float, count: int, seed: Optional[int]):
    """Drop `rate` fraction of events from a specific domain."""
    if seed is not None:
        random.seed(seed)

    print(f"\n🏛️  DOMAIN DROPOUT MODE  domain={domain}  rate={rate*100:.0f}%  count={count}\n")

    events = []
    for _ in range(count):
        sim_name = random.choice(list(SIMULATORS))
        events.extend(SIMULATORS[sim_name].random_stream(n=1))

    forwarded, dropped = apply_dropout(events, drop_rate=rate, drop_domain=domain)
    targeted = [e for e in events if e.get("domain") == domain]
    drop_pct = len(dropped) / max(len(targeted), 1) * 100

    print(f"Generated: {len(events)} | Targeted ({domain}): {len(targeted)} | "
          f"Dropped: {len(dropped)} ({drop_pct:.1f}%)\n")

    post_batch(forwarded, delay_ms=50)
    _print_confidence_summary()


def mode_replay(rate: float, seed: Optional[int]):
    """
    Replay events from SQLite DB with dropout.
    Useful for measuring confidence/unknown-state degradation on real data.
    """
    if seed is not None:
        random.seed(seed)

    if not os.path.exists(DB_PATH):
        print(f"❌ DB not found: {DB_PATH}")
        print("   Run sim/master_sim.py first to populate the database.")
        return

    print(f"\n📼 REPLAY DROPOUT MODE  rate={rate*100:.0f}%  db={DB_PATH}\n")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM events ORDER BY event_timestamp ASC"
    ).fetchall()
    conn.close()

    if not rows:
        print("❌ No events in database — run a simulator first.")
        return

    # Reconstruct event dicts
    events = [dict(row) for row in rows]
    # Strip DB-only columns
    for ev in events:
        ev.pop("inserted_at", None)

    print(f"Loaded {len(events)} events from DB\n")

    forwarded, dropped = apply_dropout(events, drop_rate=rate)
    drop_pct = len(dropped) / max(len(events), 1) * 100
    print(f"Forwarded: {len(forwarded)} | Dropped: {len(dropped)} ({drop_pct:.1f}%)\n")

    # Stats before
    unknown_before = _get_unknown_cell_count()
    print(f"Unknown cells before replay: {unknown_before}")

    post_batch(forwarded, label="REPLAY", delay_ms=30)

    # Stats after
    unknown_after = _get_unknown_cell_count()
    print(f"\nUnknown cells after dropout replay: {unknown_after}")
    _print_confidence_summary()


def mode_gradual(rate_start: float, rate_end: float, steps: int, seed: Optional[int]):
    """
    Gradually increase dropout from rate_start to rate_end over `steps`.
    Demonstrates progressive confidence degradation.
    """
    if seed is not None:
        random.seed(seed)

    print(f"\n📉 GRADUAL DROPOUT MODE  {rate_start*100:.0f}% → {rate_end*100:.0f}%  steps={steps}\n")

    for i in range(steps):
        rate = rate_start + (rate_end - rate_start) * i / max(steps - 1, 1)
        events = []
        for _ in range(10):
            sim_name = random.choice(list(SIMULATORS))
            events.extend(SIMULATORS[sim_name].random_stream(n=1))

        forwarded, dropped = apply_dropout(events, drop_rate=rate)
        post_batch(forwarded, delay_ms=20)

        unknown_count = _get_unknown_cell_count()
        conf_avg = _get_avg_confidence()
        print(f"  Step {i+1:2d}/{steps}  dropout={rate*100:.0f}%  "
              f"unknown_cells={unknown_count}  avg_confidence={conf_avg:.3f}")
        time.sleep(1)

    print("\n✅ Gradual degradation complete")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_unknown_cell_count() -> int:
    try:
        r = requests.get(f"{API_BASE}/zones/unknown", timeout=3)
        if r.status_code == 200:
            return r.json().get("count", 0)
    except Exception:
        pass
    return -1   # API not available


def _get_avg_confidence() -> float:
    try:
        r = requests.get(f"{API_BASE}/zones?risk_min=0", timeout=3)
        if r.status_code == 200:
            zones = r.json().get("zones", [])
            if zones:
                return sum(z.get("confidence", 0) for z in zones) / len(zones)
    except Exception:
        pass
    return -1.0


def _print_confidence_summary():
    try:
        r = requests.get(f"{API_BASE}/zones?risk_min=0", timeout=3)
        if r.status_code == 200:
            zones = r.json().get("zones", [])
            if zones:
                confs = [z.get("confidence", 0) for z in zones]
                print(f"\n── Confidence Summary ──")
                print(f"  Cells tracked:   {len(zones)}")
                print(f"  Avg confidence:  {sum(confs)/len(confs):.3f}")
                print(f"  Min confidence:  {min(confs):.3f}")
                print(f"  Max confidence:  {max(confs):.3f}")
                low = sum(1 for c in confs if c < 0.30)
                print(f"  Low (<0.30):     {low}")
    except Exception:
        pass


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="UrbanPulse Feed-Loss Simulator"
    )
    parser.add_argument(
        "--mode", choices=["random", "source", "domain", "replay", "gradual"],
        default="random",
        help="Dropout mode"
    )
    parser.add_argument("--drop",  default="crowd",  help="Source type or domain to target")
    parser.add_argument("--rate",  type=float, default=0.60, help="Dropout fraction (default 0.60)")
    parser.add_argument("--count", type=int,   default=40,   help="Events to generate (non-replay)")
    parser.add_argument("--steps", type=int,   default=10,   help="Steps for gradual mode")
    parser.add_argument("--seed",  type=int,   default=None, help="Random seed")
    parser.add_argument("--api",   default=None, help="Override API URL")

    args = parser.parse_args()

    if args.api:
        global API_BASE
        API_BASE = args.api

    print(f"🎯 Target API: {API_BASE}")

    # Health-check
    try:
        h = requests.get(f"{API_BASE}/health", timeout=3).json()
        print(f"✅ API online: {h.get('cells', 0)} cells  v{h.get('version','?')}\n")
    except Exception as e:
        print(f"⚠️  API offline ({e}) — events will fail\n")

    if   args.mode == "random":
        mode_random(args.rate, args.count, args.seed)
    elif args.mode == "source":
        mode_source(args.drop, args.rate, args.count, args.seed)
    elif args.mode == "domain":
        mode_domain(args.drop, args.rate, args.count, args.seed)
    elif args.mode == "replay":
        mode_replay(args.rate, args.seed)
    elif args.mode == "gradual":
        mode_gradual(0.0, args.rate, args.steps, args.seed)


if __name__ == "__main__":
    main()
