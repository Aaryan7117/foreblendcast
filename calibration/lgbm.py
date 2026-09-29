"""LightGBM layers trained on historical forecast / observation pairs (B11).

Two models, both fitted on training years only:

  LgbmQuantiles   quantile regression: predictive quantiles from the blend, the members,
                  their spread, location, season, regime and the climatological normal.
                  An alternative to the conditional quantile tables of
                  calibration.quantiles, which only look at the blend value.
  LgbmBlend       least-squares regression on the same features: a learned blend, scored
                  in the ladder next to the weight-based strategies.

Both learn the correction to the blend (observation minus blend, feature 0) and add it
back, so a model that learns nothing reproduces the blend instead of a coarse
piecewise-constant copy of it.

Whether the quantile tables or LgbmQuantiles feed the products is decided per variable
and lead by cross-validated pinball loss inside the training years
(experiments.evaluate), never on test data.
"""
from __future__ import annotations

import warnings

import numpy as np

LEVELS = (0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95)
MAX_SAMPLES = 400_000
ROUNDS = 80
PARAMS = {
    "learning_rate": 0.1, "num_leaves": 31, "min_data_in_leaf": 200,
    "feature_fraction": 0.9, "lambda_l2": 1.0, "max_bin": 127,
    "verbose": -1, "seed": 0, "deterministic": True, "force_row_wise": True,
}


def feature_names(models: list[str]) -> list[str]:
    return (["blend", "spread", "member_min", "member_max"] + [f"member_{m}" for m in models]
            + ["lat", "lon", "season", "regime", "normal", "doy_sin", "doy_cos"])


def build_features(blend: np.ndarray, members: dict[str, np.ndarray], models: list[str],
                   seasons: np.ndarray, regime_maps: np.ndarray, normal: np.ndarray,
                   valid_dates, lat2d: np.ndarray, lon2d: np.ndarray,
                   cells: np.ndarray | None = None) -> np.ndarray:
    """(n_days * n_cells, n_features) float32.

    blend, normal, regime_maps: (n, lat, lon); members: {model: (n, lat, lon)}, NaN where a
    model is missing (LightGBM treats NaN as missing); cells: boolean (lat, lon) selection.
    """
    n = blend.shape[0]
    sel = cells if cells is not None else np.ones(blend.shape[1:], dtype=bool)
    k = int(sel.sum())
    stack = np.stack([members[m][:, sel] if m in members else np.full((n, k), np.nan, np.float32)
                      for m in models])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)   # days on which every model is missing
        spread, lo, hi = np.nanstd(stack, axis=0), np.nanmin(stack, axis=0), np.nanmax(stack, axis=0)
    doy = np.array([d.dayofyear for d in valid_dates]) * (2 * np.pi / 365.25)
    per_day = lambda x: np.repeat(np.asarray(x, dtype=np.float32)[:, None], k, axis=1)
    per_cell = lambda x: np.repeat(x[sel][None].astype(np.float32), n, axis=0)
    cols = [blend[:, sel], spread, lo, hi, *stack,
            per_cell(lat2d), per_cell(lon2d), per_day(seasons), regime_maps[:, sel],
            normal[:, sel], per_day(np.sin(doy)), per_day(np.cos(doy))]
    return np.stack([np.asarray(c, dtype=np.float32).ravel() for c in cols], axis=1)


def _subsample(X: np.ndarray, y: np.ndarray, max_samples: int, seed: int = 0):
    ok = np.isfinite(y) & np.isfinite(X[:, 0])
    idx = np.flatnonzero(ok)
    if idx.size > max_samples:
        idx = np.random.default_rng(seed).choice(idx, max_samples, replace=False)
    return X[idx], y[idx]


class LgbmQuantiles:
    def __init__(self, floor: float | None = None, levels: tuple = LEVELS,
                 rounds: int = ROUNDS, max_samples: int = MAX_SAMPLES):
        self.floor, self.levels = floor, tuple(levels)
        self.rounds, self.max_samples = rounds, max_samples
        self.boosters: list = []
        self.importance: dict[str, float] = {}

    def fit(self, X: np.ndarray, y: np.ndarray, names: list[str] | None = None) -> "LgbmQuantiles":
        import lightgbm as lgb
        Xs, ys = _subsample(X, y, self.max_samples)
        data = lgb.Dataset(Xs, label=ys - Xs[:, 0], feature_name=names or "auto", free_raw_data=False)
        self.boosters = [lgb.train({**PARAMS, "objective": "quantile", "alpha": q}, data,
                                   num_boost_round=self.rounds) for q in self.levels]
        gain = np.sum([b.feature_importance("gain") for b in self.boosters], axis=0)
        total = gain.sum() or 1.0
        self.importance = {n: round(float(g / total), 4)
                           for n, g in zip(self.boosters[0].feature_name(), gain)}
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """(n_levels, n_samples), non-decreasing across levels."""
        out = np.stack([b.predict(X) for b in self.boosters]) + X[:, 0][None]
        out = np.maximum.accumulate(out, axis=0)
        if self.floor is not None:
            out = np.maximum(out, self.floor)
        return np.where(np.isfinite(X[:, 0])[None], out, np.nan)

    def level_index(self, level: float) -> int:
        return int(np.argmin(np.abs(np.array(self.levels) - level)))


class LgbmBlend:
    def __init__(self, floor: float | None = None, rounds: int = ROUNDS,
                 max_samples: int = MAX_SAMPLES):
        self.floor, self.rounds, self.max_samples = floor, rounds, max_samples
        self.booster = None

    def fit(self, X: np.ndarray, y: np.ndarray, names: list[str] | None = None) -> "LgbmBlend":
        import lightgbm as lgb
        Xs, ys = _subsample(X, y, self.max_samples)
        self.booster = lgb.train({**PARAMS, "objective": "regression"},
                                 lgb.Dataset(Xs, label=ys - Xs[:, 0], feature_name=names or "auto"),
                                 num_boost_round=self.rounds)
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        out = self.booster.predict(X) + X[:, 0]
        if self.floor is not None:
            out = np.maximum(out, self.floor)
        return np.where(np.isfinite(X[:, 0]), out, np.nan)


def pinball(quantiles: np.ndarray, obs: np.ndarray, levels,
            weights: np.ndarray | None = None) -> float:
    """Mean pinball loss over the levels. quantiles: (n_levels, ...), obs: (...)."""
    tau = np.asarray(levels, dtype=np.float64).reshape((-1,) + (1,) * obs.ndim)
    diff = obs[None] - quantiles
    loss = np.maximum(tau * diff, (tau - 1.0) * diff).mean(axis=0)
    ok = np.isfinite(loss)
    if not ok.any():
        return float("nan")
    if weights is None:
        return float(loss[ok].mean())
    return float(np.average(loss[ok], weights=np.broadcast_to(weights, loss.shape)[ok]))
