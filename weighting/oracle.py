"""Oracle weighting: hindsight best model per cell (B9)."""
from __future__ import annotations

import numpy as np

from weighting.base import WeightStrategy
from weighting.baselines import EqualWeights

class Oracle(WeightStrategy):
    """Per-cell hindsight best (ceiling only)."""
    name = "oracle"

    def compute_weights(self, models: list[str], **context) -> dict[str, float | np.ndarray]:
        # Context expects 'abs_errors' mapping model -> 2D array of absolute errors
        abs_errors = context.get("abs_errors", {})
        if not abs_errors:
            return EqualWeights().compute_weights(models)
            
        # Shape is (lat, lon)
        shape = next(iter(abs_errors.values())).shape
        best_idx = np.zeros(shape, dtype=int)
        min_err = np.full(shape, np.inf)
        
        for i, m in enumerate(models):
            err = abs_errors.get(m, np.full(shape, np.inf))
            mask = err < min_err
            min_err[mask] = err[mask]
            best_idx[mask] = i
            
        weights = {}
        for i, m in enumerate(models):
            weights[m] = (best_idx == i).astype(np.float32)
            
        return weights
