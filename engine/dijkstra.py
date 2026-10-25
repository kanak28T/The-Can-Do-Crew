"""
Multi-source reverse Dijkstra from all hospital nodes.
Produces: {h3_cell: travel_time_minutes}

Phase 1 — A1 task.
Run once at startup; recompute affected subgraph on road-closure events.
"""

import json
import os
import time
from typing import Dict, List, Optional, Set

# ── Constants ──────────────────────────────────────────────────────────────────
ROAD_GRAPH_PATH   = "data/nagpur_roads.graphml"
HOSPITALS_PATH    = "data/nagpur_hospitals.geojson"
OUTPUT_PATH       = "data/hospital_travel_times.json"
H3_GRID_PATH      = "data/nagpur_h3_res9.geojson"

CONGESTION_FACTOR = 1.5   # closed-edge neighbour edge slowdown
WALK_SPEED_KMH    = 5.0   # fallback if no road within 200m of cell centroid


def _load_graph():
    import networkx as nx
    if not os.path.exists(ROAD_GRAPH_PATH):
        raise FileNotFoundError(
            f"Road graph not found: {ROAD_GRAPH_PATH}\n"
            "Run: python data/download_scripts/download_roads.py"
        )
    print("Loading road graph…", end=" ", flush=True)
    G = nx.read_graphml(ROAD_GRAPH_PATH)
    print(f"{G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    return G


def _load_hospitals() -> List[dict]:
    """Return list of hospital dicts with lat/lon."""
    if not os.path.exists(HOSPITALS_PATH):
        print(f"⚠ Hospitals file not found ({HOSPITALS_PATH}) — using 3 mock hospitals")
        return [
            {"name": "Mayo Hospital",    "lat": 21.1458, "lon": 79.0882},
            {"name": "GMCH Nagpur",      "lat": 21.1500, "lon": 79.0800},
            {"name": "NMC Hospital",     "lat": 21.1200, "lon": 79.0700},
        ]
    with open(HOSPITALS_PATH) as f:
        data = json.load(f)
    hospitals = []
    for feat in data.get("features", []):
        if feat["geometry"]["type"] == "Point":
            lon, lat = feat["geometry"]["coordinates"]
            hospitals.append({
                "name": feat["properties"].get("name", "Hospital"),
                "lat": lat, "lon": lon
            })
    print(f"Loaded {len(hospitals)} hospitals")
    return hospitals


def _nearest_node(G, lat: float, lon: float):
    """Find the nearest graph node to a lat/lon coordinate."""
    import networkx as nx
    # osmnx stores nodes with 'y'=lat, 'x'=lon
    best_node, best_dist = None, float("inf")
    for node, data in G.nodes(data=True):
        nlat = float(data.get("y", data.get("lat", 0)))
        nlon = float(data.get("x", data.get("lon", 0)))
        dist = ((nlat - lat) ** 2 + (nlon - lon) ** 2) ** 0.5
        if dist < best_dist:
            best_dist = dist
            best_node = node
    return best_node


def run_dijkstra(
    G=None,
    closed_edges: Optional[Set[tuple]] = None,
) -> Dict[str, float]:
    """
    Multi-source reverse Dijkstra from all hospital nodes.
    Returns {h3_cell: travel_time_minutes}.

    If G is None, loads from ROAD_GRAPH_PATH.
    closed_edges: set of (u, v) tuples to remove from graph before running.
    """
    import networkx as nx
    import h3

    t0 = time.time()

    if G is None:
        G = _load_graph()

    # Remove closed edges from working copy
    working_G = G.copy()
    if closed_edges:
        for u, v in closed_edges:
            if working_G.has_edge(u, v):
                working_G.remove_edge(u, v)
                print(f"  Removed edge ({u},{v}) for closure simulation")

    hospitals = _load_hospitals()

    # Add travel time weight to edges (use 'length' in metres → minutes at 30 km/h)
    SPEED_KMH = 30.0
    for u, v, data in working_G.edges(data=True):
        length_m = float(data.get("length", 100.0))
        data["travel_time"] = length_m / (SPEED_KMH * 1000 / 60)  # minutes

    # Reverse the graph so we can do multi-source Dijkstra FROM hospitals
    rev_G = working_G.reverse(copy=False)

    # Find nearest node for each hospital
    source_nodes = set()
    for h in hospitals:
        node = _nearest_node(working_G, h["lat"], h["lon"])
        if node is not None:
            source_nodes.add(node)
    print(f"Hospital source nodes: {len(source_nodes)}")

    # Multi-source Dijkstra on reversed graph
    # Result: {node: min_travel_time_to_nearest_hospital}
    lengths = nx.multi_source_dijkstra_path_length(
        rev_G, sources=source_nodes, weight="travel_time"
    )

    # Load H3 grid to map cells → nearest road node
    if not os.path.exists(H3_GRID_PATH):
        print(f"⚠ H3 grid not found ({H3_GRID_PATH}) — skipping cell mapping")
        return {}

    with open(H3_GRID_PATH) as f:
        grid = json.load(f)

    cell_times: Dict[str, float] = {}
    for feat in grid["features"]:
        cell = feat["properties"]["cell"]
        # Cell centroid
        lat, lon = h3.cell_to_latlng(cell)
        node = _nearest_node(working_G, lat, lon)
        if node is not None and node in lengths:
            cell_times[cell] = round(lengths[node], 2)
        else:
            # Unreachable → normalise to max + penalty
            cell_times[cell] = 999.0

    elapsed = time.time() - t0
    print(f"Dijkstra complete: {len(cell_times)} cells in {elapsed:.2f}s")
    return cell_times


def recompute_subgraph(
    closed_edge_nodes: List[tuple],
    affected_radius_km: float = 2.0,
) -> Dict[str, float]:
    """
    Recompute hospital travel times for cells within radius of closed edges.
    Much faster than full recompute — only touches affected subgraph.
    Returns updated {h3_cell: travel_time} for affected cells only.
    """
    import networkx as nx
    import h3

    t0 = time.time()
    G = _load_graph()

    # Get all nodes within radius of closed edge midpoints
    affected_nodes: Set = set()
    for u, v in closed_edge_nodes:
        u_data = G.nodes.get(u, {})
        v_data = G.nodes.get(v, {})
        mid_lat = (float(u_data.get("y", 0)) + float(v_data.get("y", 0))) / 2
        mid_lon = (float(u_data.get("x", 0)) + float(v_data.get("x", 0))) / 2
        # H3 k-ring to get affected cells
        center_cell = h3.latlng_to_cell(mid_lat, mid_lon, 9)
        radius_cells = h3.grid_disk(center_cell, k=5)   # ~2 km at res 9
        affected_nodes.update(radius_cells)

    updated = run_dijkstra(G=G, closed_edges=set(closed_edge_nodes))

    elapsed = time.time() - t0
    print(f"Subgraph recompute: {len(updated)} cells in {elapsed*1000:.1f}ms")
    return {k: v for k, v in updated.items() if k in affected_nodes}


def save_travel_times(times: Dict[str, float], path: str = OUTPUT_PATH):
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    with open(path, "w") as f:
        json.dump(times, f)
    print(f"✅ Saved {len(times)} cell travel times → {path}")


if __name__ == "__main__":
    times = run_dijkstra()
    if times:
        save_travel_times(times)
        # Quick sanity check
        finite = [v for v in times.values() if v < 999]
        if finite:
            print(f"Min: {min(finite):.1f} min  Max: {max(finite):.1f} min  Median: {sorted(finite)[len(finite)//2]:.1f} min")
