"""
Download Nagpur OSM road graph and save as GraphML.
Run: python data/download_scripts/download_roads.py
Takes 5-15 min depending on internet. Run in background while coding.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

def download():
    import osmnx as ox
    import networkx as nx

    out_path = "data/nagpur_roads.graphml"
    os.makedirs("data", exist_ok=True)

    print("Downloading Nagpur road network from OSM...")
    print("(This takes 5–15 min depending on internet speed)")

    G = ox.graph_from_place("Nagpur, Maharashtra, India", network_type="drive")

    print(f"Graph loaded: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    # Save
    nx.write_graphml(G, out_path)
    print(f"✅ Saved → {out_path}")

    # Quick sanity check: find a route from city center to airport
    try:
        center = ox.distance.nearest_nodes(G, 79.0882, 21.1458)   # Nagpur center
        airport = ox.distance.nearest_nodes(G, 79.0474, 21.0922)  # Nagpur airport
        import networkx as nx
        path_length = nx.shortest_path_length(G, center, airport, weight="length")
        print(f"Sanity check: center→airport = {path_length/1000:.1f} km (should be ~10–15 km)")
    except Exception as e:
        print(f"Sanity check skipped: {e}")

if __name__ == "__main__":
    download()
