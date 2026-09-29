"""The test-year truth must not influence anything that is fitted or forecast.

experiments.evaluate is run twice on synthetic data that differs only in the test-year
observations. Everything frozen before verification (weights, regime thresholds,
calibrators, quantile tables, decision thresholds) must be identical, while the
verification scores must differ.
"""
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest

HAS_STATIC = Path("data/static/grid_static.nc").exists() and Path("data/static/districts_index.json").exists()
pytestmark = pytest.mark.skipif(not HAS_STATIC, reason="data/static not built")

FOLD = {"train": (2018,), "test": 2020}
MODELS = ["a", "b", "c"]


def _dates(year, n):
    return pd.DatetimeIndex(pd.date_range(f"{year}-01-05", periods=n, freq="9D"))


@pytest.fixture()
def harness(monkeypatch, tmp_path):
    from experiments import data, evaluate as ev
    from regimes import detector as rg

    geo = rg.load_geography()
    shape = geo.land.shape
    rng = np.random.default_rng(7)
    n = 40
    state = {"test_obs_shift": 0.0}

    def block(year, seed):
        r = np.random.default_rng(seed)
        obs = r.gamma(2.0, 4.0, (n,) + shape).astype(np.float32)
        fc = {m: (obs + (i + 1) * r.standard_normal((n,) + shape)).astype(np.float32)
              for i, m in enumerate(MODELS)}
        return {"inits": _dates(year, n), "valid": _dates(year, n), "fc": fc, "obs": obs}

    blocks = {2018: block(2018, 1), 2020: block(2020, 2)}

    def sample_block(models, variable, years, lead_day):
        b = blocks[years[0]]
        obs = b["obs"] + (state["test_obs_shift"] if years[0] == FOLD["test"] else 0.0)
        return {**b, "obs": obs.astype(np.float32), "fc": dict(b["fc"])}

    def truth_for(variable, dates):
        # climatology and persistence inputs: independent of the test-year shift
        r = np.random.default_rng(len(dates))
        return r.gamma(2.0, 4.0, (len(dates),) + shape).astype(np.float32)

    def regime_inputs(years, lead_day, geo_, inits):
        r = np.random.default_rng(years[0])
        return r.gamma(2.0, 2.0, (len(inits), geo_.n_regions + 1))

    monkeypatch.setattr(data, "models_for", lambda v: list(MODELS))
    monkeypatch.setattr(data, "sample_block", sample_block)
    monkeypatch.setattr(data, "truth_for", truth_for)
    monkeypatch.setattr(ev, "regime_inputs", regime_inputs)
    monkeypatch.setattr(ev, "TAU_GRID", (0.1,))
    monkeypatch.setattr(ev, "K_GRID", (20.0,))
    monkeypatch.setattr(ev, "FROZEN_DIR", tmp_path)

    def run(shift):
        state["test_obs_shift"] = shift
        res = ev.evaluate("precip", FOLD, 1, geo, save_frozen=True)
        frozen = joblib.load(ev.frozen_path("precip", 1, 2018))
        return res, frozen

    return run


def test_test_year_truth_cannot_change_what_is_frozen(harness):
    res_a, fz_a = harness(0.0)
    res_b, fz_b = harness(25.0)

    assert np.array_equal(fz_a.weights, fz_b.weights)
    assert np.array_equal(fz_a.regime_thresholds, fz_b.regime_thresholds, equal_nan=True)
    assert np.array_equal(fz_a.quantiles.table, fz_b.quantiles.table)
    assert fz_a.tau == fz_b.tau and fz_a.train_rmse == fz_b.train_rmse
    for key in fz_a.calibrators:
        ca, cb = fz_a.calibrators[key], fz_b.calibrators[key]
        assert ca["predictor"] == cb["predictor"]
        assert ca["decision_threshold"] == cb["decision_threshold"]
        x = np.linspace(-50, 300, 50)
        assert np.array_equal(ca["calibrator"].predict(x), cb["calibrator"].predict(x))
    assert res_a.best_single == res_b.best_single
    assert fz_a.quantile_method == fz_b.quantile_method
    assert res_a.quantile_cv_pinball == res_b.quantile_cv_pinball
    assert res_a.lgbm_importance == res_b.lgbm_importance      # same LightGBM fit

    # the forecast probabilities are identical, only their verification differs
    for key in res_a.prob:
        assert np.array_equal(res_a.prob[key]["preds"]["calibrated"],
                              res_b.prob[key]["preds"]["calibrated"])
    rmse = lambda r: np.sqrt(np.nanmean(r.daily["context_shrink"]["mse"]))
    assert rmse(res_b) > rmse(res_a) + 10.0


def test_training_dates_never_fall_in_the_test_year(harness):
    res, fz = harness(0.0)
    assert res.test_year not in fz.train_years
    assert all(y < res.test_year for y in fz.train_years)
    assert all(d.year == res.test_year for d in res.valid)


def test_best_single_is_chosen_on_training_error(harness):
    res, fz = harness(0.0)
    assert res.best_single == min(fz.train_rmse, key=fz.train_rmse.get) == "a"
