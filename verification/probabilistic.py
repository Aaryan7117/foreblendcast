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


def economic_value(prob: np.ndarray, obs_binary: np.ndarray,
                   cl_values: np.ndarray | None = None) -> dict:
    """Relative Economic Value curve over C/L ∈ [0.01, 0.99].

    Richardson (2000) formulation.
    """
    if cl_values is None:
        cl_values = np.arange(0.01, 1.0, 0.01)

    o_rate = float(np.nanmean(obs_binary))  # climatological event frequency
    rev_values = []

    for cl in cl_values:
        best_rev = -1.0
        for p_star in np.arange(0.0, 1.01, 0.05):
            act = prob >= p_star
            hits = float(np.nanmean(act & (obs_binary == 1)))
            fa = float(np.nanmean(act & (obs_binary == 0)))
            misses = float(np.nanmean((~act) & (obs_binary == 1)))

            # Cost of acting on false alarms + cost of missing
            expense = cl * fa * (1 - o_rate) + misses * o_rate
            # Cost of doing nothing (always miss)
            clim_expense = min(cl * (1 - o_rate), o_rate)
            # Cost of perfect forecast
            perfect_expense = 0.0

            if clim_expense == 0:
                rev = 0.0
            else:
                rev = (clim_expense - expense) / clim_expense
            best_rev = max(best_rev, rev)

        rev_values.append(round(best_rev, 6))

    return {
        "cost_loss": [round(float(c), 3) for c in cl_values],
        "rev": rev_values,
    }
