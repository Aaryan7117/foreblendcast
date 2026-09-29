"""Bootstrap, economic value, pooled FSS, quantiles, quality gate and hazard events."""
import numpy as np
import pytest

from calibration.quantiles import (LEVELS, ConditionalQuantiles, crps_ensemble,
                                   crps_from_quantiles)
from canonical.grid import LAT, LON
from canonical.quality_gate import screen_stack
from hazards.district import assign_tier
from hazards.events import EVENTS, heatwave_margin
from verification.bootstrap import (block_bootstrap_diff, block_bootstrap_rmse_diff,
                                    block_indices)
from verification.economic_value import economic_value, rev_from_counts
from verification.fss import KM_PER_CELL, NEIGHBOURHOODS, SCALES_KM, fss, fss_pooled
from verification.probabilistic import brier_skill_score, reliability_bins, roc_auc


# ── bootstrap ──
def test_block_indices_are_contiguous_blocks_of_dates():
    idx = block_indices(n=40, block_size=4, n_reps=5)
    assert idx.shape == (5, 40) and idx.min() >= 0 and idx.max() < 40
    inside = np.diff(idx.reshape(5, 10, 4), axis=2)
    assert np.all(inside == 1)


def test_bootstrap_handles_series_shorter_than_a_block():
    lo, hi = block_bootstrap_diff(np.array([1.0, 2.0, 3.0]), np.array([1.0, 1.0, 1.0]), block_size=7)
    assert np.isfinite(lo) and np.isfinite(hi)


def test_rmse_difference_interval_detects_a_real_difference():
    rng = np.random.default_rng(1)
    better = rng.gamma(2.0, 1.0, 200)
    worse = better + 1.0 + 0.1 * rng.standard_normal(200)
    lo, hi = block_bootstrap_rmse_diff(better, worse)
    assert hi < 0
    same = rng.permutation(better)        # same error distribution, no real difference
    lo, hi = block_bootstrap_rmse_diff(better, same)
    assert lo < 0 < hi


# ── economic value ──
def test_perfect_forecast_has_full_value_and_climatology_none():
    obs = (np.arange(1000) % 10 == 0).astype(float)
    perfect = economic_value(obs, obs)
    assert np.allclose(perfect["rev"], 1.0)
    clim = economic_value(np.full(1000, obs.mean()), obs)
    assert max(clim["rev"]) <= 1e-9


def test_rev_from_counts_matches_the_probability_version():
    rng = np.random.default_rng(2)
    obs = (rng.random(5000) < 0.1).astype(float)
    yes = ((obs + rng.random(5000) * 0.8) > 0.6).astype(float)
    hits = int(np.sum((yes == 1) & (obs == 1)))
    fa = int(np.sum((yes == 1) & (obs == 0)))
    misses = int(np.sum((yes == 0) & (obs == 1)))
    direct = rev_from_counts(hits, fa, misses, 5000, 0.1)
    curve = economic_value(yes, obs, np.array([0.1]))["rev"][0]
    # the curve may also choose never/always acting, so it is at least as good
    assert curve >= direct - 1e-6
    assert direct < 1.0


# ── FSS ──
def test_scale_labels_are_the_real_neighbourhood_widths():
    assert list(SCALES_KM) == [int(round(n * KM_PER_CELL)) for n in NEIGHBOURHOODS]
    assert SCALES_KM[NEIGHBOURHOODS.index(9)] == 250


def test_pooled_fss_ignores_days_without_events():
    rng = np.random.default_rng(3)
    event_fc = np.zeros((1, 30, 30)); event_fc[0, 5:10, 5:10] = 100
    event_ob = np.zeros((1, 30, 30)); event_ob[0, 7:12, 7:12] = 100
    quiet = np.zeros((9, 30, 30))
    fc, ob = np.concatenate([event_fc, quiet]), np.concatenate([event_ob, quiet])
    one_day = fss(event_fc[0], event_ob[0], 50.0, 5)
    assert np.isclose(fss_pooled(fc, ob, 50.0, 5), one_day, atol=1e-6)
    mean_of_daily = np.mean([fss(f, o, 50.0, 5) for f, o in zip(fc, ob)])
    assert mean_of_daily > one_day + 0.1          # what averaging would have reported
    assert np.isnan(fss_pooled(quiet, quiet, 50.0, 5))


# ── probabilities ──
def test_reliability_and_auc():
    rng = np.random.default_rng(4)
    p = rng.random(20000)
    o = (rng.random(20000) < p).astype(float)
    rel = reliability_bins(p, o)
    assert np.allclose(rel["observed_freq"], rel["mean_forecast"], atol=0.05)
    assert sum(rel["counts"]) == 20000
    assert 0.8 < roc_auc(p, o) < 0.87
    assert brier_skill_score(p, o, base_rate=0.5) > 0.3


# ── quantiles ──
def test_conditional_quantiles_are_ordered_and_calibrated():
    rng = np.random.default_rng(5)
    pred = rng.gamma(2.0, 5.0, 40000)
    obs = np.maximum(pred * rng.lognormal(0.0, 0.4, 40000), 0.0)
    q = ConditionalQuantiles(floor=0.0).fit(pred[:30000], obs[:30000])
    out = q.predict(pred[30000:])
    assert out.shape == (len(LEVELS), 10000)
    assert np.all(np.diff(out, axis=0) >= 0) and out.min() >= 0
    inside = np.mean((obs[30000:] >= out[0]) & (obs[30000:] <= out[-1]))
    assert 0.86 < inside < 0.94
    lo, hi = q.interval(np.array([10.0]))
    assert lo[0] < 10.0 < hi[0]


def test_quantile_crps_beats_the_point_forecast():
    rng = np.random.default_rng(6)
    pred = rng.gamma(2.0, 5.0, 20000)
    obs = np.maximum(pred + 3.0 * rng.standard_normal(20000), 0.0)
    q = ConditionalQuantiles(floor=0.0).fit(pred[:15000], obs[:15000])
    crps = crps_from_quantiles(q.predict(pred[15000:]), obs[15000:])
    mae = np.mean(np.abs(pred[15000:] - obs[15000:]))
    assert crps < mae
    assert np.isclose(crps_ensemble(pred[None, 15000:], obs[15000:]), mae)


# ── quality gate ──
def test_gate_rejects_bad_days_and_repairs_negative_rain():
    stack = np.full((4, len(LAT), len(LON)), 5.0, np.float32)
    stack[1, 0, 0] = 9999.0          # implausible
    stack[2] = np.nan                # model did not arrive
    stack[3, :3, :3] = -2.0          # slightly negative rain from an AI model
    clean, rejected, repaired = screen_stack(stack, "precip")
    assert set(rejected) == {1, 2}
    assert "range_violation" in rejected[1] and rejected[2] == "all_nan"
    assert np.isnan(clean[1]).all() and np.isnan(clean[2]).all()
    assert repaired == 9 and clean[3].min() == 0.0
    assert np.array_equal(clean[0], stack[0])


def test_gate_keeps_real_extremes():
    stack = np.full((1, len(LAT), len(LON)), 5.0, np.float32)
    stack[0, 10, 10] = 1339.0        # highest single-cell rainfall in the HRES archive
    _, rejected, _ = screen_stack(stack, "precip")
    assert not rejected


# ── hazards ──
def test_heatwave_needs_both_heat_and_departure():
    clim = np.array([38.0, 30.0, 41.0, 30.0])
    t2m = np.array([41.0, 41.0, 46.0, 36.0])
    assert list(heatwave_margin(t2m, clim) >= 0) == [False, True, True, False]


def test_every_variable_has_events():
    assert {e.key for e in EVENTS["precip"]} == {"p_gt_64p5", "p_gt_115p6", "p_gt_204p5"}
    assert "p_heatwave" in {e.key for e in EVENTS["t2m"]}
    assert EVENTS["wind"]
    wind = EVENTS["wind"][0]
    assert wind.margin(np.array([9.0]), None)[0] > 0 > wind.margin(np.array([3.0]), None)[0]


def test_tier_uses_the_thresholds_it_is_given():
    assert assign_tier(0.35, 0.1, 0.0) == "green"
    tuned = {"p_gt_64p5": 0.3, "p_gt_115p6": 0.25, "p_gt_204p5": 0.1}
    assert assign_tier(0.35, 0.1, 0.0, tuned) == "yellow"
    assert assign_tier(0.9, 0.3, 0.05, tuned) == "orange"
    assert assign_tier(0.9, 0.6, 0.12, tuned) == "red"


# ── LightGBM layers ──
def _lgbm_problem(n=30000, seed=8):
    from calibration import lgbm
    rng = np.random.default_rng(seed)
    blend = rng.gamma(2.0, 5.0, n).astype(np.float32)
    lat = rng.uniform(8, 36, n).astype(np.float32)
    # the blend is biased in the north, and the error grows with the amount
    obs = np.maximum(blend + np.where(lat > 22, 4.0, 0.0) + 0.3 * blend * rng.standard_normal(n), 0.0)
    X = np.stack([blend, lat], axis=1).astype(np.float32)
    return lgbm, X, obs.astype(np.float32), ["blend", "lat"]


def test_lgbm_quantiles_are_ordered_and_learn_the_context():
    lgbm, X, y, names = _lgbm_problem()
    q = lgbm.LgbmQuantiles(floor=0.0, rounds=40).fit(X[:20000], y[:20000], names)
    out = q.predict(X[20000:])
    assert out.shape == (len(lgbm.LEVELS), 10000)
    assert np.all(np.diff(out, axis=0) >= 0) and out.min() >= 0
    inside = np.mean((y[20000:] >= out[0]) & (y[20000:] <= out[-1]))
    assert 0.84 < inside < 0.95
    table = ConditionalQuantiles(floor=0.0).fit(X[:20000, 0], y[:20000])
    common = [int(np.argmin(np.abs(LEVELS - lv))) for lv in lgbm.LEVELS]
    blind = lgbm.pinball(table.predict(X[20000:, 0])[common], y[20000:], lgbm.LEVELS)
    assert lgbm.pinball(out, y[20000:], lgbm.LEVELS) < blind     # it used the latitude
    assert q.importance["lat"] > 0


def test_lgbm_blend_corrects_a_bias_and_keeps_missing_as_missing():
    lgbm, X, y, names = _lgbm_problem()
    model = lgbm.LgbmBlend(floor=0.0, rounds=40).fit(X[:20000], y[:20000], names)
    pred = model.predict(X[20000:])
    rmse = lambda f: np.sqrt(np.mean((f - y[20000:]) ** 2))
    assert rmse(pred) < rmse(X[20000:, 0])
    gap = np.array([[np.nan, 20.0]], dtype=np.float32)
    assert np.isnan(model.predict(gap)[0])


def test_lgbm_features_have_one_row_per_day_and_cell():
    from calibration import lgbm
    import pandas as pd
    n, shape = 3, (4, 5)
    rng = np.random.default_rng(9)
    members = {"a": rng.random((n,) + shape).astype(np.float32),
               "b": rng.random((n,) + shape).astype(np.float32)}
    members["b"][1] = np.nan                       # model b missing on day 1
    cells = np.zeros(shape, dtype=bool); cells[1:3, 1:4] = True
    lat2d, lon2d = np.meshgrid(np.arange(4.0), np.arange(5.0), indexing="ij")
    X = lgbm.build_features(members["a"], members, ["a", "b"], np.array([0, 1, 2]),
                            np.ones((n,) + shape, np.int8), np.zeros((n,) + shape, np.float32),
                            list(pd.date_range("2022-06-01", periods=n)), lat2d, lon2d, cells)
    names = lgbm.feature_names(["a", "b"])
    assert X.shape == (n * 6, len(names))
    day1 = X[6:12]
    assert np.isnan(day1[:, names.index("member_b")]).all()
    assert np.allclose(day1[:, names.index("member_min")], day1[:, names.index("member_a")])
    assert np.allclose(day1[:, names.index("spread")], 0.0)
