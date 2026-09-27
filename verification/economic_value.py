"""Relative Economic Value curve over C/L ∈ [0.01, 0.99] (B6)."""
from __future__ import annotations

import numpy as np


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
