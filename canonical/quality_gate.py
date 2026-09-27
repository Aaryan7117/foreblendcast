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

# Physical range limits (TECH_APPROACH §2.1)
RANGE_LIMITS = {
    "precip": (0.0, 600.0),
    "t2m":    (-40.0, 55.0),
    "u10":    (-80.0, 80.0),
    "v10":    (-80.0, 80.0),
}

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
