"""
UrbanPulse — Transport Domain Simulator (Task B2.6)
===================================================
Simulates realistic public transit disruptions across Nagpur's transit network.
Reads route-to-H3 mappings from data/mapping_tables/route_cells.json
(with fallback to data/nagpur_transit.geojson).

Produces:
1. Structured CanonicalEvent stream (domain='transit', event_type='bus_suspended', etc.)
2. Unstructured noisy text alerts (matching node/text_parser.py patterns)

Supports CLI flags:
  --interval: Delay between event bursts in seconds (default: 2.0)
  --burst: Number of events to emit before exiting (default: 0 = continuous)
  --output: Destination ('stdout', filepath, or HTTP URL)
  --format: Event format ('canonical', 'text', or 'both')
  --scenario: Optional scenario tag (e.g. 'transit_strike', 'monsoon_rain')
"""

import argparse
import json
import os
import random
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import urllib.request
import urllib.error

# Ensure workspace root is in sys.path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from contracts.event_schema import CanonicalEvent, SOURCE_RELIABILITY

ROUTE_CELLS_PATH = ROOT / "data" / "mapping_tables" / "route_cells.json"
TRANSIT_GEOJSON_PATH = ROOT / "data" / "nagpur_transit.geojson"

# Realistic transport disruption types and severities
EVENT_TYPES = [
    ("bus_suspended", 0.85, "Bus route {num} suspended"),
    ("bus_suspended", 0.90, "Route {num} cancelled due to breakdown"),
    ("transit_disruption", 0.75, "Major disruption on route {num} near Sitabuldi"),
    ("route_delay", 0.55, "Aapli Bus route {num} delayed by 45 mins"),
    ("bus_suspended", 0.80, "Bus route {num} halted due to protest"),
    ("transit_disruption", 0.70, "Route {num} service suspended on Wardha Road"),
    ("route_delay", 0.45, "Heavy congestion causing delay on bus route {num}"),
]

SOURCE_TYPES = ["official", "sensor", "crowdsourced"]


def load_route_mappings() -> Dict[str, List[str]]:
    """Load route_id -> list of H3 res-9 cells."""
    if ROUTE_CELLS_PATH.exists():
        with open(ROUTE_CELLS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {k: v for k, v in data.items() if not k.startswith("_")}
    
    # Fallback if mapping table is missing: inspect geojson
    if TRANSIT_GEOJSON_PATH.exists():
        with open(TRANSIT_GEOJSON_PATH, "r", encoding="utf-8") as f:
            geojson = json.load(f)
        routes = {}
        for feat in geojson.get("features", []):
            ref = feat.get("properties", {}).get("ref")
            if ref:
                # Fallback to central Nagpur cell if not precomputed
                routes[ref] = ["89609612d47ffff"]
        if routes:
            return routes

    # Default fallback routes
    return {
        f"route_{i}": ["89609612517ffff", "8960961256bffff", "896096120afffff"]
        for i in range(1, 13)
    }


def generate_event(
    route_map: Dict[str, List[str]],
    scenario: Optional[str] = None
) -> Tuple[CanonicalEvent, str]:
    """Generate a single CanonicalEvent and its companion raw text alert."""
    route_id = random.choice(list(route_map.keys()))
    route_cells = route_map[route_id]
    h3_cell = random.choice(route_cells)
    
    # Extract route number for natural text templating
    route_num = route_id.replace("route_", "")
    
    event_type, base_severity, text_template = random.choice(EVENT_TYPES)
    # Add slight random jitter to severity
    severity = max(0.1, min(1.0, round(base_severity + random.uniform(-0.08, 0.08), 2)))
    
    source_type = random.choices(SOURCE_TYPES, weights=[0.4, 0.4, 0.2])[0]
    reliability = SOURCE_RELIABILITY[source_type]
    
    now = datetime.now(timezone.utc)
    
    event = CanonicalEvent(
        event_id=str(uuid.uuid4()),
        domain="transit",
        event_type=event_type,
        entity_id=route_id,
        h3_cell=h3_cell,
        severity=severity,
        source_type=source_type,
        source_reliability=reliability,
        event_timestamp=now,
        ingestion_timestamp=now,
        parse_confidence=1.0,
        scenario_tag=scenario
    )
    
    raw_text = text_template.format(num=route_num)
    return event, raw_text


def event_generator(
    route_map: Optional[Dict[str, List[str]]] = None,
    burst: int = 0,
    scenario: Optional[str] = None
):
    """
    Generator function outputting (CanonicalEvent, messy_text) tuples.
    Produces canonical events formatted according to contracts/event_schema.py.
    """
    if route_map is None:
        route_map = load_route_mappings()

    count = 0
    while True:
        event, raw_text = generate_event(route_map, scenario)
        count += 1
        yield event, raw_text
        if burst > 0 and count >= burst:
            break


def send_to_output(
    payload: dict,
    output_dest: str
) -> None:
    """Send payload to stdout, a file, or an HTTP POST endpoint."""
    line = json.dumps(payload, default=str)
    
    if output_dest == "stdout":
        print(line, flush=True)
    elif output_dest.startswith("http://") or output_dest.startswith("https://"):
        req = urllib.request.Request(
            output_dest,
            data=line.encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                pass
        except urllib.error.URLError as e:
            print(f"[WARN] Failed to POST to {output_dest}: {e}", file=sys.stderr)
    else:
        # File path
        with open(output_dest, "a", encoding="utf-8") as f:
            f.write(line + "\n")


def run_simulator(
    interval: float,
    burst: int,
    output: str,
    fmt: str,
    scenario: Optional[str]
) -> None:
    """Main execution loop for transport simulator."""
    route_map = load_route_mappings()
    total_cells = sum(len(cells) for cells in route_map.values())
    print(f"[INFO] Transport Simulator initialized with {len(route_map)} routes ({total_cells} total mapped H3 cells).", file=sys.stderr)
    print(f"[INFO] Output target: {output} | Interval: {interval}s | Burst: {burst or 'infinite'} | Format: {fmt}", file=sys.stderr)

    count = 0
    try:
        while True:
            event, raw_text = generate_event(route_map, scenario)
            count += 1
            
            if fmt == "canonical":
                payload = event.model_dump(mode="json")
            elif fmt == "text":
                payload = {"raw_text": raw_text, "timestamp": event.event_timestamp.isoformat()}
            else:  # both
                payload = {
                    "event": event.model_dump(mode="json"),
                    "raw_text": raw_text
                }
            
            send_to_output(payload, output)
            
            if burst > 0 and count >= burst:
                print(f"[INFO] Emitted burst of {count} events. Exiting.", file=sys.stderr)
                break
                
            time.sleep(interval)
    except KeyboardInterrupt:
        print(f"\n[INFO] Stopped after emitting {count} events.", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="UrbanPulse Transport Domain Simulator")
    parser.add_argument(
        "--interval",
        type=float,
        default=2.0,
        help="Interval between generated events in seconds (default: 2.0)"
    )
    parser.add_argument(
        "--burst",
        type=int,
        default=0,
        help="Number of events to generate before exiting (default: 0 = run continuously)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="stdout",
        help="Output destination: 'stdout', filepath, or HTTP POST URL"
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["canonical", "text", "both"],
        default="both",
        help="Output format: 'canonical' (CanonicalEvent), 'text' (raw message), or 'both'"
    )
    parser.add_argument(
        "--scenario",
        type=str,
        default=None,
        help="Optional scenario tag (e.g., 'transit_disruption')"
    )

    args = parser.parse_args()
    run_simulator(
        interval=args.interval,
        burst=args.burst,
        output=args.output,
        fmt=args.format,
        scenario=args.scenario
    )


if __name__ == "__main__":
    main()
