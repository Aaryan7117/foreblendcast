"""Weighting strategy base class and baselines (B9).

Strategies: climatology, persistence, best_single, equal, inverse_error,
context-aware softmax, shrinkage, oracle.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from canonical.grid import LAT, LON


class WeightStrategy(ABC):
    """Base class for all weighting strategies."""
    name: str

    @abstractmethod
    def compute_weights(self, models: list[str], **context) -> dict[str, float]:
        """Return model->weight dict summing to 1."""
        ...


class EqualWeights(WeightStrategy):
    name = "equal"

    def compute_weights(self, models: list[str], **context) -> dict[str, float]:
        w = 1.0 / len(models)
        return {m: w for m in models}


class BestSingle(WeightStrategy):
    name = "best_single"

    def compute_weights(self, models: list[str], **context) -> dict[str, float]:
        """Pick the model with lowest RMSE. context must have 'rmse' dict."""
        rmse = context.get("rmse", {})
        if not rmse:
            return EqualWeights().compute_weights(models)
        best = min(rmse, key=rmse.get)
        return {m: (1.0 if m == best else 0.0) for m in models}


class InverseError(WeightStrategy):
    """w ∝ 1 / (trailing-30-day RMSE + ε)"""
    name = "inverse_error"

    def __init__(self, epsilon: float = 0.1):
        self.epsilon = epsilon

    def compute_weights(self, models: list[str], **context) -> dict[str, float]:
        rmse = context.get("rmse", {})
        if not rmse:
            return EqualWeights().compute_weights(models)
        raw = {m: 1.0 / (rmse.get(m, 10.0) + self.epsilon) for m in models}
        total = sum(raw.values())
        return {m: v / total for m, v in raw.items()}


class ContextAware(WeightStrategy):
    """Context-aware softmax: w = softmax(-score/τ)"""
    name = "context"

    def __init__(self, tau: float = 1.0):
        self.tau = tau

    def compute_weights(self, models: list[str], **context) -> dict[str, float]:
        scores = context.get("scores", {})
        if not scores:
            return EqualWeights().compute_weights(models)
        # softmax(-score/tau)
        vals = np.array([scores.get(m, 0.0) for m in models])
        exp_vals = np.exp(-vals / self.tau)
        exp_vals /= exp_vals.sum()
        return {m: float(w) for m, w in zip(models, exp_vals)}


class ContextShrinkPM(WeightStrategy):
    """Context-aware + shrinkage + probability-matched — the main strategy."""
    name = "context_shrink_pm"

    def __init__(self, tau: float = 1.0, k: float = 20.0, n_eff_min: int = 15):
        self.tau = tau
        self.k = k
        self.n_eff_min = n_eff_min

    def compute_weights(self, models: list[str], **context) -> dict[str, float]:
        scores = context.get("scores", {})
        n_eff = context.get("n_eff", 100)
        parent_weights = context.get("parent_weights", None)

        if not scores:
            return EqualWeights().compute_weights(models)

        # Local weights via softmax
        vals = np.array([scores.get(m, 0.0) for m in models])
        exp_vals = np.exp(-vals / self.tau)
        exp_vals /= exp_vals.sum()
        local = {m: float(w) for m, w in zip(models, exp_vals)}

        # Shrinkage: λ = n_eff / (n_eff + k)
        lam = n_eff / (n_eff + self.k)
        if n_eff < self.n_eff_min and parent_weights:
            # Inherit parent
            return {m: parent_weights.get(m, 1.0 / len(models)) for m in models}

        if parent_weights:
            return {m: lam * local[m] + (1 - lam) * parent_weights.get(m, local[m])
                    for m in models}
        return local


class Oracle(WeightStrategy):
    """Per-cell hindsight best (ceiling only)."""
    name = "oracle"

    def compute_weights(self, models: list[str], **context) -> dict[str, float]:
        # This is computed cell-by-cell in the blending step
        abs_errors = context.get("abs_errors", {})
        if not abs_errors:
            return EqualWeights().compute_weights(models)
        best = min(abs_errors, key=lambda m: float(np.nanmean(abs_errors[m])))
        return {m: (1.0 if m == best else 0.0) for m in models}


class Climatology(WeightStrategy):
    """Per-cell calendar-day mean of obs over training years."""
    name = "climatology"

    def compute_weights(self, models: list[str], **context) -> dict[str, float]:
        # Climatology doesn't weight models — it's a baseline that produces its own field
        return {m: 0.0 for m in models}


class Persistence(WeightStrategy):
    """Yesterday's observation."""
    name = "persistence"

    def compute_weights(self, models: list[str], **context) -> dict[str, float]:
        return {m: 0.0 for m in models}


# Strategy registry
STRATEGIES: dict[str, WeightStrategy] = {
    "equal": EqualWeights(),
    "best_single": BestSingle(),
    "inverse_error": InverseError(),
    "context": ContextAware(),
    "context_shrink_pm": ContextShrinkPM(),
    "oracle": Oracle(),
    "climatology": Climatology(),
    "persistence": Persistence(),
}
