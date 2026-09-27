"""Error database (B8): per-(model, variable, lead_day, valid_date, lat, lon) errors.

Builds errors.zarr indexed with signed error and |error|; plus sample counts
per (region × lead × season × regime).
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import xarray as xr

from canonical import accumulation as acc
from canonical.grid import LAT, LON
from experiments.design import SEASON_OF_MONTH


ERRORS_PATH = Path("data/errors.zarr")


def build_error_entry(model: str, variable: str, lead_day: int,
                      valid_date: pd.Timestamp,
                      forecast: np.ndarray, truth: np.ndarray) -> dict:
    """Create a single error record: signed error and |error| at (lat, lon)."""
    err = forecast - truth
    return {
        "model": model,
        "variable": variable,
        "lead_day": lead_day,
        "valid_date": valid_date,
        "season": SEASON_OF_MONTH[valid_date.month],
        "signed_error": err,
        "abs_error": np.abs(err),
    }


def trailing_rmse(errors: list[np.ndarray], window: int = 30) -> np.ndarray:
    """Trailing-window RMSE from a list of (lat, lon) error arrays."""
    if not errors:
        return np.zeros((len(LAT), len(LON)))
    recent = errors[-window:]
    stack = np.stack(recent, axis=0)
    return np.sqrt(np.nanmean(stack ** 2, axis=0))


def sample_counts(errors_by_context: dict) -> dict:
    """Count samples per context key for estimability checking.

    errors_by_context: dict of {(region, lead, season): list_of_error_arrays}
    """
    counts = {}
    for key, errs in errors_by_context.items():
        region, lead, season = key
        counts[f"{region}_{lead}_{season}"] = len(errs)
    return counts
