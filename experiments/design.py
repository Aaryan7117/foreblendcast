"""Single source of truth for the experimental design.

Years: 2018, 2020, 2022 — the three years every pool member (incl. GraphCast v2) covers,
and WB2 ends in 2022 (decision rule 6.1). Inits: 00 UTC every second day. Folds are
rolling-origin: each test year is weighted only from strictly earlier years (D-03).
"""
from __future__ import annotations

import pandas as pd

YEARS = (2018, 2020, 2022)
INIT_STEP_DAYS = 2
FOLDS = ({"train": (2018,), "test": 2020}, {"train": (2018, 2020), "test": 2022})
TEST_YEARS = tuple(f["test"] for f in FOLDS)

# IMD seasons
SEASON_OF_MONTH = {1: "JF", 2: "JF", 3: "MAM", 4: "MAM", 5: "MAM", 6: "JJAS", 7: "JJAS",
                   8: "JJAS", 9: "JJAS", 10: "OND", 11: "OND", 12: "OND"}
SEASONS = ("JF", "MAM", "JJAS", "OND")

# Showcase cycle for the dashboard: before the Assam–Meghalaya extreme rain of 15–17 Jun 2022,
# inside the 2022 test fold (out-of-sample for every fitted weight).
SHOWCASE_CYCLE = pd.Timestamp("2022-06-14 00:00")


def init_dates(year: int) -> list[pd.Timestamp]:
    days = pd.date_range(f"{year}-01-01", f"{year}-12-31", freq=f"{INIT_STEP_DAYS}D")
    return list(days)


def all_inits() -> list[pd.Timestamp]:
    return [t for y in YEARS for t in init_dates(y)]


def truth_days(year: int) -> list[pd.Timestamp]:
    """Every IMD day needed: persistence (init-1) through the longest lead after year end."""
    return list(pd.date_range(f"{year - 1}-12-01", f"{year + 1}-01-31", freq="D"))


def season_of(t: pd.Timestamp) -> str:
    return SEASON_OF_MONTH[t.month]
