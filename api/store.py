"""Read-only access to results/ for the API.

Everything the API returns comes from files under results/ (and data/static/).
This module owns:
  * cached JSON loading (re-read when the file changes on disk)
  * district lookup (exact id / name, then substring)
  * derived views the mobile app needs (summary, compact list, impact cards)
  * SMS text generation (5 languages, forecast date derived from the cycle)

Nothing here invents numbers: every value is read from the pipeline outputs.
"""
from __future__ import annotations

import datetime as _dt
import json
import math
import re
import threading
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "results"
STATIC_DIR = ROOT / "data" / "static"
RASTERS_DIR = RESULTS_DIR / "rasters"
POINTS_DIR = RESULTS_DIR / "points"

DISCLAIMER = (
    "⚠️ EXERCISE — This is a prototype output from SIH26081 ForeBlendCast. "
    "NOT an official IMD warning."
)

# IMD 24 h rainfall categories (mm) used for the tiers
THRESHOLDS = {"heavy": 64.5, "very_heavy": 115.6, "extremely_heavy": 204.5}
TIER_ORDER = ["red", "orange", "yellow", "green"]

COMPACT_FIELDS = (
    "id", "name", "state", "tier", "precip_p90_mm",
    "p_gt_64p5", "p_gt_115p6", "p_gt_204p5",
    "population", "disagreement", "heatwave", "high_wind", "tmax_c", "wind_ms",
)

# ──────────────────────────────────────────────────────────────
#  Cached JSON loading
# ──────────────────────────────────────────────────────────────
_cache: dict[Path, tuple[float, Any]] = {}
_lock = threading.Lock()


def load_json(path: Path) -> Any | None:
    """Load a JSON file, cached by mtime. Returns None if the file is missing."""
    try:
        mtime = path.stat().st_mtime
    except FileNotFoundError:
        return None
    with _lock:
        hit = _cache.get(path)
        if hit and hit[0] == mtime:
            return hit[1]
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    with _lock:
        _cache[path] = (mtime, data)
    return data


def _sanitize(obj: Any) -> Any:
    """Replace NaN / ±Infinity with None so the payload is strict JSON.

    The ladder contains `Infinity` frequency-bias values which Python's json
    module happily writes but most mobile JSON parsers reject.
    """
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    return obj


def load_results_json(name: str) -> Any | None:
    """Load results/<name> with NaN/Infinity sanitised."""
    data = load_json(RESULTS_DIR / name)
    return _sanitize(data) if data is not None else None


# ──────────────────────────────────────────────────────────────
#  Districts
# ──────────────────────────────────────────────────────────────
def available_lead_days() -> list[int]:
    """Lead days for which results/districts_L{n}.json exists (n ≥ 1)."""
    leads = []
    for p in RESULTS_DIR.glob("districts_L*.json"):
        m = re.fullmatch(r"districts_L(\d+)\.json", p.name)
        if m and int(m.group(1)) >= 1:
            leads.append(int(m.group(1)))
    return sorted(leads)


def load_districts(lead_day: int = 1) -> tuple[dict, list[dict]]:
    """Return (meta, districts) for a lead day, or ({}, []) if missing."""
    data = load_results_json(f"districts_L{lead_day}.json")
    if not data:
        return {}, []
    return data.get("meta", {}), data.get("districts", [])


def find_district(districts: list[dict], query: str) -> Optional[dict]:
    """Exact id/name match first, then case-insensitive substring match."""
    q = (query or "").strip().lower()
    if not q:
        return None
    for d in districts:
        if d["id"].lower() == q or d["name"].lower() == q:
            return d
    for d in districts:
        if q in d["name"].lower() or q in d["id"].lower():
            return d
    return None


def compact(d: dict) -> dict:
    """Small projection of a district record for list views on mobile."""
    out = {k: d.get(k) for k in COMPACT_FIELDS}
    w = d.get("weights") or {}
    out["dominant_model"] = max(w, key=w.get) if w else None
    return out


def tier_counts(districts: list[dict]) -> dict:
    counts = {t: 0 for t in TIER_ORDER}
    pops = {t: 0 for t in TIER_ORDER}
    for d in districts:
        t = str(d.get("tier", "green")).lower()
        if t in counts:
            counts[t] += 1
            pops[t] += int(d.get("population") or 0)
    return {"counts": counts, "exposed_population": pops}


def summary(lead_day: int = 1, top_n: int = 10) -> Optional[dict]:
    meta, districts = load_districts(lead_day)
    if not districts:
        return None
    tc = tier_counts(districts)
    top = sorted(districts, key=lambda d: (d.get("p_gt_115p6") or 0, d.get("precip_p90_mm") or 0), reverse=True)
    high_dis = sorted(districts, key=lambda d: d.get("disagreement") or 0, reverse=True)
    return {
        "lead_day": lead_day,
        "cycle": meta.get("cycle"),
        "valid_date": forecast_date(meta, lead_day).isoformat(),
        "total_districts": len(districts),
        "counts": tc["counts"],
        "exposed_population": tc["exposed_population"],
        "top_districts": [compact(d) for d in top[:top_n]],
        "highest_disagreement": [compact(d) for d in high_dis[:5]],
        "available_lead_days": available_lead_days(),
        "meta": meta,
        "disclaimer": DISCLAIMER,
    }


# ──────────────────────────────────────────────────────────────
#  Dates
# ──────────────────────────────────────────────────────────────
def cycle_datetime(meta: dict) -> _dt.datetime:
    """Parse meta.cycle such as '2022-06-14T00Z'."""
    cyc = str(meta.get("cycle", "")).strip()
    for fmt in ("%Y-%m-%dT%HZ", "%Y-%m-%dT%H:%MZ", "%Y-%m-%d"):
        try:
            return _dt.datetime.strptime(cyc, fmt).replace(tzinfo=_dt.timezone.utc)
        except ValueError:
            continue
    return _dt.datetime.now(_dt.timezone.utc)


def forecast_date(meta: dict, lead_day: int) -> _dt.date:
    """The IMD day (08:30 IST → 08:30 IST) the forecast is valid for."""
    return (cycle_datetime(meta) + _dt.timedelta(days=lead_day)).date()


# ──────────────────────────────────────────────────────────────
#  Impact cards (same wording as the web ImpactCards component)
# ──────────────────────────────────────────────────────────────
def impact_cards(district: dict) -> list[dict]:
    tier = str(district.get("tier", "green")).lower()
    pop_m = (district.get("population") or 0) / 1e6
    if tier == "red":
        cards = [
            ("farmer", "Farmer", "Do not spray pesticides. Delay all sowing activities immediately. Harvest mature crops if possible."),
            ("fisher", "Fisher", "Do not venture into the sea. Secure boats in safe harbors."),
            ("dm", "District Magistrate", f"Pre-position NDRF teams. Mobilize evacuation for low-lying areas. Approx. {pop_m:.1f}M exposed."),
            ("citizen", "Citizen", "Avoid rivers and low-lying areas. Stay indoors during heavy downpours."),
        ]
    elif tier == "orange":
        cards = [
            ("farmer", "Farmer", "Postpone irrigation and fertilizer application. Check drainage in fields."),
            ("fisher", "Fisher", "Avoid deep-sea fishing. Return to coast if weather deteriorates."),
            ("dm", "District Magistrate", "Keep SDRF on standby. Alert block development officers in flood-prone zones."),
            ("citizen", "Citizen", "Avoid unnecessary travel during rain. Keep emergency kits ready."),
        ]
    else:
        cards = [
            ("farmer", "Farmer", "Normal farming activities can continue. Monitor upcoming forecasts."),
            ("fisher", "Fisher", "Normal fishing activities allowed. Carry safety equipment."),
            ("dm", "District Magistrate", "Standard operational readiness. Review district disaster management plans."),
            ("citizen", "Citizen", "Normal routine. Follow standard weather advisories."),
        ]
    return [{"persona": p, "label": label, "action": a} for p, label, a in cards]


# ──────────────────────────────────────────────────────────────
#  SMS text
# ──────────────────────────────────────────────────────────────
SMS_LANGUAGES = ("en", "hi", "te", "ta", "mr")
_MONTHS_HI = ["जन", "फ़र", "मार्च", "अप्रैल", "मई", "जून", "जुल", "अग", "सित", "अक्टू", "नव", "दिस"]


def sms_text(district: dict, language: str, meta: dict | None = None, lead_day: int = 1) -> str:
    """Build the alert SMS. All numbers come from the district record."""
    meta = meta or {}
    name = district["name"]
    tier = str(district.get("tier", "green")).upper()
    prob = int(round((district.get("p_gt_115p6") or 0) * 100))
    precip = float(district.get("precip_p90_mm") or 0)
    pop_lakh = round((district.get("population") or 0) / 1e5, 1)
    fdate = forecast_date(meta, lead_day)
    date_en = fdate.strftime("%d %b").lstrip("0")
    date_hi = f"{fdate.day} {_MONTHS_HI[fdate.month - 1]}"

    templates = {
        "en": f"[EXERCISE] {tier} Rain alert: {name}, {date_en}. {prob}% chance >115mm ({precip:.0f}mm expected). {pop_lakh}L people exposed. Avoid rivers/low areas. -SIH26081, not IMD",
        "hi": f"[अभ्यास] {tier} वर्षा चेतावनी: {name}, {date_hi}। >115mm की {prob}% संभावना ({precip:.0f}mm अनुमानित)। {pop_lakh}L जनसंख्या प्रभावित। नदी/निचले क्षेत्र से दूर रहें। -SIH26081",
        "te": f"[అభ్యాసం] {tier} వర్షం హెచ్చరిక: {name}, {date_en}. >115mm {prob}% అవకాశం ({precip:.0f}mm అంచనా). {pop_lakh}L ప్రజలు ప్రభావితం. నదులు/పల్లపు ప్రాంతాలకు దూరంగా ఉండండి. -SIH26081",
        "ta": f"[பயிற்சி] {tier} மழை எச்சரிக்கை: {name}, {date_en}. >115mm {prob}% வாய்ப்பு ({precip:.0f}mm எதிர்பார்ப்பு). {pop_lakh}L மக்கள் பாதிப்பு. ஆறுகள்/பள்ள பகுதிகளை தவிர்க்கவும். -SIH26081",
        "mr": f"[सराव] {tier} पाऊस इशारा: {name}, {date_hi}. >115mm ची {prob}% शक्यता ({precip:.0f}mm अपेक्षित). {pop_lakh}L लोक प्रभावित. नद्या/सखल भागांपासून दूर राहा. -SIH26081",
    }
    return templates.get(language, templates["en"])


def sms_segments(text: str) -> dict:
    """GSM-7 (160 chars) vs UCS-2 (70 chars) segment estimate."""
    is_ascii = all(ord(c) < 128 for c in text)
    per = 160 if is_ascii else 70
    n = len(text)
    if n <= per:
        segments = 1
    else:
        per_multi = 153 if is_ascii else 67
        segments = math.ceil(n / per_multi)
    return {"chars": n, "encoding": "GSM-7" if is_ascii else "UCS-2", "segments": segments}


# ──────────────────────────────────────────────────────────────
#  Subscriptions (demo only — JSON file next to results)
# ──────────────────────────────────────────────────────────────
SUBSCRIPTIONS_PATH = RESULTS_DIR / "subscriptions.json"
_sub_lock = threading.Lock()


def list_subscriptions() -> list[dict]:
    data = load_json(SUBSCRIPTIONS_PATH)
    return list(data) if isinstance(data, list) else []


def add_subscription(phone: str, district_id: str, language: str) -> list[dict]:
    with _sub_lock:
        subs = list_subscriptions()
        subs = [s for s in subs if not (s["phone"] == phone and s["district_id"] == district_id)]
        subs.append({
            "phone": phone,
            "district_id": district_id,
            "language": language,
            "created_utc": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        })
        SUBSCRIPTIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(SUBSCRIPTIONS_PATH, "w", encoding="utf-8") as f:
            json.dump(subs, f, indent=1, ensure_ascii=False)
        _cache.pop(SUBSCRIPTIONS_PATH, None)
        return subs


def remove_subscription(phone: str, district_id: str | None = None) -> list[dict]:
    with _sub_lock:
        subs = list_subscriptions()
        subs = [s for s in subs if not (s["phone"] == phone and (district_id is None or s["district_id"] == district_id))]
        SUBSCRIPTIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(SUBSCRIPTIONS_PATH, "w", encoding="utf-8") as f:
            json.dump(subs, f, indent=1, ensure_ascii=False)
        _cache.pop(SUBSCRIPTIONS_PATH, None)
        return subs


# ──────────────────────────────────────────────────────────────
#  Compact district geometry (for the mobile choropleth)
# ──────────────────────────────────────────────────────────────
COMPACT_GEO_PATH = STATIC_DIR / "districts_compact.json"
GEOJSON_PATH = STATIC_DIR / "districts.geojson"


def compact_geometry() -> Any | None:
    """Return data/static/districts_compact.json, building it from the GeoJSON if needed."""
    data = load_json(COMPACT_GEO_PATH)
    if data is not None:
        return data
    if not GEOJSON_PATH.exists():
        return None
    try:
        from outputs.compact_geo import build_compact  # local import: optional dependency on repo layout
        build_compact(GEOJSON_PATH, COMPACT_GEO_PATH)
    except Exception:
        return None
    return load_json(COMPACT_GEO_PATH)
