# Audit resolution: FOREBLENDCAST vs SIH26081

Response to `FOREBLENDCAST_vs_SIH26081_Audit.md`, checked against the code on 2026-09-29.
Item numbers are the audit's. All numbers below come from `results/` as written by
`python -m experiments.run` (held-out years 2020 and 2022, 366 forecast dates per lead).

## Was the audit true?

Mostly yes. The central findings were real and two of them were worse than described.
A few items described an older version of the code.

| Verdict | Items |
|---|---|
| **True** | 1, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14–18, 20, 21, 23–25, 27, 29, 31–33, 38, 39, 43–50, 52–60, 62–65, 67–69, 72–76, 82, 84, 85, 87, 89, 90 |
| **Partly true** | 26 and 28 (already changed from what the audit quotes, still wrong), 37, 51, 61, 66 |
| **Not true of the current code** | 2 (`write_bounds` was imported from `outputs.render_png`), 3 (no `MODELS` name in the runner), 34–36 (the WeatherBench2 paths work; the data is on disk), 83 (a FastAPI service exists in `api/`) |
| **Not defects** | 19, 22, 40–42, 77–79, 88 (observations the audit itself marks green) |

### Found while verifying, not in the audit

| Finding | Where |
|---|---|
| The equal-weight row of the ladder held the climatology numbers | `experiments/run.py` |
| MAE was `rmse * 0.8`; FSS of the oracle and REV of every model were written as `0.0` | `experiments/run.py` |
| The quality gate would have rejected almost every GraphCast rainfall field (negative rain) and 49 real HRES fields (more than 600 mm). It was never called, so nobody noticed | `canonical/quality_gate.py` |
| FSS scale labels were wrong: the 9-cell neighbourhood is 250 km, not 50 km | `verification/fss.py` |
| The REV formula left out the cost of protecting on hits and the perfect-forecast normalisation | `verification/economic_value.py` |
| The best single model was chosen per day using that day's truth | `experiments/run.py` |
| The NetCDF export crashed on a boolean attribute, so it had never run | `outputs/netcdf.py` |
| The Assam replay showed leads 5, 3, 1 of one cycle as if they were forecasts from 5, 3 and 1 days before the event, with invented peak values | `AssamReplay.tsx` |
| `/api/location/lookup` returned Cachar, Ratnagiri or the first district; `/api/ops/feeds` reported satellite and radar feeds that do not exist; `/api/weights/explain` returned constants | `api/` |
| `truth.png` showed the day after the one lead day 1 verifies | `experiments/generate_truth.py` |

## What was changed

### Scientific validity (audit P0)

| Audit items | Change |
|---|---|
| 4, 12, 13, 72 | `experiments/evaluate.py`: weights, regime thresholds, calibrators and quantile tables are fitted on years before the test year and frozen. The test-year truth is read only after the forecasts exist. `tests/test_no_truth_leakage.py` runs the evaluation twice with different test-year truth and requires every frozen object to be identical. |
| 7 | One implementation, `weighting.shrinkage.softmax_weights`: `w ∝ exp(-error / τ)`. Lower error gives higher weight. The runner no longer negates scores. |
| 5, 11, 73–76 | `weighting/skill.py`: squared-error sums per (model, variable, lead, season, regime, cell), built from training samples only. Regime comes from the forecasts (`regimes/detector.py`), never from the verifying observation. |
| 6, 9 | Four levels (national, region, district, cell) with shrinkage `λ = n_eff / (n_eff + k)`, then the existing spatial smoothing. |
| 8 | τ and k are chosen by cross-fitting inside the training years (odd months against even months). |
| 26, 27 | Disagreement is normalised by the training-period inter-model spread of each cell and season. |
| 28, 59, 69 | Moving-block bootstrap over forecast dates on per-date errors. Every where-we-lose entry carries its interval and a significance flag. |
| 14–16, 70, 71 | Equal weight, inverse error and best single are separate rows, all chosen or fitted on training data. |
| 68 | `results/ablation*.json`: equal weight, inverse error, context, shrinkage, probability matching, then calibration and quantiles. |
| 43 | The gate screens every field before it can enter a blend. Hard limits were widened to keep real extremes; negative rain is clipped and counted. |

### Functional completeness (audit P1)

| Audit items | Change |
|---|---|
| 1, 20, 21 | Rainfall, 2 m temperature and wind speed (`sqrt(u10² + v10²)`) run through the same pipeline. Pangu-Weather is registered for temperature and wind. |
| 24, 25, 80 | `hazards/events.py`: heatwave, hot day, fresh and strong wind, with calibrated probabilities per district. |
| 18, 31 | Isotonic calibration fitted on cross-fitted training forecasts and applied in the forecast path. Tier probability thresholds are tuned on training data. |
| 57, 63 | `calibration/quantiles.py`: q05 and q95 are empirical quantiles of past observations given the blend. CRPS is computed from them. |
| 62, 64, 65, 67 | RMSE, MAE, bias, FSS, frequency bias, Brier, BSS, AUC, reliability, REV and CRPS for every variable. |
| 29 | Leave-one-model-out is computed per cell on training days and aggregated per district. |
| 44, 45 | A model that is missing or rejected is dropped for the day and the rest renormalised. The reason is written to the products. |
| 48–51 | Every cycle writes PNG rasters for every layer and model, a NetCDF file and one GeoTIFF per lead. |
| 82 | `experiments/cycle.py` is the operational path and needs no observation. `scripts/run_cycle.ps1` runs and publishes one cycle and documents the scheduled task. |

### Dashboard and API (audit 52–60, 84, 87)

| Audit items | Change |
|---|---|
| 52, 53 | The layer, model and region selectors now drive the map and the district panels. |
| 54 | Model cards show each model's own held-out RMSE, MAE and FSS. |
| 55 | One naming scheme: `hres`, `ens`, `graphcast`, `pangu`. |
| 56, 58 | The hard-coded `+18.4% CRPS` is gone. Quoted numbers are read from `results/summary.json`. |
| 60, 61 | The truth source is stated as ERA5 everywhere. The claim of IMD gridded verification was removed. |

## Results

Change of the adaptive blend (weighted mean) against the references. Negative is better.

| Variable | Lead | RMSE vs equal weight | RMSE vs best single | CRPS vs equal weight | 90% interval coverage |
|---|---|---|---|---|---|
| Rainfall | 1 | −20.8% | −0.1% | −19.4% | 0.908 |
| Rainfall | 5 | −10.5% | −0.8% | −8.0% | 0.912 |
| Rainfall | 9 | −7.5% | −4.0% | −3.5% | 0.912 |
| Temperature | 1 | −29.5% | −0.5% | −10.8% | 0.930 |
| Temperature | 5 | −14.3% | −2.1% | −3.9% | 0.920 |
| Temperature | 9 | −7.0% | −6.2% | −0.7% | 0.916 |
| Wind speed | 1 | −7.7% | −5.8% | −7.4% | 0.909 |
| Wind speed | 5 | −1.9% | −9.7% | −1.8% | 0.905 |
| Wind speed | 9 | −1.1% | −12.5% | −1.2% | 0.899 |

Rainfall, lead day 1, 64.5 mm event: Brier score 0.00282 (equal weight), 0.00256 (adaptive
weights), 0.00219 (adaptive weights, calibrated).

### LightGBM

Held-out years, both methods scored on the same seven quantile levels. Negative is better.

| Variable | Lead | CRPS, LightGBM vs quantile table | 90% interval coverage, table | 90% interval coverage, LightGBM | RMSE, learned blend vs weighted blend |
|---|---|---|---|---|---|
| Rainfall | 1 | −2.0% | 0.908 | 0.910 | +7.6% |
| Rainfall | 5 | +0.2% | 0.912 | 0.902 | +8.4% |
| Rainfall | 9 | −0.1% | 0.912 | 0.889 | +7.8% |
| Temperature | 1 | −14.1% | 0.930 | 0.865 | +1.7% |
| Temperature | 5 | −9.3% | 0.920 | 0.859 | +1.3% |
| Temperature | 9 | −5.1% | 0.916 | 0.843 | +1.5% |
| Wind speed | 1 | −6.6% | 0.909 | 0.888 | −4.8% |
| Wind speed | 5 | −5.3% | 0.905 | 0.880 | −3.4% |
| Wind speed | 9 | −4.6% | 0.899 | 0.871 | −3.8% |

- The training cross-validation chose LightGBM quantiles for every variable and lead, so
  the intervals in the products are LightGBM's.
- LightGBM quantiles are sharper and score better for temperature and wind. For rainfall
  the two methods are level.
- **LightGBM intervals are too narrow for temperature**: the 90% interval covers 84 to 87%
  of observations. The quantile table is closer to 90%.
- **The learned blend is not better than the weights** for rainfall and temperature. It
  helps for wind. It is reported in the ladder as `lgbm_blend` and is not used in the
  products.

## What the results do not show

- **The gain over the best single model is small at short leads.** For rainfall at lead
  day 1 the blend and GraphCast are level (interval of the RMSE difference −0.009 to
  +0.013 mm). The clear gain is over the equal-weight mean, which is the baseline the
  problem statement names.
- **ERA5 is the truth, and it favours GraphCast and Pangu-Weather**, which were trained on
  ERA5. The blend gives GraphCast about 90% of the rainfall weight at lead day 1. With IMD
  gridded observations as truth the weights would probably differ. ERA5 also
  under-represents extreme rainfall: its peak for the June 2022 Assam–Meghalaya event is
  158 mm in a cell.
- **Probability matching raises RMSE** (4.20 against 4.00 mm at lead day 1) while improving
  FSS and frequency bias slightly. It is the product for extremes, not for RMSE.
- **The blend loses in some contexts.** Rainfall: 90 of 371 region × season × regime
  contexts, 12 of them beyond bootstrap noise. They are listed in
  `results/where_we_lose.json`.
- **Three years of data** (2018, 2020, 2022), one forecast every second day. Cell-level
  evidence is thin, which is why the fitted shrinkage leans on the region level.
- **Temperature is the 12 UTC value**, a proxy for the daily maximum. Heatwave skill is
  measured against the same proxy.

## Done after the first pass

| Audit items | Change |
|---|---|
| 32, 33 | `calibration/lgbm.py`: LightGBM is trained on the cross-fitted training forecasts, as a quantile model and as a learned blend. Both learn the correction to the blend. The quantile method used in the products (quantile table or LightGBM) is chosen per variable and lead by cross-validated pinball loss inside the training years. The unused helper in `hazards/rainfall.py` was removed. See "LightGBM" below. |
| 38, 39 | `ingestion/grib2.py`: GRIB2 is a second source for every registered model (`data/raw/grib2/<model>/`), used when the files exist and falling back to the archive per variable. A GRIB2-only model is ingested and gated but kept out of the blend until it has a skill history. `tests/test_grib2.py` writes real GRIB2 files with ecCodes and runs them through the adapter, the registry and a full forecast cycle. |
| — | Android: the bundled snapshot is refreshed by `scripts/sync_android_assets.py` and now covers lead days 1, 3, 5, 7, 9. The models, district detail screen and replay screen read the new fields. `assembleDebug` and the unit tests pass, including `BundledSnapshotTest`, which parses the bundled files. |

## Not done

| Audit items | Status |
|---|---|
| 61 | No IMD gridded observations. They need a data request; the pipeline reads truth from `data/raw/era5`. |
| 82 | No live feed. `scripts/run_cycle.ps1` produces output only when a day's model files are written to `data/raw`. |
| 38 | The GRIB2 path is proven on files written by the tests, which hold archive or constructed fields. It has not been run on a file downloaded from an operational centre. Rainfall is read as a total since the start of the forecast; files with 6-hourly buckets are not handled. |
| 46, 47 | Change points are computed and written to `results/changepoint.json`, but they do not reset or decay the skill database. The detected shifts follow monsoon onset and withdrawal, not model upgrades. |
| 81 | Population is reported per district. It does not yet weight the tiers. |
| 9 | Spatial smoothing has no Western Ghats mask because no elevation data is on disk. |
| — | The Android app was built and unit-tested. It was not run on a device or emulator; none is attached to this machine. |

## Reproduce

```
python -m experiments.run                      # evaluation + showcase, about 25 minutes
python -m experiments.run --showcase_only      # products only, from the frozen weights
python -m experiments.cycle --cycle 2022-08-10 # any other cycle
python -m pytest                               # Python tests
python scripts/sync_android_assets.py          # refresh the Android snapshot
make sync                                      # copy results/ to the dashboard
```
