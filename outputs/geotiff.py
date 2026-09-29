"""GeoTIFF export: georeferenced rasters for GIS use (B17)."""
from __future__ import annotations

from pathlib import Path

import numpy as np

from canonical.grid import BOUNDS, LAT, LON, RES

NODATA = -9999.0


def write_geotiff(bands: dict[str, np.ndarray], path: str | Path, tags: dict | None = None) -> Path:
    """Write (lat, lon) fields on the canonical grid as a multi-band GeoTIFF.

    Fields are stored north-up in EPSG:4326 with one band per entry; band descriptions
    carry the names.
    """
    import rasterio
    from rasterio.transform import from_origin

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    transform = from_origin(BOUNDS["west"], BOUNDS["north"], RES, RES)
    with rasterio.open(path, "w", driver="GTiff", height=len(LAT), width=len(LON),
                       count=len(bands), dtype="float32", crs="EPSG:4326",
                       transform=transform, nodata=NODATA, compress="deflate") as dst:
        for i, (name, field) in enumerate(bands.items(), start=1):
            data = np.where(np.isfinite(field), field, NODATA).astype(np.float32)[::-1]
            dst.write(data, i)
            dst.set_band_description(i, name)
        if tags:
            dst.update_tags(**{k: str(v) for k, v in tags.items()})
    return path
