"""Test FSS implementation (B6) — hand-computed toy case."""
import numpy as np
import pytest

from verification.fss import fss, f0_and_useful, fss_curve


class TestFSS:
    def test_perfect_forecast(self):
        """Perfect forecast should have FSS = 1."""
        obs = np.zeros((20, 20))
        obs[5:10, 5:10] = 1.0  # rain event
        score = fss(obs, obs, threshold=0.5, neighbourhood=1)
        assert np.isclose(score, 1.0)

    def test_no_event_both_sides(self):
        """No event in either forecast or obs → FSS = 1 (perfect no-rain score)."""
        fc = np.zeros((20, 20))
        obs = np.zeros((20, 20))
        score = fss(fc, obs, threshold=0.5, neighbourhood=1)
        assert np.isclose(score, 1.0)

    def test_complete_miss(self):
        """Forecast and obs in opposite corners → FSS → 0 at small scale."""
        fc = np.zeros((20, 20))
        fc[0:3, 0:3] = 100.0
        obs = np.zeros((20, 20))
        obs[17:20, 17:20] = 100.0
        score = fss(fc, obs, threshold=50.0, neighbourhood=1)
        assert score < 0.1  # Nearly zero at point scale

    def test_displacement_improves_with_scale(self):
        """FSS should improve as neighbourhood increases for displaced forecasts."""
        fc = np.zeros((20, 20))
        fc[8:12, 8:12] = 100.0
        obs = np.zeros((20, 20))
        obs[10:14, 10:14] = 100.0  # Slightly displaced
        
        fss_1 = fss(fc, obs, threshold=50.0, neighbourhood=1)
        fss_5 = fss(fc, obs, threshold=50.0, neighbourhood=5)
        fss_9 = fss(fc, obs, threshold=50.0, neighbourhood=9)
        assert fss_5 > fss_1  # Larger scale → better
        assert fss_9 >= fss_5

    def test_f0_and_useful(self):
        obs = np.zeros((100, 100))
        obs[:10, :10] = 100.0  # 1% of cells
        f0, useful = f0_and_useful(obs, 50.0)
        assert np.isclose(f0, 0.01)
        assert np.isclose(useful, 0.505)

    def test_fss_curve_structure(self):
        fc = np.random.rand(20, 20) * 100
        obs = np.random.rand(20, 20) * 100
        result = fss_curve(fc, obs, threshold=50.0)
        assert "fss" in result
        assert len(result["fss"]) == 5  # 5 neighbourhoods
        assert "f0" in result
        assert "fss_useful" in result
