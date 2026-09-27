"""Download India-box daily fields from WeatherBench2 into data/raw/ (resumable).

    python -m ingestion.download                # everything, precipitation first
    python -m ingestion.download --only hres --months 2022-06

Layout:  data/raw/<source>/<var>/<YYYY-MM>.nc
  forecasts: dims (init, lead_day, lat, lon)   truth: dims (date, lat, lon)
All values already in canonical units and on the IMD-day window (canonical/accumulation.py).
"""
from __future__ import annotations

import argparse
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from canonical import accumulation as acc
from canonical.grid import LAT, LON
from canonical.units import to_canonical
from experiments import design
from ingestion import wb2

warnings.filterwarnings("ignore")
RAW = Path("data/raw")
VAR_ORDER = ("precip", "t2m", "u10", "v10")


def _months(days: list[pd.Timestamp]) -> list[str]:
    return sorted({d.strftime("%Y-%m") for d in days})


def _write(ds: xr.Dataset, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp.nc")
    ds.to_netcdf(tmp, encoding={v: {"zlib": True, "complevel": 4} for v in ds.data_vars})
    tmp.replace(path)


def forecast_month(model: str, var: str, month: str) -> int:
    path = RAW / model / var / f"{month}.nc"
    if path.exists():
        return 0
    inits = [t for t in design.all_inits() if t.strftime("%Y-%m") == month]
    if not inits:
        return 0
    src = wb2.SOURCES[model]
    if var == "precip":
        leads = [h for d in acc.LEAD_DAYS for h in acc.rain_leads(d)]
        raw = wb2.read_forecast(src, var, inits, leads)
        vals = acc.window_from_rolling(raw[:, 0::2], raw[:, 1::2])
    else:
        vals = wb2.read_forecast(src, var, inits, [acc.inst_lead(d) for d in acc.LEAD_DAYS])
    vals = to_canonical(var, vals).astype(np.float32)
    ds = xr.Dataset({var: (("init", "lead_day", "lat", "lon"), vals)},
                    coords={"init": pd.DatetimeIndex(inits), "lead_day": list(acc.LEAD_DAYS),
                            "lat": LAT, "lon": LON},
                    attrs={"source": src.label, "window": "IMD day 03-03 UTC" if var == "precip"
                           else f"instant {acc.INST_HOUR_UTC} UTC"})
    _write(ds, path)
    return len(inits) * len(acc.LEAD_DAYS) * (2 if var == "precip" else 1)


def truth_month(var: str, month: str) -> int:
    path = RAW / "era5" / var / f"{month}.nc"
    if path.exists():
        return 0
    days = list(pd.date_range(f"{month}-01", periods=pd.Period(month).days_in_month, freq="D"))
    if var == "precip":
        v = [t for d in days for t in acc.rain_valid_times(d)]
        raw = wb2.read_analysis(var, v)
        vals = acc.window_from_rolling(raw[0::2], raw[1::2])
    else:
        vals = wb2.read_analysis(var, [acc.inst_valid_time(d) for d in days])
    vals = to_canonical(var, vals).astype(np.float32)
    ds = xr.Dataset({var: (("date", "lat", "lon"), vals)},
                    coords={"date": pd.DatetimeIndex(days), "lat": LAT, "lon": LON},
                    attrs={"source": "ERA5 (WeatherBench2)"})
    _write(ds, path)
    return len(days) * (2 if var == "precip" else 1)


def jobs(only: set[str] | None, months_filter: set[str] | None):
    truth_months = _months([d for y in design.YEARS for d in design.truth_days(y)])
    init_months = _months(design.all_inits())
    for var in VAR_ORDER:  # precipitation first: the ladder needs it before anything else
        if not only or "era5" in only:
            for m in truth_months:
                if not months_filter or m in months_filter:
                    yield ("era5", var, m)
        for model, src in wb2.SOURCES.items():
            if var in src.variables and (not only or model in only):
                for m in init_months:
                    if not months_filter or m in months_filter:
                        yield (model, var, m)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", help="sources: era5 hres ens graphcast pangu")
    ap.add_argument("--months", nargs="*", help="YYYY-MM filters")
    ap.add_argument("--vars", nargs="*", help="subset of precip t2m u10 v10")
    a = ap.parse_args()
    todo = [j for j in jobs(set(a.only) if a.only else None, set(a.months) if a.months else None)
            if not a.vars or j[1] in a.vars]
    t0, chunks = time.time(), 0
    for i, (src, var, month) in enumerate(todo, 1):
        t = time.time()
        for attempt in range(4):
            try:
                n = truth_month(var, month) if src == "era5" else forecast_month(src, var, month)
                break
            except Exception as e:  # network hiccups: retry, never abort the whole pull
                print(f"  retry {attempt + 1} {src}/{var}/{month}: {e!r}"[:200], flush=True)
                time.sleep(5 * (attempt + 1))
        else:
            print(f"FAILED {src}/{var}/{month}", flush=True)
            continue
        chunks += n
        if n:
            el = time.time() - t0
            print(f"[{i}/{len(todo)}] {src}/{var}/{month}: {n} chunks in {time.time() - t:.0f}s "
                  f"| total {chunks} chunks, {chunks / el:.1f}/s, {el / 60:.1f} min", flush=True)
    print("DONE", flush=True)
    import os
    os._exit(0)  # zarr keeps a non-daemon event-loop thread alive


if __name__ == "__main__":
    main()
