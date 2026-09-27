"""Case study output writer (B16)."""
from __future__ import annotations

import json
from pathlib import Path


def write_case_study_meta(data: dict, event_name: str, out_dir: str | Path = "results/case_study"):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / f"{event_name}_meta.json", "w") as f:
        json.dump(data, f, indent=2)


def write_case_study_timeline(data: list[dict], event_name: str, out_dir: str | Path = "results/case_study"):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / f"{event_name}_timeline.json", "w") as f:
        json.dump(data, f, indent=2)
