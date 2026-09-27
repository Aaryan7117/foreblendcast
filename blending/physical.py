"""Physical validator (TECH_APPROACH §2.5, WORK_SPLIT B10).

Clips rain < 0, ensures Tmax >= Tmin, derives wind speed.
Writes to results/validator_log.jsonl via structlog.
"""
from __future__ import annotations

import numpy as np

import canonical.logging

log = canonical.logging.get_logger(__name__)


def physical_validate(blend: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    """Physical validator: clip rain < 0, ensure Tmax >= Tmin, derive wind speed.

    Args:
        blend: dict with keys like 'precip', 't2m', 'tmax', 'tmin', 'u10', 'v10'
    Returns:
        corrected dict
    """
    if "precip" in blend:
        neg = blend["precip"] < 0
        n_neg = int(neg.sum())
        if n_neg > 0:
            log.info("validator.correct", field="precip", rule="clip_negative", count=n_neg)
            blend["precip"] = np.maximum(blend["precip"], 0.0)

    if "tmax" in blend and "tmin" in blend:
        invalid = blend["tmax"] < blend["tmin"]
        n_inv = int(invalid.sum())
        if n_inv > 0:
            log.info("validator.correct", field="tmax_tmin", rule="tmax_ge_tmin", count=n_inv)
            # Fix by setting Tmax = Tmin where Tmax < Tmin
            blend["tmax"][invalid] = blend["tmin"][invalid]

    # Derive wind speed from u, v
    if "u10" in blend and "v10" in blend:
        blend["wind_speed"] = np.sqrt(blend["u10"]**2 + blend["v10"]**2).astype(np.float32)

    return blend
