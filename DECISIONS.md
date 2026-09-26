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
