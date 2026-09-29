"""ForeBlendCast API — FastAPI service over the pipeline outputs in results/.

Run from the repository root:

    uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

Every number returned here is read from results/ (see api/store.py). The service
never invents forecasts. Every alert-like payload carries the EXERCISE disclaimer.

Endpoint groups
  /api/health, /api/meta, /api/leads, /api/summary       – status & overview
  /api/districts, /api/district/{q}, /api/impact/{q}     – district data
  /api/ladder, /api/fss_curve, /api/rev, /api/where_we_lose, /api/points[/{city}]
  /api/rasters/bounds, /api/rasters/{name}.png, /api/rasters/raw/{lead}
  /api/geo/districts                                     – district polygons
  /api/blend/live                                        – server-side re-blend
  /api/alerts, /api/alerts/cap                           – JSON + CAP 1.2 feeds
  /api/sms/preview, /api/sms/dispatch, /api/subscriptions
  /api/copilot/ask                                       – grounded copilot
  /data/...                                              – raw results files (static)
"""
from __future__ import annotations

import datetime
import math
import os
import re
from pathlib import Path
from typing import Optional

import httpx
import xmltodict
from dotenv import load_dotenv
from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from api import store
from api.store import (DISCLAIMER, RASTERS_DIR, RESULTS_DIR, SMS_LANGUAGES,
                       available_lead_days, compact, find_district,
                       load_districts, load_results_json)

load_dotenv(store.ROOT / ".env")

app = FastAPI(
    title="ForeBlendCast API",
    version="1.1.0",
    description="Calibrated multi-model rainfall blend for India — SIH26081. EXERCISE outputs only.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1024)

if RESULTS_DIR.exists():
    # Same files the web frontend reads from /data/… — lets the web app point at the API.
    app.mount("/data", StaticFiles(directory=str(RESULTS_DIR)), name="data")


# ═══════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════

def _districts_or_404(lead_day: int) -> tuple[dict, list[dict]]:
    meta, districts = load_districts(lead_day)
    if not districts:
        raise HTTPException(
            status_code=404,
            detail=f"No forecast data for lead_day={lead_day}. Available: {available_lead_days()}",
        )
    return meta, districts


def _district_or_404(query: str, lead_day: int) -> tuple[dict, dict]:
    meta, districts = _districts_or_404(lead_day)
    d = find_district(districts, query)
    if not d:
        raise HTTPException(status_code=404, detail=f"District '{query}' not found")
    return meta, d


def _results_or_404(name: str):
    data = load_results_json(name)
    if data is None:
        raise HTTPException(status_code=404, detail=f"results/{name} not available")
    return data


def _get_district_data(district_id: str, lead_day: int = 1):
    """Kept for backwards compatibility with older callers/tests."""
    _, districts = load_districts(lead_day)
    return find_district(districts, district_id) if districts else None


# ═══════════════════════════════════════════════════════════════
#  Status & overview
# ═══════════════════════════════════════════════════════════════

@app.get("/api/health")
async def health():
    leads = available_lead_days()
    meta, _ = load_districts(leads[0]) if leads else ({}, [])
    return {
        "status": "ok" if leads else "no_results",
        "service": "foreblendcast-api",
        "version": app.version,
        "results_dir": str(RESULTS_DIR),
        "available_lead_days": leads,
        "cycle": meta.get("cycle"),
        "fixture": meta.get("fixture"),
        "copilot_llm": bool(os.environ.get("XAI_API_KEY") or os.environ.get("GEMINI_API_KEY")),
        "sms_gateway_configured": bool(os.environ.get("SMS_GATEWAY_URL")),
        "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "disclaimer": DISCLAIMER,
    }


@app.get("/api/meta")
async def get_meta(lead_day: int = 1):
    meta, _ = _districts_or_404(lead_day)
    return meta


@app.get("/api/leads")
async def get_leads():
    return {
        "lead_days": available_lead_days(),
        "truth_raster_available": (RASTERS_DIR / "truth.png").exists(),
        "point_lead_days": list(range(1, 11)),
    }


@app.get("/api/summary")
async def get_summary(lead_day: int = 1, top_n: int = Query(10, ge=1, le=50)):
    s = store.summary(lead_day, top_n)
    if not s:
        raise HTTPException(status_code=404, detail=f"No forecast data for lead_day={lead_day}")
    return s


# ═══════════════════════════════════════════════════════════════
#  District data
# ═══════════════════════════════════════════════════════════════

@app.get("/api/districts")
async def list_districts(
    lead_day: int = 1,
    tier: Optional[str] = None,
    state: Optional[str] = None,
    q: Optional[str] = None,
    compact_view: bool = Query(False, alias="compact"),
):
    """List districts. `compact=true` returns the small projection used by mobile lists."""
    meta, districts = _districts_or_404(lead_day)
    if tier:
        wanted = {t.strip().lower() for t in tier.split(",")}
        districts = [d for d in districts if d["tier"].lower() in wanted]
    if state:
        districts = [d for d in districts if d.get("state", "").lower() == state.lower()]
    if q:
        ql = q.lower()
        districts = [d for d in districts if ql in d["name"].lower() or ql in d["id"].lower() or ql in d.get("state", "").lower()]
    rows = [compact(d) for d in districts] if compact_view else districts
    return {"meta": meta, "lead_day": lead_day, "count": len(rows), "districts": rows}


@app.get("/api/district/{district_query}")
async def get_district(district_query: str, lead_day: int = 1):
    """Lookup a single district by name or ID (fuzzy)."""
    _, d = _district_or_404(district_query, lead_day)
    return d


@app.get("/api/district/{district_query}/leads")
async def get_district_all_leads(district_query: str):
    """The same district across every available lead day (for the lead-time strip on mobile)."""
    out = []
    for ld in available_lead_days():
        _, districts = load_districts(ld)
        d = find_district(districts, district_query)
        if d:
            out.append({"lead_day": ld, **compact(d), "weights": d.get("weights")})
    if not out:
        raise HTTPException(status_code=404, detail=f"District '{district_query}' not found")
    return {"district": out[0]["id"], "leads": out}


@app.get("/api/impact/{district_query}")
async def get_impact(district_query: str, lead_day: int = 1):
    """Persona impact cards (farmer / fisher / DM / citizen) for a district."""
    meta, d = _district_or_404(district_query, lead_day)
    return {
        "district": compact(d),
        "valid_date": store.forecast_date(meta, lead_day).isoformat(),
        "cards": store.impact_cards(d),
        "disclaimer": DISCLAIMER,
    }


# ═══════════════════════════════════════════════════════════════
#  Verification products
# ═══════════════════════════════════════════════════════════════

@app.get("/api/ladder")
async def get_ladder():
    return _results_or_404("ladder.json")


@app.get("/api/replay")
async def get_replay():
    return _results_or_404("replay.json")


@app.get("/api/ablation")
async def get_ablation(variable: str = "precip"):
    return _results_or_404(f"ablation_{variable}.json")


@app.get("/api/reliability")
async def get_reliability(variable: str = "precip"):
    return _results_or_404(f"reliability_{variable}.json")


@app.get("/api/verification/summary")
async def get_verification_summary():
    return _results_or_404("summary.json")


@app.get("/api/ladder/{variable}")
async def get_ladder_variable(variable: str):
    return _results_or_404("ladder.json" if variable == "precip" else f"ladder_{variable}.json")


@app.get("/api/fss_curve")
async def get_fss_curve():
    return _results_or_404("fss_curve.json")


@app.get("/api/rev")
async def get_rev():
    return _results_or_404("rev.json")


@app.get("/api/where_we_lose")
async def get_where_we_lose(lead_day: Optional[int] = None):
    data = _results_or_404("where_we_lose.json")
    if lead_day is not None:
        data = {**data, "cells": [c for c in data.get("cells", []) if c.get("lead_day") == lead_day]}
    return data


@app.get("/api/points")
async def list_points():
    cities = []
    for p in sorted(store.POINTS_DIR.glob("*.json")):
        d = store.load_json(p) or {}
        cities.append({"slug": p.stem, "city": d.get("city", p.stem.title()), "lat": d.get("lat"), "lon": d.get("lon")})
    return {"cities": cities}


@app.get("/api/points/{city}")
async def get_points(city: str):
    slug = re.sub(r"[^a-z0-9_-]", "", city.lower())
    data = load_results_json(f"points/{slug}.json")
    if data is None:
        raise HTTPException(status_code=404, detail=f"No point forecast for '{city}'")
    return data


# ═══════════════════════════════════════════════════════════════
#  Rasters & geometry
# ═══════════════════════════════════════════════════════════════
_RASTER_NAME = re.compile(r"^[A-Za-z0-9_]+$")


@app.get("/api/rasters/bounds")
async def raster_bounds():
    data = store.load_json(RASTERS_DIR / "bounds.json")
    if data is None:
        raise HTTPException(status_code=404, detail="bounds.json not available")
    return data


@app.get("/api/rasters")
async def list_rasters():
    pngs = sorted(p.name for p in RASTERS_DIR.glob("*.png"))
    raws = sorted(int(m.group(1)) for p in RASTERS_DIR.glob("raw_grids_L*.json")
                  if (m := re.fullmatch(r"raw_grids_L(\d+)\.json", p.name)))
    return {"png": pngs, "raw_grid_lead_days": raws}


@app.get("/api/rasters/raw/{lead_day}")
async def raster_raw(lead_day: int):
    """Per-model gridded fields for the live re-blend (≈400 KB, gzip-compressed on the wire)."""
    data = store.load_json(RASTERS_DIR / f"raw_grids_L{lead_day}.json")
    if data is None:
        raise HTTPException(status_code=404, detail=f"raw_grids_L{lead_day}.json not available")
    bounds = store.load_json(RASTERS_DIR / "bounds.json") or {}
    return {**data, "bounds": bounds, "lead_day": lead_day, "row0": "south"}


@app.get("/api/rasters/{name}.png")
async def raster_png(name: str):
    if not _RASTER_NAME.match(name):
        raise HTTPException(status_code=400, detail="bad raster name")
    path = RASTERS_DIR / f"{name}.png"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"{name}.png not available")
    return FileResponse(path, media_type="image/png", headers={"Cache-Control": "public, max-age=3600"})


@app.get("/api/geo/districts")
async def geo_districts(compact_view: bool = Query(True, alias="compact")):
    """District polygons. compact=true → simplified rings [{id,name,state,c:[lon,lat],rings:[[x,y,...]]}]."""
    if compact_view:
        data = store.compact_geometry()
        if data is None:
            raise HTTPException(status_code=404, detail="district geometry not available")
        return JSONResponse(data, headers={"Cache-Control": "public, max-age=86400"})
    if not store.GEOJSON_PATH.exists():
        raise HTTPException(status_code=404, detail="districts.geojson not available")
    return FileResponse(store.GEOJSON_PATH, media_type="application/geo+json")


# ═══════════════════════════════════════════════════════════════
#  Live re-blend (forecaster override)
# ═══════════════════════════════════════════════════════════════

class LiveBlendRequest(BaseModel):
    lead_day: int = 1
    weights: dict[str, float] = Field(..., description="e.g. {'hres':0.5,'ens':0.3,'graphcast':0.2}; normalised server-side")


@app.post("/api/blend/live")
async def live_blend(req: LiveBlendRequest):
    """Re-blend the per-model grids with user weights. Returns RMSE vs ERA5 and exceedance cell counts.

    The mobile app does the same computation on-device; this endpoint exists so the
    numbers can be cross-checked and so thin clients can use it.
    """
    import numpy as np

    data = store.load_json(RASTERS_DIR / f"raw_grids_L{req.lead_day}.json")
    if data is None:
        raise HTTPException(status_code=404, detail=f"raw_grids_L{req.lead_day}.json not available")
    models = data["models"]
    names = [m for m in models if m in req.weights]
    if not names:
        raise HTTPException(status_code=400, detail=f"weights must name at least one of {list(models)}")
    w = np.array([max(0.0, float(req.weights[m])) for m in names])
    if w.sum() <= 0:
        raise HTTPException(status_code=400, detail="weights sum to zero")
    w = w / w.sum()

    fields = np.array([[np.nan if v is None else v for v in models[m]] for m in names], dtype=float)
    blend = np.nansum(fields * w[:, None], axis=0)
    land = np.array(data["land_mask"], dtype=bool)
    obs = np.array([np.nan if v is None else v for v in data["obs"]], dtype=float)
    valid = land & np.isfinite(obs)
    rmse = float(np.sqrt(np.mean((blend[valid] - obs[valid]) ** 2))) if valid.any() else None
    mae = float(np.mean(np.abs(blend[valid] - obs[valid]))) if valid.any() else None

    per_model_rmse = {
        m: float(np.sqrt(np.mean((fields[i][valid] - obs[valid]) ** 2))) if valid.any() else None
        for i, m in enumerate(names)
    }
    counts = {
        f"cells_gt_{k}": int(np.sum(blend[land] > thr)) for k, thr in
        (("64p5", 64.5), ("115p6", 115.6), ("204p5", 204.5))
    }
    return {
        "lead_day": req.lead_day,
        "weights_used": {m: float(x) for m, x in zip(names, w)},
        "rmse_mm": rmse,
        "mae_mm": mae,
        "per_model_rmse_mm": per_model_rmse,
        "land_cells": int(land.sum()),
        "max_blend_mm": float(np.nanmax(blend[land])) if land.any() else None,
        **counts,
        "ground_truth": "ERA5",
        "disclaimer": DISCLAIMER,
    }


# ═══════════════════════════════════════════════════════════════
#  Alerts — JSON + CAP 1.2
# ═══════════════════════════════════════════════════════════════

def _alert_rows(lead_day: int) -> tuple[dict, list[dict]]:
    meta, districts = _districts_or_404(lead_day)
    rows = [d for d in districts if d["tier"].lower() in ("red", "orange")]
    rows.sort(key=lambda d: (store.TIER_ORDER.index(d["tier"].lower()), -(d.get("p_gt_115p6") or 0)))
    return meta, rows


@app.get("/api/alerts")
async def get_alerts(lead_day: int = 1):
    meta, rows = _alert_rows(lead_day)
    return {
        "lead_day": lead_day,
        "cycle": meta.get("cycle"),
        "valid_date": store.forecast_date(meta, lead_day).isoformat(),
        "count": len(rows),
        "alerts": [
            {
                **compact(d),
                "severity": "Extreme" if d["tier"].lower() == "red" else "Severe",
                "certainty": "Likely" if (d.get("p_gt_115p6") or 0) > 0.5 else "Possible",
                "headline": f"{d['tier'].upper()} Rainfall Alert for {d['name']}",
                "instruction": "Avoid low-lying areas and river banks. Do not drive through flooded roads.",
            }
            for d in rows
        ],
        "status": "Exercise",
        "disclaimer": DISCLAIMER,
    }


@app.get("/api/alerts/cap", response_class=Response)
async def get_cap_feed(lead_day: int = 1):
    """CAP 1.2 XML feed of all Red/Orange alert districts (ingestible by NDMA SACHET)."""
    meta, alert_districts = _alert_rows(lead_day)
    now = datetime.datetime.now(datetime.timezone.utc)
    valid = store.forecast_date(meta, lead_day)
    onset = datetime.datetime.combine(valid, datetime.time(3, 0), tzinfo=datetime.timezone.utc)  # 08:30 IST
    expires = onset + datetime.timedelta(days=1)

    infos = []
    for d in alert_districts:
        tier = d["tier"].upper()
        prob = d.get("p_gt_115p6") or 0
        infos.append({
            "language": "en-IN",
            "category": "Met",
            "event": f"Heavy Rainfall ({tier} Alert)",
            "urgency": "Expected",
            "severity": "Extreme" if tier == "RED" else "Severe",
            "certainty": "Likely" if prob > 0.5 else "Possible",
            "eventCode": {"valueName": "SAME", "value": "HWA"},
            "onset": onset.isoformat(),
            "expires": expires.isoformat(),
            "senderName": "ForeBlendCast Prototype (SIH26081)",
            "headline": f"{tier} Rainfall Alert for {d['name']}, {d.get('state', '')}",
            "description": (
                f"Calibrated blend indicates {int(prob * 100)}% probability of >115.6mm rainfall in 24h "
                f"(P90 {d.get('precip_p90_mm', 0):.0f} mm). Population exposed: {int(d.get('population') or 0):,}."
            ),
            "instruction": "Avoid low-lying areas and river banks. Do not drive through flooded roads.",
            "parameter": [
                {"valueName": "p_gt_64p5", "value": str(d.get("p_gt_64p5"))},
                {"valueName": "p_gt_115p6", "value": str(d.get("p_gt_115p6"))},
                {"valueName": "p_gt_204p5", "value": str(d.get("p_gt_204p5"))},
                {"valueName": "lead_day", "value": str(lead_day)},
            ],
            "area": {
                "areaDesc": f"{d['name']}, {d.get('state', '')}",
                "geocode": {"valueName": "SIH26081_DISTRICT", "value": str(d.get("id", ""))},
            },
        })

    cap_dict = {
        "alert": {
            "@xmlns": "urn:oasis:names:tc:emergency:cap:1.2",
            "identifier": f"SIH26081-{meta.get('cycle', 'cycle')}-L{lead_day}-{int(now.timestamp())}",
            "sender": "foreblendcast@sih26081.example",
            "sent": now.isoformat(timespec="seconds"),
            "status": "Exercise",
            "msgType": "Alert",
            "scope": "Public",
            "note": DISCLAIMER,
            "info": infos,
        }
    }
    xml_data = xmltodict.unparse(cap_dict, pretty=True)
    return Response(content=xml_data, media_type="application/xml")


# ═══════════════════════════════════════════════════════════════
#  SMS
# ═══════════════════════════════════════════════════════════════

class SMSRequest(BaseModel):
    district_id: str
    phone: str
    language: str = "en"
    lead_day: int = 1
    dry_run: bool = False


def _generate_sms_text(district: dict, language: str, meta: dict | None = None, lead_day: int = 1) -> str:
    return store.sms_text(district, language, meta, lead_day)


@app.get("/api/sms/preview")
async def sms_preview(district_id: str, language: str = "en", lead_day: int = 1):
    if language not in SMS_LANGUAGES:
        raise HTTPException(status_code=400, detail=f"language must be one of {SMS_LANGUAGES}")
    meta, d = _district_or_404(district_id, lead_day)
    text = store.sms_text(d, language, meta, lead_day)
    return {"district_id": d["id"], "language": language, "text": text, **store.sms_segments(text)}


async def _send_via_gateway(phone: str, text: str) -> dict:
    """POST to an Android SMS gateway (httpSMS / SMS Gateway for Android style JSON API).

    Configure with SMS_GATEWAY_URL and SMS_GATEWAY_KEY in .env. When the URL is unset the
    message is logged only, and the response says so.
    """
    gateway_url = os.environ.get("SMS_GATEWAY_URL", "").strip()
    api_key = os.environ.get("SMS_GATEWAY_KEY", "").strip()
    if not gateway_url:
        return {"delivery": "mock", "detail": "SMS_GATEWAY_URL not configured — message logged only"}
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = api_key if api_key.lower().startswith(("bearer ", "basic ")) else f"Bearer {api_key}"
    payload = {"to": phone, "message": text, "phoneNumbers": [phone], "textMessage": {"text": text}}
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(6.0, connect=4.0)) as client:
            resp = await client.post(gateway_url, json=payload, headers=headers)
            resp.raise_for_status()
            return {"delivery": "sent", "gateway_status": resp.status_code}
    except Exception as e:  # network / gateway problems must not crash the demo
        return {"delivery": "failed", "detail": str(e)}


@app.post("/api/sms/dispatch")
async def dispatch_sms(req: SMSRequest):
    if req.language not in SMS_LANGUAGES:
        raise HTTPException(status_code=400, detail=f"language must be one of {SMS_LANGUAGES}")
    meta, district = _district_or_404(req.district_id, req.lead_day)
    text = store.sms_text(district, req.language, meta, req.lead_day)
    result = {"delivery": "dry_run"} if req.dry_run else await _send_via_gateway(req.phone, text)
    try:
        print(f"--> [SMS {result['delivery'].upper()}] To: {req.phone} | {text}")
    except UnicodeEncodeError:
        print(f"--> [SMS {result['delivery'].upper()}] To: {req.phone} | (non-ASCII text, {len(text)} chars)")
    return {
        "status": "success",
        "message": f"SMS {result['delivery']}",
        "text": text,
        "district_id": district["id"],
        "tier": district["tier"],
        **store.sms_segments(text),
        **result,
        "disclaimer": DISCLAIMER,
    }


class SubscriptionRequest(BaseModel):
    phone: str
    district_id: str
    language: str = "en"


@app.get("/api/subscriptions")
async def get_subscriptions(phone: Optional[str] = None):
    subs = store.list_subscriptions()
    if phone:
        subs = [s for s in subs if s["phone"] == phone]
    return {"count": len(subs), "subscriptions": subs}


@app.post("/api/subscriptions")
async def add_subscription(req: SubscriptionRequest):
    if req.language not in SMS_LANGUAGES:
        raise HTTPException(status_code=400, detail=f"language must be one of {SMS_LANGUAGES}")
    _, d = _district_or_404(req.district_id, available_lead_days()[0] if available_lead_days() else 1)
    subs = store.add_subscription(req.phone.strip(), d["id"], req.language)
    return {"status": "subscribed", "district_id": d["id"], "count": len(subs)}


@app.delete("/api/subscriptions")
async def delete_subscription(phone: str, district_id: Optional[str] = None):
    subs = store.remove_subscription(phone.strip(), district_id)
    return {"status": "removed", "count": len(subs)}


@app.post("/api/sms/dispatch_subscribed")
async def dispatch_subscribed(lead_day: int = 1, dry_run: bool = True):
    """Send the alert SMS to every subscriber whose district is RED/ORANGE."""
    meta, rows = _alert_rows(lead_day)
    alert_ids = {d["id"]: d for d in rows}
    sent = []
    for s in store.list_subscriptions():
        d = alert_ids.get(s["district_id"])
        if not d:
            continue
        text = store.sms_text(d, s.get("language", "en"), meta, lead_day)
        result = {"delivery": "dry_run"} if dry_run else await _send_via_gateway(s["phone"], text)
        sent.append({"phone": s["phone"], "district_id": d["id"], "tier": d["tier"], "text": text, **result})
    return {"lead_day": lead_day, "alerts": len(rows), "messages": len(sent), "sent": sent, "disclaimer": DISCLAIMER}


# ═══════════════════════════════════════════════════════════════
#  Grounded Forecaster Copilot
#  Deterministic tool-router (always available) + optional Gemini
#  mode. Both ONLY report numbers read from results/.
# ═══════════════════════════════════════════════════════════════

class CopilotRequest(BaseModel):
    question: str
    lead_day: int = 1


def _extract_district_names(question: str, districts: list) -> list:
    q_lower = question.lower()
    found = []
    for d in sorted(districts, key=lambda d: len(d["name"]), reverse=True):
        if d["name"].lower() in q_lower:
            found.append(d)
            q_lower = q_lower.replace(d["name"].lower(), "")
    return found


def _detect_intent(question: str) -> str:
    q = question.lower()
    if any(w in q for w in ["list", "show", "all", "which", "how many", "count"]) and any(w in q for w in ["red", "orange", "alert", "warning", "danger"]):
        return "list_alerts"
    if any(w in q for w in ["why", "reason", "how come", "explain"]) and any(w in q for w in ["red", "orange", "alert", "warning", "tier"]):
        return "explain_tier"
    if any(w in q for w in ["tier", "alert", "level", "status", "color", "colour"]):
        return "check_tier"
    if any(w in q for w in ["verification", "ladder", "skill", "rmse", "mae", "fss", "accuracy", "accurate", "how good", "how well", "performance"]):
        return "explain_ladder"
    if any(w in q for w in ["disagree", "spread", "uncertain", "confidence", "trust"]):
        return "explain_disagreement"
    if any(w in q for w in ["lomo", "leave-one", "leave one", "sensitivity", "remove", "without", "drop"]):
        return "explain_lomo"
    if any(w in q for w in ["weight", "blend", "model", "contribution", "dominant", "important"]):
        return "explain_weights"
    if any(w in q for w in ["probability", "chance", "likelihood", "prob", "how likely"]):
        return "explain_probability"
    if any(w in q for w in ["population", "people", "exposed", "vulnerability"]):
        return "explain_population"
    if any(w in q for w in ["impact", "farmer", "fisher", "what should", "advice", "do i"]):
        return "explain_impact"
    if any(w in q for w in ["rain", "rainfall", "precipitation", "mm", "how much"]):
        return "explain_rainfall"
    return "district_summary"


def _fmt_pct(x) -> str:
    return f"{(x or 0) * 100:.1f}%"


def _answer_explain_tier(d: dict) -> str:
    lines = [f"**{d['name']}** is at **{d['tier'].upper()}** alert level. Here is why, based on the blend results:\n"]
    lines.append(f"• **P(rain > 115.6mm)** = {_fmt_pct(d['p_gt_115p6'])} — calibrated probability of very heavy rainfall.")
    lines.append(f"• **P(rain > 64.5mm)** = {_fmt_pct(d['p_gt_64p5'])} — probability of heavy rainfall.")
    lines.append(f"• **P(rain > 204.5mm)** = {_fmt_pct(d['p_gt_204p5'])} — probability of extremely heavy rainfall.")
    lines.append(f"• **Expected precip (P90)** = {d['precip_p90_mm']:.1f} mm in the next 24h.")
    w = d["weights"]
    lines.append(f"\n**Blend weights**: HRES={_fmt_pct(w.get('hres'))}, ENS={_fmt_pct(w.get('ens'))}, GraphCast={_fmt_pct(w.get('graphcast'))}.")
    lomo = d["lomo_rmse_increase_pct"]
    dom = max(lomo, key=lambda k: lomo[k])
    lines.append(f"\n**LOMO sensitivity**: removing **{dom.upper()}** changes RMSE by {lomo[dom]:+.1f}% — the most critical model here.")
    dis = d["disagreement"]
    lines.append(f"\n**Model disagreement (σ)** = {dis:.3f}. " + ("High disagreement — significant uncertainty between models." if dis > 5 else "Models are in reasonable agreement."))
    return "\n".join(lines)


def _answer_explain_weights(d: dict) -> str:
    lines = [f"**Blend weights for {d['name']}:**\n"]
    for model, weight in sorted(d["weights"].items(), key=lambda x: x[1], reverse=True):
        lines.append(f"• **{model.upper()}**: {weight * 100:.1f}% {'█' * int(weight * 20)}")
    sh = d.get("shrinkage", {})
    lines.append(f"\n**Shrinkage**: level used = {sh.get('level_used', 'N/A')}, effective sample size = {sh.get('n_eff', 'N/A')}. Reason: {sh.get('reason', 'N/A')}")
    return "\n".join(lines)


def _answer_explain_lomo(d: dict) -> str:
    lomo = d["lomo_rmse_increase_pct"]
    lines = [f"**Leave-One-Model-Out (LOMO) analysis for {d['name']}:**\n", "RMSE change when each model is removed from the blend:\n"]
    for model, pct in sorted(lomo.items(), key=lambda x: x[1], reverse=True):
        emoji = "🔴" if pct > 5 else "🟡" if pct > 0 else "🟢"
        lines.append(f"• {emoji} Remove **{model.upper()}**: RMSE changes by **{pct:+.1f}%**")
    dom = max(lomo, key=lambda k: lomo[k])
    lines.append(f"\n→ **{dom.upper()}** is the most valuable model for {d['name']}.")
    return "\n".join(lines)


def _answer_explain_probability(d: dict) -> str:
    return "\n".join([
        f"**Exceedance probabilities for {d['name']}:**\n",
        f"• P(rain > 64.5mm in 24h) = **{_fmt_pct(d['p_gt_64p5'])}** (Heavy)",
        f"• P(rain > 115.6mm in 24h) = **{_fmt_pct(d['p_gt_115p6'])}** (Very heavy)",
        f"• P(rain > 204.5mm in 24h) = **{_fmt_pct(d['p_gt_204p5'])}** (Extremely heavy)",
        "\nThese are calibrated, probability-matched values from the blended forecast, not raw model output.",
    ])


def _answer_explain_population(d: dict) -> str:
    pop = d["population"]
    lines = [f"**Exposure data for {d['name']}:**\n", f"• Population: **{pop:,}** ({pop / 1e6:.1f}M)",
             f"• Source: {d.get('population_source', 'WorldPop')}", f"• Alert tier: **{d['tier'].upper()}**"]
    if d["tier"] in ("red", "orange"):
        lines.append(f"\n→ With {pop / 1e6:.1f}M people in a {d['tier'].upper()} zone, NDRF/SDRF pre-positioning is recommended.")
    return "\n".join(lines)


def _answer_explain_disagreement(d: dict) -> str:
    v = d["disagreement"]
    level = "**very high**" if v > 15 else "**moderate**" if v > 5 else "**low**"
    w = d["weights"]
    return "\n".join([
        f"**Model disagreement for {d['name']}:** σ = **{v:.3f}**\n",
        f"This is {level} disagreement between the models for this district.",
        f"\nCurrent blend relies most heavily on **{max(w, key=w.get).upper()}** ({max(w.values()) * 100:.1f}%).",
    ])


def _answer_explain_impact(d: dict) -> str:
    lines = [f"**What {d['tier'].upper()} means for {d['name']}:**\n"]
    for c in store.impact_cards(d):
        lines.append(f"• **{c['label']}**: {c['action']}")
    return "\n".join(lines)


def _answer_list_alerts(districts: list) -> str:
    red = [d for d in districts if d["tier"] == "red"]
    orange = [d for d in districts if d["tier"] == "orange"]
    lines = [f"**Alert summary:** {len(red)} RED, {len(orange)} ORANGE districts.\n"]
    if red:
        lines.append("**🔴 RED Alert Districts:**")
        lines += [f"  • {d['name']}, {d['state']} — P(>115mm)={(d['p_gt_115p6'] or 0) * 100:.0f}%, Pop={d['population'] / 1e6:.1f}M" for d in red]
    if orange:
        lines.append("\n**🟠 ORANGE Alert Districts:**")
        lines += [f"  • {d['name']}, {d['state']} — P(>115mm)={(d['p_gt_115p6'] or 0) * 100:.0f}%, Pop={d['population'] / 1e6:.1f}M" for d in orange]
    total_pop = sum(d["population"] for d in red + orange)
    lines.append(f"\n**Total exposed population: {total_pop:,} ({total_pop / 1e6:.1f}M)**")
    return "\n".join(lines)


def _answer_explain_ladder(lead_day: int = 1) -> str:
    data = load_results_json("ladder.json")
    if not data:
        return "Verification ladder data not available."
    key = f"L{lead_day}" if any(f"L{lead_day}" in r.get("metrics", {}) for r in data.get("rows", [])) else "L1"
    lines = [f"**Verification Ladder (Lead Day {key[1:]}):**\n", "| Rung | Strategy | RMSE | MAE | FSS@50km |", "|------|----------|------|-----|----------|"]

    def f(x):
        return "N/A" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.3f}"

    for row in data.get("rows", []):
        m = row.get("metrics", {}).get(key, {})
        lines.append(f"| {row['rung']} | {row['strategy']} | {f(m.get('rmse'))} | {f(m.get('mae'))} | {f(m.get('fss50'))} |")
    lines.append("\n→ Lower RMSE/MAE is better. Higher FSS is better. Ground truth: ERA5.")
    return "\n".join(lines)


def _answer_rainfall(d: dict) -> str:
    return "\n".join([
        f"**Rainfall forecast for {d['name']}:**\n",
        f"• Expected precipitation (P90): **{d['precip_p90_mm']:.1f} mm** in the next 24 hours.",
        f"• Alert tier: **{d['tier'].upper()}**",
        f"• Probability of heavy rain (>64.5mm): **{_fmt_pct(d['p_gt_64p5'])}**",
        f"• Probability of very heavy rain (>115.6mm): **{_fmt_pct(d['p_gt_115p6'])}**",
    ])


def _answer_district_summary(d: dict) -> str:
    w = d["weights"]
    lomo = d["lomo_rmse_increase_pct"]
    dom = max(lomo, key=lambda k: lomo[k])
    return "\n".join([
        f"**Forecast summary for {d['name']}, {d['state']}:**\n",
        f"• Alert tier: **{d['tier'].upper()}**",
        f"• Precip P90: **{d['precip_p90_mm']:.1f} mm**",
        f"• P(>64.5mm): {_fmt_pct(d['p_gt_64p5'])}  |  P(>115.6mm): {_fmt_pct(d['p_gt_115p6'])}  |  P(>204.5mm): {_fmt_pct(d['p_gt_204p5'])}",
        f"• Population: {d['population']:,}",
        f"• Blend weights: HRES={_fmt_pct(w.get('hres'))}, ENS={_fmt_pct(w.get('ens'))}, GC={_fmt_pct(w.get('graphcast'))}",
        f"• Disagreement σ: {d['disagreement']:.3f}",
        f"• Most critical model (LOMO): **{dom.upper()}** ({lomo[dom]:+.1f}% RMSE on removal)",
    ])


def deterministic_copilot(question: str, lead_day: int = 1) -> dict:
    meta, districts = load_districts(lead_day)
    if not districts:
        return {"answer": "No forecast data available.", "disclaimer": DISCLAIMER, "sources": [],
                "intent_detected": None, "districts_matched": [], "mode": "deterministic"}
    intent = _detect_intent(question)
    mentioned = _extract_district_names(question, districts)
    sources = [f"results/districts_L{lead_day}.json"]

    if intent == "list_alerts":
        answer = _answer_list_alerts(districts)
    elif intent == "explain_ladder":
        answer = _answer_explain_ladder(lead_day)
        sources.append("results/ladder.json")
    elif not mentioned:
        tc = store.tier_counts(districts)["counts"]
        answer = (
            "I could not identify a specific district in your question. "
            f"Currently there are **{tc['red']} RED** and **{tc['orange']} ORANGE** alert districts for Lead Day {lead_day}.\n\n"
            "Try asking about a specific district, e.g.:\n"
            "• \"Why is Nalbari red?\"\n• \"What are the blend weights for Kamrup?\"\n"
            "• \"Show all red alert districts\"\n• \"How accurate is the blend?\""
        )
    else:
        d = mentioned[0]
        answer = {
            "explain_tier": _answer_explain_tier,
            "check_tier": _answer_explain_tier,
            "explain_weights": _answer_explain_weights,
            "explain_lomo": _answer_explain_lomo,
            "explain_probability": _answer_explain_probability,
            "explain_population": _answer_explain_population,
            "explain_disagreement": _answer_explain_disagreement,
            "explain_impact": _answer_explain_impact,
            "explain_rainfall": _answer_rainfall,
        }.get(intent, _answer_district_summary)(d)

    return {
        "answer": answer,
        "disclaimer": DISCLAIMER,
        "sources": sources,
        "intent_detected": intent,
        "districts_matched": [d["name"] for d in mentioned],
        "mode": "deterministic",
    }


@app.post("/api/copilot/ask")
async def copilot_ask(req: CopilotRequest):
    """Grounded Forecaster Copilot. Gemini mode when GEMINI_API_KEY is set, else deterministic."""
    question = (req.question or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="question is required")
    if os.environ.get("XAI_API_KEY") or os.environ.get("GEMINI_API_KEY"):
        try:
            from api.copilot import ask_copilot
            result = await ask_copilot(question, req.lead_day)
            if result is not None:
                result.setdefault("intent_detected", None)
                result.setdefault("districts_matched", [])
                return result
        except Exception as e:  # never let the LLM path break the demo
            print(f"[Copilot] Gemini mode failed: {e}; falling back to deterministic")
    return deterministic_copilot(question, req.lead_day)


@app.get("/api/copilot/suggestions")
async def copilot_suggestions(lead_day: int = 1):
    """Example questions built from the districts that are actually on alert."""
    meta, districts = load_districts(lead_day)
    alerts = sorted([d for d in districts if d["tier"] in ("red", "orange")], key=lambda d: -(d.get("p_gt_115p6") or 0))
    names = [d["name"] for d in alerts[:4]] or [d["name"] for d in districts[:2]]
    qs = ["Show all red alert districts", "How accurate is the blend?"]
    templates = ["Why is {} {}?", "What are the blend weights for {}?", "LOMO sensitivity for {}", "How many people are exposed in {}?"]
    for i, n in enumerate(names):
        d = next(x for x in alerts if x["name"] == n) if alerts else None
        t = templates[i % len(templates)]
        qs.append(t.format(n, d["tier"]) if t.count("{}") == 2 else t.format(n))
    return {"suggestions": qs[:8]}


# ═══════════════════════════════════════════════════════════════
#  Crowdsourced Ground Truth & Flood Observations (VGI)
# ═══════════════════════════════════════════════════════════════
@app.get("/api/crowdsource/reports")
async def get_crowdsourced_reports(
    district_id: Optional[str] = None,
    hazard_type: Optional[str] = None,
):
    from api import crowdsource
    reports = crowdsource.load_reports()
    if district_id:
        did = district_id.strip().upper()
        reports = [r for r in reports if did in r.get("district_id", "").upper() or did in r.get("district_name", "").upper()]
    if hazard_type:
        reports = [r for r in reports if r.get("hazard_type") == hazard_type]
    
    verified_count = sum(1 for r in reports if r.get("verified_by_ndrf"))
    avg_depth = [r["water_depth_cm"] for r in reports if r.get("water_depth_cm") is not None]
    avg_water_depth = sum(avg_depth) / max(1, len(avg_depth)) if avg_depth else 0.0
    return {
        "count": len(reports),
        "verified_by_ndrf_count": verified_count,
        "average_reported_depth_cm": round(avg_water_depth, 1),
        "reports": reports,
    }


@app.post("/api/crowdsource/report")
async def submit_crowdsourced_report(report: dict = Body(...)):
    from api import crowdsource
    obs = crowdsource.ObservationReport(**report)
    entry = crowdsource.add_report(obs)
    return {"status": "ok", "message": "Ground observation logged successfully", "report": entry}


# ═══════════════════════════════════════════════════════════════
#  Operational Telemetry & Data Feeds Status
# ═══════════════════════════════════════════════════════════════
@app.get("/api/ops/feeds")
async def get_ops_feeds():
    from api import ops
    return ops.get_data_feeds_status()


# ═══════════════════════════════════════════════════════════════
#  "Why These Weights?" Multi-Factor Attribution
# ═══════════════════════════════════════════════════════════════
@app.get("/api/weights/explain")
async def get_weights_explanation(lead_day: int = 1, region: Optional[str] = None,
                                  variable: str = "precip"):
    from api import ops
    return ops.explain_weights(lead_day, region, variable)


# ═══════════════════════════════════════════════════════════════
#  Forecaster Bulletin Sign-Off & Official Review
# ═══════════════════════════════════════════════════════════════
@app.post("/api/bulletin/signoff")
async def sign_off_bulletin(req: dict = Body(...)):
    from api import ops
    sign_req = ops.BulletinSignOffRequest(**req)
    bulletin = ops.sign_off_bulletin(sign_req)
    return {"status": "ok", "message": "Official forecaster bulletin signed and published", "bulletin": bulletin}


@app.get("/api/bulletins")
async def list_bulletins():
    from api import ops
    return {"bulletins": ops.load_bulletins()}


# ═══════════════════════════════════════════════════════════════
#  Triple-Hazard Summary & "Mera Sthan" Geolocation
# ═══════════════════════════════════════════════════════════════
@app.get("/api/hazards/summary")
async def get_hazards_summary(lead_day: int = 1):
    meta, districts = _districts_or_404(lead_day)
    heavy_rain = [d for d in districts if d.get("tier") in ("red", "orange")]
    heatwave = [d for d in districts if d.get("heatwave")]
    high_wind = [d for d in districts if d.get("high_wind")]
    multi = sorted((d for d in districts
                    if d.get("tier") in ("red", "orange") or d.get("heatwave") or d.get("high_wind")),
                   key=lambda d: -(d.get("p_gt_115p6") or 0))
    
    return {
        "lead_day": lead_day,
        "cycle": meta.get("cycle"),
        "multi_hazard_active": bool(heavy_rain or heatwave or high_wind),
        "hazard_definitions": meta.get("hazard_definitions", {}),
        "temperature_definition": meta.get("temperature_definition"),
        "heavy_rain_districts": len(heavy_rain),
        "heatwave_districts": len(heatwave),
        "high_wind_districts": len(high_wind),
        "multi_hazard_districts": [
            {
                "id": d["id"],
                "name": d["name"],
                "state": d["state"],
                "tier": d["tier"],
                "precip_mm": d.get("precip_p90_mm", 0),
                "tmax_c": d.get("tmax_c"),
                "wind_kmh": round(d["wind_ms"] * 3.6, 1) if d.get("wind_ms") is not None else None,
                "p_heatwave": d.get("p_heatwave"),
                "p_wind_8": d.get("p_wind_8"),
                "hazards": [
                    *(["Heavy Rain"] if d.get("tier") in ("red", "orange") else []),
                    *(["Heatwave"] if d.get("heatwave") else []),
                    *(["Strong Wind"] if d.get("high_wind") else []),
                ]
            }
            for d in multi[:15]
        ]
    }


@app.get("/api/location/lookup")
async def location_lookup(lat: float = Query(...), lon: float = Query(...), lead_day: int = 1):
    """Mera Sthan / GPS Geolocation: Resolves coordinates to nearest district and returns localized forecast."""
    meta, districts = _districts_or_404(lead_day)
    
    from api import ops
    matched = ops.find_nearest_district(lat, lon, districts)
    if not matched:
        raise HTTPException(status_code=404, detail="Location is outside the forecast districts")

    d = matched
    tier = d.get("tier", "green")
    hindi_tiers = {
        "red": "लाल चेतावनी (अत्यधिक भारी वर्षा)",
        "orange": "नारंगी चेतावनी (भारी वर्षा)",
        "yellow": "पीली चेतावनी (सतर्क रहें)",
        "green": "हरा संकेत (सामान्य मौसम)"
    }
    
    return {
        "location": {"latitude": lat, "longitude": lon},
        "district": d["id"],
        "name": d["name"],
        "state": d["state"],
        "lead_day": lead_day,
        "valid_date": store.forecast_date(meta, lead_day).isoformat(),
        "tier": tier,
        "tier_label_en": tier.upper() + " WARNING",
        "tier_label_hi": hindi_tiers.get(tier, "सामान्य"),
        "rainfall_p90_mm": d.get("precip_p90_mm", 0.0),
        "prob_heavy_rain_pct": round((d.get("p_gt_115p6") or 0.0) * 100, 1),
        "temperature_c": d.get("tmax_c"),
        "temperature_definition": meta.get("temperature_definition"),
        "wind_speed_kmh": round(d["wind_ms"] * 3.6, 1) if d.get("wind_ms") is not None else None,
        "heatwave": bool(d.get("heatwave")),
        "high_wind": bool(d.get("high_wind")),
        "disclaimer": DISCLAIMER,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)

