"""Frequency bias and intensity CDF (B6)."""
from __future__ import annotations

import numpy as np

RAIN_THRESHOLDS_MM = (15.6, 64.5, 115.6, 204.5)


def frequency_bias(forecast: np.ndarray, truth: np.ndarray,
                   threshold: float) -> float:
    """Frequency bias = (# forecast >= thr) / (# observed >= thr)."""
    n_fc = np.sum(forecast >= threshold)
    n_ob = np.sum(truth >= threshold)
    if n_ob == 0:
        return float("inf") if n_fc > 0 else 1.0
    return float(n_fc / n_ob)


def all_frequency_biases(forecast: np.ndarray, truth: np.ndarray) -> dict[str, float]:
    """Frequency bias at all standard thresholds."""
    return {f"fb_{t}mm": frequency_bias(forecast, truth, t) for t in RAIN_THRESHOLDS_MM}


def intensity_cdf(values: np.ndarray, percentiles: np.ndarray | None = None) -> dict:
    """Empirical CDF of rain intensity for non-zero cells."""
    if percentiles is None:
        percentiles = np.arange(0, 101, 5)
    vals = values[values > 0.1]  # > 0.1 mm = trace
    if len(vals) == 0:
        return {"percentiles": percentiles.tolist(), "values": [0.0] * len(percentiles)}
    q = np.nanpercentile(vals, percentiles)
    return {"percentiles": percentiles.tolist(), "values": q.tolist()}
