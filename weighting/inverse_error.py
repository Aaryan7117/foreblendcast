"""Inverse error weighting: w ∝ 1 / (trailing-30-day RMSE + ε) (B9)."""
from __future__ import annotations

from weighting.base import WeightStrategy
from weighting.baselines import EqualWeights

class InverseError(WeightStrategy):
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
