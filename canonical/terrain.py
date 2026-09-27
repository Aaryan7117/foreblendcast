"""Terrain classification per grid cell from SRTM (B3, TECH_APPROACH §2.2).

Classes (orthogonal to the region hierarchy):
  ghats_windward   — lon < Ghats crest & elevation > 300 m
  ghats_leeward    — lon > Ghats crest & elevation > 300 m, south of 20°N
  himalayan_foothills — elevation 300–2000 m, lat > 26°N
  coastal           — ≤ 25 km from coastline (approximated by land fraction < 0.8)
  plains            — everything else on land

Definitions are printed in the limitations appendix.
"""
from __future__ import annotations

import numpy as np

from canonical.grid import LAT, LON

# Approximate Western Ghats crest longitude (degrees E) as a function of latitude.
# Simplified from SRTM ridge line. Used when SRTM DEM is not available.
_GHATS_CREST_LON = {
    (8, 12): 77.0,   # Kerala / Tamil Nadu border
    (12, 16): 76.0,  # Karnataka
    (16, 20): 74.0,  # Goa / Maharashtra
}


def _ghats_crest(lat: float) -> float | None:
    """Return approximate crest longitude for a latitude, or None if outside Ghats range."""
    for (lo, hi), lon in _GHATS_CREST_LON.items():
        if lo <= lat < hi:
            return lon
    return None


def classify_cells(
    elevation: np.ndarray | None = None,
    land_mask: np.ndarray | None = None,
) -> np.ndarray:
    """Return a string array (lat, lon) of terrain class labels.

    If elevation is None, uses a flat approximation (plains everywhere on land).
    """
    nlat, nlon = len(LAT), len(LON)
    classes = np.full((nlat, nlon), "ocean", dtype="U20")

    if land_mask is None:
        land_mask = np.ones((nlat, nlon), dtype=bool)

    classes[land_mask] = "plains"

    if elevation is not None:
        for i, lat in enumerate(LAT):
            for j, lon in enumerate(LON):
                if not land_mask[i, j]:
                    continue
                elev = elevation[i, j]

                # Himalayan foothills
                if lat > 26.0 and 300 <= elev <= 2000:
                    classes[i, j] = "himalayan_foothills"
                    continue

                # Western Ghats
                crest = _ghats_crest(lat)
                if crest is not None and elev > 300:
                    if lon < crest:
                        classes[i, j] = "ghats_windward"
                    else:
                        classes[i, j] = "ghats_leeward"
                    continue

        # Coastal: land fraction < 0.8 approximation (cells near coastline)
        # When we have the actual land fraction from regionmask, use it.
        # For now, mark cells where at least one neighbour is ocean.
        for i in range(nlat):
            for j in range(nlon):
                if classes[i, j] != "plains":
                    continue
                neighbours = []
                for di in (-1, 0, 1):
                    for dj in (-1, 0, 1):
                        ni, nj = i + di, j + dj
                        if 0 <= ni < nlat and 0 <= nj < nlon:
                            neighbours.append(land_mask[ni, nj])
                if not all(neighbours):
                    classes[i, j] = "coastal"

    return classes


TERRAIN_CLASSES = ("plains", "ghats_windward", "ghats_leeward",
                   "himalayan_foothills", "coastal", "ocean")
