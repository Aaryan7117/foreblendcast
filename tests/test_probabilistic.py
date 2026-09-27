"""Tests for probabilistic metrics."""

import numpy as np
from verification.probabilistic import brier_score, brier_skill_score, roc_auc

def test_brier_score():
    prob = np.array([0.1, 0.9, 0.8, 0.3])
    obs = np.array([0.0, 1.0, 0.0, 1.0])
    
    # diff = [0.1, -0.1, 0.8, -0.7]
    # diff^2 = [0.01, 0.01, 0.64, 0.49]
    # mean = 1.15 / 4 = 0.2875
    bs = brier_score(prob, obs)
    np.testing.assert_almost_equal(bs, 0.2875)

def test_roc_auc_perfect():
    prob = np.array([0.9, 0.8, 0.2, 0.1])
    obs = np.array([1, 1, 0, 0])
    
    auc = roc_auc(prob, obs)
    assert auc == 1.0

def test_roc_auc_random():
    prob = np.array([0.5, 0.5, 0.5, 0.5])
    obs = np.array([1, 0, 1, 0])
    
    auc = roc_auc(prob, obs)
    assert auc == 0.5
