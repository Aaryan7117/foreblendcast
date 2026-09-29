"""Fractions Skill Score (B6, TECH_APPROACH §2.3).

FSS at neighbourhoods {1, 3, 5, 9, 19} cells for thresholds {15.6, 64.5, 115.6, 204.5} mm.
Reports f0 and fss_useful = 0.5 + f0/2 alongside.

Scale labels are the true neighbourhood widths on the 0.25° grid (27.8 km per cell).
The ladder's headline FSS uses HEADLINE_NEIGHBOURHOOD = 3 cells (~83 km), the closest
the grid gets to a 50 km scale above a single cell.
"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import uniform_filter


THRESHOLDS_MM = (15.6, 64.5, 115.6, 204.5)
NEIGHBOURHOODS = (1, 3, 5, 9, 19)
KM_PER_CELL = 27.8
SCALES_KM = tuple(int(round(n * KM_PER_CELL)) for n in NEIGHBOURHOODS)
HEADLINE_NEIGHBOURHOOD = 3


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


def fss_pooled(forecast: np.ndarray, truth: np.ndarray, threshold: float,
               neighbourhood: int, mask: np.ndarray | None = None) -> float:
    """FSS over a stack of days (n, lat, lon), pooling numerator and denominator.

    Pooling avoids averaging per-day scores, where the many days without any event
    would each contribute a meaningless perfect 1.0. NaN if the event never occurs
    in either forecast or truth.
    """
    return fss_from_parts(*fss_parts(forecast, truth, threshold, neighbourhood, mask))


def fss_parts(forecast: np.ndarray, truth: np.ndarray, threshold: float,
              neighbourhood: int, mask: np.ndarray | None = None) -> tuple[float, float]:
    """(sum of squared fraction differences, reference sum) so folds can be pooled."""
    ok = np.isfinite(forecast) & np.isfinite(truth)
    bf = ((forecast >= threshold) & ok).astype(np.float32)
    bo = ((truth >= threshold) & ok).astype(np.float32)
    if neighbourhood > 1:
        size = (1, neighbourhood, neighbourhood)
        bf = uniform_filter(bf, size=size, mode="constant")
        bo = uniform_filter(bo, size=size, mode="constant")
    if mask is not None:
        bf, bo = bf[:, mask], bo[:, mask]
    num = float(np.sum((bf - bo).astype(np.float64) ** 2))
    ref = float(np.sum(bf.astype(np.float64) ** 2) + np.sum(bo.astype(np.float64) ** 2))
    return num, ref


def fss_from_parts(num: float, ref: float) -> float:
    return float("nan") if ref == 0 else float(1.0 - num / ref)
