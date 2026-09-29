"""Rebuild the showcase products (including rasters/truth.png) from the frozen artifacts.

Kept for compatibility: the work is done by `python -m experiments.run --showcase_only`.
"""
import pandas as pd

from experiments.run import LEAD_DAYS, run_showcase
from regimes.detector import load_geography


def main():
    run_showcase(pd.Timestamp("2022-06-14"), LEAD_DAYS, load_geography())


if __name__ == "__main__":
    main()
