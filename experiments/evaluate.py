"""Leakage-free evaluation of one (variable, lead, fold).

Order of operations, which is the whole point of this module:

    1. training samples (years < test year)  -> regime thresholds, climatology
    2. cross-fit inside training (odd vs even months) -> τ, calibrators, quantile tables
    3. skill database from all training samples -> weights, FROZEN
    4. test-year forecasts are blended with the frozen weights
    5. only then is the test-year truth read, for verification

Nothing fitted in 1-3 sees a test-year observation (experiments.folds.check_no_leakage).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from scipy.ndimage import uniform_filter

import canonical.logging
from blending.probability_matched import probability_matched
from calibration.isotonic import apply_calibration, calibrate_isotonic
from calibration import lgbm
from calibration import quantiles as cq
from calibration.quantiles import (ConditionalQuantiles, crps_ensemble,
                                   crps_from_quantiles)
from canonical.grid import LAT, LON
from experiments import data
from experiments.folds import check_no_leakage
from hazards.events import EVENTS, clim_for, monthly_climatology
from regimes import detector as rg
from verification.fss import NEIGHBOURHOODS, THRESHOLDS_MM, fss_parts
from weighting import skill as sk

log = canonical.logging.get_logger(__name__)

TAU_GRID = (0.02, 0.05, 0.1, 0.2, 0.5, 1.0)
K_GRID = (20.0, 100.0, 500.0, 2000.0)   # shrinkage strength: larger k leans harder on the parent level
N_EFF_MIN = 15.0
NEIGHBOURHOOD_PROB = 5      # cells, for the member-neighbourhood probability
PERSISTENCE_LAG_DAYS = 2    # last IMD day fully observed at 00 UTC init
FLOOR = {"precip": 0.0, "wind": 0.0, "t2m": None}
FINAL = {"precip": "context_shrink_pm", "t2m": "context_shrink", "wind": "context_shrink"}


FROZEN_DIR = Path("data/frozen")


@dataclass
class Frozen:
    """Everything a forecast cycle needs, fitted on training years only."""
    variable: str
    lead_day: int
    train_years: tuple
    models: list[str]
    tau: float
    shrink_k: float
    regime_thresholds: np.ndarray      # (S, node, 2)
    clim12: np.ndarray                 # (12, lat, lon) training truth normal
    weights: np.ndarray                # (S, K, M, lat, lon)
    level_used: np.ndarray             # (S, K, lat, lon)
    lam_cell: np.ndarray
    n_days: np.ndarray
    calibrators: dict                  # event -> {predictor, calibrator, decision_threshold, ...}
    quantiles: ConditionalQuantiles
    clim_spread: np.ndarray            # (S, lat, lon) mean inter-model std in training
    lomo_sse: np.ndarray               # (S, M, lat, lon) SSE of the blend without model m
    full_sse: np.ndarray               # (S, lat, lon) SSE of the full blend
    train_rmse: dict
    region_skill: dict
    quantile_method: str = "table"     # "table" or "lgbm", chosen on training data
    lgbm_quantiles: object = None      # calibration.lgbm.LgbmQuantiles when chosen

    def path(self) -> Path:
        return frozen_path(self.variable, self.lead_day, max(self.train_years))


def frozen_path(variable: str, lead_day: int, last_train_year: int) -> Path:
    return FROZEN_DIR / f"{variable}_L{lead_day}_train_to_{last_train_year}.joblib"


def load_frozen(variable: str, lead_day: int, init: pd.Timestamp) -> Frozen | None:
    """The most recent artifact whose training years all precede the init year."""
    best = None
    for f in FROZEN_DIR.glob(f"{variable}_L{lead_day}_train_to_*.joblib"):
        year = int(f.stem.rsplit("_", 1)[1])
        if year < init.year and (best is None or year > best[0]):
            best = (year, f)
    return joblib.load(best[1]) if best else None


@dataclass
class LeadResult:
    variable: str
    lead_day: int
    test_year: int
    train_years: tuple
    models: list[str]
    tau: float
    shrink_k: float
    tau_scores: dict
    n_train: int
    n_test: int
    inits: pd.DatetimeIndex
    valid: pd.DatetimeIndex
    seasons: np.ndarray
    regimes: np.ndarray
    best_single: str
    train_rmse: dict
    daily: dict = field(default_factory=dict)      # strategy -> {mse, mae, bias, region_mse}
    fss: dict = field(default_factory=dict)        # strategy -> {(thr, nb): (num, ref)}
    freq: dict = field(default_factory=dict)       # strategy -> {event: (n_fc, n_ob)}
    prob: dict = field(default_factory=dict)       # event -> {obs, preds{name: array}, ...}
    crps: dict = field(default_factory=dict)       # name -> (weighted sum, weight)
    coverage90: tuple = (0.0, 0.0)
    coverage90_lgbm: tuple = (0.0, 0.0)
    quantile_method: str = "table"
    quantile_cv_pinball: dict = field(default_factory=dict)
    lgbm_importance: dict = field(default_factory=dict)
    missing: dict = field(default_factory=dict)    # model -> number of test days without data
    weights_summary: dict = field(default_factory=dict)


# ───────────────────────── helpers ─────────────────────────

def regime_inputs(years: tuple, lead_day: int, geo: rg.Geography, inits) -> np.ndarray:
    """Region means of the equal-weight multi-model rainfall forecast, aligned to `inits`."""
    all_inits = pd.DatetimeIndex([t for y in years for t in data.init_dates(y)])
    j = data.LEAD_DAYS.index(lead_day)
    stacks = []
    for m in data.models_for("precip"):
        parts = [data.forecast_year(m, "precip", y) for y in years]
        stacks.append(np.concatenate([np.asarray(p[:, j]) for p in parts], axis=0))
    idx = all_inits.get_indexer(inits)
    mean = rg.multi_model_mean({i: s[idx] for i, s in enumerate(stacks)})
    return rg.region_means(mean, geo)


def land_mean(field_stack: np.ndarray, geo: rg.Geography) -> np.ndarray:
    """Area-weighted land mean of each day. NaN cells are skipped."""
    v = field_stack[:, geo.land].astype(np.float64)
    w = geo.aw[geo.land]
    ok = np.isfinite(v)
    den = ok @ w
    return np.where(den > 0, (np.where(ok, v, 0.0) @ w) / np.where(den > 0, den, 1.0), np.nan)


def daily_scores(fc: np.ndarray, obs: np.ndarray, geo: rg.Geography) -> dict:
    err = fc.astype(np.float64) - obs
    return {
        "mse": land_mean(err ** 2, geo),
        "mae": land_mean(np.abs(err), geo),
        "bias": land_mean(err, geo),
        "region_mse": rg.region_means(err ** 2, geo),
    }


def equal_mean(fc: dict[str, np.ndarray]) -> np.ndarray:
    return rg.multi_model_mean(fc).astype(np.float32)


def oracle(fc: dict[str, np.ndarray], obs: np.ndarray) -> np.ndarray:
    stack = np.stack(list(fc.values()))
    err = np.where(np.isfinite(stack), np.abs(stack - obs[None]), np.inf)
    best = err.argmin(axis=0)
    out = np.take_along_axis(stack, best[None], axis=0)[0]
    return np.where(np.isfinite(err.min(axis=0)), out, np.nan)


def pm_stack(fc: dict[str, np.ndarray], models: list[str], applied: np.ndarray,
             geo: rg.Geography) -> np.ndarray:
    """Probability-matched blend for every day (rain only)."""
    out = np.empty(applied.shape[:1] + geo.land.shape, np.float32)
    for d in range(applied.shape[0]):
        fields = {m: fc[m][d] for m in models if np.isfinite(fc[m][d]).any()}
        w = {m: applied[d, i].astype(np.float64) for i, m in enumerate(models) if m in fields}
        _, out[d] = probability_matched(fields, w, geo.land)
    return np.maximum(out, 0.0)


def neighbourhood_probability(fc: dict[str, np.ndarray], models: list[str], applied: np.ndarray,
                              margin_fn, clim: np.ndarray | None) -> np.ndarray:
    """P(event) as the weighted share of members exceeding in a neighbourhood."""
    p = np.zeros(applied.shape[:1] + applied.shape[2:], np.float32)
    for i, m in enumerate(models):
        with np.errstate(invalid="ignore"):
            exceed = (margin_fn(fc[m], clim) >= 0).astype(np.float32)
        nb = uniform_filter(exceed, size=(1, NEIGHBOURHOOD_PROB, NEIGHBOURHOOD_PROB), mode="nearest")
        p += applied[:, i] * nb
    return np.clip(p, 0.0, 1.0)


def equal_applied(fc: dict[str, np.ndarray], models: list[str]) -> np.ndarray:
    ok = np.stack([np.isfinite(fc[m]) for m in models], axis=1).astype(np.float32)
    return ok / np.maximum(ok.sum(axis=1, keepdims=True), 1.0)


def brier(p: np.ndarray, o: np.ndarray) -> float:
    ok = np.isfinite(p)
    return float(np.mean((p[ok] - o[ok]) ** 2)) if ok.any() else float("nan")


def best_csi_threshold(p: np.ndarray, o: np.ndarray) -> tuple[float, float]:
    """Probability threshold with the highest critical success index on training data."""
    best, best_csi = 0.5, -1.0
    ok = np.isfinite(p)
    p, o = p[ok], o[ok] > 0.5
    for t in np.round(np.arange(0.05, 0.91, 0.05), 2):
        act = p >= t
        hits = float(np.sum(act & o))
        denom = hits + float(np.sum(act & ~o)) + float(np.sum(~act & o))
        csi = hits / denom if denom > 0 else 0.0
        if csi > best_csi:
            best, best_csi = float(t), csi
    return best, best_csi


# ───────────────────────── main ─────────────────────────

def evaluate(variable: str, fold: dict, lead_day: int, geo: rg.Geography,
             save_frozen: bool = False) -> LeadResult | None:
    models = data.models_for(variable)
    train_years, test_year = tuple(fold["train"]), fold["test"]
    tr = data.sample_block(models, variable, train_years, lead_day)
    te = data.sample_block(models, variable, (test_year,), lead_day)
    models = [m for m in models if m in tr["fc"] and m in te["fc"]]
    if not models or len(tr["valid"]) == 0 or len(te["valid"]) == 0:
        return None
    # Samples whose verifying day falls in the test year never enter a fit.
    keep = np.array([d.year != test_year for d in tr["valid"]])
    tr = {"inits": tr["inits"][keep], "valid": tr["valid"][keep], "obs": tr["obs"][keep],
          "fc": {m: v[keep] for m, v in tr["fc"].items()}}
    check_no_leakage(train_years, test_year, list(tr["valid"]))

    land = geo.land
    s_tr, s_te = rg.season_index(tr["valid"]), rg.season_index(te["valid"])
    series_tr = regime_inputs(train_years, lead_day, geo, tr["inits"])
    series_te = regime_inputs((test_year,), lead_day, geo, te["inits"])
    thresholds = rg.fit_thresholds(series_tr, s_tr)
    r_tr, r_te = rg.classify(series_tr, s_tr, thresholds), rg.classify(series_te, s_te, thresholds)

    # climatology from every training-year truth day (not only the sampled valid dates)
    clim_days = [d for y in train_years for d in pd.date_range(f"{y}-01-01", f"{y}-12-31")]
    clim12 = monthly_climatology(data.truth_for(variable, clim_days), clim_days)
    clim_tr, clim_te = clim_for(clim12, tr["valid"]), clim_for(clim12, te["valid"])

    # ── cross-fit inside training: τ, then out-of-sample training blends ──
    half = np.array([d.month % 2 for d in tr["valid"]])
    dbs = [sk.build_skill(models, variable, lead_day, tr["fc"], tr["obs"], s_tr, r_tr, geo,
                          tr["valid"], use=(half != h)) for h in (0, 1)]
    tau_scores = {}
    for tau in TAU_GRID:
        for k in K_GRID:
            sq = np.full(len(tr["valid"]), np.nan)
            for h in (0, 1):
                ws = sk.compute_weights(dbs[h], geo, tau, k, N_EFF_MIN)
                sel = half == h
                b, _ = sk.blend_stack({m: tr["fc"][m][sel] for m in models}, models, ws.cell,
                                      s_tr[sel], r_tr[sel], geo)
                sq[sel] = land_mean((b - tr["obs"][sel]) ** 2, geo)
            tau_scores[(tau, k)] = float(np.sqrt(np.nanmean(sq)))
    tau, shrink_k = min(tau_scores, key=tau_scores.get)

    xfit = np.empty_like(tr["obs"])
    xfit_w = np.empty((len(tr["valid"]), len(models)) + land.shape, np.float32)
    for h in (0, 1):
        ws = sk.compute_weights(dbs[h], geo, tau, shrink_k, N_EFF_MIN)
        sel = half == h
        xfit[sel], xfit_w[sel] = sk.blend_stack({m: tr["fc"][m][sel] for m in models}, models,
                                                ws.cell, s_tr[sel], r_tr[sel], geo)
    xfit_final = pm_stack(tr["fc"], models, xfit_w, geo) if variable == "precip" else xfit

    # ── frozen weights from the full training set ──
    db = sk.build_skill(models, variable, lead_day, tr["fc"], tr["obs"], s_tr, r_tr, geo, tr["valid"])
    ws = sk.compute_weights(db, geo, tau, shrink_k, N_EFF_MIN)
    train_rmse = sk.national_rmse(db, geo)
    best_single = min(train_rmse, key=lambda m: train_rmse[m] if np.isfinite(train_rmse[m]) else np.inf)

    # ── forecasts for the test year (truth not touched yet) ──
    fc = te["fc"]
    strategies: dict[str, np.ndarray] = {}
    strategies["climatology"] = clim_te
    lagged = [t - pd.Timedelta(days=PERSISTENCE_LAG_DAYS) for t in te["inits"]]
    strategies["persistence"] = data.truth_for(variable, lagged)
    for m in models:
        strategies[m] = fc[m]
    strategies["best_single_train"] = fc[best_single]
    strategies["equal_weight"] = equal_mean(fc)
    inv = {m: 1.0 / max(train_rmse[m], 1e-6) for m in models if np.isfinite(train_rmse[m])}
    strategies["inverse_error"] = sk.fixed_blend(fc, {m: v / sum(inv.values()) for m, v in inv.items()})
    strategies["context"], _ = sk.blend_stack(fc, models, ws.context_cell(geo), s_te, r_te, geo)
    strategies["context_shrink"], applied = sk.blend_stack(fc, models, ws.cell, s_te, r_te, geo)
    if variable == "precip":
        strategies["context_shrink_pm"] = pm_stack(fc, models, applied, geo)
    final_name = FINAL[variable]
    final = strategies[final_name]

    events = EVENTS[variable]
    eq_w_tr, eq_w_te = equal_applied(tr["fc"], models), equal_applied(fc, models)
    qmap = ConditionalQuantiles(floor=FLOOR[variable]).fit(xfit_final[:, land], tr["obs"][:, land])
    qmap_eq = ConditionalQuantiles(floor=FLOOR[variable]).fit(
        equal_mean(tr["fc"])[:, land], tr["obs"][:, land])

    calibrators, prob_fc = {}, {}
    for ev in events:
        o_tr = (ev.margin(tr["obs"], clim_tr) >= 0)[:, land].astype(np.float32)
        cand_tr = {
            "neighbourhood": neighbourhood_probability(tr["fc"], models, xfit_w, ev.margin, clim_tr)[:, land],
            "amount": ev.margin(xfit_final, clim_tr)[:, land],
        }
        # pick the predictor by cross-validated Brier score inside training
        cv = {}
        for name, x in cand_tr.items():
            pred = np.full(x.shape, np.nan, np.float32)
            for h in (0, 1):
                sel = half == h
                if (half != h).any() and sel.any():
                    pred[sel] = apply_calibration(calibrate_isotonic(x[half != h], o_tr[half != h]), x[sel])
            cv[name] = brier(pred, o_tr)
        predictor = min(cv, key=lambda k: cv[k] if np.isfinite(cv[k]) else np.inf)
        cal = calibrate_isotonic(cand_tr[predictor], o_tr)
        p_tr = apply_calibration(cal, cand_tr[predictor])
        tier_thr, tier_csi = best_csi_threshold(p_tr, o_tr)
        calibrators[ev.key] = {"predictor": predictor, "calibrator": cal, "cv_brier": cv,
                               "base_rate_train": float(o_tr.mean()),
                               "decision_threshold": tier_thr, "train_csi": tier_csi}

        raw = neighbourhood_probability(fc, models, applied, ev.margin, clim_te)
        x_te = raw if predictor == "neighbourhood" else ev.margin(final, clim_te)
        prob_fc[ev.key] = {
            "raw": raw,
            "calibrated": apply_calibration(cal, x_te),
            "equal_raw": neighbourhood_probability(fc, models, eq_w_te, ev.margin, clim_te),
        }
    quant_te = qmap.predict(final[:, land])
    quant_eq = qmap_eq.predict(strategies["equal_weight"][:, land])

    # ── LightGBM layers, trained on the same cross-fitted training forecasts ──
    lat2d, lon2d = np.meshgrid(LAT, LON, indexing="ij")
    node = geo.node_cells()
    names = lgbm.feature_names(models)
    X_tr = lgbm.build_features(xfit_final, tr["fc"], models, s_tr, r_tr[:, node], clim_tr,
                               tr["valid"], lat2d, lon2d, land)
    X_te = lgbm.build_features(final, fc, models, s_te, r_te[:, node], clim_te,
                               te["valid"], lat2d, lon2d, land)
    y_tr = tr["obs"][:, land].ravel()
    n_land = int(land.sum())
    sample_half = np.repeat(half, n_land)
    common = [int(np.argmin(np.abs(cq.LEVELS - q))) for q in lgbm.LEVELS]
    cv_pin = {"table": [], "lgbm": []}
    for h in (0, 1):
        fit, val = sample_half != h, sample_half == h
        if not fit.any() or not val.any():
            continue
        q_l = lgbm.LgbmQuantiles(FLOOR[variable]).fit(X_tr[fit], y_tr[fit], names).predict(X_tr[val])
        q_t = ConditionalQuantiles(floor=FLOOR[variable]).fit(X_tr[fit][:, 0], y_tr[fit]) \
            .predict(X_tr[val][:, 0])[common]
        cv_pin["lgbm"].append(lgbm.pinball(q_l, y_tr[val], lgbm.LEVELS))
        cv_pin["table"].append(lgbm.pinball(q_t, y_tr[val], lgbm.LEVELS))
    cv_pin = {k: float(np.mean(v)) if v else float("inf") for k, v in cv_pin.items()}
    quantile_method = min(cv_pin, key=cv_pin.get)
    lq = lgbm.LgbmQuantiles(FLOOR[variable]).fit(X_tr, y_tr, names)
    quant_lgbm = lq.predict(X_te).reshape(len(lgbm.LEVELS), len(te["valid"]), n_land)
    learned = np.full(final.shape, np.nan, np.float32)
    learned[:, land] = lgbm.LgbmBlend(FLOOR[variable]).fit(X_tr, y_tr, names) \
        .predict(X_te).reshape(len(te["valid"]), n_land)
    strategies["lgbm_blend"] = learned

    # ═════════ everything above is frozen; the test truth is read from here on ═════════
    obs = te["obs"]
    res = LeadResult(
        variable=variable, lead_day=lead_day, test_year=test_year, train_years=train_years,
        models=models, tau=tau, shrink_k=shrink_k,
        tau_scores={f"tau={t},k={k:g}": v for (t, k), v in tau_scores.items()},
        n_train=len(tr["valid"]),
        n_test=len(te["valid"]), inits=te["inits"], valid=te["valid"], seasons=s_te,
        regimes=r_te, best_single=best_single, train_rmse=train_rmse)
    res.missing = {m: int((~np.isfinite(fc[m]).any(axis=(1, 2))).sum()) for m in models}
    strategies["oracle"] = oracle(fc, obs)

    for name, f in strategies.items():
        res.daily[name] = daily_scores(f, obs, geo)
        res.freq[name] = {}
        for ev in events:
            with np.errstate(invalid="ignore"):
                ok = (np.isfinite(f) & np.isfinite(obs))[:, land]
                yes_fc = (ev.margin(f, clim_te) >= 0)[:, land] & ok
                yes_ob = (ev.margin(obs, clim_te) >= 0)[:, land] & ok
            # (forecast yes, observed yes, hits, cases)
            res.freq[name][ev.key] = (int(yes_fc.sum()), int(yes_ob.sum()),
                                      int((yes_fc & yes_ob).sum()), int(ok.sum()))
        if variable == "precip":
            res.fss[name] = {(t, n): fss_parts(f, obs, t, n, land)
                             for t in THRESHOLDS_MM for n in NEIGHBOURHOODS}

    w_land = np.broadcast_to(geo.aw[land], obs[:, land].shape)
    for ev in events:
        o = (ev.margin(obs, clim_te) >= 0)[:, land].astype(np.float32).ravel()
        preds = {k: v[:, land].ravel() for k, v in prob_fc[ev.key].items()}
        c = calibrators[ev.key]
        res.prob[ev.key] = {
            "obs": o, "preds": preds, "predictor": c["predictor"], "cv_brier": c["cv_brier"],
            "base_rate_train": c["base_rate_train"],
            "decision_threshold": c["decision_threshold"], "train_csi": c["train_csi"],
        }

    o_land = obs[:, land]
    wsum = float(w_land[np.isfinite(o_land)].sum())
    members = np.stack([fc[m][:, land] for m in models])
    res.crps = {
        "blend_dressed": (crps_from_quantiles(quant_te, o_land, w_land) * wsum, wsum),
        "equal_dressed": (crps_from_quantiles(quant_eq, o_land, w_land) * wsum, wsum),
        "raw_ensemble": (crps_ensemble(members, o_land, w_land) * wsum, wsum),
        "blend_deterministic": (float(np.nansum(np.abs(final[:, land] - o_land) * w_land)), wsum),
    }
    inside = (o_land >= quant_te[0]) & (o_land <= quant_te[-1])
    res.coverage90 = (float(inside.sum()), float(np.isfinite(o_land).sum()))
    # like-for-like: both quantile methods on the seven levels LightGBM is trained for
    res.crps["blend_table_7_levels"] = (
        2 * lgbm.pinball(quant_te[common], o_land, lgbm.LEVELS, w_land) * wsum, wsum)
    res.crps["blend_lgbm_7_levels"] = (
        2 * lgbm.pinball(quant_lgbm, o_land, lgbm.LEVELS, w_land) * wsum, wsum)
    inside = (o_land >= quant_lgbm[0]) & (o_land <= quant_lgbm[-1])
    res.coverage90_lgbm = (float(inside.sum()), float(np.isfinite(o_land).sum()))
    res.quantile_method, res.quantile_cv_pinball = quantile_method, cv_pin
    res.lgbm_importance = lq.importance

    rr = sk.region_rmse(db, geo)
    res.weights_summary = {
        "national": {rg.SEASONS[s]: {m: float(ws.national[s, i]) for i, m in enumerate(models)}
                     for s in range(sk.S)},
        "region": {geo.region_names[r]: {rg.SEASONS[s]: {rg.REGIMES[k]: {
            "weights": {m: float(ws.region[s, k, i, r]) for i, m in enumerate(models)},
            "train_rmse": {m: _f(rr[i, s, k, r]) for i, m in enumerate(models)},
            "train_days": int(db.count[:, s, k][:, geo.region_idx == r].max()) if (geo.region_idx == r).any() else 0,
        } for k in range(sk.K)} for s in range(sk.S)} for r in range(geo.n_regions)},
    }

    if save_frozen:
        clim_spread = np.empty((sk.S,) + land.shape, np.float32)
        lomo_sse = np.zeros((sk.S, len(models)) + land.shape, np.float32)
        full_sse = np.zeros((sk.S,) + land.shape, np.float32)
        overall = np.nanmean(np.nanstd(np.stack([tr["fc"][m] for m in models]), axis=0), axis=0)
        for s in range(sk.S):
            sel = s_tr == s
            if not sel.any():
                clim_spread[s] = overall
                continue
            clim_spread[s] = np.nanmean(
                np.nanstd(np.stack([tr["fc"][m][sel] for m in models]), axis=0), axis=0)
            full_sse[s] = np.nansum((xfit[sel] - tr["obs"][sel]) ** 2, axis=0)
            f = np.stack([np.nan_to_num(tr["fc"][m][sel]) for m in models], axis=1)
            for i in range(len(models)):
                w = xfit_w[sel].copy()
                w[:, i] = 0.0
                tot = w.sum(axis=1)
                b = (w * f).sum(axis=1) / np.where(tot > 0, tot, 1.0)
                lomo_sse[s, i] = np.nansum((b - tr["obs"][sel]) ** 2, axis=0)
        frozen = Frozen(
            variable=variable, lead_day=lead_day, train_years=train_years, models=models,
            tau=tau, shrink_k=shrink_k, regime_thresholds=thresholds, clim12=clim12,
            weights=ws.cell.astype(np.float32), level_used=ws.level_used.astype(np.int8),
            lam_cell=ws.lam_cell.astype(np.float32), n_days=ws.n_days.astype(np.int16),
            calibrators=calibrators, quantiles=qmap, clim_spread=clim_spread,
            lomo_sse=lomo_sse, full_sse=full_sse, train_rmse=train_rmse,
            region_skill=res.weights_summary, quantile_method=quantile_method,
            lgbm_quantiles=lq if quantile_method == "lgbm" else None)
        FROZEN_DIR.mkdir(parents=True, exist_ok=True)
        joblib.dump(frozen, frozen.path(), compress=3)
    return res


def _f(x) -> float | None:
    return float(x) if np.isfinite(x) else None
