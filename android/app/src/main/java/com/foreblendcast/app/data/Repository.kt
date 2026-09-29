package com.foreblendcast.app.data

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import com.foreblendcast.app.blend.GridSet
import com.foreblendcast.app.map.GeoIndex
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import kotlinx.serialization.KSerializer
import kotlinx.serialization.builtins.serializer
import java.io.IOException
import java.util.concurrent.ConcurrentHashMap

/**
 * Single source of data for the UI.
 *
 * Policy: try the API first, fall back to the snapshot bundled under assets/data/ (a copy of
 * results/ at build time). Each answer is tagged LIVE or SNAPSHOT so screens can show the badge.
 * Bundled assets exist for every lead day the pipeline produces (1, 3, 5, 7, 9). They are
 * refreshed from results/ with `python scripts/sync_android_assets.py`.
 */
class Repository(private val context: Context, val settings: Settings) {

    val api = ApiClient { settings.baseUrl.value }

    private val cache = ConcurrentHashMap<String, Sourced<Any>>()
    private val locks = ConcurrentHashMap<String, Mutex>()

    private val _connection = MutableStateFlow<Health?>(null)
    val connection: StateFlow<Health?> = _connection

    private val _lastError = MutableStateFlow<String?>(null)
    val lastError: StateFlow<String?> = _lastError

    /** Drop cached payloads (used when the server URL changes or on pull-to-refresh). */
    fun invalidate() {
        cache.clear()
        geoIndex = null
    }

    // ── connection ────────────────────────────────────────────
    suspend fun checkConnection(): Result<Health> = runCatching {
        api.get("/api/health", Health.serializer())
    }.onSuccess { _connection.value = it; _lastError.value = null }
        .onFailure { _connection.value = null; _lastError.value = it.message }

    // ── core products ─────────────────────────────────────────
    suspend fun districts(leadDay: Int): Sourced<DistrictsResult> =
        cached("districts_L$leadDay", "/api/districts?lead_day=$leadDay", "data/districts_L$leadDay.json", DistrictsResult.serializer())

    suspend fun ladder(): Sourced<Ladder> = cached("ladder", "/api/ladder", "data/ladder.json", Ladder.serializer())
    suspend fun fssCurve(): Sourced<FssCurve> = cached("fss", "/api/fss_curve", "data/fss_curve.json", FssCurve.serializer())
    suspend fun rev(): Sourced<Rev> = cached("rev", "/api/rev", "data/rev.json", Rev.serializer())
    suspend fun replay(): Sourced<Replay> = cached("replay", "/api/replay", "data/replay.json", Replay.serializer())
    suspend fun whereWeLose(): Sourced<WhereWeLose> = cached("wwl", "/api/where_we_lose", "data/where_we_lose.json", WhereWeLose.serializer())
    suspend fun points(city: String): Sourced<Points> = cached("points_$city", "/api/points/$city", "data/points/$city.json", Points.serializer())
    suspend fun bounds(): Sourced<Bounds> = cached("bounds", "/api/rasters/bounds", "data/rasters/bounds.json", Bounds.serializer())

    suspend fun rawGrids(leadDay: Int): Sourced<GridSet> {
        val key = "grid_L$leadDay"
        @Suppress("UNCHECKED_CAST")
        cache[key]?.let { return it as Sourced<GridSet> }
        val raw = cached("raw_L$leadDay", "/api/rasters/raw/$leadDay", "data/rasters/raw_grids_L$leadDay.json", RawGrids.serializer())
        val b = raw.data.bounds ?: bounds().data
        val grid = withContext(Dispatchers.Default) { GridSet.from(raw.data, b) }
        val out = Sourced(grid, raw.source, raw.error)
        @Suppress("UNCHECKED_CAST")
        cache[key] = out as Sourced<Any>
        return out
    }

    /** District outlines always come from the bundled asset (735 districts, ~780 KB). */
    @Volatile private var geoIndex: GeoIndex? = null
    private val geoLock = Mutex()

    suspend fun geo(): GeoIndex {
        geoIndex?.let { return it }
        return geoLock.withLock {
            geoIndex ?: withContext(Dispatchers.Default) {
                val text = readAsset("data/geo_districts.json")
                GeoIndex.from(api.json.decodeFromString(GeoCompact.serializer(), text))
            }.also { geoIndex = it }
        }
    }

    /** Pre-rendered raster PNG (precip_pm, p_gt_115p6, disagreement, truth …), live then bundled. */
    suspend fun rasterBitmap(name: String): Sourced<Bitmap>? {
        val key = "png_$name"
        @Suppress("UNCHECKED_CAST")
        cache[key]?.let { return it as Sourced<Bitmap> }
        val live = runCatching { api.getBytes("/api/rasters/$name.png") }.getOrNull()
        val bytes = live ?: runCatching { withContext(Dispatchers.IO) { context.assets.open("data/rasters/$name.png").use { it.readBytes() } } }.getOrNull()
            ?: return null
        val bmp = withContext(Dispatchers.Default) { BitmapFactory.decodeByteArray(bytes, 0, bytes.size) } ?: return null
        val out = Sourced(bmp, if (live != null) DataSource.LIVE else DataSource.SNAPSHOT)
        @Suppress("UNCHECKED_CAST")
        cache[key] = out as Sourced<Any>
        return out
    }

    // ── live-only endpoints ───────────────────────────────────
    suspend fun districtLeads(id: String): DistrictLeads = api.get("/api/district/$id/leads", DistrictLeads.serializer())

    suspend fun alerts(leadDay: Int): AlertsResponse = api.get("/api/alerts?lead_day=$leadDay", AlertsResponse.serializer())

    suspend fun copilot(question: String, leadDay: Int): CopilotResponse =
        api.post("/api/copilot/ask", CopilotRequest(question, leadDay), CopilotRequest.serializer(), CopilotResponse.serializer())

    suspend fun copilotSuggestions(leadDay: Int): List<String> =
        runCatching { api.get("/api/copilot/suggestions?lead_day=$leadDay", CopilotSuggestions.serializer()).suggestions }.getOrDefault(emptyList())

    suspend fun smsPreview(districtId: String, language: String, leadDay: Int): SmsPreview =
        api.get("/api/sms/preview?district_id=${enc(districtId)}&language=$language&lead_day=$leadDay", SmsPreview.serializer())

    suspend fun smsDispatch(req: SmsDispatchRequest): SmsDispatchResponse =
        api.post("/api/sms/dispatch", req, SmsDispatchRequest.serializer(), SmsDispatchResponse.serializer())

    suspend fun subscribe(req: SubscriptionRequest): SubscriptionResponse =
        api.post("/api/subscriptions", req, SubscriptionRequest.serializer(), SubscriptionResponse.serializer())

    suspend fun liveBlendServer(leadDay: Int, weights: Map<String, Double>): LiveBlendResponse =
        api.post("/api/blend/live", LiveBlendRequest(leadDay, weights), LiveBlendRequest.serializer(), LiveBlendResponse.serializer())

    suspend fun capFeedXml(leadDay: Int): String = api.getText("/api/alerts/cap?lead_day=$leadDay")

    fun capFeedUrl(leadDay: Int): String = api.url("/api/alerts/cap?lead_day=$leadDay")

    // ── internals ─────────────────────────────────────────────
    private suspend fun <T : Any> cached(key: String, apiPath: String, assetPath: String, serializer: KSerializer<T>): Sourced<T> {
        @Suppress("UNCHECKED_CAST")
        cache[key]?.let { return it as Sourced<T> }
        val lock = locks.getOrPut(key) { Mutex() }
        return lock.withLock {
            @Suppress("UNCHECKED_CAST")
            cache[key]?.let { return it as Sourced<T> }
            val result = fetch(apiPath, assetPath, serializer)
            @Suppress("UNCHECKED_CAST")
            cache[key] = result as Sourced<Any>
            result
        }
    }

    private suspend fun <T : Any> fetch(apiPath: String, assetPath: String, serializer: KSerializer<T>): Sourced<T> {
        val liveError: String? = try {
            val data = api.get(apiPath, serializer)
            _lastError.value = null
            return Sourced(data, DataSource.LIVE)
        } catch (e: Exception) {
            e.message ?: e.javaClass.simpleName
        }
        _lastError.value = liveError
        val text = try {
            readAsset(assetPath)
        } catch (e: IOException) {
            throw IOException("API unreachable ($liveError) and no bundled snapshot for $assetPath")
        }
        val data = withContext(Dispatchers.Default) { api.json.decodeFromString(serializer, text) }
        return Sourced(data, DataSource.SNAPSHOT, liveError)
    }

    private suspend fun readAsset(path: String): String = withContext(Dispatchers.IO) {
        context.assets.open(path).bufferedReader(Charsets.UTF_8).use { it.readText() }
    }

    private fun enc(s: String) = java.net.URLEncoder.encode(s, "UTF-8")

    companion object {
        val BUNDLED_LEAD_DAYS = listOf(1, 3, 5, 7, 9)
        val CITIES = listOf("mumbai" to "Mumbai", "chennai" to "Chennai", "kolkata" to "Kolkata", "delhi" to "Delhi", "guwahati" to "Guwahati")
    }
}

@Suppress("unused")
private val StringSerializer = String.serializer()
