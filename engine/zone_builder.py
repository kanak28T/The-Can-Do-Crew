"""
UrbanPulse — Zone Builder
==========================
Owner  : Kanak (A2) — Day 3 (A3.7)

Merges adjacent High-risk H3 cells into named polygon zones.
Uses DBSCAN on H3 cell centroids with H3 grid-distance as the metric.

A cell is "High" when:
  - risk >= HIGH_THRESHOLD  AND
  - not is_unknown

Output per zone:
  zone_id     : "Z01", "Z02", ...
  cells       : list of H3 res-9 cell IDs
  centroid    : (lat, lng) of the zone centre
  risk_max    : highest risk score in the zone
  risk_mean   : mean risk score
  confidence  : mean confidence of member cells
  label       : "high" | "watch"  (watch = 90th pct model says High)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


HIGH_THRESHOLD  = 0.65   # must match risk_model.py
WATCH_THRESHOLD = 0.50   # cells that might tip over


@dataclass
class Zone:
    zone_id:    str
    cells:      list[str]
    risk_max:   float
    risk_mean:  float
    confidence: float
    label:      str          # "high" | "watch"
    centroid:   tuple[float, float] = (0.0, 0.0)   # (lat, lng)

    def to_dict(self) -> dict:
        return {
            "zone_id":    self.zone_id,
            "cells":      self.cells,
            "cell_count": len(self.cells),
            "risk_max":   self.risk_max,
            "risk_mean":  self.risk_mean,
            "confidence": self.confidence,
            "label":      self.label,
            "centroid":   {"lat": self.centroid[0], "lng": self.centroid[1]},
        }


def _h3_distance(cell_a: str, cell_b: str) -> int:
    """Grid distance between two H3 res-9 cells (number of steps)."""
    try:
        import h3
        return h3.grid_distance(cell_a, cell_b)
    except Exception:
        # Fallback: Euclidean on centroids (less accurate but never crashes)
        try:
            import h3
            la, loa = h3.cell_to_latlng(cell_a)
            lb, lob = h3.cell_to_latlng(cell_b)
            deg_dist = math.sqrt((la - lb) ** 2 + (loa - lob) ** 2)
            return int(deg_dist / 0.001)   # rough: 1 step ≈ 0.001°
        except Exception:
            return 999


def _centroid(cells: list[str]) -> tuple[float, float]:
    """Mean lat/lng of a list of H3 cells."""
    try:
        import h3
        lats, lngs = zip(*[h3.cell_to_latlng(c) for c in cells])
        return round(sum(lats) / len(lats), 6), round(sum(lngs) / len(lngs), 6)
    except Exception:
        return (0.0, 0.0)


def build_zones(
    cell_scores: dict[str, dict],
    min_cluster_size: int = 1,
    eps_steps: int = 2,
) -> list[Zone]:
    """
    Cluster High-risk cells into zones using neighbour expansion (BFS).
    Falls back gracefully if sklearn is not available.

    Args:
        cell_scores     : {h3_cell: {"risk": float, "label": str,
                                     "confidence": float, "is_unknown": bool}}
        min_cluster_size: minimum cells to form a named zone (default 1)
        eps_steps       : H3 grid steps to consider "adjacent" (default 2)

    Returns:
        list[Zone] sorted by risk_max descending
    """
    # Filter to High + Watch cells only
    candidates = {
        cell: data
        for cell, data in cell_scores.items()
        if not data.get("is_unknown", False)
        and data.get("risk", 0.0) >= WATCH_THRESHOLD
    }

    if not candidates:
        return []

    # Try DBSCAN first; fall back to BFS neighbour expansion
    try:
        zones = _dbscan_cluster(candidates, eps_steps, min_cluster_size)
    except Exception:
        zones = _bfs_cluster(candidates, eps_steps, min_cluster_size)

    # Label and sort
    for z in zones:
        z.label = "high" if z.risk_max >= HIGH_THRESHOLD else "watch"

    zones.sort(key=lambda z: z.risk_max, reverse=True)

    # Assign readable zone IDs
    for i, z in enumerate(zones):
        z.zone_id = f"Z{i+1:02d}"

    return zones


def _bfs_cluster(
    candidates: dict[str, dict],
    eps: int,
    min_size: int,
) -> list[Zone]:
    """BFS neighbour expansion — no sklearn needed."""
    try:
        import h3
    except ImportError:
        # No h3: treat every cell as its own zone
        return [
            Zone(zone_id="", cells=[c], risk_max=d["risk"],
                 risk_mean=d["risk"], confidence=d.get("confidence", 0.0),
                 label="high", centroid=(0.0, 0.0))
            for c, d in candidates.items()
        ]

    visited: set[str] = set()
    zones: list[Zone] = []

    for seed in candidates:
        if seed in visited:
            continue
        # BFS from seed
        cluster: list[str] = []
        queue = [seed]
        while queue:
            cell = queue.pop(0)
            if cell in visited or cell not in candidates:
                continue
            visited.add(cell)
            cluster.append(cell)
            # All neighbours within eps steps
            neighbours = h3.grid_disk(cell, eps)
            for nb in neighbours:
                if nb not in visited and nb in candidates:
                    queue.append(nb)

        if len(cluster) < min_size:
            continue

        risks = [candidates[c]["risk"] for c in cluster]
        confs = [candidates[c].get("confidence", 0.0) for c in cluster]
        zones.append(Zone(
            zone_id="",
            cells=cluster,
            risk_max=round(max(risks), 4),
            risk_mean=round(sum(risks) / len(risks), 4),
            confidence=round(sum(confs) / len(confs), 4),
            label="high",
            centroid=_centroid(cluster),
        ))

    return zones


def _dbscan_cluster(
    candidates: dict[str, dict],
    eps: int,
    min_size: int,
) -> list[Zone]:
    """DBSCAN clustering using H3 grid distance as the metric."""
    import numpy as np
    from sklearn.cluster import DBSCAN
    import h3

    cells = list(candidates.keys())
    n = len(cells)

    # Precompute pairwise grid distances (capped at eps+1 for speed)
    dist_matrix = np.zeros((n, n), dtype=np.float32)
    for i in range(n):
        for j in range(i + 1, n):
            d = min(_h3_distance(cells[i], cells[j]), eps + 1)
            dist_matrix[i, j] = d
            dist_matrix[j, i] = d

    db = DBSCAN(eps=eps, min_samples=min_size, metric="precomputed")
    labels = db.fit_predict(dist_matrix)

    zones: list[Zone] = []
    for cluster_id in set(labels):
        if cluster_id == -1:
            continue   # noise
        cluster_cells = [cells[i] for i, lbl in enumerate(labels) if lbl == cluster_id]
        risks = [candidates[c]["risk"] for c in cluster_cells]
        confs = [candidates[c].get("confidence", 0.0) for c in cluster_cells]
        zones.append(Zone(
            zone_id="",
            cells=cluster_cells,
            risk_max=round(max(risks), 4),
            risk_mean=round(sum(risks) / len(risks), 4),
            confidence=round(sum(confs) / len(confs), 4),
            label="high",
            centroid=_centroid(cluster_cells),
        ))

    return zones
