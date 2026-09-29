"""Deterministic verification metrics (B6): RMSE, MAE, bias.

All metrics work per (model, variable, lead, cell) and produce
land-area-weighted aggregates.
"""
from __future__ import annotations

import numpy as np
from canonical.grid import area_weights


def rmse(forecast: np.ndarray, truth: np.ndarray,
         weights: np.ndarray | None = None) -> float:
    """Root-mean-square error, optionally area-weighted."""
    diff2 = (forecast - truth) ** 2
    mask = np.isfinite(diff2)
    if not mask.any():
        return float("nan")
    if weights is not None:
        w = weights[mask] if weights.shape == diff2.shape else weights.ravel()[:mask.sum()]
        if w.sum() == 0:
            return float("nan")
        return float(np.sqrt(np.average(diff2[mask], weights=w)))
    return float(np.sqrt(np.nanmean(diff2)))


def mae(forecast: np.ndarray, truth: np.ndarray,
        weights: np.ndarray | None = None) -> float:
    """Mean absolute error."""
    absdiff = np.abs(forecast - truth)
    mask = np.isfinite(absdiff)
    if not mask.any():
        return float("nan")
    if weights is not None:
        w = weights[mask]
        if w.sum() == 0:
            return float("nan")
        return float(np.average(absdiff[mask], weights=w))
    return float(np.nanmean(absdiff))


def bias(forecast: np.ndarray, truth: np.ndarray,
         weights: np.ndarray | None = None) -> float:
    """Mean bias (forecast - truth)."""
    diff = forecast - truth
    mask = np.isfinite(diff)
    if not mask.any():
        return float("nan")
    if weights is not None:
        w = weights[mask]
        if w.sum() == 0:
            return float("nan")
        return float(np.average(diff[mask], weights=w))
    return float(np.nanmean(diff))


def cell_rmse(forecast_stack: np.ndarray, truth_stack: np.ndarray) -> np.ndarray:
    """Per-cell RMSE over a time axis. Input shape: (n_times, lat, lon)."""
    return np.sqrt(np.nanmean((forecast_stack - truth_stack) ** 2, axis=0))


def cell_mae(forecast_stack: np.ndarray, truth_stack: np.ndarray) -> np.ndarray:
    """Per-cell MAE over a time axis."""
    return np.nanmean(np.abs(forecast_stack - truth_stack), axis=0)


def cell_bias(forecast_stack: np.ndarray, truth_stack: np.ndarray) -> np.ndarray:
    """Per-cell bias over a time axis."""
    return np.nanmean(forecast_stack - truth_stack, axis=0)


def weighted_aggregate(cell_metric: np.ndarray, land_mask: np.ndarray) -> float:
    """Land-area-weighted aggregate of a per-cell metric."""
    w = area_weights()
    masked = cell_metric[land_mask]
    w_masked = w[land_mask]
    valid = np.isfinite(masked)
    if not valid.any():
        return float("nan")
    return float(np.average(masked[valid], weights=w_masked[valid]))
