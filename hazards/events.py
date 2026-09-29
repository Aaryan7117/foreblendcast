"""Hazard event definitions for rainfall, heat and wind (B11).

Every event is a margin function: margin(field, climatology) >= 0 means the event occurs.
The same function is applied to forecasts and to the verifying truth, so an event
probability can be verified like any other binary forecast.

Temperature is 2 m temperature at 12 UTC (17:30 IST), the afternoon value the pipeline
ingests. It is a proxy for the daily maximum, not Tmax itself, and sits slightly below it.
Wind is the 10 m wind speed on the 0.25 degree grid, a sustained-wind value without gusts.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np


@dataclass(frozen=True)
class Event:
    key: str
    label: str
    margin: Callable[[np.ndarray, np.ndarray | None], np.ndarray]
    definition: str


def _above(threshold: float):
    return lambda field, clim=None: field - threshold


def heatwave_margin(t2m: np.ndarray, clim: np.ndarray | None) -> np.ndarray:
    """IMD plains criterion: T >= 40 degC with departure >= 4.5 degC, or T >= 45 degC."""
    severe = t2m - 45.0
    if clim is None:
        return severe
    return np.maximum(np.minimum(t2m - 40.0, (t2m - clim) - 4.5), severe)


EVENTS: dict[str, list[Event]] = {
    "precip": [
        Event("p_gt_64p5", "Heavy rain", _above(64.5), "24 h rainfall >= 64.5 mm"),
        Event("p_gt_115p6", "Very heavy rain", _above(115.6), "24 h rainfall >= 115.6 mm"),
        Event("p_gt_204p5", "Extremely heavy rain", _above(204.5), "24 h rainfall >= 204.5 mm"),
    ],
    "t2m": [
        Event("p_hot_40", "Hot day", _above(40.0), "2 m temperature at 12 UTC >= 40 degC"),
        Event("p_heatwave", "Heatwave", heatwave_margin,
              "12 UTC temperature >= 40 degC and >= 4.5 degC above the training-period "
              "monthly normal, or >= 45 degC"),
    ],
    "wind": [
        Event("p_wind_8", "Fresh wind", _above(8.0), "10 m wind speed >= 8.0 m/s (Beaufort 5)"),
        Event("p_wind_10p8", "Strong wind", _above(10.8), "10 m wind speed >= 10.8 m/s (Beaufort 6)"),
    ],
}

# Headline event of each variable, used for the ladder's probabilistic columns.
HEADLINE_EVENT = {"precip": "p_gt_64p5", "t2m": "p_hot_40", "wind": "p_wind_8"}


def monthly_climatology(truth: np.ndarray, dates) -> np.ndarray:
    """(12, lat, lon) mean of the training truth per calendar month."""
    months = np.array([d.month for d in dates])
    out = np.full((12,) + truth.shape[1:], np.nan, np.float32)
    overall = np.nanmean(truth, axis=0)
    for m in range(1, 13):
        sel = months == m
        out[m - 1] = np.nanmean(truth[sel], axis=0) if sel.any() else overall
    return out


def clim_for(clim12: np.ndarray, dates) -> np.ndarray:
    """(n, lat, lon) climatology matching each date."""
    return clim12[np.array([d.month for d in dates]) - 1]
