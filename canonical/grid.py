"""Canonical grid = the IMD 0.25° gridded-rainfall grid (D-20).

lat 6.5 -> 38.5 N (129, ascending), lon 66.5 -> 100.0 E (135). WB2 0.25° products sit on
exactly these points, so alignment is an index slice, not an interpolation.
"""
import numpy as np

RES = 0.25
LAT = np.round(np.arange(6.5, 38.5 + RES / 2, RES), 2)
LON = np.round(np.arange(66.5, 100.0 + RES / 2, RES), 2)
KM_PER_CELL = 111.2 * RES  # ~27.8 km (meridional)

# Cell-edge bounds for georeferenced PNG overlays.
BOUNDS = {"south": float(LAT[0] - RES / 2), "north": float(LAT[-1] + RES / 2),
          "west": float(LON[0] - RES / 2), "east": float(LON[-1] + RES / 2)}


def area_weights() -> np.ndarray:
    """cos(lat) weights broadcast to (lat, lon)."""
    return np.repeat(np.cos(np.deg2rad(LAT))[:, None], len(LON), axis=1)
