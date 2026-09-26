# DECISIONS.md — SIH26081

**Append-only.** Every entry is dated. Never edit or delete a past entry — supersede it with a new one and note which it replaces.

A decision here is binding on code, slides and README. If you change one, update `SIH26081_MASTER_PLAN.md` §1 and every affected slide **in the same commit**.

---

## 2026-09-26 — Initial decision set (v3.0, from MASTER_PLAN §1)

| # | Decision | Locked value | One-line reason |
|---|---|---|---|
| D-01 | Canonical daily accumulation window | **0300 UTC → 0300 UTC** (0830–0830 IST) | IMD gridded rain accumulates 0830 IST; a 3 h offset corrupts every rain score |
| D-02 | Year range | **2020–2023** primary; 2018–2023 stretch | Three conflicting ranges existed across drafts |
| D-03 | Folds | Train 2020–21→Test 2022; Train 2020–22→Test 2023 (**2 held-out seasons**) | Pitch must not claim 5 seasons on 4 seasons of data |
| D-04 | Regime source | **Forecast-derived only**, same lead time | Obs-derived regimes are inoperable at forecast time and leak the target |
| D-05 | Softmax τ | **Fitted** per (variable, lead-band); `results/tau.json` | Most influential hyperparameter; was undefined in three formulas |
| D-06 | Wind ground truth | **ERA5 10 m** + stated caveats; stretch: IMD AWS | IMD gridded has no wind; don't claim unverifiable gale skill |
| D-07 | Grid → district aggregation | **Area-weighted 90th percentile** (default); mean/max toggles; rule printed | `max` reddens every large district; `mean` hides local extremes |
| D-08 | Case study | **North India / Himachal floods, July 2023** (in 2023 test fold). Alt: Cyclone Biparjoy, Jun 2023. **Kerala 2018 dropped.** | "Warned 72 h early" is invalid if the event year is in training |
| D-09 | Environment | **conda-forge `environment.yml`** (committed); Docker fallback | `cfgrib`/`eccodes` on native Windows is a known trap on our critical path |
| D-10 | Ground truth priority | Rain: IMD 0.25° → ERA5 (**with explicit monsoon-bias caveat**). Temp: IMD 1° → ERA5. Wind: ERA5. | ERA5 is fine for T/wind; for rain it is a material limitation, not a free substitution |
| D-11 | Deterministic rain blending | **Probability-matched blending** | A weighted mean destroys the peaks the system exists to warn about |
| D-12 | Headline metric policy | Rain **never** reported with RMSE alone — always + FSS + frequency bias + intensity CDF | RMSE rewards smoothing; say it before a judge does |
| D-13 | Output legal status | CAP `status="Exercise"`; persistent **"EXPERIMENTAL — NOT AN OFFICIAL IMD WARNING"** banner; provenance block | Warning issuance is IMD's statutory mandate |
| D-14 | Competitor teardown | Detailed teardown stays **internal** (`SIH26081_research_gaps.md`); submission speaks of "published approaches" in aggregate | One wrong claim about a named team is a credibility hit |
| D-15 | Population data | **WorldPop / GPW v4** cited — or the figure is deleted from the UI | An un-sourced impact number is the fabrication we criticise in others |
| D-16 | Team allocation | ⚠️ **TO FILL TONIGHT** — backend: ____ · frontend: ____ · verification/slides: ____ | Sprint feasibility depends entirely on this, and it was never stated |
| D-17 | Version control | `git init` done; feature branches; `main` always runnable; lockfiles committed | Four days, parallel tracks, one shared result set |

---

## Open items requiring a decision

| Item | Blocked on | Owner | Due |
|---|---|---|---|
| **D-16 team allocation** | nothing — just decide | — | tonight |
| Does GraphCast supply usable precipitation in WB2 for our box/years? | **pre-work P-3** | — | tonight |
| If not: activate the §7.3 split (rain from NWP+ensemble; T/wind from NWP+AI) | P-3 result | — | tonight |
| Is IMD gridded data obtainable in time, or is ERA5 the prototype truth? | data request | — | Sep 27 |
| Stretch: extend data back to 2018 (→ 3 held-out seasons)? | download bandwidth after D1/D2 | — | Sep 27 |

---

## Template for new entries

```
## YYYY-MM-DD — <short title>

**Decision:** <what was decided>
**Supersedes:** <D-xx, or "none">
**Reason:** <why this and not the alternative>
**Affects:** <code modules / slides / README sections to update in the same commit>
**Decided by:** <name>
```

---

## 2026-09-27 — Tech approach & team split (from TECH_APPROACH_AND_TEAMS.md §1, §4)

**Supersedes:** every "X or Y" in MASTER_PLAN §9. **Affects:** `environment.yml`, `frontend/package.json`, repo ownership.

| # | Decision | Locked value | One-line reason |
|---|---|---|---|
| D-18 | Backend runtime | **Python 3.11 on conda-forge (mamba)**; Docker base `condaforge/mambaforge` | `eccodes` is a C lib; conda-forge is the only sane path on Windows |
| D-19 | Schema | **pydantic v2** | The quality gate *is* validation |
| D-20 | Canonical grid | **The IMD 0.25° rainfall grid itself** (6.5–38.5 N, 66.5–100 E) | Truth is never regridded |
| D-21 | Regridding | **`xarray.interp` bilinear** | `xesmf` has no Windows build; WB2 is already 0.25° |
| D-22 | ML | **LightGBM** (quantile objective) | Native quantile, CPU-fast, light install |
| D-23 | Config / CLI / scheduler | **pyyaml + argparse + cron-in-Docker** | Zero learning curve; cron is what NCMRWF runs. Prefect = production upgrade path |
| D-24 | API | **FastAPI, 6 endpoints**, `results/` mounted static | Dashboard never depends on the API during the demo |
| D-25 | Frontend | **Vite + React 18 + TypeScript + zustand + Tailwind** | Shared state across six panels; TS types generated from the data contract |
| D-26 | Map / charts | **Leaflet + react-leaflet** (PNG `ImageOverlay` rasters pre-rendered by backend) · **Plotly.js** | No token/billing; scientific charts native |
| D-27 | Team A ↔ Team B interface | **Files in `results/` per TECH_APPROACH §3.** Team A writes, Team B reads. Nothing else crosses. | Lets both teams work from hour one |
| D-28 | Fixtures | `frontend/fixtures/` only; `"fixture": true`; full-screen watermark; `build:demo` refuses them | Team B is never blocked, and never fakes a number |
| D-29 | `results/` freeze | **Tue 30 Sep, 14:00** — tag `v1.0-results` | Numbers in deck == numbers in results |
| D-30 | Repo ownership | Team A: science modules + tests + env. Team B: `frontend/ api/ outputs/ docker/ README deck demo`. | See TECH_APPROACH §4.1 |

**Decision rules pending data (TECH_APPROACH §6):**
- **6.1** If WB2 has no 2023 → range becomes **2018–2022**, folds Train 2018–20/Test 2021 + Train 2018–21/Test 2022, case study → **Assam–Meghalaya floods June 2022**. Record as D-31 by Sat 27 noon.
- **6.2** If no usable AI-model precipitation → **split pools** (rain: NWP+ensemble; T/wind: NWP+AI). Record as D-32 by Sat 27 noon.
- **6.7** D-16 team allocation — **still unfilled.** Fill Sat 27 09:00.
