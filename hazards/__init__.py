"""Hazards & calibration (B11): rainfall probabilities, district tiers, calibration.

TECH_APPROACH §2.6:
- Predictive distribution from member ensemble → P(>64.5), P(>115.6), P(>204.5)
- Isotonic calibration on training fold
- District-level area-weighted 90th percentile → Green/Yellow/Orange/Red tiers
- Disagreement index: D = spread / climatological_spread
- LOMO: per-district RMSE increase when each model is removed
"""
from __future__ import annotations

import numpy as np
from sklearn.isotonic import IsotonicRegression


# IMD warning thresholds (mm/24h)
THRESHOLDS = {"heavy": 64.5, "very_heavy": 115.6, "extremely_heavy": 204.5}

# Tier thresholds on probability (starting values, tuned on validation fold)
TIER_THRESHOLDS = {
    "yellow":  ("p_gt_64p5", 0.4),
    "orange":  ("p_gt_115p6", 0.3),
    "red":     ("p_gt_204p5", 0.2),
}


def exceedance_prob_empirical(member_values: dict[str, np.ndarray],
                              weights: dict[str, float],
                              threshold: float) -> np.ndarray:
    """P(rain > threshold) from weighted member ensemble (empirical fallback).

    member_values: {model: (lat, lon) rain field}
    weights: {model: weight}
    """
    probs = np.zeros_like(next(iter(member_values.values())), dtype=np.float64)
    w_total = 0.0
    for model, field in member_values.items():
        w = weights.get(model, 0.0)
        probs += w * (field > threshold).astype(np.float64)
        w_total += w
    if w_total > 0:
        probs /= w_total
    return probs.astype(np.float32)


def all_exceedance_probs(member_values: dict[str, np.ndarray],
                         weights: dict[str, float]) -> dict[str, np.ndarray]:
    """Compute all three probability fields."""
    return {
        "p_gt_64p5": exceedance_prob_empirical(member_values, weights, THRESHOLDS["heavy"]),
        "p_gt_115p6": exceedance_prob_empirical(member_values, weights, THRESHOLDS["very_heavy"]),
        "p_gt_204p5": exceedance_prob_empirical(member_values, weights, THRESHOLDS["extremely_heavy"]),
    }


def calibrate_isotonic(train_probs: np.ndarray, train_obs: np.ndarray) -> IsotonicRegression:
    """Fit isotonic calibration on training fold."""
    ir = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip")
    ir.fit(train_probs.ravel(), train_obs.ravel())
    return ir


def apply_calibration(calibrator: IsotonicRegression, probs: np.ndarray) -> np.ndarray:
    """Apply isotonic calibration to probability field."""
    shape = probs.shape
    cal = calibrator.predict(probs.ravel())
    return cal.reshape(shape).astype(np.float32)


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


def disagreement_index(member_values: dict[str, np.ndarray],
                       clim_spread: np.ndarray) -> np.ndarray:
    """D = std(members) / climatological_spread. D > 1.5 → attention."""
    stack = np.stack(list(member_values.values()), axis=0)
    spread = np.nanstd(stack, axis=0)
    with np.errstate(divide="ignore", invalid="ignore"):
        D = np.where(clim_spread > 0, spread / clim_spread, 0.0)
    return D.astype(np.float32)


def lomo_rmse_increase(member_values: dict[str, np.ndarray],
                       weights: dict[str, float],
                       truth: np.ndarray,
                       land_mask: np.ndarray) -> dict[str, float]:
    """Leave-one-model-out: % RMSE increase when each model is removed."""
    from blending import weighted_mean

    # Full blend RMSE
    full_blend = weighted_mean(member_values, weights)
    full_rmse = float(np.sqrt(np.nanmean((full_blend[land_mask] - truth[land_mask]) ** 2)))

    result = {}
    for drop_model in member_values:
        subset_fields = {m: v for m, v in member_values.items() if m != drop_model}
        subset_weights = {m: w for m, w in weights.items() if m != drop_model}
        # Re-normalize weights
        w_total = sum(subset_weights.values())
        if w_total > 0:
            subset_weights = {m: w / w_total for m, w in subset_weights.items()}
        if subset_fields:
            lomo_blend = weighted_mean(subset_fields, subset_weights)
            lomo_rmse = float(np.sqrt(np.nanmean((lomo_blend[land_mask] - truth[land_mask]) ** 2)))
            pct = ((lomo_rmse - full_rmse) / max(full_rmse, 0.001)) * 100
        else:
            pct = 100.0
        result[drop_model] = round(pct, 1)
    return result
