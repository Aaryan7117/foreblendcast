"""Context-aware softmax weighting (B9).

score[m, v, region, lead, season] -> softmax(-score/τ)
"""
from __future__ import annotations

import numpy as np

from weighting.base import WeightStrategy
from weighting.baselines import EqualWeights

class ContextAware(WeightStrategy):
    name = "context"

    def __init__(self, tau: float = 1.0):
        self.tau = tau

    def compute_weights(self, models: list[str], **context) -> dict[str, float]:
        scores = context.get("scores", {})
        if not scores:
            return EqualWeights().compute_weights(models)
        
        vals = np.array([scores.get(m, 0.0) for m in models])
        # Handle nan in scores by setting them to high values (low weight)
        vals = np.nan_to_num(vals, nan=1e6)
        
        # Stability: subtract min before exp
        vals = vals - vals.min()
        exp_vals = np.exp(-vals / self.tau)
        
        total = exp_vals.sum()
        if total == 0 or np.isnan(total):
             return EqualWeights().compute_weights(models)
             
        exp_vals /= total
        return {m: float(w) for m, w in zip(models, exp_vals)}
