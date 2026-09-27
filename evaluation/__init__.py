"""Result writers (B12): produce all JSON files in results/ per the data contract.

Writers for: ladder.json, districts_L{lead}.json, points/{city}.json,
where_we_lose.json, rev.json, reliability.json, fss_curve.json.
Every file carries the `meta` block from provenance().
"""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

RESULTS = Path("results")
RESULTS.mkdir(exist_ok=True)

# Five showcase cities (§3.5)
CITIES = {
    "mumbai":   {"lat": 19.07, "lon": 72.88, "name": "Mumbai"},
    "chennai":  {"lat": 13.08, "lon": 80.27, "name": "Chennai"},
    "kolkata":  {"lat": 22.57, "lon": 88.36, "name": "Kolkata"},
    "delhi":    {"lat": 28.61, "lon": 77.21, "name": "Delhi"},
    "guwahati": {"lat": 26.14, "lon": 91.74, "name": "Guwahati"},
}


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return "unknown"


def provenance(cycle: str = "2022-06-14T00Z", models: list[str] | None = None,
               strategy: str = "context_shrink_pm",
               ground_truth: str = "ERA5",
               fixture: bool = False) -> dict:
    """Build the common meta block for every results JSON."""
    return {
        "cycle": cycle,
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "git_commit": _git_commit(),
        "fixture": fixture,
        "ground_truth": ground_truth,
        "models_used": models or ["hres", "ens", "graphcast"],
        "availability_pattern": "full",
        "strategy": strategy,
        "accumulation_window_utc": "03:00-03:00",
        "district_aggregation": "area_weighted_p90",
        "status": "EXERCISE - NOT AN OFFICIAL IMD WARNING",
    }


def _write_json(obj: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    class NumpyEncoder(json.JSONEncoder):
        def default(self, o):
            if isinstance(o, (np.integer,)):
                return int(o)
            if isinstance(o, (np.floating,)):
                return round(float(o), 6)
            if isinstance(o, np.ndarray):
                return o.tolist()
            return super().default(o)

    path.write_text(json.dumps(obj, indent=2, cls=NumpyEncoder))


def write_ladder(rows: list[dict], headline: dict,
                 variable: str = "precip",
                 lead_days: list[int] = None,
                 **meta_kwargs) -> Path:
    """Write results/ladder.json per TECH_APPROACH §3.2."""
    lead_days = lead_days or [1, 3, 5, 7, 9]
    obj = {
        "meta": provenance(**meta_kwargs),
        "variable": variable,
        "lead_days": lead_days,
        "rows": rows,
        "headline": headline,
    }
    path = RESULTS / "ladder.json"
    _write_json(obj, path)
    return path


def write_districts(lead_day: int, districts: list[dict], **meta_kwargs) -> Path:
    """Write results/districts_L{lead}.json per TECH_APPROACH §3.3."""
    obj = {
        "meta": provenance(**meta_kwargs),
        "lead_day": lead_day,
        "districts": districts,
    }
    path = RESULTS / f"districts_L{lead_day}.json"
    _write_json(obj, path)
    return path


def write_points(city_slug: str, city_data: dict, **meta_kwargs) -> Path:
    """Write results/points/{city}.json per TECH_APPROACH §3.5."""
    info = CITIES[city_slug]
    obj = {
        "meta": provenance(**meta_kwargs),
        "city": info["name"],
        "lat": info["lat"],
        "lon": info["lon"],
        "variable": "precip",
        "lead_days": list(range(1, 11)),
        **city_data,
    }
    path = RESULTS / "points" / f"{city_slug}.json"
    _write_json(obj, path)
    return path


def write_where_we_lose(cells: list[dict], **meta_kwargs) -> Path:
    """Write results/where_we_lose.json per TECH_APPROACH §3.7."""
    obj = {
        "meta": provenance(**meta_kwargs),
        "cells": cells,
    }
    path = RESULTS / "where_we_lose.json"
    _write_json(obj, path)
    return path


def write_rev(rev_data: dict, **meta_kwargs) -> Path:
    """Write results/rev.json."""
    obj = {"meta": provenance(**meta_kwargs), **rev_data, "headline_cl": 0.1}
    path = RESULTS / "rev.json"
    _write_json(obj, path)
    return path


def write_reliability(rel_data: dict, **meta_kwargs) -> Path:
    """Write results/reliability.json."""
    obj = {"meta": provenance(**meta_kwargs), **rel_data}
    path = RESULTS / "reliability.json"
    _write_json(obj, path)
    return path


def write_fss_curve(fss_data: dict, **meta_kwargs) -> Path:
    """Write results/fss_curve.json."""
    obj = {"meta": provenance(**meta_kwargs), **fss_data}
    path = RESULTS / "fss_curve.json"
    _write_json(obj, path)
    return path


def write_sample_counts(counts: dict) -> Path:
    """Write results/sample_counts.json."""
    path = RESULTS / "sample_counts.json"
    _write_json(counts, path)
    return path
