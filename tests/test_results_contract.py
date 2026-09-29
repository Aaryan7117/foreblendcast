"""Output contract: what the pipeline writes to results/ must be real and self-consistent.

Skipped until the pipeline has been run (`python -m experiments.run`).
"""
import json
import math
from pathlib import Path

import pytest

RESULTS = Path("results")
pytestmark = pytest.mark.skipif(not (RESULTS / "summary.json").exists(),
                                reason="pipeline outputs not generated")


def load(name):
    # json.loads rejects NaN / Infinity here, so every file must be strict JSON
    return json.loads((RESULTS / name).read_text(encoding="utf-8"),
                      parse_constant=lambda c: pytest.fail(f"{name} contains {c}"))


def rows(ladder):
    return {r["strategy"]: r["metrics"] for r in ladder["rows"]}


@pytest.fixture(scope="module")
def ladder():
    return load("ladder.json")


def test_every_variable_has_a_ladder():
    for name, variable in (("ladder.json", "precip"), ("ladder_t2m.json", "t2m"),
                           ("ladder_wind.json", "wind")):
        lad = load(name)
        assert lad["variable"] == variable
        assert {"equal_weight", "context_shrink", "oracle", "climatology"} <= set(rows(lad))


def test_truth_source_is_stated(ladder):
    assert ladder["meta"]["ground_truth"] == "ERA5"
    assert "not IMD" in ladder["meta"]["ground_truth_detail"]
    assert ladder["meta"]["fixture"] is False


def test_equal_weight_baseline_is_its_own_row(ladder):
    r = rows(ladder)
    for lead in r["equal_weight"]:
        assert r["equal_weight"][lead]["rmse"] != r["climatology"][lead]["rmse"]
        assert r["equal_weight"][lead]["rmse"] < r["climatology"][lead]["rmse"]


def test_mae_is_measured_not_derived_from_rmse(ladder):
    ratios = {round(m["mae"] / m["rmse"], 3) for metrics in rows(ladder).values()
              for m in metrics.values() if m["rmse"]}
    assert len(ratios) > 3 and ratios != {0.8}


def test_oracle_is_the_ceiling_and_blend_beats_equal_weights(ladder):
    r = rows(ladder)
    for lead, m in r["context_shrink"].items():
        assert r["oracle"][lead]["rmse"] <= m["rmse"]
        assert m["rmse"] < r["equal_weight"][lead]["rmse"]
        lo, hi = m["ci_rmse_vs_equal_weight"]
        assert lo <= hi


def test_headline_numbers_follow_from_the_rows(ladder):
    r, head = rows(ladder), ladder["headline"]
    for lead, pct in head["rmse_change_vs_equal_weight_pct"].items():
        ours, eq = r["context_shrink"][lead]["rmse"], r["equal_weight"][lead]["rmse"]
        assert math.isclose(pct, 100 * (ours - eq) / eq, abs_tol=0.05)
    assert head["test_years"] == [2020, 2022]
    for fold in ladder["folds"]:
        assert all(y < fold["test"] for y in fold["train"])


def test_ablation_has_every_step():
    ab = load("ablation.json")["leads"]
    for lead in ab.values():
        steps = [s["strategy"] for s in lead["deterministic"]]
        assert steps == ["equal_weight", "inverse_error", "context", "context_shrink",
                         "context_shrink_pm"]
        p = lead["probabilistic"]
        assert set(p["crps"]) >= {"adaptive_blend_with_quantiles", "equal_weight_with_quantiles"}
        assert 0.8 < p["interval_90_coverage"] < 0.97
        assert p["brier"]["adaptive_weights_calibrated"] <= p["brier"]["adaptive_weights_members"] * 1.05


def test_reliability_is_built_from_held_out_forecasts():
    rel = load("reliability.json")
    assert rel["threshold_mm"] == 64.5 and len(rel["bins"]) == 10
    for curve in ("equal_weight", "blend_raw", "blend_calibrated"):
        assert len(rel["observed_freq"][curve]) == 10
        assert sum(rel["counts"][curve]) > 100_000
        assert 0.5 <= rel["auc"][curve] <= 1.0


def test_where_we_lose_intervals_are_bootstrap_intervals():
    wl = load("where_we_lose.json")
    assert wl["summary"]["contexts_tested"] > 0
    for c in wl["cells"]:
        lo, hi = c["ci"]
        assert lo < hi
        assert c["blend_rmse"] >= c["best_single_rmse"]   # rounded to 3 decimals
        assert c["significant"] == (lo > 0)
        assert c["n_days"] >= 15


def test_districts_carry_all_three_hazards():
    leads = sorted(int(p.stem.split("_L")[1]) for p in RESULTS.glob("districts_L*.json"))
    assert [ld for ld in leads if ld > 0] == [1, 3, 5, 7, 9]
    d = load("districts_L1.json")
    assert d["meta"]["weights_frozen_before_cycle"] is True
    assert 2022 not in d["meta"]["train_years"]
    assert len(d["districts"]) > 700
    temps, winds = set(), set()
    for rec in d["districts"]:
        assert rec["tmax_c"] is not None and rec["wind_ms"] is not None
        assert isinstance(rec["heatwave"], bool) and isinstance(rec["high_wind"], bool)
        assert 0 <= rec["p_heatwave"] <= 1 and 0 <= rec["p_wind_8"] <= 1
        assert math.isclose(sum(rec["weights"].values()), 1.0, abs_tol=0.01)
        assert rec["precip_q05_mm"] <= rec["precip_q95_mm"]
        assert rec["shrinkage"]["level_used"] in ("national", "region", "district", "cell")
        temps.add(rec["tmax_c"]); winds.add(rec["wind_ms"])
    assert len(temps) > 100 and len(winds) > 20      # real fields, not a constant
    assert len({json.dumps(r["weights"], sort_keys=True) for r in d["districts"]}) > 50


def test_point_quantiles_are_not_a_multiple_of_the_blend():
    for p in (RESULTS / "points").glob("*.json"):
        pt = json.loads(p.read_text(encoding="utf-8"))
        assert pt["lead_days"] == [1, 3, 5, 7, 9]
        assert set(pt["members"]) == {"hres", "ens", "graphcast"}
        pairs = [(b, lo, hi) for b, lo, hi in zip(pt["blend"], pt["q05"], pt["q95"]) if b]
        assert all(lo <= hi for _, lo, hi in pairs)
        assert len({round(hi / b, 2) for b, _, hi in pairs}) > 1 or len(pairs) < 2


def test_rasters_exist_for_every_selector_and_lead():
    names = {p.name for p in (RESULTS / "rasters").glob("*.png")}
    for ld in (1, 3, 5, 7, 9):
        for stem in ("precip_pm", "precip_hres", "precip_ens", "precip_graphcast", "precip_baseline",
                     "p_gt_64p5", "disagreement", "tier", "t2m", "wind", "p_heatwave", "p_wind_8",
                     "weight_hres", "dominant_model"):
            assert f"{stem}_L{ld}.png" in names, f"{stem}_L{ld}.png"
    assert "truth.png" in names


def test_gis_products_are_written():
    products = {p.name for p in (RESULTS / "products").glob("*")}
    assert any(n.endswith(".nc") for n in products)
    assert sum(n.endswith(".tif") for n in products) >= 5


def test_replay_uses_three_cycles_for_one_target_day():
    rp = load("replay.json")
    assert [s["lead_day"] for s in rp["steps"]] == [5, 3, 1]
    assert len({s["init"] for s in rp["steps"]}) == 3
    assert {s["valid"] for s in rp["steps"]} == {rp["target_date"]}
    for s in rp["steps"]:
        assert sum(s["tiers"].values()) == rp["verification"]["districts_in_focus"]


def test_lightgbm_is_scored_and_selected_on_training_data():
    for variable in ("precip", "t2m", "wind"):
        name = "ladder.json" if variable == "precip" else f"ladder_{variable}.json"
        assert "lgbm_blend" in rows(load(name))
        for lead in load(f"ablation_{variable}.json")["leads"].values():
            q = lead["probabilistic"]["quantile_methods"]
            assert q["selected"] in ("table", "lgbm")
            cv = q["train_cv_pinball"]
            for year, method in q["selected_by_fold"].items():
                assert method == min(cv[year], key=cv[year].get)      # chosen by training CV
            assert set(q["test_crps_7_levels"]) == {"quantile_table", "lightgbm"}
            assert abs(sum(q["lightgbm_feature_importance"].values()) - 1.0) < 0.01
            assert lead["learned_blend"]["rmse"] > 0
