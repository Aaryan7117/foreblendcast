"""Monitoring change points (B15)."""
from __future__ import annotations

import json
from pathlib import Path


def detect_changepoints(time_series: list[float], penalty: float = 1.0) -> list[int]:
    """Detect changes in model error using ruptures PELT algorithm.
    
    Requires 'ruptures' package. Returns indices of change points.
    """
    try:
        import ruptures as rpt
        import numpy as np
        
        signal = np.array(time_series)
        algo = rpt.Pelt(model="l2", min_size=3).fit(signal)
        result = algo.predict(pen=penalty)
        return result[:-1]  # The last index is always the length of the array
    except ImportError:
        # Fallback if ruptures is not installed
        return []


def write_changepoint(data: dict, out_dir: str | Path = "results"):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "changepoint.json", "w") as f:
        json.dump(data, f, indent=2)
