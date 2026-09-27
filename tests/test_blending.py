"""Tests for blending algorithms."""

import numpy as np
from blending.deterministic import weighted_mean
from blending.probability_matched import probability_matched
from blending.physical import physical_validate

def test_weighted_mean():
    fields = {
        "m1": np.array([[1.0, 2.0], [3.0, 4.0]]),
        "m2": np.array([[3.0, 4.0], [1.0, 2.0]])
    }
    weights = {"m1": 0.7, "m2": 0.3}
    
    result = weighted_mean(fields, weights)
    
    # m1 gets 0.7, m2 gets 0.3
    # [0, 0] = 0.7*1 + 0.3*3 = 1.6
    # [0, 1] = 0.7*2 + 0.3*4 = 2.6
    # [1, 0] = 0.7*3 + 0.3*1 = 2.4
    # [1, 1] = 0.7*4 + 0.3*2 = 3.4
    
    expected = np.array([[1.6, 2.6], [2.4, 3.4]], dtype=np.float32)
    np.testing.assert_allclose(result, expected, rtol=1e-5)

def test_physical_validate():
    blend = {
        "precip": np.array([[-1.0, 2.0], [0.0, -0.5]]),
        "tmax": np.array([[30.0, 25.0]]),
        "tmin": np.array([[20.0, 28.0]]),  # tmin > tmax at index 1
        "u10": np.array([[3.0, 0.0]]),
        "v10": np.array([[4.0, 0.0]])
    }
    
    validated = physical_validate(blend)
    
    # precip clipped to 0
    np.testing.assert_allclose(validated["precip"], np.array([[0.0, 2.0], [0.0, 0.0]]))
    
    # tmax forced to tmin where invalid
    np.testing.assert_allclose(validated["tmax"], np.array([[30.0, 28.0]]))
    
    # wind speed derived
    np.testing.assert_allclose(validated["wind_speed"], np.array([[5.0, 0.0]]))
