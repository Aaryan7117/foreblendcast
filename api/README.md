# ForeBlendCast API

FastAPI service over the pipeline outputs in `results/`. It never invents forecasts: every
number comes from the JSON/PNG files the pipeline wrote, and every alert-like payload carries
the EXERCISE disclaimer.

## Run

```powershell
# Windows — uses the repo's .venv and prints the LAN URL to type into the phone app
powershell -ExecutionPolicy Bypass -File scripts/run_api.ps1

# or manually
.venv\Scripts\python.exe -m pip install -r api/requirements.txt
.venv\Scripts\python.exe -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

Interactive docs: http://localhost:8000/docs · Contract tests: `pytest tests/test_api.py`

Optional `.env` in the repo root:

| Variable | Effect |
|---|---|
| `GEMINI_API_KEY` | enables the LLM copilot mode; without it the deterministic tool router answers |
| `GEMINI_MODEL` | model id for the copilot (default `gemini-2.5-flash`) |
| `SMS_GATEWAY_URL`, `SMS_GATEWAY_KEY` | Android SMS gateway; unset ⇒ messages are only logged and the response says `delivery: mock` |

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | status, available lead days, cycle, copilot/SMS configuration |
| GET | `/api/meta?lead_day=` | provenance block of a results file |
| GET | `/api/leads` | lead days that have district files, truth-raster flag |
| GET | `/api/summary?lead_day=&top_n=` | tier counts, exposed population, top districts, valid date |
| GET | `/api/districts?lead_day=&tier=red,orange&state=&q=&compact=true` | district list (`compact` = small projection for lists) |
| GET | `/api/district/{name-or-id}?lead_day=` | one district, fuzzy match on id or name |
| GET | `/api/district/{id}/leads` | the same district across every lead day |
| GET | `/api/impact/{id}?lead_day=` | persona impact cards (farmer / fisher / DM / citizen) |
| GET | `/api/ladder`, `/api/fss_curve`, `/api/rev`, `/api/where_we_lose?lead_day=` | verification products, NaN/Infinity sanitised to null |
| GET | `/api/ladder/{precip\|t2m\|wind}`, `/api/ablation?variable=`, `/api/reliability?variable=` | per-variable ladder, ablation steps, reliability / Brier / AUC of every hazard event |
| GET | `/api/verification/summary` | headline numbers of every variable (what the dashboard quotes) |
| GET | `/api/weights/explain?lead_day=&region=&variable=` | weights of the cycle and the training RMSE behind them |
| GET | `/api/hazards/summary?lead_day=` | districts with heavy rain, heatwave or strong wind |
| GET | `/api/location/lookup?lat=&lon=` | district of a coordinate, from the district grid |
| GET | `/api/ops/feeds` | quality-gate report per model (fields checked, missing, rejected, repaired) |
| GET | `/api/points`, `/api/points/{city}` | plume data for mumbai, chennai, kolkata, delhi, guwahati |
| GET | `/api/rasters`, `/api/rasters/bounds`, `/api/rasters/{name}.png` | pre-rendered rasters such as `precip_pm_L1`, `p_gt_115p6_L3`, `truth` |
| GET | `/api/rasters/raw/{lead_day}` | per-model grids for the live re-blend (row 0 = south) |
| GET | `/api/geo/districts?compact=true` | district polygons: compact rings, or full GeoJSON with `compact=false` |
| POST | `/api/blend/live` `{lead_day, weights}` | server-side re-blend: RMSE/MAE vs ERA5, exceedance cell counts |
| GET | `/api/alerts?lead_day=` | JSON alert list (red and orange districts) |
| GET | `/api/alerts/cap?lead_day=` | CAP 1.2 XML feed, status Exercise |
| GET | `/api/sms/preview?district_id=&language=en\|hi\|te\|ta\|mr&lead_day=` | SMS text plus segment estimate |
| POST | `/api/sms/dispatch` `{district_id, phone, language, lead_day, dry_run}` | send via the gateway, or mock |
| GET / POST / DELETE | `/api/subscriptions` | demo subscriber list stored in `results/subscriptions.json` |
| POST | `/api/sms/dispatch_subscribed?lead_day=&dry_run=` | alert every subscriber in a red/orange district |
| POST | `/api/copilot/ask` `{question, lead_day}` | grounded copilot: Gemini when a key is set, else deterministic |
| GET | `/api/copilot/suggestions?lead_day=` | example questions built from the live alerts |
| GET | `/data/...` | raw `results/` files, same paths the web frontend reads |

Responses above 1 KB are gzip-compressed. CORS is open for development.

## Android app

`android/` (Kotlin + Jetpack Compose) uses these endpoints and falls back to a bundled snapshot
of `results/` when the server is unreachable. Set the base URL in the app's Settings screen:
emulator `http://10.0.2.2:8000`, real phone the LAN IP printed by `scripts/run_api.ps1`.
