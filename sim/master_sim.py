"""
Master simulator — orchestrates all 6 domain simulators.
Generates realistic multi-domain events and posts to API.

Usage:
    python sim/master_sim.py --mode random --count 20 --interval 5
    python sim/master_sim.py --mode cascade --scenario power_water_cascade
    python sim/master_sim.py --mode realistic --duration 3600
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import time
import random
import argparse
import requests
from typing import List, Dict
from datetime import datetime

# Import all domain simulators
import sim.power_sim as power_sim
import sim.water_sim as water_sim
import sim.transit_sim as transit_sim
import sim.health_sim as health_sim
import sim.comms_sim as comms_sim
import sim.road_sim as road_sim


API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")


def post_event(event: dict) -> dict:
    """Post a single event to /ingest endpoint."""
    try:
        response = requests.post(f"{API_BASE}/ingest", json=event, timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ POST failed: {e}")
        return {"status": "error", "error": str(e)}


def post_batch(events: List[dict], delay_ms: int = 100):
    """Post multiple events with optional delay between them."""
    results = []
    for i, event in enumerate(events):
        result = post_event(event)
        results.append(result)
        
        # Print summary
        status = result.get("status", "unknown")
        domain = event.get("domain", "?")
        event_type = event.get("event_type", "?")
        risk = result.get("risk_score", result.get("risk", "N/A"))
        label = result.get("risk_label", result.get("label", ""))
        
        if status == "accepted":
            print(f"✅ [{i+1}/{len(events)}] {domain:8} | {event_type:20} | Risk: {risk:.3f} ({label})")
        else:
            reason = result.get("reason", "unknown")
            print(f"❌ [{i+1}/{len(events)}] {domain:8} | {event_type:20} | {reason}")
        
        if delay_ms > 0 and i < len(events) - 1:
            time.sleep(delay_ms / 1000)
    
    return results


# ────────────────────────────────────────────────────────────────────────────────
# Simulation Modes
# ────────────────────────────────────────────────────────────────────────────────

def random_mode(count: int = 20, interval: int = 5, seed: int = None):
    """Generate random events from all domains."""
    if seed:
        random.seed(seed)
    
    print(f"\n🎲 RANDOM MODE: {count} events, {interval}s interval\n")
    
    simulators = [
        ("power", power_sim),
        ("water", water_sim),
        ("transit", transit_sim),
        ("health", health_sim),
        ("comms", comms_sim),
        ("road", road_sim),
    ]
    
    for i in range(count):
        domain_name, sim = random.choice(simulators)
        events = sim.random_stream(n=1, seed=None)
        
        print(f"\n── Event {i+1}/{count} ({domain_name}) ──")
        post_batch(events, delay_ms=50)
        
        if i < count - 1:
            print(f"\n⏳ Waiting {interval}s...")
            time.sleep(interval)


def cascade_mode(scenario: str = "power_water"):
    """Simulate cascading failures across domains."""
    print(f"\n⚠️  CASCADE MODE: {scenario}\n")
    
    scenarios = {
        "power_water": [
            ("Power outage", power_sim.blackout("feeder-F01", scenario_tag=scenario)),
            ("Wait 10s", None),
            ("Water pump fails (depends on power)", water_sim.pump_failure("pump-P05", scenario_tag=scenario)),
        ],
        "road_transit_health": [
            ("Road closure", road_sim.road_closed(scenario_tag=scenario)),
            ("Wait 5s", None),
            ("Transit delays (rerouting)", transit_sim.severe_delay(scenario_tag=scenario)),
            ("Wait 5s", None),
            ("Hospital access degraded", health_sim.capacity_high(scenario_tag=scenario)),
        ],
        "comms_health": [
            ("Cell tower down", comms_sim.tower_down(scenario_tag=scenario)),
            ("Wait 5s", None),
            ("Hospital unable to coordinate", health_sim.equipment_failure(scenario_tag=scenario)),
        ],
    }
    
    steps = scenarios.get(scenario)
    if not steps:
        print(f"❌ Unknown scenario: {scenario}")
        print(f"Available: {', '.join(scenarios.keys())}")
        return
    
    for description, events in steps:
        print(f"\n── {description} ──")
        if events is None:
            time.sleep(10)
            continue
        post_batch(events, delay_ms=100)
        time.sleep(2)


def realistic_mode(duration: int = 3600, seed: int = None):
    """Simulate realistic event stream for N seconds."""
    if seed:
        random.seed(seed)
    
    print(f"\n🏙️  REALISTIC MODE: {duration}s simulation\n")
    
    # Event frequency per domain (events per hour)
    frequencies = {
        "power": 5,      # ~5 power events/hour
        "water": 3,      # ~3 water events/hour
        "transit": 10,   # ~10 transit events/hour (busiest)
        "health": 2,     # ~2 health events/hour
        "comms": 4,      # ~4 comms events/hour
        "road": 8,       # ~8 road events/hour
    }
    
    simulators = {
        "power": power_sim,
        "water": water_sim,
        "transit": transit_sim,
        "health": health_sim,
        "comms": comms_sim,
        "road": road_sim,
    }
    
    start_time = time.time()
    event_count = 0
    
    while time.time() - start_time < duration:
        # Pick domain based on frequency weights
        domain = random.choices(
            list(frequencies.keys()),
            weights=list(frequencies.values())
        )[0]
        
        sim = simulators[domain]
        events = sim.random_stream(n=1, seed=None)
        
        print(f"\n── Event {event_count+1} ({domain}) at T+{int(time.time()-start_time)}s ──")
        post_batch(events, delay_ms=50)
        event_count += 1
        
        # Random wait (realistic inter-event timing)
        wait = random.expovariate(1.0 / 60)  # Mean 60s between events
        wait = min(wait, 300)  # Cap at 5 minutes
        print(f"⏳ Next event in {wait:.1f}s...")
        time.sleep(wait)
    
    print(f"\n✅ Simulation complete: {event_count} events in {duration}s")


def test_mode():
    """Run one event from each domain to test integration."""
    print("\n🧪 TEST MODE: One event per domain\n")
    
    test_events = [
        ("Power", power_sim.voltage_drop("feeder-F01", severity=0.8, scenario_tag="test")),
        ("Water", water_sim.pressure_drop("pump-P05", severity=0.6, scenario_tag="test")),
        ("Transit", transit_sim.severe_delay(scenario_tag="test")),
        ("Health", health_sim.capacity_high(scenario_tag="test")),
        ("Comms", comms_sim.signal_degraded(scenario_tag="test")),
        ("Road", road_sim.accident_reported(scenario_tag="test")),
    ]
    
    for domain, events in test_events:
        print(f"\n── Testing {domain} ──")
        results = post_batch(events, delay_ms=100)
        time.sleep(1)
    
    print("\n✅ Test complete — check /zones endpoint for results")


# ────────────────────────────────────────────────────────────────────────────────
# CLI
# ────────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="UrbanPulse Multi-Domain Event Simulator")
    parser.add_argument("--mode", choices=["random", "cascade", "realistic", "test"], default="test",
                        help="Simulation mode")
    parser.add_argument("--count", type=int, default=20,
                        help="Number of events (random mode)")
    parser.add_argument("--interval", type=int, default=5,
                        help="Seconds between events (random mode)")
    parser.add_argument("--scenario", default="power_water",
                        help="Cascade scenario name (cascade mode)")
    parser.add_argument("--duration", type=int, default=3600,
                        help="Simulation duration in seconds (realistic mode)")
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed for reproducibility")
    parser.add_argument("--api", default=None,
                        help="Override API base URL (default: http://localhost:8000)")
    
    args = parser.parse_args()
    
    if args.api:
        global API_BASE
        API_BASE = args.api
    
    print(f"🎯 Target API: {API_BASE}")
    
    # Check API health
    try:
        health = requests.get(f"{API_BASE}/health", timeout=3).json()
        print(f"✅ API online: {health.get('cells', 0)} cells tracked\n")
    except Exception as e:
        print(f"⚠️  API health check failed: {e}")
        print("Continuing anyway...\n")
    
    # Run selected mode
    if args.mode == "random":
        random_mode(count=args.count, interval=args.interval, seed=args.seed)
    elif args.mode == "cascade":
        cascade_mode(scenario=args.scenario)
    elif args.mode == "realistic":
        realistic_mode(duration=args.duration, seed=args.seed)
    elif args.mode == "test":
        test_mode()


if __name__ == "__main__":
    main()
