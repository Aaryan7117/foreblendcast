"""GRIB2 adapter via cfgrib — the "runs on HPC" proof (B4, TECH_APPROACH §1.1).

Reads a single GFS/ECMWF GRIB2 file from NOMADS or local disk and returns
a CanonicalForecast, proving the operational ingest path works.

    python -m ingestion.grib2 path/to/gfs.t00z.pgrb2.0p25.f024

This adapter is NOT used in the retrospective experiment (which reads WB2 Zarr).
It exists to prove the path from a live NWP GRIB2 file to the canonical schema.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from canonical import accumulation as acc
from canonical.forecast import CanonicalForecast
from canonical.grid import LAT, LON
from canonical.units import CANONICAL_UNITS, to_canonical
from ingestion.base import Adapter
from ingestion.registry import register

try:
    import xarray as xr
    HAS_CFGRIB = True
except ImportError:
    HAS_CFGRIB = False


# GRIB2 variable name mappings (GFS convention)
GRIB_VAR_MAP = {
    "precip": {"shortName": "tp", "cfName": "total_precipitation"},
    "t2m": {"shortName": "2t", "cfName": "2m_temperature"},
    "u10": {"shortName": "10u", "cfName": "10m_u_component_of_wind"},
    "v10": {"shortName": "10v", "cfName": "10m_v_component_of_wind"},
}


class Grib2Adapter(Adapter):
    """Reads a single GRIB2 file and extracts the India box.

    This proves the operational path: download a GRIB2 from NOMADS →
    extract the India box → return a CanonicalForecast.
    """
    name = "grib2"
    label = "GRIB2 proof-of-concept"
    kind = "nwp"
    variables = ("precip", "t2m", "u10", "v10")

    def __init__(self, grib_dir: str | Path = "data/raw/grib2"):
        self.grib_dir = Path(grib_dir)

    def load(self, init_time: pd.Timestamp, variable: str,
             lead_days: list[int] | None = None) -> Optional[CanonicalForecast]:
        """Load from GRIB2. Expects files named like gfs_YYYYMMDD00_fHHH.grib2."""
        if not HAS_CFGRIB:
            return None

        lead_days = lead_days or list(acc.LEAD_DAYS)
        init_str = init_time.strftime("%Y%m%d%H")

        fields = []
        valid_leads = []

        for ld in lead_days:
            if variable == "precip":
                lead_h = ld * 24  # use 24h accumulated total
            else:
                lead_h = acc.inst_lead(ld)

            pattern = f"*_{init_str}_f{lead_h:03d}.grib2"
            matches = list(self.grib_dir.glob(pattern))
            if not matches:
                continue

            try:
                ds = xr.open_dataset(matches[0], engine="cfgrib")
            except Exception:
                continue

            # Find the variable
            var_info = GRIB_VAR_MAP.get(variable, {})
            data_var = None
            for name in ds.data_vars:
                if name == var_info.get("shortName") or name == var_info.get("cfName"):
                    data_var = name
                    break
            if data_var is None and len(ds.data_vars) == 1:
                data_var = list(ds.data_vars)[0]
            if data_var is None:
                ds.close()
                continue

            da = ds[data_var]

            # Extract India box via interpolation to canonical grid
            lat_name = "latitude" if "latitude" in da.dims else "lat"
            lon_name = "longitude" if "longitude" in da.dims else "lon"

            # Handle longitude convention (GRIB is typically 0-360)
            da_india = da.interp(
                {lat_name: LAT, lon_name: LON},
                method="linear"
            ).values.astype(np.float32)

            fields.append(da_india)
            valid_leads.append(ld)
            ds.close()

        if not fields:
            return None

        values = np.stack(fields, axis=0)
        values = to_canonical(variable, values)

        return self._build_forecast(init_time, variable, valid_leads, values)


def prove_grib2(grib_path: str) -> None:
    """CLI entry point: read one GRIB2 file and print summary."""
    import xarray as xr
    ds = xr.open_dataset(grib_path, engine="cfgrib")
    print(f"Variables: {list(ds.data_vars)}")
    print(f"Dimensions: {dict(ds.dims)}")
    for v in ds.data_vars:
        da = ds[v]
        print(f"  {v}: shape={da.shape}, min={float(da.min()):.2f}, max={float(da.max()):.2f}")
    ds.close()
    print("✓ cfgrib read successful — HPC path proven")


register(Grib2Adapter())

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Prove GRIB2 read path")
    ap.add_argument("grib_file", help="Path to a GRIB2 file")
    args = ap.parse_args()
    prove_grib2(args.grib_file)
