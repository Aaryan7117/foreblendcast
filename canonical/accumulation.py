"""IMD-day windows (D-01): rainfall day D = [D 03 UTC, D+1 03 UTC) = 0830-0830 IST.

WB2 only has 6-hourly steps, so a 03Z-03Z total cannot be read directly. It CAN be built
exactly from two rolling 24 h totals, assuming a uniform rate inside the two 6 h edge bins:

    W(03Z->03Z) = 0.5*b0 + b1 + b2 + b3 + 0.5*b4
                = 0.5 * [A(00Z->00Z) + A(06Z->06Z)]

where b_k are consecutive 6 h bins starting at 00Z on day D. Proven in tests/test_accumulation.py.

Instantaneous fields (T2m, u10, v10) are taken at D 12 UTC (17:30 IST) — inside the window,
afternoon. This is NOT Tmax; the same definition is applied to forecasts and truth.
"""
from __future__ import annotations

import pandas as pd

LEAD_DAYS = (1, 3, 5, 7, 9)  # day 10 would need lead 246 h > 240 h available
INST_HOUR_UTC = 12


def imd_date(init: pd.Timestamp, lead_day: int) -> pd.Timestamp:
    """IMD date verified by a 00Z forecast at lead day d (d=1 -> the init day itself)."""
    return (init.normalize() + pd.Timedelta(days=lead_day - 1))


def rain_leads(lead_day: int) -> tuple[int, int]:
    """Lead hours of the two rolling-24h totals whose mean is the IMD-day window."""
    return 24 * lead_day, 24 * lead_day + 6


def inst_lead(lead_day: int) -> int:
    return 24 * (lead_day - 1) + INST_HOUR_UTC


def rain_valid_times(day: pd.Timestamp) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Valid times of the two rolling-24h analysis totals for IMD day D."""
    nxt = day.normalize() + pd.Timedelta(days=1)
    return nxt, nxt + pd.Timedelta(hours=6)


def inst_valid_time(day: pd.Timestamp) -> pd.Timestamp:
    return day.normalize() + pd.Timedelta(hours=INST_HOUR_UTC)


def window_from_rolling(a00, a06):
    """IMD-day total from the 00Z-ending and 06Z-ending rolling 24 h totals."""
    return 0.5 * (a00 + a06)
