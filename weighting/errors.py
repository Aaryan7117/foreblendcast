"""Error database (B8)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from canonical.grid import LAT, LON
from experiments.design import SEASON_OF_MONTH

ERRORS_PATH = Path("data/errors.zarr")


def build_error_entry(model: str, variable: str, lead_day: int,
                      valid_date: pd.Timestamp,
                      forecast: np.ndarray, truth: np.ndarray) -> dict:
    err = forecast - truth
    return {
        "model": model, "variable": variable, "lead_day": lead_day,
        "valid_date": valid_date, "season": SEASON_OF_MONTH[valid_date.month],
        "signed_error": err, "abs_error": np.abs(err),
    }


def trailing_rmse(errors: list[np.ndarray], window: int = 30) -> np.ndarray:
    if not errors:
        return np.full((len(LAT), len(LON)), np.nan)
    recent = errors[-window:]
    stack = np.stack(recent, axis=0)
    return np.sqrt(np.nanmean(stack ** 2, axis=0))


def sample_counts(errors_by_context: dict) -> dict:
    return {f"{r}_{l}_{s}": len(e) for (r, l, s), e in errors_by_context.items()}
