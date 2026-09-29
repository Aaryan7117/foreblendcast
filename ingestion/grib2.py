"""GRIB2 ingestion via cfgrib: the path from an operational NWP file to the blend (B4).

GRIB2 is a file format, not a model, so this module does not add a model called "grib2".
It gives every registered model a second source:

    data/raw/grib2/<model>/<model>_<YYYYMMDDHH>_f<HHH>.grib2

`register_grib_sources()` wraps each registered adapter so that a cycle is read from
GRIB2 when the files are there and from the WeatherBench2 NetCDF archive otherwise. A
directory for a model that has no adapter yet (for example `gfs`) is registered as a new
model. It is ingested and quality-gated, but it enters the blend only after a skill
history has been built for it, because its weight would otherwise be arbitrary.

Conventions handled here:
  * rainfall `tp` accumulated since the start of the forecast (ECMWF, and GFS files that
    were requested that way). The 03-03 UTC IMD-day total is built from the 24 h totals
    ending at leads 24d and 24d+6 h, exactly as for the archive (canonical/accumulation.py).
  * units from the GRIB metadata: m or mm of water, K or degC.
  * any regular lat-lon grid, either latitude order, longitudes in 0..360 or -180..180.

    python -m ingestion.grib2 path/to/file.grib2          # print what a file contains
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from canonical import accumulation as acc
from canonical.forecast import CanonicalForecast
from canonical.grid import LAT, LON
from ingestion.base import Adapter
from ingestion.registry import all_adapters, register

try:
    import cfgrib  # noqa: F401
    import xarray as xr
    HAS_CFGRIB = True
except ImportError:
    HAS_CFGRIB = False

GRIB_ROOT = Path("data/raw/grib2")
SHORT_NAME = {"precip": "tp", "t2m": "2t", "u10": "10u", "v10": "10v"}
ALL_VARIABLES = ("precip", "t2m", "u10", "v10")


def grib_path(grib_dir: Path, model: str, init: pd.Timestamp, lead_h: int) -> Path:
    return grib_dir / f"{model}_{init:%Y%m%d%H}_f{lead_h:03d}.grib2"


def _to_canonical_units(values: np.ndarray, variable: str, units: str) -> np.ndarray:
    units = (units or "").strip()
    if variable == "precip":
        if units == "m":
            return values * 1000.0
        if units in ("mm", "kg m**-2", "kg m-2"):
            return values
        raise ValueError(f"unknown rainfall units {units!r}")
    if variable == "t2m":
        if units == "K":
            return values - 273.15
        if units in ("C", "degC", "Celsius"):
            return values
        raise ValueError(f"unknown temperature units {units!r}")
    return values


def read_field(path: Path, variable: str) -> np.ndarray:
    """One variable of one GRIB2 file on the canonical grid, in canonical units."""
    ds = xr.open_dataset(path, engine="cfgrib",
                         backend_kwargs={"filter_by_keys": {"shortName": SHORT_NAME[variable]},
                                         "indexpath": ""})
    try:
        if not ds.data_vars:
            raise KeyError(f"{SHORT_NAME[variable]} not in {path.name}")
        da = ds[list(ds.data_vars)[0]]
        lat = "latitude" if "latitude" in da.dims else "lat"
        lon = "longitude" if "longitude" in da.dims else "lon"
        da = da.sortby(lat)
        if float(da[lon].min()) < 0:                       # -180..180 -> 0..360
            da = da.assign_coords({lon: da[lon] % 360}).sortby(lon)
        covers = (float(da[lat].min()) <= LAT[0] and float(da[lat].max()) >= LAT[-1]
                  and float(da[lon].min()) <= LON[0] and float(da[lon].max()) >= LON[-1])
        if not covers:
            raise ValueError(f"{path.name} does not cover the India box")
        values = da.interp({lat: LAT, lon: LON}, method="linear").values.astype(np.float32)
        return _to_canonical_units(values, variable, da.attrs.get("units", "")).astype(np.float32)
    finally:
        ds.close()


class Grib2Adapter(Adapter):
    """Reads one model from a directory of GRIB2 files."""

    def __init__(self, name: str, label: str | None = None, kind: str = "nwp",
                 variables: tuple[str, ...] = ALL_VARIABLES, grib_dir: str | Path | None = None):
        self.name = name
        self.label = label or f"{name} (GRIB2)"
        self.kind = kind
        self.variables = variables
        self.grib_dir = Path(grib_dir) if grib_dir else GRIB_ROOT / name

    def _total_since_init(self, init: pd.Timestamp, lead_h: int) -> np.ndarray | None:
        if lead_h == 0:
            return np.zeros((len(LAT), len(LON)), np.float32)
        path = grib_path(self.grib_dir, self.name, init, lead_h)
        return read_field(path, "precip") if path.exists() else None

    def _rain_day(self, init: pd.Timestamp, lead_day: int) -> np.ndarray | None:
        rolling = []
        for end in acc.rain_leads(lead_day):
            upto, before = self._total_since_init(init, end), self._total_since_init(init, end - 24)
            if upto is None or before is None:
                return None
            rolling.append(upto - before)
        return acc.window_from_rolling(*rolling).astype(np.float32)

    def has_cycle(self, init: pd.Timestamp) -> bool:
        return any(self.grib_dir.glob(f"{self.name}_{init:%Y%m%d%H}_f*.grib2"))

    def load(self, init_time: pd.Timestamp, variable: str,
             lead_days: list[int] | None = None) -> Optional[CanonicalForecast]:
        if not HAS_CFGRIB or variable not in self.variables:
            return None
        fields, leads = [], []
        for ld in lead_days or list(acc.LEAD_DAYS):
            if variable == "precip":
                field = self._rain_day(init_time, ld)
            else:
                path = grib_path(self.grib_dir, self.name, init_time, acc.inst_lead(ld))
                field = read_field(path, variable) if path.exists() else None
            if field is not None:
                fields.append(field)
                leads.append(ld)
        if not fields:
            return None
        return self._build_forecast(init_time, variable, leads, np.stack(fields))


class GribFirst(Adapter):
    """A model with two sources: GRIB2 files when present, else the NetCDF archive."""

    def __init__(self, archive: Adapter, grib: Grib2Adapter):
        self.archive, self.grib = archive, grib
        self.name, self.label, self.kind = archive.name, archive.label, archive.kind
        self.variables = archive.variables
        self.last_source: dict[tuple, str] = {}

    def load(self, init_time: pd.Timestamp, variable: str,
             lead_days: list[int] | None = None) -> Optional[CanonicalForecast]:
        fc = self.grib.load(init_time, variable, lead_days) if self.grib.has_cycle(init_time) else None
        self.last_source[(init_time, variable)] = "grib2" if fc is not None else "archive"
        return fc if fc is not None else self.archive.load(init_time, variable, lead_days)


def register_grib_sources(root: str | Path | None = None) -> list[str]:
    """Give every registered model a GRIB2 source and register GRIB2-only models.

    Returns the names of the models that exist only as GRIB2. Safe to call repeatedly.
    """
    root = Path(root) if root else GRIB_ROOT
    for name, adapter in all_adapters().items():
        if isinstance(adapter, (GribFirst, Grib2Adapter)):
            continue
        register(GribFirst(adapter, Grib2Adapter(name, adapter.label, adapter.kind,
                                                 adapter.variables, root / name)))
    new = []
    if root.is_dir():
        for d in sorted(p for p in root.iterdir() if p.is_dir()):
            if d.name not in all_adapters():
                register(Grib2Adapter(d.name, grib_dir=d))
            if isinstance(all_adapters()[d.name], Grib2Adapter):
                new.append(d.name)
    return new


def describe(grib_path_: str) -> None:
    """CLI entry point: read one GRIB2 file and print a summary."""
    for ds in cfgrib.open_datasets(grib_path_, backend_kwargs={"indexpath": ""}):
        for v in ds.data_vars:
            da = ds[v]
            print(f"{v}: shortName={da.attrs.get('GRIB_shortName')} units={da.attrs.get('units')} "
                  f"shape={da.shape} min={float(da.min()):.3f} max={float(da.max()):.3f}")
        ds.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Print the contents of a GRIB2 file")
    ap.add_argument("grib_file", help="Path to a GRIB2 file")
    describe(ap.parse_args().grib_file)
