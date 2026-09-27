"""Unit normalisation to canonical units: rain mm, temperature °C, wind m/s."""
import numpy as np

CANONICAL_UNITS = {"precip": "mm", "t2m": "degC", "u10": "m s-1", "v10": "m s-1"}


def to_canonical(var: str, x: np.ndarray) -> np.ndarray:
    if var == "precip":
        return x * 1000.0      # WB2 stores metres of water
    if var == "t2m":
        return x - 273.15      # K -> °C
    return x
