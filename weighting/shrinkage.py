"""Shrinkage along the spatial hierarchy (B9, TECH_APPROACH §2.2).

Hierarchy: cell -> district -> homogeneous region -> national.
λ = n_eff / (n_eff + k)
If n_eff < n_eff_min, inherit parent and record the reason.

Scores are *errors* (lower is better): w ∝ exp(-score / τ).
"""
from __future__ import annotations

import logging
import numpy as np

from weighting.base import WeightStrategy
from weighting.baselines import EqualWeights

log = logging.getLogger(__name__)


def softmax_weights(errors: np.ndarray, tau: float) -> np.ndarray:
    """w ∝ exp(-error / τ) along axis 0 (the model axis).

    errors: (M, ...) non-negative, NaN where a model has no history (-> weight 0).
    A node where every model is NaN gets equal weights.
    """
    err = np.asarray(errors, dtype=np.float64)
    missing = ~np.isfinite(err)
    filled = np.where(missing, np.inf, err)
    lo = filled.min(axis=0, keepdims=True)
    lo = np.where(np.isfinite(lo), lo, 0.0)
    with np.errstate(invalid="ignore", over="ignore"):
        w = np.exp(-(filled - lo) / tau)
    w = np.where(missing, 0.0, w)
    total = w.sum(axis=0, keepdims=True)
    equal = np.full_like(w, 1.0 / err.shape[0])
    return np.where(total > 0, w / np.where(total > 0, total, 1.0), equal)


def shrink(local: np.ndarray, parent: np.ndarray, n_eff: np.ndarray,
           k: float = 20.0, n_eff_min: float = 15.0) -> tuple[np.ndarray, np.ndarray]:
    """Blend local weights with the parent node: λ·local + (1-λ)·parent.

    local, parent: (M, ...); n_eff: (...). Returns (weights, λ) with λ = 0 where the
    node inherits its parent outright (n_eff < n_eff_min).
    """
    n_eff = np.asarray(n_eff, dtype=np.float64)
    lam = np.where(n_eff < n_eff_min, 0.0, n_eff / (n_eff + k))
    w = lam * local + (1.0 - lam) * parent
    total = w.sum(axis=0, keepdims=True)
    return w / np.where(total > 0, total, 1.0), lam


class ContextShrinkPM(WeightStrategy):
    name = "context_shrink_pm"

    def __init__(self, tau: float = 1.0, k: float = 20.0, n_eff_min: int = 15):
        self.tau = tau
        self.k = k
        self.n_eff_min = n_eff_min

    def compute_weights(self, models: list[str], **context) -> dict[str, float]:
        """Compute shrunk weights for a specific node in the hierarchy.

        Requires context:
          - scores: dict[model, float]  historical error of each model at this node
          - n_eff: int
          - parent_weights: dict[model, float] (if applicable)
          - node_id: str (for logging)
        """
        scores = context.get("scores", {})
        n_eff = context.get("n_eff", 0)
        parent_weights = context.get("parent_weights", None)
        node_id = context.get("node_id", "unknown")

        if not scores:
            if parent_weights:
                return parent_weights.copy()
            return EqualWeights().compute_weights(models)

        vals = np.array([scores.get(m, np.nan) for m in models], dtype=np.float64)
        local_arr = softmax_weights(vals, self.tau)
        local = {m: float(w) for m, w in zip(models, local_arr)}

        if not parent_weights:
            return local

        if n_eff < self.n_eff_min:
            log.info("shrinkage.inherit", extra={
                "node": node_id, "n_eff": n_eff,
                "reason": f"n_eff < {self.n_eff_min}"
            })
        parent_arr = np.array([parent_weights.get(m, local[m]) for m in models])
        w, _ = shrink(local_arr, parent_arr, n_eff, self.k, self.n_eff_min)
        return {m: float(x) for m, x in zip(models, w)}
