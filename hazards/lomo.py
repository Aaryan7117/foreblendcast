"""Leave-one-model-out (LOMO) RMSE increase (B11)."""
from __future__ import annotations

import numpy as np


def lomo_rmse_increase(member_values: dict[str, np.ndarray],
                       weights: dict[str, float | np.ndarray],
                       truth: np.ndarray,
                       land_mask: np.ndarray) -> dict[str, float]:
    """Leave-one-model-out: % RMSE increase when each model is removed."""
    from blending.deterministic import weighted_mean

    # Full blend RMSE
    full_blend = weighted_mean(member_values, weights)
    full_rmse = float(np.sqrt(np.nanmean((full_blend[land_mask] - truth[land_mask]) ** 2)))

    result = {}
    for drop_model in member_values:
        subset_fields = {m: v for m, v in member_values.items() if m != drop_model}
        subset_weights = {m: w for m, w in weights.items() if m != drop_model}
        
        # Re-normalize weights
        if isinstance(next(iter(subset_weights.values())), float):
            w_total = sum(subset_weights.values())
            if w_total > 0:
                subset_weights = {m: w / w_total for m, w in subset_weights.items()}
        else:
            w_total = sum(subset_weights.values())
            subset_weights = {m: w / w_total for m, w in subset_weights.items()}
            
        if subset_fields:
            lomo_blend = weighted_mean(subset_fields, subset_weights)
            lomo_rmse = float(np.sqrt(np.nanmean((lomo_blend[land_mask] - truth[land_mask]) ** 2)))
            pct = ((lomo_rmse - full_rmse) / max(full_rmse, 0.001)) * 100
        else:
            pct = 100.0
            
        result[drop_model] = round(pct, 1)
        
    return result
