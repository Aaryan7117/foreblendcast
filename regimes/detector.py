"""Forecast-based weather regime (wet / normal / dry spell) per homogeneous region.

The regime of a forecast is decided from the forecasts themselves, never from the
verifying observation: the region-mean of the equal-weight multi-model rainfall forecast
is compared with the terciles of the same quantity over the training years, per season.
During JJAS the upper and lower terciles correspond to active and break monsoon spells.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from experiments.design import SEASONS

REGIMES = ("break", "normal", "active")  # lower, middle, upper tercile
MIN_SAMPLES = 9  # fewer training days than this in a season -> everything is "normal"


@dataclass
class Geography:
    land: np.ndarray          # (lat, lon) bool
    aw: np.ndarray            # (lat, lon) cos(lat)
    region_idx: np.ndarray    # (lat, lon) int, -1 outside the regions
    region_names: list[str]
    district_idx: np.ndarray  # (lat, lon) int, -1 where no district
    district_ids: list[str]
    district_region: np.ndarray  # (district,) int

    @property
    def n_regions(self) -> int:
        return len(self.region_names)

    def node_cells(self) -> np.ndarray:
        """Column of the regime table each cell reads: its region, or national (last)."""
        return np.where(self.region_idx >= 0, self.region_idx, self.n_regions)


def load_geography() -> Geography:
    import json
    from pathlib import Path
    import xarray as xr
    from canonical.grid import area_weights

    with xr.open_dataset("data/static/grid_static.nc") as ds:
        land = ds["land"].values.astype(bool)
        cell_district = ds["cell_district"].values.astype(int)
        ids = ds["district"].values.tolist()
    meta = {d["id"]: d for d in json.loads(Path("data/static/districts_index.json").read_text())}
    names = sorted({d["region"] for d in meta.values() if d.get("region")})
    district_region = np.array([names.index(meta[i]["region"]) if meta.get(i, {}).get("region") in names
                                else -1 for i in ids])
    district_idx = np.where(land, cell_district, -1)
    region_idx = np.where(district_idx >= 0, district_region[np.maximum(district_idx, 0)], -1)
    return Geography(land, area_weights(), region_idx, names, district_idx, ids, district_region)


def region_means(field_stack: np.ndarray, geo: Geography) -> np.ndarray:
    """(n, lat, lon) -> (n, R + 1) area-weighted means; the last column is all-India land."""
    out = np.full((field_stack.shape[0], geo.n_regions + 1), np.nan)
    masks = [geo.region_idx == r for r in range(geo.n_regions)] + [geo.land]
    for c, mask in enumerate(masks):
        if mask.any():
            w = geo.aw[mask]
            vals = field_stack[:, mask]
            ok = np.isfinite(vals)
            num = np.where(ok, vals, 0.0) @ w
            den = ok @ w
            out[:, c] = np.where(den > 0, num / np.where(den > 0, den, 1.0), np.nan)
    return out


def multi_model_mean(fc: dict[str, np.ndarray]) -> np.ndarray:
    """Equal-weight mean over the models available on each day."""
    with np.errstate(invalid="ignore"):
        return np.nanmean(np.stack(list(fc.values()), axis=0), axis=0)


def season_index(valid_dates) -> np.ndarray:
    from experiments.design import SEASON_OF_MONTH
    return np.array([SEASONS.index(SEASON_OF_MONTH[t.month]) for t in valid_dates])


def fit_thresholds(series: np.ndarray, seasons: np.ndarray) -> np.ndarray:
    """Tercile thresholds (season, node, 2) from training forecasts."""
    thr = np.full((len(SEASONS), series.shape[1], 2), np.nan)
    for s in range(len(SEASONS)):
        rows = series[seasons == s]
        for c in range(series.shape[1]):
            v = rows[:, c][np.isfinite(rows[:, c])]
            if len(v) >= MIN_SAMPLES:
                thr[s, c] = np.percentile(v, [100 / 3, 200 / 3])
    return thr


def classify(series: np.ndarray, seasons: np.ndarray, thresholds: np.ndarray) -> np.ndarray:
    """(n, node) regime index into REGIMES. Missing thresholds or values -> normal."""
    lo, hi = thresholds[seasons, :, 0], thresholds[seasons, :, 1]
    out = np.ones(series.shape, dtype=np.int8)
    with np.errstate(invalid="ignore"):
        out[series < lo] = 0
        out[series > hi] = 2
    return out


def regime_map(regimes_day: np.ndarray, geo: Geography) -> np.ndarray:
    """(lat, lon) regime index of each cell for one day."""
    return regimes_day[geo.node_cells()]
