"""Probabilistic verification (B6): Brier, BSS, reliability, ROC-AUC, CRPS."""
from __future__ import annotations

import numpy as np


def brier_score(prob: np.ndarray, obs_binary: np.ndarray) -> float:
    """Brier score = mean((p - o)^2)."""
    return float(np.nanmean((prob - obs_binary) ** 2))


def brier_skill_score(prob: np.ndarray, obs_binary: np.ndarray,
                      base_rate: float | None = None) -> float:
    """BSS = 1 - BS / BS_ref, the reference being a constant climatological probability.

    base_rate: the climatological event frequency to use as the reference forecast.
    Pass the training-period frequency for an out-of-sample reference; when omitted the
    sample frequency of obs_binary is used (the in-sample, hardest-to-beat constant).
    """
    bs = brier_score(prob, obs_binary)
    if base_rate is None:
        clim = float(np.nanmean(obs_binary))
        bs_ref = clim * (1 - clim)
    else:
        bs_ref = float(np.nanmean((base_rate - obs_binary) ** 2))
    if bs_ref == 0:
        return 0.0
    return float(1.0 - bs / bs_ref)


def reliability_bins(prob: np.ndarray, obs_binary: np.ndarray,
                     n_bins: int = 10) -> dict:
    """Reliability diagram data: bin midpoints, mean forecast, observed frequencies, counts."""
    edges = np.linspace(0, 1, n_bins + 1)
    midpoints = (edges[:-1] + edges[1:]) / 2
    ok = np.isfinite(prob) & np.isfinite(obs_binary)
    p, o = np.asarray(prob)[ok], np.asarray(obs_binary)[ok]
    which = np.clip(np.digitize(p, edges[1:-1]), 0, n_bins - 1)
    counts = np.bincount(which, minlength=n_bins)
    obs_sum = np.bincount(which, weights=o, minlength=n_bins)
    fc_sum = np.bincount(which, weights=p, minlength=n_bins)
    nz = np.maximum(counts, 1)
    return {
        "bins": midpoints.tolist(),
        "mean_forecast": (fc_sum / nz).tolist(),
        "observed_freq": (obs_sum / nz).tolist(),
        "counts": counts.astype(int).tolist(),
    }


def roc_auc(prob: np.ndarray, obs_binary: np.ndarray) -> float:
    """Area under ROC curve (trapezoidal), with correct handling of tied probabilities.

    Tied scores are moved through together so the curve steps diagonally
    (an all-tied forecast gives exactly 0.5 instead of a staircase artefact).
    """
    prob = np.asarray(prob, dtype=float).ravel()
    obs = np.asarray(obs_binary).ravel() > 0.5
    ok = np.isfinite(prob)
    prob, obs = prob[ok], obs[ok]
    n_pos = int(obs.sum())
    n_neg = int(obs.size - n_pos)
    if n_pos == 0 or n_neg == 0:
        return 0.5

    # one ROC point per distinct probability, from the highest threshold down
    values, inverse = np.unique(prob, return_inverse=True)
    pos = np.bincount(inverse, weights=obs, minlength=values.size)[::-1]
    tot = np.bincount(inverse, minlength=values.size)[::-1]
    tpr = np.concatenate([[0.0], np.cumsum(pos) / n_pos])
    fpr = np.concatenate([[0.0], np.cumsum(tot - pos) / n_neg])

    _trapz = getattr(np, "trapezoid", None) or np.trapz  # numpy 2 renamed trapz
    return float(_trapz(tpr, fpr))
