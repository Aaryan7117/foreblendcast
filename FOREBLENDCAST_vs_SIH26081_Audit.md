# FOREBLENDCAST vs SIH26081 — Consolidated Implementation Audit

## Purpose

This document consolidates the implementation audit of **FOREBLENDCAST** against **SIH26081**, covering:

- Current implementation
- Errors and missing pieces
- Correct implementation
- Why each item matters
- Priority

---

## Consolidated Audit Table

| # | Area / File | What your project currently does | What is wrong / missing | Correct implementation | Why it matters for SIH26081 | Priority |
|---:|---|---|---|---|---|---|
| 1 | `experiments/run.py` | Runs mainly `precip` | Temperature and wind are not actually processed by the main experiment | Run separate pipelines for precipitation, temperature and wind | PS requires heterogeneous weather forecasting, not rainfall alone | 🔴 P0 |
| 2 | `experiments/run.py` | Imports `write_bounds` from `evaluation` | `write_bounds` is not defined there | Import it only from `outputs.render_png` | Pipeline can fail before execution | 🔴 P0 |
| 3 | `experiments/run.py` | Uses `for model in MODELS` | `MODELS` is undefined; `models` was created instead | Use a properly defined model registry/list | Causes runtime `NameError` | 🔴 P0 |
| 4 | `experiments/run.py` | Calculates current forecast error against truth and immediately uses it for weights | **Future/test truth leaks into weight generation** | Learn weights only from historical training data; apply them to unseen forecasts | This invalidates the adaptive forecast experiment | 🔴 P0 |
| 5 | `weighting/context.py` / `shrinkage.py` | Context-aware weighting framework exists | Actual experiment does not properly feed historical contextual skill into it | `W(model | region, season, lead, regime, variable)` from historical data | Contextual weighting is the central PS requirement | 🔴 P0 |
| 6 | `weighting/shrinkage.py` | Hierarchical shrinkage exists | Runner effectively uses `node_id="national"` | Implement grid → district → region → national hierarchy | Low-sample regions need statistical stabilization | 🔴 P1 |
| 7 | `weighting/context.py` | Uses error-derived scores | `scores[model] = -err` while weighting uses `exp(-score/tau)` | Use positive error with `exp(-error/tau)` or correctly reverse sign | Current formulation can give **larger weight to worse models** | 🔴 P0 |
| 8 | `weighting/tau_fit.py` | `fit_tau()` exists | Actual runner effectively uses default `tau=1.0` | Fit τ using training/validation data | Controls how aggressively weights adapt | 🟠 P1 |
| 9 | `weighting/spatial.py` | Spatial smoothing implementation exists | Not properly connected to actual blending | Generate spatially varying weight fields and apply them to forecasts | PS expects region-dependent blending | 🟠 P1 |
| 10 | `regimes/verify_detector.py` | Weather regime detector exists | Regime is not actually driving weights in the main pipeline | `weight = f(model, region, season, lead, regime)` | Weather situation is explicitly important to adaptive blending | 🔴 P1 |
| 11 | Historical skill | Error modules exist | Current runner uses essentially a single-cycle calculation | Maintain rolling historical skill database | Adaptive weighting requires historical model performance | 🔴 P0 |
| 12 | `experiments/folds.py` | Leakage-safe folds exist | Main runner doesn't correctly use them for model weighting | Train → validation → unseen test chronology | Prevents overestimated skill | 🔴 P0 |
| 13 | Test evaluation | Forecast truth is available before weighting | Test information contaminates forecast generation | Test truth is accessed **only after forecast is frozen** | Required for credible benchmarking | 🔴 P0 |
| 14 | Baseline | Equal-weight architecture exists | Not sufficiently demonstrated as a formal baseline | Always compare against equal-weight mean | PS explicitly identifies equal-weight multi-model mean as baseline | 🔴 P1 |
| 15 | Best-single baseline | `BestSingle` exists | Needs proper out-of-sample selection | Select best model using historical training only | Shows whether blending actually adds value | 🟠 P1 |
| 16 | Inverse-error baseline | Exists | Must be evaluated leakage-free | Historical inverse-error weights only | Provides a conventional benchmark | 🟠 P1 |
| 17 | Probability matching | `probability_matched.py` exists | Not fully demonstrated through ablation | Compare arithmetic mean vs weighted mean vs probability-matched blend | Helps preserve rainfall extremes | 🟢 P1 |
| 18 | Calibration | `calibration/isotonic.py` exists | Not actually integrated into final forecast path | Train calibration on validation data and apply to unseen forecasts | Probability outputs need reliability | 🔴 P1 |
| 19 | Rainfall | Main implemented variable | Strongest part of current system | Keep and expand | Important SIH disaster-management variable | 🟢 |
| 20 | Temperature | Ingestion support exists | Main experiment doesn't actually evaluate it | Add `t2m`, `tmax`, `tmin` pipeline | PS requires broader weather outputs | 🔴 P1 |
| 21 | Wind | `u10`, `v10` ingestion exists | Not converted/evaluated as actual operational wind forecast | Calculate `wind_speed = sqrt(u10²+v10²)` and evaluate it | Needed for high-wind hazards | 🔴 P1 |
| 22 | Heavy rainfall | Threshold logic exists | Currently strongest hazard implementation | Keep and calibrate probabilities | Direct disaster-management application | 🟢 |
| 23 | Extreme rainfall | Thresholds such as 115.6/204.5 mm exist | Needs proper forecast probability verification | Evaluate event probability using Brier/reliability/ROC | A warning probability must be trustworthy | 🟠 P1 |
| 24 | Heatwave | UI/backend fields exist | Backend effectively returns placeholder `False` | Implement temperature-based heatwave detection/forecast | Current feature is not genuinely implemented | 🔴 P1 |
| 25 | High wind | UI/data fields exist | Wind is placeholder/zero in parts of pipeline | Implement threshold/event probability from wind forecasts | PS/disaster-management requirement | 🔴 P1 |
| 26 | `hazards/disagreement.py` | Model disagreement implemented | Uses `clim_spread = 10.0` placeholder | Use real climatological standard deviation by grid/season/variable | Current uncertainty map is not physically/statistically meaningful | 🔴 P0 |
| 27 | Model uncertainty | Disagreement is calculated | No proper historical normalization | `disagreement / climatological variability` | Makes uncertainty comparable between regions | 🟠 P1 |
| 28 | Confidence interval | Bootstrap module exists | Current experiment can treat spatial cells as temporal samples | Bootstrap actual forecast dates using temporal blocks | Current CI can be statistically invalid | 🔴 P0 |
| 29 | `hazards/lomo.py` | Leave-one-model-out analysis exists | District outputs can use whole-grid results | Calculate LOMO independently for each region/district | Needed to explain model contribution locally | 🔴 P1 |
| 30 | District risk | District hazard framework exists | Some outputs are prototype-level | Generate real district-level forecast/risk from gridded outputs | Makes system useful for disaster response | 🟠 P1 |
| 31 | District probability | Weighted threshold exceedance exists | Not necessarily calibrated | Calibrate probability against historical events | Probability ≠ calibrated probability automatically | 🟠 P1 |
| 32 | `hazards/rainfall.py` | Empirical exceedance probability | LightGBM quantile capability exists but isn't used | Either integrate quantile ML properly or remove unsupported claim | Avoids unused "AI" modules | 🟠 P2 |
| 33 | LightGBM | Quantile function exists | Not part of core forecast path | Train on historical forecast/observation features | Could become a real ML blending/calibration layer | 🟢 P2 |
| 34 | HRES | ECMWF ingestion exists | Dataset path/version assumptions need verification | Validate against current WB2 dataset structure | Incorrect paths cause missing model data | 🔴 P0 |
| 35 | ENS | ENS adapter exists | Current path appears inconsistent with documented WB2 hierarchy | Use verified WB2 ENS dataset path | Prevents ingestion failure | 🔴 P0 |
| 36 | GraphCast | GraphCast adapter exists | Year/data availability assumptions need verification | Build a model/year availability matrix | Cannot train/evaluate on nonexistent data | 🔴 P0 |
| 37 | Pangu | Adapter exists | Doesn't provide the precipitation variable used by current rainfall experiment | Use Pangu for supported variables or remove it from rainfall claims | Avoids falsely claiming four-model rainfall blending | 🟠 P1 |
| 38 | GRIB2 | Adapter exists | Not registered in normal model pipeline | Register and test GRIB2 ingestion end-to-end | Important bridge to real NWP operational data | 🟠 P1 |
| 39 | Model registry | Registry exists | Not all adapters are necessarily used | One central registry must drive ingestion → blending → evaluation | Prevents disconnected modules | 🟠 P1 |
| 40 | Canonical grid | `canonical/grid.py` exists | Good architecture but needs full model verification | Regrid all models to identical grid/resolution | Multi-model blending requires spatial alignment | 🟢 |
| 41 | Units | `canonical/units.py` exists | Needs validation for every model/variable | Standardize mm, K/°C, m/s, accumulation periods | Prevents physically meaningless blending | 🟢 |
| 42 | Accumulation | `canonical/accumulation.py` exists | Needs validation across different model lead conventions | Convert all forecasts to identical accumulation windows | Rainfall accumulation mismatch can invalidate results | 🔴 P1 |
| 43 | Quality gate | QC module exists | Must be executed before every model enters blend | Reject/flag invalid grids before weighting | Bad model data can contaminate the blend | 🟢 |
| 44 | Missing data | Some loaders handle missing files | No robust operational fallback strategy | If one model fails, renormalize weights and record reason | Real operational systems cannot assume every model arrives | 🟠 P1 |
| 45 | Model failure | Model registry exists | No strong live fallback workflow | Detect failed model → remove it → renormalize weights | Required for operational reliability | 🟠 P1 |
| 46 | Model drift | Change-point module exists | Not connected to skill/weight update | Detect model version/performance drift and decay stale skill | Strong potential operational novelty | 🟢 P2 |
| 47 | Model version | Canonical forecast has version metadata | Not driving skill reset/update | Separate skill by model/version | Prevents old model performance contaminating new model weights | 🟠 P2 |
| 48 | NetCDF | Output module exists | Not fully integrated into experiment | Produce final blended NetCDF automatically | Standard scientific data product | 🟠 P1 |
| 49 | GeoTIFF | Not properly implemented | Dashboard/GIS cannot rely on georeferenced forecast raster | Generate GeoTIFF with CRS/transform/nodata | Useful for disaster-management GIS | 🟠 P2 |
| 50 | PNG | Rendering exists | Raster assets aren't consistently generated/present | Generate maps automatically from each cycle | Required for dashboard visualization | 🟠 P1 |
| 51 | RasterLayer | Requests `precip_pm_L*.png` | Corresponding raster assets are not reliably present | Connect generated raster files to frontend | Current map can produce 404s | 🔴 P0 |
| 52 | Frontend layer selector | Has rainfall/disagreement/risk options | Layer selection isn't fully connected to raster source | `activeLayer → correct backend raster` | UI currently implies functionality that may not work | 🔴 P1 |
| 53 | Region selector | UI contains regions | Selection isn't properly connected to data filtering | Region state → backend/query/filter | Otherwise it's decorative | 🟠 P2 |
| 54 | Model comparison | Cards exist | Can display same aggregate values rather than true model-specific results | Compute model-specific metrics/data | Judges need real comparison | 🔴 P1 |
| 55 | Model naming | Frontend uses `gfs/ecmwf/graphcast` in fixtures | Backend uses `hres/ens/graphcast` | One canonical model naming scheme | Prevents broken data contracts | 🔴 P1 |
| 56 | Fixtures | Frontend has generated fixture data | Contains explicit mock values such as constant arrays | Demo must consume actual experiment outputs | Mock data cannot be presented as forecast evidence | 🔴 P0 |
| 57 | Confidence bands | Fixture q05/q95 are simple `×0.5` and `×1.5` | Not statistical quantiles | Generate real ensemble/calibrated quantiles | Current uncertainty visualization can be misleading | 🔴 P0 |
| 58 | Performance claim | Frontend contains `+18.4% CRPS` | Hard-coded claim isn't dynamically derived | Calculate from reproducible evaluation output | Judges can ask for evidence | 🔴 P0 |
| 59 | `WhereWeLose` CI | Uses artificial ±0.5 type interval | Not a genuine confidence interval | Use actual bootstrap distribution | Otherwise statistical explanation is unreliable | 🔴 P0 |
| 60 | ERA5 truth | Pipeline uses ERA5 | UI/documentation can imply IMD observation | Clearly state ERA5 reanalysis unless IMD data is actually used | Truth-source credibility matters | 🔴 P0 |
| 61 | IMD data | PS context emphasizes Indian operational forecasting | Current pipeline does not actually establish IMD gridded observations | Add IMD observations if claiming IMD verification | Makes Indian deployment story stronger | 🟠 P1 |
| 62 | Evaluation metrics | RMSE/MAE/FSS etc. exist | Need complete consistent evaluation across variables/models | RMSE + MAE + FSS + bias + CRPS/Brier/reliability | Proves whether blend actually improves forecasts | 🔴 P1 |
| 63 | CRPS | Mentioned in UI/research | Not sufficiently connected to actual result generation | Calculate CRPS from actual probabilistic forecasts | Required for probabilistic comparison | 🔴 P1 |
| 64 | Brier score | Probability system exists | Needs systematic event verification | Brier + reliability diagrams for rain/heat/wind events | Proves probability quality | 🟠 P1 |
| 65 | Reliability diagram | Framework exists | Needs real historical forecasts | Plot predicted probability vs observed frequency | Essential for calibrated warning probabilities | 🟠 P1 |
| 66 | FSS | Implementation exists | Current dashboard/evaluation doesn't fully expose multi-scale FSS | Report FSS across multiple spatial scales | Rainfall spatial skill is important | 🟢 |
| 67 | Frequency bias | Module exists | Needs inclusion in final comparison | Report frequency bias per threshold/model | Shows over/under-warning behavior | 🟠 P1 |
| 68 | Ablation | Multiple algorithms exist | No strong final ablation proving contribution of each feature | Equal → inverse error → context → shrinkage → PM → calibration | This proves each novelty actually helps | 🔴 P0 |
| 69 | Statistical significance | Bootstrap exists | Current implementation needs correction | Temporal block bootstrap on independent test period | Prevents overclaiming small improvements | 🔴 P0 |
| 70 | Equal-weight baseline | Exists conceptually | Must be the official baseline | `mean(HRES, ENS, GraphCast...)` | Direct PS comparison | 🔴 P1 |
| 71 | "Best model" baseline | Exists | Must select without test leakage | Historical validation only | Fair benchmark | 🟠 P1 |
| 72 | Adaptive weights | Exists conceptually | Current implementation isn't genuinely adaptive in the valid experimental sense | Learn from historical context and freeze weights before test | Main PS requirement | 🔴 P0 |
| 73 | Regional weighting | Architecture exists | Current runner defaults to national | Compute regional/grid-specific weights | PS explicitly expects geographic context | 🔴 P0 |
| 74 | Seasonal weighting | Season module exists | Not actually central to current weights | Train separate/conditional seasonal skill | Models behave differently by season | 🔴 P1 |
| 75 | Lead-time weighting | Lead is present | Needs historical skill by lead | `W(model, lead)` learned from past forecasts | Different models have different lead-time strengths | 🔴 P1 |
| 76 | Weather-regime weighting | Detector exists | Not integrated | Condition weights on active regime | Directly addresses weather-situation dependence | 🔴 P1 |
| 77 | Spatial weight map | Rendering concept exists | Must come from actual adaptive weights | Produce grid-level `w_HRES`, `w_ENS`, `w_GraphCast` | Strong visual evidence of novelty | 🟢 |
| 78 | Weight explainability | Partial | Need "why this model received this weight" | Show historical RMSE, regime, season, lead contribution | Makes AI decision auditable | 🟢 |
| 79 | Disagreement explainability | Exists | Needs real climatological normalization | Show model spread and historical expected spread | Helps forecasters identify uncertainty | 🟢 |
| 80 | Disaster-management output | District risk exists | Mostly rainfall-focused | Convert forecast → hazard → exposure → district priority | Aligns with MoES disaster-management theme | 🔴 P1 |
| 81 | Population exposure | District module exists | Needs reliable population data/versioning | Link hazard probability with exposed population | Makes output decision-oriented | 🟠 P2 |
| 82 | Operational scheduler | Python script exists | No real automatic cycle | Cron/Airflow/Prefect/systemd/K8s schedule | PS asks for automated system | 🟠 P1 |
| 83 | API | Frontend reads static JSON | No proper live forecast service | FastAPI endpoints for latest cycle/maps/metrics | Enables operational deployment | 🟠 P2 |
| 84 | Dashboard | Visually strong | Some controls/data are prototype-level | Connect every UI element to real backend outputs | Demo must reflect actual science | 🔴 P1 |
| 85 | Testing | Many unit tests exist | Tests don't prove complete end-to-end scientific correctness | Add integration + leakage + dataset + output-contract tests | Prevents demo failures | 🟠 P1 |
| 86 | Reproducibility | Makefile/config exists | Dataset paths and assumptions are fragile | Version datasets/config/model artifacts | SIH judges should be able to reproduce results | 🟠 P1 |
| 87 | Research claims | Architecture is sophisticated | Some modules are presented as implemented when they are only framework/code | Clearly distinguish implemented vs prototype | Protects technical credibility | 🔴 P0 |
| 88 | AI novelty | GraphCast + ML weighting | Merely combining AI forecasts isn't enough | Adaptive context-conditioned blending + calibration + uncertainty | This is where the real novelty should be | 🟢 |
| 89 | Scientific novelty | Probability matching + shrinkage | Not all are connected to final system | Integrate and perform ablation | Otherwise novelty remains theoretical | 🔴 P1 |
| 90 | Final SIH product | Prototype forecasting dashboard | Not yet a fully valid operational multi-model forecasting system | End-to-end: ingest → QC → historical skill → adaptive weights → blend → calibrate → hazards → dashboard | This is the actual target state of SIH26081 | 🔴 P0 |

---

## Bottom Line

The repository is **not a zero-level project**. The architecture contains several strong ideas, but the **implemented execution path has not caught up with the architecture**.

### Highest-priority fixes

#### 1. Remove truth leakage

Rebuild the train/validation/test weighting pipeline:

```text
Historical forecasts + historical truth
            ↓
    Training / validation
            ↓
 Historical contextual skill
            ↓
 Adaptive weight function
            ↓
 Freeze weights / model
            ↓
     Unseen test forecasts
            ↓
      Final evaluation
```

The test truth must be accessed **only after the forecast has been frozen**.

#### 2. Fix adaptive weighting mathematically and architecturally

The core weight should follow the intended direction:

```text
lower historical error
        ↓
higher skill
        ↓
higher weight
```

A valid formulation is conceptually:

```python
weight ∝ exp(-error / tau)
```

with contextual conditioning such as:

```text
W(model | region, season, lead, regime, variable)
```

rather than deriving weights directly from the current test forecast error.

#### 3. Replace prototype frontend data

Remove fixture-driven or hard-coded scientific outputs, especially:

- constant forecast arrays
- artificial q05/q95 bands
- hard-coded CRPS improvements
- artificial confidence intervals
- placeholder heatwave/high-wind results
- missing raster assets

The dashboard should consume the **actual experiment outputs**.

---

## Recommended Implementation Order

```text
P0 SCIENTIFIC VALIDITY
│
├── Fix runner/runtime errors
├── Remove truth leakage
├── Correct weighting sign/math
├── Build historical skill database
├── Implement leakage-safe folds
├── Freeze weights before test
├── Fix climatological uncertainty
├── Fix bootstrap methodology
├── Replace mock frontend metrics
└── Generate real raster outputs

        ↓

P1 SIH FUNCTIONAL COMPLETENESS
│
├── Regional weighting
├── Seasonal weighting
├── Lead-time weighting
├── Weather-regime weighting
├── Temperature pipeline
├── Wind-speed pipeline
├── Heatwave detection
├── High-wind hazard
├── Proper calibration
├── CRPS / Brier / FSS / bias
├── Ablation study
└── District-level hazard outputs

        ↓

P2 OPERATIONALIZATION / POLISH
│
├── GeoTIFF
├── API
├── Scheduler
├── Population exposure
├── Model drift
├── Version-aware skill
└── Advanced explainability
```

---

## Core Scientific Story to Demonstrate

The strongest technical story is not simply:

> "We combine several weather models."

It should be demonstrated as:

```text
Multiple heterogeneous forecasts
              ↓
       Canonical grid + QC
              ↓
 Historical contextual skill
              ↓
 Region + season + lead + regime
              ↓
 Hierarchical adaptive weighting
              ↓
       Probabilistic blend
              ↓
 Calibration + probability matching
              ↓
 Spatial disagreement / uncertainty
              ↓
 Hazard detection
              ↓
 District-level actionable risk
```

The key experimental proof should be an ablation such as:

```text
Equal-weight
      ↓
Inverse-error
      ↓
Context-aware
      ↓
+ hierarchical shrinkage
      ↓
+ probability matching
      ↓
+ calibration
```

That allows you to demonstrate which components actually improve the system rather than merely showing that the repository contains sophisticated modules.

---

## Final Assessment

The primary issue is **integration and scientific validity**, not lack of ideas.

The target end-state is:

```text
Ingest
  ↓
Normalize / QC
  ↓
Historical skill
  ↓
Context-conditioned adaptive weights
  ↓
Multi-model blend
  ↓
Calibration
  ↓
Uncertainty
  ↓
Hazards
  ↓
District risk
  ↓
API / Dashboard
```

That is the architecture the implementation should converge toward for the **SIH26081** submission.
