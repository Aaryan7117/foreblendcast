"""Main experiment runner: runs the full pipeline from downloaded data to results/.

    python -m experiments.run [--lead_days 1 3 5] [--cycle 2022-06-14] [--variables precip t2m wind]

Two stages, in this order:

  A. Held-out evaluation (experiments.evaluate). For every variable, lead and fold the
     weights are learned from earlier years, frozen, applied to the test year and only
     then verified. Writes the ladder, ablation, reliability, REV, FSS and
     where-we-lose files.
  B. Showcase cycle (experiments.cycle). The operational path with the frozen weights
     produces districts, rasters, NetCDF and GeoTIFF. Truth is appended afterwards for
     display only.
"""
from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path

import numpy as np
import pandas as pd

import canonical.logging
from canonical import accumulation as acc
from canonical.grid import LAT, LON
from experiments import cycle as cyc
from experiments import data
from experiments.design import FOLDS, SEASONS, TEST_YEARS
from experiments.evaluate import FINAL, LeadResult, evaluate
from hazards.events import EVENTS, HEADLINE_EVENT
from regimes import detector as rg
from verification.bootstrap import block_bootstrap_rmse_diff
from verification.economic_value import economic_value, rev_at, rev_from_counts
from verification.fss import (HEADLINE_NEIGHBOURHOOD, KM_PER_CELL, NEIGHBOURHOODS,
                              SCALES_KM, THRESHOLDS_MM, fss_from_parts)
from verification.probabilistic import (brier_score, brier_skill_score,
                                        reliability_bins, roc_auc)

log = canonical.logging.get_logger(__name__)

LEAD_DAYS = list(acc.LEAD_DAYS)
VARIABLES = ["precip", "t2m", "wind"]
RESULTS = Path("results")
REGION_LABEL = {"NW": "Northwest India", "CENTRAL": "Central India", "SOUTH": "South Peninsula",
                "EAST_NE": "East & Northeast India"}
MIN_CONTEXT_DAYS = 15
UNITS = {"precip": "mm", "t2m": "degC", "wind": "m/s"}


def _r(x, n=3):
    return round(float(x), n) if x is not None and np.isfinite(x) else None


# ───────────────────────── pooling over folds ─────────────────────────

def cat(results: list[LeadResult], strategy: str, key: str) -> np.ndarray:
    return np.concatenate([r.daily[strategy][key] for r in results if strategy in r.daily])


def strategy_names(results: list[LeadResult]) -> list[str]:
    names = []
    for r in results:
        names += [n for n in r.daily if n not in names]
    return names


def pooled_prob(results: list[LeadResult], event: str, pred: str) -> tuple[np.ndarray, np.ndarray]:
    return (np.concatenate([r.prob[event]["preds"][pred] for r in results]),
            np.concatenate([r.prob[event]["obs"] for r in results]))


def metrics(results: list[LeadResult], strategy: str, variable: str) -> dict:
    event = HEADLINE_EVENT[variable]
    mse = cat(results, strategy, "mse")
    fc_yes, ob_yes, hits, n = (sum(r.freq[strategy][event][i] for r in results) for i in range(4))
    out = {
        "rmse": _r(np.sqrt(np.nanmean(mse))),
        "mae": _r(np.nanmean(cat(results, strategy, "mae"))),
        "bias": _r(np.nanmean(cat(results, strategy, "bias"))),
        "n_days": int(np.isfinite(mse).sum()),
        "freq_bias": _r(fc_yes / ob_yes) if ob_yes else None,
        "rev_cl0p1": _r(rev_from_counts(hits, fc_yes - hits, ob_yes - hits, n), 4),
        "brier": _r((fc_yes + ob_yes - 2 * hits) / n, 6) if n else None,
    }
    if variable == "precip":
        num, ref = (sum(r.fss[strategy][(64.5, HEADLINE_NEIGHBOURHOOD)][i] for r in results)
                    for i in range(2))
        out["fss"] = _r(fss_from_parts(num, ref), 4)
        # legacy key names read by the dashboard and the mobile app
        out["fss50"] = out["fss"]
        out["freq_bias_64p5"] = out["freq_bias"]
    return out


def ci_vs(results: list[LeadResult], strategy: str, reference: str) -> list:
    lo, hi = block_bootstrap_rmse_diff(cat(results, strategy, "mse"), cat(results, reference, "mse"))
    return [_r(lo, 4), _r(hi, 4)]


# ───────────────────────── ladder and ablation ─────────────────────────

def rungs(variable: str, models: list[str]) -> list[tuple[str, str]]:
    final = FINAL[variable]
    rows = [("floor", "climatology"), ("floor", "persistence"),
            ("baseline", "equal_weight"), ("baseline", "inverse_error"),
            ("baseline", "best_single_train")]
    rows += [("single", m) for m in models]
    rows.append(("ablation", "context"))
    rows.append(("ablation", "lgbm_blend"))
    if final != "context_shrink":
        rows.append(("blend", "context_shrink"))
    rows += [("blend", final), ("ceiling", "oracle")]
    return rows


def build_ladder(by_lead: dict[int, list[LeadResult]], variable: str) -> tuple[list, dict, dict]:
    final = FINAL[variable]
    event = HEADLINE_EVENT[variable]
    models = by_lead[min(by_lead)][-1].models
    rows = []
    for rung, name in rungs(variable, models):
        row = {"rung": rung, "strategy": name, "metrics": {}}
        for ld, results in by_lead.items():
            if name not in strategy_names(results):
                continue
            m = metrics(results, name, variable)
            if name in ("context_shrink", final):
                m["ci_rmse_vs_best_single"] = ci_vs(results, name, "best_single_train")
                m["ci_rmse_vs_equal_weight"] = ci_vs(results, name, "equal_weight")
            if name == final:
                p, o = pooled_prob(results, event, "calibrated")
                m["rev_cl0p1"] = _r(rev_at(p, o), 4)
                m["brier"] = _r(brier_score(p, o), 6)
            elif name == "equal_weight":
                p, o = pooled_prob(results, event, "equal_raw")
                m["rev_cl0p1"] = _r(rev_at(p, o), 4)
                m["brier"] = _r(brier_score(p, o), 6)
            row["metrics"][f"L{ld}"] = m
        rows.append(row)

    by_name = {r["strategy"]: r["metrics"] for r in rows}
    gain, vs_equal, vs_best = {}, {}, {}
    for ld in by_lead:
        k = f"L{ld}"
        best, ours = by_name["best_single_train"][k]["rmse"], by_name["context_shrink"][k]["rmse"]
        orc, eq = by_name["oracle"][k]["rmse"], by_name["equal_weight"][k]["rmse"]
        gain[k] = _r(100 * (best - ours) / (best - orc), 1) if best > orc else 0.0
        vs_equal[k] = _r(100 * (ours - eq) / eq, 2)
        vs_best[k] = _r(100 * (ours - best) / best, 2)
    latest = {ld: rs[-1] for ld, rs in by_lead.items()}
    headline = {
        "best_single": latest[min(latest)].best_single,
        "best_single_by_fold": {f"L{ld}": {str(r.test_year): r.best_single for r in rs}
                                for ld, rs in by_lead.items()},
        "best_single_selection": "lowest RMSE on the training years of each fold",
        "ours": final,
        "rmse_strategy": "context_shrink",
        "pct_of_achievable_gain": gain,
        "rmse_change_vs_equal_weight_pct": vs_equal,
        "rmse_change_vs_best_single_pct": vs_best,
        "test_years": list(TEST_YEARS),
        "total_test_days": {f"L{ld}": sum(r.n_test for r in rs) for ld, rs in by_lead.items()},
    }
    extra = {
        "units": UNITS[variable],
        "headline_event": event,
        "fss_neighbourhood_cells": HEADLINE_NEIGHBOURHOOD,
        "fss_scale_km": int(round(HEADLINE_NEIGHBOURHOOD * KM_PER_CELL)),
        "folds": [{"train": list(f["train"]), "test": f["test"]} for f in FOLDS],
        "fitted": {f"L{ld}": [{"test_year": r.test_year, "tau": r.tau, "shrink_k": r.shrink_k,
                                "n_train": r.n_train, "n_test": r.n_test,
                                "train_rmse": {m: _r(v) for m, v in r.train_rmse.items()},
                                "days_without_model": r.missing}
                               for r in rs] for ld, rs in by_lead.items()},
    }
    return rows, headline, extra


def crps_of(results: list[LeadResult], name: str) -> float:
    s = sum(r.crps[name][0] for r in results)
    w = sum(r.crps[name][1] for r in results)
    return s / w if w else float("nan")


def build_ablation(by_lead: dict[int, list[LeadResult]], variable: str, ladder_rows: list) -> dict:
    """Each step adds one component. Deterministic steps are scored by RMSE/MAE,
    probabilistic ones by CRPS and the Brier score of the headline event."""
    event = HEADLINE_EVENT[variable]
    by_name = {r["strategy"]: r["metrics"] for r in ladder_rows}
    steps = ["equal_weight", "inverse_error", "context", "context_shrink"]
    if variable == "precip":
        steps.append("context_shrink_pm")
    labels = {"equal_weight": "Equal-weight mean", "inverse_error": "+ inverse-error weights",
              "context": "+ context (region, season, lead, regime)",
              "context_shrink": "+ hierarchical shrinkage and smoothing",
              "context_shrink_pm": "+ probability matching"}
    out = {}
    for ld, results in by_lead.items():
        k = f"L{ld}"
        rows, prev = [], None
        for s in steps:
            m = by_name[s][k]
            rows.append({"step": labels[s], "strategy": s, "rmse": m["rmse"], "mae": m["mae"],
                         "bias": m["bias"], "fss": m.get("fss"), "freq_bias": m["freq_bias"],
                         "rmse_change_vs_previous_pct":
                             _r(100 * (m["rmse"] - prev) / prev, 2) if prev else None})
            prev = m["rmse"]
        ml = by_name["lgbm_blend"][k]
        learned = {"strategy": "lgbm_blend", "rmse": ml["rmse"], "mae": ml["mae"], "bias": ml["bias"],
                   "fss": ml.get("fss"), "freq_bias": ml["freq_bias"],
                   "rmse_change_vs_context_shrink_pct":
                       _r(100 * (ml["rmse"] - by_name["context_shrink"][k]["rmse"])
                          / by_name["context_shrink"][k]["rmse"], 2),
                   "note": "LightGBM regression on the blend, the members and the context; "
                           "an alternative to the weights, not a step on top of them"}
        brier = {}
        for pred in ("equal_raw", "raw", "calibrated"):
            p, o = pooled_prob(results, event, pred)
            brier[pred] = _r(brier_score(p, o), 6)
        crps = {n: _r(crps_of(results, n), 4) for n in results[0].crps}
        cov = sum(r.coverage90[0] for r in results) / max(sum(r.coverage90[1] for r in results), 1)
        out[k] = {
            "deterministic": rows,
            "learned_blend": learned,
            "probabilistic": {
                "event": event,
                "brier": {"equal_weight_members": brier["equal_raw"],
                          "adaptive_weights_members": brier["raw"],
                          "adaptive_weights_calibrated": brier["calibrated"]},
                "crps": {"equal_weight_3_member_ensemble": crps["raw_ensemble"],
                         "deterministic_blend_mae": crps["blend_deterministic"],
                         "equal_weight_with_quantiles": crps["equal_dressed"],
                         "adaptive_blend_with_quantiles": crps["blend_dressed"]},
                "crps_change_vs_equal_weight_pct":
                    _r(100 * (crps["blend_dressed"] - crps["equal_dressed"]) / crps["equal_dressed"], 2),
                "crps_change_vs_raw_ensemble_pct":
                    _r(100 * (crps["blend_dressed"] - crps["raw_ensemble"]) / crps["raw_ensemble"], 2),
                "interval_90_coverage": _r(cov, 4),
                "quantile_methods": {
                    "selected": results[-1].quantile_method,
                    "selected_by": "cross-validated pinball loss inside the training years",
                    "selected_by_fold": {str(r.test_year): r.quantile_method for r in results},
                    "train_cv_pinball": {str(r.test_year): {k: _r(v, 4) for k, v in
                                                            r.quantile_cv_pinball.items()}
                                         for r in results},
                    "test_crps_7_levels": {"quantile_table": crps["blend_table_7_levels"],
                                           "lightgbm": crps["blend_lgbm_7_levels"]},
                    "test_interval_90_coverage": {
                        "quantile_table": _r(cov, 4),
                        "lightgbm": _r(sum(r.coverage90_lgbm[0] for r in results)
                                       / max(sum(r.coverage90_lgbm[1] for r in results), 1), 4)},
                    "test_crps_change_lightgbm_vs_table_pct":
                        _r(100 * (crps["blend_lgbm_7_levels"] - crps["blend_table_7_levels"])
                           / crps["blend_table_7_levels"], 2),
                    "lightgbm_feature_importance": results[-1].lgbm_importance,
                },
                "selected_interval_90_coverage": _r(
                    sum((r.coverage90_lgbm if r.quantile_method == "lgbm" else r.coverage90)[0]
                        for r in results)
                    / max(sum(r.coverage90[1] for r in results), 1), 4),
                "crps_note": "Quantile CRPS is twice the mean pinball loss over 19 levels; the "
                             "ensemble CRPS uses the exact small-ensemble formula.",
            },
        }
    return out


# ───────────────────────── probabilistic products ─────────────────────────

def build_reliability(by_lead: dict[int, list[LeadResult]], variable: str) -> dict:
    out = {}
    for ev in EVENTS[variable]:
        out[ev.key] = {"label": ev.label, "definition": ev.definition, "leads": {}}
        for ld, results in by_lead.items():
            base_train = float(np.mean([r.prob[ev.key]["base_rate_train"] for r in results]))
            entry = {"predictor": results[-1].prob[ev.key]["predictor"],
                     "decision_threshold": results[-1].prob[ev.key]["decision_threshold"],
                     "base_rate_train": _r(base_train, 6), "curves": {}}
            for pred, label in (("equal_raw", "equal_weight"), ("raw", "blend_raw"),
                                ("calibrated", "blend_calibrated")):
                p, o = pooled_prob(results, ev.key, pred)
                entry["base_rate_test"] = _r(float(o.mean()), 6)
                entry["n"] = int(o.size)
                entry["curves"][label] = {
                    **reliability_bins(p, o),
                    "brier": _r(brier_score(p, o), 6),
                    "bss_vs_train_climatology": _r(brier_skill_score(p, o, base_train), 4),
                    "auc": _r(roc_auc(p, o), 4),
                }
            out[ev.key]["leads"][f"L{ld}"] = entry
    return out


def build_rev(by_lead: dict[int, list[LeadResult]], variable: str) -> dict:
    event = HEADLINE_EVENT[variable]
    leads = {}
    for ld, results in by_lead.items():
        curves = {}
        for pred, label in (("equal_raw", "equal_weight"), ("raw", "blend_raw"),
                            ("calibrated", "blend_calibrated")):
            p, o = pooled_prob(results, event, pred)
            ev = economic_value(p, o)
            curves[label] = ev["rev"]
        leads[f"L{ld}"] = {"cost_loss": ev["cost_loss"], "curves": curves}
    first = leads[f"L{min(by_lead)}"]
    return {"event": event, "cost_loss": first["cost_loss"],
            "rev": first["curves"]["blend_calibrated"], "curves": first["curves"],
            "headline_cl": 0.1, "leads": leads}


def build_fss_curve(by_lead: dict[int, list[LeadResult]]) -> dict:
    def entries(results, strategy):
        out = []
        for t in THRESHOLDS_MM:
            scores = []
            for n in NEIGHBOURHOODS:
                num, ref = (sum(r.fss[strategy][(t, n)][i] for r in results) for i in range(2))
                scores.append(_r(fss_from_parts(num, ref), 4))
            ob, n_cases = (sum(r.freq[strategy].get(f"p_gt_{str(t).replace('.', 'p')}", (0, 0, 0, 0))[i]
                               for r in results) for i in (1, 3))
            f0 = ob / n_cases if n_cases and t != 15.6 else None
            out.append({"threshold_mm": t, "scales_km": list(SCALES_KM),
                        "neighbourhoods": list(NEIGHBOURHOODS), "fss": scores,
                        "f0": _r(f0, 6) if f0 is not None else 0.0,
                        "fss_useful": _r(0.5 + f0 / 2, 4) if f0 is not None else 0.5})
        return out

    final = FINAL["precip"]
    return {
        "strategy": final,
        "leads": {f"L{ld}": entries(rs, final) for ld, rs in by_lead.items()},
        "by_strategy": {s: {f"L{ld}": entries(rs, s) for ld, rs in by_lead.items()}
                        for s in ("equal_weight", "best_single_train", "context_shrink", final)},
        "note": "Pooled over every held-out test day, not a single cycle.",
    }


def build_where_we_lose(by_lead: dict[int, list[LeadResult]], geo: rg.Geography,
                        variable: str = "precip") -> tuple[list, dict]:
    """Contexts where a single model beats the blend on held-out data.

    The comparison is against the best single model of that context in hindsight, which
    is harder to beat than the training-selected best single of the ladder.
    """
    final = "context_shrink"
    cells, tested = [], 0
    nodes = geo.region_names + ["NATIONAL"]
    for ld, results in by_lead.items():
        seasons = np.concatenate([r.seasons for r in results])
        regimes = np.concatenate([r.regimes for r in results])
        models = results[-1].models
        mse = {n: cat(results, n, "region_mse") for n in [final] + models}
        for c, node in enumerate(nodes):
            for s, season in enumerate(SEASONS):
                for k, regime in [(None, "all")] + list(enumerate(rg.REGIMES)):
                    sel = seasons == s
                    if k is not None:
                        sel &= regimes[:, c] == k
                    sel &= np.isfinite(mse[final][:, c])
                    if sel.sum() < MIN_CONTEXT_DAYS:
                        continue
                    tested += 1
                    rmse = {n: float(np.sqrt(np.nanmean(v[sel, c]))) for n, v in mse.items()}
                    best = min(models, key=lambda m: rmse[m])
                    if rmse[final] <= rmse[best]:
                        continue
                    lo, hi = block_bootstrap_rmse_diff(mse[final][sel, c], mse[best][sel, c])
                    if not np.isfinite(lo):
                        continue
                    label = "All India" if node == "NATIONAL" else REGION_LABEL.get(node, node)
                    cells.append({
                        "district": label, "region": node, "lead_day": ld, "season": season,
                        "regime": regime, "variable": variable,
                        "blend_rmse": _r(rmse[final]), "best_single": best,
                        "best_single_rmse": _r(rmse[best]),
                        "loss_pct": _r(100 * (rmse[final] - rmse[best]) / rmse[best], 2),
                        "ci": [_r(lo, 4), _r(hi, 4)],
                        "significant": bool(lo > 0),
                        "n_days": int(sel.sum()),
                        "reason": (f"{best} had the lowest RMSE in {label}, {season}, regime {regime} "
                                   f"over {int(sel.sum())} held-out days; the blend was "
                                   f"{100 * (rmse[final] - rmse[best]) / rmse[best]:.1f}% worse"
                                   + ("" if lo > 0 else " (within the bootstrap noise)")),
                        "override_available": False,
                    })
    cells.sort(key=lambda c: (not c["significant"], -(c["loss_pct"] or 0)))
    summary = {"contexts_tested": tested, "contexts_lost": len(cells),
               "contexts_lost_significantly": sum(c["significant"] for c in cells),
               "blend": final, "comparison": "best single model of each context in hindsight",
               "ci": "95% moving-block bootstrap over forecast dates, RMSE(blend) - RMSE(best single)"}
    return cells, summary


def build_changepoints(variable: str, lead_day: int, geo: rg.Geography) -> dict:
    """Shifts in each model's daily error over the whole archive (monitoring only)."""
    from monitoring.change_point import detect_changepoints
    models = data.models_for(variable)
    blk = data.sample_block(models, variable, tuple(sorted({y for f in FOLDS for y in f["train"]}
                                                           | set(TEST_YEARS))), lead_day)
    out = {}
    for m, f in blk["fc"].items():
        sq = ((f - blk["obs"]) ** 2)[:, geo.land]
        ok = np.isfinite(sq).any(axis=1)
        err = np.full(sq.shape[0], np.nan)
        err[ok] = np.sqrt(np.nanmean(sq[ok], axis=1))
        z = (err[ok] - err[ok].mean()) / (err[ok].std() or 1.0)
        idx = detect_changepoints(z.tolist(), penalty=3 * np.log(max(len(z), 2)))
        dates = blk["valid"][ok]
        out[m] = {"n": int(ok.sum()), "change_points": [str(dates[i].date()) for i in idx if i < len(dates)]}
    return {"variable": variable, "lead_day": lead_day, "metric": "daily land RMSE, standardised",
            "method": "PELT, l2 cost, penalty 3 ln(n)", "models": out,
            "note": "Monitoring output. Detected shifts do not yet reset or decay the skill database."}


# ───────────────────────── verification appended to the showcase ─────────────────────────

def append_truth(init: pd.Timestamp, forecasts: dict, geo: rg.Geography, meta_kw: dict) -> None:
    """Truth for display next to the forecast. Runs after the products are written."""
    from evaluation import CITIES, write_points
    from outputs.render_png import RASTERS, _save_png

    leads = sorted(forecasts)
    obs = {ld: data.truth_for("precip", [forecasts[ld]["precip"]["valid"]])[0] for ld in leads}
    for ld in leads:
        rain = forecasts[ld]["precip"]
        o = obs[ld]
        flat = lambda f: [round(float(x), 1) if np.isfinite(x) else None for x in f.ravel()]
        raw = {
            "shape": [len(LAT), len(LON)],
            "land_mask": [int(x) for x in geo.land.ravel()],
            "obs": flat(o) if np.isfinite(o).any() else None,
            "models": {m: flat(f) for m, f in rain["members"].items()},
            "blend_weights_mean": {m: _r(float(w[geo.land].mean()), 4) for m, w in rain["weights"].items()},
        }
        RASTERS.mkdir(parents=True, exist_ok=True)
        (RASTERS / f"raw_grids_L{ld}.json").write_text(json.dumps(raw))
    if leads and np.isfinite(obs[leads[0]]).any():
        _save_png(obs[leads[0]], RASTERS / "truth.png", cmap="Blues", vmin=0, vmax=200,
                  transparent_below=1.0)

    for slug, info in CITIES.items():
        i, j = int(np.abs(LAT - info["lat"]).argmin()), int(np.abs(LON - info["lon"]).argmin())
        at = lambda f: _r(f[i, j], 2)
        rains = [forecasts[ld]["precip"] for ld in leads]
        models = rains[0]["models"]
        point = {
            "lead_days": leads,
            "members": {m: [at(r["members"][m]) if m in r["members"] else None for r in rains]
                        for m in models},
            "blend": [at(r["blend"]) for r in rains],
            "blend_mean": [at(r["blend_mean"]) for r in rains],
            "equal_weight": [at(r["equal"]) for r in rains],
            "q05": [at(r["q05"]) for r in rains],
            "q50": [at(r["q50"]) for r in rains],
            "q95": [at(r["q95"]) for r in rains],
            "quantile_method": rains[0]["quantile_method"],
            "disagreement": [at(r["disagreement"]) for r in rains],
            "weights": {m: [at(r["weights"][m]) for r in rains] for m in models},
            "obs": [at(obs[ld]) for ld in leads],
        }
        for v, key in (("t2m", "t2m_c"), ("wind", "wind_ms")):
            if all(v in forecasts[ld] for ld in leads):
                truth = [data.truth_for(v, [forecasts[ld][v]["valid"]])[0] for ld in leads]
                point[key] = {
                    "blend": [at(forecasts[ld][v]["blend"]) for ld in leads],
                    "q05": [at(forecasts[ld][v]["q05"]) for ld in leads],
                    "q95": [at(forecasts[ld][v]["q95"]) for ld in leads],
                    "members": {m: [at(forecasts[ld][v]["members"][m])
                                    if m in forecasts[ld][v]["members"] else None for ld in leads]
                                for m in forecasts[leads[0]][v]["models"]},
                    "obs": [at(t) for t in truth],
                }
        write_points(slug, point, **meta_kw)


def build_weights_explain(forecasts: dict, geo: rg.Geography) -> dict:
    """Why each model got its weight: the training skill behind the showcase weights."""
    from experiments.evaluate import load_frozen
    out = {}
    for ld, fc in forecasts.items():
        out[f"L{ld}"] = {}
        for v, f in fc.items():
            init_year = f["valid"].year
            fz = load_frozen(v, ld, pd.Timestamp(f"{init_year}-06-01"))
            regions = {}
            for r, name in enumerate(geo.region_names):
                cells = geo.region_idx == r
                aw = geo.aw[cells]
                regime = f["regimes"][name]
                skill = fz.region_skill["region"][name][f["season"]][regime]
                regions[name] = {
                    "label": REGION_LABEL.get(name, name), "season": f["season"], "regime": regime,
                    "weights_applied": {m: _r(np.average(w[cells], weights=aw), 4)
                                        for m, w in f["weights"].items()},
                    "region_weights_before_shrinkage": {m: _r(x, 4) for m, x in skill["weights"].items()},
                    "train_rmse": {m: _r(x) for m, x in skill["train_rmse"].items()},
                    "train_days": skill["train_days"],
                }
            out[f"L{ld}"][v] = {
                "national_weights_applied": {m: _r(np.average(w[geo.land], weights=geo.aw[geo.land]), 4)
                                             for m, w in f["weights"].items()},
                "national_train_rmse": {m: _r(x) for m, x in f["train_rmse"].items()},
                "tau": f["tau"], "shrink_k": f["shrink_k"], "train_years": f["train_years"],
                "model_status": f["status"], "regions": regions,
                "formula": "w ∝ exp(-(RMSE_model / mean RMSE) / tau), shrunk towards the parent "
                           "level by lambda = n_eff / (n_eff + k)",
            }
    return out


# ───────────────────────── pipeline ─────────────────────────

REPLAY = {"event": "Assam-Meghalaya extreme rainfall, June 2022",
          "target": pd.Timestamp("2022-06-16"), "states": ("Assam", "Meghalaya"), "leads": (5, 3, 1)}


def build_replay(geo: rg.Geography, districts: "cyc.Districts") -> dict | None:
    """Forecasts of one target day from three successive cycles, then its verification.

    Every step is a separate init (target - lead + 1 days) run through the operational
    path, so a step shows what was known on that day. Truth is read after all steps.
    """
    from outputs.render_png import RASTERS, _save_png, render_precip

    target, states = REPLAY["target"], REPLAY["states"]
    in_focus = np.array([districts.meta.get(d, {}).get("state") in states for d in districts.ids])
    focus = (geo.district_idx >= 0) & in_focus[np.maximum(geo.district_idx, 0)]
    steps, blends = [], {}
    for ld in REPLAY["leads"]:
        init = target - pd.Timedelta(days=ld - 1)
        fc = cyc.forecast_variable("precip", init, ld, geo)
        if fc is None:
            continue
        records = [r for r in cyc.district_records({"precip": fc}, districts) if r["state"] in states]
        render_precip(fc["blend"], ld, name="replay")
        blends[ld] = fc["blend"]
        steps.append({
            "lead_day": ld, "init": f"{init:%Y-%m-%d}", "valid": f"{target:%Y-%m-%d}",
            "raster": f"replay_L{ld}.png",
            "blend_peak_mm": _r(np.nanmax(fc["blend"][focus]), 1),
            "member_peak_mm": {m: _r(np.nanmax(f[focus]), 1) for m, f in fc["members"].items()},
            "max_p_gt_64p5": _r(np.nanmax(fc["probs"]["p_gt_64p5"][focus]), 3),
            "max_p_gt_115p6": _r(np.nanmax(fc["probs"]["p_gt_115p6"][focus]), 3),
            "mean_disagreement": _r(np.nanmean(fc["disagreement"][focus]), 2),
            "tiers": {t: sum(r["tier"] == t for r in records) for t in ("red", "orange", "yellow", "green")},
            "flagged": sorted(r["id"] for r in records if r["tier"] != "green"),
            "weights_mean": {m: _r(np.nanmean(w[focus]), 3) for m, w in fc["weights"].items()},
            "model_status": fc["status"],
        })
    if not steps:
        return None

    obs = data.truth_for("precip", [target])[0]
    verification = None
    if np.isfinite(obs).any():
        _save_png(obs, RASTERS / "replay_truth.png", cmap="Blues", vmin=0, vmax=200, transparent_below=1.0)
        ks = [k for k in range(len(districts.ids)) if in_focus[k]]
        heavy = sorted(districts.ids[k] for k in ks if districts.quantile(obs, k) >= 64.5)
        for st in steps:
            flagged = set(st["flagged"])
            hits = len(flagged & set(heavy))
            st["verification"] = {
                "hits": hits, "misses": len(heavy) - hits, "false_alarms": len(flagged) - hits,
                "rmse_mm": _r(np.sqrt(np.nanmean((blends[st["lead_day"]][focus] - obs[focus]) ** 2)), 2),
            }
            del st["flagged"]
        verification = {"raster": "replay_truth.png", "observed_peak_mm": _r(np.nanmax(obs[focus]), 1),
                        "districts_with_heavy_rain": len(heavy), "districts_in_focus": len(ks),
                        "definition": "district 90th-percentile cell of ERA5 rainfall >= 64.5 mm"}
    return {"event": REPLAY["event"], "target_date": f"{target:%Y-%m-%d}", "states": list(states),
            "steps": steps, "verification": verification,
            "note": "ERA5 on a 0.25 degree grid under-represents station extremes such as the "
                    "Cherrapunji totals of this event."}


def run_showcase(cycle: pd.Timestamp, lead_days: list[int], geo: rg.Geography) -> None:
    """STEP B: the operational path with the frozen weights, then truth for display."""
    from evaluation import write_json

    forecasts = cyc.run_cycle(cycle, lead_days, geo)
    if not forecasts:
        log.warning("pipeline.no_showcase", cycle=str(cycle.date()))
        return
    cyc.write_products(cycle, forecasts, geo)
    meta = cyc.cycle_meta(cycle, forecasts[min(forecasts)])
    kw = dict(cycle=meta.pop("cycle"), models=meta.pop("models"), strategy=meta.pop("strategy"),
              availability_pattern=meta.pop("availability_pattern"))
    append_truth(cycle, forecasts, geo, kw)
    write_json("weights_explain.json", {"leads": build_weights_explain(forecasts, geo)}, **kw)
    replay = build_replay(geo, cyc.Districts(geo))
    if replay:
        write_json("replay.json", replay, **{**kw, "cycle": f"{REPLAY['target']:%Y-%m-%d}"})
    first_lead = RESULTS / f"districts_L{min(forecasts)}.json"
    shutil.copyfile(first_lead, RESULTS / "districts_L0.json")  # outcome view of the replay


def run_pipeline(cycle: pd.Timestamp, lead_days: list[int] | None = None,
                 variables: list[str] | None = None) -> None:
    from evaluation import write_json, write_ladder, write_where_we_lose

    lead_days = lead_days or LEAD_DAYS
    variables = variables or VARIABLES
    geo = rg.load_geography()
    t0 = time.time()
    log.info("pipeline.start", cycle=str(cycle.date()), leads=lead_days, variables=variables)

    # STEP A: held-out evaluation, weights frozen before the test year is verified
    results: dict[str, dict[int, list[LeadResult]]] = {}
    latest_train = max(max(f["train"]) for f in FOLDS)
    for v in variables:
        for ld in lead_days:
            for fold in FOLDS:
                t1 = time.time()
                r = evaluate(v, fold, ld, geo, save_frozen=max(fold["train"]) == latest_train)
                if r is None:
                    log.warning("pipeline.skip", variable=v, lead_day=ld, test=fold["test"])
                    continue
                results.setdefault(v, {}).setdefault(ld, []).append(r)
                log.info("pipeline.fold", variable=v, lead_day=ld, test=fold["test"], tau=r.tau,
                         shrink_k=r.shrink_k, n_train=r.n_train, n_test=r.n_test,
                         seconds=round(time.time() - t1, 1))

    summary = {}
    for v, by_lead in results.items():
        models = by_lead[min(by_lead)][-1].models
        kw = dict(cycle=f"{cycle:%Y-%m-%dT%HZ}", models=models, strategy=FINAL[v])
        rows, headline, extra = build_ladder(by_lead, v)
        name = "ladder.json" if v == "precip" else f"ladder_{v}.json"
        write_ladder(rows, headline, variable=v, lead_days=sorted(by_lead), filename=name,
                     extra=extra, **kw)
        ablation = build_ablation(by_lead, v, rows)
        reliability = build_reliability(by_lead, v)
        cells, lose_summary = build_where_we_lose(by_lead, geo, v)
        summary[v] = {"headline": headline, "ablation": ablation, "where_we_lose": lose_summary,
                      "units": UNITS[v]}
        write_json(f"ablation_{v}.json", {"variable": v, "leads": ablation}, **kw)
        write_json(f"reliability_{v}.json", {"variable": v, "events": reliability}, **kw)
        write_json(f"rev_{v}.json", build_rev(by_lead, v), **kw)
        write_json(f"where_we_lose_{v}.json", {"summary": lose_summary, "cells": cells}, **kw)
        if v == "precip":
            write_json("ablation.json", {"variable": v, "leads": ablation}, **kw)
            write_json("rev.json", build_rev(by_lead, v), **kw)
            write_json("fss_curve.json", build_fss_curve(by_lead), **kw)
            head = reliability[HEADLINE_EVENT[v]]["leads"][f"L{min(by_lead)}"]
            write_json("reliability.json", {
                "threshold_mm": 64.5, "lead_day": min(by_lead),
                "bins": head["curves"]["blend_calibrated"]["bins"],
                "observed_freq": {k: c["observed_freq"] for k, c in head["curves"].items()},
                "mean_forecast": {k: c["mean_forecast"] for k, c in head["curves"].items()},
                "counts": {k: c["counts"] for k, c in head["curves"].items()},
                "brier": {k: c["brier"] for k, c in head["curves"].items()},
                "auc": {k: c["auc"] for k, c in head["curves"].items()},
                "events": reliability}, **kw)
            _write_where(cells, lose_summary, write_where_we_lose, kw)
        log.info("pipeline.verification_written", variable=v)

    first = variables[0]
    kw0 = dict(cycle=f"{cycle:%Y-%m-%dT%HZ}", models=results[first][min(results[first])][-1].models,
               strategy=FINAL[first])
    write_json("summary.json", {"variables": summary, "test_years": list(TEST_YEARS)}, **kw0)
    write_json("qc_report.json", {"gate": [
        {"model": m, "variable": v, "years": list(y), "lead_day": ld, **info}
        for (m, v, y, ld), info in sorted(data.QC_LOG.items())]}, **kw0)
    try:
        write_json("changepoint.json", build_changepoints("precip", min(lead_days), geo), **kw0)
    except Exception as e:  # monitoring must never stop the pipeline
        log.warning("pipeline.changepoint_failed", error=str(e))

    run_showcase(cycle, lead_days, geo)

    log.info("pipeline.done", seconds=round(time.time() - t0, 1))


def _write_where(cells, summary, writer, kw):
    path = writer(cells, **kw)
    obj = json.loads(path.read_text())
    obj["summary"] = summary
    path.write_text(json.dumps(obj, indent=2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cycle", default="2022-06-14", help="Showcase init date YYYY-MM-DD")
    ap.add_argument("--lead_days", nargs="*", type=int, default=None)
    ap.add_argument("--variables", nargs="*", default=None, choices=VARIABLES)
    ap.add_argument("--showcase_only", action="store_true",
                    help="skip the evaluation and rebuild the cycle products from the frozen artifacts")
    args = ap.parse_args()
    canonical.logging.setup()
    if args.showcase_only:
        run_showcase(pd.Timestamp(args.cycle), args.lead_days or LEAD_DAYS, rg.load_geography())
    else:
        run_pipeline(pd.Timestamp(args.cycle), args.lead_days, args.variables)


if __name__ == "__main__":
    main()
