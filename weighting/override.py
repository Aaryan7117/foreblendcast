"""Manual overrides for weights (B9).

Reads results/overrides.jsonl, renormalizes weights.
"""
from __future__ import annotations

import json
from pathlib import Path

def apply_overrides(weights: dict[str, float], region_id: str, lead_day: int, variable: str) -> dict[str, float]:
    """Check for manual overrides and apply if present.
    
    overrides.jsonl format:
    {"region": "IN-MH-MUMBAI", "lead_day": 3, "variable": "precip", "weights": {"hres": 0.8, "ens": 0.2}}
    """
    path = Path("results/overrides.jsonl")
    if not path.exists():
        return weights
        
    for line in path.read_text().strip().split("\n"):
        if not line:
            continue
        try:
            record = json.loads(line)
            if (record.get("region") == region_id and 
                record.get("lead_day") == lead_day and 
                record.get("variable") == variable):
                
                # Apply and renormalize
                override_w = record.get("weights", {})
                total = sum(override_w.values())
                if total > 0:
                    return {m: override_w.get(m, 0.0) / total for m in weights}
        except json.JSONDecodeError:
            continue
            
    return weights
