"""Rolling-origin folds & leakage guard (B7).

Train on years < Y, test on Y. No test-year observation ever reaches any weight fit.
"""
from __future__ import annotations

import pandas as pd
import numpy as np

from experiments.design import FOLDS, init_dates, YEARS


def train_inits(fold: dict) -> list[pd.Timestamp]:
    """Return all init dates in the training years of this fold."""
    return [t for y in fold["train"] for t in init_dates(y)]


def get_test_inits(fold: dict) -> list[pd.Timestamp]:
    """Return all init dates in the test year."""
    return init_dates(fold["test"])


def train_dates(fold: dict) -> list[pd.Timestamp]:
    """All dates that can be used for fitting (including edges for trailing windows)."""
    first_year = min(fold["train"])
    start = pd.Timestamp(f"{first_year - 1}-12-01")
    end = pd.Timestamp(f"{max(fold['train'])}-12-31")
    return list(pd.date_range(start, end, freq="D"))


def test_dates(fold: dict) -> list[pd.Timestamp]:
    """All dates in the test year."""
    y = fold["test"]
    return list(pd.date_range(f"{y}-01-01", f"{y}-12-31", freq="D"))


def check_no_leakage(train_years: tuple[int, ...], test_year: int,
                     weight_dates: list[pd.Timestamp]) -> bool:
    """Verify that no date used in weight fitting falls in the test year.

    Returns True if clean, raises AssertionError if leakage detected.
    """
    test_start = pd.Timestamp(f"{test_year}-01-01")
    test_end = pd.Timestamp(f"{test_year}-12-31")
    leaked = [d for d in weight_dates if test_start <= d <= test_end]
    assert len(leaked) == 0, (
        f"LEAKAGE: {len(leaked)} weight-fitting dates in test year {test_year}: "
        f"{leaked[:5]}"
    )
    return True


def fold_info() -> list[dict]:
    """Return fold specifications as dicts."""
    return list(FOLDS)
