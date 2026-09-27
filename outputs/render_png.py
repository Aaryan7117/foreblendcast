"""PNG raster renderer (B13): render georeferenced PNGs for Leaflet overlays.

For each lead: dominant_model, weight_<model>, p_gt_64p5, p_gt_115p6, p_gt_204p5,
precip_pm, disagreement → PNG with fixed colormaps, plus one bounds.json.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap, BoundaryNorm
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

from canonical.grid import BOUNDS, LAT, LON

RASTERS = Path("results/rasters")

# Model-to-integer mapping for dominant_model rasters
MODEL_IDS = {"hres": 0, "ens": 1, "graphcast": 2, "pangu": 3}
MODEL_COLORS = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]

# Probability colormap: white → yellow → orange → red
PROB_CMAP = "YlOrRd"
PRECIP_CMAP = "Blues"
DISAGREE_CMAP = "RdYlGn_r"


def _save_png(data: np.ndarray, path: Path, cmap: str = "viridis",
              vmin: float = 0, vmax: float = 1,
              transparent_below: float | None = None) -> None:
    """Save a 2D array as a georeferenced PNG (no axes, no border)."""
    if not HAS_MPL:
        # Fallback: save raw data
        np.save(path.with_suffix(".npy"), data)
        return

    fig, ax = plt.subplots(1, 1, figsize=(len(LON) / 50, len(LAT) / 50), dpi=100)
    ax.set_axis_off()

    plot_data = data.copy().astype(np.float64)
    if transparent_below is not None:
        plot_data = np.ma.masked_where(plot_data < transparent_below, plot_data)

    ax.imshow(plot_data[::-1], cmap=cmap, vmin=vmin, vmax=vmax,
              aspect="auto", interpolation="nearest")
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=100, transparent=True, bbox_inches="tight", pad_inches=0)
    plt.close(fig)


def render_probability(field: np.ndarray, field_name: str, lead: int) -> Path:
    """Render a probability field as PNG."""
    path = RASTERS / f"{field_name}_L{lead}.png"
    _save_png(field, path, cmap=PROB_CMAP, vmin=0, vmax=1, transparent_below=0.01)
    return path


def render_precip(field: np.ndarray, lead: int, name: str = "precip_pm") -> Path:
    """Render precipitation blend as PNG."""
    path = RASTERS / f"{name}_L{lead}.png"
    _save_png(field, path, cmap=PRECIP_CMAP, vmin=0, vmax=200, transparent_below=0.5)
    return path


def render_dominant_model(model_ids: np.ndarray, lead: int) -> Path:
    """Render dominant model map."""
    path = RASTERS / f"dominant_model_L{lead}.png"
    if HAS_MPL:
        cmap = ListedColormap(MODEL_COLORS[:int(model_ids.max()) + 1])
        _save_png(model_ids.astype(np.float64), path, cmap=cmap,
                  vmin=-0.5, vmax=model_ids.max() + 0.5)
    else:
        np.save(path.with_suffix(".npy"), model_ids)
    return path


def render_disagreement(field: np.ndarray, lead: int) -> Path:
    """Render disagreement index."""
    path = RASTERS / f"disagreement_L{lead}.png"
    _save_png(field, path, cmap=DISAGREE_CMAP, vmin=0, vmax=3)
    return path


def render_weight(field: np.ndarray, model: str, lead: int) -> Path:
    """Render per-model weight field."""
    path = RASTERS / f"weight_{model}_L{lead}.png"
    _save_png(field, path, cmap="viridis", vmin=0, vmax=1)
    return path


def write_bounds() -> Path:
    """Write the bounds.json used by Leaflet ImageOverlay."""
    path = RASTERS / "bounds.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(BOUNDS, indent=2))
    return path


def render_all_for_lead(lead: int,
                        precip_pm: np.ndarray | None = None,
                        probs: dict[str, np.ndarray] | None = None,
                        dominant_model: np.ndarray | None = None,
                        weight_fields: dict[str, np.ndarray] | None = None,
                        disagreement: np.ndarray | None = None) -> list[Path]:
    """Render all rasters for a single lead day."""
    paths = [write_bounds()]

    if precip_pm is not None:
        paths.append(render_precip(precip_pm, lead))

    if probs:
        for name, field in probs.items():
            paths.append(render_probability(field, name, lead))

    if dominant_model is not None:
        paths.append(render_dominant_model(dominant_model, lead))

    if weight_fields:
        for model, field in weight_fields.items():
            paths.append(render_weight(field, model, lead))

    if disagreement is not None:
        paths.append(render_disagreement(disagreement, lead))

    return paths
