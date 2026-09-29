"""Copy the pipeline outputs into the Android app's bundled snapshot.

    python scripts/sync_android_assets.py

The app falls back to android/app/src/main/assets/data/ when the API is unreachable, so
the snapshot must be the same results/ the dashboard shows. JSON is minified on the way;
geo_districts.json is static geometry and is left alone.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
ASSETS = ROOT / "android" / "app" / "src" / "main" / "assets" / "data"

JSON_FILES = ["ladder.json", "ladder_t2m.json", "ladder_wind.json", "fss_curve.json", "rev.json",
              "where_we_lose.json", "ablation.json", "summary.json", "weights_explain.json",
              "replay.json"]
# rasters the app draws; the dashboard-only ones (per-model weights, GIS products) stay out
RASTER_STEMS = ["precip_pm", "p_gt_64p5", "p_gt_115p6", "p_gt_204p5", "disagreement",
                "dominant_model", "tier", "t2m", "wind", "p_heatwave", "p_wind_8"]
KEEP = {"geo_districts.json"}


def minify(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(json.loads(src.read_text(encoding="utf-8")),
                              separators=(",", ":"), ensure_ascii=False), encoding="utf-8")


def lead_days() -> list[int]:
    days = sorted(int(p.stem.split("_L")[1]) for p in RESULTS.glob("districts_L*.json"))
    return [d for d in days if d >= 1]


def main() -> None:
    leads = lead_days()
    if not leads:
        raise SystemExit("results/ has no district files: run `python -m experiments.run` first")

    for p in ASSETS.rglob("*"):
        if p.is_file() and p.name not in KEEP:
            p.unlink()

    for ld in leads:
        minify(RESULTS / f"districts_L{ld}.json", ASSETS / f"districts_L{ld}.json")
        minify(RESULTS / "rasters" / f"raw_grids_L{ld}.json", ASSETS / "rasters" / f"raw_grids_L{ld}.json")
        for stem in RASTER_STEMS:
            src = RESULTS / "rasters" / f"{stem}_L{ld}.png"
            if src.exists():
                shutil.copyfile(src, ASSETS / "rasters" / src.name)
    for name in JSON_FILES:
        if (RESULTS / name).exists():
            minify(RESULTS / name, ASSETS / name)
    for p in (RESULTS / "points").glob("*.json"):
        minify(p, ASSETS / "points" / p.name)
    for name in ("bounds.json",):
        minify(RESULTS / "rasters" / name, ASSETS / "rasters" / name)
    for name in ("truth.png", "replay_truth.png", *(f"replay_L{d}.png" for d in (1, 3, 5))):
        if (RESULTS / "rasters" / name).exists():
            shutil.copyfile(RESULTS / "rasters" / name, ASSETS / "rasters" / name)

    (ASSETS / "snapshot.json").write_text(json.dumps({
        "lead_days": leads,
        "generated_utc": json.loads((RESULTS / "ladder.json").read_text(encoding="utf-8"))["meta"]["generated_utc"],
    }), encoding="utf-8")
    size = sum(p.stat().st_size for p in ASSETS.rglob("*") if p.is_file()) / 1e6
    print(f"snapshot: lead days {leads}, {size:.1f} MB in {ASSETS}")


if __name__ == "__main__":
    main()
