"""Rainfall probabilities (B11).

exceedance_prob_empirical is the weighted share of members above a threshold. The
pipeline uses its neighbourhood version followed by isotonic calibration
(experiments.evaluate). Predictive quantiles come from calibration.quantiles or
calibration.lgbm, whichever has the lower cross-validated pinball loss in training.
"""
from __future__ import annotations

import numpy as np


# IMD warning thresholds (mm/24h)
THRESHOLDS = {"heavy": 64.5, "very_heavy": 115.6, "extremely_heavy": 204.5}


def exceedance_prob_empirical(member_values: dict[str, np.ndarray],
                              weights: dict[str, float | np.ndarray],
                              threshold: float) -> np.ndarray:
    """P(rain > threshold) from weighted member ensemble (empirical fallback)."""
    probs = np.zeros_like(next(iter(member_values.values())), dtype=np.float64)
    w_total = np.zeros_like(probs)
    
    for model, field in member_values.items():
        if model not in weights:
            continue
        w = weights[model]
        mask = (field > threshold).astype(np.float64)
        valid = np.isfinite(field)
        
        if isinstance(w, float):
            probs[valid] += w * mask[valid]
            w_total[valid] += w
        else:
            w_valid = valid & np.isfinite(w)
            probs[w_valid] += w[w_valid] * mask[w_valid]
            w_total[w_valid] += w[w_valid]
            
    valid = w_total > 0
    probs[valid] /= w_total[valid]
    probs[~valid] = np.nan
    return probs.astype(np.float32)


def all_exceedance_probs_empirical(member_values: dict[str, np.ndarray],
                                   weights: dict[str, float | np.ndarray]) -> dict[str, np.ndarray]:
    """Compute all three probability fields using empirical fallback."""
    return {
        "p_gt_64p5": exceedance_prob_empirical(member_values, weights, THRESHOLDS["heavy"]),
        "p_gt_115p6": exceedance_prob_empirical(member_values, weights, THRESHOLDS["very_heavy"]),
        "p_gt_204p5": exceedance_prob_empirical(member_values, weights, THRESHOLDS["extremely_heavy"]),
    }
