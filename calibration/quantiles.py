"""Predictive quantiles conditional on the blended value (B11).

Training pairs (blend, observation) are binned on the blend value; each bin keeps the
empirical quantiles of the observations that followed. A new blend value reads its
quantiles by interpolating between bins. This turns the deterministic blend into a
predictive distribution whose spread comes from real past errors.
"""
from __future__ import annotations

import numpy as np

LEVELS = np.round(np.arange(0.05, 0.96, 0.05), 2)


class ConditionalQuantiles:
    def __init__(self, n_bins: int = 25, min_per_bin: int = 200, floor: float | None = None):
        self.n_bins = n_bins
        self.min_per_bin = min_per_bin
        self.floor = floor  # physical lower bound of the variable (0 for rain and wind)
        self.centres: np.ndarray | None = None
        self.table: np.ndarray | None = None  # (n_bins, n_levels)

    def fit(self, pred: np.ndarray, obs: np.ndarray) -> "ConditionalQuantiles":
        ok = np.isfinite(pred) & np.isfinite(obs)
        p, o = pred[ok].astype(np.float64), obs[ok].astype(np.float64)
        if p.size < self.min_per_bin:
            raise ValueError(f"need at least {self.min_per_bin} training pairs, got {p.size}")
        edges = np.unique(np.percentile(p, np.linspace(0, 100, self.n_bins + 1)))
        if len(edges) < 2:
            edges = np.array([p.min(), p.max() + 1e-6])
        which = np.clip(np.searchsorted(edges, p, side="right") - 1, 0, len(edges) - 2)
        centres, rows = [], []
        for b in range(len(edges) - 1):
            sel = which == b
            if sel.sum() < self.min_per_bin:
                continue
            centres.append(p[sel].mean())
            rows.append(np.percentile(o[sel], LEVELS * 100))
        if not rows:
            centres, rows = [p.mean()], [np.percentile(o, LEVELS * 100)]
        order = np.argsort(centres)
        self.centres = np.array(centres)[order]
        self.table = np.array(rows)[order]
        return self

    def predict(self, pred: np.ndarray) -> np.ndarray:
        """Quantiles with shape (n_levels,) + pred.shape. Beyond the last bin the offsets
        of the last bin are carried along with the predicted value."""
        x = np.asarray(pred, dtype=np.float64)
        out = np.empty((len(LEVELS),) + x.shape)
        xc = np.clip(x, self.centres[0], self.centres[-1])
        shift = x - xc
        for i in range(len(LEVELS)):
            out[i] = np.interp(xc, self.centres, self.table[:, i]) + shift
        out = np.maximum.accumulate(out, axis=0)
        if self.floor is not None:
            out = np.maximum(out, self.floor)
        return np.where(np.isfinite(x), out, np.nan)

    def interval(self, pred: np.ndarray, lo: float = 0.05, hi: float = 0.95):
        q = self.predict(pred)
        return q[int(np.argmin(np.abs(LEVELS - lo)))], q[int(np.argmin(np.abs(LEVELS - hi)))]


def crps_from_quantiles(quantiles: np.ndarray, obs: np.ndarray,
                        weights: np.ndarray | None = None) -> float:
    """CRPS approximated as twice the mean pinball loss over the quantile levels."""
    diff = obs[None] - quantiles
    tau = LEVELS.reshape((-1,) + (1,) * obs.ndim)
    pin = np.maximum(tau * diff, (tau - 1.0) * diff).mean(axis=0) * 2.0
    ok = np.isfinite(pin)
    if not ok.any():
        return float("nan")
    if weights is None:
        return float(pin[ok].mean())
    w = np.broadcast_to(weights, pin.shape)[ok]
    return float(np.average(pin[ok], weights=w))


def crps_ensemble(members: np.ndarray, obs: np.ndarray,
                  weights: np.ndarray | None = None) -> float:
    """CRPS of a small equal-weight ensemble: E|X - y| - 0.5 E|X - X'|. members: (M, ...)."""
    m = members.astype(np.float64)
    t1 = np.nanmean(np.abs(m - obs[None]), axis=0)
    t2 = np.nanmean(np.abs(m[:, None] - m[None, :]), axis=(0, 1))
    c = t1 - 0.5 * t2
    ok = np.isfinite(c)
    if not ok.any():
        return float("nan")
    if weights is None:
        return float(c[ok].mean())
    return float(np.average(c[ok], weights=np.broadcast_to(weights, c.shape)[ok]))
