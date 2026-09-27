"""Shrinkage along the spatial hierarchy (B9, TECH_APPROACH §2.2).

Hierarchy: cell -> district -> subdivision -> homogeneous region -> national.
λ = n_eff / (n_eff + k)
If n_eff < 15, inherit parent and record the reason.
"""
from __future__ import annotations

import logging
import numpy as np

from weighting.base import WeightStrategy
from weighting.baselines import EqualWeights

log = logging.getLogger(__name__)

class ContextShrinkPM(WeightStrategy):
    name = "context_shrink_pm"

    def __init__(self, tau: float = 1.0, k: float = 20.0, n_eff_min: int = 15):
        self.tau = tau
        self.k = k
        self.n_eff_min = n_eff_min

    def compute_weights(self, models: list[str], **context) -> dict[str, float]:
        """Compute shrunk weights for a specific node in the hierarchy.
        
        Requires context:
          - scores: dict[model, float]
          - n_eff: int
          - parent_weights: dict[model, float] (if applicable)
          - node_id: str (for logging)
        """
        scores = context.get("scores", {})
        n_eff = context.get("n_eff", 0)
        parent_weights = context.get("parent_weights", None)
        node_id = context.get("node_id", "unknown")

        if not scores:
            if parent_weights:
                return parent_weights.copy()
            return EqualWeights().compute_weights(models)

        # Local softmax
        vals = np.array([scores.get(m, 0.0) for m in models])
        vals = np.nan_to_num(vals, nan=1e6)
        vals = vals - vals.min()
        exp_vals = np.exp(-vals / self.tau)
        total = exp_vals.sum()
        
        if total == 0 or np.isnan(total):
            local = {m: 1.0 / len(models) for m in models}
        else:
            exp_vals /= total
            local = {m: float(w) for m, w in zip(models, exp_vals)}

        # Shrinkage
        if n_eff < self.n_eff_min and parent_weights:
            # Fall back completely to parent
            log.info("shrinkage.inherit", extra={
                "node": node_id, "n_eff": n_eff, 
                "reason": f"n_eff < {self.n_eff_min}"
            })
            return parent_weights.copy()

        lam = n_eff / (n_eff + self.k)
        if parent_weights:
            return {
                m: lam * local[m] + (1 - lam) * parent_weights.get(m, local[m])
                for m in models
            }
        
        return local

