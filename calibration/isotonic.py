"""Isotonic calibration (B11, TECH_APPROACH §2.6).

Fits and applies isotonic regression. One calibrator per availability pattern.
"""
from __future__ import annotations

import numpy as np
from sklearn.isotonic import IsotonicRegression


def calibrate_isotonic(train_probs: np.ndarray, train_obs: np.ndarray) -> IsotonicRegression:
    """Fit isotonic calibration on training fold."""
    ir = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip")
    
    # Filter valid data
    valid = np.isfinite(train_probs) & np.isfinite(train_obs)
    if not valid.any():
        # Fallback to identity if no valid data
        ir.fit([0.0, 1.0], [0.0, 1.0])
        return ir
        
    ir.fit(train_probs[valid].ravel(), train_obs[valid].ravel())
    return ir


def apply_calibration(calibrator: IsotonicRegression, probs: np.ndarray) -> np.ndarray:
    """Apply isotonic calibration to probability field."""
    shape = probs.shape
    valid = np.isfinite(probs)
    
    out = np.full(shape, np.nan, dtype=np.float32)
    if valid.any():
        cal = calibrator.predict(probs[valid])
        out[valid] = cal.astype(np.float32)
        
    return out
