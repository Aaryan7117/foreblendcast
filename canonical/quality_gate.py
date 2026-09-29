"""Quality gate: schema + coord + time + window + unit + NaN + range checks (B3).

A failing forecast is rejected with a structured reason. The cycle continues.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np

from canonical.forecast import CanonicalForecast, CanonicalTruth
from canonical.grid import LAT, LON

logger = logging.getLogger(__name__)

# Hard limits: a field outside them is implausible and the model is dropped for the day.
# They are deliberately wide. Real forecasts in the archive reach 1340 mm/day (IFS HRES,
# single cell) and -43 degC over the Tibetan plateau, and must not be rejected.
RANGE_LIMITS = {
    "precip": (-10.0, 2000.0),
    "t2m":    (-60.0, 60.0),
    "u10":    (-80.0, 80.0),
    "v10":    (-80.0, 80.0),
    "wind":   (0.0, 115.0),
}

# Soft limits: values beyond them are repaired in place and counted, not rejected.
# AI models produce slightly negative rain (GraphCast: down to -8 mm).
REPAIR_FLOOR = {"precip": 0.0}

MAX_NAN_FRAC = 0.05  # reject if >5% NaN over land


@dataclass
class QCResult:
    passed: bool
    reason: Optional[str] = None


def _check_grid(lat: np.ndarray, lon: np.ndarray) -> Optional[str]:
    if len(lat) != len(LAT) or len(lon) != len(LON):
        return f"grid_size_mismatch: got ({len(lat)}, {len(lon)}), expected ({len(LAT)}, {len(LON)})"
    if not np.allclose(lat, LAT, atol=0.01):
        return "lat_mismatch"
    if not np.allclose(lon, LON, atol=0.01):
        return "lon_mismatch"
    return None


def _check_range(values: np.ndarray, variable: str) -> Optional[str]:
    lo, hi = RANGE_LIMITS.get(variable, (-1e9, 1e9))
    finite = values[np.isfinite(values)]
    if len(finite) == 0:
        return "all_nan"
    vmin, vmax = float(finite.min()), float(finite.max())
    if vmin < lo or vmax > hi:
        return f"range_violation: [{vmin:.1f}, {vmax:.1f}] outside [{lo}, {hi}]"
    return None


def _check_nan(values: np.ndarray, land_mask: np.ndarray | None = None) -> Optional[str]:
    if land_mask is not None:
        land_vals = values[..., land_mask]
    else:
        land_vals = values
    frac = np.isnan(land_vals).mean()
    if frac > MAX_NAN_FRAC:
        return f"nan_fraction: {frac:.3f} > {MAX_NAN_FRAC}"
    return None


def check_forecast(fc: CanonicalForecast, land_mask: np.ndarray | None = None) -> QCResult:
    """Run all QC checks on a canonical forecast."""
    # Grid check
    reason = _check_grid(fc.lat, fc.lon)
    if reason:
        logger.warning("qc.reject", extra={"model": fc.model, "variable": fc.variable, "reason": reason})
        return QCResult(passed=False, reason=reason)

    # Shape check
    expected = (len(fc.lead_days), len(fc.lat), len(fc.lon))
    if fc.values.shape != expected:
        reason = f"shape_mismatch: {fc.values.shape} vs {expected}"
        logger.warning("qc.reject", extra={"model": fc.model, "reason": reason})
        return QCResult(passed=False, reason=reason)

    # Range check
    reason = _check_range(fc.values, fc.variable)
    if reason:
        logger.warning("qc.reject", extra={"model": fc.model, "variable": fc.variable, "reason": reason})
        return QCResult(passed=False, reason=reason)

    # NaN check
    reason = _check_nan(fc.values, land_mask)
    if reason:
        logger.warning("qc.reject", extra={"model": fc.model, "variable": fc.variable, "reason": reason})
        return QCResult(passed=False, reason=reason)

    return QCResult(passed=True)


def check_truth(truth: CanonicalTruth) -> QCResult:
    """Run QC checks on a truth object."""
    reason = _check_grid(truth.lat, truth.lon)
    if reason:
        return QCResult(passed=False, reason=reason)
    reason = _check_range(truth.values, truth.variable)
    if reason:
        return QCResult(passed=False, reason=reason)
    reason = _check_nan(truth.values, truth.land_mask)
    if reason:
        return QCResult(passed=False, reason=reason)
    return QCResult(passed=True)


def repair(values: np.ndarray, variable: str) -> tuple[np.ndarray, int]:
    """Clip to the physical floor of the variable. Returns (values, cells repaired)."""
    floor = REPAIR_FLOOR.get(variable)
    if floor is None:
        return values, 0
    with np.errstate(invalid="ignore"):
        bad = values < floor
    n = int(bad.sum())
    return (np.where(bad, floor, values).astype(values.dtype), n) if n else (values, 0)


def check_field(values: np.ndarray, variable: str,
                land_mask: np.ndarray | None = None) -> QCResult:
    """Range and NaN checks on one (lat, lon) field that is already on the canonical grid."""
    if values.shape[-2:] != (len(LAT), len(LON)):
        return QCResult(False, f"shape_mismatch: {values.shape}")
    reason = _check_range(values, variable) or _check_nan(values, land_mask)
    return QCResult(passed=reason is None, reason=reason)


def screen_stack(stack: np.ndarray, variable: str,
                 land_mask: np.ndarray | None = None) -> tuple[np.ndarray, dict[int, str], int]:
    """Gate every day of a (n, lat, lon) stack before it can enter a blend.

    A rejected day becomes all-NaN, so the blend drops that model for the day and
    renormalises the remaining weights. Returns (clean stack, {day index: reason},
    number of repaired cells).
    """
    out = np.array(stack, dtype=np.float32)
    lo, hi = RANGE_LIMITS.get(variable, (-1e9, 1e9))
    flat = out.reshape(out.shape[0], -1)
    finite = np.isfinite(flat)
    with np.errstate(invalid="ignore"):
        vmax = np.where(finite, flat, -np.inf).max(axis=1)
        vmin = np.where(finite, flat, np.inf).min(axis=1)
    cells = flat[:, land_mask.ravel()] if land_mask is not None else flat
    nan_frac = np.isnan(cells).mean(axis=1)
    rejected: dict[int, str] = {}
    for d in range(out.shape[0]):
        if not finite[d].any():
            rejected[d] = "all_nan"
        elif vmin[d] < lo or vmax[d] > hi:
            rejected[d] = f"range_violation: [{vmin[d]:.1f}, {vmax[d]:.1f}] outside [{lo}, {hi}]"
        elif nan_frac[d] > MAX_NAN_FRAC:
            rejected[d] = f"nan_fraction: {nan_frac[d]:.3f} > {MAX_NAN_FRAC}"
    for d in rejected:
        out[d] = np.nan
    out, n_fixed = repair(out, variable)
    return out, rejected, n_fixed
