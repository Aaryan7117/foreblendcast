"""Simple baselines: climatology, persistence, best_single, equal (B9)."""
from __future__ import annotations

import numpy as np

from weighting.base import WeightStrategy

class EqualWeights(WeightStrategy):
    name = "equal"

    def compute_weights(self, models: list[str], **context) -> dict[str, float]:
        w = 1.0 / len(models)
        return {m: w for m in models}


class BestSingle(WeightStrategy):
    name = "best_single"

    def compute_weights(self, models: list[str], **context) -> dict[str, float]:
        """Pick the model with lowest RMSE globally. Context must have 'rmse' dict."""
        rmse = context.get("rmse", {})
        if not rmse:
            return EqualWeights().compute_weights(models)
        best = min(rmse, key=rmse.get)
        return {m: (1.0 if m == best else 0.0) for m in models}


class Climatology(WeightStrategy):
    """Per-cell calendar-day mean of obs over training years."""
    name = "climatology"

    def compute_weights(self, models: list[str], **context) -> dict[str, float]:
        return {m: 0.0 for m in models}


class Persistence(WeightStrategy):
    """Yesterday's observation."""
    name = "persistence"

    def compute_weights(self, models: list[str], **context) -> dict[str, float]:
        return {m: 0.0 for m in models}
