"""Base class for weighting strategies (B9)."""
from __future__ import annotations

from abc import ABC, abstractmethod
import numpy as np

class WeightStrategy(ABC):
    """Base class for all weighting strategies."""
    name: str

    @abstractmethod
    def compute_weights(self, models: list[str], **context) -> dict[str, float | np.ndarray]:
        """Return model->weight dict summing to 1. Weights can be floats or per-cell arrays."""
        ...
