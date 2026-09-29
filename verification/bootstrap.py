"""Block bootstrap for CIs on metric differences (B6, TECH_APPROACH §2.3).

Moving-block bootstrap over forecast dates, 1000 reps, 95% CI on differences vs. a
reference system. The inputs are one value per forecast date in time order; blocks keep
the serial correlation of consecutive dates. Never pass spatial cells as samples.
"""
from __future__ import annotations

import numpy as np


def block_indices(n: int, block_size: int, n_reps: int, seed: int = 42) -> np.ndarray:
    """(n_reps, n) resampled time indices built from contiguous blocks."""
    block_size = max(1, min(block_size, n))
    n_blocks = int(np.ceil(n / block_size))
    rng = np.random.default_rng(seed)
    starts = rng.integers(0, n - block_size + 1, size=(n_reps, n_blocks))
    idx = starts[:, :, None] + np.arange(block_size)[None, None, :]
    return idx.reshape(n_reps, -1)[:, :n]


def block_bootstrap_rmse_diff(mse_a: np.ndarray, mse_b: np.ndarray,
                              block_size: int = 4, n_reps: int = 1000,
                              ci: float = 0.95) -> tuple[float, float]:
    """CI on RMSE(A) - RMSE(B) from per-date mean squared errors of both systems.

    block_size counts forecast dates (4 dates = 8 days at one init every second day).
    """
    ok = np.isfinite(mse_a) & np.isfinite(mse_b)
    a, b = np.asarray(mse_a)[ok], np.asarray(mse_b)[ok]
    if a.size < 2 * block_size:
        return float("nan"), float("nan")
    idx = block_indices(a.size, block_size, n_reps)
    diffs = np.sqrt(a[idx].mean(axis=1)) - np.sqrt(b[idx].mean(axis=1))
    alpha = (1 - ci) / 2
    return (float(np.percentile(diffs, 100 * alpha)),
            float(np.percentile(diffs, 100 * (1 - alpha))))


def block_bootstrap_diff(errors_a: np.ndarray, errors_b: np.ndarray,
                         block_size: int = 7, n_reps: int = 1000,
                         ci: float = 0.95) -> tuple[float, float]:
    """Bootstrap CI on the difference in mean |error| between A and B.

    Args:
        errors_a: 1D array, one mean absolute error per forecast date, system A (e.g. blend)
        errors_b: 1D array, one mean absolute error per forecast date, system B
        block_size: block length in forecast dates
        n_reps: number of bootstrap replicates
        ci: confidence level

    Returns:
        (lower, upper) bounds of the CI on mean(|A|) - mean(|B|)
    """
    n = len(errors_a)
    diffs = np.empty(n_reps)
    for i, idx in enumerate(block_indices(n, block_size, n_reps)):
        diffs[i] = np.nanmean(errors_a[idx]) - np.nanmean(errors_b[idx])

    alpha = (1 - ci) / 2
    lo = float(np.nanpercentile(diffs, 100 * alpha))
    hi = float(np.nanpercentile(diffs, 100 * (1 - alpha)))
    return lo, hi


def block_bootstrap_metric(values: np.ndarray, metric_fn,
                           block_size: int = 7, n_reps: int = 1000,
                           ci: float = 0.95) -> tuple[float, float, float]:
    """Bootstrap CI on a single metric.

    Returns:
        (estimate, ci_lower, ci_upper)
    """
    n = len(values)
    estimates = np.empty(n_reps)
    for i, idx in enumerate(block_indices(n, block_size, n_reps)):
        estimates[i] = metric_fn(values[idx])

    alpha = (1 - ci) / 2
    return (
        float(metric_fn(values)),
        float(np.nanpercentile(estimates, 100 * alpha)),
        float(np.nanpercentile(estimates, 100 * (1 - alpha))),
    )
