"""Disagreement index (B11).

D = spread / climatological_spread
"""
from __future__ import annotations

import numpy as np


def disagreement_index(member_values: dict[str, np.ndarray],
                       clim_spread: np.ndarray) -> np.ndarray:
    """D = std(members) / climatological_spread. D > 1.5 -> attention."""
    stack = np.stack(list(member_values.values()), axis=0)
    spread = np.nanstd(stack, axis=0)
    
    with np.errstate(divide="ignore", invalid="ignore"):
        D = np.where(clim_spread > 0, spread / clim_spread, 0.0)
        
    return D.astype(np.float32)
