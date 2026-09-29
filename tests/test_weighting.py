"""Tests for weighting strategies."""

import numpy as np
from weighting.inverse_error import InverseError
from weighting.context import ContextAware
from weighting.baselines import EqualWeights, BestSingle

def test_equal_weights():
    w = EqualWeights().compute_weights(["m1", "m2", "m3"])
    assert w == {"m1": 1/3, "m2": 1/3, "m3": 1/3}

def test_best_single():
    w = BestSingle().compute_weights(["m1", "m2", "m3"], rmse={"m1": 2.0, "m2": 1.0, "m3": 3.0})
    assert w == {"m1": 0.0, "m2": 1.0, "m3": 0.0}

def test_inverse_error():
    w = InverseError(epsilon=0).compute_weights(["m1", "m2"], rmse={"m1": 2.0, "m2": 4.0})
    # inv errors = 0.5, 0.25 -> total 0.75
    # w = 0.5/0.75, 0.25/0.75
    assert np.isclose(w["m1"], 2/3)
    assert np.isclose(w["m2"], 1/3)

def test_context_aware():
    # ContextAware scores are *errors* (lower is better): w = softmax(-score / tau).
    # See weighting/context.py docstring. m2 (score 0) must therefore get the larger weight.
    strategy = ContextAware(tau=1.0)
    w = strategy.compute_weights(["m1", "m2"], scores={"m1": 1.0, "m2": 0.0})
    exp_vals = np.exp([-1.0, 0.0])
    expected_m1 = exp_vals[0] / sum(exp_vals)
    expected_m2 = exp_vals[1] / sum(exp_vals)

    assert np.isclose(w["m1"], expected_m1)
    assert np.isclose(w["m2"], expected_m2)
    assert w["m2"] > w["m1"]
    assert np.isclose(sum(w.values()), 1.0)


def test_context_aware_nan_score_gets_negligible_weight():
    w = ContextAware(tau=1.0).compute_weights(["m1", "m2"], scores={"m1": float("nan"), "m2": 0.5})
    assert w["m1"] < 1e-6
    assert np.isclose(w["m2"], 1.0)
