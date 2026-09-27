"""Intensity CDF comparison (B6, TECH_APPROACH §2.3).

Computes empirical CDFs of forecast and observed precipitation intensity
over land cells, for a given threshold mask (e.g., only cells where obs > 1 mm).
Used alongside frequency bias to diagnose drizzle bias and intensity errors.
"""
from __future__ import annotations

import numpy as np


def empirical_cdf(values: np.ndarray, bins: np.ndarray | None = None
                  ) -> tuple[np.ndarray, np.ndarray]:
    """Compute empirical CDF from a 1D array of values.

    Returns (sorted_values, cumulative_probability).
    """
    v = values[np.isfinite(values)]
    if len(v) == 0:
        return np.array([]), np.array([])
    if bins is not None:
        counts, edges = np.histogram(v, bins=bins)
        cdf = np.cumsum(counts).astype(np.float64) / len(v)
        return (edges[:-1] + edges[1:]) / 2, cdf
    sv = np.sort(v)
    cdf = np.arange(1, len(sv) + 1, dtype=np.float64) / len(sv)
    return sv, cdf


def intensity_cdf_comparison(
    forecast: np.ndarray,
    truth: np.ndarray,
    land_mask: np.ndarray,
    min_threshold: float = 1.0,
    n_bins: int = 100,
) -> dict:
    """Compare intensity CDFs of forecast vs. truth over rainy land cells.

    Args:
        forecast: 2D (lat, lon) rain field in mm.
        truth: 2D (lat, lon) rain field in mm.
        land_mask: boolean 2D mask.
        min_threshold: only include cells where truth > this value.
        n_bins: number of histogram bins.

    Returns:
        dict with keys: bins_mm, cdf_forecast, cdf_truth, ks_statistic
    """
    fc_land = forecast[land_mask]
    obs_land = truth[land_mask]

    # Filter to rainy cells (based on truth)
    rainy = obs_land > min_threshold
    if rainy.sum() < 10:
        return {"bins_mm": [], "cdf_forecast": [], "cdf_truth": [],
                "ks_statistic": 0.0, "n_rainy_cells": 0}

    fc_rainy = fc_land[rainy]
    obs_rainy = obs_land[rainy]

    vmax = max(float(np.nanmax(fc_rainy)), float(np.nanmax(obs_rainy)))
    bins = np.linspace(0, vmax, n_bins + 1)

    mid_fc, cdf_fc = empirical_cdf(fc_rainy, bins)
    mid_obs, cdf_obs = empirical_cdf(obs_rainy, bins)

    # Kolmogorov–Smirnov statistic
    ks = float(np.max(np.abs(cdf_fc - cdf_obs))) if len(cdf_fc) == len(cdf_obs) else 0.0

    return {
        "bins_mm": mid_fc.round(2).tolist(),
        "cdf_forecast": cdf_fc.round(6).tolist(),
        "cdf_truth": cdf_obs.round(6).tolist(),
        "ks_statistic": round(ks, 4),
        "n_rainy_cells": int(rainy.sum()),
    }
