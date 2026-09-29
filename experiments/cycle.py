"""One forecast cycle with frozen weights: ingest -> QC -> blend -> calibrate -> hazards -> products.

    python -m experiments.cycle --cycle 2022-06-14

This is the operational path. It reads model forecasts through the adapter registry and
the artifacts frozen by experiments.evaluate (weights, calibrators, quantile tables). It
never reads an observation: a cycle can be produced before its verifying truth exists.
A model that is missing or fails the quality gate is dropped for that cycle, the weights
of the remaining models are renormalised, and the reason is written to the products.
Verification against truth is appended afterwards by experiments.run.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

import canonical.logging
from blending.physical import physical_validate
from blending.probability_matched import probability_matched
from calibration.isotonic import apply_calibration
from canonical import accumulation as acc
from canonical.grid import LAT, LON
from canonical.quality_gate import screen_stack
from experiments import data
from experiments.evaluate import (FINAL, Frozen, load_frozen,
                                  neighbourhood_probability)
from hazards.disagreement import disagreement_index
from hazards.events import EVENTS
from regimes import detector as rg
from weighting import skill as sk

log = canonical.logging.get_logger(__name__)

VARIABLES = ("precip", "t2m", "wind")
LEVELS = {0: "national", 1: "region", 2: "district", 3: "cell"}


def load_members(init: pd.Timestamp, variable: str, lead_day: int,
                 land: np.ndarray) -> tuple[dict[str, np.ndarray], dict[str, str]]:
    """Fields that passed the quality gate, and the status of every registered model."""
    from ingestion import registry
    registry.load_all()
    need = data.DERIVED.get(variable, (variable,))
    fields, status = {}, {}
    for name, adapter in registry.all_adapters().items():
        if not all(v in adapter.variables for v in need):
            continue
        parts = []
        for v in need:
            fc = adapter.load(init, v, [lead_day])
            if fc is None or not np.isfinite(fc.sel_lead(lead_day)).any():
                parts = None
                break
            parts.append(fc.sel_lead(lead_day))
        if parts is None:
            status[name] = "missing"
            continue
        raw = parts[0] if len(parts) == 1 else np.sqrt(parts[0] ** 2 + parts[1] ** 2)
        clean, rejected, _ = screen_stack(raw[None], variable, land)
        if rejected:
            status[name] = f"rejected: {rejected[0]}"
            log.warning("cycle.model_rejected", model=name, variable=variable, reason=rejected[0])
            continue
        fields[name] = clean[0]
        source = getattr(adapter, "last_source", {}).get((init, need[0]))
        status[name] = "ok (grib2)" if source == "grib2" or type(adapter).__name__ == "Grib2Adapter" else "ok"
    return fields, status


def cycle_regimes(init: pd.Timestamp, lead_day: int, thresholds: np.ndarray,
                  season: int, geo: rg.Geography) -> np.ndarray:
    """Regime of every region from the rainfall forecasts of this cycle."""
    from ingestion import registry
    registry.load_all()
    fields = {}
    trained_on = set(data.models_for("precip"))   # the models the thresholds were fitted with
    for name, adapter in registry.all_adapters().items():
        if name in trained_on:
            fc = adapter.load(init, "precip", [lead_day])
            if fc is not None:
                fields[name] = fc.sel_lead(lead_day)[None]
    if not fields:
        return np.ones(geo.n_regions + 1, dtype=np.int8)
    series = rg.region_means(rg.multi_model_mean(fields), geo)
    return rg.classify(series, np.array([season]), thresholds)[0]


def forecast_variable(variable: str, init: pd.Timestamp, lead_day: int,
                      geo: rg.Geography) -> dict | None:
    fz: Frozen | None = load_frozen(variable, lead_day, init)
    if fz is None:
        log.warning("cycle.no_frozen_artifact", variable=variable, lead_day=lead_day)
        return None
    members, status = load_members(init, variable, lead_day, geo.land)
    for m in members:
        if m not in fz.models:
            # ingested and gated, but without a skill history its weight would be arbitrary
            status[m] = "no_skill_history: excluded from the blend"
            log.warning("cycle.model_without_history", model=m, variable=variable)
    members = {m: f for m, f in members.items() if m in fz.models}
    if not members:
        return None
    valid = acc.imd_date(init, lead_day)
    season = int(rg.season_index([valid])[0])
    regimes = cycle_regimes(init, lead_day, fz.regime_thresholds, season, geo)
    rmap = rg.regime_map(regimes, geo)

    nan = np.full(geo.land.shape, np.nan, np.float32)
    stack = {m: members.get(m, nan)[None] for m in fz.models}
    blend_mean, applied = sk.blend_stack(stack, fz.models, fz.weights.astype(np.float64),
                                         np.array([season]), regimes[None], geo)
    weights = {m: applied[0, i] for i, m in enumerate(fz.models)}
    blend = blend_mean[0]
    if variable == "precip":
        _, blend = probability_matched(members, {m: weights[m].astype(np.float64) for m in members},
                                       geo.land)
        blend = physical_validate({"precip": blend})["precip"]

    clim = fz.clim12[valid.month - 1]
    probs, probs_raw, decisions = {}, {}, {}
    for ev in EVENTS[variable]:
        c = fz.calibrators[ev.key]
        raw = neighbourhood_probability(stack, fz.models, applied, ev.margin, clim[None])[0]
        x = raw if c["predictor"] == "neighbourhood" else ev.margin(blend, clim)
        probs[ev.key] = apply_calibration(c["calibrator"], x)
        probs_raw[ev.key] = raw
        decisions[ev.key] = c["decision_threshold"]
    if getattr(fz, "quantile_method", "table") == "lgbm" and fz.lgbm_quantiles is not None:
        from calibration import lgbm
        lat2d, lon2d = np.meshgrid(LAT, LON, indexing="ij")
        X = lgbm.build_features(blend[None], stack, fz.models, np.array([season]), rmap[None],
                                clim[None], [valid], lat2d, lon2d)
        q = fz.lgbm_quantiles.predict(X).reshape((-1,) + geo.land.shape)
        q_levels = np.array(fz.lgbm_quantiles.levels)
        method = "LightGBM quantile regression"
    else:
        from calibration.quantiles import LEVELS as q_levels
        q = fz.quantiles.predict(blend)
        method = "empirical quantiles of training observations conditional on the blend"
    at = lambda level: q[int(np.argmin(np.abs(np.asarray(q_levels) - level)))]

    pattern = "full" if len(members) == len(fz.models) else \
        "without_" + "_".join(m for m in fz.models if m not in members)
    return {
        "variable": variable, "lead_day": lead_day, "valid": valid,
        "season": rg.SEASONS[season],
        "regimes": {n: rg.REGIMES[int(regimes[c])]
                    for c, n in enumerate(geo.region_names + ["NATIONAL"])},
        "models": list(fz.models), "members": members, "status": status,
        "availability_pattern": pattern,
        "weights": weights, "blend": blend, "blend_mean": blend_mean[0],
        "equal": rg.multi_model_mean({m: f[None] for m, f in members.items()})[0],
        "probs": probs, "probs_raw": probs_raw, "decision_thresholds": decisions,
        "q05": at(0.05), "q50": at(0.5), "q95": at(0.95), "quantile_method": method,
        "clim": clim,
        "disagreement": disagreement_index(members, fz.clim_spread[season]) if len(members) > 1
        else np.zeros(geo.land.shape, np.float32),
        "lomo_sse": fz.lomo_sse[season], "full_sse": fz.full_sse[season],
        "level_used": np.choose(rmap, [fz.level_used[season, k] for k in range(sk.K)]),
        "lam_cell": np.choose(rmap, [fz.lam_cell[season, k] for k in range(sk.K)]),
        "n_days": np.choose(rmap, [fz.n_days[season, k] for k in range(sk.K)]),
        "tau": fz.tau, "shrink_k": fz.shrink_k, "train_years": list(fz.train_years),
        "train_rmse": fz.train_rmse, "strategy": FINAL[variable],
    }


def run_cycle(init: pd.Timestamp, lead_days: list[int], geo: rg.Geography) -> dict[int, dict]:
    """{lead_day: {variable: forecast}} for every lead that has at least rainfall."""
    out = {}
    for ld in lead_days:
        per_var = {v: forecast_variable(v, init, ld, geo) for v in VARIABLES}
        per_var = {v: f for v, f in per_var.items() if f is not None}
        if "precip" in per_var:
            out[ld] = per_var
    return out


# ───────────────────────── district aggregation ─────────────────────────

class Districts:
    """Cells and area weights of every district on the canonical grid."""

    def __init__(self, geo: rg.Geography, min_frac: float = 0.1):
        with xr.open_dataset("data/static/grid_static.nc") as ds:
            frac = ds["district_frac"].values
            self.population = ds["population"].values
            self.ids = ds["district"].values.tolist()
        meta = json.loads(Path("data/static/districts_index.json").read_text())
        self.meta = {d["id"]: d for d in meta}
        self.cells, self.w = [], []
        for k in range(len(self.ids)):
            ii, jj = np.where(frac[k] > min_frac)
            if ii.size == 0:
                i, j = np.unravel_index(frac[k].argmax(), frac[k].shape)
                ii, jj = np.array([i]), np.array([j])
            self.cells.append((ii, jj))
            self.w.append(frac[k][ii, jj] * geo.aw[ii, jj])

    def mean(self, field: np.ndarray, k: int) -> float:
        v = field[self.cells[k]]
        ok = np.isfinite(v)
        return float(np.average(v[ok], weights=self.w[k][ok])) if ok.any() else float("nan")

    def quantile(self, field: np.ndarray, k: int, q: float = 0.9) -> float:
        v, w = field[self.cells[k]], self.w[k]
        ok = np.isfinite(v)
        if not ok.any():
            return float("nan")
        v, w = v[ok], w[ok]
        order = np.argsort(v)
        cum = np.cumsum(w[order]) / w[order].sum()
        return float(v[order][min(np.searchsorted(cum, q), v.size - 1)])

    def total(self, field: np.ndarray, k: int) -> float:
        return float(np.nansum(field[self.cells[k]]))

    def mode(self, field: np.ndarray, k: int) -> int:
        return int(np.bincount(field[self.cells[k]].astype(int)).argmax())


def _r(x: float, n: int = 3):
    return round(float(x), n) if np.isfinite(x) else None


def district_records(fc: dict, districts: Districts) -> list[dict]:
    """One record per district from the forecasts of one lead day."""
    from hazards.district import assign_tier

    rain, heat, wind = fc["precip"], fc.get("t2m"), fc.get("wind")
    thr = rain["decision_thresholds"]
    out = []
    for k, did in enumerate(districts.ids):
        meta = districts.meta.get(did, {})
        p = {key: districts.quantile(rain["probs"][key], k) for key in rain["probs"]}
        tier = assign_tier(p["p_gt_64p5"], p["p_gt_115p6"], p["p_gt_204p5"], thr)
        full = districts.mean(rain["full_sse"], k)
        lomo = {}
        for i, m in enumerate(rain["models"]):
            drop = districts.mean(rain["lomo_sse"][i], k)
            lomo[m] = _r(100.0 * (np.sqrt(drop / full) - 1.0), 1) if full > 0 else None
        level = districts.mode(rain["level_used"], k)
        n_days = int(np.round(districts.mean(rain["n_days"].astype(float), k)))
        rec = {
            "id": did,
            "name": meta.get("name", did),
            "state": meta.get("state", ""),
            "region": meta.get("region", ""),
            "precip_p90_mm": _r(districts.quantile(rain["blend"], k), 1),
            # predictive interval, aggregated like precip_p90_mm (district 90th percentile cell)
            "precip_q05_mm": _r(districts.quantile(rain["q05"], k), 1),
            "precip_q50_mm": _r(districts.quantile(rain["q50"], k), 1),
            "precip_q95_mm": _r(districts.quantile(rain["q95"], k), 1),
            "p_gt_64p5": _r(p["p_gt_64p5"], 4),
            "p_gt_115p6": _r(p["p_gt_115p6"], 4),
            "p_gt_204p5": _r(p["p_gt_204p5"], 4),
            "tier": tier,
            "population": int(districts.total(districts.population, k)),
            "population_source": "WorldPop 2020",
            "disagreement": _r(districts.mean(rain["disagreement"], k)),
            "weights": {m: _r(districts.mean(w, k), 4) for m, w in rain["weights"].items()},
            "lomo_rmse_increase_pct": lomo,
            "season": rain["season"],
            "regime": rain["regimes"].get(meta.get("region", ""), rain["regimes"]["NATIONAL"]),
            "shrinkage": {
                "level_used": LEVELS[level],
                "n_eff": n_days,
                "lambda": _r(districts.mean(rain["lam_cell"], k)),
                "reason": ("cell_history" if level == 3 else f"inherited_{LEVELS[level]}_n_eff_below_min"),
            },
        }
        if heat is not None:
            t = districts.mean(heat["blend"], k)
            p_hw = districts.quantile(heat["probs"]["p_heatwave"], k)
            rec.update({
                "tmax_c": _r(t, 1),
                "t2m_anomaly_c": _r(t - districts.mean(heat["clim"], k), 1),
                "p_hot_40": _r(districts.quantile(heat["probs"]["p_hot_40"], k), 4),
                "p_heatwave": _r(p_hw, 4),
                "heatwave": bool(p_hw >= heat["decision_thresholds"]["p_heatwave"]),
                "weights_t2m": {m: _r(districts.mean(w, k), 4) for m, w in heat["weights"].items()},
            })
        else:
            rec.update({"tmax_c": None, "heatwave": False})
        if wind is not None:
            p_w = districts.quantile(wind["probs"]["p_wind_8"], k)
            rec.update({
                "wind_ms": _r(districts.quantile(wind["blend"], k), 1),
                "p_wind_8": _r(p_w, 4),
                "p_wind_10p8": _r(districts.quantile(wind["probs"]["p_wind_10p8"], k), 4),
                "high_wind": bool(p_w >= wind["decision_thresholds"]["p_wind_8"]),
                "weights_wind": {m: _r(districts.mean(w, k), 4) for m, w in wind["weights"].items()},
            })
        else:
            rec.update({"wind_ms": None, "high_wind": False})
        out.append(rec)
    return out


# ───────────────────────── products ─────────────────────────

def cycle_meta(init: pd.Timestamp, fc: dict) -> dict:
    rain = fc["precip"]
    return {
        "cycle": init.strftime("%Y-%m-%dT%HZ"),
        "models": [m for m in rain["models"] if m in rain["members"]],
        "strategy": rain["strategy"],
        "availability_pattern": rain["availability_pattern"],
        "model_status": {v: f["status"] for v, f in fc.items()},
        "train_years": rain["train_years"],
        "weights_frozen_before_cycle": True,
        "tau": {v: f["tau"] for v, f in fc.items()},
        "shrink_k": {v: f["shrink_k"] for v, f in fc.items()},
        "season": rain["season"],
        "regimes": rain["regimes"],
        "tier_probability_thresholds": rain["decision_thresholds"],
        "hazard_definitions": {e.key: e.definition for v in fc for e in EVENTS[v]},
        "temperature_definition": "2 m temperature at 12 UTC (17:30 IST), a proxy for Tmax",
        "valid_window_utc": f"{fc['precip']['valid'].strftime('%Y-%m-%d')}T03:00 +24h",
    }


def write_products(init: pd.Timestamp, forecasts: dict[int, dict], geo: rg.Geography) -> None:
    """District JSONs, rasters, NetCDF and GeoTIFF for every lead of the cycle."""
    from evaluation import provenance, write_districts
    from outputs.geotiff import write_geotiff
    from outputs.netcdf import export_cycle_netcdf
    from matplotlib.colors import ListedColormap
    from outputs.render_png import (MODEL_IDS, render_all_for_lead, render_field,
                                    render_precip, render_probability)

    districts = Districts(geo)
    datasets = {}
    for ld, fc in forecasts.items():
        rain = fc["precip"]
        meta = cycle_meta(init, fc)
        kw = dict(cycle=meta.pop("cycle"), models=meta.pop("models"), strategy=meta.pop("strategy"),
                  availability_pattern=meta.pop("availability_pattern"), **meta)
        records = district_records(fc, districts)
        write_districts(ld, records, **kw)

        # per-model and baseline rainfall, and the district tiers, for the map's selectors
        for m, f in rain["members"].items():
            render_precip(f, ld, name=f"precip_{m}")
        render_precip(rain["equal"], ld, name="precip_baseline")
        tier_of = np.array([("green", "yellow", "orange", "red").index(r["tier"]) for r in records])
        tiers = np.where(geo.district_idx >= 0, tier_of[np.maximum(geo.district_idx, 0)], np.nan)
        render_field(tiers, "tier", ld, ListedColormap(["#2E7D32", "#F9A825", "#EF6C00", "#C62828"]),
                     -0.5, 3.5)

        order = list(rain["weights"])
        wstack = np.stack([rain["weights"][m] for m in order])
        ids = np.array([MODEL_IDS.get(m, 0) for m in order])
        dominant = np.where(geo.land, ids[wstack.argmax(axis=0)], -1).astype(np.int16)
        mask = lambda f: np.where(geo.land, f, np.nan)
        render_all_for_lead(
            ld, precip_pm=rain["blend"], probs={k: mask(v) for k, v in rain["probs"].items()},
            dominant_model=dominant, weight_fields={m: mask(w) for m, w in rain["weights"].items()},
            disagreement=mask(rain["disagreement"]),
            t2m=fc["t2m"]["blend"] if "t2m" in fc else None,
            wind=fc["wind"]["blend"] if "wind" in fc else None)
        for v in ("t2m", "wind"):
            if v in fc:
                for key, p in fc[v]["probs"].items():
                    render_probability(mask(p), key, ld)

        bands = {"precip_mm": rain["blend"], "precip_q05_mm": rain["q05"], "precip_q95_mm": rain["q95"],
                 "disagreement": rain["disagreement"],
                 **{k: v for k, v in rain["probs"].items()},
                 **{f"weight_{m}": w for m, w in rain["weights"].items()}}
        for v, name in (("t2m", "t2m_12utc_degC"), ("wind", "wind_speed_ms")):
            if v in fc:
                bands[name] = fc[v]["blend"]
                bands.update(fc[v]["probs"])
        write_geotiff(bands, Path("results/products") / f"blend_{init:%Y%m%d}_L{ld}.tif",
                      tags={"cycle": kw["cycle"], "lead_day": ld, "status": "EXERCISE"})
        datasets[ld] = xr.Dataset(
            {k: (("lat", "lon"), np.asarray(v, dtype=np.float32)) for k, v in bands.items()},
            coords={"lat": LAT, "lon": LON})

    if datasets:
        first = forecasts[min(forecasts)]
        export_cycle_netcdf(datasets, f"{init:%Y%m%d}",
                            provenance(cycle=f"{init:%Y-%m-%dT%HZ}", models=first["precip"]["models"],
                                       strategy=first["precip"]["strategy"]),
                            out_dir="results/products")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cycle", required=True, help="init date YYYY-MM-DD (00 UTC)")
    ap.add_argument("--lead_days", nargs="*", type=int, default=list(acc.LEAD_DAYS))
    a = ap.parse_args()
    canonical.logging.setup()
    geo = rg.load_geography()
    init = pd.Timestamp(a.cycle)
    forecasts = run_cycle(init, a.lead_days, geo)
    if not forecasts:
        raise SystemExit("no forecast produced: run `python -m experiments.run` first to freeze "
                         "the weights, and check that model data exists for this cycle")
    write_products(init, forecasts, geo)
    log.info("cycle.done", cycle=str(init.date()), leads=sorted(forecasts))


if __name__ == "__main__":
    main()
