"""Ground truth loader (B5): ERA5 (or IMD) onto the canonical grid."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import xarray as xr

from canonical.forecast import CanonicalTruth
from canonical.grid import LAT, LON
from canonical.units import CANONICAL_UNITS

RAW = Path("data/raw/era5")


def truth(date: pd.Timestamp, variable: str,
          land_mask: np.ndarray | None = None) -> Optional[CanonicalTruth]:
    """Load ERA5 truth for an IMD day. Returns None if missing."""
    month = date.strftime("%Y-%m")
    path = RAW / variable / f"{month}.nc"
    if not path.exists():
        return None
    ds = xr.open_dataset(path)
    day_idx = pd.Timestamp(date.date())
    if day_idx not in ds.date.values:
        ds.close()
        return None
    vals = ds[variable].sel(date=day_idx).values.astype(np.float32)
    ds.close()
    return CanonicalTruth(
        source="ERA5 (WeatherBench2)",
        variable=variable,
        date=day_idx.to_pydatetime(),
        units=CANONICAL_UNITS[variable],
        lat=LAT,
        lon=LON,
        values=vals,
        land_mask=land_mask,
    )


def load_land_mask() -> np.ndarray:
    """Load land mask from grid_static.nc."""
    path = Path("data/static/grid_static.nc")
    if path.exists():
        ds = xr.open_dataset(path)
        mask = ds["land"].values
        ds.close()
        return mask
    return np.ones((len(LAT), len(LON)), dtype=bool)
