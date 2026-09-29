# ForeBlendCast — Android app

Native Kotlin + Jetpack Compose client for the SIH26081 ForeBlendCast backend (`api/`).

## What it does
- **Map** — pan/zoom choropleth of all 735 districts coloured by IMD tier, with rainfall / P(>115.6 mm) / disagreement raster layers for lead days D+1, D+3, D+5; tap a district for details.
- **Districts** — searchable, filterable list (tier, state, risk / rain / exposure / spread sort).
- **District detail** — exceedance probabilities, blend weights + shrinkage, LOMO sensitivity, persona impact cards, SMS preview in 5 languages, send / subscribe, "ask copilot".
- **Blender** — forecaster override: drag model weights, the field is re-blended on the phone, RMSE vs ERA5 updates live, districts re-colour (approximate, centroid-sampled).
- **Evaluate** — verification ladder, rainfall plume per city, FSS-vs-scale, relative economic value, where-we-lose, provenance block.
- **Copilot** — grounded chat (server: Gemini or deterministic router; offline: on-device router over the snapshot).
- **Replay** — Assam–Meghalaya June 2022 case: D+5 → D+3 → D+1 → ERA5 truth.
- **Settings** — API base URL + connection test, SMS defaults, CAP 1.2 feed viewer.

Works offline from a bundled snapshot of `results/` (assets/data, lead days 1/3/5) and switches to the live API when reachable. Every screen shows a LIVE / SNAPSHOT badge and the EXERCISE banner.

## Build
Requirements: JDK 17+ (JDK 24 tested), Android SDK with platform 36. Gradle 9.3.1 wrapper, AGP 9.1.0 (built-in Kotlin), Kotlin 2.4.0.

```powershell
cd android
# local.properties: sdk.dir=C:/Users/<you>/AppData/Local/Android/Sdk   (forward slashes)
.\gradlew.bat assembleDebug testDebugUnitTest
# APK: app\build\outputs\apk\debug\app-debug.apk
adb install -r app\build\outputs\apk\debug\app-debug.apk
```

Default API URL is `http://10.0.2.2:8000` (emulator → host). For a phone on the same Wi-Fi start the API with
`powershell -File ..\scripts\run_api.ps1`, then enter the printed LAN URL in the app's Settings, or bake it in:
`.\gradlew.bat assembleDebug -PapiBaseUrl=http://192.168.1.20:8000`.

## Refresh the bundled snapshot
After re-running the pipeline copy `results/districts_L{1,3,5}.json`, `ladder.json`, `fss_curve.json`, `rev.json`,
`where_we_lose.json`, `points/*.json`, `rasters/bounds.json`, `rasters/raw_grids_L*.json` and the `*_L*.png` / `truth.png`
rasters into `app/src/main/assets/data/`, and regenerate `geo_districts.json` with `python -m outputs.compact_geo`.

## Layout
```
app/src/main/java/com/foreblendcast/app/
  data/      Models.kt (wire types), ApiClient.kt, Repository.kt (API → snapshot fallback), Settings.kt, LocalInsights.kt
  blend/     LiveBlend.kt (on-device re-blend, RMSE, colour ramp)
  map/       GeoIndex.kt (polygons + hit test), IndiaMap.kt (Compose canvas map)
  ui/        AppViewModel.kt, MainActivity.kt (nav), theme/, components/ (charts, cards, markdown), screens/
app/src/test/  JVM unit tests for blend, geometry, JSON contracts and the on-device copilot
```
