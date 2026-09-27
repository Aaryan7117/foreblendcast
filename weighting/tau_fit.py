"""Grid search for softmax tau (B9, TECH_APPROACH §2.2).

Fits tau by scanning values on the validation fold to minimize RMSE.
Writes results/tau.json.
"""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np

from weighting.context import ContextAware

def fit_tau(
    models: list[str], 
    validation_scores: list[dict[str, float]], 
    validation_truths: list[float],
    validation_forecasts: list[dict[str, float]],
    tau_candidates: list[float] | None = None
) -> float:
    """Find the tau that minimizes RMSE on the validation set."""
    if tau_candidates is None:
        tau_candidates = [0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
        
    best_tau = 1.0
    best_rmse = float("inf")
    
    for tau in tau_candidates:
        strategy = ContextAware(tau=tau)
        sq_errs = []
        
        for scores, truth, fcasts in zip(validation_scores, validation_truths, validation_forecasts):
            w = strategy.compute_weights(models, scores=scores)
            blend = sum(w.get(m, 0.0) * fcasts.get(m, 0.0) for m in models)
            sq_errs.append((blend - truth) ** 2)
            
        rmse = np.sqrt(np.mean(sq_errs)) if sq_errs else float("inf")
        if rmse < best_rmse:
            best_rmse = rmse
            best_tau = tau
            
    return best_tau

def save_tau(tau: float, variable: str, lead_day: int, out_dir: str | Path = "results"):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "tau.json"
    
    data = {}
    if out_path.exists():
        with open(out_path) as f:
            data = json.load(f)
            
    data.setdefault(variable, {})[str(lead_day)] = tau
    
    with open(out_path, "w") as f:
        json.dump(data, f, indent=2)

