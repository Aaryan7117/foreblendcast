"""Block bootstrap for CIs on metric differences (B6, TECH_APPROACH §2.3).

7-day block bootstrap, 1000 reps, 95% CI on differences vs. best single model.
"""
from __future__ import annotations

import numpy as np


def block_bootstrap_diff(errors_a: np.ndarray, errors_b: np.ndarray,
                         block_size: int = 7, n_reps: int = 1000,
                         ci: float = 0.95) -> tuple[float, float]:
    """Bootstrap CI on the difference in mean |error| between A and B.

    Args:
        errors_a: 1D array of absolute errors for system A (e.g. blend)
        errors_b: 1D array of absolute errors for system B (e.g. best single)
        block_size: block length in days
        n_reps: number of bootstrap replicates
        ci: confidence level

    Returns:
        (lower, upper) bounds of the CI on mean(|A|) - mean(|B|)
    """
    n = len(errors_a)
    n_blocks = max(1, n // block_size)
    diffs = np.empty(n_reps)

    rng = np.random.default_rng(42)
    for i in range(n_reps):
        starts = rng.integers(0, n - block_size + 1, size=n_blocks)
        idx = np.concatenate([np.arange(s, s + block_size) for s in starts])[:n]
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
    n_blocks = max(1, n // block_size)
    estimates = np.empty(n_reps)

    rng = np.random.default_rng(42)
    for i in range(n_reps):
        starts = rng.integers(0, n - block_size + 1, size=n_blocks)
        idx = np.concatenate([np.arange(s, s + block_size) for s in starts])[:n]
        estimates[i] = metric_fn(values[idx])

    alpha = (1 - ci) / 2
    return (
        float(metric_fn(values)),
        float(np.nanpercentile(estimates, 100 * alpha)),
        float(np.nanpercentile(estimates, 100 * (1 - alpha))),
    )
