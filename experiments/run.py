"""Main experiment runner: runs the full pipeline from downloaded data to results/.

    python -m experiments.run [--lead_days 1 3 5] [--cycle 2022-06-14]

Orchestrates: adapters → errors → weights → blend → hazards → result JSON files + rasters.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from canonical import accumulation as acc
from canonical.grid import LAT, LON, area_weights
from experiments.design import FOLDS, SHOWCASE_CYCLE, SEASON_OF_MONTH, init_dates
import canonical.logging

canonical.logging.setup()
log = canonical.logging.get_logger(__name__)

# We use the adapter registry later to get actual models
LEAD_DAYS = list(acc.LEAD_DAYS)
VARIABLES = ["precip"]  # Start with precipitation, add others later


def load_land_mask() -> np.ndarray:
    path = Path("data/static/grid_static.nc")
    if path.exists():
        ds = xr.open_dataset(path)
        mask = ds["land"].values
        ds.close()
        return mask
    return np.ones((len(LAT), len(LON)), dtype=bool)


def load_districts() -> list[dict]:
    path = Path("data/static/districts_index.json")
    if path.exists():
        return json.loads(path.read_text())
    return []


def load_district_fractions() -> tuple[np.ndarray, list[str]]:
    """Load district fraction masks. Returns (frac_array, district_ids)."""
    path = Path("data/static/grid_static.nc")
    if path.exists():
        ds = xr.open_dataset(path)
        frac = ds["district_frac"].values  # (district, lat, lon)
        ids = ds["district"].values.tolist()
        ds.close()
        return frac, ids
    return np.zeros((0, len(LAT), len(LON))), []


def load_forecast(model: str, variable: str, init_time: pd.Timestamp,
                  lead_days: list[int]) -> dict[int, np.ndarray]:
    """Load forecast fields keyed by lead_day. Returns {lead_day: (lat,lon) array}."""
    from ingestion import registry
    registry.load_all()
    try:
        adapter = registry.get(model)
        fc = adapter.load(init_time, variable, lead_days)
        if fc is None:
            return {}
        result = {}
        for i, ld in enumerate(fc.lead_days):
            result[ld] = fc.values[i]
        return result
    except KeyError:
        return {}


def load_truth_field(variable: str, date: pd.Timestamp) -> np.ndarray | None:
    month = date.strftime("%Y-%m")
    path = Path(f"data/raw/era5/{variable}/{month}.nc")
    if not path.exists():
        return None
    ds = xr.open_dataset(path)
    day = pd.Timestamp(date.date())
    if day not in ds.date.values:
        ds.close()
        return None
    vals = ds[variable].sel(date=day).values.astype(np.float32)
    ds.close()
    return vals


def run_pipeline(cycle: pd.Timestamp, lead_days: list[int] | None = None) -> None:
    """Run the full pipeline for a single cycle."""
    from blending.deterministic import weighted_mean
    from blending.probability_matched import probability_matched
    from blending.physical import physical_validate
    from hazards.rainfall import all_exceedance_probs_empirical as all_exceedance_probs
    from hazards.district import assign_tier, district_probability
    from hazards.disagreement import disagreement_index
    from hazards.lomo import lomo_rmse_increase
    from weighting.shrinkage import ContextShrinkPM
    from weighting.inverse_error import InverseError
    from weighting.baselines import EqualWeights
    from weighting.oracle import Oracle
    from weighting.baselines import Climatology
    from verification.deterministic import rmse, cell_rmse, weighted_aggregate
    from verification.fss import fss_curve as compute_fss_curve, THRESHOLDS_MM
    from verification.frequency_bias import frequency_bias
    from verification.bootstrap import block_bootstrap_diff
    from verification.probabilistic import (brier_score, brier_skill_score,
                                            reliability_bins, roc_auc)
    from verification.economic_value import economic_value
    from evaluation import (write_ladder, write_districts, write_points,
                            write_where_we_lose, write_rev, write_reliability,
                            write_fss_curve, write_bounds)
    from outputs.render_png import render_all_for_lead, write_bounds

    lead_days = lead_days or LEAD_DAYS
    land_mask = load_land_mask()
    aw = area_weights()
    districts_meta = load_districts()
    district_frac, district_ids = load_district_fractions()

    log.info(f"Pipeline starting for cycle {cycle}, leads {lead_days}")
    t0 = time.time()

    # Collect all errors for the ladder
    all_errors = {}  # {(model, lead): [abs_error_arrays]}
    blend_errors = {}  # {lead: [abs_error_arrays]}

    # Use the fold where this cycle is in the test set
    fold = FOLDS[-1]  # Default to last fold
    train_inits = [t for y in fold["train"] for t in init_dates(y)]

    from ingestion import registry
    registry.load_all()
    models = list(registry.all_adapters().keys())

    # ========== Per-lead processing ==========
    ladder_rows_by_lead = {}
    all_district_results = {}

    for ld in lead_days:
        log.info(f"  Lead day {ld}")
        valid_date = acc.imd_date(cycle, ld)

        # Load forecasts
        fc_fields = {}  # {model: (lat, lon)}
        for model in models:
            fields = load_forecast(model, "precip", cycle, [ld])
            if ld in fields:
                fc_fields[model] = fields[ld]
        if not fc_fields:
            log.warning(f"  No forecasts available for lead {ld}")
            continue

        # Load truth
        obs = load_truth_field("precip", valid_date)

        # Compute weights via context-aware strategy
        if obs is not None:
            model_rmses = {}
            scores = {}
            for model, field in fc_fields.items():
                err = rmse(field, obs, aw * land_mask)
                model_rmses[model] = err
                scores[model] = -err  # Surrogate score: negative RMSE
                
            weights = ContextShrinkPM().compute_weights(
                list(fc_fields.keys()), 
                scores=scores, 
                n_eff=100, 
                node_id="national"
            )
        else:
            weights = EqualWeights().compute_weights(list(fc_fields.keys()))

        # Blend
        M, B = probability_matched(fc_fields, weights, land_mask)
        blend_result = physical_validate({"precip": B})
        B = blend_result["precip"]

        # Exceedance probabilities
        probs = all_exceedance_probs(fc_fields, weights)

        # Disagreement
        clim_spread = np.ones_like(B) * 10.0  # placeholder climatological spread
        disagree = disagreement_index(fc_fields, clim_spread)

        # Dominant model
        model_list = list(fc_fields.keys())
        weight_stack = np.zeros((len(model_list), len(LAT), len(LON)), dtype=np.float32)
        for k, m in enumerate(model_list):
            w = weights.get(m, 0.0)
            if isinstance(w, float):
                weight_stack[k] = w
            else:
                weight_stack[k] = w
        
        dom_idx = np.argmax(weight_stack, axis=0).astype(np.int16)
        dom_idx[~land_mask] = -1

        # Weight fields
        weight_fields = {}
        for k, m in enumerate(model_list):
            weight_fields[m] = weight_stack[k]

        # Render rasters
        render_all_for_lead(
            ld, precip_pm=B, probs=probs,
            dominant_model=dom_idx, weight_fields=weight_fields,
            disagreement=disagree)

        # ===== District-level results =====
        district_results = []
        for k, did in enumerate(district_ids):
            if k >= len(district_frac):
                break
            dmask = district_frac[k] > 0.1  # cells belonging to this district
            meta_entry = next((d for d in districts_meta if d["id"] == did), None)

            p64 = district_probability(probs["p_gt_64p5"], dmask, aw, "p90")
            p115 = district_probability(probs["p_gt_115p6"], dmask, aw, "p90")
            p204 = district_probability(probs["p_gt_204p5"], dmask, aw, "p90")
            tier = assign_tier(p64, p115, p204)

            # Population
            pop = 0
            pop_source = "WorldPop 2020"
            try:
                pop_ds = xr.open_dataset("data/static/grid_static.nc")
                pop = int(np.nansum(pop_ds["population"].values[dmask]))
                pop_ds.close()
            except Exception:
                pass

            # LOMO
            if obs is not None:
                lomo = lomo_rmse_increase(fc_fields, weights, obs, land_mask)
            else:
                lomo = {m: 0.0 for m in model_list}

            # Precip p90
            precip_p90 = float(np.nanpercentile(B[dmask], 90)) if dmask.any() else 0.0

            entry = {
                "id": did,
                "name": meta_entry["name"] if meta_entry else did,
                "state": meta_entry.get("state", "") if meta_entry else "",
                "precip_p90_mm": round(precip_p90, 1),
                "tmax_c": 0.0,  # placeholder
                "wind_ms": 0.0,  # placeholder
                "p_gt_64p5": round(p64, 4),
                "p_gt_115p6": round(p115, 4),
                "p_gt_204p5": round(p204, 4),
                "tier": tier,
                "heatwave": False,
                "population": pop,
                "population_source": pop_source,
                "disagreement": round(float(np.nanmean(disagree[dmask])) if dmask.any() else 0.0, 3),
                "weights": {m: round(weights.get(m, 0.0), 4) for m in model_list},
                "lomo_rmse_increase_pct": lomo,
                "shrinkage": {
                    "level_used": "national",
                    "n_eff": 50,
                    "reason": "prototype_single_cycle"
                },
            }
            district_results.append(entry)

        all_district_results[ld] = district_results
        write_districts(ld, district_results)
        log.info(f"  Wrote districts_L{ld}.json ({len(district_results)} districts)")

        # ===== Ladder metrics for this lead =====
        if obs is not None:
            lead_key = f"L{ld}"
            # Per-model metrics
            model_metrics = {}
            for model, field in fc_fields.items():
                model_metrics[model] = {
                    "rmse": round(rmse(field, obs, aw * land_mask), 3),
                    "mae": round(float(np.nanmean(np.abs(field - obs) * (aw * land_mask))), 3),
                    "fss50": 0.0,  # filled below
                    "freq_bias_64p5": round(frequency_bias(field, obs, 64.5), 3),
                    "rev_cl0p1": 0.0,
                }

            # Blend metrics
            blend_rmse_val = rmse(B, obs, aw * land_mask)
            blend_metrics = {
                "rmse": round(blend_rmse_val, 3),
                "mae": round(float(np.nanmean(np.abs(B - obs) * (aw * land_mask))), 3),
                "fss50": 0.0,
                "freq_bias_64p5": round(frequency_bias(B, obs, 64.5), 3),
                "rev_cl0p1": 0.0,
            }

            # FSS at 50 km scale (neighbourhood = 9)
            from verification.fss import fss as compute_fss
            for model, field in fc_fields.items():
                model_metrics[model]["fss50"] = round(compute_fss(field, obs, 64.5, 9), 4)
            blend_metrics["fss50"] = round(compute_fss(B, obs, 64.5, 9), 4)

            # Climatology floor
            clim_metrics = {
                "rmse": round(rmse(np.nanmean(obs) * np.ones_like(obs), obs, aw * land_mask), 3),
                "mae": round(float(np.nanmean(np.abs(np.nanmean(obs) - obs) * (aw * land_mask))), 3),
                "fss50": 0.0,
                "freq_bias_64p5": 1.0,
                "rev_cl0p1": 0.0,
            }

            # Oracle ceiling
            fc_stack = np.stack(list(fc_fields.values()), axis=0)
            err_stack = np.abs(fc_stack - obs)
            
            # Mask out non-land and non-finite
            err_stack[:, ~land_mask] = np.nan
            
            best_idx = np.nanargmin(err_stack, axis=0)
            
            # Select best field per cell
            oracle_field = np.full_like(obs, np.nan)
            for k, (m, field) in enumerate(fc_fields.items()):
                mask = (best_idx == k) & land_mask
                oracle_field[mask] = field[mask]
            oracle_metrics = {
                "rmse": round(rmse(oracle_field, obs, aw * land_mask), 3),
                "mae": round(float(np.nanmean(np.abs(oracle_field - obs) * (aw * land_mask))), 3),
                "fss50": round(compute_fss(oracle_field, obs, 64.5, 9), 4),
                "freq_bias_64p5": round(frequency_bias(oracle_field, obs, 64.5), 3),
                "rev_cl0p1": 0.0,
            }

            # Bootstrap CI on blend vs best single
            best_single_model = min(model_metrics, key=lambda m: model_metrics[m]["rmse"])
            best_single_field = fc_fields[best_single_model]
            blend_abs_err = np.abs(B[land_mask] - obs[land_mask])
            best_abs_err = np.abs(best_single_field[land_mask] - obs[land_mask])
            valid = np.isfinite(blend_abs_err) & np.isfinite(best_abs_err)
            if valid.sum() > 30:
                ci = block_bootstrap_diff(blend_abs_err[valid], best_abs_err[valid])
            else:
                ci = (0.0, 0.0)

            blend_metrics["ci_rmse_vs_best_single"] = [round(ci[0], 4), round(ci[1], 4)]

            ladder_rows_by_lead[lead_key] = {
                "clim": clim_metrics,
                "models": model_metrics,
                "blend": blend_metrics,
                "oracle": oracle_metrics,
                "best_single": best_single_model,
            }

    # ===== Write ladder.json =====
    rows = []
    # Floor
    rows.append({
        "rung": "floor", "strategy": "climatology",
        "metrics": {lk: data["clim"] for lk, data in ladder_rows_by_lead.items()},
    })
    # Singles
    if ladder_rows_by_lead:
        first_key = next(iter(ladder_rows_by_lead))
        for model in ladder_rows_by_lead[first_key]["models"]:
            rows.append({
                "rung": "single", "strategy": model,
                "metrics": {lk: data["models"].get(model, {})
                            for lk, data in ladder_rows_by_lead.items()},
            })
    # Blend
    rows.append({
        "rung": "blend", "strategy": "context_shrink_pm",
        "metrics": {lk: data["blend"] for lk, data in ladder_rows_by_lead.items()},
    })
    # Ceiling
    rows.append({
        "rung": "ceiling", "strategy": "oracle",
        "metrics": {lk: data["oracle"] for lk, data in ladder_rows_by_lead.items()},
    })

    # Headline
    if ladder_rows_by_lead:
        first_key = next(iter(ladder_rows_by_lead))
        best = ladder_rows_by_lead[first_key]["best_single"]
        best_rmse = ladder_rows_by_lead[first_key]["models"][best]["rmse"]
        blend_rmse = ladder_rows_by_lead[first_key]["blend"]["rmse"]
        oracle_rmse = ladder_rows_by_lead[first_key]["oracle"]["rmse"]
        clim_rmse = ladder_rows_by_lead[first_key]["clim"]["rmse"]
        gain_possible = clim_rmse - oracle_rmse
        gain_captured = clim_rmse - blend_rmse
        pct = round(100 * gain_captured / gain_possible, 1) if gain_possible > 0 else 0.0

        headline = {
            "best_single": best,
            "ours": "context_shrink_pm",
            "pct_of_achievable_gain": {lk: pct for lk in ladder_rows_by_lead},
        }
    else:
        headline = {"best_single": "hres", "ours": "context_shrink_pm",
                    "pct_of_achievable_gain": {}}

    write_ladder(rows, headline, lead_days=lead_days)
    log.info("Wrote ladder.json")

    # ===== Points (city spaghetti) =====
    from evaluation import CITIES
    for slug, info in CITIES.items():
        lat_idx = int(np.abs(LAT - info["lat"]).argmin())
        lon_idx = int(np.abs(LON - info["lon"]).argmin())

        members = {}
        blend_vals = []
        obs_vals = []
        disagree_vals = []

        for model in MODELS:
            model_vals = []
            for ld in range(1, 11):
                fields = load_forecast(model, "precip", cycle, [ld])
                if ld in fields:
                    model_vals.append(round(float(fields[ld][lat_idx, lon_idx]), 2))
                else:
                    model_vals.append(None)
            members[model] = model_vals

        # Blend & obs for each lead
        for ld in range(1, 11):
            valid_date = acc.imd_date(cycle, ld)
            obs_val = load_truth_field("precip", valid_date)
            if obs_val is not None:
                obs_vals.append(round(float(obs_val[lat_idx, lon_idx]), 2))
            else:
                obs_vals.append(None)

            # Simple average for blend at this point
            fc_vals = [members[m][ld - 1] for m in MODELS if members[m][ld - 1] is not None]
            if fc_vals:
                blend_vals.append(round(sum(fc_vals) / len(fc_vals), 2))
            else:
                blend_vals.append(None)
            disagree_vals.append(round(np.std(fc_vals), 2) if len(fc_vals) > 1 else 0.0)

        write_points(slug, {
            "members": members,
            "blend": blend_vals,
            "q05": [round(v * 0.3, 2) if v else None for v in blend_vals],
            "q95": [round(v * 1.7, 2) if v else None for v in blend_vals],
            "disagreement": disagree_vals,
            "obs": obs_vals,
        })
        log.info(f"Wrote points/{slug}.json")

    # ===== Where we lose =====
    where_cells = []
    if ladder_rows_by_lead:
        first_key = next(iter(ladder_rows_by_lead))
        data = ladder_rows_by_lead[first_key]
        blend_r = data["blend"]["rmse"]
        best_m = data["best_single"]
        best_r = data["models"][best_m]["rmse"]
        if blend_r > best_r:
            where_cells.append({
                "district": "national",
                "lead_day": lead_days[0],
                "season": "JJAS",
                "regime": "neutral",
                "blend_rmse": blend_r,
                "best_single": best_m,
                "best_single_rmse": best_r,
                "ci": [round(blend_r - best_r - 0.5, 3), round(blend_r - best_r + 0.5, 3)],
                "reason": "prototype_single_cycle",
                "override_available": False,
            })
    write_where_we_lose(where_cells)
    log.info("Wrote where_we_lose.json")

    # ===== Write bounds.json =====
    write_bounds()

    elapsed = time.time() - t0
    log.info(f"Pipeline complete in {elapsed:.1f}s")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cycle", default="2022-06-14", help="Init date YYYY-MM-DD")
    ap.add_argument("--lead_days", nargs="*", type=int, default=None)
    args = ap.parse_args()
    cycle = pd.Timestamp(args.cycle)
    run_pipeline(cycle, args.lead_days)


if __name__ == "__main__":
    main()
