# SIH26081 — Hybrid AI–NWP Multi-Model Forecast Blending System
## MASTER PLAN — Canonical Build & Strategy Document

**Problem ID:** SIH26081
**Organisation:** Ministry of Earth Sciences (MoES) · NCMRWF
**Theme:** Disaster Management · **Category:** Software
**Submission deadline:** 30 September 2026
**Document version:** v3.0 — 26 September 2026
**Status:** ✅ **CANONICAL.** This file supersedes `SIH26081_solution_blueprint.md` and `SIH26081_solution_revised`. Those two are archived; do not build from them.

---

## 0. How To Use This Document

| If you are… | Read |
|---|---|
| Starting work right now | §1 (Decisions Locked) → §13.2 (Tonight's Pre-Work) → your sprint in §13.3 |
| Writing code | §1, §7 (Architecture), §8 (Repo structure), §9 (Tech stack) |
| Building the frontend | §1, §11 (Features), §7.11 (Provenance/Exercise rules) |
| Making slides / pitching | §5 (Innovations), §12 (Scorecard), §14 (Q&A), §16 (Pitch) |
| Checking we didn't regress | §17 (Flaw→Fix traceability), §18 (Innovation index) |

**Document map — one canonical file, two annexes:**

```
SIH26081_MASTER_PLAN.md          ← THIS FILE. Single source of truth for scope, DoD, pitch.
TECH_APPROACH_AND_TEAMS.md       ← BINDING for tech choices (§9 "or"s resolved), algorithms,
                                    the results/ data contract, and the Team A / Team B split.
DECISIONS.md                       ← D-01…D-17 from §1, D-18…D-30 from TECH_APPROACH; append-only
SIH26081_research_gaps.md         ← INTERNAL ANNEX: competitor evidence, per-repo detail, sources
docs/archive/                     ← old blueprint + revised (historical only)
```

> ⚠️ **Rule:** if a number, year range, or design choice appears in a slide, it must trace to §1 or a `results/` file. Nothing in this document may be quoted to judges until it is measured. Placeholders are written as `?.??` on purpose.

---

## Table of Contents

1. [Decisions Locked (read first)](#1-decisions-locked-read-first)
2. [Problem Statement (Official)](#2-problem-statement-official)
3. [Expected Outcomes & How We Hit Each](#3-expected-outcomes--how-we-hit-each)
4. [Competitive Landscape (internal)](#4-competitive-landscape-internal)
5. [Research Gaps → Our Answer](#5-research-gaps--our-answer)
6. [Our Innovations](#6-our-innovations)
7. [Solution Architecture](#7-solution-architecture)
8. [Repository Structure](#8-repository-structure)
9. [Tech Stack](#9-tech-stack)
10. [Google AI Models — Honest Integration Strategy](#10-google-ai-models--honest-integration-strategy)
11. [User-Facing Features](#11-user-facing-features)
12. [Gap-to-Outcome Scorecard](#12-gap-to-outcome-scorecard)
13. [Implementation Plan](#13-implementation-plan)
14. [Judge Q&A Preparation](#14-judge-qa-preparation)
15. [Ethics, Provenance & Data Licensing](#15-ethics-provenance--data-licensing)
16. [The Pitch](#16-the-pitch)
17. [Flaw → Fix Traceability](#17-flaw--fix-traceability)
18. [Innovation Index](#18-innovation-index)
19. [Glossary of Metrics](#19-glossary-of-metrics)

---

# 1. Decisions Locked (read first)

These were ambiguous or contradictory across the earlier drafts. They are now **fixed**. Changing one requires updating this table, `DECISIONS.md`, and every downstream slide.

| # | Decision | **LOCKED VALUE** | Why this and not the alternative |
|---|---|---|---|
| **D-01** | **Canonical daily accumulation window** | **0300 UTC → 0300 UTC** (= 0830 IST → 0830 IST) | IMD's 0.25° gridded rainfall (Pai et al.) accumulates 0830–0830 IST. Verifying a 00Z–00Z forecast window against it introduces a **3-hour offset of monsoon rainfall** into every RMSE, FSS and threshold count. All forecasts are resampled to this window in `canonical/variables.py` **before** blending. Non-negotiable. |
| **D-02** | **Year range** | **Primary: 2020–2023** (4 monsoon seasons). **Stretch: extend back to 2018** if download bandwidth allows (6 seasons). | Earlier drafts said 2018–2022 (Gap 2), 2018–2023 (leakage example) and 2020–2023 (pre-work) in three places. One range only. |
| **D-03** | **Rolling-origin folds** | Train 2020–2021 → **Test 2022**; Train 2020–2022 → **Test 2023**. = **2 fully held-out monsoon seasons.** (Stretch range gives 3.) | Forces the pitch to say "four seasons, two held out" — not "five monsoon seasons", which the data does not support. |
| **D-04** | **Regime source** | **Forecast-derived only**, computed from the same model fields at the same lead time being blended. Never from observations. | Observation-derived regimes are (a) unavailable at forecast time → inoperable, and (b) leak the target into the weights → invalid. Hard rule in `regimes/base.py`. |
| **D-05** | **Softmax temperature τ** | **Fitted** by grid search on the validation fold, **per (variable, lead-band)**. Values recorded in `results/tau.json` and reported in the appendix. | τ is the most influential hyperparameter in the weighting scheme (τ→0 = winner-take-all; τ→∞ = equal weights). It cannot be left dangling in three formulas. |
| **D-06** | **Wind ground truth** | **ERA5 10 m wind**, with documented land-surface caveats. Claim is scoped to *"blend verified against ERA5; station verification is the production target."* **Stretch:** IMD AWS point data. | IMD gridded has no wind. We do not make an operational gale-force claim we cannot verify. |
| **D-07** | **Grid → district aggregation** | **Area-weighted 90th percentile** over the district polygon (default). `mean` and `max` available as UI toggles; choice printed on every map. | `max` turns every large district red; `mean` hides local extremes. This single choice determines what the flagship map looks like — so it is stated, not hidden. |
| **D-08** | **Case study event** | **Primary: North India / Himachal floods, July 2023** (inside the 2023 test fold → genuinely out-of-sample). **Alternate: Cyclone Biparjoy, June 2023.** **Kerala 2018 is DROPPED** unless 2018 is excluded from training entirely. | "We would have warned 72 h early" is invalid if the event year is in the training data. Out-of-sample beats emotionally resonant. |
| **D-09** | **Environment** | **conda-forge env** (`environment.yml`, committed) — or Docker if conda fails. Resolved and verified **tonight**, not on Sprint 1 morning. | `cfgrib`/`eccodes` on native Windows is a known install trap, and it sits directly on our strongest claim ("runs on NCMRWF HPC"). |
| **D-10** | **Ground truth priority** | **Rain:** IMD 0.25° gridded (primary) → ERA5 (fallback, with explicit caveat that ERA5 monsoon precip has large known biases). **Temperature:** IMD 1° Tmax/Tmin → ERA5. **Wind:** ERA5 (per D-06). | ERA5 substitution is acceptable for temperature/wind; for **rainfall** it must be flagged as a material limitation, not waved through as "still scientifically valid". |
| **D-11** | **Deterministic rain blending method** | **Probability-matched blending** (§7.6), not a plain weighted mean. | A weighted mean destroys the rainfall peaks the system exists to warn about — our own Gap 4. |
| **D-12** | **Headline metric policy** | Rain is **never** reported with RMSE alone. Every rain result ships **RMSE + FSS + frequency bias + intensity CDF** together. | RMSE rewards smoothing; a mean-seeking blend "wins" RMSE while being operationally useless. We say this out loud before a judge says it to us. |
| **D-13** | **Output legal status** | Every output carries CAP `status="Exercise"` and a persistent **"EXPERIMENTAL — NOT AN OFFICIAL IMD WARNING"** banner + provenance block. | Issuing weather warnings is IMD's statutory mandate. Under MoES's own panel this earns marks rather than costing them. |
| **D-14** | **Competitor teardown** | Detailed teardown stays in the **internal annex** (`SIH26081_research_gaps.md`). The submission discusses *"published approaches"* without naming repos, teams or deployments. | One wrong claim about a named team is a credibility hit, and panels dislike naming-and-shaming regardless. |
| **D-15** | **Population data** | **WorldPop 1 km India raster** (or GPW v4) downloaded and cited — **or** the population figure is deleted from the UI. | An un-sourced "Affected population: 1.6M" is the exact fabrication we criticise in others. |
| **D-16** | **Team allocation** | **FILLED 27 Sep: 1 backend + 1 frontend.** Two people, no third. Scope, contract and ownership re-sized in `TECH_APPROACH_AND_TEAMS.md` §4; §13.5 below becomes **8 core + 4 stretch** per TECH_APPROACH §4.7. | The §13.3 sprint tables were sized for four people; for two, TECH_APPROACH §4.4/4.5 are the binding half-day plans with hard cut lines. |
| **D-17** | **Version control** | `git init` done. Feature branches, `main` always runnable. `environment.yml` + `package-lock.json` committed. | Four days, parallel tracks, one shared numeric result set. |

---

# 2. Problem Statement (Official)

> **Different forecasting systems perform differently depending on region, season, lead time and weather situation.** Physical NWP models, ensemble forecasts and AI/ML weather models may each have strengths under different conditions. Therefore, there is a need for an intelligent blending system that can dynamically combine multiple forecasts.

> The challenge is to develop a **hybrid AI–NWP blending framework** that assigns **adaptive weights** to different forecast sources based on **historical skill, forecast lead time, region, season and weather regime**. The final product should provide an optimized forecast for **rainfall, temperature, wind and extreme weather indicators**.

### Key reading of the statement
The PS names **five conditioning axes** (historical skill, lead time, region, season, regime) and **four target quantities** (rainfall, temperature, wind, extreme indicators). Together with the model identity, the trust function the PS is asking for is six-dimensional:

```
W = f(model, variable, region, lead_time, season, regime)
```

The PS is **not** asking us to build a weather model. It is asking for the **decision layer above** the models. That distinction is the whole pitch (§16).

---

# 3. Expected Outcomes & How We Hit Each

| # | Official Expected Outcome | What judges look for | **Our delivery** |
|---|---|---|---|
| 1 | **Dynamically blended forecast** | Continuous gridded blend, all-India, Day 1–10, multiple variables | Gridded 0.25° blend for rain / T / wind, Day 1–10, via Model Registry + Canonical Forecast layer (§7.2), with **probability-matched** rain blending (§7.6) |
| 2 | **Model weight maps** | 2D spatial maps per model, variable, lead, regime | Gridded weight maps with **hierarchical shrinkage** (§7.4), **computed leave-one-model-out explanations** (§6.E), lead-time slider, forecaster override |
| 3 | **Improved forecast skill** | Quantified improvement vs. individual models, against Indian truth, with CIs | **Full baseline ladder with climatology floor and hindsight-oracle ceiling** (§7.5), RMSE + FSS + frequency bias + intensity CDF, block-bootstrap CIs, **leakage-free rolling origin** (D-03) |
| 4 | **Extreme weather guidance** | Calibrated exceedance probabilities at IMD thresholds | Predictive distribution → isotonic calibration → IMD Green/Yellow/Orange/Red, verified with Brier, reliability diagram, ROC-AUC **and Relative Economic Value** (§6.D) |
| 5 | **Operational workflow** | Scheduled cycles, operational formats, not just a dashboard | GRIB2 in → CF-1.8 NetCDF / GeoTIFF / CAP 1.2 (`status=Exercise`) out, Docker + scheduler, **verified graceful degradation** (§7.9), **version-drift change-point detection** (§6.H), full provenance stamping (§7.11) |

---

# 4. Competitive Landscape (internal)

> **D-14 applies:** this section is internal. In the submission, refer to "published approaches" in aggregate. Full per-repo evidence lives in `SIH26081_research_gaps.md`.

### 4.1 Summary

| Class | Entries | Real data? | Coverage | Fatal limitation |
|---|---|---|---|---|
| **Rigorous but narrow** | AtmosFusion, MausamMix, Weather_Blend | ✅ | Each covers a *slice*: rain over 29 districts / temperature only / 3 point stations | None covers all five expected outcomes on real data |
| **Feature-rich but synthetic** | Omnicast, SAMVAY, AtmosBlend-AI | ❌ | Nominally everything | Values from `np.random` or declared-synthetic pipelines; metrics not measurable |
| **Dashboard-first** | HYBRIDCAST, WEATHERFUSION-AWX, AAGAM, MOSAIC, ForecastFusion, Synthesis | Live API only | Varies | No leakage-free historical verification at all |
| **Single-model MOS** | HYBRID-AI-NWP-FORECAST | ✅ | Temperature, GFS only | Bias correction, not multi-model blending |

### 4.2 The five structural openings

1. **Open-Meteo is a commodity.** Nearly every entry reads the same free JSON API. Not a differentiator — and it cannot run on NCMRWF's HPC.
2. **Nobody ingests a GRIB2 file.** The problem owner's own models (NCUM-G, NCUM-R, NEPS) appear in **zero** pools.
3. **Nobody covers rain + temperature + wind, nationwide, multi-year, against Indian observations.**
4. **Nobody uses operational-grade verification.** No FSS, no reliability diagrams, no decision-value analysis, almost no confidence intervals.
5. **Nobody reports a null result.** Every entry claims uniform victory — which is, to a verification scientist, a tell.

### 4.3 What we borrow (good ideas exist in weak repos)
- Dark command-centre dashboard aesthetic (appropriate for disaster management; skip mascots and chatbots).
- A guided 3-step tour banner for non-technical judges.
- A crisp 30-second pitch block in the README.

### 4.4 Specific anti-patterns to avoid
- **N-of-N consensus alert rules** (one entry requires 4/4 models to agree before alerting) → catastrophic false negatives. We use **calibrated probability thresholds**, not consensus votes.
- **Macro-regions** (one weight set for all of "SOUTH") → we use gridded weights with shrinkage.
- **Stopping at Day 5/Day 7** → NCMRWF's remit is medium range; we go to Day 10.
- **LLM chatbots** → gimmick; no operational forecaster will use it.

---

# 5. Research Gaps → Our Answer

All twelve gaps plus the meteorological blind spots, each mapped to the section that closes it.

| Gap | The gap in one line | Our answer | Where |
|---|---|---|---|
| **G1** | NCMRWF's own models (NCUM-G/R, NEPS) absent from every pool; **no entry reads GRIB2 at all** | Model Registry + per-source Adapter → Canonical Forecast. NCUM/NEPS = one new file + one registry line, zero downstream changes. Demonstrated on real NOMADS GFS GRIB2. | §7.2, §8 |
| **G2** | No entry verifies rain **and** temperature **and** wind, nationwide, multi-year, on Indian observations | WeatherBench2 archives × IMD 0.25° rain / 1° Tmax-Tmin, 4 monsoon seasons, all-India, 2 seasons fully held out | §7.3, D-02/03/10 |
| **G3** | Regime conditioning **has never been shown to add skill** (AtmosFusion's own ablation: zero) | Forecast-derived dynamical regimes (D-04) **+ we verify the detector itself** (§6.G) **+ the regime rung is ablated and reported honestly, positive or null** | §6.G, §7.5 |
| **G4** | Extremes handled by thresholding a blended **mean** — which smooths the peak | **Probability-matched blending** preserves intensity distribution (§7.6) **+** a real predictive distribution → calibrated exceedance probability (§7.7) | §7.6, §7.7 |
| **G5** | Wind extremes entirely unverified by anyone | Wind blended as **(u,v) vectors**, speed derived; verified against ERA5 with stated caveats (D-06); claim scoped honestly | §7.6, D-06 |
| **G6** | Rain verification ignores neighbourhood scores | FSS at 5/25/50/100/150 km with the **correct** skill criterion `FSS_useful = 0.5 + f₀/2` → skill-vs-scale curve | §7.8 |
| **G7** | Model-version drift undetected; no skill-memory reset | Version tagging on ingest + **CUSUM/`ruptures` change-point detection on real error series, demonstrated on an actual IFS cycle upgrade inside our window** | §6.H |
| **G8** | Seasonal generalisation untested (one entry trains with zero winter) | Season is an explicit ladder rung; rolling-origin across full annual cycles; per-season skill table | §7.5 |
| **G9** | Real-data entries stop at Day 5 | Day 1–10 for all variables, skill reported per lead day | §7.3 |
| **G10** | Outputs are CSV/GeoJSON/JSON-pretending-to-be-NetCDF; cycles simulated | CF-1.8 NetCDF + GeoTIFF + CAP 1.2 (`status=Exercise`), Docker + real scheduler, full provenance block | §7.11 |
| **G11** | Weight maps are not a first-class **explained** product | Gridded per variable × lead × season × regime, **explanation computed by leave-one-model-out impact** (not prose), forecaster-overridable with audit log | §6.E, §11 |
| **G12** | Statistical honesty is rare | Bootstrap CIs on every number, structural leakage prevention, **the "Where We Lose" map** (§6.I), **`make reproduce`** regenerating every slide number (§6.J) | §6.I, §6.J |
| **B1** | *Blind spot:* blending T and Td independently → Td > T; scalar wind blending → vector inconsistency | `PhysicalValidator` — blend (u,v) and derive speed; clamp Td ≤ T; clip rain ≥ 0; **every correction logged, not silently patched** | §7.6 |
| **B2** | *Blind spot:* models arrive asynchronously in live 00Z/12Z ops | Missing models are a **first-class state**; weights renormalised **and recalibrated per availability pattern**, and the degraded configurations are **verified**, not just tagged | §7.9 |
| **B3** | *Blind spot:* interpolation across steep terrain (Ghats, Himalaya) | **Elevation- and coast-stratified verification** (§6.K) — a measured finding rather than an unbuilt model change; elevation/land-sea masks in the weight stage | §6.K, §7.4 |
| **B4** | *New:* overfitting of a 6-D weight table on ~4 seasons | **Hierarchical shrinkage + minimum-sample fallback ladder** (§6.B) — the principled fix; spatial smoothing alone treats a sampling problem as cosmetic | §6.B, §7.4 |
| **B5** | *New:* no floor and no ceiling on the results table | **Climatology + persistence floor; per-cell hindsight oracle ceiling** → "we capture X% of achievable gain" | §6.C, §7.5 |
| **B6** | *New:* "so what?" is unanswered for a decision-maker | **Relative Economic Value (cost–loss) curves** — the key slide for a Disaster Management panel | §6.D |

---

# 6. Our Innovations

### The core framing

> *"Google didn't invent websites — it invented the intelligence that decides which website to trust. We didn't invent weather models. We built the intelligence that decides which weather model to trust for your district, your season, your lead time and your weather regime — and we prove how much of the achievable skill that intelligence actually captures."*

### The four-part differentiated claim
No competitor can say any of these:
1. Our blended rain field **stays physically realistic** (probability-matched, §6.A).
2. We **quantify how much of the achievable skill we capture** (floor + ceiling, §6.C).
3. We tell you **where the forecast is unusually unsure** (disagreement index, §6.F).
4. We show you **where we lose** (§6.I).

---

## Foundational Innovations (the PS deliverables, done properly)

### I-1 · Six-Dimensional Context-Aware Trust Scoring — built as a scored ladder, not a lookup table

The PS names season alongside region, lead and regime, so:
```
W = f(model, variable, region, lead_time, season, regime)
```
We deliberately do **not** build this as one 6-D table on day one — with four seasons of data it overfits instantly and produces noisy, unexplainable weights. It is built as a ladder where **every added axis must earn its place through an ablation**:

```
climatology / persistence            ← the reference floor (NEW)
        ↓
best single model
        ↓
equal weights                        ← does ANY blending help?
        ↓
inverse historical error
        ↓
+ region × lead conditioning
        ↓
+ season conditioning
        ↓
+ regime conditioning (forecast-derived, D-04)
        ↓
score[m, v, r, lead, season, regime]  with hierarchical shrinkage (§6.B)
        ↓
weight = softmax(−score / τ)          τ fitted, not guessed (D-05)
        ↓
per-cell hindsight oracle            ← the achievable ceiling (NEW)
```

**The IP is the scoring function *and* the ladder that validates it** — not the final weight numbers.

**Prerequisite, do this before choosing rungs (20 minutes, Sprint 2):** histogram the **sample count per (region × lead × season × regime) cell**. Cells like *"cyclone regime × Day 9 × Kerala"* may hold three samples. That histogram tells you which rungs are even estimable. Do not skip it.

### I-2 · Dynamical Regime Detection from Forecast Fields

| Regime | Detection | Source |
|---|---|---|
| Active vs. Break monsoon | Central India rainfall index, IMD definition | **Forecast fields** (D-04) |
| Western Disturbance | 500 hPa geopotential trough detection | **Forecast fields** |
| Cyclone proximity | MSLP gradient + 850 hPa relative vorticity | **Forecast fields** |
| Heat wave | IMD criteria: Tmax ≥ 40 °C plains / ≥ 30 °C hills **and** departure ≥ 4.5 °C | **Forecast fields** |

Gap 3 exists because the one team that tested regime conditioning found **zero** skill gain. We do not assert ours helps — we ablate it, we verify the detector itself (§6.G), and we report the result either way.

### I-3 · Probabilistic Extreme Hazard Calibration to IMD Standards
Output the sentence no competitor can produce:
> *"78 % probability that rainfall in Ratnagiri exceeds 115.6 mm (IMD Very Heavy) in the next 24 h."*

Real predictive distribution → isotonic calibration → IMD's exact Green/Yellow/Orange/Red thresholds (64.5 / 115.6 / 204.5 mm rain; heatwave and wind criteria per IMD). Verified with Brier, reliability diagram, ROC-AUC **and decision value** (§6.D).

### I-4 · Forecaster-in-the-Loop Override with **Computed** Explainability
An NCMRWF duty forecaster can:
- see **why** each model has its weight — as a **measured** attribution, not a hand-written sentence (§6.E);
- **override** a cell or region during a critical event;
- have every override **logged and auditable** with user, timestamp, reason and the pre-override weights.

### I-5 · Spatial Verification Framework for India (FSS, done correctly)
FSS at 5/25/50/100/150 km per IMD threshold, producing a **skill-vs-scale curve**, using the correct criterion `FSS_useful = 0.5 + f₀/2` (Roberts & Lean 2008) — not the incorrect flat "FSS > 0.5" in the earlier drafts.
> *"At 50 km the blend is skilful for heavy rain; GFS alone needs 150 km to reach the same skill."*

---

## New Innovations (v3.0 — these are the differentiators)

### 6.A · Probability-Matched Blending — our strongest scientific card
**Problem it solves:** a weighted mean smooths exactly the rainfall peak the system exists to warn about. Our own Gap 4 diagnoses this — and then the earlier draft's blend was still a weighted mean.

**Method:** take the **location** information from the weighted-mean field, but remap its intensity distribution onto the weighted-member CDF, so the blended field's rainfall distribution matches the members'.
```
1. M      = weighted_mean(members)                  # good location skill
2. P_pool = sorted(concat(members), weighted)       # correct intensity distribution
3. rank M's cells, assign the corresponding quantile from P_pool
4. → blended field with member-like intensities and mean-like placement
```
Standard at operational centres (probability-matched mean, Ebert 2001; used in US HREF/NBM), essentially absent from SIH-tier work, and **~30 lines of numpy percentile mapping.**

**Claim it buys:** *"Every other blend smooths the peak it was built to warn about. Ours preserves the intensity distribution of its members while taking the location skill of the blend — here are the side-by-side CDFs and the FSS at heavy-rain thresholds."* **Closes G4 and G6 at once.**

### 6.B · Hierarchical Shrinkage Weights with Minimum-Sample Fallback
**Problem it solves:** a 6-D weight table over ~4 seasons is a sampling problem. Gaussian smoothing of the weight map treats it as a cosmetic one.

**Method:** estimate at the finest level, then shrink toward coarser parents by effective sample size:
```
w_cell = λ·w_cell_raw + (1−λ)·w_parent ,   λ = n_eff / (n_eff + k)

fallback ladder:  cell → district → homogeneous region → national
```
Below a sample threshold, a cell **automatically inherits its parent's weights and says so in its explanation** ("insufficient local history: using Konkan regional weights, n=17").

**Why it matters:** this is the principled answer to "how do you avoid overfitting?" — *structurally*, not by hope. It is a genuine methodological contribution and it makes I-1 statistically real.

### 6.C · Climatology Floor + Hindsight-Oracle Ceiling
**Problem it solves:** the results table had no floor and no ceiling, so "better than GFS by Y%" was the only possible statement.

- **Floor:** climatology and persistence as reference forecasts — operational verification always includes them, and skill scores are normally expressed *against* climatology. Without them you cannot claim the blend is **skilful**, only that it beats GFS.
- **Ceiling:** the **per-cell hindsight oracle** — pick the best model in each cell *knowing the answer*. This is the maximum any weighting scheme could ever extract.

**Claim it buys:** *"We capture X % of the achievable gain between the best single model and the hindsight ceiling."* That reframes results from a percentage to a narrative: **floor → best single → our blend → ceiling.**

### 6.D · Cost–Loss Decision Value — the killer slide for a Disaster Management panel
**Problem it solves:** Brier score and reliability answer *"is the probability honest?"* Neither answers *"so what?"* for a District Magistrate.

**Method:** from the same contingency tables, compute the **Relative Economic Value** curve (Richardson 2000) across cost:loss ratios.

**Claim it buys:**
> *"For a district responder whose cost of acting is one-tenth the loss of not acting, our blend delivers 0.38 decision value versus 0.21 for the best single model."*

WMO-standard, near-free once contingency tables exist, and almost certainly unique in this problem statement. **Highest value per hour in the entire plan.**

### 6.E · Computed Weight Explanations via Leave-One-Model-Out Impact
**Problem it solves:** I-4 promised explainability but the example was a hand-written sentence — un-auditable and not generalisable.

**Method:** per cell, recompute the blend with each model removed:
> *"Removing ECMWF here raises RMSE 14 %. Removing GraphCast raises it 2 %."*

N blend recomputations — trivial. Every weight-map hover becomes a **measured attribution**, and the override UI becomes honest because the forecaster sees what each model actually contributes.

### 6.F · Normalized Model-Disagreement Index — a novel operational product
**Problem it solves:** everyone converts spread into probability. Nobody flags *anomalous* spread.

**Method:**
```
D = spread(t) / climatological_spread(cell, season, regime)
```
High **D** = models disagree *more than they usually do here* = **"forecaster attention needed."**

**Claim it buys:** *"We don't just tell you the forecast — we tell you where the forecast is unusually unsure."* A product a duty forecaster would open the dashboard for. Not in any competitor, and ~50 lines.

### 6.G · Verify the Regime Detector Itself
**Problem it solves:** turns the D-04 constraint from a risk into a measurable sub-claim.

Compare forecast-derived regime classifications against observation-derived ones:
> *"Our forecast-derived regime classification agrees with observation-derived regimes 84 % of the time at D+3, degrading to 61 % at D+7."*

Now regime conditioning has a measured foundation — and if the ablation is null we can explain **why** (detector degrades with lead time), which is a far stronger finding than a bare null.

### 6.H · Demonstrated Version-Drift Detection (rescues orphaned G7)
**Problem it solves:** G7 was a listed differentiator with **zero implementation path in any sprint**.

Our WB2 window spans real IFS cycle upgrades. Run CUSUM / `ruptures` change-point detection on per-model error series and **show the detected change point on a real plot**, with the skill-memory reset firing. A claimed differentiator becomes a demonstrated one, using data already on disk. **Half a day.**

### 6.I · The "Where We Lose" Slide
**Problem it solves:** G12, and the credibility ceiling of claiming uniform victory.

An explicit map + table of regions / leads / regimes where the blend is **worse** than the best single model, with the reason and the override path. Every competitor claims it always wins. Being the only team that shows its own failure modes — with bootstrap CIs — is the strongest available signal of scientific maturity to an NCMRWF panel.

### 6.J · One-Command Reproducibility
```bash
make reproduce     # regenerates every number in the deck from configs
```
Then say it out loud: *"every number in this deck was produced by this command; here is the log."* This weaponises the fact that several published approaches have synthetic numbers — **without naming anyone** (D-14).

### 6.K · Elevation- and Coast-Stratified Verification
**Problem it solves:** blind spot B3, cheaply. The drafts flagged topographic masking then proposed a modelling fix there is no time for.

Report skill **stratified** by: Western Ghats windward / Ghats leeward / Himalayan foothills / interior plains / coastal strip.
> *"The blend's largest gain is on the leeward side of the Ghats, where GFS's rain-shadow bias is worst."*

A real meteorological finding from a `groupby`.

### 6.L · Provenance-Stamped, Exercise-Flagged Outputs
Every NetCDF / GeoTIFF / CAP file carries: model list, availability pattern, weight strategy, τ, git commit SHA, ground-truth source, generation timestamp, and `status="Exercise"`.

Operational centres call this **traceability**. It is what actually separates a system that *could* run at NCMRWF from one that merely reads GRIB2 — and it discharges the ethical duty in D-13.

---

# 7. Solution Architecture

> **Framing.** The core scientific experiment is separated from optional enhancements. The **minimal path** — *3 real models → canonical schema → aligned data → historical errors → weights → blend → verification* — works entirely on its own. TimesFM, regime detection, the frontend and NCUM/NEPS ingestion are **extensions layered on top, never dependencies**. Build order follows the dependency chain (§13.1).

## 7.1 End-to-End Data Flow

```
                          FORECAST SOURCES
   ┌──────────┬──────────┬──────────┬──────────┬──────────┐
   │ NCUM-G/R │   GFS    │ ECMWF    │GraphCast │  NEPS /  │   ← Model Registry (§7.2)
   │  (GRIB2) │ (GRIB2)  │ IFS/AIFS │ (Zarr)   │  GEFS    │
   └────┬─────┴────┬─────┴────┬─────┴────┬─────┴────┬─────┘
        └──────────┴─────┬────┴──────────┴──────────┘
                          ▼
                   MODEL ADAPTERS            one per source; GRIB2 / Zarr / JSON in
                          ▼
                 CANONICAL FORECAST          one schema, §7.2
                          ▼
                QUALITY CONTROL GATE         schema / coord / time / unit / NaN / range
                          ▼
         ACCUMULATION NORMALISATION          ► 0300–0300 UTC window (D-01)  ◄ CRITICAL
                          ▼
                GRID / TIME ALIGNMENT        common 0.25° grid, common valid-time
                          │
        ┌─────────────────┴──────────────────┐
        │                                     │
  Historical Obs                        Live Forecast
  (IMD / ERA5, D-10)                          │
        │                                     │
        ▼                                     │
    VERIFICATION                              │
    RMSE · MAE · Bias · FSS · Brier           │
    · CRPS · Frequency bias · Intensity CDF   │
    · Relative Economic Value (§6.D)          │
    · stratified by terrain class (§6.K)      │
        │                                     │
        ▼                                     │
    ERROR DATABASE                            │
    per model × var × region × lead           │
        × season × regime                     │
        │  + sample counts (§6.B)             │
        ▼                                     │
  ┌─────────────────────────┐                 │
  │  CHANGE-POINT MONITOR   │  §6.H           │
  │  version drift → reset  │                 │
  └────────────┬────────────┘                 │
               ▼                              │
        WEIGHT ENGINE  ◄──────────────────────┘
        ├─ baseline ladder (§7.5)
        ├─ hierarchical shrinkage (§6.B)
        ├─ τ fitted (D-05)
        └─ forecaster override + audit log
               ▼
        ┌──────────────┐
        │   BLENDER    │
        │ · prob-matched rain (§6.A / D-11)
        │ · (u,v) wind vectors
        └──────┬───────┘
               ▼
    PHYSICAL VALIDATION (logged, §7.6)
               ▼
    SPATIAL COHERENCE PASS (§7.4)
               │
     ┌─────────┴──────────┐
     ▼                     ▼
deterministic          probabilistic
     │                     ▼
     │            POST-PROCESSING  quantile GBM / EMOS / BMA
     │                     ▼
     │              CALIBRATION  isotonic (§7.7)
     │                     │
     └──────────┬──────────┘
                ▼
          HAZARD ENGINE          rain / heatwave / wind — shared pipeline
                ▼
   ┌────────────┼────────────┬─────────────────┐
   ▼            ▼            ▼                 ▼
forecast     weights      hazards      disagreement index (§6.F)
   │            │            │                 │
   └────────────┴─────┬──────┴─────────────────┘
                       ▼
            PROVENANCE STAMPING (§7.11 / §6.L)
                       ▼
┌──────────────────────────────────┐  ┌──────────────────────────────────┐
│    DISASTER MANAGEMENT OUTPUT    │  │     OPERATIONAL DELIVERABLES     │
│ • District traffic light map     │  │ • CF-1.8 NetCDF grids            │
│   (G/Y/O/R, D-07 aggregation)    │  │ • GeoTIFF rasters                │
│ • Calibrated exceedance probs    │  │ • 2D model weight maps + LOMO    │
│ • Impact cards (WorldPop, D-15)  │  │ • CAP 1.2 XML, status=Exercise   │
│ • "Attention needed" overlay     │  │ • REST API                       │
│ • EXPERIMENTAL banner (D-13)     │  │ • 00Z/12Z scheduled pipeline     │
│                                  │  │ • Forecaster override interface  │
└──────────────────────────────────┘  └──────────────────────────────────┘
```

**The single most important structural property:** NCUM-G, NCUM-R, NEPS, GFS, ECMWF IFS/AIFS and GraphCast all enter through the same **Adapter → Canonical Forecast** step. Nothing downstream knows or cares whether a model arrived as GRIB2, Zarr or JSON. That is what makes "can this run on NCMRWF's HPC?" a **yes** with no second code path.

## 7.2 Canonical Forecast Layer & Model Registry

Sources disagree on resolution, longitude convention (0–360 vs −180–180), latitude ordering, timestamps, horizons, variable names and units. None of that is allowed to leak downstream.

```python
CanonicalForecast(
    model="gfs",
    model_version="gfs.v16.3.0",     # for change-point detection, §6.H
    init_time=...,
    valid_time=...,
    lead_hours=...,
    variable="tp",
    accumulation_hours=24,
    accumulation_window_start_utc="03:00",   # D-01
    units="mm",
    lat=..., lon=...,
    values=...,
)
```

**Adapters are registered, not hardcoded:**
```python
ModelSpec(name="gfs", source="nomads", adapter=GFSAdapter,
          resolution=0.25, variables=[...], lead_times=[...],
          native_format="grib2")

registry.register(GFSAdapter(...))
registry.register(ECMWFAdapter(...))
registry.register(GraphCastAdapter(...))
registry.register(NCUMAdapter(...))     # drop-in when NCMRWF GRIB2 available (G1)
registry.register(NEPSAdapter(...))     # ensemble member handling
```
This is what makes "declare NCUM/NEPS as drop-in sources" a **registry entry, not a rewrite.**

**Quality gate — before anything is blended:**
```
File → schema validation → coordinate validation → time validation
     → accumulation-window validation (D-01) → unit validation
     → missing-value check → physical range check → ACCEPT / REJECT + log
```
One bad GRIB2 file rejects **that file**, not the whole cycle, and never poisons the blend.

**Rainfall cannot be blended across sources unless accumulation windows match.** Unit and accumulation normalisation happens **before** weighting, never as a side effect of it:
```python
CanonicalRainfall(accumulation_hours=24, window_start_utc="03:00", units="mm")
```

## 7.3 Data Coverage

| Axis | Committed coverage |
|---|---|
| **Variables** | Rainfall (24 h accum), 2 m temperature (+ Tmax/Tmin), 10 m wind (u,v → speed) |
| **Domain** | All-India box: lat 5–38 °N, lon 65–100 °E, 0.25° |
| **Lead times** | Day 1 → Day 10, skill reported **per lead day** |
| **Years** | 2020–2023 primary; 2018–2023 stretch (D-02) |
| **Held-out seasons** | 2 (2022, 2023) — 3 with stretch range (D-03) |
| **Models** | GFS, ECMWF IFS HRES, GraphCast (core 3) + AIFS / NeuralGCM / GEFS as available; NCUM/NEPS declared drop-in |
| **Ground truth** | Per D-10 |

> ⚠️ **PRE-WORK GATE (see §13.2, item P-3).** Before Sprint 1, **inventory precipitation availability per model per year for the India box.** Precipitation is the weakest, most caveated variable for ERA5-trained AI models, and available fields differ by model and year in WB2. If GraphCast cannot supply usable rain, the rainfall blend collapses to 2 members — which is not a multi-model story.
> **Pre-approved contingency (announce it, don't hide it):** split the design — **rain** blended across NWP + ensemble members (GFS, IFS HRES, IFS ENS, GEFS); **temperature and wind** blended across NWP + AI (adds GraphCast, AIFS, NeuralGCM). That split is scientifically defensible and reflects a real property of AI models. Discovering it on Sep 29 is not defensible.
> **Also internalise:** an AI model trained on ERA5 gives you *ERA5's* rain — and ERA5 monsoon precipitation over India has large known biases. State this in the limitations slide.

## 7.4 Weight Engine

A single global weight set defeats the PS. So does jumping to the full 6-D table without proof. We build a **strategy ladder** and a **complexity ladder** and measure each rung against the one below.

```python
class WeightStrategy:
    def compute_weights(self, context) -> dict[str, float]: ...

ClimatologyStrategy      # reference floor (NEW, §6.C)
PersistenceStrategy      # reference floor (NEW, §6.C)
BestSingleStrategy       # the model to beat
EqualWeightStrategy      # w_i = 1/N — does ANY blending help?
InverseErrorStrategy     # w_i ∝ 1/historical_error_i
ContextAwareStrategy     # score[m,v,r,lead,season,regime] → softmax, with shrinkage
TimesFMStrategy          # ContextAware + predicted error drift (optional, §10.2)
OracleStrategy           # per-cell hindsight best — the ceiling (NEW, §6.C)
```

**Hierarchical shrinkage is part of `ContextAwareStrategy`, not an afterthought** (§6.B):
```python
w = shrink(w_cell_raw, w_parent, n_eff)     # λ = n_eff/(n_eff+k)
# fallback ladder: cell → district → homogeneous region → national
# below threshold: inherit parent AND record the reason in the explanation
```

**τ is fitted** on the validation fold per (variable, lead-band) and written to `results/tau.json` (D-05).

**Spatial coherence.** Cells choosing weights independently produce salt-and-pepper weight maps. We apply a smoothing/regularisation pass on the **raw** weight field (Gaussian/local to start) while deliberately **not** blurring across genuine boundaries — the Western Ghats rain-shadow line above all. Note: smoothing is cosmetic coherence; **shrinkage (§6.B) is the statistical fix.** Both, in that order.

**Masks in the weight stage:** elevation and land–sea masks participate in region definition, so coastal and leeward cells are not pooled with cells they have no physical business sharing weights with (blind spot B3).

**Forecaster override** writes to an audit log: user, timestamp, scope, reason, pre-override weights, post-override weights.

## 7.5 Baseline Ladder & Leakage Prevention

### The ladder table — generated by the pipeline, never assembled by hand

| Rung | Strategy | RMSE | MAE | FSS@50 km | Freq. bias | Rel. Econ. Value | vs. best single | 95 % CI |
|---|---|---|---|---|---|---|---|---|
| Floor | Climatology | `?.??` | `?.??` | `?.??` | `?.??` | `?.??` | — | `[?, ?]` |
| Floor | Persistence | `?.??` | `?.??` | `?.??` | `?.??` | `?.??` | — | `[?, ?]` |
| Single | GFS | `?.??` | `?.??` | `?.??` | `?.??` | `?.??` | baseline | `[?, ?]` |
| Single | ECMWF IFS | `?.??` | `?.??` | `?.??` | `?.??` | `?.??` | baseline | `[?, ?]` |
| Single | GraphCast | `?.??` | `?.??` | `?.??` | `?.??` | `?.??` | baseline | `[?, ?]` |
| Blend | Equal weight | `?.??` | `?.??` | `?.??` | `?.??` | `?.??` | `?.?%` | `[?, ?]` |
| Blend | Inverse error | `?.??` | `?.??` | `?.??` | `?.??` | `?.??` | `?.?%` | `[?, ?]` |
| Blend | Context (region×lead) | `?.??` | `?.??` | `?.??` | `?.??` | `?.??` | `?.?%` | `[?, ?]` |
| Blend | + season | `?.??` | `?.??` | `?.??` | `?.??` | `?.??` | `?.?%` | `[?, ?]` |
| Blend | + regime | `?.??` | `?.??` | `?.??` | `?.??` | `?.??` | `?.?%` | `[?, ?]` |
| Blend | + probability-matched (§6.A) | `?.??` | `?.??` | `?.??` | `?.??` | `?.??` | `?.?%` | `[?, ?]` |
| Blend | + TimesFM (optional) | `?.??` | `?.??` | `?.??` | `?.??` | `?.??` | `?.?%` | `[?, ?]` |
| **Ceiling** | **Hindsight oracle** | `?.??` | `?.??` | `?.??` | `?.??` | `?.??` | `?.?%` | `[?, ?]` |

Derived headline: **`% of achievable gain captured = (best_single − ours) / (best_single − oracle)`.**

> **Every `?.??` above is deliberate. No number is quoted to a judge until it is measured (G12). A null result on any rung is a reportable finding, not a failure.**

### Training / inference separation
```
OFFLINE TRAINING                        OPERATIONAL INFERENCE
Historical forecasts + Obs              New forecasts
        ↓                                      ↓
Accumulation normalisation (D-01)      Quality gate + normalisation
        ↓                                      ↓
Alignment                              Grid alignment
        ↓                                      ↓
Error calculation                      Load trained weight artifact
        ↓                                      ↓
Feature generation                     Predict weights (+ override)
        ↓                                      ↓
Weight model + τ + shrinkage params    Blend → hazards → provenance → output
        ↓
Saved artifact ───────────────────────────────┘
```
Two explicit entry points. **Not** one script that recomputes everything on every cycle.

### Leakage prevention is structural, not conventional
```
Train 2020 → 2021    Test 2022
Train 2020 → 2022    Test 2023
```
The weighting engine only ever sees observations available **before** the forecast being evaluated. Enforced in `experiments/runner.py`, not left to whoever runs the experiment. A 2022 forecast is never weighted using 2022 observations.

## 7.6 Blending & Physical Validation

**Shared pipeline, four variables, not four systems:**
```
                 ┌── Rain  → 24 h accum (D-01) → probability-matched blend (§6.A)
Common Forecast ─┼── Temp  → weighted mean → Tmax/Tmin extremes
Pipeline         └── Wind  → blend (u,v) vectors → derive speed
                       ↓
                 Hazard Engine
```

**`PhysicalValidator` — a logging validator, never a silent patch:**
```python
class PhysicalValidator:
    def validate_temperature(...)   # plausible range, Tmax ≥ Tmin
    def validate_precipitation(...) # clip < 0; no unphysical maxima
    def validate_wind(...)          # blend (u,v), derive speed — never a blended scalar
    def validate_humidity(...)      # clamp Td ≤ T
```
```json
{"field":"precipitation","cells_corrected":31,"operation":"clip_negative","max_correction":0.12}
```
Every correction is counted and logged, and the counts appear in the results appendix. A validator that silently fixes things is indistinguishable from a bug.

## 7.7 Extreme Hazard Probability & Calibration

Thresholding a blended mean smooths out exactly the peaks that matter. The extreme path is a **real predictive distribution**:
```
Ensemble members / multi-model spread
          ↓
Post-processing   quantile GBM / EMOS / BMA
          ↓
Predictive distribution
          ↓
P(X > threshold)     rain: 64.5 / 115.6 / 204.5 mm
                     heatwave: IMD criteria (40 °C plains, 30 °C hills, dep. ≥ 4.5 °C)
                     wind: IMD gale criteria (scoped per D-06)
          ↓
CALIBRATION   isotonic first; Platt / Beta / EMOS as compared alternatives
          ↓
IMD hazard category   Green / Yellow / Orange / Red
          ↓
Decision value (§6.D) + reliability + Brier + ROC-AUC
```
**One robust calibrator implemented properly first**, with calibrated-vs-uncalibrated compared — not four calibrators half-tested.

**Alerting rule:** calibrated probability thresholds, **never** N-of-N model consensus (§4.4).

## 7.8 Verification Suite

| Metric | Applies to | Notes |
|---|---|---|
| RMSE, MAE, Bias | all | **Never alone for rain** (D-12) |
| **FSS** at 5/25/50/100/150 km | rain | Skill criterion **`FSS_useful = 0.5 + f₀/2`**, not "> 0.5" |
| **Frequency bias** | rain | Detects smoothing |
| **Intensity CDF comparison** | rain | Shows §6.A working |
| Brier score, Brier skill score | probabilistic | vs. climatology |
| Reliability diagram | probabilistic | with sharpness histogram |
| ROC / AUC | probabilistic | discrimination |
| CRPS | probabilistic | distributional |
| **Relative Economic Value** | probabilistic | §6.D — the decision-maker's metric |
| Block-bootstrap 95 % CIs | **all** | on differences, not just levels |
| **Terrain-stratified cuts** | all | §6.K — Ghats windward / leeward / foothills / plains / coastal |
| **Per-season, per-lead cuts** | all | closes G8, G9 |
| **Regime-detector agreement** | regimes | §6.G |

## 7.9 Missing Models & Verified Graceful Degradation

Missing models are a **first-class state**, not an error path:
```python
available = [m for m in models if m.is_available(cutoff)]
weights   = weights.loc[available]
weights  /= weights.sum()
calibrator = calibrators[availability_pattern(available)]   # ← recalibrate, §7.9
```
```json
{"available_models":["gfs","ecmwf"],"missing_models":["graphcast"],
 "renormalized":true,"calibrator":"pattern_gfs+ecmwf"}
```

**Why renormalisation alone is not enough:** dropping a member changes the blend's **bias and spread**, so calibrated exceedance probabilities become miscalibrated — precisely in the degraded conditions where alerts matter most. Therefore:
1. **Recalibrate per availability pattern** (pre-fit calibrators for the common patterns).
2. **Verify the degraded configurations** — publish a blend-minus-one skill table.
3. Tag metadata and notify the duty forecaster.

> **Untested degradation is a claim, not a feature.** The blend-minus-one table is what makes it a feature.

## 7.10 Experiment Framework

Parameters live in config, not buried in Python, so several people (or agents) can run comparable experiments.
```yaml
experiment:
  variable: precipitation
  lead_hours: [24, 48, 72, 120, 168, 240]
  accumulation_window_start_utc: "03:00"      # D-01
models: [gfs, ecmwf, graphcast]
weighting:
  strategy: context
  history_days: 30
  region: true
  season: true
  regime: true
  shrinkage: {enabled: true, k: 20, min_samples: 15}
  tau: fitted
blending:
  method: probability_matched                  # D-11
verification:
  metrics: [rmse, mae, bias, fss, freq_bias, intensity_cdf,
            brier, reliability, roc, crps, rev]
  fss_scales_km: [5, 25, 50, 100, 150]
  stratify_by: [terrain_class, season, lead_day]
  bootstrap: {method: block, n: 1000, ci: 0.95}
folds: rolling_origin                          # D-03
```
```bash
python experiments/run.py --strategy climatology
python experiments/run.py --strategy persistence
python experiments/run.py --strategy best_single
python experiments/run.py --strategy equal
python experiments/run.py --strategy inverse_error
python experiments/run.py --strategy context
python experiments/run.py --strategy context --no-regime      # ablation
python experiments/run.py --strategy context_timesfm
python experiments/run.py --strategy oracle
make reproduce                                 # §6.J — regenerates every deck number
```
Each run writes `results/<strategy>/` with all metrics, CIs and plots. **The ladder table in §7.5 is generated, not typed.**

## 7.11 Provenance, Output Formats & Legal Status (§6.L / D-13)

Every output file — NetCDF, GeoTIFF, CAP, JSON — carries:
```json
{
  "system": "SIH26081 Hybrid AI-NWP Blend",
  "status": "EXERCISE - NOT AN OFFICIAL IMD WARNING",
  "generated_utc": "...",
  "git_commit": "...",
  "models_used": ["gfs","ecmwf","graphcast"],
  "availability_pattern": "full",
  "weight_strategy": "context+shrinkage",
  "tau": {"precipitation": {"d1-d3": 0.42}},
  "blend_method": "probability_matched",
  "ground_truth": "IMD 0.25 gridded rainfall (Pai et al.)",
  "accumulation_window_utc": "03:00-03:00",
  "district_aggregation": "area_weighted_p90",
  "forecaster_overrides": []
}
```
- **CF-1.8 NetCDF** — slots into NCMRWF visualisation/dissemination workflows.
- **GeoTIFF** — GIS consumers.
- **CAP 1.2 XML** with `<status>Exercise</status>`.
- **REST API** (FastAPI) for downstream consumers.
- **UI banner** — persistent, non-dismissible: *"EXPERIMENTAL SYSTEM — NOT AN OFFICIAL IMD WARNING."*

---

# 8. Repository Structure

```
sih26081-blend/
├── DECISIONS.md                  # §1, append-only with dates
├── environment.yml               # D-09, committed, locked
├── Makefile                      # `make reproduce` → §6.J
├── README.md                     # setup, architecture, ladder table, limitations
│
├── ingestion/                    base.py, gfs.py, ecmwf.py, graphcast.py,
│                                 ncum.py, neps.py, openmeteo.py, registry.py
├── canonical/                    forecast.py, variables.py, accumulation.py,
│                                 units.py, grid.py, quality_gate.py
├── verification/                 deterministic.py, fss.py, probabilistic.py,
│                                 economic_value.py, bootstrap.py, stratify.py
├── weighting/                    base.py, climatology.py, persistence.py,
│                                 equal.py, inverse_error.py, context.py,
│                                 shrinkage.py, oracle.py, timesfm.py,
│                                 override.py, tau_fit.py
├── blending/                     deterministic.py, probability_matched.py,
│                                 probabilistic.py, physical.py, spatial.py
├── regimes/                      base.py, detector.py, verify_detector.py
├── hazards/                      rainfall.py, heatwave.py, wind.py, disagreement.py
├── calibration/                  base.py, isotonic.py, patterns.py
├── monitoring/                   change_point.py            # §6.H
├── experiments/                  configs/, runner.py, folds.py
├── evaluation/                   reports.py, plots.py, ladder.py, where_we_lose.py
├── outputs/                      netcdf.py, geotiff.py, cap.py, provenance.py
├── api/                          main.py, routes/
├── frontend/                     Vite + Leaflet + Chart.js
├── data/                         raw/ interim/ processed/ static/   (gitignored)
├── results/                      <strategy>/ …                      (gitignored)
└── tests/                        test_accumulation.py, test_quality_gate.py,
                                  test_fss.py, test_leakage.py, test_shrinkage.py
```

Each top-level module maps to one box in §7.1. **Adding NCUM/NEPS is a new file in `ingestion/` plus a registry entry — it touches nothing in `weighting/`, `blending/` or downstream.** That is the answer to G1.

**Minimum test set (not optional — these four guard the four worst failure modes):**
| Test | Guards against |
|---|---|
| `test_accumulation.py` | D-01 window drift — the silent killer |
| `test_leakage.py` | asserts no test-fold observation reaches the weight fit |
| `test_quality_gate.py` | a deliberately corrupted GRIB2 is rejected, clean input passes |
| `test_fss.py` | FSS against a hand-computed toy case, incl. `f₀` reference |

---

# 9. Tech Stack

> **Every "X or Y" below is resolved in `TECH_APPROACH_AND_TEAMS.md` §1 (D-18 → D-30).** That document is binding for tooling; this section is the survey it was chosen from.

## 9.1 Backend / Core (Python)

| Component | Library | Purpose |
|---|---|---|
| Ingestion | `xarray`, `cfgrib`, `zarr`, `netCDF4` | GRIB2 / NetCDF / Zarr behind per-model adapters (§7.2). **D-09: environment resolved tonight.** |
| Canonical schema | `pydantic` (or dataclasses + xarray accessors) | Enforce `CanonicalForecast` / `CanonicalRainfall` + quality gate |
| Accumulation | `pandas`, `xarray` resample | **D-01 window normalisation** — the single highest-risk module |
| Geospatial | `rioxarray`, `geopandas`, `shapely`, `regionmask` | District polygons, land-sea & elevation masks, zonal stats (D-07), GeoTIFF |
| Elevation | SRTM / ETOPO via `rioxarray` | Terrain classes for §6.K stratification |
| Population | **WorldPop / GPW v4 raster** (D-15) | Impact estimates — sourced, not invented |
| Weighting | `scikit-learn`, `lightgbm`/`xgboost` | `WeightStrategy` implementations; quantile regression for extremes |
| Shrinkage | `numpy`, `scipy` | §6.B hierarchical pooling, effective sample size |
| Probability matching | `numpy` percentile mapping | §6.A — ~30 lines |
| Calibration | `scikit-learn` isotonic; custom EMOS/Beta | `ProbabilityCalibrator`, per availability pattern (§7.9) |
| Verification | `xskillscore`, `properscoring`, custom FSS | RMSE/MAE/FSS/CRPS/Brier/reliability; correct `FSS_useful` |
| Decision value | custom (contingency tables) | **§6.D Relative Economic Value** |
| Change-point | `ruptures` (or hand-rolled CUSUM) | **§6.H version-drift detection** |
| Inference | `scipy`, `numpy` | Block-bootstrap CIs |
| Error forecasting *(optional)* | `google/timesfm` (HuggingFace) | `TimesFMStrategy` — behind the interface, ablated (§10.2) |
| Experiment config | `pyyaml` (or `hydra`) | §7.10 — reproducible ablations |
| Pipeline | `prefect` or cron + Docker | 00Z/12Z cycles; separate train / infer entry points |
| API | `FastAPI` | REST for dashboards, CAP feeds, downstream systems |
| Output formats | `netCDF4`, `rasterio`, `lxml` | CF-1.8 NetCDF, GeoTIFF, CAP 1.2 |
| Testing | `pytest` | The four guard tests in §8 |

## 9.2 Frontend

| Component | Library | Purpose |
|---|---|---|
| Framework | Vite + Vanilla JS (or React) | Fast SPA |
| Mapping | Leaflet (+ Leaflet.heat) or Mapbox GL | District boundaries, raster overlays, animation |
| Charts | Chart.js or Plotly.js | Spaghetti, confidence bands, reliability diagrams, REV curves, ladder table |
| Styling | Vanilla CSS, **one dark professional theme** | IMD/NCMRWF-appropriate. No mascots, no pastel themes. |
| Animation | CSS transitions + `requestAnimationFrame` | Timeline for the weather movie (P3 only) |

## 9.3 Data Sources

| Source | Provides | Access |
|---|---|---|
| **WeatherBench2** | Archived IFS HRES, GFS, GraphCast, NeuralGCM, ERA5 (2018–2023) | Zarr on GCS, `xarray.open_zarr()` |
| **IMD Pune** | 0.25° gridded daily rainfall (Pai et al.); 1° Tmax/Tmin | Dataset request / cached `.nc` |
| **ERA5 (CDS)** | Reanalysis fallback truth; 10 m wind (D-06) | `cdsapi` / WB2 |
| **NOMADS (NOAA)** | Live GFS **GRIB2** — proves the GRIB2 path | HTTP |
| **Open-Meteo** | Live GFS/ECMWF/ICON/AIFS for live-mode demo | REST JSON |
| **datameet / SoI** | India district polygons (730+) | GitHub GeoJSON |
| **WorldPop / GPW v4** | Gridded population (D-15) | HTTP raster |
| **SRTM / ETOPO** | Elevation for terrain classes (§6.K) | HTTP raster |
| **NCMRWF (declared)** | NCUM-G, NCUM-R, NEPS GRIB2 | Drop-in via same adapter |

---

# 10. Google AI Models — Honest Integration Strategy

## 10.1 Roles

| Model | Role | Status | How we use it |
|---|---|---|---|
| **GraphCast** (DeepMind, *Science* 2023) | AI model **in the blending pool** | ✅ Open | 0.25° 10-day forecasts via WB2 Zarr, competing against GFS/IFS/NCUM. **Precip availability gated by P-3 (§7.3).** |
| **NeuralGCM** (Google Research, *Nature* 2024) | Hybrid physics-AI model in pool | ✅ Open | Second AI model for pool diversity (optional) |
| **TimesFM** (Google Research) | **Optional** meta-forecaster for error drift | ✅ Open | `TimesFMStrategy` behind the `WeightStrategy` interface — **ablated, never assumed** |
| **WeatherBench 2** | **Primary data pipeline** | ✅ Open | Archived forecasts + ERA5 for training and verification |
| **MetNet-3** (DeepMind) | Related work only | ❌ Proprietary | Cited, not used |

## 10.2 TimesFM is one strategy — explicitly **not** the critical path

Most teams weight models with a lagging moving average of past error. Weather changes abruptly; when an active monsoon spell breaks, yesterday's errors don't predict tomorrow's. TimesFM is our **hypothesis** for beating a lagging average. It is a hypothesis we test, not a dependency.

```
                    ┌── historical skill weighting (+ shrinkage) ──┐
forecast models ────┤                                               ├──→ weights
                    └── optional TimesFM error-drift prediction ────┘
```

**Mechanism when enabled:**
1. Per-model error forms a 1-D series at each grid zone: `e_GFS(t)`, `e_ECMWF(t)`, `e_GraphCast(t)`
2. Feed the trailing 30-day series to TimesFM zero-shot
3. TimesFM predicts each model's expected error for Days 1–10
4. `W_i(t+k) = exp(−ê_i(t+k)/τ) / Σ_j exp(−ê_j(t+k)/τ)`  — with τ from D-05

**Why decoupled:** the earlier draft put TimesFM directly in the critical path, meaning the entire weighting engine breaks if TimesFM underperforms, runs slow, or the HuggingFace pull fails on demo day.

**Priority reality check.** TimesFM is a good Q&A answer and the **lowest-value hour in the plan**. Innovations **6.A + 6.D** cost roughly the same time and are worth far more to this panel. TimesFM is **P3 / cut-first** (§13.6).

**What we report:** the ladder with and without it, side by side. If it does not beat `ContextAwareStrategy`, that is a **reportable finding** (G12, §14).

---

# 11. User-Facing Features

> Every screen carries the **persistent EXPERIMENTAL banner** (D-13) and shows its **provenance footer** (§7.11). Every number on every screen comes from `results/` — never a literal in the JS.

### Priority matrix

| Priority | Feature | Effort | Impact | Why |
|---|---|---|---|---|
| **P0** | 🚦 District Traffic Light Board | Med | 🔥🔥🔥🔥🔥 | The disaster-management deliverable |
| **P0** | 🎯 Model Weight Map + **LOMO explanations** (§6.E) | Med | 🔥🔥🔥🔥🔥 | *Is* Expected Outcome 2 |
| **P0** | 📊 **Baseline Ladder table** (floor→ceiling, §6.C) | Low | 🔥🔥🔥🔥🔥 | The scientific core |
| **P1** | ⚠️ **"Attention Needed" disagreement overlay** (§6.F) | Low | 🔥🔥🔥🔥 | Novel; forecaster-facing |
| **P1** | 📈 **Decision-value curve** (§6.D) | Low | 🔥🔥🔥🔥🔥 | Answers "so what?" |
| **P1** | 📊 Spaghetti + confidence gauge | Low-Med | 🔥🔥🔥🔥 | Non-technical judges |
| **P1** | 📋 Forecaster Decision Card | Low | 🔥🔥🔥🔥 | NCMRWF recognises the format |
| **P1** | 🔍 **"Where We Lose" map** (§6.I) | Low | 🔥🔥🔥🔥🔥 | Credibility centrepiece |
| **P2** | 🕰️ July 2023 case replay (D-08) | Med | 🔥🔥🔥🔥🔥 | Out-of-sample, legitimate |
| **P2** | 📉 **Version-drift change-point plot** (§6.H) | Low | 🔥🔥🔥 | Demonstrates G7 |
| **P2** | 🏅 Skill leaderboard | Low | 🔥🔥🔥 | Visual, quick |
| **P3** | 🎬 Weather movie animation | High | 🔥🔥🔥🔥🔥 | **Cut first** |

### Feature detail

**🚦 District Traffic Light Board.** All-India district map, Green/Yellow/Orange/Red per IMD's 4-tier system, driven by **calibrated probabilities** (never N-of-N consensus). Aggregation per **D-07**, with the rule printed on the map and toggleable. Click a district:
> 🔴 **Ratnagiri** — `??`% probability of > 115.6 mm in 24 h (IMD Very Heavy)
> Population in affected cells: `??` (WorldPop 2020, D-15)
> Weights: ECMWF `?.??` · GFS `?.??` · GraphCast `?.??`
> Removing ECMWF here raises RMSE `??`% (§6.E)
> Disagreement index: `?.??` × normal (§6.F)
> *EXERCISE — not an official IMD warning*

**🎯 Model Weight Map.** Gridded choropleth of dominant model / weight per model. Lead-time slider D+1→D+10; variable and season selectors. Hover gives the **computed** LOMO attribution and, where shrinkage fired, the honest reason ("insufficient local history: using Konkan regional weights, n=17"). Forecaster override control with audit log.

**📊 Baseline Ladder panel.** Renders `results/ladder.json` directly — floor, singles, blends, ceiling, CIs, and the derived "% of achievable gain captured."

**⚠️ Attention-Needed overlay.** Cells where `D = spread / climatological_spread` is high. The one screen a duty forecaster would open daily.

**📈 Decision-value panel.** Relative Economic Value vs. cost:loss ratio, blend vs. best single model, with the responder interpretation spelled out in words.

**📊 Spaghetti panel.** All members as thin lines, blend bold, shaded band. Agreement gauge 🟢/🟡/🔴 driven by §6.F, not raw spread.

**📋 Forecaster Decision Card** (printable, populated from real data only):
```
┌─────────────────────────────────────────────────────┐
│  DAILY FORECAST BRIEF — MAHARASHTRA        EXERCISE │
│  Issued: ?? | Valid: D+1 | Cycle: 00Z               │
├─────────────────────────────────────────────────────┤
│  Rain:  ?? mm  (IMD class: ??)  over Konkan-Goa     │
│  Temp:  Tmax ?? °C (departure ?? °C)                │
│  Wind:  ?? km/h from (u,v) blend                    │
│  Alert: ?? — ?? districts                           │
│  Calibrated P(>115.6 mm): ??%                       │
│  Disagreement vs. normal: ?.??×                     │
│  Top model here: ?? (weight ?.??)                   │
│  Models used: ?? | Missing: ?? | Renormalised: ??   │
│  NOT AN OFFICIAL IMD WARNING · commit ???????        │
└─────────────────────────────────────────────────────┘
```

**🔍 "Where We Lose" map.** Regions/leads/regimes where the blend underperforms the best single model, with reason and override path.

**🕰️ Case replay (July 2023, out-of-sample).** What each model predicted at D+1/D+3/D+5 → what happened → what our blend said → when the calibrated probability crossed Orange/Red. **Stated explicitly as outside the training folds.**

### Deliberately NOT built (time traps)
| Temptation | Why skip | Instead |
|---|---|---|
| LLM chatbot | Gimmick; NCMRWF scientists won't use it; 4–8 h | FSS + decision value |
| Login / auth | Nobody logs in during a demo | Hardcoded "Forecaster Mode" toggle |
| Mobile responsive | Judges view on a projector | Optimise 1920×1080 |
| Multiple themes | One dark theme suffices | Map interactivity |
| Mascots / gamified onboarding | Tone mismatch for disaster management | 3-step guided tour banner |
| 4 calibrators | Half-tested each | One isotonic, done properly |

---

# 12. Gap-to-Outcome Scorecard

| Expected outcome | Best existing coverage | Gap that remained | **Our answer** |
|---|---|---|---|
| **Dynamically blended forecast** | rain over 29 districts; temperature all-India | All four targets, all-India, D1–10, NCMRWF models | Gridded blend, 3 variables, D1–10, GRIB2 adapter + registry (G1, G2, G9), **probability-matched rain** (§6.A) |
| **Model weight maps** | temperature at 1.5° | Gridded, per var/lead/season/regime, explained, overridable | Shrinkage-stabilised gridded weights (§6.B) + **computed LOMO explanations** (§6.E) + override with audit log (G11) |
| **Improved forecast skill** | three partial studies | Multi-season test, FSS, CIs, floor & ceiling | **Full ladder: climatology floor → oracle ceiling** (§6.C), FSS with correct criterion, block-bootstrap CIs, leakage-free rolling origin, **terrain-stratified** (§6.K), **"Where We Lose"** (§6.I) |
| **Extreme weather guidance** | Brier at one threshold; percentile flags | Calibrated probabilities, heatwave/wind criteria, reliability | Predictive distribution → isotonic → IMD G/Y/O/R, Brier + reliability + ROC + **Relative Economic Value** (§6.D), wind scoped honestly (D-06) |
| **Operational workflow** | one daily cycle + CAP | GRIB in, NetCDF/GeoTIFF out, scheduler, drift handling | Docker + scheduler, CF-1.8 NetCDF + GeoTIFF + CAP (`Exercise`), **verified** graceful degradation (§7.9), **demonstrated version-drift detection** (§6.H), full provenance (§6.L) |

---

# 13. Implementation Plan

## 13.1 Governing principle

Build order follows the **dependency chain, not feature attractiveness**:
```
environment → data model → adapters → accumulation normalisation → alignment
   → verification → baseline ladder (floor + singles + equal + inverse)
   → adaptive weighting + shrinkage → probability matching → extremes + calibration
   → decision value → oracle ceiling → regimes → frontend → TimesFM → polish
```
**Each stage starts only when the previous one produces real, verified output.** No frontend against fabricated numbers. No adaptive weighting before baselines exist to beat. No extreme probabilities before the deterministic blend is verified.

## 13.2 Pre-Work — TONIGHT (26 Sep), before any feature code

These four items are the difference between a working Sprint 1 and a lost day.

| # | Task | Why it is tonight | Done when |
|---|---|---|---|
| **P-1** | `git init` ✅ done · write `.gitignore` ✅ done · create `DECISIONS.md` from §1 · push to a shared remote | Four days, parallel tracks, one shared result set (D-17) | Every teammate can clone |
| **P-2** | **Resolve the environment (D-09).** `conda env create -f environment.yml`; verify `import cfgrib` **and** open a real GRIB2 file. Docker fallback if it fights. | `cfgrib`/`eccodes` on native Windows is a known trap, and it sits on our strongest claim. Losing Sprint 1 morning to an eccodes binary is a realistic failure. | `python -c "import cfgrib, xarray; xarray.open_dataset('test.grib2', engine='cfgrib')"` succeeds, and `environment.yml` is committed |
| **P-3** | **Start the WB2 download — and in the same session print the precipitation inventory per model per year for the India box.** | **This single output can reshape the project scope** (§7.3). Everything else waits on it. | A printed table: model × year × precip variable present/absent + India-subset stats. Contingency in §7.3 triggered or not. |
| **P-4** | **Write `DECISIONS.md`** with §1 verbatim, **fill in D-16 (team allocation)** | The sprint plan's feasibility depends on a number that was never stated | Committed, with names |

### Downloads to launch in parallel tonight

| # | Source | What | Est. size | Method | ☐ |
|---|---|---|---|---|---|
| D1 | WeatherBench2 | IFS HRES + GFS + GraphCast, India box (lat 5–38 N, lon 65–100 E), **2020–2023** (D-02) | ~5–15 GB/model | `xr.open_zarr('gs://weatherbench2/...').sel(latitude=slice(38,5), longitude=slice(65,100))` | ☐ |
| D2 | WeatherBench2 | ERA5 same region/years — fallback truth + wind (D-06, D-10) | ~3–5 GB | same | ☐ |
| D3 | IMD Pune | 0.25° daily gridded rainfall, 2020–2023 | ~200 MB | request / cached `.nc` | ☐ |
| D4 | IMD Pune | 1° Tmax/Tmin daily, 2020–2023 | ~100 MB | request / cached `.nc` | ☐ |
| D5 | datameet / SoI | District GeoJSON (730+) | ~15 MB | GitHub | ☐ |
| D6 | **WorldPop / GPW v4** | India gridded population (D-15) | ~100 MB | HTTP | ☐ |
| D7 | **SRTM / ETOPO** | Elevation for terrain classes (§6.K) | ~200 MB | HTTP | ☐ |
| D8 | NOMADS | One live GFS **GRIB2** file — proves the GRIB2 path for judges | ~300 MB | HTTP | ☐ |
| D9 | Open-Meteo | Live GFS/ECMWF/ICON/AIFS for ~50 cities (live-mode demo) | API | REST, cached JSON | ☐ |
| D10 | *(stretch, D-02)* | Extend D1/D2 back to 2018 → 6 seasons, 3 held out | +GBs | same | ☐ |

> **Risk (D-10):** IMD gridded data may need an institutional request taking days. **Mitigation:** ERA5 as prototype truth, with the **explicit caveat that ERA5 monsoon precipitation over India has large known biases** — acceptable for temperature and wind, a stated material limitation for rainfall. IMD is named as the production target. Honest, and still scientifically usable.

## 13.3 Sprints

### SPRINT 1 — Foundation (27 Sep)
**Goal:** data flows end to end, raw source → blended grid. No ML, no extremes. Prove the pipeline.

| # | Task | Module | Done when |
|---|---|---|---|
| S1.1 | `CanonicalForecast` + `CanonicalRainfall` schema | `canonical/forecast.py` | Represents GFS, IFS, GraphCast fields with one coordinate convention |
| S1.2 | **Accumulation normaliser (D-01)** — *highest-risk module in the project* | `canonical/accumulation.py` | Any source → 0300–0300 UTC 24 h accumulation; `test_accumulation.py` green |
| S1.3 | GFS adapter (incl. real GRIB2 path) | `ingestion/gfs.py` | `adapter.load(init, lead, var)` returns canonical objects for rain + T2m; reads the D8 GRIB2 file |
| S1.4 | ECMWF adapter | `ingestion/ecmwf.py` | Same interface, same variables |
| S1.5 | GraphCast adapter | `ingestion/graphcast.py` | Same interface; variables per P-3 outcome |
| S1.6 | Model registry | `ingestion/registry.py` | Adding a model = one `register()` call |
| S1.7 | Quality gate | `canonical/quality_gate.py` | Rejects a deliberately corrupted input, passes clean; `test_quality_gate.py` green |
| S1.8 | Grid/time alignment | `canonical/grid.py` | All models on common 0.25° grid and valid times |
| S1.9 | `EqualWeightStrategy` | `weighting/equal.py` | `blend = mean(members)` — trivial, but proves the chain |
| S1.10 | Smoke test | `experiments/` | `python experiments/run.py --strategy equal --date 2022-06-15` writes a plottable `.nc` |

**🚩 CHECKPOINT 1:** a blended rainfall grid over India you can `matplotlib` — with the accumulation window verifiably correct. **If this fails, nothing downstream works. Do not proceed past it.**

### SPRINT 2 — Verification & the Ladder (28 Sep)
**Goal:** the first **real, measured numbers**. This is what separates us from every synthetic entry.

| # | Task | Module | Done when |
|---|---|---|---|
| S2.1 | Ground truth loader (D-10) | `verification/` | IMD/ERA5 aligned to forecast grid **on the D-01 window** |
| S2.2 | **Sample-count histogram** per (region × lead × season × regime) | `evaluation/` | Printed. **Decides which ladder rungs are estimable.** Do this before S2.6. |
| S2.3 | Deterministic verification | `verification/deterministic.py` | RMSE/MAE/Bias/frequency bias, D1–10, per model |
| S2.4 | **FSS with correct criterion** | `verification/fss.py` | FSS at 5/25/50/100/150 km per IMD threshold; `FSS_useful = 0.5 + f₀/2`; `test_fss.py` green |
| S2.5 | **Climatology + persistence floors** (§6.C) | `weighting/climatology.py`, `persistence.py` | Both on the ladder |
| S2.6 | `InverseErrorStrategy` | `weighting/inverse_error.py` | Weights from trailing-30-day RMSE per model × var × lead |
| S2.7 | **Rolling-origin folds + leakage test** (D-03) | `experiments/folds.py` | `test_leakage.py` asserts no test-fold obs reaches the weight fit |
| S2.8 | Block-bootstrap CIs | `verification/bootstrap.py` | 95 % CIs **on differences** |
| S2.9 | **Ladder v1 generated** | `evaluation/ladder.py` | `results/ladder.json` + rendered table: floors → singles → equal → inverse |
| S2.10 | **Intensity-CDF comparison** (D-12) | `evaluation/plots.py` | CDF plot, members vs. blend |

**🚩 CHECKPOINT 2:** §7.5's table with **real numbers** for the first rungs, with CIs. **This table is the scientific core of the presentation.** Even if inverse-error loses to equal weighting, that is a reportable finding.

### SPRINT 3 — Intelligence Layer + Frontend (29 Sep) — two parallel tracks

**Track A — Backend**

| # | Task | Module | Done when |
|---|---|---|---|
| S3.1 | `ContextAwareStrategy` (region × lead × season) | `weighting/context.py` | Different weights for monsoon-Kerala vs. winter-Rajasthan |
| S3.2 | **Hierarchical shrinkage + min-sample fallback** (§6.B) | `weighting/shrinkage.py` | Low-sample cells inherit parent weights **and record why** |
| S3.3 | **τ fitting** (D-05) | `weighting/tau_fit.py` | `results/tau.json` per variable × lead-band |
| S3.4 | **Probability-matched blending** (§6.A / D-11) | `blending/probability_matched.py` | Blended rain CDF matches weighted-member CDF; FSS + freq-bias improve or the result is reported |
| S3.5 | Physical validator | `blending/physical.py` | Clips rain < 0, clamps Td ≤ T, blends (u,v); **every correction logged** |
| S3.6 | Extreme probability + isotonic calibration | `hazards/rainfall.py`, `calibration/isotonic.py` | Calibrated `P(>64.5)`, `P(>115.6)`, `P(>204.5)`; reliability diagram |
| S3.7 | **Relative Economic Value** (§6.D) | `verification/economic_value.py` | REV curve, blend vs. best single |
| S3.8 | **Oracle ceiling** (§6.C) | `weighting/oracle.py` | Ladder top rung + "% of achievable gain captured" |
| S3.9 | Heatwave module | `hazards/heatwave.py` | Cells meeting IMD criteria flagged |
| S3.10 | **Disagreement index** (§6.F) | `hazards/disagreement.py` | `D = spread / climatological_spread` gridded field |
| S3.11 | **LOMO weight explanations** (§6.E) | `evaluation/reports.py` | Per-cell "removing X raises RMSE Y%" |
| S3.12 | Regime detector, **forecast-derived** (D-04) | `regimes/detector.py` | Heavy-rain / Active-Break flag from forecast fields only |
| S3.13 | **Regime-detector verification** (§6.G) | `regimes/verify_detector.py` | Agreement % vs. obs-derived regimes, per lead day |
| S3.14 | Regime ablation | `experiments/` | Ladder extended: context with vs. without regime. **Honest result.** |
| S3.15 | **Terrain-stratified cuts** (§6.K) | `verification/stratify.py` | Skill by Ghats windward/leeward/foothills/plains/coastal |
| S3.16 | **Blend-minus-one degradation table** (§7.9) | `verification/` | Skill for each availability pattern + per-pattern calibrators |

**Track B — Frontend (parallel, reads `results/*.json` — no live API needed)**

| # | Task | Done when |
|---|---|---|
| S3.17 | Vite + Leaflet + Chart.js scaffold, dark theme, **EXPERIMENTAL banner (D-13)** | `npm run dev` serves the India base map with the banner |
| S3.18 | District Traffic Light Board (D-07 aggregation, toggle shown) | Districts coloured from S3.6 probabilities; popup per §11 |
| S3.19 | Model Weight Map + lead slider + **LOMO hover** | Weights from S3.2/S3.11, D+1→D+10 |
| S3.20 | **Ladder table panel** | Renders `results/ladder.json` verbatim |
| S3.21 | **Decision-value panel** (§6.D) | REV curve with the responder interpretation in words |
| S3.22 | **Attention-Needed overlay** (§6.F) | Disagreement field as a toggleable layer |
| S3.23 | Spaghetti + agreement gauge | Select city → members + blend + band |
| S3.24 | Forecaster Decision Card | Real data only; provenance footer |
| S3.25 | **"Where We Lose" map** (§6.I) | Underperforming regions/leads with reasons |
| S3.26 | Leaderboard | Skill ranking per variable |

**🚩 CHECKPOINT 3:** dashboard loads **real data from Sprint 2/3**. A non-technical person can see (a) where the danger is, (b) which model to trust and why, (c) how confident the forecast is, (d) **where we lose**.

### SPRINT 4 — Story, Honesty & Presentation (30 Sep)

| # | Task | Priority | Done when |
|---|---|---|---|
| S4.1 | **Case replay — July 2023, out-of-sample** (D-08) | HIGH | Model predictions → actual event → our blend → probability-crossing timeline, labelled out-of-sample |
| S4.2 | **Version-drift change-point plot** (§6.H) | MEDIUM | Detected change point on a real per-model error series, with skill-memory reset |
| S4.3 | Spatial weight smoothing | MEDIUM | Salt-and-pepper artefacts gone, Ghats boundary preserved |
| S4.4 | **`make reproduce`** (§6.J) | HIGH | One command regenerates every deck number; log saved |
| S4.5 | **Limitations slide** | **CRITICAL** | ERA5-vs-IMD caveat, wind truth scoping, 2 test seasons, precip availability, null results |
| S4.6 | `TimesFMStrategy` *(only if S4.1/4/5 are done)* | LOW | Behind the interface, measured on the ladder, reported honestly |
| S4.7 | Weather movie animation | LOW | **Cut first** |
| S4.8 | Presentation deck | **CRITICAL** | 12 slides per §13.4 |
| S4.9 | Demo recording | **CRITICAL** | 3-minute screen recording as live-demo backup |
| S4.10 | README + repo cleanup | HIGH | Setup, architecture, ladder table, limitations, licences (§15) |
| S4.11 | **Number sweep** | **CRITICAL** | Every `?.??` in deck and README replaced by a measured value, or the claim is deleted |

## 13.4 Deck outline (12 slides)

1. **Hook** — "Weather models disagree. During a disaster, who do you trust?"
2. **Problem + the five conditioning axes** the PS names
3. **Architecture** — one Adapter→Canonical diagram; GRIB2 in, CF-NetCDF out
4. **The ladder** — floor → singles → blend → **ceiling**, with CIs, and "% of achievable gain captured"
5. **Rain done right** — probability-matched blending, intensity CDFs, FSS-vs-scale curve
6. **Extremes** — calibrated probabilities, reliability diagram, IMD G/Y/O/R map
7. **So what?** — Relative Economic Value curve for a district responder ⭐ *the slide most decks won't have*
8. **Weight maps + computed explanations** — LOMO attribution, shrinkage honesty, forecaster override
9. **Where the forecast is unusually unsure** — disagreement index
10. **Where we lose** — failure modes, with CIs ⭐ *the credibility slide*
11. **Out-of-sample case replay** — July 2023
12. **Operational readiness + limitations** — provenance, Exercise status, degradation table, version-drift detection, honest caveats, `make reproduce`

## 13.5 Definition of Done — the hard commitment

The submission is presentable to an NCMRWF panel when **all** of these are true. §13.3 is aspiration; **this list is the contract.**

- [ ] **Real data in, real numbers out.** Not one `np.random` or hardcoded weather value anywhere in the pipeline.
- [ ] **Accumulation window verified (D-01)** — `test_accumulation.py` green. *Without this every rain number is wrong.*
- [ ] **Ladder table** with measured RMSE + FSS + frequency bias for ≥ 3 models, ≥ 2 blend strategies, **plus climatology floor and oracle ceiling**, with 95 % CIs.
- [ ] **Leakage-free verification** — rolling-origin split, `test_leakage.py` green, explainable in one sentence.
- [ ] **≥ 1 real visual map** (traffic light or weight map) from data-driven output.
- [ ] **One extreme-weather demo** — calibrated exceedance map **or** the July 2023 out-of-sample replay.
- [ ] **Decision-value curve** (§6.D) — the "so what?" answered.
- [ ] **"Where We Lose" honest failure analysis** (§6.I).
- [ ] **GRIB2 readiness proven** — `cfgrib` reads a real NOMADS GFS file on camera; registry pattern shown.
- [ ] **Provenance + EXERCISE status** on every output and screen (D-13).
- [ ] **Limitations slide** — ERA5-vs-IMD, wind scoping, 2 test seasons, precip availability, any null results.
- [ ] **Deck + 3-minute recorded demo.**

If all twelve are checked, the submission is **stronger than every approach surveyed in §4** — regardless of whether TimesFM, the weather movie, or the full regime suite made it in.

## 13.6 Cut order (when time runs out, cut from the bottom up)

```
CUT FIRST ▸ weather movie animation (S4.7)
          ▸ TimesFM strategy (S4.6)
          ▸ leaderboard (S3.26)
          ▸ NeuralGCM as a 4th/5th member
          ▸ full regime suite → keep only the heavy-rain flag
          ▸ heatwave module → keep rain only
          ▸ GeoTIFF export → keep NetCDF
LAST TO CUT ▸ ladder table, D-01 accumulation, leakage test,
              decision value, where-we-lose, provenance
```

## 13.7 Risk matrix

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| **Accumulation window bug (D-01) goes unnoticed** | **Medium** | **Critical** | `test_accumulation.py` in Sprint 1; Checkpoint 1 gate; hand-check one date against IMD |
| **GraphCast precipitation unusable in WB2** | **Medium** | **High** | **P-3 tonight.** Pre-approved split: rain from NWP+ensemble, T/wind from NWP+AI (§7.3) |
| `cfgrib`/`eccodes` fails on Windows | Medium | Critical | **P-2 tonight** (D-09); Docker fallback |
| WB2 download slow / partial | Medium | Critical | Start tonight; region+year subset only; Open-Meteo live fallback |
| IMD gridded data not granted in time | High | Moderate | ERA5 with explicit rainfall-bias caveat (D-10); IMD named as production target |
| 6-D weights overfit | **High** | High | Shrinkage + min-sample fallback (§6.B) + the S2.2 sample histogram before committing rungs |
| Regime conditioning adds zero skill | Medium | Low | Reportable finding; §6.G explains *why* via detector agreement |
| TimesFM slow / unavailable on demo day | Medium | **None** | Behind the strategy interface; `ContextAware` is the top rung; TimesFM is cut-first |
| Blend worse than best single in some regions | **High** | Low | **Expected.** §6.I turns it into the credibility slide; override handles it |
| Frontend can't consume backend in time | Medium | Moderate | Backend writes static JSON to `results/`; frontend reads files; no live API needed |
| Live demo crashes | Low | Critical | 3-minute recording (S4.9) |
| Numbers in deck ≠ numbers in results | Medium | **Critical** | S4.11 number sweep + `make reproduce` (§6.J) |
| Team bandwidth over-committed | High | High | §13.5 is the contract; §13.6 is the cut order; D-16 fixes allocation tonight |

---

# 14. Judge Q&A Preparation

**Q: "Where's your innovation? You just connected existing models and tools."**
> *"The innovation is the decision layer above the models. Four things here don't exist anywhere else. One: our blended rain field stays physically realistic — we use probability-matched blending, so the intensity distribution of the members survives; every other blend smooths the very peak it exists to warn about. Two: we quantify how much of the achievable skill we actually capture, because our results table has a climatology floor and a hindsight-oracle ceiling, not just 'better than GFS'. Three: we tell you where the forecast is unusually unsure, via a disagreement index normalised by each cell's climatological spread. Four: we show you where we lose. And underneath all of it is a six-dimensional trust function built as an ablated ladder with hierarchical shrinkage, so every added dimension had to earn its place."*

**Q: "Why should we trust your blend over individual models?"**
> *"We don't ask you to trust it — we show the proof. FSS at five neighbourhood scales with the correct f₀-based skill criterion, frequency bias, intensity CDFs, block-bootstrap confidence intervals on the differences, rolling-origin validation so no forecast is verified against data used to weight it, and two fully held-out monsoon seasons. And where the blend doesn't beat the best single model, we show you exactly where and why — that's slide ten."*

**Q: "Can this actually run at NCMRWF?"**
> *"Yes. The ingestion layer reads native GRIB2 through xarray + cfgrib — the format NCUM and NEPS already produce on your HPC — and here it is reading a real GFS GRIB2 file. Adding NCUM is one new file in `ingestion/` plus one registry line; nothing downstream changes. We output CF-1.8 NetCDF, which slots into your existing visualisation and dissemination workflow, with a full provenance block: model list, weight strategy, τ, ground truth, git commit."*

**Q: "What if a model is delayed or missing?"**
> *"Missing models are a first-class state, not an error path. Weights renormalise over what arrived — but renormalising alone changes the blend's bias and spread, so the probabilities would quietly go miscalibrated exactly when alerts matter most. So we also recalibrate per availability pattern, and we verify the degraded configurations: here's the blend-minus-one skill table. Untested degradation is a claim; that table makes it a feature."*

**Q: "What's your ground truth, and is it good enough?"**
> *"IMD 0.25° gridded rainfall and 1° Tmax/Tmin are primary, ERA5 is the fallback. Two things we're explicit about. First, IMD's gridded rainfall accumulates 0830 to 0830 IST, so every forecast is resampled to a 0300–0300 UTC window before anything is blended — a three-hour offset there would corrupt every rainfall score, and it's the first thing our test suite checks. Second, where we fell back to ERA5 for rain, we say so, because ERA5 monsoon precipitation over India carries large known biases. Wind is verified against ERA5 with stated land-surface caveats; station verification is the production target — we don't claim gale-force skill we can't verify."*

**Q: "How do you prevent overfitting on only a few seasons?"**
> *"Structurally. First we count samples: we histogram every region × lead × season × regime cell before deciding which rungs of the ladder are even estimable — some cells hold three samples. Then weights use hierarchical shrinkage: each cell shrinks toward its district, region and national parents by effective sample size, and below a threshold it inherits the parent's weights and says so in its explanation. Spatial smoothing is cosmetic; shrinkage is the statistical fix."*

**Q: "What if regime conditioning — or TimesFM — doesn't improve the forecast?"**
> *"Then we report that. Both sit behind a strategy interface and are measured against simpler baselines in the same framework. A published SIH entry's own ablation found regime features added zero skill, so we're not asserting ours does without the same test. And we go one step further: we verify the regime detector itself against observation-derived regimes, so if the ablation is null we can say why — agreement drops from about 84 % at D+3 to 61 % at D+7. A null result explained is more credible than a claim never checked."*

**Q: "Your RMSE improvement — isn't that just from smoothing?"**
> *"Good question, and it's why we never report RMSE alone for rainfall. RMSE rewards smooth fields, so a mean-seeking blend can win it while being operationally useless. Every rain result ships with FSS, frequency bias and an intensity CDF alongside — and the probability-matched blend exists precisely so the peaks survive. Here are the member and blend CDFs side by side."*

**Q: "So what? What does this change for a district officer?"**
> *"That's the decision-value curve. For a responder whose cost of acting is one-tenth the loss of not acting, our blend delivers measurably more value than the best single model — computed from the contingency tables using the WMO-standard relative economic value framework. Brier score tells you the probability is honest; this tells you it's worth acting on."*

**Q: "What if the deadline hits and half the roadmap isn't built?"**
> *"The minimal path stands alone: three real models, one canonical schema, correct accumulation windows, historical skill weighting, a blend, and leakage-free verification against Indian observations with a floor and a ceiling. Regimes, TimesFM, the animation and NCUM ingestion are layered extensions, not dependencies. We also wrote the cut order down in advance — so what's left still answers the problem statement, just with less polish."*

**Q: "Are you issuing weather warnings?"**
> *"No, and that matters. Issuing warnings is IMD's statutory mandate. Every output carries CAP status Exercise, every screen carries a non-dismissible 'experimental — not an official IMD warning' banner, and every file carries provenance down to the git commit. This is decision-support for a duty forecaster, who always has the final call — and every override is logged and auditable."*

**Q: "Is every number in this deck reproducible?"**
> *"Yes — `make reproduce` regenerates every number in it from the configs in the repository. Here's the log."*

**Q: "Why TimesFM at all?"**
> *"TimesFM is a general-purpose time-series foundation model — it knows nothing about weather, models, or India. Applying it to *forecast-model error drift*, using each model's trailing error series to anticipate which model is about to degrade, is our idea. But we were careful not to put it in the critical path: it's one strategy behind an interface, and it has to beat context-aware weighting on the ladder to earn its place. If it doesn't, we say so."*

---

# 15. Ethics, Provenance & Data Licensing

### 15.1 Operational and legal positioning (D-13)
- Forecast warnings for India are **IMD's statutory mandate.** This system is **decision support**, not a warning authority.
- Every output: CAP `status="Exercise"`; every screen: persistent **"EXPERIMENTAL — NOT AN OFFICIAL IMD WARNING."**
- **No autonomous action recommendations** presented as authoritative. The forecaster is always in the loop, and every override is logged with user, timestamp, reason and prior weights.
- Impact figures (population) are **estimates from a cited raster** (D-15), labelled with source and year — never invented.

### 15.2 Data provenance & licence table (one appendix slide — easy marks, nobody else will have it)

| Dataset | Provider | Licence / terms | Our compliance |
|---|---|---|---|
| WeatherBench2 archives | Google / ECMWF / NOAA | Per-product terms; some ECMWF products research-use | Research/academic use; attribution in README + deck |
| ERA5 | Copernicus / ECMWF | Copernicus licence, attribution required | Attribution in README, deck, and every NetCDF header |
| IMD gridded rainfall / temperature | IMD Pune (Pai et al.) | IMD data-use terms; institutional request | Cited; usage stated; not redistributed in the repo |
| GFS / GEFS | NOAA NCEP | Public domain | Attributed |
| GraphCast | Google DeepMind | Open weights/code, per repo licence | Cited (*Science* 2023); used as published |
| NeuralGCM | Google Research | Open, per repo licence | Cited (*Nature* 2024) |
| TimesFM | Google Research | Open, HuggingFace licence | Cited; optional component |
| Open-Meteo | Open-Meteo | Free tier, attribution + rate limits | Attributed; cached, rate-limit respected |
| District boundaries | datameet / Survey of India | Per-source terms | Attributed |
| WorldPop / GPW v4 | WorldPop / CIESIN | CC-BY | Attributed with year |
| SRTM / ETOPO | NASA / NOAA | Public domain | Attributed |

### 15.3 Scientific honesty commitments
1. No number reaches a slide until it is measured (§13.5, S4.11).
2. Null results are reported, not buried (regime, TimesFM, any rung).
3. Where the blend loses is shown explicitly (§6.I).
4. Ground-truth substitutions are declared with their known biases (D-10).
5. Every deck number is regenerable by one command (§6.J).
6. Other teams' work is discussed in aggregate, never named and disparaged (D-14).

---

# 16. The Pitch

### 16.1 The one-sentence reframe
The earlier drafts sold *"we pick the right model."* That is table stakes, and half the field claims it. The defensible product is:

> **"We produce a blended forecast that stays physically realistic, we quantify how much of the achievable skill we actually capture, we tell you where the forecast is unusually unsure, and we show you where we lose."**

No surveyed approach can say any one of those four.

### 16.2 The 30-second pitch

> **"Weather models disagree. During a disaster, who do you trust?"**
>
> Different models are best in different places, seasons, lead times and weather regimes — so no single model is best everywhere. **Ours is the decision-intelligence layer** that answers which model to trust, when, where, and why.
>
> We ingest physics-based NWP, AI models and ensembles through a **native GRIB2 pipeline** — the same format NCUM and NEPS produce on NCMRWF's HPC — not a public web API.
>
> Our **six-dimensional trust engine** — model, variable, region, lead time, season, regime — weights each source by its proven skill in that exact context, with **hierarchical shrinkage** so a few seasons of data can't overfit it, and **every added dimension validated by ablation** against a simpler baseline.
>
> Rain is blended **probability-matched**, so the intensity peaks survive — every other blend smooths the very peak it exists to warn about.
>
> We report skill against a **climatology floor and a hindsight ceiling**, so we can tell you what fraction of the achievable gain we actually capture — verified with WMO-standard FSS across two fully held-out monsoon seasons, with bootstrap confidence intervals and leakage-free rolling-origin validation.
>
> For disaster management we don't just blend means: we issue **calibrated probabilities** — *"`??`% chance of Very Heavy Rain in Ratnagiri"* — mapped to IMD's exact Yellow/Orange/Red thresholds, with a **decision-value curve** showing what that's worth to a responder whose cost of acting is a tenth of the loss of not acting.
>
> And because trust is earned: we flag **where the forecast is unusually unsure**, we show **where our blend loses**, every output is **provenance-stamped and marked EXERCISE**, and every number in this deck is regenerated by one command.
>
> **The forecaster always has the final call — every weight is explained by measured model impact, and every override is logged.**

---

# 17. Flaw → Fix Traceability

Every flaw identified in the review of the earlier drafts, and where it is now closed. **Nothing dropped.**

| # | Flaw (earlier drafts) | Severity | **Closed by** |
|---|---|---|---|
| F1 | IMD 0830 IST vs. UTC accumulation mismatch — corrupts every rain number | 🔴 Blocker | **D-01**, §7.1 normalisation step, `canonical/accumulation.py`, S1.2, `test_accumulation.py`, §13.5 |
| F2 | Precipitation availability for AI models unverified; rain blend could collapse to 2 members | 🔴 Blocker | **P-3** (§13.2), §7.3 gate + pre-approved split contingency, risk matrix |
| F3 | Regime source ambiguous → leakage or inoperable | 🔴 Blocker | **D-04**, §7.4, `regimes/base.py`, S3.12 |
| F4 | `cfgrib`/`eccodes` on Windows blocks the strongest claim | 🔴 Blocker | **D-09**, **P-2** (§13.2), `environment.yml` committed |
| F5 | No version control | 🔴 Blocker | **D-17**, `git init` + `.gitignore` done, P-1 |
| F6 | Ladder had no climatology floor and no oracle ceiling | 🟠 Serious | **§6.C**, §7.4 strategies, §7.5 table, S2.5 + S3.8 |
| F7 | RMSE rewards smoothing; would be led with | 🟠 Serious | **D-12**, §7.8, S2.10 intensity CDF, §14 Q&A |
| F8 | Weighted-mean blending contradicts own Gap 4 | 🟠 Serious | **D-11 / §6.A**, `blending/probability_matched.py`, S3.4 |
| F9 | 6-D weights overfit; smoothing treated a sampling problem as cosmetic | 🟠 Serious | **§6.B**, §7.4, S2.2 sample histogram, S3.2, `test_shrinkage.py` |
| F10 | Softmax τ undefined in three places | 🟠 Serious | **D-05**, `weighting/tau_fit.py`, S3.3, `results/tau.json` |
| F11 | FSS criterion wrong ("FSS > 0.5") | 🟠 Serious | **§6-I5 / §7.8** — `FSS_useful = 0.5 + f₀/2`, S2.4, `test_fss.py` |
| F12 | Renormalisation ≠ graceful degradation; probabilities go miscalibrated | 🟠 Serious | **§7.9** — per-pattern recalibration + blend-minus-one table, S3.16 |
| F13 | Wind had no ground truth | 🟠 Serious | **D-06**, §7.8, scoped claim, §14 Q&A |
| F14 | "Affected population 1.6M" fabricated in own mockup | 🟠 Serious | **D-15**, download D6, §11 popup labelling |
| F15 | District aggregation rule unspecified | 🟠 Serious | **D-07** — area-weighted p90 default, toggles, printed on map |
| F16 | Kerala 2018 replay risked being a leakage claim | 🟠 Serious | **D-08** — July 2023 out-of-sample; Kerala dropped |
| F17 | Best document had no `.md` extension | 🟡 Doc | This file is `.md` and canonical (§0) |
| F18 | Two divergent copies (5-D vs 6-D; TimesFM in vs. out of critical path) | 🟡 Doc | §0 document map; old files archived; this file supersedes |
| F19 | Three different year ranges; pitch claimed "5 seasons" on 4 seasons of data | 🟡 Doc | **D-02 / D-03**; §16.2 says "two fully held-out seasons" |
| F20 | Research-gaps doc orphaned; detail lost | 🟡 Doc | §0 names it the **internal annex**; §4/§5 reference it |
| F21 | Gap 7 (version drift) appeared in no sprint | 🟡 Doc | **§6.H**, `monitoring/change_point.py`, S4.2, deck slide 12 |
| F22 | Team size never stated; ~40 tasks in 4 days | 🟠 Serious | **D-16** filled tonight; §13.5 contract; **§13.6 cut order** |
| F23 | Competitor teardown a liability in a submitted doc | 🟡 Doc | **D-14**; §4 aggregate framing; detail in internal annex |
| F24 | CAP alerts + action advice styled as IMD warnings | 🟠 Serious | **D-13**, §7.11, §15.1, §6.L |
| F25 | No data licence / provenance audit | 🟡 Doc | **§15.2** licence table; provenance block in every output |

---

# 18. Innovation Index

| ID | Innovation | Cost | Differentiation | Priority |
|---|---|---|---|---|
| **I-1** | 6-D trust scoring as an ablated ladder | Med | High | P0 |
| **I-2** | Forecast-derived dynamical regime detection | Med | High | P2 |
| **I-3** | IMD-threshold calibrated hazard probabilities | Med | High | P0 |
| **I-4** | Forecaster override with computed explainability | Low | High | P1 |
| **I-5** | FSS framework for India (correct criterion) | Low | High | P0 |
| **6.A** | **Probability-matched blending** | **Low (~30 lines)** | **Very high** | **P0 ⭐** |
| **6.B** | **Hierarchical shrinkage + min-sample fallback** | Med | **Very high** | **P0 ⭐** |
| **6.C** | **Climatology floor + oracle ceiling** | Low | High | **P0 ⭐** |
| **6.D** | **Relative Economic Value (cost–loss)** | **Very low** | **Very high** | **P1 ⭐ best value/hour** |
| **6.E** | **Leave-one-model-out weight explanations** | Low | High | P1 |
| **6.F** | **Normalized disagreement index** | **Very low (~50 lines)** | **Very high** | P1 |
| **6.G** | **Regime-detector verification** | Low | High | P2 |
| **6.H** | **Demonstrated version-drift detection** | Low (½ day) | High | P2 |
| **6.I** | **"Where We Lose" analysis** | Low | **Very high** | **P1 ⭐** |
| **6.J** | **`make reproduce`** | Low | High | P1 |
| **6.K** | **Terrain-stratified verification** | **Very low (groupby)** | High | P1 |
| **6.L** | **Provenance-stamped, EXERCISE-flagged outputs** | Low | High | P0 |

**The five to fight for:** **6.A** (physically realistic rain) · **6.B** (statistically real weights) · **6.C** (floor + ceiling narrative) · **6.D** (the "so what?") · **6.I** (credibility).

---

# 19. Glossary of Metrics

| Metric | What it measures | Why we use it | Gotcha |
|---|---|---|---|
| **RMSE / MAE** | Mean error magnitude | Comparability with prior work | **Rewards smoothing** — never alone for rain (D-12) |
| **Bias / Frequency bias** | Systematic over/under-forecast; over/under-prediction of events above a threshold | Detects smoothing and threshold drift | Needs a threshold for frequency bias |
| **FSS** (Fractions Skill Score) | Fractional agreement within a neighbourhood | Avoids double-penalising small displacement — operational standard for rain | Skill target is **`0.5 + f₀/2`**, not 0.5; random reference is `f₀` |
| **Intensity CDF** | Distribution of forecast values vs. observed | Shows probability matching working | Compare on the same mask/domain |
| **Brier / Brier skill score** | Accuracy of probability forecasts | Standard probabilistic metric | BSS needs a stated reference (climatology) |
| **Reliability diagram** | Do 70 % forecasts verify 70 % of the time? | Calibration evidence | Needs a sharpness histogram beside it |
| **ROC / AUC** | Discrimination between event and non-event | Independent of calibration | High AUC with bad calibration is possible |
| **CRPS** | Whole-distribution accuracy | Distributional scoring | Sensitive to spread errors |
| **Relative Economic Value** | Decision value across cost:loss ratios | **Answers "so what?" for a responder** (§6.D) | Must state the cost:loss ratio assumed |
| **Block-bootstrap CI** | Uncertainty on skill *differences* | Honest comparison; handles autocorrelation | Block length must exceed the weather decorrelation scale |
| **`n_eff` / sample count** | How much data a weight cell actually has | Drives shrinkage (§6.B) | Autocorrelated days ≠ independent samples |
| **Disagreement index D** | Spread relative to *climatological* spread | Flags unusual uncertainty (§6.F) | Needs a per-cell/season/regime climatology first |
| **Regime agreement %** | Forecast-derived vs. obs-derived regime match | Validates the detector (§6.G) | Degrades with lead time — report per lead day |

---

## Document control

| | |
|---|---|
| **Version** | v3.0 — 26 September 2026 |
| **Status** | ✅ Canonical. Supersedes `SIH26081_solution_blueprint.md` and `SIH26081_solution_revised` (archived). |
| **Internal annex** | `SIH26081_research_gaps.md` — competitor evidence, per-repo detail, sources (not for submission, per D-14) |
| **Decisions log** | `DECISIONS.md` — append-only, dated |
| **Change rule** | Any change to a §1 decision must be reflected here, in `DECISIONS.md`, and in every affected slide, in the same commit. |
| **Confidential** | Team use only until the SIH presentation. |
