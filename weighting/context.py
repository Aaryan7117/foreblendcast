"""Context-aware softmax weighting (B9).

score[m, v, region, lead, season] -> softmax(-score/τ)
"""
from __future__ import annotations

import numpy as np

from weighting.base import WeightStrategy
from weighting.baselines import EqualWeights
from weighting.shrinkage import softmax_weights

class ContextAware(WeightStrategy):
    name = "context"

    def __init__(self, tau: float = 1.0):
        self.tau = tau

    def compute_weights(self, models: list[str], **context) -> dict[str, float]:
        scores = context.get("scores", {})
        if not scores:
            return EqualWeights().compute_weights(models)
        
        # Scores are historical errors (lower is better); a model with no history gets 0.
        vals = np.array([scores.get(m, np.nan) for m in models], dtype=np.float64)
        w = softmax_weights(vals, self.tau)
        return {m: float(x) for m, x in zip(models, w)}
