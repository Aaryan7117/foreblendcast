# SIH26081 — Hybrid AI–NWP Multi-Model Forecast Blending System
## Research gaps in existing public solutions

**Organisation:** Ministry of Earth Sciences (MoES) · NCMRWF
**Survey date:** 26 September 2026
**Scope:** Public GitHub repositories targeting SIH26081 / "Hybrid AI–NWP Multi-Model Forecast Blending System"

---

## 1. Landscape summary

| Repo | Forecast sources | Ground truth | Variables verified | Reported gain | Key limitation |
|---|---|---|---|---|---|
| [AtmosFusion](https://github.com/Gaurav-205/SIH-2026) | 10+ models via Open-Meteo; AIFS/GEFS via dynamical.org Zarr | IMD 0.25° gridded rain, Tmax | Rain, Tmax | Day-1 rain RMSE 13.28 mm vs 13.97 (equal mean); ETS ≥64.5 mm 0.29 | 29 districts in Konkan-Goa + Kerala only; days 1–5; regime/season/place features add no skill (own ablation); held-out 2025 test unscored |
| [MausamMix](https://github.com/parthnayyar07/mausammix) | WeatherBench2: IFS HRES + Pangu-Weather | ERA5 | 2 m temperature only | 15–18 % RMSE cut at Day 3–10 (2020–22, leakage-free) | No rain / wind / extremes / regime; 1.5° grid; Colab notebook, no operational layer |
| [Weather_Blend](https://github.com/PiyushSharma-05/Weather_Blend) | GFS, IFS, AIFS via Open-Meteo | ERA5 (archive API) | T, rain, wind | MAE 0.567 vs 0.676 best single; weekly block-bootstrap CIs | 3 point stations; one annual cycle, zero winter in train; 5–6 of 27 cells significantly worse than best model |
| [Omnicast / ForcastApp](https://github.com/jayshpatelfc-afk/ForcastApp) | "7 models" (NCUM, NEPS, GFS, ECMWF, GraphCast, FourCastNet, Pangu) | none | all (nominal) | "+24.8 % RMSE, +31 % ETS" | Dependencies are only `flask` + `requests`; model pool and metrics are synthetic; "NetCDF" output is a JSON manifest |
| [SAMVAY](https://github.com/rudhhstoic/SAMVAY) | synthetic (declared) | synthetic | all (nominal) | n/a | Full pipeline design on simulated sources; no real verification |
| [HYBRIDCAST](https://github.com/yuvaadhika/HYBRID-AI), [WEATHERFUSION-AWX](https://github.com/kashishpathak20/WEATHERFUSION-AWX), [AAGAM](https://github.com/bitsubhayu/AAGAM), [Synthesis](https://github.com/hitanshuthegr8/Synthesis--SIH26), [ForecastFusion](https://github.com/jai-ganesh-R/ForecastFusion), [MOSAIC](https://github.com/neerajrajput02511-ctrl/MOSAIC) | mostly Open-Meteo live feeds | none or illustrative | varies | unverified / illustrative | Dashboard-first prototypes; no leakage-free historical verification |
| [HYBRID-AI-NWP-FORECAST](https://github.com/aditya0119d/HYBRID-AI-NWP-FORECAST) | GFS only | ERA5 | Temperature (Phase 1) | not reported | Single-model MOS bias correction (XGBoost residual), not multi-model blending |

**Cross-cutting observations**

- Open-Meteo's free API is the forecast source for nearly every entry — a commodity, not a differentiator.
- The three rigorous entries each cover a *slice*: AtmosFusion (rain, two regions), MausamMix (temperature, all-India grid), Weather_Blend (three variables, three points). None covers all five expected outcomes on real data.
- The feature-rich entries (Omnicast, HYBRIDCAST, etc.) cover every outcome nominally but on synthetic data.

---

## 2. Research gaps

### Gap 1 — NCMRWF's own models are absent from every pool
The problem owner operates NCUM-G, NCUM-R and NEPS. No repository ingests them, and none ingests a GRIB2 file at all; every entry reads JSON from a third-party API.
**Opportunity:** a generic GRIB2/NetCDF ingestion adapter (`cfgrib` / `xarray`), demonstrated on public NOMADS GFS GRIB2, with NCUM/NEPS declared as drop-in sources through the same adapter. Directly answers "can this run on our HPC?"

### Gap 2 — No entry verifies rainfall, temperature *and* wind on Indian observations across the whole country over multiple years
- AtmosFusion: IMD truth but only rain/Tmax, 29 districts, one training year.
- MausamMix: all-India grid but temperature only, ERA5 truth.
- Weather_Blend: three variables but three stations, 14 months.
**Opportunity:** WeatherBench2 archives (IFS HRES, IFS ENS, GraphCast, NeuralGCM, 2018–2022) × IMD 0.25° gridded rainfall and 1° Tmax/Tmin for the same years → five monsoon seasons, nationwide, Indian ground truth. Live operation on Open-Meteo continues the same skill ledger.

### Gap 3 — Weather-regime conditioning has not been shown to add skill
AtmosFusion's ablations (E5–E8) found regime, place and season features add no measurable skill; Weather_Blend's regime toggle activates in only 6/27 cells and is defined as a simple "high vs normal" threshold. Other entries assert regime awareness without testing it.
**Opportunity:** derive regimes from the models' own fields — monsoon-trough position, active/break spells (IMD rainfall-index definition), western-disturbance detection from 500 hPa troughs, cyclone detection from vorticity/MSLP — and report the ablation honestly, positive or null.

### Gap 4 — Extremes are handled by thresholding a blended mean
Mean-seeking blends smooth peaks; every entry that touches extremes still thresholds the blended value (Omnicast adds an ad-hoc "EV-Boost" max-mixing term on synthetic data).
**Opportunity:** probabilistic post-processing — quantile gradient boosting, EMOS or BMA — producing calibrated exceedance probabilities at IMD thresholds (64.5 / 115.6 / 204.5 mm rain; heatwave: Tmax ≥ 40 °C plains / ≥ 30 °C hills and departure ≥ 4.5 °C; gale-force wind). Verify with reliability diagrams, ROC, Brier skill score, CRPS.

### Gap 5 — Wind extremes are entirely unverified
No repository reports any wind-extreme (high-wind / gale) skill on real data; wind appears only as a blended mean in Weather_Blend.

### Gap 6 — Precipitation verification ignores spatial/neighbourhood scores
All entries use point-wise RMSE/MAE/ETS. Operational NWP centres verify rainfall with neighbourhood methods (Fractions Skill Score, SAL) because point scores double-penalise small displacement errors.
**Opportunity:** add FSS at multiple neighbourhood scales; report the scale at which the blend becomes skilful.

### Gap 7 — Model-version drift is not handled
Weather_Blend had to freeze its data window before the May 2026 IFS 50r1 / AIFS v2 upgrades because Open-Meteo exposes no run tags. No entry detects a model upgrade or resets/decays its skill memory when one occurs.
**Opportunity:** version tagging on ingestion, change-point detection on per-model error series, and automatic skill-memory reset with a forecaster notification.

### Gap 8 — Seasonal generalisation is untested
Weather_Blend trains with zero winter hours; AtmosFusion validates on 2024 only; MausamMix is the only entry with multi-season test years, and only for temperature. Nobody shows weights validated on an unseen monsoon season.

### Gap 9 — Lead-time coverage stops at Day 5 for real-data entries
AtmosFusion covers days 1–5; Weather_Blend 24/72/168 h. Only MausamMix (temperature) reaches Day 10, which is NCMRWF's medium-range remit.

### Gap 10 — Operational outputs are not in operational formats
Omnicast ships a JSON "NetCDF manifest"; most entries emit CSV/GeoJSON only. No entry writes CF-compliant NetCDF or GeoTIFF, and only AtmosFusion and Omnicast emit CAP 1.2 alerts. Scheduled 00Z/12Z cycles are simulated rather than run by a scheduler.
**Opportunity:** Docker + cron/Prefect cycle → NetCDF (CF-1.8), GeoTIFF, CAP 1.2, REST API.

### Gap 11 — Weight maps are not a first-class, explained product
The problem statement asks for model-weight maps. MausamMix produces them (temperature, 1.5°); AtmosFusion per district; others show mock-ups. None provides per-variable × per-lead × per-season gridded weight maps with a plain-language "why" per cell, or a forecaster override.

### Gap 12 — Statistical honesty is rare
Only Weather_Blend and AtmosFusion report confidence intervals (block bootstrap). Only MausamMix and Weather_Blend publish an explicit leakage guarantee. The rest report point estimates or synthetic numbers.

---

## 3. Gap-to-outcome map

| Expected outcome (problem statement) | Best existing coverage | Remaining gap |
|---|---|---|
| Dynamically blended forecast | AtmosFusion (rain), MausamMix (temp) | All four targets, all-India, Day 1–10, NCMRWF models (Gaps 1, 2, 9) |
| Model weight maps | MausamMix (temp, 1.5°) | Gridded, per variable/lead/season, explained, overridable (Gap 11) |
| Improved forecast skill | AtmosFusion, MausamMix, Weather_Blend | Multi-season test, FSS, CIs everywhere (Gaps 6, 8, 12) |
| Extreme weather guidance | AtmosFusion (Brier ≥64.5 mm), Weather_Blend (95th pct flags) | Calibrated probabilities, heatwave/wind criteria, reliability (Gaps 4, 5) |
| Operational workflow | AtmosFusion (daily cycle, CAP) | GRIB in, NetCDF/GeoTIFF out, scheduler, version-drift handling (Gaps 1, 7, 10) |

---

## 4. Sources

- https://github.com/Gaurav-205/SIH-2026
- https://github.com/parthnayyar07/mausammix
- https://github.com/PiyushSharma-05/Weather_Blend
- https://github.com/jayshpatelfc-afk/ForcastApp
- https://github.com/rudhhstoic/SAMVAY
- https://github.com/yuvaadhika/HYBRID-AI
- https://github.com/kashishpathak20/WEATHERFUSION-AWX
- https://github.com/bitsubhayu/AAGAM
- https://github.com/hitanshuthegr8/Synthesis--SIH26
- https://github.com/jai-ganesh-R/ForecastFusion
- https://github.com/neerajrajput02511-ctrl/MOSAIC
- https://github.com/aditya0119d/HYBRID-AI-NWP-FORECAST
- https://github.com/reddytharuni300-jpg/Hybrid-AI-NWP-Multi-Model-Forecast-Blendig-System
