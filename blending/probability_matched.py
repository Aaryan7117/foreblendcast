"""Probability-matched blending for rain (TECH_APPROACH §2.5)."""
from __future__ import annotations

import numpy as np

from blending.deterministic import weighted_mean

def probability_matched(fields: dict[str, np.ndarray],
                        weights: dict[str, float | np.ndarray],
                        land_mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Probability-matched blending for rain (TECH_APPROACH §2.5).

    Returns:
        (M, B) — the weighted mean and probability-matched blend
    """
    # M: location field
    M = weighted_mean(fields, weights)

    # Build the intensity pool from land cells
    pool_vals = []
    pool_weights = []
    
    for model, field in fields.items():
        if model not in weights:
            continue
        w = weights[model]
        land_vals = field[land_mask]
        valid = np.isfinite(land_vals)
        
        if isinstance(w, float):
            pool_vals.extend(land_vals[valid].tolist())
            pool_weights.extend([w] * int(valid.sum()))
        else:
            w_land = w[land_mask]
            w_valid = valid & np.isfinite(w_land)
            pool_vals.extend(land_vals[w_valid].tolist())
            pool_weights.extend(w_land[w_valid].tolist())

    if not pool_vals:
        return M, M

    pool_vals = np.array(pool_vals)
    pool_weights = np.array(pool_weights)

    # Sort pool by value
    sort_idx = np.argsort(pool_vals)
    pool_sorted = pool_vals[sort_idx]
    pw_sorted = pool_weights[sort_idx]
    
    # Cumulative weight
    cum_weights = np.cumsum(pw_sorted)
    if cum_weights[-1] > 0:
        cum_weights /= cum_weights[-1]  # normalize to [0, 1]

    # B: rank-remap
    B = M.copy()
    m_land = M[land_mask]
    
    valid_m = np.isfinite(m_land)
    m_land_valid = m_land[valid_m]
    
    if len(m_land_valid) > 0:
        # Rank of each land cell in M
        ranks = np.argsort(np.argsort(m_land_valid)).astype(np.float64)
        ranks /= max(1, len(ranks) - 1)  # normalize to [0, 1]

        # Map ranks to pool values
        remapped = np.interp(ranks, cum_weights, pool_sorted)
        
        # Insert back into land mask
        b_land = B[land_mask]
        b_land[valid_m] = remapped.astype(np.float32)
        B[land_mask] = b_land

    return M, B
