"""WeatherBench2 source registry and India-box chunk reader.

All WB2 0.25° stores are chunked as one global field per (init, lead) — so every read
pulls a whole globe and we slice the India box locally. Reads go through zarr
orthogonal selection so all needed chunks are fetched concurrently.

Findings from the P-3 inventory (results/inventory.json) baked in here:
- WB2 has no GFS; the pool is IFS HRES (NWP), IFS ENS mean (ensemble), GraphCast and
  Pangu (AI). Pangu has no precipitation.
- GraphCast v2 is split into per-year stores (2018, 2020, 2022) with 6-hourly inits.
- Latitude order differs per store; lon is 0..359.75 everywhere.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

import numpy as np
import pandas as pd
import zarr

from canonical.grid import LAT, LON

WB2 = "gs://weatherbench2/datasets"
zarr.config.set({"async.concurrency": 64})


@dataclass(frozen=True)
class Store:
    path: str
    lat_ascending: bool
    time_epoch: str  # value of the "hours since ..." units attribute


@dataclass(frozen=True)
class ModelSource:
    name: str
    kind: str                      # "nwp" | "ensemble" | "ai" | "reanalysis"
    stores: dict[int, Store]       # year -> store holding that year's inits
    variables: tuple[str, ...]
    label: str
    notes: str = ""
    max_lead_h: int = 240


_HRES = Store("hres/2016-2022-0012-1440x721.zarr", True, "2016-01-01")
_ENS = Store("ifs_ens/2018-2022-1440x721_mean.zarr", True, "2018-01-01")
_PANGU = Store("pangu/2018-2022_0012_0p25.zarr", False, "2018-01-01")
_ERA5 = Store("era5/1959-2023_01_10-wb13-6h-1440x721_with_derived_variables.zarr", False, "1959-01-01")

ALL_VARS = ("precip", "t2m", "u10", "v10")
INST_VARS = ("t2m", "u10", "v10")

SOURCES: dict[str, ModelSource] = {
    "hres": ModelSource("hres", "nwp", {y: _HRES for y in range(2016, 2023)}, ALL_VARS,
                        "ECMWF IFS HRES"),
    "ens": ModelSource("ens", "ensemble", {y: _ENS for y in range(2018, 2023)}, ALL_VARS,
                       "ECMWF IFS ENS mean", max_lead_h=360),
    "graphcast": ModelSource("graphcast", "ai", {
        2018: Store("graphcast_v2/2018-1440x721.zarr", True, "2017-12-01"),
        2020: Store("graphcast_v2/2020-1440x721.zarr", True, "2019-12-01"),
        2022: Store("graphcast_v2/2022-1440x721.zarr", True, "2021-12-01"),
    }, ALL_VARS, "Google DeepMind GraphCast"),
    "pangu": ModelSource("pangu", "ai", {y: _PANGU for y in range(2018, 2023)}, INST_VARS,
                         "Huawei Pangu-Weather", notes="no precipitation output"),
}
TRUTH = ModelSource("era5", "reanalysis", {y: _ERA5 for y in range(1959, 2024)}, ALL_VARS, "ERA5")

WB2_NAME = {"precip": "total_precipitation_24hr", "t2m": "2m_temperature",
            "u10": "10m_u_component_of_wind", "v10": "10m_v_component_of_wind"}


def _box_index(lat_ascending: bool) -> tuple[slice, slice, bool]:
    """Index slices of the canonical box inside a global 0.25° grid."""
    lon0 = int(round(LON[0] / 0.25))
    lon_sl = slice(lon0, lon0 + len(LON))
    if lat_ascending:
        i0 = int(round((LAT[0] + 90) / 0.25))
        return slice(i0, i0 + len(LAT)), lon_sl, False
    i0 = int(round((90 - LAT[-1]) / 0.25))
    return slice(i0, i0 + len(LAT)), lon_sl, True  # flip afterwards


@lru_cache(maxsize=None)
def _group(path: str) -> zarr.Group:
    return zarr.open_group(f"{WB2}/{path}", mode="r", storage_options={"token": "anon"})


@lru_cache(maxsize=None)
def _time_index(path: str, epoch: str) -> dict[pd.Timestamp, int]:
    hours = _group(path)["time"][:]
    times = pd.Timestamp(epoch) + pd.to_timedelta(hours, unit="h")
    return {t: i for i, t in enumerate(times)}


@lru_cache(maxsize=None)
def _lead_index(path: str) -> dict[int, int]:
    g = _group(path)
    if "prediction_timedelta" not in g:
        return {}
    return {int(h): i for i, h in enumerate(g["prediction_timedelta"][:])}


def store_for(src: ModelSource, t: pd.Timestamp) -> Store:
    return src.stores[t.year]


def read_forecast(src: ModelSource, var: str, inits: list[pd.Timestamp],
                  lead_hours: list[int]) -> np.ndarray:
    """Return array (init, lead, lat, lon) in native WB2 units, NaN where missing."""
    out = np.full((len(inits), len(lead_hours), len(LAT), len(LON)), np.nan, np.float32)
    by_store: dict[Store, list[int]] = {}
    for k, t in enumerate(inits):
        by_store.setdefault(store_for(src, t), []).append(k)
    for store, ks in by_store.items():
        tix, lix = _time_index(store.path, store.time_epoch), _lead_index(store.path)
        have = [k for k in ks if inits[k] in tix]
        leads_ok = [j for j, h in enumerate(lead_hours) if h in lix]
        if not have or not leads_ok:
            continue
        lat_sl, lon_sl, flip = _box_index(store.lat_ascending)
        arr = _group(store.path)[WB2_NAME[var]]
        block = arr.get_orthogonal_selection(
            ([tix[inits[k]] for k in have], [lix[lead_hours[j]] for j in leads_ok], lat_sl, lon_sl))
        if flip:
            block = block[:, :, ::-1, :]
        out[np.ix_(have, leads_ok)] = block
    return out


def read_analysis(var: str, valid: list[pd.Timestamp]) -> np.ndarray:
    """ERA5 at valid times -> (time, lat, lon)."""
    store = _ERA5
    tix = _time_index(store.path, store.time_epoch)
    lat_sl, lon_sl, flip = _box_index(store.lat_ascending)
    idx = [tix[t] for t in valid]
    block = _group(store.path)[WB2_NAME[var]].get_orthogonal_selection((idx, lat_sl, lon_sl))
    return block[:, ::-1, :] if flip else block
