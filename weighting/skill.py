"""Historical skill database and the adaptive weights derived from it (B8, B9).

The database holds squared-error sums of every model per

    (model | variable, lead, season, regime, cell)

built from training samples only. Weights for a context are

    W(model | region, season, lead, regime, variable) = softmax(-relative RMSE / τ)

computed at four levels (national -> region -> district -> cell) and shrunk towards the
parent level by λ = n_eff / (n_eff + k). n_eff = training days x sqrt(cells pooled): days
are the independent unit, and pooling cells adds less than linearly because neighbouring
cells are correlated. Nothing in this module ever sees a test-year observation.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from experiments.design import SEASONS
from regimes.detector import REGIMES, Geography
from weighting.shrinkage import shrink, softmax_weights
from weighting.spatial import apply_spatial_smoothing

S, K = len(SEASONS), len(REGIMES)


@dataclass
class SkillDB:
    models: list[str]
    variable: str
    lead_day: int
    sse: np.ndarray            # (M, S, K, lat, lon) sum of squared errors
    count: np.ndarray          # (M, S, K, lat, lon) number of training days
    train_dates: list = field(default_factory=list)  # valid dates that entered the sums

    def n_samples(self) -> int:
        return len(self.train_dates)


def build_skill(models: list[str], variable: str, lead_day: int,
                fc: dict[str, np.ndarray], obs: np.ndarray,
                seasons: np.ndarray, regimes: np.ndarray, geo: Geography,
                valid_dates=None, use: np.ndarray | None = None) -> SkillDB:
    """Accumulate squared errors per context from the samples selected by `use`."""
    n = obs.shape[0]
    use = np.ones(n, dtype=bool) if use is None else use
    shape = (len(models), S, K) + obs.shape[1:]
    sse, count = np.zeros(shape), np.zeros(shape)
    node = geo.node_cells()
    for mi, m in enumerate(models):
        err2 = np.square(fc[m].astype(np.float64) - obs)
        ok = np.isfinite(err2)
        err2 = np.where(ok, err2, 0.0)
        for s in range(S):
            for k in range(K):
                for c in range(geo.n_regions + 1):
                    days = use & (seasons == s) & (regimes[:, c] == k)
                    cells = node == c
                    if not days.any() or not cells.any():
                        continue
                    sse[mi, s, k][cells] = err2[days][:, cells].sum(axis=0)
                    count[mi, s, k][cells] = ok[days][:, cells].sum(axis=0)
    dates = [d for d, u in zip(valid_dates, use) if u] if valid_dates is not None else []
    return SkillDB(models, variable, lead_day, sse, count, dates)


def _pool(values: np.ndarray, labels: np.ndarray, n_labels: int, weights: np.ndarray) -> np.ndarray:
    """Area-weighted sum of (..., lat, lon) over the cells of each label -> (..., n_labels)."""
    flat_l = labels.ravel()
    ok = flat_l >= 0
    lead_shape = values.shape[:-2]
    v = (values * weights).reshape(-1, flat_l.size)[:, ok]
    out = np.zeros((v.shape[0], n_labels))
    for i in range(v.shape[0]):
        out[i] = np.bincount(flat_l[ok], weights=v[i], minlength=n_labels)
    return out.reshape(lead_shape + (n_labels,))


def _rel(rmse: np.ndarray) -> np.ndarray:
    """RMSE relative to the mean over models, so τ is dimensionless across variables."""
    ok = np.isfinite(rmse)
    n = ok.sum(axis=0, keepdims=True)
    ref = np.where(ok, rmse, 0.0).sum(axis=0, keepdims=True) / np.maximum(n, 1)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(ref > 0, rmse / np.where(ref > 0, ref, 1.0), np.nan)


def _rmse(sse: np.ndarray, cnt: np.ndarray) -> np.ndarray:
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.sqrt(np.where(cnt > 0, sse / np.where(cnt > 0, cnt, 1.0), np.nan))


@dataclass
class WeightSet:
    """Weights for every (season, regime) of one variable and lead."""
    models: list[str]
    cell: np.ndarray        # (S, K, M, lat, lon) full hierarchy + smoothing
    region: np.ndarray      # (S, K, M, R) region level, no shrinkage  ("context" rung)
    national: np.ndarray    # (S, M)
    lam_cell: np.ndarray    # (S, K, lat, lon) share of the cell's own evidence
    level_used: np.ndarray  # (S, K, lat, lon) 0 national, 1 region, 2 district, 3 cell
    n_days: np.ndarray      # (S, K, lat, lon) training days behind the cell's context
    tau: float
    k: float

    def context_cell(self, geo: Geography) -> np.ndarray:
        """Region weights broadcast to cells (national outside the regions)."""
        out = np.empty((S, K, len(self.models)) + geo.land.shape)
        for s in range(S):
            for k in range(K):
                out[s, k] = self.national[s][:, None, None]
                for r in range(geo.n_regions):
                    out[s, k][:, geo.region_idx == r] = self.region[s, k][:, r][:, None]
        return out


def compute_weights(db: SkillDB, geo: Geography, tau: float, k: float = 20.0,
                    n_eff_min: float = 15.0, smooth_sigma: float = 1.0) -> WeightSet:
    M = len(db.models)
    aw = geo.aw
    R, D = geo.n_regions, len(geo.district_ids)
    land_lbl = np.where(geo.land, 0, -1)

    # national: regimes pooled, one node per season
    nat_sse = _pool(db.sse.sum(axis=2), land_lbl, 1, aw)[..., 0]          # (M, S)
    nat_cnt = _pool(db.count.sum(axis=2), land_lbl, 1, aw)[..., 0]
    w_nat = softmax_weights(_rel(_rmse(nat_sse, nat_cnt)), tau)            # (M, S)

    days = db.count.max(axis=0)                                            # (S, K, lat, lon)

    def level(labels: np.ndarray, n_labels: int, parent: np.ndarray):
        sse = _pool(db.sse, labels, n_labels, aw)                          # (M, S, K, n)
        cnt = _pool(db.count, labels, n_labels, aw)
        local = softmax_weights(_rel(_rmse(sse, cnt)), tau)
        cells = np.bincount(labels[labels >= 0].ravel(), minlength=n_labels)
        node_days = np.zeros((S, K, n_labels))
        for s in range(S):
            for kk in range(K):
                np.maximum.at(node_days[s, kk], labels[labels >= 0], days[s, kk][labels >= 0])
        n_eff = node_days * np.sqrt(np.maximum(cells, 1))
        w, lam = shrink(local, parent, n_eff, k, n_eff_min)
        return local, w, lam

    parent_nat = np.broadcast_to(w_nat[:, :, None, None], (M, S, K, R))
    local_reg, w_reg, lam_reg = level(geo.region_idx, R, parent_nat)

    dr = np.maximum(geo.district_region, 0)
    parent_reg = w_reg[..., dr]                                            # (M, S, K, D)
    _, w_dis, lam_dis = level(geo.district_idx, D, parent_reg)

    # cell level: parent is the district (national where the cell has none)
    di = np.maximum(geo.district_idx, 0)
    parent_cell = np.where(geo.district_idx >= 0, w_dis[..., di],
                           w_nat[:, :, None, None, None])                  # (M, S, K, lat, lon)
    local_cell = softmax_weights(_rel(_rmse(db.sse, db.count)), tau)
    w_cell, lam_cell = shrink(local_cell, parent_cell, days, k, n_eff_min)

    level_used = np.where(lam_cell > 0, 3,
                          np.where(lam_dis[..., di] > 0, 2,
                                   np.where(lam_reg[..., dr][..., di] > 0, 1, 0)))
    level_used = np.where(geo.district_idx >= 0, level_used, 0)

    # smooth each weight field, then renormalise over models
    from canonical.terrain import classify_cells
    terrain = classify_cells(None, geo.land)
    out = np.empty((S, K, M) + geo.land.shape)
    for s in range(S):
        for kk in range(K):
            fields = np.stack([apply_spatial_smoothing(w_cell[m, s, kk], terrain, smooth_sigma)
                               for m in range(M)])
            out[s, kk] = fields / np.maximum(fields.sum(axis=0, keepdims=True), 1e-12)

    return WeightSet(
        models=db.models, cell=out,
        region=np.moveaxis(local_reg, 0, 2),      # (S, K, M, R)
        national=np.moveaxis(w_nat, 0, 1),        # (S, M)
        lam_cell=lam_cell, level_used=level_used, n_days=days, tau=tau, k=k)


def day_weights(table: np.ndarray, season: int, rmap: np.ndarray) -> np.ndarray:
    """(M, lat, lon) weights of one day from a (S, K, M, lat, lon) table."""
    return np.choose(rmap[None], [table[season, kk] for kk in range(K)])


def blend_stack(fc: dict[str, np.ndarray], models: list[str], table: np.ndarray,
                seasons: np.ndarray, regimes: np.ndarray, geo: Geography) -> tuple[np.ndarray, np.ndarray]:
    """Weighted mean of every day. A model missing on a day is dropped and the rest renormalised.

    Returns (blend (n, lat, lon), weights actually applied (n, M, lat, lon) as float32).
    """
    n = len(seasons)
    node = geo.node_cells()
    out = np.empty((n,) + geo.land.shape, np.float32)
    applied = np.empty((n, len(models)) + geo.land.shape, np.float32)
    for d in range(n):
        w = day_weights(table, seasons[d], regimes[d][node])
        f = np.stack([fc[m][d] for m in models]).astype(np.float64)
        ok = np.isfinite(f)
        w = np.where(ok, w, 0.0)
        tot = w.sum(axis=0)
        w = w / np.where(tot > 0, tot, 1.0)
        out[d] = np.where(tot > 0, (w * np.where(ok, f, 0.0)).sum(axis=0), np.nan)
        applied[d] = w
    return out, applied


def fixed_blend(fc: dict[str, np.ndarray], weights: dict[str, float]) -> np.ndarray:
    """Weighted mean with constant scalar weights, renormalised over the models present."""
    models = list(weights)
    f = np.stack([fc[m] for m in models]).astype(np.float64)
    w = np.array([weights[m] for m in models])[:, None, None, None] * np.isfinite(f)
    tot = w.sum(axis=0)
    out = (w * np.nan_to_num(f)).sum(axis=0) / np.where(tot > 0, tot, 1.0)
    return np.where(tot > 0, out, np.nan).astype(np.float32)


def national_rmse(db: SkillDB, geo: Geography) -> dict[str, float]:
    """Training RMSE of every model over all land, seasons and regimes."""
    lbl = np.where(geo.land, 0, -1)
    sse = _pool(db.sse.sum(axis=(1, 2)), lbl, 1, geo.aw)[..., 0]
    cnt = _pool(db.count.sum(axis=(1, 2)), lbl, 1, geo.aw)[..., 0]
    return {m: float(v) for m, v in zip(db.models, _rmse(sse, cnt))}


def region_rmse(db: SkillDB, geo: Geography) -> np.ndarray:
    """(M, S, K, R) training RMSE per region context, for the explanation outputs."""
    return _rmse(_pool(db.sse, geo.region_idx, geo.n_regions, geo.aw),
                 _pool(db.count, geo.region_idx, geo.n_regions, geo.aw))
