"""P-3: inventory WeatherBench2 stores — which variables, years, leads exist over the India box.

Run: python -m ingestion.inventory
Writes: results/inventory.json and prints a table.
"""
from __future__ import annotations

import json
import warnings
from pathlib import Path

import xarray as xr

warnings.filterwarnings("ignore")

WB2 = "gs://weatherbench2/datasets"
CANDIDATES = {
    "hres": f"{WB2}/hres/2016-2022-0012-1440x721.zarr",
    "ifs_ens_mean": f"{WB2}/ifs_ens/2018-2022-1440x721_mean.zarr",
    "graphcast_2018": f"{WB2}/graphcast_v2/2018-1440x721.zarr",
    "graphcast_2020": f"{WB2}/graphcast_v2/2020-1440x721.zarr",
    "graphcast_2022": f"{WB2}/graphcast_v2/2022-1440x721.zarr",
    "pangu": f"{WB2}/pangu/2018-2022_0012_0p25.zarr",
    "era5": f"{WB2}/era5/1959-2022-6h-1440x721.zarr",
}
WANTED = ["total_precipitation_24hr", "total_precipitation_6hr", "total_precipitation",
          "2m_temperature", "10m_u_component_of_wind", "10m_v_component_of_wind",
          "maximum_temperature", "minimum_temperature"]


def describe(name: str, url: str) -> dict:
    ds = xr.open_zarr(url, storage_options={"token": "anon"}, consolidated=True, chunks=None)
    out = {"url": url, "dims": {k: int(v) for k, v in ds.sizes.items()}}
    tdim = "time" if "time" in ds.dims else None
    if tdim:
        t = ds[tdim].values
        out["time_first"], out["time_last"] = str(t[0])[:16], str(t[-1])[:16]
    if "prediction_timedelta" in ds.dims:
        lt = ds["prediction_timedelta"].values.astype("timedelta64[h]").astype(int)
        out["lead_hours"] = [int(lt[0]), int(lt[1] - lt[0]) if len(lt) > 1 else 0, int(lt[-1])]
    out["vars_wanted"] = {v: (v in ds.data_vars) for v in WANTED}
    out["precip_vars"] = sorted(v for v in ds.data_vars if "precip" in v)
    out["lat_order"] = "asc" if float(ds.latitude[0]) < float(ds.latitude[-1]) else "desc"
    return out


def main() -> None:
    inv = {}
    for name, url in CANDIDATES.items():
        try:
            inv[name] = describe(name, url)
        except Exception as e:  # noqa: BLE001 — inventory must report, not crash
            inv[name] = {"url": url, "error": repr(e)[:200]}
    Path("results").mkdir(exist_ok=True)
    Path("results/inventory.json").write_text(json.dumps(inv, indent=2))
    for name, d in inv.items():
        if "error" in d:
            print(f"{name:16s} ERROR {d['error']}")
            continue
        wanted = " ".join(k.replace("_component_of_wind", "").replace("total_precipitation", "tp")
                          for k, v in d["vars_wanted"].items() if v)
        print(f"{name:16s} {d.get('time_first','')} → {d.get('time_last','')}  "
              f"lead={d.get('lead_hours')}  lat={d['lat_order']}  dims={d['dims']}\n"
              f"{'':16s} has: {wanted}  | precip vars: {d['precip_vars']}")


if __name__ == "__main__":
    main()
