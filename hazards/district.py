"""District level tiers (B11).

District-level area-weighted 90th percentile -> Green/Yellow/Orange/Red tiers.
"""
from __future__ import annotations

import numpy as np


# Tier thresholds on probability (starting values, tuned on validation fold)
TIER_THRESHOLDS = {
    "yellow":  ("p_gt_64p5", 0.4),
    "orange":  ("p_gt_115p6", 0.3),
    "red":     ("p_gt_204p5", 0.2),
}


def district_probability(cell_probs: np.ndarray, district_mask: np.ndarray,
                         area_weights: np.ndarray,
                         aggregation: str = "p90") -> float:
    """Aggregate cell probabilities to a district level.

    aggregation: 'p90' (area-weighted 90th percentile), 'mean', 'max'
    """
    cells = cell_probs[district_mask]
    w = area_weights[district_mask]
    valid = np.isfinite(cells)
    if not valid.any():
        return 0.0
    cells, w = cells[valid], w[valid]

    if aggregation == "max":
        return float(np.max(cells))
    elif aggregation == "mean":
        return float(np.average(cells, weights=w))
    else:  # p90
        # Weighted 90th percentile
        sorted_idx = np.argsort(cells)
        cumw = np.cumsum(w[sorted_idx])
        cumw /= cumw[-1]
        idx90 = np.searchsorted(cumw, 0.9)
        return float(cells[sorted_idx[min(idx90, len(cells) - 1)]])


def assign_tier(p_64: float, p_115: float, p_204: float) -> str:
    """Assign IMD warning tier from exceedance probabilities."""
    if p_204 >= TIER_THRESHOLDS["red"][1]:
        return "red"
    if p_115 >= TIER_THRESHOLDS["orange"][1]:
        return "orange"
    if p_64 >= TIER_THRESHOLDS["yellow"][1]:
        return "yellow"
    return "green"
