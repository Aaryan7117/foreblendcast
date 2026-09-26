# SIH26081 — Hybrid AI–NWP Multi-Model Forecast Blending System
## Complete Solution Blueprint & Strategy Document

**Organisation:** Ministry of Earth Sciences (MoES) · NCMRWF  
**Theme:** Disaster Management  
**Category:** Software  
**Deadline:** 30 September 2026  
**Document Date:** 26 September 2026  

---

## Table of Contents

1. [Problem Statement (Official)](#1-problem-statement-official)
2. [Expected Outcomes](#2-expected-outcomes)
3. [Competitive Intelligence](#3-competitive-intelligence)
4. [Research Gaps in Existing Solutions](#4-research-gaps-in-existing-solutions)
5. [Our Innovation — What We Build That Doesn't Exist](#5-our-innovation--what-we-build-that-doesnt-exist)
6. [Solution Architecture](#6-solution-architecture)
   - 6.1 [End-to-End Data Flow](#61-end-to-end-data-flow)
   - 6.2 [Canonical Forecast Layer & Model Registry](#62-canonical-forecast-layer--model-registry)
   - 6.3 [Weighting Engine: Baseline Ladder → Adaptive Strategies](#63-weighting-engine-baseline-ladder--adaptive-strategies)
   - 6.4 [Training / Inference Separation & Leakage Prevention](#64-training--inference-separation--leakage-prevention)
   - 6.5 [Blending, Physical Validation & Spatial Coherence](#65-blending-physical-validation--spatial-coherence)
   - 6.6 [Extreme Hazard Probability & Calibration](#66-extreme-hazard-probability--calibration)
   - 6.7 [Spatial Verification — FSS](#67-spatial-verification--fss)
   - 6.8 [Experiment Framework & Configuration](#68-experiment-framework--configuration)
   - 6.9 [Repository / Module Structure](#69-repository--module-structure)
7. [Tech Stack](#7-tech-stack)
8. [Google AI Models Integration Strategy](#8-google-ai-models-integration-strategy)
9. [Killer Features (User-Facing)](#9-killer-features-user-facing)
10. [Gap-to-Outcome Scorecard](#10-gap-to-outcome-scorecard)
11. [Innovation Defense (Judge Q&A Prep)](#11-innovation-defense-judge-qa-prep)
12. [Implementation Priority & Timeline](#12-implementation-priority--timeline)
13. [30-Second Judge Pitch](#13-30-second-judge-pitch)

---

## 1. Problem Statement (Official)

> **Different forecasting systems perform differently depending on region, season, lead time and weather situation.** Physical NWP models, ensemble forecasts and AI/ML weather models may each have strengths under different conditions. Therefore, there is a need for an intelligent blending system that can dynamically combine multiple forecasts.

> The challenge is to develop a **hybrid AI–NWP blending framework** that assigns **adaptive weights** to different forecast sources based on **historical skill, forecast lead time, region, season and weather regime**. The final product should provide an optimized forecast for **rainfall, temperature, wind and extreme weather indicators**.

### Key Insight from the Problem Statement
The PS explicitly asks for **integration intelligence**, not invention of new weather models. NCMRWF already operates NCUM-G, NCUM-R, and NEPS. They need the **decision brain** that determines which model to trust, when, where, and why.

---

## 2. Expected Outcomes

| # | Official Expected Outcome | What Judges Will Look For |
|---|---|---|
| 1 | **Dynamically blended forecast** — Best-combined forecast from multiple model sources | Continuous gridded blend (not point stations), all-India, Day 1–10, multiple variables |
| 2 | **Model weight maps** — Indication of which model is more reliable for each region/lead time | Spatial 2D maps showing weight distribution per model, variable, lead time, and regime |
| 3 | **Improved forecast skill** — Better performance than individual models | Quantifiable RMSE/FSS improvement verified against IMD ground truth with confidence intervals |
| 4 | **Extreme weather guidance** — Improved signals for heavy rainfall, heat wave and high-wind events | Calibrated exceedance probabilities at IMD thresholds (64.5/115.6/204.5 mm rain, 40°C heatwave, gale-force wind) |
| 5 | **Operational workflow** — Automated script/dashboard for routine forecast blending | Scheduled batch pipeline (00Z/12Z cycles), CF-NetCDF/GeoTIFF output, not just a web dashboard |

---

## 3. Competitive Intelligence

### 3.1 Landscape Summary

| Repo / Team | Real Data? | Variables | Spatial Coverage | Lead Times | Fatal Flaw |
|---|---|---|---|---|---|
| **AtmosFusion** | ✅ IMD gridded rain | Rain, Tmax | 29 districts (Konkan-Goa + Kerala) | Day 1–5 | Regime features add zero skill (own ablation); narrow coverage |
| **MausamMix** | ✅ ERA5 | Temperature only | All-India 1.5° grid | Day 3–10 | No rain / wind / extremes; Colab notebook only |
| **Weather_Blend** | ✅ ERA5 | Temp, Rain, Wind | 3 point stations | 24/72/168h | 3 stations, zero winter training, some cells worse than single model |
| **AAGAM** | ✅ Open-Meteo live | Temp, Rain, Wind | 40 hardcoded station pins | Day 0–7 | 5 macro-regions; 4/4 consensus extreme rule; no NCMRWF models |
| **AtmosBlend-AI** | ❌ 100% Fake (`np.random`) | Temp, Rain, Wind | 8 states (dropdown) | 6h–72h | Entirely synthetic data; anime mascot UI inappropriate for disaster theme |
| **Omnicast** | ❌ Synthetic | All (nominal) | Nominal | — | Dependencies are only `flask`+`requests`; metrics are fabricated |
| **SAMVAY** | ❌ Synthetic | All (nominal) | Nominal | — | Full pipeline on simulated sources |
| **HYBRIDCAST, WEATHERFUSION-AWX, MOSAIC, ForecastFusion, Synthesis** | ❌ Illustrative | Varies | Varies | — | Dashboard-first prototypes; no verification |

### 3.2 Cross-Cutting Observations

- Open-Meteo's free API is the forecast source for nearly every entry — a commodity, not a differentiator.
- The three rigorous entries each cover a *slice*: AtmosFusion (rain, two regions), MausamMix (temperature, all-India), Weather_Blend (three variables, three points). **None covers all expected outcomes on real data.**
- The feature-rich entries cover every outcome nominally but on synthetic/mock data.
- **No single competitor includes NCMRWF's own models (NCUM, NEPS)** — the problem owner's primary systems.

### 3.3 Detailed Competitor Tear-Down

#### AAGAM (`aagam-mlb8.vercel.app`)
**Strengths to borrow:**
- Clean dark-mode command-center dashboard aesthetic
- Interactive Leaflet station map with model telemetry
- Alert modal system

**Critical weaknesses we exploit:**
- Only 40 hardcoded station points (not continuous gridded)
- 5 oversimplified macro-regions (entire "SOUTH" shares one weight set)
- Extreme alert requires 4/4 model consensus — **catastrophic false negatives** (if 3 of 4 models predict 120mm but 1 says 45mm, alert is suppressed)
- Stops at Day 7 (NCMRWF's medium-range mandate is Day 3–10)
- Zero NCMRWF models (uses GFS, ECMWF, ICON, AIFS)
- Ground truth banner: "ERA5 Climatology Fallback (IMD Offline)"
- LLM chatbot is a gimmick for disaster management judges

#### AtmosBlend-AI (`atmosblend-ai1`)
**Strengths to borrow:**
- Onboarding tutorial concept (non-tech judges need guided walkthrough)
- 30-second pitch structure in README

**Critical weaknesses we exploit:**
- **100% synthetic data** — every value generated by `np.random.uniform()` seeded by string hash
- No API calls, no GRIB2, no NetCDF — not even Open-Meteo
- Only 8 Indian states (20 states + UTs missing including Delhi, UP, Bihar, Gujarat, NE India)
- Stops at 72 hours (Day 3)
- Anime mascot / pastel kawaii theme — **severe tone mismatch** for Disaster Management theme under MoES

---

## 4. Research Gaps in Existing Solutions

### Gap 1 — NCMRWF's Own Models Are Absent from Every Pool
No repository ingests NCUM-G, NCUM-R, or NEPS. No entry reads a GRIB2 file at all.
> **Our Opportunity:** Generic GRIB2/NetCDF ingestion adapter (`cfgrib`/`xarray`), demonstrated on NOMADS GFS GRIB2, with NCUM/NEPS as declared drop-in sources.

### Gap 2 — No Entry Verifies Rainfall, Temperature AND Wind Across India Over Multiple Years
AtmosFusion: IMD truth but rain/Tmax only, 29 districts, one year. MausamMix: all-India but temperature only. Weather_Blend: three variables but three stations.
> **Our Opportunity:** WeatherBench2 archives × IMD 0.25° gridded observations → five monsoon seasons, nationwide, Indian ground truth.

### Gap 3 — Weather-Regime Conditioning Has Not Been Shown to Add Skill
AtmosFusion's ablations found regime/season features add zero measurable skill. Other entries assert regime awareness without testing it.
> **Our Opportunity:** Derive regimes from dynamical indices (IMD Active/Break index, 500 hPa trough detection, MSLP vorticity for cyclones) rather than calendar-based labels.

### Gap 4 — Extremes Are Handled by Thresholding a Blended Mean
Mean-seeking blends smooth peaks. Every entry thresholds the blended value.
> **Our Opportunity:** Quantile gradient boosting / EMOS / BMA → calibrated exceedance probabilities at IMD thresholds with reliability diagrams.

### Gap 5 — Wind Extremes Are Entirely Unverified
No repository reports any wind-extreme skill on real data.

### Gap 6 — Precipitation Verification Ignores Spatial/Neighbourhood Scores
All entries use point-wise RMSE/MAE/ETS. No FSS or SAL scores.
> **Our Opportunity:** FSS at multiple neighbourhood scales; report the scale at which the blend becomes skilful.

### Gap 7 — Model-Version Drift Is Not Handled
No entry detects model upgrades or resets skill memory.
> **Our Opportunity:** Version tagging, change-point detection on error series, automatic skill-memory reset.

### Gap 8 — Seasonal Generalisation Is Untested
Weather_Blend trains with zero winter hours; AtmosFusion validates on 2024 only.

### Gap 9 — Lead-Time Coverage Stops at Day 5 for Real-Data Entries
Only MausamMix (temperature) reaches Day 10, which is NCMRWF's medium-range remit.

### Gap 10 — Operational Outputs Are Not in Operational Formats
No entry writes CF-compliant NetCDF or GeoTIFF. Scheduled cycles are simulated.
> **Our Opportunity:** Docker + cron/Prefect → NetCDF (CF-1.8), GeoTIFF, CAP 1.2, REST API.

### Gap 11 — Weight Maps Are Not a First-Class Explained Product
None provides per-variable × per-lead × per-season gridded weight maps with plain-language "why" per cell, or a forecaster override.

### Gap 12 — Statistical Honesty Is Rare
Only Weather_Blend and AtmosFusion report confidence intervals. Most report point estimates or synthetic numbers.

### Additional Blind Spots (From Meteorological Deep-Dive)

#### Physical Consistency & Thermodynamic Bounds
- Blending T and Td independently can produce Td > T (unphysical supersaturation)
- Blending scalar wind speed vs. (u, v) vector components produces vector inconsistencies
- **Solution:** Blend (u, v) wind vectors, compute speed from blended vectors; clamp Td ≤ T; clip rain ≥ 0

#### Dynamic Missing Data & Latency Fallback
- In live 00Z/12Z operations, models arrive asynchronously (NCUM at T+3.5h, GFS at T+4h, ECMWF at T+6.5h)
- **Solution:** Graceful degradation engine — if a model is missing at cutoff, re-normalize weights and tag metadata

#### Topographic & Coastal Masking
- Standard gridded interpolation across steep elevation gradients (Western Ghats, Himalayas) introduces lapse-rate and rain-shadow errors
- **Solution:** Elevation and land-sea masks in weight calculation

---

## 5. Our Innovation — What We Build That Doesn't Exist

### The Core Insight
> *"Google didn't invent websites. Google invented PageRank — the intelligence that decides which website to trust. We didn't invent weather models. We invented the intelligence that decides which weather model to trust for your district, your season, your lead time, and your weather regime."*

### Innovation 1: 6-Dimensional Context-Aware Trust Scoring — Built Progressively, Not as a Lookup Table
No off-the-shelf tool answers: "Should I trust GFS or NCUM for rainfall in Kerala during an active monsoon trough on Day 7 of the monsoon season?"

The PS explicitly names **season** as a conditioning factor alongside region, lead time and regime, so the trust function is:

```
W = f(model, variable, region, lead_time, season, regime)
```

We deliberately do **not** build this as one giant 6-dimensional lookup table from day one — with a few years of data that overfits immediately and produces noisy, unexplainable weights. Instead we build it as a scored ladder that adds one axis of conditioning at a time, so every added dimension has to earn its place through an ablation rather than being assumed to help:

```
historical error
      ↓
model × variable × region × lead
      ↓
+ season conditioning
      ↓
+ regime conditioning
      ↓
score[m, v, r, lead, season, regime]
      ↓
weight = softmax(−score / τ)
```

Trained on years of Indian verification data against IMD ground truth, with each added dimension checked against the simpler version below it (see §6.3, Baseline Ladder). **This scoring function and the ablation ladder that produces it are our core IP** — not just the final weight values.

### Innovation 2: Dynamical Regime Detection from Model Fields
Nobody provides an "Indian weather regime detector." We build:
- **Active vs. Break monsoon** → derived from Central India rainfall index (IMD definition)
- **Western Disturbance** → detected from 500 hPa geopotential height troughs
- **Cyclone proximity** → from MSLP gradients and 850 hPa relative vorticity
- **Heat wave** → IMD criteria (Tmax ≥ 40°C plains / ≥ 30°C hills, departure ≥ 4.5°C)

This is original meteorological feature engineering — but Gap 3 exists precisely because AtmosFusion's own ablation found regime/season features added *zero* measurable skill. We report our regime-conditioning ablation honestly, positive or null, rather than assuming it earns its complexity budget (see §6.3).

### Innovation 3: Probabilistic Extreme Hazard Calibration to IMD Standards
No existing model outputs:
> *"78% probability that rainfall in Ratnagiri exceeds 115.6 mm (IMD Very Heavy threshold) in the next 24 hours."*

We convert deterministic multi-model spread into calibrated exceedance probabilities mapped to IMD's exact color-coded warning system (Green/Yellow/Orange/Red).

### Innovation 4: Forecaster-in-the-Loop Override with Explainability
No existing tool lets an NCMRWF duty forecaster:
- See **WHY** each model got its weight ("ECMWF scored 12% lower RMSE than GFS for monsoon rain over Western Ghats in the last 3 years")
- **Override** weights manually during critical events ("I know NCUM tracks Bay of Bengal cyclones better — set NCUM weight to 0.6")
- Have the override logged and auditable

### Innovation 5: Spatial Verification Framework for India (FSS)
No competitor uses Fractions Skill Score. Our system reports:
> *"At 50 km neighbourhood scale, the blend becomes skilful (FSS > 0.5) for heavy rainfall, while GFS alone requires 150 km to reach the same skill."*

This is an original scientific contribution to Indian weather verification.

---

## 6. Solution Architecture

> **Framing.** The biggest technical risk in the original draft wasn't missing features — it was too many components with no separation between the *core scientific experiment* and *optional enhancements*. Everything below is organized so that a minimal path — **3 real models → aligned data → historical errors → adaptive weights → blended forecast → verification** — works completely on its own. TimesFM, regime detection, the frontend, and NCUM/NEPS ingestion are extensions layered on top of that core, not dependencies of it. Build order follows this dependency chain: **data model → adapters → alignment → verification → baseline blends → adaptive weighting → extremes → TimesFM/regimes → API/frontend** (see §12).

### 6.1 End-to-End Data Flow

```
             FORECAST SOURCES
   ┌─────────┬─────────┬─────────┬─────────┐
   │  NCUM   │   GFS   │  ECMWF  │GraphCast│  ... via Model Registry (§6.2)
   └────┬────┴────┬────┴────┬────┴────┬────┘
        │         │         │         │
        └─────────┴────┬────┴─────────┘
                        ▼
                MODEL ADAPTERS  (one per source; GRIB2 / Zarr / JSON in)
                        ▼
               CANONICAL FORECAST  (common schema, §6.2)
                        ▼
              QUALITY CONTROL GATE  (schema/coord/time/unit/NaN/range checks)
                        ▼
             GRID / TIME ALIGNMENT  (common grid, common valid-time)
                        │
        ┌───────────────┴────────────────┐
        │                                 │
  Historical Obs (IMD/ERA5)          New Forecast (live)
        │                                 │
        ▼                                 │
   VERIFICATION  (RMSE/MAE/FSS/Brier)      │
        │                                 │
        ▼                                 │
   ERROR DATABASE  (per model×var×region×lead×season×regime)
        │                                 │
        ▼                                 │
   WEIGHT ENGINE  ◄─────────────────────┘   (Baseline Ladder + Strategy interface, §6.3)
        │
   ┌────┴─────┐
   │          │
baseline   adaptive
   │          │
   └────┬─────┘
        ▼
     BLENDER
        ▼
  PHYSICAL VALIDATION + SPATIAL SMOOTHING  (§6.5)
        │
   ┌────┴─────────┐
   │               │
deterministic   probability
   │               │
   │          CALIBRATION  (§6.6)
   │               │
   └───────┬───────┘
           ▼
     HAZARD ENGINE  (rain / heatwave / wind, shared pipeline, §6.5)
           ▼
   ┌───────┼─────────┐
   ▼       ▼          ▼
forecast weights   hazards
   │       │          │
   └───────┴──────────┘
           ▼
┌───────────────────────────────────┐   ┌───────────────────────────────────┐
│     DISASTER MANAGEMENT OUTPUT    │   │       OPERATIONAL DELIVERABLES    │
│ • District Traffic Light Map      │   │ • CF-1.8 NetCDF Grids             │
│   (Green/Yellow/Orange/Red)       │   │ • GeoTIFF Rasters                 │
│ • IMD-calibrated exceedance       │   │ • 2D Model Weight Maps            │
│   probabilities                   │   │ • CAP 1.2 XML Alert Feeds         │
│ • Impact-based forecast cards     │   │ • REST API                        │
│ • CAP 1.2 XML alert feeds         │   │ • Automated 00Z/12Z CLI Pipeline  │
│ • Population impact estimates     │   │ • Forecaster Override Interface   │
└───────────────────────────────────┘   └───────────────────────────────────┘
```

NCUM-G, NCUM-R, NEPS, GFS, ECMWF IFS/AIFS and GraphCast all enter through the same **Model Adapter → Canonical Forecast** step — nothing downstream of that step knows or cares whether a model arrived as GRIB2, Zarr, or JSON. This directly answers "can this run on NCMRWF's HPC?" (native GRIB2 in) without a second code path for live vs. archival data.

### 6.2 Canonical Forecast Layer & Model Registry

Different sources disagree on resolution, longitude convention, latitude ordering, timestamps, forecast horizons, variable names, and units. Rather than let those differences leak into the blending engine, every adapter converts into one schema:

```python
CanonicalForecast(
    model="gfs",
    init_time=...,
    valid_time=...,
    lead_hours=...,
    variable="tp",
    lat=..., lon=...,
    values=...,
)
```

Adapters are registered, not hardcoded:

```python
ModelSpec(name="gfs", source="nomads", adapter=GFSAdapter,
          resolution=..., variables=[...], lead_times=[...])

registry.register(GFSAdapter(...))
registry.register(GraphCastAdapter(...))
registry.register(NCUMAdapter(...))   # drop-in once NCMRWF GRIB2 is available
```

This is what makes "declare NCUM/NEPS as drop-in sources" (Gap 1) a registry entry rather than a rewrite.

**Quality gate, before anything is blended:**

```
File → schema validation → coordinate validation → time validation
     → unit validation → missing-value check → range check → accept/reject
```

One bad GRIB2 file should reject that file, not poison the blend.

**Canonical variable representation** — rainfall specifically cannot be blended across sources unless accumulation windows match:

```python
CanonicalRainfall(accumulation_hours=24, units="mm")
```

Unit and accumulation normalization happens *before* weighting, not as a side effect of it.

**Missing models are a first-class state, not an error path.** If GraphCast hasn't arrived by cutoff, the engine renormalizes weights over what's available and records what happened rather than propagating `NaN` through the blend:

```python
available = [m for m in models if m.is_available()]
weights = weights.loc[available]
weights /= weights.sum()
```
```json
{"available_models": ["gfs", "ecmwf"], "missing_models": ["graphcast"], "renormalized": true}
```

### 6.3 Weighting Engine: Baseline Ladder → Adaptive Strategies

A single global weight set (`w_gfs=0.3, w_ecmwf=0.4, w_graphcast=0.3`) defeats the point of the PS — skill varies by context. So does jumping straight to the full 6-dimensional `W(model, variable, region, lead, season, regime)` (Innovation 1) without proof that each added axis helps. We build **both** a complexity ladder and a strategy ladder, and measure each rung against the one below it:

```python
class WeightStrategy:
    def compute_weights(self, context) -> dict[str, float]: ...

EqualWeightStrategy      # w_i = 1/N — the null hypothesis
InverseErrorStrategy     # w_i ∝ 1 / historical_error_i
ContextAwareStrategy     # score[m, v, r, lead, season, regime] → softmax
TimesFMStrategy          # ContextAware + TimesFM error-drift prediction
```

TimesFM sits **behind this interface, not in the critical path**:

```
                    ┌── historical skill weighting ──┐
forecast models ────┤                                 ├──→ weights
                    └── optional TimesFM prediction ──┘
```

Every experiment reports all four rungs side by side, so "did the adaptive system actually help?" has a measured answer instead of an assumed one:

| Strategy | Illustrative RMSE* | What it tests |
|---|---|---|
| GFS / ECMWF / GraphCast alone | 1.83 / 1.72 / 1.65 | Best single model — the floor to beat |
| `EqualWeightStrategy` | 1.54 | Does *any* blending help? |
| `InverseErrorStrategy` | 1.48 | Does historical skill weighting beat equal weighting? |
| `ContextAwareStrategy` (region×lead×season×regime) | 1.31 | Does context conditioning beat flat inverse-error? |
| `TimesFMStrategy` | *TBD — ablated, not assumed* | Does predicted error drift beat static historical skill? |

*\*Structure to fill in with measured numbers once verification runs on real data — see Gap 12 (statistical honesty). No number here is reported to judges until it's measured.*

### 6.4 Training / Inference Separation & Leakage Prevention

Training (how weights are learned) and inference (how a live forecast is blended) are explicit, separate code paths — not one script that recomputes everything from scratch on every incoming cycle:

```
OFFLINE TRAINING                          OPERATIONAL INFERENCE
Historical forecasts + Observations       New forecasts
        ↓                                        ↓
   Alignment                                Validation
        ↓                                        ↓
   Error calculation                        Grid alignment
        ↓                                        ↓
   Feature generation                        Load trained weight model
        ↓                                        ↓
   Weight model                               Predict weights
        ↓                                        ↓
   Saved model/artifact ────────────────────→   Blend → Hazard probabilities → Output
```

**Leakage is enforced in the pipeline, not left to whoever runs an experiment.** A 2022 forecast is never weighted using 2022 observations. We use rolling-origin validation:

```
Train 2018 → 2020   Test 2021
Train 2018 → 2021   Test 2022
Train 2018 → 2022   Test 2023
```

The weighting engine only ever sees observations available before the forecast it's evaluating — this is the same leakage guarantee MausamMix and Weather_Blend publish explicitly (Gap 12), and we hold ourselves to it structurally rather than by convention.

### 6.5 Blending, Physical Validation & Spatial Coherence

**Shared pipeline, not four independent systems.** Rain, temperature and wind share ingestion, alignment, verification, weighting and blending; only the variable-specific transforms (rainfall accumulation, wind vector handling, temperature extremes) branch:

```
                 ┌── Rain
Common Forecast ─┼── Temperature
Pipeline         └── Wind
                       ↓
                Hazard Engine
```

**Physical consistency is a dedicated, logging validator — not a silent patch:**

```python
class PhysicalValidator:
    def validate_temperature(...): ...
    def validate_precipitation(...): ...
    def validate_wind(...): ...       # blend (u, v), derive speed — not a blended scalar
    def validate_humidity(...): ...  # clamp Td ≤ T
```
```json
{"field": "precipitation", "cells_corrected": 31, "operation": "clip_negative", "max_correction": 0.12}
```

**Spatially coherent weights.** Grid cells choosing weights independently produce "salt-and-pepper" weight maps (e.g. `GFS: .21 .84 .17 .92` across adjacent cells). We apply a spatial smoothing/regularization pass on the raw weight field — starting with simple Gaussian/local smoothing — while deliberately *not* blurring across genuine regional boundaries (e.g. the Western Ghats rain-shadow line).

### 6.6 Extreme Hazard Probability & Calibration

Thresholding a blended mean (what most competitors do — even Omnicast's "EV-Boost" is an ad-hoc max-mixing term, not a distribution) smooths out exactly the peaks that matter for disaster warnings. The extreme-event path is a real predictive distribution, not a deterministic value with a cutoff:

```
Forecast ensemble / model spread
          ↓
   Post-processing (quantile GBM / EMOS / BMA)
          ↓
   Predictive distribution
          ↓
   P(X > threshold)     e.g. P(rain > 64.5), P(rain > 115.6), P(rain > 204.4)
          ↓
   Calibration  (ProbabilityCalibrator — isotonic to start; Platt/Beta/EMOS as alternatives)
          ↓
   Hazard category  (IMD Green/Yellow/Orange/Red)
```

We implement **one** robust calibration method first and compare calibrated vs. uncalibrated probabilities, rather than shipping all four calibrators half-tested. Every probability is evaluated with Brier Score, reliability diagrams and ROC-AUC — not just reported as a single confidence number.

### 6.7 Spatial Verification — FSS

Point-wise RMSE/MAE/ETS double-penalizes small displacement errors, which is why no competitor's rainfall verification holds up at NCMRWF's operational standard (Gap 6). FSS is implemented as a real module, evaluated at multiple neighbourhood scales rather than reported as one number:

```python
fss(forecast, observation, threshold, neighborhood_km)
```

Scales: **5 / 25 / 50 / 100 / 150 km**, for each IMD rainfall threshold — producing a skill-vs-scale curve ("at 50 km the blend is skilful; GFS alone needs 150 km") instead of a single FSS score.

### 6.8 Experiment Framework & Configuration

Parameters live in config files, not buried in Python, so multiple people (or agents) can run comparable experiments:

```yaml
experiment:
  variable: precipitation
  lead_hours: [24, 48, 72]
models: [gfs, ecmwf, graphcast]
weighting:
  strategy: context
  history_days: 30
  season: true
  region: true
  regime: true
verification:
  metrics: [rmse, mae, fss, brier]
```

```bash
python experiments/run.py --strategy equal
python experiments/run.py --strategy inverse_error
python experiments/run.py --strategy context
python experiments/run.py --strategy context_timesfm
```

Each run writes to `results/<strategy>/` with RMSE, MAE, FSS, Brier, CRPS and reliability outputs — so the Baseline Ladder table in §6.3 is generated by the pipeline, not assembled by hand.

### 6.9 Repository / Module Structure

```
dmat-weather/
├── ingestion/       base.py, gfs.py, ecmwf.py, graphcast.py, ncum.py
├── canonical/       forecast.py, variables.py, units.py, grid.py
├── verification/    deterministic.py, fss.py, probabilistic.py, bootstrap.py
├── weighting/       base.py, equal.py, inverse_error.py, context.py, timesfm.py
├── blending/        deterministic.py, probabilistic.py, physical.py
├── regimes/         base.py, detector.py
├── hazards/         rainfall.py, heatwave.py, wind.py
├── calibration/      base.py, isotonic.py
├── experiments/     configs/, runner.py
├── evaluation/      reports.py, plots.py
├── api/
└── frontend/
```

Each top-level module maps to one box in §6.1's data flow. Adding NCUM/NEPS is a new file in `ingestion/` plus a registry entry (§6.2) — it does not touch `weighting/`, `blending/`, or anything downstream.

---

## 7. Tech Stack

### 7.1 Backend / Core Engine (Python)

| Component | Library / Tool | Purpose |
|---|---|---|
| **Data Ingestion** | `xarray`, `cfgrib`, `zarr`, `netCDF4` | Read GRIB2/NetCDF/Zarr from NWP models and WeatherBench2, behind per-model adapters (§6.2) |
| **Canonical Schema** | `pydantic` (or `dataclasses` + `xarray` accessors) | Enforce the `CanonicalForecast` / `CanonicalRainfall` schema and quality-gate validation (§6.2) |
| **Geospatial Processing** | `rioxarray`, `geopandas`, `shapely` | District boundaries, land-sea masks, elevation grids, GeoTIFF export |
| **Weighting Engine** | `scikit-learn`, `lightgbm` or `xgboost` | `WeightStrategy` implementations: equal, inverse-error, context-aware, and quantile regression for probabilistic extremes |
| **Error Forecasting (optional strategy)** | `google/timesfm` (HuggingFace) | `TimesFMStrategy` — zero-shot error-drift prediction, plugged behind the same `WeightStrategy` interface, ablated against the simpler strategies rather than assumed |
| **Calibration** | `scikit-learn` (isotonic), custom EMOS/Beta | `ProbabilityCalibrator` module — one method implemented first, compared uncalibrated-vs-calibrated |
| **Verification** | `xskillscore`, `properscoring`, custom FSS | RMSE, MAE, FSS (Fractions Skill Score) at multiple neighbourhood scales, CRPS, Brier Skill Score, reliability diagrams |
| **Statistical Inference** | `scipy`, `numpy` | Block bootstrap confidence intervals, change-point detection for model-version drift |
| **Experiment Config** | `pyyaml` (or `hydra`) | YAML-driven experiment configs + CLI runner (§6.8), so ablations are reproducible, not ad hoc |
| **Operational Pipeline** | `prefect` or `cron` + Docker | Automated 00Z/12Z forecast blending cycles; offline training and online inference as separate entry points (§6.4) |
| **API Layer** | `FastAPI` | REST API for downstream consumers (dashboards, CAP feeds, NDMA systems) |
| **Alert Formats** | `lxml`, `rasterio` | CAP 1.2 XML generation, CF-1.8 NetCDF and GeoTIFF writing |

### 7.2 Frontend / Dashboard (Web)

| Component | Library / Tool | Purpose |
|---|---|---|
| **Framework** | Vite + Vanilla JS (or React) | Fast, modern SPA |
| **Mapping** | Leaflet + Leaflet.heat / Mapbox GL | Interactive India maps with district boundaries, raster overlays, animated layers |
| **Charts** | Chart.js or Plotly.js | Spaghetti plots, confidence bands, leaderboard, reliability diagrams |
| **Styling** | Vanilla CSS (dark professional theme) | Clean, IMD/NCMRWF-appropriate disaster management aesthetic |
| **Animations** | CSS transitions + requestAnimationFrame | Weather movie timeline, smooth map transitions |

### 7.3 Data Sources

| Source | What It Provides | Access Method |
|---|---|---|
| **Google WeatherBench2** | Archived forecasts: IFS HRES, GFS, GraphCast, NeuralGCM (2018–2022) | Zarr on Google Cloud (`xarray.open_zarr()`) |
| **Open-Meteo API** | Live forecasts: GFS, ECMWF, ICON, AIFS, DWD | REST JSON (for live operational mode) |
| **NOMADS (NOAA)** | Live GFS GRIB2 files | HTTP/FTP download |
| **IMD Pune** | 0.25° gridded rainfall, 1° Tmax/Tmin (historical) | Data request / Pai et al. dataset |
| **ERA5 (CDS)** | Reanalysis ground truth (supplementary) | CDS API (`cdsapi`) |
| **NCMRWF (declared)** | NCUM-G, NCUM-R, NEPS (GRIB2) | Declared as drop-in via same GRIB2 adapter |

---

## 8. Google AI Models Integration Strategy

### 8.1 Models and Their Roles

| Google Model | Role in Our System | Open/Proprietary | How We Use It |
|---|---|---|---|
| **GraphCast** (DeepMind, Science 2023) | **AI Weather Model** in blending pool | ✅ Open (GitHub + Google Cloud) | Ingest 0.25° 10-day forecasts via WeatherBench2 Zarr as a competing model alongside GFS/NCUM |
| **NeuralGCM** (Google Research, Nature 2024) | **Hybrid Physics-AI Model** in pool | ✅ Open (GitHub) | Optional second AI model for diversity in the ensemble |
| **TimesFM** (Google Research, 200M/330M params) | **Optional Meta-Forecaster for Error Prediction** | ✅ Open (HuggingFace) | Plugged in behind the `WeightStrategy` interface (§6.3) as `TimesFMStrategy`; predicts future model error drift for anticipatory weight adjustment — *if* it beats the simpler strategies |
| **MetNet-3** (DeepMind) | Referenced in literature only | ❌ Proprietary | Cannot directly use; cite as related work |
| **WeatherBench 2** (Google Cloud platform) | **Primary Data Pipeline** | ✅ Open | Stream archived forecasts + observations for training and verification |

### 8.2 TimesFM as One Weighting Strategy — Not the Critical Path

Most teams compute weights using a simple lagging moving average of past errors. Weather changes abruptly — when an active monsoon spell breaks, yesterday's errors don't predict tomorrow's. TimesFM is our hypothesis for doing better than a lagging average. It is a hypothesis we test, not a dependency the system needs to function.

**Why it's decoupled, not hardcoded:** the original design put TimesFM directly in the critical path (`historical errors → TimesFM → weights`), which means the whole weighting engine breaks if TimesFM underperforms, is slow, or the HuggingFace model can't be pulled on demo day. Instead:

```
                    ┌── historical skill weighting ──┐
forecast models ────┤                                 ├──→ weights
                    └── optional TimesFM prediction ──┘
```

**Mechanism, when the strategy is enabled:**
1. Model forecast errors form a 1D time-series at every grid zone: `e_NCUM(t), e_GFS(t), e_GraphCast(t)`
2. Feed the trailing 30-day error series into **TimesFM zero-shot forecasting**
3. TimesFM predicts expected error of each model for Days 1–10
4. Compute dynamic softmax weights: `W_i(t+k) = exp(-ê_i(t+k)/τ) / Σ_j exp(-ê_j(t+k)/τ)`

**What we report:** the Baseline Ladder (§6.3) run with and without the TimesFM strategy enabled, side by side. If it doesn't beat `ContextAwareStrategy`, that's a reportable finding, not a failure to hide — see Gap 12 on statistical honesty, and the Q&A entry in §11 on this exact question.

---

## 9. Killer Features (User-Facing)

### Feature 1: 🎬 "Weather Movie" — Animated Forecast Evolution Map
An animated map of India where rainfall/temperature/wind sweeps across the country hour-by-hour, Day 1 → Day 10. Think TV weather channel storm tracking.

**Implementation:** Leaflet/Mapbox map with play/pause timeline slider. Each frame renders a color-filled raster layer.

**Why it wins:** Every judge — tech or not — instantly understands a moving storm. Forecasters at IMD use animated radar loops daily.

---

### Feature 2: 🚦 District Traffic Light Warning Board
Full India map where every district glows **Green / Yellow / Orange / Red** matching IMD's actual 4-tier color-coded warning system.

**Enhancement:** Click any red district → popup:
> *"🔴 Ratnagiri: 82% chance of >115 mm in next 24h. Affected population: 1.6M. 3 of 4 models agree. Recommended: Pre-position flood rescue teams."*

**Why it wins:** This is exactly what a District Magistrate / NDMA official needs at 6 AM. Transforms raw numbers into **impact-based actionable guidance** (WMO IBF direction).

---

### Feature 3: 🎯 "Who Do You Trust?" — Interactive Model Confidence Map
Heat map of India showing which model is most reliable in each region. Hover over Western Ghats → "ECMWF IFS dominates here during monsoon (weight: 0.42)."

**Enhancement:** Lead-time slider (Day 1 → Day 10). Watch how trust shifts as lead time increases.

**Why it wins:** This IS the "Model weight maps" deliverable from the PS. AAGAM shows 5 giant boxes. We show a smooth, continuous, per-district map.

---

### Feature 4: 📊 Model "Spaghetti" Confidence Panel
For any selected location, all models plotted as individual lines with the blended forecast as a bold highlighted line + shaded confidence band.

**Enhancement:** Confidence gauge ring — 🟢 High Agreement / 🟡 Moderate / 🔴 Low.

**Why it wins:** When models converge, judge sees "high confidence." When they diverge, "uncertainty." No explanation needed.

---

### Feature 5: 🕰️ Historical Replay — "What If We Had This During Kerala Floods?"
Case study replay mode:
- "Here's what happened during Kerala Floods (Aug 2018)"
- "Here's what each model predicted 3 days before"
- "Here's what our blend would have predicted"
- "Our system would have issued a Red Alert 72 hours early"

**Why it wins:** The single most emotionally compelling demo. Transforms abstract RMSE into **lives saved**.

---

### Feature 6: 📋 Forecaster Decision Card
Clean, printable daily summary card:

```
┌─────────────────────────────────────────────────┐
│  📋 DAILY FORECAST BRIEF — MAHARASHTRA          │
│  Issued: 26 Sep 2026 06:00 IST  |  Valid: D+1   │
├─────────────────────────────────────────────────┤
│  🌧️ Rain:  Heavy (64–115 mm) over Konkan-Goa    │
│  🌡️ Temp:  Tmax 34°C (normal)                    │
│  💨 Wind:  Moderate (25–35 km/h) coastal gusts   │
│  ⚠️ Alert: 🟠 ORANGE — Konkan (3 districts)      │
│  🤝 Model Agreement: HIGH (4/4 models concur)    │
│  📊 Confidence: ████████░░ 82%                    │
│  👤 Best Model Today: ECMWF IFS (weight: 0.41)   │
└─────────────────────────────────────────────────┘
```

**Why it wins:** This is what a real operational center produces every morning. NCMRWF judges will recognize the format instantly.

---

### Feature 7: 🏅 Live Model Skill Leaderboard
Real-time scoreboard showing which model is performing best this week/month:

```
   🏆 MODEL PERFORMANCE LEADERBOARD — September 2026
   ┌────┬──────────────┬────────┬──────────┬───────┐
   │ #  │ Model        │ Rain   │ Temp     │ Wind  │
   ├────┼──────────────┼────────┼──────────┼───────┤
   │ 🥇 │ ECMWF IFS    │ ★★★★☆ │ ★★★★★    │ ★★★★☆│
   │ 🥈 │ GraphCast    │ ★★★★☆ │ ★★★★☆    │ ★★★☆☆│
   │ 🥉 │ GFS          │ ★★★☆☆ │ ★★★★☆    │ ★★★★☆│
   │ 4  │ AIFS         │ ★★★☆☆ │ ★★★☆☆    │ ★★★☆☆│
   │ 🏆 │ OUR BLEND    │ ★★★★★ │ ★★★★★    │ ★★★★★│
   └────┴──────────────┴────────┴──────────┴───────┘
```

**Why it wins:** Gamification. Instantly visual. Proves the blend beats every individual model.

---

### Feature Priority Matrix

| Priority | Feature | Effort | Visual Impact | Judge Appeal |
|---|---|---|---|---|
| **P0** | 🚦 District Traffic Light Map | Medium | 🔥🔥🔥🔥🔥 | Both tech & non-tech |
| **P0** | 🎯 Interactive Model Weight Map | Medium | 🔥🔥🔥🔥🔥 | Directly answers PS |
| **P1** | 📊 Spaghetti + Confidence Gauge | Low-Medium | 🔥🔥🔥🔥 | Non-tech judges love it |
| **P1** | 📋 Forecaster Decision Card | Low | 🔥🔥🔥🔥 | NCMRWF judges |
| **P2** | 🎬 Animated Weather Movie | High | 🔥🔥🔥🔥🔥 | Ultimate wow factor |
| **P2** | 🏅 Live Skill Leaderboard | Low | 🔥🔥🔥 | Gamification appeal |
| **P3** | 🕰️ Historical Replay | Medium-High | 🔥🔥🔥🔥🔥 | Emotional impact |

---

## 10. Gap-to-Outcome Scorecard

| Expected Outcome | Best Existing Coverage | Remaining Gap | Our Solution |
|---|---|---|---|
| **Dynamically blended forecast** | AtmosFusion (rain), MausamMix (temp) | All variables, all-India, Day 1–10, NCMRWF models | Full gridded blend via canonical schema + model registry (§6.2); GRIB2 adapter for NCUM/NEPS as a drop-in registry entry |
| **Model weight maps** | MausamMix (temp, 1.5°) | Gridded, per var/lead/season, explained, overridable | Interactive 2D maps with lead-time slider + forecaster override; spatially smoothed to avoid salt-and-pepper artifacts (§6.5) |
| **Improved forecast skill** | AtmosFusion, MausamMix, Weather_Blend | Multi-season test, FSS, CIs everywhere | Baseline Ladder (equal → inverse-error → context → TimesFM, §6.3) + FSS across neighbourhood scales + bootstrap CIs, leakage-free (§6.4) |
| **Extreme weather guidance** | AtmosFusion (Brier ≥64.5mm), Weather_Blend (95th pct) | Calibrated probabilities, heatwave/wind criteria, reliability | Quantile/EMOS predictive distribution → `ProbabilityCalibrator` → IMD thresholds (§6.6) + district traffic light + impact cards |
| **Operational workflow** | AtmosFusion (daily cycle, CAP) | GRIB in, NetCDF/GeoTIFF out, scheduler, version-drift | Docker + Prefect pipeline → CF-NetCDF, GeoTIFF, CAP 1.2, REST API |

---

## 11. Innovation Defense (Judge Q&A Prep)

### Q: "Where's your innovation? You just connected existing models and tools."

**A:** *"The innovation is not in the weather models — just as Google's innovation was not in building websites. The innovation is in the DECISION INTELLIGENCE layer.*

*We built three things that don't exist anywhere:*
1. *A 6-dimensional trust engine — model, variable, region, lead time, season, weather regime — built as a scored ladder, so every added dimension is proven against a simpler baseline instead of assumed. Trained against years of IMD ground truth.*
2. *A probabilistic hazard translator that converts raw model disagreement into calibrated flood/heatwave/gale probabilities mapped to IMD's exact warning thresholds.*
3. *An explainable forecaster override — because in disaster management, the final call must always be a human's.*

*No existing model, API, or library provides any of these three. That is our contribution."*

---

### Q: "Why should we trust your blend over individual models?"

**A:** *"We don't ask you to trust us. We show you the proof: FSS verification across 5 monsoon seasons, block-bootstrap confidence intervals, and reliability diagrams — computed with rolling-origin validation so no forecast is ever verified against data it was trained on. If our blend doesn't beat every individual model, we show you where it doesn't and why — and the forecaster can override those cells."*

---

### Q: "What's actually working if the deadline hits and half the roadmap isn't built?"

**A:** *"The system is built so a minimal path stands on its own: three real models, aligned to a common schema, weighted by historical skill, blended, and verified against IMD ground truth. Regime detection, TimesFM, and the frontend are layered on top of that core — they're extensions, not dependencies. If we run out of time, what's left still answers the problem statement; it's just less refined."*

---

### Q: "Can this actually run at NCMRWF?"

**A:** *"Yes. Our ingestion layer reads native GRIB2 files via xarray+cfgrib — the same format NCUM and NEPS output on NCMRWF's HPC. We output CF-1.8 NetCDF, which slots directly into existing NCMRWF visualization and dissemination workflows. Every competitor reads JSON from web APIs — they cannot run on your HPC."*

---

### Q: "What if a model is delayed or missing?"

**A:** *"Our pipeline has a graceful degradation engine. If NCUM hasn't arrived by the cutoff time, the blend re-normalizes weights among available models, tags the output metadata as 'NCUM-absent', and notifies the duty forecaster. No crash, no missing cycle."*

---

### Q: "What about Google TimesFM — isn't that just using someone else's work?"

**A:** *"TimesFM is a general-purpose time-series foundation model. It knows nothing about weather, models, or India. We made the novel decision to apply it to forecast model error prediction — using each model's trailing error series as input. This specific application — predicting which weather model will degrade before it happens — has never been done before."*

---

### Q: "What if TimesFM — or regime conditioning — doesn't actually improve the forecast?"

**A:** *"Then we say so. Both sit behind a strategy interface and are measured against simpler baselines — equal weighting, then inverse-error weighting — in the same experiment framework. AtmosFusion's own ablation found regime features added zero skill; we're not going to assert ours does without the same test. Reporting a null result honestly is more credible to an NCMRWF judge than a system that has never checked."*

---

## 12. Implementation Plan

### 12.1 Governing Principle

Build order follows the **dependency chain, not feature attractiveness**:

```
data model → adapters → alignment → verification → baseline blends
     → adaptive weighting → extremes → TimesFM/regimes → API/frontend
```

Each stage only starts once the one before it produces **real, verified output**. No frontend work against fabricated numbers. No adaptive weighting before baselines exist to compare against. No extreme-probability module before the deterministic blend is verified.

### 12.2 Pre-Work: Data Acquisition (Start Immediately — Night of Sep 26)

Data downloads are the longest wall-clock bottleneck. Start these **tonight** in parallel before any code is written:

| # | Data Source | What to Download | Est. Size | Command / Method | Status |
|---|---|---|---|---|---|
| D1 | **WeatherBench2** | IFS HRES + GFS + GraphCast forecasts, India region (lat 5–38°N, lon 65–100°E), 2020–2023 | ~5–15 GB/model | `xarray.open_zarr('gs://weatherbench2/...')` with `.sel(latitude=slice(38,5), longitude=slice(65,100))` | [ ] |
| D2 | **WeatherBench2** | ERA5 reanalysis (same region/years) — supplementary ground truth | ~3–5 GB | Same Zarr interface | [ ] |
| D3 | **IMD Gridded Rainfall** | Pai et al. 0.25° daily gridded rainfall, 2020–2023 | ~200 MB | Dataset request or cached `.nc` file | [ ] |
| D4 | **IMD Gridded Temperature** | 1° Tmax/Tmin daily, 2020–2023 | ~100 MB | Dataset request or cached `.nc` file | [ ] |
| D5 | **India District GeoJSON** | Administrative boundary polygons (730+ districts) | ~15 MB | `datameet` GitHub or Survey of India shapefile | [ ] |
| D6 | **Open-Meteo** (live fallback) | Current GFS + ECMWF + ICON + AIFS for ~50 Indian cities | API calls | REST, cached as JSON | [ ] |

> **Risk:** IMD gridded data (D3, D4) may require an institutional request that takes days. **Mitigation:** Use ERA5 (D2) as primary ground truth for the prototype; note in the presentation that IMD data is the production target. This is honest and still scientifically valid.

### 12.3 Sprint Plan (4 Sprints)

---

#### SPRINT 1 — Foundation (Sep 27, Morning → Evening)
**Goal:** Data flows end-to-end from raw source to a blended grid. No ML, no extremes — just prove the pipeline works.

| Task | Module (§6.9) | Definition of Done |
|---|---|---|
| S1.1 Define `CanonicalForecast` schema | `canonical/` | Schema can represent GFS, ECMWF, and GraphCast fields with common coordinate convention |
| S1.2 Write GFS adapter | `ingestion/gfs.py` | `adapter.load(init_time, lead_hours, variable)` returns a valid canonical object for precipitation and 2m temp |
| S1.3 Write ECMWF adapter | `ingestion/ecmwf.py` | Same interface, same variables |
| S1.4 Write GraphCast adapter | `ingestion/graphcast.py` | Same interface, same variables |
| S1.5 Quality gate | `canonical/` | Rejects a deliberately corrupted test input; passes clean inputs |
| S1.6 Grid/time alignment | `canonical/grid.py` | All three models on common 0.25° grid, common valid times |
| S1.7 `EqualWeightStrategy` | `weighting/equal.py` | `blend = (gfs + ecmwf + graphcast) / 3` — trivial, but proves the pipeline |
| S1.8 Smoke test | `experiments/` | `python experiments/run.py --strategy equal --date 2022-06-15` outputs a blended `.nc` you can plot |

**Checkpoint:** A blended rainfall grid for India that you can plot with `matplotlib`. If this doesn't work, nothing downstream works.

---

#### SPRINT 2 — Verification & Baseline Ladder (Sep 28, Morning → Evening)
**Goal:** Produce the first **real, measured numbers**. This is what separates us from every synthetic competitor.

| Task | Module | Definition of Done |
|---|---|---|
| S2.1 Load ground truth | `verification/` | Observation xarray aligned to forecast grid |
| S2.2 Deterministic verification | `verification/deterministic.py` | RMSE, MAE, Bias table for GFS / ECMWF / GraphCast / Equal-blend, Days 1–10 |
| S2.3 FSS implementation | `verification/fss.py` | FSS at 25/50/100/150 km for rainfall ≥ 15 mm; produces skill-vs-scale curve |
| S2.4 `InverseErrorStrategy` | `weighting/inverse_error.py` | Weights computed from trailing 30-day RMSE, per model × variable × lead |
| S2.5 Rolling-origin split | `experiments/runner.py` | Train 2020–2021 / Test 2022, Train 2020–2022 / Test 2023 — no leakage |
| S2.6 **Baseline Ladder v1** | `evaluation/reports.py` | Side-by-side table: single models → EqualWeight → InverseError, with RMSE, MAE, FSS@50km |
| S2.7 Bootstrap CIs | `verification/bootstrap.py` | 95% block-bootstrap CIs on RMSE differences |

**Checkpoint:** A table like this with **real numbers**:

```
| Strategy              | RMSE (mm) | MAE (mm) | FSS@50km | vs best single |
|-----------------------|-----------|----------|----------|-----------------|
| GFS alone             |   ?.??    |   ?.??   |   ?.??   |    baseline     |
| ECMWF alone           |   ?.??    |   ?.??   |   ?.??   |    baseline     |
| GraphCast alone       |   ?.??    |   ?.??   |   ?.??   |    baseline     |
| Equal-weight blend    |   ?.??    |   ?.??   |   ?.??   |     -?.?%       |
| Inverse-error blend   |   ?.??    |   ?.??   |   ?.??   |     -?.?%       |
```

This table IS the scientific core of the presentation. Even if inverse-error doesn't beat equal-weight, **that's a reportable finding**.

---

#### SPRINT 3 — Intelligence Layer & Frontend (Sep 29, Morning → Evening)
**Goal:** Add context-aware weighting and build the visual dashboard. Two parallel tracks.

**Track A — Backend:**

| Task | Module | Definition of Done |
|---|---|---|
| S3.1 `ContextAwareStrategy` | `weighting/context.py` | Weights conditioned on region × lead × season. Different weights for monsoon-Kerala vs winter-Rajasthan |
| S3.2 Regime detection (basic) | `regimes/detector.py` | Heavy-rain flag (Central India daily rainfall > 1σ above climatology). Ideally: Active/Break classification |
| S3.3 Regime ablation | `experiments/` | Baseline Ladder extended: context-without-regime vs. context-with-regime. Honest result |
| S3.4 Physical validator | `blending/physical.py` | Clips rain < 0, clamps Td ≤ T. Logs every correction |
| S3.5 Extreme probability module | `hazards/rainfall.py` | `P(rain > 64.5mm)`, `P(rain > 115.6mm)` from multi-model spread |
| S3.6 Heatwave module | `hazards/heatwave.py` | Flag cells meeting IMD heatwave criteria |

**Track B — Frontend (parallel):**

| Task | What | Definition of Done |
|---|---|---|
| S3.7 Project scaffold | Vite + Leaflet + Chart.js | `npm run dev` serves India base map |
| S3.8 District Traffic Light Map | Leaflet + GeoJSON | Districts colored G/Y/O/R from S3.5 probabilities. Click popup shows details |
| S3.9 Model Weight Map | Leaflet choropleth | Dominant model per region. Lead-time slider D+1 to D+10 |
| S3.10 Spaghetti Panel | Chart.js line chart | Select city → GFS/ECMWF/GraphCast/Blend lines with confidence band |
| S3.11 Forecaster Decision Card | HTML/CSS | Styled summary card for one state, populated from real data |
| S3.12 Leaderboard | HTML/CSS table | Model skill rankings by variable |

**Checkpoint:** Dashboard loads with **real data** from Sprint 2. A non-technical person can see: (a) where the danger is, (b) which model to trust, (c) how confident the forecast is.

---

#### SPRINT 4 — Polish, Story & Presentation (Sep 30)
**Goal:** Transform "technically correct" into "wins the hackathon."

| Task | Priority | Definition of Done |
|---|---|---|
| S4.1 Kerala 2018 Replay | HIGH | Aug 2018 data loaded. Shows: model predictions → actual event → our blend → "Red Alert 72h early" |
| S4.2 `TimesFMStrategy` (if time) | MEDIUM | Plugged behind strategy interface. Measured against baseline ladder. Result reported honestly |
| S4.3 Spatial weight smoothing | MEDIUM | Gaussian pass eliminating salt-and-pepper weight artifacts |
| S4.4 Weather Movie animation | LOW | Timeline slider animating Day 1→10 rainfall evolution on Leaflet |
| S4.5 Presentation slides | CRITICAL | 10–12 slides: Hook → Problem → Architecture → Demo → Baseline Ladder → Extreme Weather → Kerala Replay → Innovation Defense → Future Work |
| S4.6 Demo recording | CRITICAL | 3-minute screen recording as backup if live demo fails |
| S4.7 README + repo cleanup | HIGH | Clean README with setup instructions, architecture diagram, Baseline Ladder table |
| S4.8 Number update | CRITICAL | Replace ALL placeholder numbers in pitch/slides with **actual measured values** from Sprint 2 |

### 12.4 Risk Matrix

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| WeatherBench2 download slow/fails | Medium | Critical | Start tonight (§12.2). Fallback: Open-Meteo API for live data (fewer years, still functional) |
| IMD gridded data unavailable in time | High | Moderate | Use ERA5 as ground truth. Note IMD as production target |
| TimesFM model too large / slow | Medium | Low | Behind strategy interface. If it fails, `ContextAwareStrategy` is the top rung |
| Regime conditioning adds zero skill | Medium | Low | Reportable finding, not a failure. Ablation ladder handles it |
| Frontend can't consume backend data in time | Medium | Moderate | Backend writes static JSON. Frontend reads files. No live API needed for Day 1–3 |
| Live demo crashes during presentation | Low | Critical | Record 3-min demo video (S4.6) as backup |
| Blend worse than best single model for some region | High | Low | Expected. Show WHERE and WHY. Forecaster override handles it |

### 12.5 Definition of Done — Minimum Viable Submission

The submission is **presentable to NCMRWF judges** when ALL of these are true:

- [ ] **Real data in, real numbers out.** Not a single `np.random` or hardcoded weather value in the pipeline
- [ ] **Baseline Ladder table** with measured RMSE/FSS for ≥3 models + 2 blending strategies, with 95% CIs
- [ ] **At least one visual map** (district traffic light OR model weight map) showing real, data-driven output
- [ ] **One extreme weather demo** — probabilistic exceedance map or Kerala 2018 replay
- [ ] **Presentation slides** with 30-second pitch, architecture, baseline ladder, and live/recorded demo
- [ ] **Leakage-free verification** — can answer "how do you prevent data leakage?" with rolling-origin split
- [ ] **GRIB2 readiness** — can answer "can this run on our HPC?" by showing adapter pattern + working `cfgrib` import

If all seven boxes are checked, the submission is **stronger than every competitor in §3**, regardless of whether TimesFM, regime conditioning, or the weather movie made it in.

### 12.6 What NOT to Build (Time Traps)

| Temptation | Why Skip It | Do This Instead |
|---|---|---|
| LLM Chatbot (like AAGAM/AtmosBlend) | Gimmick. NCMRWF scientists won't use it. Eats 4–8 hours | Spend those hours on FSS verification |
| Polished login/auth system | Nobody logs in during a demo | Hardcode a "Forecaster Mode" toggle |
| Mobile responsive design | Judges view on a projector | Optimize for 1920×1080 landscape |
| Multiple color themes | One dark professional theme is enough | Spend time on map interactivity |
| Animated mascot / gamified onboarding | Tone mismatch for disaster management | Clean 3-step guided tour banner |

---

## 13. 30-Second Judge Pitch

> **"Weather models disagree. During a disaster, who do you trust?"**
>
> Different models perform differently depending on region, season, and weather regime. No single model is best everywhere.
>
> **Our system is the decision intelligence layer** that answers: which model to trust, when, where, and why.
>
> We ingest physics-based NWP (NCUM, GFS), AI models (Google GraphCast), and ensemble forecasts (NEPS/GEFS) through a native GRIB2 pipeline — not web APIs.
>
> Our **6-dimensional trust engine** — model, variable, region, lead time, season, weather regime — dynamically assigns weights based on each model's proven skill for the exact operational context. Every added dimension is validated through ablation against a simpler baseline — verified against IMD ground truth using WMO-standard spatial verification (Fractions Skill Score).
>
> For disaster management, we don't just blend means — we generate **calibrated probabilities**: "82% chance of Very Heavy Rain in Ratnagiri district." Mapped to IMD's exact Yellow/Orange/Red warning system, with population impact.
>
> The forecaster always has the final call — our weight maps are explained, and every cell is overridable.
>
> **The result:** Measured, verifiable skill improvement over every individual model — proven through a leakage-free baseline ladder, not assumed. Extreme weather alerts that catch events other systems miss, and an operational pipeline ready to run on NCMRWF's HPC from Day 1.

---

> **Document Status:** Living document. Updated as implementation progresses.  
> **Confidential:** Team use only until SIH presentation.
