"""
UrbanPulse — Custom FedAvg Trainer
=====================================
Owner  : Kanak (A2) — Day 4 (Phase 6)

5 simulated municipal zone nodes. Each holds all domains for its own
H3 cells. They train the shared logistic coefficients (beta + gamma)
with FedAvg, with:
  - Gaussian noise on updates (differential privacy)
  - Update clipping (L2 norm ≤ 1.0)
  - Random node dropout (1-2 nodes per round)
  - Median aggregation (robust to Byzantine nodes)

Plan D8 (locked):
  No Flower. Nodes run in-process. ~40 lines of core FedAvg logic.
  Share only beta + gamma — never raw event data.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


# ── Config ─────────────────────────────────────────────────────────────────

@dataclass
class FedConfig:
    n_nodes:          int   = 5
    noise_sigma:      float = 0.01    # Gaussian noise std on updates
    clip_norm:        float = 1.0     # L2 clip threshold
    dropout_prob:     float = 0.2     # probability any node drops out per round
    min_nodes:        int   = 3       # minimum nodes needed to aggregate
    learning_rate:    float = 0.1
    l2_penalty:       float = 0.01


DEFAULT_CONFIG = FedConfig()


# ── Zone node ──────────────────────────────────────────────────────────────

@dataclass
class ZoneNode:
    """
    Simulated municipal zone node.
    Each node holds event data for a geographic slice of the city.
    Only shares model weight updates — never raw events.
    """
    node_id:    str
    cells:      list[str]           # H3 cells this node is responsible for
    is_online:  bool = True

    def local_gradient(
        self,
        beta: dict[str, float],
        gamma: dict[tuple, float],
        events: list[dict],
        baseline_map: dict[str, dict],
    ) -> tuple[dict[str, float], dict[tuple, float]]:
        """
        Compute local gradient on this node's events.
        Returns (delta_beta, delta_gamma) — never the raw events.
        """
        from engine.risk_model import sigmoid

        delta_beta  = {k: 0.0 for k in beta}
        delta_gamma = {k: 0.0 for k in gamma}

        node_events = [e for e in events if e.get("h3_cell") in set(self.cells)]
        if not node_events:
            return delta_beta, delta_gamma

        for ev in node_events:
            cell    = ev.get("h3_cell", "")
            domain  = ev.get("domain", "")
            stress  = float(ev.get("severity", 0.0))
            bl      = baseline_map.get(cell, {})

            # Build input vector
            x = {
                "hospital_isolation": bl.get("hospital_isolation", 0.5),
                "transit_loss":       bl.get("transit_deficit", 0.3),
                "power_stress":       stress if domain == "power"   else 0.0,
                "water_loss":         stress if domain == "water"   else 0.0,
                "comms_loss":         stress if domain == "comms"   else 0.0,
                "road_stress":        stress if domain == "roads"   else 0.0,
            }

            # Forward pass
            z = -1.2  # bias
            for k, v in x.items():
                z += beta.get(k, 0.0) * v
            for (j, k_), g in gamma.items():
                z += g * x.get(j, 0.0) * x.get(k_, 0.0)

            p     = sigmoid(z)
            # Label: high stress events should predict high risk
            label = 1.0 if stress > 0.6 else 0.0
            err   = p - label   # cross-entropy gradient

            # Accumulate gradients
            for k in delta_beta:
                grad = err * x.get(k, 0.0) + DEFAULT_CONFIG.l2_penalty * beta.get(k, 0.0)
                delta_beta[k] += grad

            for (j, k_) in delta_gamma:
                grad = err * x.get(j, 0.0) * x.get(k_, 0.0)
                delta_gamma[(j, k_)] += grad

        # Average over events
        n = len(node_events)
        delta_beta  = {k: v / n for k, v in delta_beta.items()}
        delta_gamma = {k: v / n for k, v in delta_gamma.items()}

        return delta_beta, delta_gamma


# ── FedAvg trainer ─────────────────────────────────────────────────────────

@dataclass
class FedAvgTrainer:
    config: FedConfig = field(default_factory=FedConfig)
    round_number: int = 0
    training_log: list[dict] = field(default_factory=list)

    def _clip(self, delta: dict) -> dict:
        """Clip update vector to L2 norm ≤ clip_norm."""
        norm = math.sqrt(sum(v ** 2 for v in delta.values())) or 1e-9
        if norm > self.config.clip_norm:
            scale = self.config.clip_norm / norm
            return {k: v * scale for k, v in delta.items()}
        return delta

    def _add_noise(self, delta: dict) -> dict:
        """Add calibrated Gaussian noise for differential privacy."""
        return {
            k: v + random.gauss(0, self.config.noise_sigma)
            for k, v in delta.items()
        }

    def _median_aggregate(self, updates: list[dict]) -> dict:
        """Robust median aggregation — resistant to Byzantine nodes."""
        if not updates:
            return {}
        keys = updates[0].keys()
        return {
            k: sorted(u[k] for u in updates)[len(updates) // 2]
            for k in keys
        }

    def train_round(
        self,
        nodes: list[ZoneNode],
        events: list[dict],
        baseline_map: dict[str, dict],
    ) -> dict:
        """
        Run one FedAvg round.

        1. Random dropout of nodes
        2. Each surviving node computes local gradient
        3. Clip + noise each update
        4. Median aggregate
        5. Apply to global model with learning rate
        6. Enforce non-negativity (plan D6)

        Returns a summary dict with round stats.
        """
        from engine.risk_model import MODEL

        self.round_number += 1
        online_nodes = [n for n in nodes if n.is_online]

        # Random dropout
        surviving = [
            n for n in online_nodes
            if random.random() > self.config.dropout_prob
        ]

        if len(surviving) < self.config.min_nodes:
            # Not enough nodes — skip round
            result = {
                "round":          self.round_number,
                "status":         "skipped",
                "reason":         f"Only {len(surviving)} nodes online (min {self.config.min_nodes})",
                "nodes_used":     len(surviving),
                "timestamp":      datetime.now(timezone.utc).isoformat(),
            }
            self.training_log.append(result)
            return result

        # Collect local gradients
        beta_updates  = []
        gamma_updates = []

        for node in surviving:
            db, dg = node.local_gradient(
                MODEL.beta, MODEL.gamma, events, baseline_map
            )
            # Clip
            db_flat = self._clip(db)
            dg_flat = self._clip({str(k): v for k, v in dg.items()})
            # Noise
            db_flat = self._add_noise(db_flat)
            dg_flat = self._add_noise(dg_flat)

            beta_updates.append(db_flat)
            gamma_updates.append({eval(k) if isinstance(k, str) else k: v
                                   for k, v in dg_flat.items()})

        # Median aggregate
        avg_beta  = self._median_aggregate(beta_updates)
        avg_gamma = self._median_aggregate([
            {str(k): v for k, v in gu.items()} for gu in gamma_updates
        ])

        # Apply update — enforce non-negativity (plan D6)
        lr = self.config.learning_rate
        for k in MODEL.beta:
            MODEL.beta[k] = max(0.0, MODEL.beta[k] - lr * avg_beta.get(k, 0.0))

        for k in MODEL.gamma:
            str_k = str(k)
            MODEL.gamma[k] = max(0.0, MODEL.gamma[k] - lr * avg_gamma.get(str_k, 0.0))

        result = {
            "round":          self.round_number,
            "status":         "completed",
            "nodes_total":    len(nodes),
            "nodes_used":     len(surviving),
            "nodes_dropped":  len(online_nodes) - len(surviving),
            "beta_snapshot":  {k: round(v, 4) for k, v in MODEL.beta.items()},
            "timestamp":      datetime.now(timezone.utc).isoformat(),
        }
        self.training_log.append(result)
        return result


def create_nodes(all_cells: list[str], n_nodes: int = 5) -> list[ZoneNode]:
    """
    Divide the canonical H3 grid into n geographic zone nodes.
    Each node gets a contiguous slice of cells.
    """
    chunk = max(1, len(all_cells) // n_nodes)
    nodes = []
    for i in range(n_nodes):
        start = i * chunk
        end   = start + chunk if i < n_nodes - 1 else len(all_cells)
        nodes.append(ZoneNode(
            node_id=f"node_{i+1}",
            cells=all_cells[start:end],
            is_online=True,
        ))
    return nodes


# ── Global trainer instance ────────────────────────────────────────────────
TRAINER = FedAvgTrainer(config=DEFAULT_CONFIG)
