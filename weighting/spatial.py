"""Gaussian smoothing of the final weight field (B9).

σ = 1 cell, masked at the Ghats crest.
"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter

def apply_spatial_smoothing(
    weight_field: np.ndarray, 
    terrain_classes: np.ndarray,
    sigma: float = 1.0
) -> np.ndarray:
    """Apply Gaussian smoothing respecting the Ghats crest boundary.
    
    weight_field: 2D array of weights (lat, lon)
    terrain_classes: 2D string array from canonical/terrain.py
    
    Smooths separately on windward/leeward sides of the Ghats to avoid
    blurring weights across the major orographic divide.
    """
    windward = terrain_classes == "ghats_windward"
    leeward_or_other = ~windward
    
    smoothed = np.zeros_like(weight_field)
    
    # Smooth windward side
    w_wind = weight_field.copy()
    w_wind[leeward_or_other] = np.nan
    # Replace NaNs with nearest valid for filter boundary effects
    mask = np.isnan(w_wind)
    w_wind[mask] = np.nanmean(w_wind) if not np.all(mask) else 0.0
    s_wind = gaussian_filter(w_wind, sigma=sigma, mode="nearest")
    
    # Smooth leeward side
    w_other = weight_field.copy()
    w_other[windward] = np.nan
    mask = np.isnan(w_other)
    w_other[mask] = np.nanmean(w_other) if not np.all(mask) else 0.0
    s_other = gaussian_filter(w_other, sigma=sigma, mode="nearest")
    
    smoothed[windward] = s_wind[windward]
    smoothed[leeward_or_other] = s_other[leeward_or_other]
    
    return smoothed
