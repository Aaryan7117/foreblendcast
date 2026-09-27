"""Pydantic-validated canonical forecast object (B3, TECH_APPROACH §2.1).

Every adapter returns one CanonicalForecast per (model, init_time, variable).
The quality gate runs on this object before it enters the error database.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

import numpy as np
from pydantic import BaseModel, ConfigDict, field_validator


class CanonicalForecast(BaseModel):
    """One model's forecast for one variable across all lead days."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    model: str
    model_version: str
    init_time: datetime
    valid_times: list[datetime]
    lead_days: list[int]
    variable: str
    accumulation_hours: Optional[int] = None
    accumulation_window_utc: Optional[str] = None
    units: str
    lat: np.ndarray
    lon: np.ndarray
    values: np.ndarray  # shape (lead_day, lat, lon)

    @field_validator("values", mode="before")
    @classmethod
    def _coerce_float32(cls, v):
        if isinstance(v, np.ndarray):
            return v.astype(np.float32)
        return v

    @property
    def shape(self) -> tuple[int, ...]:
        return self.values.shape

    def sel_lead(self, day: int) -> np.ndarray:
        """Return the (lat, lon) field for a single lead day."""
        idx = self.lead_days.index(day)
        return self.values[idx]


class CanonicalTruth(BaseModel):
    """Ground truth for one variable on one date."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    source: str
    variable: str
    date: datetime
    units: str
    lat: np.ndarray
    lon: np.ndarray
    values: np.ndarray  # shape (lat, lon)
    land_mask: Optional[np.ndarray] = None
