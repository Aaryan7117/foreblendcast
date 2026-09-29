"""Year-stack loaders for the experiment (forecasts and truth) with an on-disk cache.

Reading ~700 compressed monthly NetCDF files takes minutes, so every
(source, variable, year) stack is materialised once under data/cache/ as .npy and
memory-mapped afterwards.

Variables: the four ingested ones (precip, t2m, u10, v10) plus the derived
"wind" = sqrt(u10^2 + v10^2), computed per source before any blending.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from canonical import accumulation as acc
from canonical.grid import LAT, LON
from canonical.quality_gate import screen_stack
from experiments.design import YEARS, init_dates

RAW = Path("data/raw")
CACHE = Path("data/cache")
LEAD_DAYS = tuple(acc.LEAD_DAYS)
DERIVED = {"wind": ("u10", "v10")}
UNITS = {"precip": "mm", "t2m": "degC", "wind": "m s-1", "u10": "m s-1", "v10": "m s-1"}


def _raw_forecast_year(model: str, variable: str, year: int) -> np.ndarray | None:
    """(init, lead, lat, lon) for every design init of the year, NaN where missing."""
    inits = init_dates(year)
    out = np.full((len(inits), len(LEAD_DAYS), len(LAT), len(LON)), np.nan, np.float32)
    pos = {t: i for i, t in enumerate(inits)}
    found = False
    for month in sorted({t.strftime("%Y-%m") for t in inits}):
        path = RAW / model / variable / f"{month}.nc"
        if not path.exists():
            continue
        with xr.open_dataset(path) as ds:
            leads = [int(d) for d in ds.lead_day.values]
            vals = ds[variable].values
            for k, t in enumerate(pd.DatetimeIndex(ds.init.values)):
                if t not in pos:
                    continue
                for j, ld in enumerate(leads):
                    if ld in LEAD_DAYS:
                        out[pos[t], LEAD_DAYS.index(ld)] = vals[k, j]
                found = True
    return out if found else None


def forecast_year(model: str, variable: str, year: int) -> np.ndarray | None:
    """Memory-mapped (init, lead, lat, lon) stack, or None if the source lacks the variable."""
    if variable in DERIVED:
        parts = [forecast_year(model, v, year) for v in DERIVED[variable]]
        if any(p is None for p in parts):
            return None
        path = CACHE / f"{model}_{variable}_{year}.npy"
        if not path.exists():
            CACHE.mkdir(parents=True, exist_ok=True)
            np.save(path, np.sqrt(np.square(parts[0]) + np.square(parts[1])).astype(np.float32))
        return np.load(path, mmap_mode="r")
    path = CACHE / f"{model}_{variable}_{year}.npy"
    if not path.exists():
        arr = _raw_forecast_year(model, variable, year)
        if arr is None:
            return None
        CACHE.mkdir(parents=True, exist_ok=True)
        np.save(path, arr)
    return np.load(path, mmap_mode="r")


@lru_cache(maxsize=None)
def truth_all(variable: str) -> tuple[pd.DatetimeIndex, np.ndarray]:
    """Every truth day on disk: (dates, (date, lat, lon) array)."""
    if variable in DERIVED:
        (d, u), (_, v) = (truth_all(x) for x in DERIVED[variable])
        return d, np.sqrt(np.square(u) + np.square(v)).astype(np.float32)
    path, dpath = CACHE / f"era5_{variable}.npy", CACHE / f"era5_{variable}_dates.npy"
    if not (path.exists() and dpath.exists()):
        dates, fields = [], []
        for f in sorted((RAW / "era5" / variable).glob("*.nc")):
            with xr.open_dataset(f) as ds:
                dates.extend(pd.DatetimeIndex(ds.date.values))
                fields.append(ds[variable].values.astype(np.float32))
        CACHE.mkdir(parents=True, exist_ok=True)
        np.save(path, np.concatenate(fields, axis=0))
        np.save(dpath, np.array(dates, dtype="datetime64[ns]"))
    return pd.DatetimeIndex(np.load(dpath)), np.load(path, mmap_mode="r")


def truth_for(variable: str, dates: list[pd.Timestamp]) -> np.ndarray:
    """(n, lat, lon) truth for the given days, NaN fields where the day is not on disk."""
    all_dates, arr = truth_all(variable)
    idx = all_dates.get_indexer(pd.DatetimeIndex(dates))
    out = np.full((len(dates), len(LAT), len(LON)), np.nan, np.float32)
    ok = idx >= 0
    out[ok] = arr[idx[ok]]
    if variable == "precip":
        np.maximum(out, 0.0, out=out)  # ERA5 carries tiny negative numerical noise
    return out


def models_for(variable: str) -> list[str]:
    """Registered adapters that provide the variable (derived ones need every component)."""
    from ingestion import registry
    registry.load_all()
    need = DERIVED.get(variable, (variable,))
    return [name for name, a in registry.all_adapters().items()
            if all(v in a.variables for v in need) and (RAW / name).exists()]


QC_LOG: dict[tuple, dict] = {}  # (model, variable, years, lead) -> what the gate did


@lru_cache(maxsize=1)
def _land() -> np.ndarray:
    with xr.open_dataset("data/static/grid_static.nc") as ds:
        return ds["land"].values.astype(bool)


def sample_block(models: list[str], variable: str, years: tuple[int, ...], lead_day: int) -> dict:
    """All samples of the given years at one lead, after the quality gate.

    Returns inits, valid dates, fc {model: (n, lat, lon)} and obs (n, lat, lon).
    Samples without truth are dropped. A model that is missing or rejected by the
    quality gate on a day is NaN for that day, which removes it from that day's blend.
    """
    j = LEAD_DAYS.index(lead_day)
    inits = [t for y in years for t in init_dates(y)]
    valid = [acc.imd_date(t, lead_day) for t in inits]
    obs = truth_for(variable, valid)
    fc = {}
    for m in models:
        stacks = [forecast_year(m, variable, y) for y in years]
        if any(s is None for s in stacks):
            continue
        raw = np.concatenate([np.asarray(s[:, j]) for s in stacks], axis=0)
        absent = int((~np.isfinite(raw).any(axis=(1, 2))).sum())
        fc[m], rejected, repaired = screen_stack(raw, variable, _land())
        QC_LOG[(m, variable, tuple(years), lead_day)] = {
            "fields": int(raw.shape[0]), "missing": absent,
            "rejected": len(rejected) - absent, "repaired_cells": repaired,
            "reasons": sorted({r.split(":")[0] for r in rejected.values() if r != "all_nan"}),
        }
    keep = np.isfinite(obs).any(axis=(1, 2))
    return {
        "inits": pd.DatetimeIndex(inits)[keep],
        "valid": pd.DatetimeIndex(valid)[keep],
        "fc": {m: v[keep] for m, v in fc.items()},
        "obs": obs[keep],
    }


def warm_cache(variables: tuple[str, ...] = ("precip", "t2m", "wind")) -> None:
    for v in variables:
        truth_all(v)
        for m in models_for(v):
            for y in YEARS:
                forecast_year(m, v, y)
