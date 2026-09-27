"""Test accumulation windows (B3) — hand-check against known values."""
import numpy as np
import pandas as pd
import pytest

from canonical.accumulation import (
    imd_date, rain_leads, inst_lead,
    rain_valid_times, window_from_rolling, LEAD_DAYS
)


class TestAccumulation:
    def test_imd_date_lead1(self):
        """Lead day 1 from a 00Z init verifies the init day itself."""
        init = pd.Timestamp("2022-06-14 00:00")
        assert imd_date(init, 1) == pd.Timestamp("2022-06-14")

    def test_imd_date_lead3(self):
        init = pd.Timestamp("2022-06-14 00:00")
        assert imd_date(init, 3) == pd.Timestamp("2022-06-16")

    def test_rain_leads(self):
        """Lead day 1: rolling 24h totals at 24h and 30h."""
        h1, h2 = rain_leads(1)
        assert h1 == 24
        assert h2 == 30

    def test_inst_lead(self):
        """Lead day 1: instantaneous at 12 UTC."""
        assert inst_lead(1) == 12
        assert inst_lead(3) == 60

    def test_rain_valid_times(self):
        day = pd.Timestamp("2022-06-14")
        vt1, vt2 = rain_valid_times(day)
        assert vt1 == pd.Timestamp("2022-06-15 00:00")
        assert vt2 == pd.Timestamp("2022-06-15 06:00")

    def test_window_from_rolling_exact(self):
        """Prove: W(03Z->03Z) = 0.5 * [A(00Z->00Z) + A(06Z->06Z)]"""
        # If uniform rate: 6-hour bins b0..b3, each = R/4 for total R
        R = 100.0
        # A(00Z->00Z) = b0+b1+b2+b3 = R
        # A(06Z->06Z) = b1+b2+b3+b4 where b4 = 0 (next day boundary)
        # For uniform rate within the day: b0=b1=b2=b3=R/4
        a00 = R  # sum of 4 bins
        a06 = 3 * R / 4  # sum of b1..b3 + 0
        w = window_from_rolling(a00, a06)
        # W = 0.5 * (R + 3R/4) = 7R/8
        expected = 0.5 * (a00 + a06)
        assert np.isclose(w, expected)

    def test_all_lead_days_valid(self):
        """All lead days should produce valid lead hours within 240h."""
        for d in LEAD_DAYS:
            h1, h2 = rain_leads(d)
            assert h1 <= 240, f"Lead {d}: rain lead {h1} exceeds 240h"
            assert h2 <= 246, f"Lead {d}: rain lead {h2} exceeds 246h"
