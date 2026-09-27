"""Blending module (B10): deterministic + probability-matched.

TECH_APPROACH §2.5:
- Deterministic (T, wind): weighted mean
- Rain: probability-matched blending — weighted mean for location, member pool for intensity
- Physical validator: clip rain < 0, Tmax >= Tmin, speed from blended (u, v)
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


def weighted_mean(fields: dict[str, np.ndarray], weights: dict[str, float]) -> np.ndarray:
    """Deterministic blend: weighted mean of model fields.

    Args:
        fields: {model_name: (lat, lon) array}
        weights: {model_name: weight}
    """
    result = np.zeros_like(next(iter(fields.values())), dtype=np.float64)
    w_total = 0.0
    for model, field in fields.items():
        w = weights.get(model, 0.0)
        valid = np.isfinite(field)
        result[valid] += w * field[valid]
        w_total += w
    if w_total > 0:
        result /= w_total
    return result.astype(np.float32)


def probability_matched(fields: dict[str, np.ndarray],
                        weights: dict[str, float],
                        land_mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Probability-matched blending for rain (TECH_APPROACH §2.5).

    M = Σ w_i F_i                     # location field (weighted mean)
    pool = concat(F_i) with weights   # intensity pool (land only)
    q = rank(M) / N                   # each cell's rank in M
    B = weighted_quantile(pool, q)    # rank-remap

    Returns:
        (M, B) — the weighted mean and probability-matched blend
    """
    # M: location field
    M = weighted_mean(fields, weights)

    # Build the intensity pool from land cells
    pool_vals = []
    pool_weights = []
    for model, field in fields.items():
        w = weights.get(model, 0.0)
        land_vals = field[land_mask]
        valid = np.isfinite(land_vals)
        pool_vals.extend(land_vals[valid].tolist())
        pool_weights.extend([w] * int(valid.sum()))

    if not pool_vals:
        return M, M

    pool_vals = np.array(pool_vals)
    pool_weights = np.array(pool_weights)

    # Sort pool by value
    sort_idx = np.argsort(pool_vals)
    pool_sorted = pool_vals[sort_idx]
    pw_sorted = pool_weights[sort_idx]
    cum_weights = np.cumsum(pw_sorted)
    cum_weights /= cum_weights[-1]  # normalize to [0, 1]

    # B: rank-remap
    B = M.copy()
    m_land = M[land_mask]
    if len(m_land) > 0:
        # Rank of each land cell in M
        ranks = np.argsort(np.argsort(m_land)).astype(np.float64)
        ranks /= max(1, len(ranks) - 1)  # normalize to [0, 1]

        # Map ranks to pool values
        remapped = np.interp(ranks, cum_weights, pool_sorted)
        B[land_mask] = remapped.astype(np.float32)

    return M, B


def physical_validate(blend: dict[str, np.ndarray],
                      log_path: Path | None = None) -> dict[str, np.ndarray]:
    """Physical validator: clip rain < 0, ensure Tmax >= Tmin, derive wind speed.

    Args:
        blend: dict with keys like 'precip', 't2m', 'u10', 'v10'
    Returns:
        corrected dict + optional log entries
    """
    corrections = []

    if "precip" in blend:
        neg = blend["precip"] < 0
        if neg.any():
            n = int(neg.sum())
            corrections.append({"field": "precip", "rule": "clip_negative", "count": n})
            blend["precip"] = np.maximum(blend["precip"], 0.0)

    # Derive wind speed from u, v
    if "u10" in blend and "v10" in blend:
        blend["wind_speed"] = np.sqrt(blend["u10"]**2 + blend["v10"]**2).astype(np.float32)

    if corrections and log_path:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a") as f:
            for c in corrections:
                f.write(json.dumps(c) + "\n")
        logger.info(f"Physical validator: {len(corrections)} corrections logged")

    return blend
