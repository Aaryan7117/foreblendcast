"""Test suite for the quality gate (B3)."""
import numpy as np
import pytest

from canonical.forecast import CanonicalForecast, CanonicalTruth
from canonical.grid import LAT, LON
from canonical.quality_gate import check_forecast, check_truth


def _make_forecast(variable="precip", values=None, **overrides):
    if values is None:
        shape = (5, len(LAT), len(LON))
        values = np.random.rand(*shape).astype(np.float32) * 10
    defaults = dict(
        model="test", model_version="test v1",
        init_time="2022-06-14T00:00:00",
        valid_times=["2022-06-14", "2022-06-15", "2022-06-16", "2022-06-17", "2022-06-18"],
        lead_days=[1, 3, 5, 7, 9],
        variable=variable,
        units="mm", lat=LAT, lon=LON, values=values,
    )
    defaults.update(overrides)
    return CanonicalForecast(**defaults)


class TestQualityGate:
    def test_clean_forecast_passes(self):
        fc = _make_forecast()
        result = check_forecast(fc)
        assert result.passed

    def test_corrupt_range_rejected(self):
        vals = np.full((5, len(LAT), len(LON)), 999.0, dtype=np.float32)
        fc = _make_forecast(values=vals)
        result = check_forecast(fc)
        assert not result.passed
        assert "range_violation" in result.reason

    def test_all_nan_rejected(self):
        vals = np.full((5, len(LAT), len(LON)), np.nan, dtype=np.float32)
        fc = _make_forecast(values=vals)
        result = check_forecast(fc)
        assert not result.passed

    def test_wrong_grid_rejected(self):
        fc = _make_forecast(
            lat=np.arange(10), lon=np.arange(10),
            values=np.random.rand(5, 10, 10).astype(np.float32)
        )
        result = check_forecast(fc)
        assert not result.passed
        assert "grid_size_mismatch" in result.reason

    def test_truth_passes(self):
        t = CanonicalTruth(
            source="ERA5", variable="precip",
            date="2022-06-14", units="mm",
            lat=LAT, lon=LON,
            values=np.random.rand(len(LAT), len(LON)).astype(np.float32) * 10,
        )
        result = check_truth(t)
        assert result.passed
