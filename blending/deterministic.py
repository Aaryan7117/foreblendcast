"""Deterministic blend: weighted mean of model fields."""
from __future__ import annotations

import numpy as np

def weighted_mean(fields: dict[str, np.ndarray], weights: dict[str, float | np.ndarray]) -> np.ndarray:
    """Deterministic blend: weighted mean of model fields.

    Args:
        fields: {model_name: (lat, lon) array}
        weights: {model_name: weight} where weight is float or (lat, lon) array
    """
    result = np.zeros_like(next(iter(fields.values())), dtype=np.float64)
    w_total = np.zeros_like(result)
    
    for model, field in fields.items():
        if model not in weights:
            continue
        w = weights[model]
        valid = np.isfinite(field)
        
        if isinstance(w, float):
            result[valid] += w * field[valid]
            w_total[valid] += w
        else:
            w_valid = valid & np.isfinite(w)
            result[w_valid] += w[w_valid] * field[w_valid]
            w_total[w_valid] += w[w_valid]
            
    mask = w_total > 0
    result[mask] /= w_total[mask]
    result[~mask] = np.nan
    return result.astype(np.float32)
