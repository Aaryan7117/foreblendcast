"""NetCDF export (B17).

One CF-1.8 file per cycle with the provenance block as global attrs.
"""
from __future__ import annotations

from pathlib import Path

import xarray as xr


def export_cycle_netcdf(datasets: dict[int, xr.Dataset], cycle: str, provenance_meta: dict, out_dir: str | Path = "results"):
    """Export the blended fields for all lead days into a single CF-compliant NetCDF.
    
    datasets: {lead_day: xr.Dataset(lat, lon)}
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    
    # Combine datasets along lead_day dimension
    leads = sorted(datasets.keys())
    combined = xr.concat([datasets[ld] for ld in leads], dim="lead_day")
    combined = combined.assign_coords(lead_day=leads)
    
    # Add global attributes
    for k, v in provenance_meta.items():
        if isinstance(v, (dict, list)):
            combined.attrs[k] = str(v)
        else:
            combined.attrs[k] = v
            
    combined.attrs["Conventions"] = "CF-1.8"
    
    # Add encoding for compression
    encoding = {var: {"zlib": True, "complevel": 4} for var in combined.data_vars}
    
    combined.to_netcdf(out / f"blend_{cycle}.nc", encoding=encoding)
