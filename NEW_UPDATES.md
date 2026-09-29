# SIH26081 — New Updates

A snapshot of where the project stands, what is missing, and what we build next.

---

## 1. Data — what we actually have

The WeatherBench2 inventory changed three assumptions from the original plan:

| Finding | Consequence |
|---|---|
| **WeatherBench2 has no GFS** | Our pool is **ECMWF IFS HRES** (physical NWP), **IFS ENS mean** (ensemble), **GraphCast** and **Pangu-Weather** (AI). This actually matches the problem statement better: NWP + ensemble + AI. |
| **WeatherBench2 ends in 2022** | Years are **2018, 2020, 2022** (the years GraphCast covers). Folds: train 2018 → test 2020; train 2018+2020 → test 2022. Two fully held-out years. |
| **IMD's gridded-data server is unreachable** | Ground truth is **ERA5** for now, stated on every output. Caveat for the limitations slide: ERA5 underestimates monsoon rainfall extremes. |
| **Pangu has no precipitation** | Rain is blended from HRES + ENS + GraphCast; temperature and wind from all four. |
| **The IMD 08:30 IST day can be built exactly** | The 03Z→03Z rainfall total = mean of the 00Z→00Z and 06Z→06Z rolling totals. No 3-hour offset. |
| **Lead days are 1, 3, 5, 7, 9** (not 10) | Day 10 would need a 246 h lead; the archive stops at 240 h. |

**Download status**

| Variable | Status |
|---|---|
| Precipitation | ✅ complete — HRES, ENS, GraphCast, ERA5 × 3 years |
| 2 m temperature | ✅ complete — all 4 models + ERA5 |
| u10 wind | ⏳ in progress |
| v10 wind | ⏳ queued after u10 (~1.5–2 h total remaining) |

Do not kill the download process — it is resumable, but a restart wastes time.

**Static layers built:** 736 districts (geoBoundaries 2021, ODbL), states, IMD homogeneous regions, WorldPop 2020 population on the 0.25° grid.

---

## 2. Audit of the current code

The code covers a lot of ground, but **no real numbers have reached the screen yet**.

| Problem | Impact |
|---|---|
| **Pipeline crashes on import** (`experiments/run.py`: `write_bounds` imported from the wrong module) | `results/` has never been generated. |
| **Every file in `frontend/public/data/` is `"fixture": true`, and the watermark was disabled** | The dashboard currently shows fake numbers with no warning. This must be fixed before anyone sees it — it is exactly what we criticise other teams for. |
| **The ladder is computed on a single day**, not over the 2020 + 2022 held-out years | The "leakage-free, two held-out years, bootstrap CIs" claim is not yet true. |
| REV, equal-weight and inverse-error rungs are `0.0`; `tmax_c` / `wind_ms` are `0.0`; climatological spread is a constant `10.0` | Several headline innovations currently display placeholders. |
| `fss50` uses a 9-cell window (~250 km) | Mislabelled metric. |
| "% of achievable gain" uses climatology instead of best-single-model | Wrong formula. |
| 3 failing tests (`roc_auc` ×2, `context_aware`) | |
| No `make` on Windows | `make reproduce` can't run as-is; needs a Python task runner. |

---

## 3. Innovation scope — nothing left out

### ✅ Working
- Probability-matched rain blending (6.A)
- Leave-one-model-out weight explanations (6.E) — needs multi-day evaluation
- Provenance `meta` block on every file
- District tiers (area-weighted 90th percentile)
- Static layers (districts, population, land mask)

### ⚠️ Code exists but is not wired into the pipeline
- Hierarchical shrinkage weights (6.B) — unverified
- Regime detector + its verification (I-2, 6.G)
- Version-drift change-point detection (6.H)
- Terrain-stratified verification (6.K)
- Case study (Assam–Meghalaya floods, June 2022)
- Isotonic calibration (I-3)
- τ (softmax temperature) fitting
- Forecaster override (I-4)
- NetCDF writer
- GRIB2 adapter (not demoed)

### ⚠️ Wired but placeholder or wrong
- Baseline ladder (I-1) — single day, missing rungs
- Climatology floor + oracle ceiling (6.C) — no persistence rung; gain formula wrong
- Relative Economic Value (6.D) — zeros
- Disagreement index (6.F) — constant spread
- FSS (I-5) — one mislabelled scale instead of a skill-vs-scale curve
- "Where We Lose" (6.I) — based on one day
- `make reproduce` (6.J) — pipeline broken, no `make` on Windows

### ❌ Not built yet
- FastAPI (0 endpoints)
- CAP 1.2 XML alerts
- GeoTIFF export
- Docker + scheduler
- TimesFM weighting strategy
- Western-disturbance / cyclone regimes
- Heatwave hazard
- Wind hazard (waiting on u10/v10)
- NeuralGCM as an extra member
- Model skill leaderboard
- Weather-movie animation
- Blend-minus-one degradation table + per-availability-pattern calibrators
- Raster PNG overlays

---

## 4. New "wow" features — agreed direction

### 4.1 Live re-blending with weight sliders ⭐ strongest for a technical panel
The backend ships each model's field per lead as compact arrays (~280 KB). The browser computes the blend and probabilities itself. A judge drags "GraphCast weight" up and **watches districts re-colour in real time**, with RMSE updating live. This makes our core IP — adaptive weighting — tangible, and it *is* the forecaster-override feature.

### 4.2 SMS alerts ⭐ biggest impact story
Reaches every phone, including feature phones without data.

- **The catch:** business/bulk SMS in India requires **TRAI DLT registration** (entity, sender ID, every template). Takes days — not feasible before submission.
- **Demo solution:** an **Android phone as the SMS gateway** (open-source apps like *SMS Gateway for Android* / *httpSMS* expose an HTTP API; messages go out from the phone's own SIM as normal SMS, no DLT needed). Limit ~100 SMS/day per SIM — plenty for a demo.
- **Live moment:** a judge gives their number, a district turns Red, their phone buzzes.
- **Production story:** NDMA's **SACHET** (India's national alert platform, SMS + cell broadcast) ingests **CAP 1.2**. Pitch line: *"We don't build SMS infrastructure — our CAP 1.2 feed plugs straight into SACHET."*
- **Constraints:** 160 characters in English, **70 characters per segment** in Indian scripts. Every message carries the EXERCISE tag.

Example messages:
```
[EXERCISE] ORANGE Rain alert: Ratnagiri, 16 Jun. 72% chance >115mm. Avoid rivers/low areas. -SIH26081 blend, not IMD
```
```
[अभ्यास] ऑरेंज अलर्ट रत्नागिरी 16 जून: 115mm+ वर्षा की 72% संभावना। नदी से दूर रहें
```

Pipeline: **CAP 1.2 feed → FastAPI `/alerts` → SMS dispatcher** (Android gateway for demo, SACHET for production) + subscriber list per district.

WhatsApp is **dropped for now** (needs a business account).

### 4.3 "What does this mean for me?" impact cards
The same forecast rendered per persona:
- **Farmer:** don't spray pesticide, delay sowing
- **Fisher:** don't go to sea
- **District Magistrate:** pre-position NDRF teams, N people exposed (WorldPop)
- **Citizen:** avoid rivers and low-lying areas

This follows WMO's impact-based forecasting direction, and the same text feeds the SMS templates.

### 4.4 Grounded forecaster copilot (not a generic RAG chatbot)
RAG over PDFs is commodity — every team will have one. Ours is an agent that **calls tools over our actual results**: "Why is Ratnagiri red?" → it reads that district's probabilities, weights and LOMO numbers and answers with them.
Hard rules: it may only state numbers returned by a tool, and every answer carries the EXERCISE disclaimer. An LLM inventing a warning in front of MoES is a liability.

### 4.5 Cinematic case replay — "Watch the blend see Assam 2022 coming"
Scroll-driven timeline from 5 days before the Assam–Meghalaya extreme rain (15–17 June 2022) to the event: the probability map sharpens each day, then the real ERA5 outcome is revealed. It's in the 2022 test fold, so the claim is legitimately out-of-sample.

### 4.6 Later, if time allows
- **Voice / IVR:** missed-call forecast line (caller gives a missed call, system calls back free), speech in Indian languages via **Bhashini** (Govt of India language-AI platform). Reuses the SMS message templates.

---

## 5. Order of work

| # | Step | Why this order |
|---|---|---|
| **1** | **Make it real** — fix the pipeline; compute the ladder over both held-out years; fill REV, equal/inverse-error/persistence rungs, real disagreement spread, FSS curve; generate rasters; sync to frontend; restore the fixture watermark | Every wow feature built on fixture data just amplifies fake numbers. Real data is already on disk — this is hours, not days. |
| **2** | **Live re-blending sliders** | Highest wow per hour; doubles as forecaster override. |
| **3** | **CAP 1.2 + FastAPI + SMS dispatcher** (Android gateway) | Highest impact story; also completes the operational-output deliverable. |
| **4** | **Impact cards** | Feeds the SMS text; cheap once step 3 exists. |
| **5** | **Grounded copilot** | Reuses the FastAPI endpoints from step 3. |
| **6** | **Cinematic Assam 2022 replay [DONE]** | Needs the case study wired in step 1. Built scroll-driven React timeline, rendered D-5, D-3, D-1 JSON forecasts, and ERA5 truth raster for UI visualization. |
| **7** | **Remaining items from §3** — change-point, terrain cuts, regimes, heatwave, wind hazards, TimesFM, GeoTIFF, Docker, weather movie, leaderboard, minus-one table, NeuralGCM | Nothing is dropped; these come after the core is real. |
| **8** | **Voice / IVR** | Only if everything above is done. |

---

## 6. Rules that still apply

- **No number on screen, in the deck, or in an SMS unless it comes from a `results/` file.**
- **Every output says EXERCISE — not an official IMD warning.**
- **The fixture watermark stays on until real data replaces every fixture.**
- Backend writes `results/`; frontend reads it. Shape changes = one conversation, two commits.
