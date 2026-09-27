"""Probabilistic verification (B6): Brier, BSS, reliability, ROC-AUC, CRPS."""
from __future__ import annotations

import numpy as np


def brier_score(prob: np.ndarray, obs_binary: np.ndarray) -> float:
    """Brier score = mean((p - o)^2)."""
    return float(np.nanmean((prob - obs_binary) ** 2))


def brier_skill_score(prob: np.ndarray, obs_binary: np.ndarray) -> float:
    """BSS = 1 - BS / BS_clim where BS_clim uses mean(obs)."""
    bs = brier_score(prob, obs_binary)
    clim = float(np.nanmean(obs_binary))
    bs_clim = clim * (1 - clim)
    if bs_clim == 0:
        return 0.0
    return float(1.0 - bs / bs_clim)


def reliability_bins(prob: np.ndarray, obs_binary: np.ndarray,
                     n_bins: int = 10) -> dict:
    """Reliability diagram data: bin midpoints, observed frequencies, counts."""
    edges = np.linspace(0, 1, n_bins + 1)
    midpoints = (edges[:-1] + edges[1:]) / 2
    obs_freq = np.zeros(n_bins)
    counts = np.zeros(n_bins, dtype=int)
    for i in range(n_bins):
        mask = (prob >= edges[i]) & (prob < edges[i + 1])
        if i == n_bins - 1:
            mask = (prob >= edges[i]) & (prob <= edges[i + 1])
        counts[i] = int(mask.sum())
        if counts[i] > 0:
            obs_freq[i] = float(np.nanmean(obs_binary[mask]))
    return {
        "bins": midpoints.tolist(),
        "observed_freq": obs_freq.tolist(),
        "counts": counts.tolist(),
    }


def roc_auc(prob: np.ndarray, obs_binary: np.ndarray) -> float:
    """Area under ROC curve (trapezoidal)."""
    # Sort by decreasing probability
    idx = np.argsort(-prob)
    p_sorted = prob[idx]
    o_sorted = obs_binary[idx]

    n_pos = o_sorted.sum()
    n_neg = len(o_sorted) - n_pos
    if n_pos == 0 or n_neg == 0:
        return 0.5

    tpr_list, fpr_list = [0.0], [0.0]
    tp, fp = 0, 0
    for o in o_sorted:
        if o:
            tp += 1
        else:
            fp += 1
        tpr_list.append(tp / n_pos)
        fpr_list.append(fp / n_neg)

    auc = float(np.trapz(tpr_list, fpr_list))
    return auc

