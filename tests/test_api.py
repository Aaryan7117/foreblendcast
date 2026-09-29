"""API contract tests — every endpoint the web and Android clients depend on.

These run against the real results/ directory (skipped if it has not been generated).
"""
from __future__ import annotations

import json
import math

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
pytest.importorskip("xmltodict")

from fastapi.testclient import TestClient  # noqa: E402

from api import store  # noqa: E402
from api.main import app  # noqa: E402

LEADS = store.available_lead_days()
pytestmark = pytest.mark.skipif(not LEADS, reason="results/districts_L*.json not generated")


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _no_nan(obj):
    if isinstance(obj, float):
        assert math.isfinite(obj), "NaN/Infinity leaked into JSON payload"
    elif isinstance(obj, dict):
        for v in obj.values():
            _no_nan(v)
    elif isinstance(obj, list):
        for v in obj:
            _no_nan(v)


# ── status ──────────────────────────────────────────────────────
def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["available_lead_days"] == LEADS
    assert "EXERCISE" in body["disclaimer"]


def test_leads_and_meta(client):
    assert client.get("/api/leads").json()["lead_days"] == LEADS
    meta = client.get("/api/meta", params={"lead_day": LEADS[0]}).json()
    assert meta["fixture"] is False, "frontend must never be fed fixture data silently"
    assert meta["ground_truth"] == "ERA5"


def test_summary(client):
    r = client.get("/api/summary", params={"lead_day": LEADS[0]})
    assert r.status_code == 200
    s = r.json()
    assert sum(s["counts"].values()) == s["total_districts"]
    assert s["top_districts"] and "p_gt_115p6" in s["top_districts"][0]
    assert s["valid_date"].startswith("20")
    _no_nan(s)


def test_missing_lead_day_is_404_with_hint(client):
    r = client.get("/api/districts", params={"lead_day": 42})
    assert r.status_code == 404
    assert "Available" in r.json()["detail"]


# ── districts ───────────────────────────────────────────────────
def test_districts_full_and_compact(client):
    full = client.get("/api/districts", params={"lead_day": LEADS[0]}).json()
    comp = client.get("/api/districts", params={"lead_day": LEADS[0], "compact": "true"}).json()
    assert full["count"] == comp["count"] > 700
    assert "weights" in full["districts"][0]
    assert "weights" not in comp["districts"][0]
    assert set(store.COMPACT_FIELDS) <= set(comp["districts"][0])
    assert comp["districts"][0]["dominant_model"] in ("hres", "ens", "graphcast")
    _no_nan(comp)


def test_districts_filters(client):
    red = client.get("/api/districts", params={"tier": "red", "compact": "true"}).json()
    assert all(d["tier"] == "red" for d in red["districts"])
    both = client.get("/api/districts", params={"tier": "red,orange", "compact": "true"}).json()
    assert both["count"] >= red["count"]
    q = client.get("/api/districts", params={"q": "kamrup", "compact": "true"}).json()
    assert q["count"] >= 1 and all("kamrup" in d["name"].lower() or "kamrup" in d["id"].lower() for d in q["districts"])


def test_district_lookup_variants(client):
    _, districts = store.load_districts(LEADS[0])
    d0 = districts[0]
    by_id = client.get(f"/api/district/{d0['id']}").json()
    by_name = client.get(f"/api/district/{d0['name']}").json()
    by_lower = client.get(f"/api/district/{d0['name'].lower()}").json()
    assert by_id["id"] == by_name["id"] == by_lower["id"] == d0["id"]
    assert client.get("/api/district/definitely-not-a-district").status_code == 404


def test_district_across_leads(client):
    _, districts = store.load_districts(LEADS[0])
    r = client.get(f"/api/district/{districts[0]['id']}/leads")
    assert r.status_code == 200
    assert [x["lead_day"] for x in r.json()["leads"]] == LEADS


def test_impact_cards(client):
    _, districts = store.load_districts(LEADS[0])
    r = client.get(f"/api/impact/{districts[0]['id']}")
    assert r.status_code == 200
    cards = r.json()["cards"]
    assert [c["persona"] for c in cards] == ["farmer", "fisher", "dm", "citizen"]


# ── verification products ──────────────────────────────────────
@pytest.mark.parametrize("path", ["/api/ladder", "/api/fss_curve", "/api/rev", "/api/where_we_lose"])
def test_verification_products_are_strict_json(client, path):
    r = client.get(path)
    assert r.status_code == 200
    assert "meta" in r.json()
    _no_nan(r.json())  # ladder.json contains NaN / Infinity on disk — must be sanitised


def test_points(client):
    cities = client.get("/api/points").json()["cities"]
    assert {c["slug"] for c in cities} >= {"mumbai", "delhi"}
    p = client.get("/api/points/mumbai").json()
    assert p["city"] == "Mumbai" and len(p["blend"]) == len(p["lead_days"]) > 0
    assert client.get("/api/points/atlantis").status_code == 404


# ── rasters / geometry ──────────────────────────────────────────
def test_rasters(client):
    b = client.get("/api/rasters/bounds").json()
    assert b["south"] < b["north"] and b["west"] < b["east"]
    lst = client.get("/api/rasters").json()
    assert f"precip_pm_L{LEADS[0]}.png" in lst["png"]
    png = client.get(f"/api/rasters/precip_pm_L{LEADS[0]}.png")
    assert png.status_code == 200 and png.headers["content-type"] == "image/png"
    assert client.get("/api/rasters/../secret.png").status_code in (400, 404)
    raw = client.get(f"/api/rasters/raw/{LEADS[0]}").json()
    rows, cols = raw["shape"]
    assert rows * cols == len(raw["obs"]) == len(raw["models"]["hres"])
    assert raw["row0"] == "south" and raw["bounds"]["south"] == b["south"]


def test_geometry(client):
    r = client.get("/api/geo/districts")
    assert r.status_code == 200
    g = r.json()
    assert len(g["districts"]) > 700
    d = g["districts"][0]
    assert {"id", "name", "state", "c", "rings"} <= set(d)
    assert len(d["rings"][0]) % 2 == 0 and len(d["rings"][0]) >= 8
    # every district in the forecast has geometry and vice versa
    _, districts = store.load_districts(LEADS[0])
    assert {x["id"] for x in districts} == {x["id"] for x in g["districts"]}


# ── live blend ──────────────────────────────────────────────────
def test_live_blend_matches_single_model(client):
    pytest.importorskip("numpy")
    r = client.post("/api/blend/live", json={"lead_day": LEADS[0], "weights": {"hres": 1.0, "ens": 0.0, "graphcast": 0.0}})
    assert r.status_code == 200
    body = r.json()
    assert body["weights_used"]["hres"] == pytest.approx(1.0)
    assert body["rmse_mm"] == pytest.approx(body["per_model_rmse_mm"]["hres"])
    r2 = client.post("/api/blend/live", json={"lead_day": LEADS[0], "weights": {"hres": 2, "ens": 2, "graphcast": 2}})
    assert r2.json()["weights_used"]["ens"] == pytest.approx(1 / 3)
    assert client.post("/api/blend/live", json={"lead_day": LEADS[0], "weights": {"pangu": 1}}).status_code == 400
    assert client.post("/api/blend/live", json={"lead_day": LEADS[0], "weights": {"hres": 0}}).status_code == 400


# ── alerts / CAP ────────────────────────────────────────────────
def test_alerts_json_and_cap(client):
    a = client.get("/api/alerts").json()
    assert a["status"] == "Exercise"
    assert all(x["tier"] in ("red", "orange") for x in a["alerts"])
    cap = client.get("/api/alerts/cap")
    assert cap.status_code == 200 and cap.headers["content-type"].startswith("application/xml")
    xml = cap.text
    assert 'xmlns="urn:oasis:names:tc:emergency:cap:1.2"' in xml
    assert "<status>Exercise</status>" in xml
    assert xml.count("<info>") == a["count"]


# ── SMS ─────────────────────────────────────────────────────────
def test_sms_preview_all_languages(client):
    _, districts = store.load_districts(LEADS[0])
    d = districts[0]
    for lang in store.SMS_LANGUAGES:
        r = client.get("/api/sms/preview", params={"district_id": d["id"], "language": lang})
        assert r.status_code == 200, lang
        body = r.json()
        assert d["name"] in body["text"]
        assert body["segments"] >= 1 and body["encoding"] in ("GSM-7", "UCS-2")
    assert client.get("/api/sms/preview", params={"district_id": d["id"], "language": "xx"}).status_code == 400


def test_sms_text_uses_cycle_date_not_today():
    meta = {"cycle": "2022-06-14T00Z"}
    d = {"name": "Nalbari", "tier": "red", "p_gt_115p6": 0.72, "precip_p90_mm": 180.4, "population": 771639}
    assert "15 Jun" in store.sms_text(d, "en", meta, 1)
    assert "17 Jun" in store.sms_text(d, "en", meta, 3)
    assert "[EXERCISE] RED" in store.sms_text(d, "en", meta, 1)
    assert "72%" in store.sms_text(d, "hi", meta, 1)


def test_sms_dispatch_dry_run(client, monkeypatch):
    monkeypatch.delenv("SMS_GATEWAY_URL", raising=False)
    _, districts = store.load_districts(LEADS[0])
    r = client.post("/api/sms/dispatch", json={"district_id": districts[0]["id"], "phone": "+910000000000", "language": "en", "dry_run": True})
    assert r.status_code == 200 and r.json()["delivery"] == "dry_run"
    r = client.post("/api/sms/dispatch", json={"district_id": districts[0]["id"], "phone": "+910000000000", "language": "en"})
    assert r.status_code == 200 and r.json()["delivery"] == "mock"
    assert client.post("/api/sms/dispatch", json={"district_id": "nope", "phone": "1"}).status_code == 404


def test_subscriptions_roundtrip(client, tmp_path, monkeypatch):
    monkeypatch.setattr(store, "SUBSCRIPTIONS_PATH", tmp_path / "subs.json")
    _, districts = store.load_districts(LEADS[0])
    d = districts[0]
    r = client.post("/api/subscriptions", json={"phone": "+911234567890", "district_id": d["name"], "language": "hi"})
    assert r.status_code == 200 and r.json()["district_id"] == d["id"]
    assert client.get("/api/subscriptions", params={"phone": "+911234567890"}).json()["count"] == 1
    out = client.post("/api/sms/dispatch_subscribed", params={"dry_run": "true"}).json()
    assert out["messages"] in (0, 1)  # 1 only if that district is on alert
    assert client.delete("/api/subscriptions", params={"phone": "+911234567890"}).json()["count"] == 0


# ── copilot ─────────────────────────────────────────────────────
def test_copilot_deterministic(client, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    red = client.get("/api/districts", params={"tier": "red,orange", "compact": "true"}).json()["districts"]
    name = red[0]["name"] if red else store.load_districts(LEADS[0])[1][0]["name"]

    r = client.post("/api/copilot/ask", json={"question": f"Why is {name} red?"})
    body = r.json()
    assert r.status_code == 200 and body["mode"] == "deterministic"
    assert body["intent_detected"] == "explain_tier" and body["districts_matched"] == [name]
    assert "EXERCISE" in body["disclaimer"]

    body = client.post("/api/copilot/ask", json={"question": "Show all red alert districts"}).json()
    assert body["intent_detected"] == "list_alerts" and "RED" in body["answer"]

    body = client.post("/api/copilot/ask", json={"question": "How accurate is the blend?"}).json()
    assert body["intent_detected"] == "explain_ladder" and "results/ladder.json" in body["sources"]

    body = client.post("/api/copilot/ask", json={"question": f"What should a farmer in {name} do?"}).json()
    assert body["intent_detected"] == "explain_impact" and "Farmer" in body["answer"]

    assert client.post("/api/copilot/ask", json={"question": "   "}).status_code == 400
    assert len(client.get("/api/copilot/suggestions").json()["suggestions"]) >= 2


def test_static_data_mount(client):
    r = client.get(f"/data/districts_L{LEADS[0]}.json")
    assert r.status_code == 200
    assert json.loads(r.text)["lead_day"] == LEADS[0]
