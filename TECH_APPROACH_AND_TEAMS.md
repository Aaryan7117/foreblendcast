# SIH26081 — Tech Approach & Two-Team Work Split

**Version:** v1.0 — 27 September 2026
**Binding on:** `SIH26081_MASTER_PLAN.md` §7–§9, §13. Where MASTER_PLAN §9 says "X or Y", **this document picks one.**
**Companion:** `DECISIONS.md` (decisions D-18 → D-30 appended from this document).

---

## 0. What this document settles

1. **Every "or" in the tech stack becomes a single choice**, with the rejected alternative and the reason (§1).
2. **The concrete algorithm for every module** — not just the library, but the method, the formula, the parameters (§2).
3. **The data contract between the two teams** — exact files, exact JSON shapes, who writes, who reads (§3). This is what lets the teams work in parallel from hour one.
4. **The two-team split** — charters, ownership, a day-by-day plan per team, sync rituals, and the fixture policy that keeps Team B productive before real numbers exist (§4).
5. **Scaffold** — the exact `environment.yml`, `package.json` dependencies, and first commands (§5).
6. **Open items with a decision rule** so nobody waits on a meeting (§6).

---

# 1. Tech Decisions — Locked

## 1.1 Backend / Science

| Area | **CHOSEN** | Rejected | Why |
|---|---|---|---|
| Language / runtime | **Python 3.11**, conda-forge | 3.12 | Widest wheel/conda coverage for `eccodes`, `xskillscore`, `numba` deps; zero surprises |
| Env manager | **mamba / conda-forge** (`environment.yml`) | pip + venv | `eccodes` (for `cfgrib`) is a C library — conda-forge is the only sane path on Windows (D-09) |
| Container | **Docker on `condaforge/mambaforge`** base | python-slim + pip | Same reason; one Dockerfile works on the HPC story and on a laptop |
| Array / IO | **xarray + dask + zarr + gcsfs + netCDF4 + h5netcdf + cfgrib** | — | `gcsfs` for `gs://weatherbench2`; `dask` for lazy region subsetting; `cfgrib` for the GRIB2 proof |
| Schema / validation | **pydantic v2** | dataclasses | The quality gate *is* validation; pydantic gives it for free, with clear error messages in logs |
| Canonical grid | **The IMD 0.25° rainfall grid itself** (lat 6.5→38.5 N, lon 66.5→100 E, 129 × 135) | a custom 0.25° grid | Truth is never regridded. WB2 0.25° products land on it with a near-identity alignment |
| Regridding | **`xarray.interp` bilinear** (T, wind, and rain) | `xesmf` conservative | `xesmf`/ESMF has no Windows conda build — a trap. WB2 is already 0.25° so it is an offset alignment, not a real regrid. Caveat noted in limitations. |
| Geospatial | **geopandas + shapely 2 + regionmask + rioxarray + rasterio** | pure shapely loops | `regionmask` rasterises 730 district polygons onto the grid once, then every zonal stat is a `groupby` |
| Zonal stats | **`regionmask` mask → `xarray.groupby` → weighted quantile** | rasterstats | One mask, all statistics, no per-district loops |
| ML (quantile / weights) | **LightGBM** | XGBoost | Native `objective='quantile'`, faster on CPU, lighter install |
| Calibration | **scikit-learn `IsotonicRegression`** | Platt / Beta / EMOS | One method done properly (MASTER_PLAN §7.7); others are compared only if time |
| Verification | **xskillscore + properscoring + custom `fss.py` + custom `economic_value.py`** | climpred | Everything else is a thin wrapper on these |
| FSS kernel | **`scipy.ndimage.uniform_filter`** on binary fields | convolution by hand | Standard, fast, exact |
| Bootstrap | **custom block bootstrap** (`numpy`), block = 7 days | `arch` | Trivial to write, no dep |
| Change-point | **`ruptures`** (PELT, `l2` cost) | hand-rolled CUSUM | 5 lines, proven; CUSUM as a fallback if the install fights |
| Config | **plain YAML via `pyyaml` + a pydantic `ExperimentConfig`** | hydra | Hydra is a day of learning curve; we have four days |
| CLI | **`argparse`** | typer / click | Zero deps, never breaks |
| Scheduler | **`cron` inside the Docker image** running `run_cycle.py` | Prefect | Prefect is a real product but a half-day of setup; cron is 3 lines and *is* what NCMRWF runs. Prefect named as the production upgrade path. |
| API | **FastAPI + uvicorn**, ≤ 6 endpoints | Flask | Auto OpenAPI docs are a free slide; async static file serving |
| Output: NetCDF | **xarray `to_netcdf` + explicit CF-1.8 attrs** | — | |
| Output: GeoTIFF | **rioxarray `rio.to_raster`** | GDAL CLI | |
| Output: CAP 1.2 | **`lxml` from a template** | — | `status=Exercise` hard-coded (D-13) |
| Tests | **pytest** | — | The four guard tests in MASTER_PLAN §8 |
| Logging | **`structlog`** → JSON lines | print | Physical-validator corrections and QC rejections must be machine-readable |
| Reproducibility | **`Makefile`** (`make data`, `make train`, `make ladder`, `make reproduce`) | invoke / just | `make` exists everywhere incl. Git Bash on Windows |

## 1.2 Frontend / Product

| Area | **CHOSEN** | Rejected | Why |
|---|---|---|---|
| Build | **Vite** | CRA / Next | Instant HMR, static build, no server needed for the demo |
| Framework | **React 18 + TypeScript** | Vanilla JS | Six panels share state (variable, lead, district, layer). Vanilla = prop-passing hell by day two. TS types are **generated from the data contract** (§3) so a backend shape change is a compile error, not a demo-day surprise |
| State | **zustand** (one store) | Redux / Context | 1 KB, no boilerplate, works outside React tree (Leaflet callbacks) |
| Map | **Leaflet + react-leaflet** | Mapbox GL | No token, no account, no billing, offline-capable for the demo. GeoJSON districts + `ImageOverlay` PNG rasters |
| Raster overlays | **Backend pre-renders georeferenced PNGs** (`matplotlib` → PNG + `bounds.json`) | client-side rendering of NetCDF | Zero client compute, pixel-perfect colormaps, trivially cached |
| Charts | **Plotly.js (react-plotly.js)** | Chart.js | Reliability diagrams, REV curves, FSS-vs-scale, CDFs and spaghetti-with-bands are all native; Chart.js needs plugins for half of them |
| Styling | **Tailwind CSS** with a dark token palette | vanilla CSS | Fastest to a consistent dark theme without a designer; one config file |
| Colours | **IMD warning tiers** `#2E7D32` green · `#F9A825` yellow · `#EF6C00` orange · `#C62828` red; **viridis** for probability rasters; **categorical set** per model (fixed order: GFS, ECMWF, GraphCast, …) | ad hoc | Same colour = same model on every screen |
| Data access | **Static files** from `frontend/public/data/` (symlink or copy of `results/`) | live API during demo | The demo never depends on a running backend. FastAPI is shown separately as "operational path" |
| Deck | **Google Slides / PowerPoint** — whichever the presenter owns | reveal.js | Do not engineer the slides |
| Demo backup | **OBS screen recording, 1920 × 1080, 3 min** | — | Non-negotiable (MASTER_PLAN S4.9) |

## 1.3 Shared

| Area | **CHOSEN** |
|---|---|
| Repo | Single monorepo `sih26081-blend/` (MASTER_PLAN §8), `main` always runnable, feature branches `A/<thing>`, `B/<thing>` |
| Line endings | `.gitattributes` with `* text=auto eol=lf` — kills the CRLF warnings seen at first commit |
| Data hand-off | **Files in `results/`** — never a DB, never a socket. §3 is the contract |
| Fixtures | `frontend/fixtures/` only, `"fixture": true` flag, watermark rendered, **build step refuses to ship them** (§4.5) |

---

# 2. Algorithm Approach — Per Module

Concrete method per module. Parameters are starting values; anything fitted is written to `results/params/`.

### 2.1 Ingestion → Canonical (`ingestion/`, `canonical/`)
- **WB2 access:** `xr.open_zarr("gs://weatherbench2/datasets/<product>/<years>-<res>.zarr", storage_options={"token":"anon"})` → `.sel(latitude=slice(38.5,6.5), longitude=slice(66.5,100))` → `.to_zarr("data/raw/<model>.zarr")`. **Exact product paths confirmed in P-3** (§6).
- **Longitude convention:** canonical is 0–360 (matches WB2 and IMD); adapter flips −180–180 sources.
- **Latitude ordering:** canonical is **ascending** (6.5 → 38.5); adapter flips descending sources.
- **Accumulation (D-01):** WB2 stores `total_precipitation_6hr` (or 24hr) on UTC steps. `canonical/accumulation.py` sums the 6-h steps whose valid times fall in `[D 03:00, D+1 03:00)` UTC. For a 00Z init that is steps ending 09, 15, 21, 03 → lead 27 h. Temperature: Tmax/Tmin taken over the same window. **`test_accumulation.py` hand-checks one date against IMD.**
- **Units:** rain → mm; T → °C; wind → m s⁻¹ (u, v kept separately; speed derived only after blending).
- **Quality gate:** pydantic model + range checks (rain 0–600 mm/24 h, T −40…55 °C, |wind| < 80 m s⁻¹, NaN fraction < 5 % over land). Failure → `structlog` event `qc.reject` with reason; the file is skipped, the cycle continues.

### 2.2 Region hierarchy (used by shrinkage, context weights, stratification)
```
cell (0.25°)
 └─ district (730, from datameet GeoJSON via regionmask)
     └─ IMD meteorological subdivision (36)
         └─ IMD homogeneous region (NW India, Central/NE, South Peninsula, NE India — 4)
             └─ national
```
Terrain class (for §6.K stratification) is an **orthogonal** label per cell from SRTM: `ghats_windward` (lon < Ghats crest & elev > 300 m), `ghats_leeward`, `himalayan_foothills` (elev 300–2000 m, lat > 26), `plains`, `coastal` (≤ 25 km from coastline). Definitions live in `canonical/terrain.py` and are printed in the limitations appendix.

### 2.3 Verification (`verification/`)
- **Deterministic:** RMSE, MAE, bias per (model, variable, lead, cell); aggregated with land-area weights.
- **Frequency bias:** `(# forecast ≥ thr) / (# observed ≥ thr)` at 15.6 / 64.5 / 115.6 / 204.5 mm.
- **FSS:** binary fields at threshold → `uniform_filter(size=n)` for n = {1, 5, 9, 19, 29} cells ≈ {5, 25, 50, 100, 150} km at 0.25° (≈ 27 km/cell — the labels are nominal) → `FSS = 1 − Σ(Pf−Po)² / (ΣPf² + ΣPo²)`. Report `f₀` and `FSS_useful = 0.5 + f₀/2` on every curve.
- **Probabilistic:** Brier, BSS vs. climatological frequency, reliability (10 bins), ROC-AUC, CRPS (properscoring, from member ensemble).
- **Relative Economic Value:** from the 2×2 contingency table at each probability threshold p*, over C/L ∈ [0.01, 0.99]: `REV = (min(C/L, o) − F·C/L·(1−o) − M·o·(1−C/L)... )` — implement the standard Richardson (2000) form; plot the **envelope** over p*. Report at C/L = 0.1 in the headline.
- **Block bootstrap:** resample 7-day blocks of valid dates, 1000 reps, CI on **differences** (blend − best single).
- **Stratified:** every metric additionally `groupby(terrain_class)`, `groupby(season)`, `groupby(lead_day)`.

### 2.4 Weighting (`weighting/`)
- **Error database:** `errors.zarr` indexed `(model, variable, lead_day, valid_date, lat, lon)` holding signed error and |error|. Everything else derives from this.
- **Inverse-error:** `w_i ∝ 1 / (RMSE_i,trailing30d + ε)`, per (model, variable, lead_day, cell).
- **Context-aware:** `score[m, v, region, lead, season, regime] = mean |error|` over training folds; `w = softmax(−score/τ)`.
- **Shrinkage (§6.B):** `λ = n_eff / (n_eff + k)`, `k = 20` to start (fitted on validation among {10, 20, 50}); `n_eff = n / (1 + 2·ρ₁)` with lag-1 autocorrelation ρ₁ of the error series. Below `n_eff < 15` → inherit parent, set `explanation.reason = "insufficient_local_history"`.
- **τ fitting (D-05):** grid {0.1, 0.2, 0.5, 1, 2, 5} × trailing-RMSE units, per (variable, lead-band {1–3, 4–6, 7–10}), chosen on the validation fold by CRPS of the blend.
- **Spatial coherence:** Gaussian filter σ = 1 cell on the weight field, **masked** so the filter does not cross the terrain-class boundary between `ghats_windward` and `ghats_leeward`.
- **Oracle:** per (cell, date, lead) pick the model with min |error|. Ceiling only — never shipped as a forecast.
- **Climatology floor:** per-cell, per-calendar-day mean of IMD obs over training years, ±15-day window. **Persistence:** yesterday's observation.
- **Override:** `weighting/override.py` reads `results/overrides.jsonl` (append-only) and multiplies/renormalises; every entry has `user, ts, scope, reason, before, after`.

### 2.5 Blending (`blending/`)
- **Deterministic (T, u, v):** weighted mean.
- **Rain — probability-matched (§6.A / D-11):**
  ```
  M   = Σ w_i F_i                         # location field
  pool = concat_i(F_i) with weights w_i   # intensity pool (land cells only)
  q    = rank(M) / N                      # each cell's rank in M
  B    = weighted_quantile(pool, q)       # remap
  ```
  Applied per lead per day over the land mask. Ships both `M` and `B`; the ladder has a rung for each.
- **Physical validator:** logged corrections only (rain < 0 → 0; Tmax < Tmin → swap + log; speed derived from blended u, v). Counts to `results/validator_log.jsonl`.

### 2.6 Hazards & calibration (`hazards/`, `calibration/`)
- **Predictive distribution for rain:** LightGBM quantile regression at q ∈ {0.05, 0.1, …, 0.95} with features = member values, blend `B`, spread, lead, season, terrain class, regime flag. **Fallback if time is short:** empirical member ensemble + spread-inflation.
- **P(X > thr):** read off the quantile function.
- **Calibration:** isotonic on (raw p, observed binary) from the training fold, **one calibrator per availability pattern** in `{full, minus_gfs, minus_ecmwf, minus_graphcast}`.
- **Heatwave:** IMD rule on blended Tmax vs. per-cell climatology; hills mask from SRTM > 1000 m (plains ≥ 40 °C, hills ≥ 30 °C, departure ≥ 4.5 °C, ≥ 2 consecutive days).
- **Wind:** speed from blended (u, v); IMD thresholds flagged; verified vs. ERA5 only (D-06).
- **Disagreement index (§6.F):** `D = std_i(F_i) / clim_std[cell, month, regime]`, where `clim_std` is the training-period mean member spread. `D > 1.5` → "attention".
- **District category (D-07):** area-weighted 90th percentile of the cell probability within the district polygon → tier by `P(>64.5) ≥ 0.4 → Yellow`, `P(>115.6) ≥ 0.3 → Orange`, `P(>204.5) ≥ 0.2 → Red` (starting thresholds; re-tuned on the validation fold to maximise REV at C/L = 0.1 — and the tuned values are printed).

### 2.7 Regimes (`regimes/`)
- **Heavy-rain / Active-Break flag:** forecast rainfall averaged over the IMD core-monsoon-zone box (18–28 N, 65–88 E) vs. its climatology; active if > +1σ, break if < −1σ, else neutral. **Forecast-derived at the blended lead (D-04).**
- **Verification (§6.G):** same rule on IMD obs → confusion matrix per lead day → agreement %.
- WD / cyclone detectors: **P3 only**, after everything in MASTER_PLAN §13.5 is green.

### 2.8 Monitoring (`monitoring/change_point.py`)
- Per (model, variable, lead-band): national land-mean |error| daily series → 30-day rolling mean → `ruptures.Pelt(model="l2", min_size=60).fit(series).predict(pen=…)`. Detected dates plotted against known IFS cycle dates. On detection: `history_days` for that model resets to the post-change window.

### 2.9 Outputs (`outputs/`)
- **NetCDF:** one file per cycle `blend_YYYYMMDDTHHZ.nc` with variables `precip_24h`, `t2m_max`, `t2m_min`, `wind10_speed`, `p_rain_gt_64p5`, `p_rain_gt_115p6`, `p_rain_gt_204p5`, `weight_<model>`, `disagreement`; global attrs = the provenance block (MASTER_PLAN §7.11); `Conventions = "CF-1.8"`.
- **GeoTIFF:** same fields, EPSG:4326, one band per lead.
- **CAP 1.2:** one `<alert>` per district at Orange/Red, `<status>Exercise</status>`, `<msgType>Alert</msgType>`, `<scope>Public</scope>`, polygon from district GeoJSON.
- **PNG rasters for the UI:** `matplotlib` with fixed colormap and `bounds.json` — see §3.

### 2.10 API (`api/`) — six endpoints, no more
```
GET /health
GET /cycles                          → list of available cycles
GET /cycles/{cycle}/ladder           → results/ladder.json
GET /cycles/{cycle}/districts/{lead} → results/districts_L{lead}.json
GET /cycles/{cycle}/points/{city}    → results/points/{city}.json
GET /cycles/{cycle}/netcdf           → file download
```
Plus `StaticFiles` mount of `results/` at `/data`. The dashboard **does not** call these during the demo; they exist to prove the operational path and to show the auto-generated OpenAPI page.

---

# 3. Data Contract — the interface between the two teams

**Team A writes `results/`. Team B reads it. Nothing else crosses the boundary.**
Every file has a `meta` block. TypeScript types are generated from these shapes (`frontend/src/types/results.ts`) on day one and committed; a schema change requires a PR touching both sides.

```
results/
├── provenance.json
├── ladder.json
├── tau.json
├── fss_curve.json
├── reliability.json
├── rev.json
├── where_we_lose.json
├── regime_agreement.json
├── changepoint.json
├── validator_log.jsonl
├── overrides.jsonl
├── districts_L{1..10}.json
├── weights_L{1..10}.json
├── disagreement_L{1..10}.json
├── points/{city_slug}.json
├── rasters/
│   ├── {field}_L{lead}.png            field ∈ precip_blend | precip_pm | p_gt_64p5 | p_gt_115p6 |
│   │                                           p_gt_204p5 | dominant_model | weight_{model} | disagreement
│   └── bounds.json                    {"north":38.5,"south":6.5,"east":100,"west":66.5}
├── case_study/
│   ├── meta.json                      {event, dates, out_of_sample: true, fold}
│   ├── timeline.json                  per issue date: per model, blend, obs, tier
│   └── rasters/…                      same PNG convention
└── netcdf/blend_{cycle}.nc
```

### 3.1 Common `meta` block (every JSON file)
```json
"meta": {
  "cycle": "2022-07-15T00Z",
  "generated_utc": "2026-09-28T14:03:11Z",
  "git_commit": "67a442b",
  "fixture": false,
  "ground_truth": "IMD_0p25_rain|ERA5",
  "models_used": ["gfs","ecmwf","graphcast"],
  "availability_pattern": "full",
  "strategy": "context_shrink_pm",
  "accumulation_window_utc": "03:00-03:00",
  "district_aggregation": "area_weighted_p90",
  "status": "EXERCISE - NOT AN OFFICIAL IMD WARNING"
}
```

### 3.2 `ladder.json`
```json
{ "meta": {...},
  "variable": "precip", "lead_days": [1,2,3,5,7,10],
  "rows": [
    { "rung": "floor", "strategy": "climatology",
      "metrics": { "L1": { "rmse": 0.0, "mae": 0.0, "fss50": 0.0, "freq_bias_64p5": 0.0, "rev_cl0p1": 0.0,
                           "ci_rmse_vs_best_single": [0.0, 0.0] }, "L2": {...} } },
    { "rung": "single", "strategy": "gfs", "metrics": {...} },
    { "rung": "blend",  "strategy": "context_shrink_pm", "metrics": {...} },
    { "rung": "ceiling","strategy": "oracle", "metrics": {...} }
  ],
  "headline": { "best_single": "ecmwf", "ours": "context_shrink_pm",
                "pct_of_achievable_gain": { "L1": 0.0, "L3": 0.0 } } }
```

### 3.3 `districts_L{lead}.json`
```json
{ "meta": {...}, "lead_day": 3,
  "districts": [
    { "id": "MH-RATNAGIRI", "name": "Ratnagiri", "state": "Maharashtra",
      "precip_p90_mm": 0.0, "tmax_c": 0.0, "wind_ms": 0.0,
      "p_gt_64p5": 0.0, "p_gt_115p6": 0.0, "p_gt_204p5": 0.0,
      "tier": "orange",
      "heatwave": false,
      "population": 0, "population_source": "WorldPop 2020",
      "disagreement": 0.0,
      "weights": { "gfs": 0.0, "ecmwf": 0.0, "graphcast": 0.0 },
      "lomo_rmse_increase_pct": { "gfs": 0.0, "ecmwf": 0.0, "graphcast": 0.0 },
      "shrinkage": { "level_used": "subdivision", "n_eff": 0, "reason": "insufficient_local_history" } }
  ] }
```

### 3.4 `weights_L{lead}.json` (district-level summary; the gridded version is the PNG + NetCDF)
```json
{ "meta": {...}, "lead_day": 3, "variable": "precip", "season": "JJAS",
  "by_district": { "MH-RATNAGIRI": { "gfs": 0.0, "ecmwf": 0.0, "graphcast": 0.0, "dominant": "ecmwf" } } }
```

### 3.5 `points/{city_slug}.json` (spaghetti panel)
```json
{ "meta": {...}, "city": "Mumbai", "lat": 19.07, "lon": 72.88, "variable": "precip",
  "lead_days": [1,2,3,4,5,6,7,8,9,10],
  "members": { "gfs": [..10..], "ecmwf": [..10..], "graphcast": [..10..] },
  "blend": [..10..], "q05": [..10..], "q95": [..10..],
  "disagreement": [..10..], "obs": [..10 or null..] }
```

### 3.6 `rev.json`, `reliability.json`, `fss_curve.json`
```json
"rev":         { "meta":{...}, "cost_loss": [0.01,...,0.99], "curves": { "blend":[...], "ecmwf":[...], "gfs":[...] }, "headline_cl": 0.1 }
"reliability": { "meta":{...}, "threshold_mm": 64.5, "bins": [0.05,...,0.95], "observed_freq": {"blend":[...], "blend_uncal":[...]}, "counts": {...}, "brier": {...}, "auc": {...} }
"fss_curve":   { "meta":{...}, "threshold_mm": 64.5, "scales_km": [5,25,50,100,150], "f0": 0.0, "fss_useful": 0.0, "curves": { "blend":[...], "ecmwf":[...], "gfs":[...] } }
```

### 3.7 `where_we_lose.json`
```json
{ "meta":{...}, "cells": [ { "district": "…", "lead_day": 7, "season": "JJAS", "regime": "break",
   "blend_rmse": 0.0, "best_single": "ecmwf", "best_single_rmse": 0.0, "ci": [0.0,0.0],
   "reason": "shrinkage_to_national|regime_misclassified|member_collapse", "override_available": true } ] }
```

### 3.8 `changepoint.json`, `regime_agreement.json`
```json
"changepoint":      { "meta":{...}, "model":"ecmwf", "series_dates":[...], "series":[...], "detected":["2021-05-11"], "known_upgrades":["2021-05-11"] }
"regime_agreement": { "meta":{...}, "lead_days":[1,3,5,7,10], "agreement_pct":[...], "confusion": {"L3": [[..],[..],[..]]} }
```

### 3.9 Fixtures
`frontend/fixtures/` contains one file per contract with **`"fixture": true`** and obviously-fake values (all probabilities 0.5, all RMSE 1.0). The UI renders a full-screen diagonal **"FIXTURE DATA — NOT RESULTS"** watermark whenever `meta.fixture === true`. `npm run build:demo` **exits non-zero** if any file under `public/data/` has `fixture: true`.

---

# 4. Two-Team Split

## 4.1 Charters

| | **Team A — ENGINE** | **Team B — PRODUCT & PLATFORM** |
|---|---|---|
| **Mission** | Produce **real, verified numbers**. Own every value in `results/`. | Carry the numbers to the judges. Own everything a judge *sees*. |
| **Owns (repo)** | `ingestion/ canonical/ verification/ weighting/ blending/ regimes/ hazards/ calibration/ monitoring/ experiments/ evaluation/ tests/ environment.yml Makefile (science targets)` | `frontend/ api/ outputs/ docker/ README.md deck/ demo/ results/rasters (renderer) Makefile (serve/build targets)` |
| **Owns (decisions)** | D-01, 02, 03, 04, 05, 06, 10, 11, 12 | D-07 (UI toggles), 13, 14, 15 |
| **Success = ** | MASTER_PLAN §13.5 items 1–4, 7, 8 green | §13.5 items 5, 6, 9–12 green |
| **Never does** | Frontend, slides, README prose | Change a number; write to `results/` except `rasters/` |
| **Minimum staffing** | 2 (one on ingestion/canonical/verification, one on weighting/blending/hazards) | 2 (one frontend, one platform+deck) |
| **If 3rd person** | → verification/FSS/REV/bootstrap specialist | → deck + case study narrative + demo video |

## 4.2 Day-by-day — Team A (Engine)

| Day | Focus | Deliverables (files that appear) | Checkpoint |
|---|---|---|---|
| **Sat 27 · AM** | P-2 env, P-3 inventory, canonical schema, accumulation | `environment.yml` verified; `data/raw/*.zarr` subset started; `canonical/forecast.py`, `accumulation.py` + `test_accumulation.py` green | **P-3 result → §6.1 decision by noon** |
| **Sat 27 · PM** | Adapters, registry, QC gate, alignment, equal blend | `ingestion/{gfs,ecmwf,graphcast,registry}.py`, `quality_gate.py` + test, `grid.py`, `weighting/equal.py`, `experiments/run.py --strategy equal` → `.nc` | **CP-1:** plottable blended rain grid, window verified |
| **Sun 28 · AM** | Truth loader, sample histogram, deterministic + FSS + floors | `verification/{deterministic,fss}.py` + `test_fss.py`, `weighting/{climatology,persistence}.py`, `results/sample_counts.json` | Sample histogram reviewed → ladder rungs confirmed |
| **Sun 28 · PM** | Folds + leakage test, inverse-error, bootstrap, **ladder v1**, intensity CDF, **first real `results/` drop** | `experiments/folds.py` + `test_leakage.py`, `weighting/inverse_error.py`, `verification/bootstrap.py`, `results/ladder.json`, `results/districts_L*.json` (rain only), `results/points/*.json` | **CP-2:** ladder with real numbers + CIs; **Team B switches off fixtures** |
| **Mon 29 · AM** | Context weights, shrinkage, τ, **probability matching**, physical validator | `weighting/{context,shrinkage,tau_fit}.py`, `blending/{probability_matched,physical}.py`, `results/tau.json`, ladder rungs added | PM rung on the ladder |
| **Mon 29 · PM** | Extremes + isotonic, REV, oracle, disagreement, LOMO, regime flag + verify, terrain cuts, minus-one table | `hazards/*`, `calibration/*`, `verification/{economic_value,stratify}.py`, `weighting/oracle.py`, `regimes/*`, `results/{rev,reliability,where_we_lose,regime_agreement}.json`, `districts_L*.json` full | **CP-3:** every contract file real; `where_we_lose.json` exists |
| **Tue 30 · AM** | Case study (July 2023 or fallback), change-point, spatial smoothing, `make reproduce` | `results/case_study/*`, `results/changepoint.json`, `Makefile reproduce` target + log | `make reproduce` runs clean end-to-end |
| **Tue 30 · PM** | **Freeze `results/`** at 14:00. Number sweep with Team B. TimesFM only if everything above is green. | tag `v1.0-results` | Numbers in deck == numbers in `results/` |

## 4.3 Day-by-day — Team B (Product & Platform)

| Day | Focus | Deliverables | Checkpoint |
|---|---|---|---|
| **Sat 27 · AM** | Repo plumbing, downloads D5–D9, contract types, fixtures | `.gitattributes`, `frontend/` scaffold (Vite + React + TS + Tailwind + zustand + react-leaflet + plotly), `src/types/results.ts` generated from §3, `frontend/fixtures/*` with watermark logic, district GeoJSON simplified (`mapshaper -simplify 10%`) and keyed by the `id` scheme in §3.3 | App boots on fixtures with watermark |
| **Sat 27 · PM** | Traffic-light board, EXPERIMENTAL banner, layout shell, raster renderer | `DistrictMap.tsx` (GeoJSON, tier colours, D-07 toggle, popup skeleton), `Banner.tsx`, app shell with variable/lead controls in zustand, `outputs/render_png.py` (colormaps fixed, `bounds.json`) tested on the CP-1 `.nc` | Board renders from fixtures; renderer produces a PNG from CP-1 output |
| **Sun 28 · AM** | Weight map + LOMO hover, ladder panel, spaghetti | `WeightMap.tsx` (ImageOverlay + district hover from `weights_L*.json`), `LadderTable.tsx`, `Spaghetti.tsx` (Plotly with q05–q95 band) | All three on fixtures |
| **Sun 28 · PM** | **Switch to real data (CP-2)**, decision card, API scaffold, Docker | `public/data` → real `results/`; `DecisionCard.tsx` with provenance footer; `api/main.py` 6 endpoints; `docker/Dockerfile` + `crontab` for `run_cycle.py` | Dashboard shows real ladder + real district tiers; `docker build` passes |
| **Mon 29 · AM** | REV panel, reliability + FSS panels, attention overlay, where-we-lose map | `RevCurve.tsx`, `Reliability.tsx`, `FssCurve.tsx`, `DisagreementLayer.tsx`, `WhereWeLose.tsx` | Renders as soon as A drops the files (fixtures until then) |
| **Mon 29 · PM** | Outputs: CF-NetCDF attrs + GeoTIFF + CAP; README; deck skeleton | `outputs/{netcdf,geotiff,cap,provenance}.py` on A's `.nc`; `README.md` with architecture + setup; 12-slide skeleton with `?.??` placeholders | **CP-3:** every panel on real data; CAP file validates against the 1.2 XSD |
| **Tue 30 · AM** | Case-study replay panel, change-point plot, leaderboard, `build:demo` gate, guided-tour banner | `CaseStudy.tsx`, `ChangePoint.tsx`, `Leaderboard.tsx`, `npm run build:demo` refuses fixtures | Full click-through works |
| **Tue 30 · PM** | **Number sweep with Team A**, deck final, limitations + licence slides, OBS recording, repo cleanup | deck v1.0, `demo/demo.mp4`, README final, tag `v1.0-submission` | Recording done **before** live-demo rehearsal |

## 4.4 Sync rituals (fixed, short)

| When | What | Length |
|---|---|---|
| **09:00 daily** | Contract check: did any `results/` shape change? Which files will land today, by when? | 10 min |
| **14:00 daily** | Unblock: anything waiting on the other team? | 5 min |
| **20:00 daily** | Integration: Team B pulls today's `results/`, runs the app, both teams look at one screen together | 15 min |
| **Checkpoints CP-1/2/3** | Named in §4.2/4.3. **A checkpoint failing stops feature work on both teams until it passes.** | as needed |

Communication channel: one group chat, one pinned message = today's expected `results/` drops with ETA. No DMs about contract changes.

## 4.5 Rules that keep the split from breaking

1. **Team B never invents a number.** Fixtures are flagged, watermarked, and cannot be built into the demo. If a panel has no real data by the deck freeze, the panel is cut — not faked.
2. **Team A never touches presentation.** If A wants a chart in the deck, A writes the JSON; B draws it.
3. **A contract change = a PR that edits `results/` writer, `types/results.ts`, and the fixture, together.** Reviewed by one person from each team.
4. **`results/` freezes Tue 14:00.** After that, only `where_we_lose.json` and the number sweep may change, and only by tagging a new `results` version.
5. **Cut order is MASTER_PLAN §13.6.** Either lead can invoke it; neither needs permission.

## 4.6 Load balance sanity check
Team A has the harder science; Team B has more surface area. The balance holds because B also owns *platform* (API, Docker, outputs, CAP), *narrative* (deck, README, case study), and *downloads D5–D9*. If A falls behind, the first thing moved to B is `outputs/render_png.py` → already B's. The second is `evaluation/plots.py` (matplotlib versions of REV/reliability/FSS for the deck) → B can draw those from the JSON with Plotly export instead. **Nothing in the weighting/verification chain is ever moved to B.**

---

# 5. Scaffold — exact starting artefacts

### 5.1 `environment.yml`
```yaml
name: sih26081
channels: [conda-forge]
dependencies:
  - python=3.11
  - xarray>=2024.6
  - dask
  - zarr
  - gcsfs
  - netcdf4
  - h5netcdf
  - cfgrib
  - eccodes
  - numpy
  - scipy
  - pandas
  - geopandas
  - shapely>=2
  - regionmask
  - rioxarray
  - rasterio
  - matplotlib
  - lightgbm
  - scikit-learn
  - xskillscore
  - properscoring
  - ruptures
  - pydantic>=2
  - pyyaml
  - structlog
  - fastapi
  - uvicorn
  - lxml
  - pytest
  - pip
  - pip:
      - timesfm   # optional; install only if S4.6 is reached
```
Verify: `mamba env create -f environment.yml && conda activate sih26081 && python -c "import cfgrib, xarray as xr; print(cfgrib.__version__)"`.

### 5.2 `frontend/package.json` dependencies
```
react react-dom zustand leaflet react-leaflet plotly.js-dist-min react-plotly.js
devDependencies: vite @vitejs/plugin-react typescript tailwindcss postcss autoprefixer @types/leaflet @types/react @types/react-dom
```
Scaffold: `npm create vite@latest frontend -- --template react-ts && cd frontend && npm i zustand leaflet react-leaflet plotly.js-dist-min react-plotly.js && npm i -D tailwindcss postcss autoprefixer @types/leaflet && npx tailwindcss init -p`.

### 5.3 `Makefile` targets
```
make env        # mamba env create
make data       # run all downloads (idempotent)
make inventory  # P-3: print precip availability table
make test       # pytest tests/
make ladder     # run every strategy, write results/ladder.json
make results    # everything under results/
make rasters    # outputs/render_png.py
make serve      # uvicorn api.main:app
make demo       # cd frontend && npm run build:demo
make reproduce  # data → test → results → rasters, logs to reproduce.log
```

### 5.4 `.gitattributes`
```
* text=auto eol=lf
*.png binary
*.nc binary
*.zarr/** binary
```

### 5.5 First commands, in order (Sat 27 morning)
```bash
git checkout -b A/env && mamba env create -f environment.yml          # Team A
git checkout -b B/scaffold && npm create vite@latest frontend ...       # Team B
python -m ingestion.inventory --box 6.5,38.5,66.5,100 --years 2018-2023  # Team A, P-3, output pasted into DECISIONS.md
```

---

# 6. Open Items with Decision Rules (no meeting needed)

| # | Question | Decision rule | Owner | Deadline |
|---|---|---|---|---|
| **6.1** | **Does WB2 hold 2023 for HRES/GFS/GraphCast?** The public WB2 archives are widely documented as ending in **2022**; D-02's "2020–2023" may be unfulfillable. | **If 2023 absent:** year range becomes **2018–2022** (the stretch range is now the *required* range); folds = Train 2018–20/Test 2021, Train 2018–21/Test 2022 (still 2 held-out seasons); case study becomes **Assam–Meghalaya floods, June 2022** (in the 2022 test fold), alt. Cyclone Asani May 2022. Append as D-18 in `DECISIONS.md`. | Team A | Sat 27, noon |
| **6.2** | Does GraphCast (and any AI model) provide usable 24-h precipitation over the India box? | **If no:** activate MASTER_PLAN §7.3 split — rain pool = {GFS, IFS HRES, + IFS ENS/GEFS if present}; T/wind pool adds GraphCast. Ladder tables are per-pool. Append as D-19. | Team A | Sat 27, noon |
| **6.3** | IMD gridded rain granted in time? | **If not by Sun 28 09:00:** ERA5 is the prototype truth for rain with the explicit caveat; `meta.ground_truth = "ERA5"` on every file so the UI footer says so automatically. | Team A | Sun 28, 09:00 |
| **6.4** | LightGBM quantile model or empirical-ensemble fallback for the predictive distribution? | **If Mon 29 12:00 and the quantile model isn't producing calibrated output:** ship the empirical fallback; note it in limitations. | Team A | Mon 29, noon |
| **6.5** | React unfamiliar to the frontend person? | **Decide Sat 27 09:00.** If yes → keep Vite + TS but drop to a small vanilla module per panel with a shared `store.ts`; everything else in §1.2 stands. | Team B | Sat 27, 09:00 |
| **6.6** | Deck tool | Whatever the presenter already uses. No debate. | Team B | Sat 27 |
| **6.7** | D-16 team allocation | **Fill now.** The tables in §4.2/4.3 assume 2 + 2. | Both leads | Sat 27, 09:00 |

---

## Document control
| | |
|---|---|
| **Version** | v1.0 — 27 Sep 2026 |
| **Relation** | Binding refinement of `SIH26081_MASTER_PLAN.md` §7–§9, §13. On conflict, this document wins for tech choices; MASTER_PLAN wins for scope and DoD. |
| **Change rule** | A change here that alters a `results/` shape must change `types/results.ts` and the fixture in the same commit. |
