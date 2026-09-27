"""Monsoon regime detection (active/break phases) (B14)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np


def detect_regime(precip_field: np.ndarray, climatology: np.ndarray, land_mask: np.ndarray) -> str:
    """Classify the day as active, break, or normal based on rainfall anomalies.
    
    A simplistic active/break classifier based on central India rainfall anomaly.
    """
    valid = np.isfinite(precip_field) & np.isfinite(climatology) & land_mask
    if not valid.any():
        return "normal"
        
    anomaly = precip_field[valid] - climatology[valid]
    mean_anomaly = float(np.mean(anomaly))
    
    if mean_anomaly > 2.0:
        return "active"
    elif mean_anomaly < -2.0:
        return "break"
    return "normal"


def verify_detector(forecasts: dict[str, np.ndarray], truth: np.ndarray, climatology: np.ndarray, land_mask: np.ndarray) -> dict:
    """Compare forecast regimes with truth regime."""
    truth_regime = detect_regime(truth, climatology, land_mask)
    
    results = {"truth_regime": truth_regime, "forecasts": {}}
    
    for model, field in forecasts.items():
        fc_regime = detect_regime(field, climatology, land_mask)
        results["forecasts"][model] = {
            "regime": fc_regime,
            "match": fc_regime == truth_regime
        }
        
    return results


def write_regime_agreement(data: dict, out_dir: str | Path = "results"):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "regime_agreement.json", "w") as f:
        json.dump(data, f, indent=2)
