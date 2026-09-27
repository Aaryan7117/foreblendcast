"""Fractions Skill Score (B6, TECH_APPROACH §2.3).

FSS at neighbourhoods {1, 5, 9, 19, 29} cells for thresholds {15.6, 64.5, 115.6, 204.5} mm.
Reports f0 and fss_useful = 0.5 + f0/2 alongside.
"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import uniform_filter


THRESHOLDS_MM = (15.6, 64.5, 115.6, 204.5)
NEIGHBOURHOODS = (1, 5, 9, 19, 29)
# Nominal scale labels (km) at 0.25° ≈ 27.8 km/cell
SCALES_KM = (5, 25, 50, 100, 150)


def fss(forecast: np.ndarray, truth: np.ndarray,
        threshold: float, neighbourhood: int) -> float:
    """Compute FSS for a single field at a single threshold and neighbourhood.

    Args:
        forecast: 2D array (lat, lon) of rain in mm
        truth: 2D array (lat, lon) of rain in mm
        threshold: mm threshold for binary conversion
        neighbourhood: filter size in grid cells (must be odd)
    """
    bf = (forecast >= threshold).astype(np.float64)
    bo = (truth >= threshold).astype(np.float64)

    if neighbourhood > 1:
        pf = uniform_filter(bf, size=neighbourhood, mode="constant")
        po = uniform_filter(bo, size=neighbourhood, mode="constant")
    else:
        pf, po = bf, bo

    mse = np.nanmean((pf - po) ** 2)
    ref = np.nanmean(pf ** 2) + np.nanmean(po ** 2)

    if ref == 0:
        return 1.0  # perfect score when nothing happens
    return float(1.0 - mse / ref)


def f0_and_useful(truth: np.ndarray, threshold: float) -> tuple[float, float]:
    """Climatological frequency f0 and FSS_useful = 0.5 + f0/2."""
    bo = (truth >= threshold).astype(np.float64)
    f0 = float(np.nanmean(bo))
    return f0, 0.5 + f0 / 2


def fss_curve(forecast: np.ndarray, truth: np.ndarray,
              threshold: float) -> dict:
    """FSS at all standard neighbourhoods plus f0 and FSS_useful."""
    f0, useful = f0_and_useful(truth, threshold)
    scores = [fss(forecast, truth, threshold, n) for n in NEIGHBOURHOODS]
    return {
        "threshold_mm": threshold,
        "scales_km": list(SCALES_KM),
        "neighbourhoods": list(NEIGHBOURHOODS),
        "fss": scores,
        "f0": f0,
        "fss_useful": useful,
    }
