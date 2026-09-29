"""Relative Economic Value curve over C/L ∈ [0.01, 0.99] (B6)."""
from __future__ import annotations

import numpy as np

P_STAR = np.round(np.arange(0.0, 1.0001, 0.05), 2)


def contingency(prob: np.ndarray, obs_binary: np.ndarray,
                p_star: np.ndarray = P_STAR) -> tuple[np.ndarray, np.ndarray, float]:
    """Joint frequencies (hits, false alarms) of acting when prob >= p*, and the base rate."""
    ok = np.isfinite(prob) & np.isfinite(obs_binary)
    p, o = np.asarray(prob)[ok], np.asarray(obs_binary)[ok] > 0.5
    n = p.size
    if n == 0:
        return np.zeros(len(p_star)), np.zeros(len(p_star)), float("nan")
    order = np.sort(p)
    order_event = np.sort(p[o])
    acted = n - np.searchsorted(order, p_star, side="left")
    hits = order_event.size - np.searchsorted(order_event, p_star, side="left")
    return hits / n, (acted - hits) / n, float(o.mean())


def economic_value(prob: np.ndarray, obs_binary: np.ndarray,
                   cl_values: np.ndarray | None = None) -> dict:
    """Relative Economic Value curve over C/L ∈ [0.01, 0.99].

    Richardson (2000): with costs in units of the loss L and α = C/L,
        E_forecast = α·(hits + false alarms) + misses
        E_climate  = min(α, ō)          (always or never protect)
        E_perfect  = α·ō
        REV        = (E_climate − E_forecast) / (E_climate − E_perfect)
    For each α the best probability threshold p* is used (the envelope).
    A deterministic forecast is passed as probabilities of 0 and 1.
    """
    if cl_values is None:
        cl_values = np.arange(0.01, 1.0, 0.01)
    cl = np.asarray(cl_values, dtype=np.float64)

    hits, fa, o_rate = contingency(prob, obs_binary)
    if not np.isfinite(o_rate) or o_rate in (0.0, 1.0):
        rev = np.zeros(len(cl))
    else:
        misses = o_rate - hits
        expense = cl[:, None] * (hits + fa)[None, :] + misses[None, :]
        e_clim = np.minimum(cl, o_rate)
        e_perf = cl * o_rate
        denom = e_clim - e_perf
        rev = np.where(denom > 0, (e_clim[:, None] - expense).max(axis=1) / np.where(denom > 0, denom, 1.0), 0.0)

    return {
        "cost_loss": [round(float(c), 3) for c in cl],
        "rev": [round(float(v), 6) for v in rev],
    }


def rev_at(prob: np.ndarray, obs_binary: np.ndarray, cost_loss: float = 0.1) -> float:
    return economic_value(prob, obs_binary, np.array([cost_loss]))["rev"][0]


def rev_from_counts(hits: int, false_alarms: int, misses: int, n: int,
                    cost_loss: float = 0.1) -> float:
    """REV of a yes/no forecast from its contingency table."""
    if n == 0:
        return float("nan")
    o_rate = (hits + misses) / n
    if o_rate in (0.0, 1.0):
        return 0.0
    expense = cost_loss * (hits + false_alarms) / n + misses / n
    e_clim = min(cost_loss, o_rate)
    denom = e_clim - cost_loss * o_rate
    return float((e_clim - expense) / denom) if denom > 0 else 0.0
