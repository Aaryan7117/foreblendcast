# SIH26081 — WORK SPLIT

**Backend builds `results/`. Frontend builds everything that reads `results/`. They connect through the files in Part 3.**

Order inside each part = build order (each item depends on the ones above it). Everything marked **⭐** is required; everything marked *(optional)* is done only after all ⭐ items are done. Shapes of every file are in `TECH_APPROACH_AND_TEAMS.md` §3; algorithms in §2.

---

# PART 1 — BACKEND

**Goal: every file in Part 3 exists, is real (no synthetic values), and is regenerable by `make results`.**

### B1 ⭐ Environment
- `environment.yml` (conda-forge, Python 3.11) — from TECH_APPROACH §5.1.
- **Done when:** `python -c "import cfgrib, xarray"` works and one real GRIB2 file opens with `engine="cfgrib"`.

### B2 ⭐ Data
- Download WeatherBench2 subset for the India box (lat 6.5–38.5 N, lon 66.5–100 E) for GFS, ECMWF IFS HRES, GraphCast → `data/raw/<model>.zarr`.
- Download ERA5 for the same box (fallback truth + wind).
- Obtain IMD 0.25° gridded rainfall and 1° Tmax/Tmin (if unavailable → ERA5, and every output file says so in `meta.ground_truth`).
- Download one live GFS GRIB2 from NOMADS (the "runs on HPC" proof).
- SRTM elevation for the box.
- `ingestion/inventory.py`: prints, per model × year, which variables exist (especially precipitation) over the box.
- **Done when:** the inventory table is printed and pasted into `DECISIONS.md`, and the year range / model pools are decided from it (TECH_APPROACH §6.1, §6.2).

### B3 ⭐ Canonical layer (`canonical/`)
- `forecast.py` — pydantic `CanonicalForecast` (model, model_version, init_time, valid_time, lead_hours, variable, accumulation_hours, accumulation_window_start_utc, units, lat, lon, values).
- `grid.py` — canonical grid = the IMD 0.25° grid; lat ascending; lon 0–360; `to_canonical_grid(ds)` via bilinear `interp`.
- `accumulation.py` — rain → 24 h sum over **0300 UTC → 0300 UTC** (= IMD's 0830 IST day); Tmax/Tmin over the same window.
- `units.py` — rain mm, T °C, wind m/s (u, v separate).
- `quality_gate.py` — schema + coord + time + window + unit + NaN + range checks; reject the file, log the reason, continue.
- `terrain.py` — terrain class per cell from SRTM *(optional)*.
- **Done when:** `tests/test_accumulation.py` passes (one date hand-checked against IMD) and `tests/test_quality_gate.py` passes (corrupt file rejected, clean file accepted).

### B4 ⭐ Adapters (`ingestion/`)
- `base.py` — `Adapter.load(init_time, lead_hours, variable) -> CanonicalForecast`.
- `gfs.py`, `ecmwf.py`, `graphcast.py` — read Zarr, flip lat/lon conventions, call accumulation + units, return canonical.
- `grib2.py` — same interface reading the NOMADS GRIB2 via cfgrib (proves the path).
- `registry.py` — `register(adapter)`; adding NCUM later = one file + one line.
- **Done when:** all three adapters return identical-shaped canonical objects for rain and T2m at every lead 1–10, and `experiments/run.py --strategy equal --date <d>` writes a blended `.nc` you can plot.

### B5 ⭐ Ground truth (`verification/truth.py`)
- Load IMD (or ERA5) onto the canonical grid, same 0300 UTC window, land mask applied.
- **Done when:** `truth(date, variable)` returns an array aligned cell-for-cell with any adapter output.

### B6 ⭐ Verification (`verification/`)
- `deterministic.py` — RMSE, MAE, bias, per (model, variable, lead, cell); land-area-weighted aggregates.
- `fss.py` — FSS at neighbourhoods {1, 5, 9, 19, 29} cells for thresholds {15.6, 64.5, 115.6, 204.5} mm; returns `f0` and `fss_useful = 0.5 + f0/2` alongside.
- `frequency_bias.py`, `intensity_cdf.py`.
- `bootstrap.py` — 7-day block bootstrap, 1000 reps, 95 % CI on **differences** vs. best single.
- `probabilistic.py` — Brier, BSS, reliability bins, ROC-AUC, CRPS.
- `economic_value.py` — Relative Economic Value curve over C/L ∈ [0.01, 0.99].
- **Done when:** `tests/test_fss.py` passes against a hand-computed toy case, and every metric runs on B4's output vs. B5's truth.

### B7 ⭐ Folds & leakage (`experiments/folds.py`)
- Rolling-origin: train on years < Y, test on Y, for each held-out year.
- **Done when:** `tests/test_leakage.py` proves no test-year observation reaches any weight fit.

### B8 ⭐ Error database (`weighting/errors.py`)
- `errors.zarr` indexed `(model, variable, lead_day, valid_date, lat, lon)` with signed error and |error|; plus sample counts per (region × lead × season × regime).
- **Done when:** `results/sample_counts.json` is written and reviewed — it decides which context axes are estimable.

### B9 ⭐ Weighting strategies (`weighting/`)
- `base.py` — `WeightStrategy.compute_weights(context) -> dict[model, float]`.
- `climatology.py` (per-cell calendar-day mean of obs), `persistence.py`, `best_single.py`, `equal.py`.
- `inverse_error.py` — `w ∝ 1 / (trailing-30-day RMSE + ε)`.
- `context.py` — `score[m, v, region, lead, season(, regime)] → softmax(−score/τ)`.
- `shrinkage.py` — `λ = n_eff/(n_eff + k)`; cell → district → subdivision → homogeneous region → national; below `n_eff < 15` inherit parent and record the reason.
- `tau_fit.py` — grid-search τ per (variable, lead-band) on the validation fold → `results/tau.json`.
- `oracle.py` — per-cell hindsight best (ceiling only).
- `spatial.py` — Gaussian σ = 1 cell on the weight field, masked at the Ghats crest.
- `override.py` — reads `results/overrides.jsonl`, renormalises, keeps the audit fields.
- **Done when:** every strategy produces a weight field for every (variable, lead) and the ladder (B12) has one row per strategy.

### B10 ⭐ Blending (`blending/`)
- `deterministic.py` — weighted mean (T, u, v).
- `probability_matched.py` — weighted-mean field for location, weighted-member pool for intensity, rank-remap (TECH_APPROACH §2.5). Ships both `M` and `B`.
- `physical.py` — clip rain < 0, Tmax ≥ Tmin, speed from blended (u, v); every correction logged to `results/validator_log.jsonl`.
- **Done when:** the probability-matched rung is on the ladder with FSS, frequency bias and intensity CDF alongside RMSE.

### B11 ⭐ Hazards & calibration (`hazards/`, `calibration/`)
- `rainfall.py` — predictive distribution (LightGBM quantiles; fallback: empirical member ensemble) → `P(>64.5)`, `P(>115.6)`, `P(>204.5)`.
- `calibration/isotonic.py` — fit on training fold; one calibrator per availability pattern.
- `district.py` — area-weighted 90th percentile of cell probabilities per district (via `regionmask`) → tier Green/Yellow/Orange/Red; thresholds tuned on validation to maximise REV at C/L = 0.1; tuned values written out.
- `disagreement.py` — `D = spread / climatological_spread[cell, month]`.
- `lomo.py` — per district, RMSE increase when each model is removed.
- `heatwave.py`, `wind.py` *(optional)*.
- **Done when:** `districts_L*.json` (Part 3) is complete for every field, and `reliability.json` shows calibrated vs. uncalibrated.

### B12 ⭐ Result writers (`evaluation/`)
- `ladder.py` → `results/ladder.json` (floor → singles → blends → ceiling, CIs, `pct_of_achievable_gain`).
- `districts.py` → `results/districts_L{1,3,5,7,10}.json`.
- `points.py` → `results/points/{mumbai,chennai,kolkata,delhi,guwahati}.json`.
- `where_we_lose.py` → `results/where_we_lose.json` (cells where blend > best single, with CI and reason).
- `curves.py` → `results/rev.json`, `reliability.json`, `fss_curve.json`.
- `provenance.py` → the `meta` block stamped on every file (git commit, models, strategy, truth, window, aggregation, `status`).
- **Done when:** every Tier-1 file in Part 3 exists and validates against `frontend/src/types/results.ts`.

### B13 ⭐ Rasters (`outputs/render_png.py`)
- For each lead: `dominant_model`, `weight_<model>`, `p_gt_64p5`, `p_gt_115p6`, `p_gt_204p5`, `precip_pm`, `disagreement` → PNG with fixed colormaps, plus one `bounds.json`.
- **Done when:** PNGs overlay correctly on the Leaflet map (checked with the frontend at the first connect).

### B14 *(optional)* Regimes (`regimes/`)
- Forecast-derived active/break flag; `verify_detector.py` → `results/regime_agreement.json`; regime rung on the ladder.

### B15 *(optional)* Monitoring (`monitoring/change_point.py`)
- `ruptures` PELT on per-model error series → `results/changepoint.json`.

### B16 *(optional)* Case study (`evaluation/case_study.py`)
- Out-of-sample event in a test year → `results/case_study/{meta,timeline}.json` + rasters.

### B17 *(optional)* NetCDF (`outputs/netcdf.py`)
- One CF-1.8 file per cycle with the provenance block as global attrs.

### B18 ⭐ Makefile
```
make env · make data · make inventory · make test · make results · make rasters · make sync · make reproduce
```
- `make sync` = copy `results/` → `frontend/public/data/` (`robocopy … /MIR` on Windows).
- **Done when:** `make reproduce` runs from raw data to every Part-3 file with a log.

---

# PART 2 — FRONTEND

**Goal: every panel renders from `frontend/public/data/` and nothing else; a fixture never reaches the demo build.**

### F1 ⭐ Scaffold
- Vite + React 18 + TypeScript + Tailwind + zustand + react-leaflet + react-plotly.js (TECH_APPROACH §5.2).
- **Done when:** `npm run dev` serves a dark-themed empty shell.

### F2 ⭐ Contract mirror + fixtures + gate
- `src/types/results.ts` — TypeScript types for every file in Part 3 (from TECH_APPROACH §3).
- `src/hooks/useResults.ts` — `useResults<T>(path)` → fetches `/data/<path>`, typed.
- `fixtures/` — one file per contract with `"fixture": true` and obviously-fake values; copied into `public/data/` until the backend's first `make sync`.
- `Watermark.tsx` — full-screen diagonal "FIXTURE DATA — NOT RESULTS" whenever `meta.fixture === true`.
- `npm run build:demo` — fails if any file under `public/data/` has `fixture: true`.
- **Done when:** the app boots on fixtures with the watermark, and `build:demo` correctly refuses them.

### F3 ⭐ Static assets (`public/static/`)
- District GeoJSON (datameet), simplified (`mapshaper -simplify 10%`), each feature given the `id` scheme used in `districts_L*.json` (`<STATE>-<DISTRICT>`); the id list shared with the backend.
- City list for the spaghetti panel (same five slugs as Part 3).
- **Done when:** the GeoJSON renders as an India map and every `id` matches the backend's.

### F4 ⭐ App shell
- zustand store: `variable`, `lead`, `layer`, `selectedDistrict`, `aggregation`.
- Controls: variable selector, lead slider 1/3/5/7/10, layer switch.
- **EXPERIMENTAL — NOT AN OFFICIAL IMD WARNING** banner: persistent, non-dismissible.
- Provenance footer on every screen from `meta` (cycle, models, strategy, truth, git commit, `status`).
- **Done when:** changing any control re-renders every panel from the right file.

### F5 ⭐ `DistrictMap.tsx` — traffic-light board
- GeoJSON layer coloured by `tier` (IMD hex: green `#2E7D32`, yellow `#F9A825`, orange `#EF6C00`, red `#C62828`).
- Aggregation label + toggle (p90 / mean / max) shown on the map.
- Click → popup with every field of `districts_L*.json`: probabilities, population + source, weights, LOMO %, disagreement, shrinkage level + reason, and the `status` line.
- **Done when:** the board reads `districts_L{lead}.json` for the selected lead and the popup shows real values.

### F6 ⭐ `RasterLayer.tsx`
- Leaflet `ImageOverlay` from `rasters/<field>_L<lead>.png` with `bounds.json`; layer switch: dominant model / weight per model / `p_gt_64p5` / disagreement; legend per layer.
- **Done when:** rasters align with district borders.

### F7 ⭐ `LadderTable.tsx`
- Rows floor → singles → blends → ceiling; columns RMSE, MAE, FSS@50, frequency bias, REV@0.1, Δ vs. best single with CI; headline "% of achievable gain captured".
- **Done when:** it renders `ladder.json` verbatim — no number typed by hand.

### F8 ⭐ `Spaghetti.tsx`
- City selector → members as thin lines, blend bold, q05–q95 band, obs dots where present, disagreement mini-bar.
- **Done when:** reads `points/<city>.json`.

### F9 ⭐ `WhereWeLose.tsx`
- Map highlight + table of `where_we_lose.json`: district, lead, season, blend vs. best single with CI, reason, "override available".
- **Done when:** it renders and is reachable from the nav.

### F10 ⭐ `DecisionCard.tsx`
- Printable state-level card populated from `districts_L*.json` + `meta`; provenance footer; `status` line.
- **Done when:** print preview is legible on one page.

### F11 ⭐ Curves
- `RevCurve.tsx` (`rev.json`), `Reliability.tsx` (`reliability.json`, with sharpness histogram), `FssCurve.tsx` (`fss_curve.json`, with the `fss_useful` line).
- Built on fixtures; light up when the backend files land.

### F12 *(optional)* `CaseStudy.tsx`, `ChangePoint.tsx`, guided-tour banner.

### F13 ⭐ Deliverables
- `README.md` — setup, architecture diagram (MASTER_PLAN §7.1), ladder table pasted from `ladder.json`, limitations, data licences (MASTER_PLAN §15.2).
- Deck — 12 slides per MASTER_PLAN §13.4, screenshots from real data, every number traceable to a `results/` file.
- Demo recording — 3 min, 1920 × 1080.
- **Done when:** every number in the deck matches `results/`.

---

# PART 3 — CONNECT

### 3.1 The files (the whole interface)

| Tier | File | Backend writer | Frontend reader |
|---|---|---|---|
| ⭐ | `results/ladder.json` | B12 | F7 |
| ⭐ | `results/districts_L{1,3,5,7,10}.json` | B11 + B12 | F5, F10 |
| ⭐ | `results/points/{mumbai,chennai,kolkata,delhi,guwahati}.json` | B12 | F8 |
| ⭐ | `results/rasters/*.png` + `bounds.json` | B13 | F6 |
| ⭐ | `results/where_we_lose.json` | B12 | F9 |
| opt | `results/rev.json`, `reliability.json`, `fss_curve.json` | B12 | F11 |
| opt | `results/case_study/*`, `changepoint.json`, `regime_agreement.json` | B14–B16 | F12 |
| opt | `results/netcdf/*.nc` | B17 | shown on a slide only |

Every file carries the `meta` block. Full JSON shapes: `TECH_APPROACH_AND_TEAMS.md` §3.

### 3.2 The mechanism
```
backend:   make results  →  make sync   (results/  →  frontend/public/data/)
frontend:  useResults('districts_L3.json')  →  typed object  →  render
           meta.fixture === true  →  watermark
           npm run build:demo     →  refuses any fixture
```

### 3.3 The rules
1. **`types/results.ts` and the fixtures are written first**, from TECH_APPROACH §3, before any adapter or any map. Then the frontend can build everything on fixtures while the backend produces real files.
2. **A shape change is one conversation and two commits:** backend changes the writer, frontend changes `results.ts` + the fixture. Never a silent rename.
3. **Backend never edits anything under `frontend/`. Frontend never writes anything under `results/`.**
4. **If a file is malformed at connect time, fix the writer, not the reader.**
5. **No number is typed into the UI or the deck.** If it isn't in a `results/` file, it isn't shown.

### 3.4 The connect checklist (run it every time `make sync` happens)
- [ ] Watermark is gone on every panel (no fixture left).
- [ ] Ladder table shows floor and ceiling rows and the "% of achievable gain" headline.
- [ ] Changing the lead slider changes district colours, raster, and spaghetti together.
- [ ] Clicking a red/orange district shows probabilities, weights, LOMO %, population + source, shrinkage reason.
- [ ] Raster edges line up with district borders.
- [ ] Where-We-Lose has at least one row with a CI and a reason.
- [ ] Provenance footer shows the current git commit and `status` on every screen.
- [ ] `npm run build:demo` passes.
- [ ] The five numbers on slide 4 equal the five numbers in `ladder.json`.

When all nine boxes tick, the two halves are connected.
