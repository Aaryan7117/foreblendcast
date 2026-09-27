"""Base adapter class (B4). Every model adapter inherits from this."""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import xarray as xr

from canonical import accumulation as acc
from canonical.forecast import CanonicalForecast
from canonical.grid import LAT, LON
from canonical.units import CANONICAL_UNITS

RAW = Path("data/raw")


class Adapter(ABC):
    """Abstract base for model adapters.

    Every adapter reads local NetCDF files (downloaded by ingestion/download.py)
    and returns CanonicalForecast objects aligned to the IMD grid.
    """
    name: str
    label: str
    kind: str  # "nwp" | "ensemble" | "ai"
    variables: tuple[str, ...]

    @abstractmethod
    def load(self, init_time: pd.Timestamp, variable: str,
             lead_days: list[int] | None = None) -> Optional[CanonicalForecast]:
        """Load one forecast. Returns None if data is missing."""
        ...

    def _read_nc(self, variable: str, month: str) -> Optional[xr.Dataset]:
        """Read a monthly NetCDF file from data/raw/<model>/<var>/<month>.nc"""
        path = RAW / self.name / variable / f"{month}.nc"
        if not path.exists():
            return None
        return xr.open_dataset(path)

    def _build_forecast(self, init_time: pd.Timestamp, variable: str,
                        lead_days: list[int], values: np.ndarray) -> CanonicalForecast:
        valid_times = [acc.imd_date(init_time, d) for d in lead_days]
        return CanonicalForecast(
            model=self.name,
            model_version=self.label,
            init_time=init_time.to_pydatetime(),
            valid_times=[v.to_pydatetime() for v in valid_times],
            lead_days=lead_days,
            variable=variable,
            accumulation_hours=24 if variable == "precip" else None,
            accumulation_window_utc="03:00-03:00" if variable == "precip" else None,
            units=CANONICAL_UNITS[variable],
            lat=LAT,
            lon=LON,
            values=values,
        )
