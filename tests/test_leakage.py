"""Test leakage guard (B7) — no test-year observation reaches any weight fit."""
import pandas as pd
import pytest

from experiments.design import FOLDS
from experiments.folds import train_inits, get_test_inits, check_no_leakage


class TestLeakage:
    def test_no_overlap_between_train_and_test(self):
        """Train and test init dates must not overlap."""
        for fold in FOLDS:
            train = set(train_inits(fold))
            test = set(get_test_inits(fold))
            overlap = train & test
            assert len(overlap) == 0, f"Overlap in fold test={fold['test']}: {overlap}"

    def test_check_no_leakage_clean(self):
        """Using only training dates should pass the leakage check."""
        for fold in FOLDS:
            train_dates = [t for t in train_inits(fold)]
            assert check_no_leakage(fold["train"], fold["test"], train_dates)

    def test_check_no_leakage_detects_leak(self):
        """Using a test-year date should raise AssertionError."""
        fold = FOLDS[0]  # train=(2018,), test=2020
        leaked_dates = [pd.Timestamp("2020-07-15")]
        with pytest.raises(AssertionError, match="LEAKAGE"):
            check_no_leakage(fold["train"], fold["test"], leaked_dates)

    def test_folds_are_rolling_origin(self):
        """Each test year should be after all training years."""
        for fold in FOLDS:
            assert all(y < fold["test"] for y in fold["train"])
