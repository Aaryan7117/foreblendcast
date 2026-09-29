"""Adaptive weighting: direction of the weights, shrinkage, and the historical skill database."""
from pathlib import Path

import numpy as np
import pytest

from weighting.context import ContextAware
from weighting.shrinkage import ContextShrinkPM, shrink, softmax_weights

HAS_STATIC = Path("data/static/grid_static.nc").exists() and Path("data/static/districts_index.json").exists()
needs_static = pytest.mark.skipif(not HAS_STATIC, reason="data/static not built")


def test_lower_error_gets_higher_weight():
    w = softmax_weights(np.array([2.0, 1.0, 4.0]), tau=1.0)
    assert w[1] > w[0] > w[2]
    assert np.isclose(w.sum(), 1.0)


def test_strategies_treat_scores_as_errors():
    scores = {"good": 1.0, "bad": 3.0}
    for strategy in (ContextAware(tau=1.0), ContextShrinkPM(tau=1.0)):
        w = strategy.compute_weights(["good", "bad"], scores=scores, n_eff=100)
        assert w["good"] > w["bad"], type(strategy).__name__


def test_model_without_history_gets_zero_weight():
    w = softmax_weights(np.array([1.0, np.nan]), tau=0.5)
    assert w[1] == 0.0 and np.isclose(w[0], 1.0)


def test_no_history_at_all_gives_equal_weights():
    w = softmax_weights(np.array([np.nan, np.nan, np.nan]), tau=0.5)
    assert np.allclose(w, 1 / 3)


def test_smaller_tau_is_sharper():
    err = np.array([1.0, 1.2])
    assert softmax_weights(err, 0.05)[0] > softmax_weights(err, 1.0)[0]


def test_shrinkage_moves_towards_parent_when_evidence_is_thin():
    local = np.array([[0.9], [0.1]])
    parent = np.array([[0.5], [0.5]])
    thin, lam_thin = shrink(local, parent, np.array([20.0]), k=20.0, n_eff_min=15.0)
    rich, lam_rich = shrink(local, parent, np.array([2000.0]), k=20.0, n_eff_min=15.0)
    assert np.isclose(lam_thin[0], 0.5) and lam_rich[0] > 0.98
    assert abs(thin[0, 0] - 0.5) < abs(rich[0, 0] - 0.5)
    assert np.allclose(thin.sum(axis=0), 1.0)


def test_node_below_minimum_inherits_parent():
    local = np.array([[0.9], [0.1]])
    parent = np.array([[0.3], [0.7]])
    w, lam = shrink(local, parent, np.array([5.0]), k=20.0, n_eff_min=15.0)
    assert lam[0] == 0.0 and np.allclose(w, parent)
    got = ContextShrinkPM(tau=1.0).compute_weights(
        ["a", "b"], scores={"a": 1.0, "b": 2.0}, n_eff=5, parent_weights={"a": 0.3, "b": 0.7})
    assert np.isclose(got["a"], 0.3) and np.isclose(got["b"], 0.7)


@pytest.fixture(scope="module")
def setup():
    from regimes import detector as rg
    from weighting import skill as sk

    geo = rg.load_geography()
    rng = np.random.default_rng(0)
    n = 48
    shape = (n,) + geo.land.shape
    obs = rng.gamma(2.0, 3.0, shape).astype(np.float32)
    # "north" is accurate in the northern half, "south" in the southern half
    north = np.arange(shape[1])[:, None] >= shape[1] // 2
    noise = lambda good: np.where(good, 0.5, 5.0) * rng.standard_normal(shape)
    fc = {"north": (obs + noise(north)).astype(np.float32),
          "south": (obs + noise(~north)).astype(np.float32)}
    seasons = np.repeat(np.arange(4), n // 4)
    regimes = np.tile(np.arange(3), n // 3)[:, None].repeat(geo.n_regions + 1, axis=1)
    db = sk.build_skill(["north", "south"], "precip", 1, fc, obs, seasons, regimes, geo)
    return geo, sk, db, fc, obs, seasons, regimes, north


@needs_static
def test_weights_follow_regional_skill(setup):
    geo, sk, db, *_, north = setup
    ws = sk.compute_weights(db, geo, tau=0.1, k=20.0, n_eff_min=1.0)
    w_north_model = ws.cell[:, :, 0]
    up = np.broadcast_to(north & geo.land, w_north_model.shape)
    down = np.broadcast_to(~north & geo.land, w_north_model.shape)
    assert w_north_model[up].mean() > 0.8
    assert w_north_model[down].mean() < 0.2
    assert np.allclose(ws.cell.sum(axis=2), 1.0, atol=1e-6)


@needs_static
def test_blend_beats_equal_weights(setup):
    geo, sk, db, fc, obs, seasons, regimes, _ = setup
    ws = sk.compute_weights(db, geo, tau=0.1, k=20.0, n_eff_min=1.0)
    blend, applied = sk.blend_stack(fc, db.models, ws.cell, seasons, regimes, geo)
    equal = np.mean(np.stack(list(fc.values())), axis=0)
    err = lambda f: np.sqrt(np.mean((f - obs)[:, geo.land] ** 2))
    assert err(blend) < err(equal)
    assert np.allclose(applied.sum(axis=1), 1.0, atol=1e-5)


@needs_static
def test_missing_model_is_dropped_and_weights_renormalised(setup):
    geo, sk, db, fc, obs, seasons, regimes, _ = setup
    ws = sk.compute_weights(db, geo, tau=0.1, k=20.0, n_eff_min=1.0)
    broken = {"north": fc["north"].copy(), "south": fc["south"]}
    broken["north"][0] = np.nan
    blend, applied = sk.blend_stack(broken, db.models, ws.cell, seasons, regimes, geo)
    assert np.allclose(applied[0, 0], 0.0) and np.allclose(applied[0, 1], 1.0)
    assert np.allclose(blend[0], fc["south"][0])


@needs_static
def test_skill_uses_only_selected_samples(setup):
    geo, sk, _, fc, obs, seasons, regimes, _ = setup
    use = np.arange(len(seasons)) % 2 == 0
    a = sk.build_skill(["north", "south"], "precip", 1, fc, obs, seasons, regimes, geo, use=use)
    changed = obs.copy()
    changed[~use] += 100.0          # observations outside the selection
    b = sk.build_skill(["north", "south"], "precip", 1, fc, changed, seasons, regimes, geo, use=use)
    assert np.array_equal(a.sse, b.sse) and np.array_equal(a.count, b.count)
