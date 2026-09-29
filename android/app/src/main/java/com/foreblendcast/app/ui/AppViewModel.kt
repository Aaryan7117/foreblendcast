package com.foreblendcast.app.ui

import android.app.Application
import android.graphics.Bitmap
import androidx.compose.runtime.Immutable
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.foreblendcast.app.ForeBlendCastApp
import com.foreblendcast.app.blend.BlendStats
import com.foreblendcast.app.blend.GridSet
import com.foreblendcast.app.blend.LiveBlend
import com.foreblendcast.app.data.DataSource
import com.foreblendcast.app.data.District
import com.foreblendcast.app.data.DistrictsResult
import com.foreblendcast.app.data.FssCurve
import com.foreblendcast.app.data.Ladder
import com.foreblendcast.app.data.LocalInsights
import com.foreblendcast.app.data.Points
import com.foreblendcast.app.data.Rev
import com.foreblendcast.app.data.Sourced
import com.foreblendcast.app.data.Tier
import com.foreblendcast.app.data.WhereWeLose
import com.foreblendcast.app.map.GeoIndex
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.FlowPreview
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.debounce
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

sealed interface UiState<out T> {
    data object Loading : UiState<Nothing>
    data class Ready<T>(val value: T) : UiState<T>
    data class Error(val message: String) : UiState<Nothing>
}

/** Which layer the home map shows. `png` is the pre-rendered raster name prefix (results/rasters). */
enum class MapLayer(val label: String, val short: String, val png: String?) {
    TIERS("District risk tiers", "Tiers", null),
    RAINFALL("Rainfall (mm, calibrated blend)", "Rain", "precip_pm"),
    EXCEEDANCE("P(rain > 115.6 mm)", "P>115", "p_gt_115p6"),
    DISAGREEMENT("Model disagreement σ", "Spread", "disagreement"),
}

@Immutable
data class LiveResult(
    val leadDay: Int,
    val weights: Map<String, Float>,
    val stats: BlendStats,
    val bitmap: Bitmap,
    val approxTiers: Map<String, Tier>,
    val approxCounts: Map<Tier, Int>,
)

@OptIn(FlowPreview::class)
class AppViewModel(app: Application) : AndroidViewModel(app) {

    val repo = (app as ForeBlendCastApp).repository
    val settings = repo.settings

    // ── navigation-ish UI state ─────────────────────────────
    val leadDay = MutableStateFlow(1)
    val layer = MutableStateFlow(MapLayer.TIERS)
    val selectedDistrictId = MutableStateFlow<String?>(null)
    val tierFilter = MutableStateFlow<Tier?>(null)
    val query = MutableStateFlow("")

    // ── data ────────────────────────────────────────────────
    private val _districts = MutableStateFlow<UiState<Sourced<DistrictsResult>>>(UiState.Loading)
    val districts: StateFlow<UiState<Sourced<DistrictsResult>>> = _districts.asStateFlow()

    private val _geo = MutableStateFlow<GeoIndex?>(null)
    val geo: StateFlow<GeoIndex?> = _geo.asStateFlow()

    private val _ladder = MutableStateFlow<UiState<Sourced<Ladder>>>(UiState.Loading)
    val ladder: StateFlow<UiState<Sourced<Ladder>>> = _ladder.asStateFlow()
    private val _fss = MutableStateFlow<UiState<Sourced<FssCurve>>>(UiState.Loading)
    val fss: StateFlow<UiState<Sourced<FssCurve>>> = _fss.asStateFlow()
    private val _rev = MutableStateFlow<UiState<Sourced<Rev>>>(UiState.Loading)
    val rev: StateFlow<UiState<Sourced<Rev>>> = _rev.asStateFlow()
    private val _wwl = MutableStateFlow<UiState<Sourced<WhereWeLose>>>(UiState.Loading)
    val wwl: StateFlow<UiState<Sourced<WhereWeLose>>> = _wwl.asStateFlow()

    val pointsCity = MutableStateFlow("mumbai")
    private val _points = MutableStateFlow<UiState<Sourced<Points>>>(UiState.Loading)
    val points: StateFlow<UiState<Sourced<Points>>> = _points.asStateFlow()

    val availableLeadDays: StateFlow<List<Int>> = MutableStateFlow(com.foreblendcast.app.data.Repository.BUNDLED_LEAD_DAYS)
    val connection = repo.connection

    // ── live blender ────────────────────────────────────────
    val blenderEnabled = MutableStateFlow(false)
    val weights = MutableStateFlow(mapOf("hres" to 0.33, "ens" to 0.33, "graphcast" to 0.34))
    private val _grid = MutableStateFlow<UiState<Sourced<GridSet>>>(UiState.Loading)
    val grid: StateFlow<UiState<Sourced<GridSet>>> = _grid.asStateFlow()
    private val _live = MutableStateFlow<LiveResult?>(null)
    val live: StateFlow<LiveResult?> = _live.asStateFlow()
    private var gridJob: Job? = null

    init {
        viewModelScope.launch { runCatching { repo.geo() }.onSuccess { _geo.value = it } }
        viewModelScope.launch { repo.checkConnection().onSuccess { h -> if (h.available_lead_days.isNotEmpty()) (availableLeadDays as MutableStateFlow).value = h.available_lead_days } }
        viewModelScope.launch { leadDay.collectLatest { loadDistricts(it) } }
        viewModelScope.launch { pointsCity.collectLatest { c -> _points.value = UiState.Loading; _points.value = load { repo.points(c) } } }
        viewModelScope.launch {
            combine(blenderEnabled, leadDay) { on, ld -> on to ld }.collectLatest { (on, ld) -> if (on) ensureGrid(ld) }
        }
        viewModelScope.launch {
            combine(weights.debounce(40), _grid, _geo, blenderEnabled) { w, g, geo, on -> Triple(w, g, geo) to on }
                .collectLatest { (t, on) ->
                    val (w, g, geoIdx) = t
                    if (!on || g !is UiState.Ready) { if (!on) _live.value = null; return@collectLatest }
                    _live.value = withContext(Dispatchers.Default) { compute(g.value.data, w, geoIdx) }
                }
        }
    }

    // ── actions ─────────────────────────────────────────────
    fun setLeadDay(day: Int) { leadDay.value = day }
    fun setLayer(l: MapLayer) { layer.value = l }
    fun selectDistrict(id: String?) { selectedDistrictId.value = id }
    fun setTierFilter(t: Tier?) { tierFilter.value = t }
    fun setQuery(q: String) { query.value = q }
    fun setPointsCity(slug: String) { pointsCity.value = slug }

    fun refresh() {
        repo.invalidate()
        _ladder.value = UiState.Loading; _fss.value = UiState.Loading; _rev.value = UiState.Loading; _wwl.value = UiState.Loading
        _grid.value = UiState.Loading
        viewModelScope.launch { repo.checkConnection() }
        viewModelScope.launch { loadDistricts(leadDay.value) }
        viewModelScope.launch { _points.value = load { repo.points(pointsCity.value) } }
        if (blenderEnabled.value) viewModelScope.launch { ensureGrid(leadDay.value) }
    }

    fun onServerUrlChanged(url: String) {
        settings.setBaseUrl(url)
        refresh()
    }

    fun ensureEvaluationLoaded() {
        if (_ladder.value is UiState.Loading) viewModelScope.launch { _ladder.value = load { repo.ladder() } }
        if (_fss.value is UiState.Loading) viewModelScope.launch { _fss.value = load { repo.fssCurve() } }
        if (_rev.value is UiState.Loading) viewModelScope.launch { _rev.value = load { repo.rev() } }
        if (_wwl.value is UiState.Loading) viewModelScope.launch { _wwl.value = load { repo.whereWeLose() } }
    }

    fun setBlenderEnabled(on: Boolean) { blenderEnabled.value = on }

    fun setWeight(model: String, value: Double) { weights.update { it + (model to value.coerceIn(0.0, 1.0)) } }

    fun setWeights(w: Map<String, Double>) { weights.value = w }

    /** Start the sliders from the pipeline's own weights for a district. */
    fun adoptDistrictWeights(d: District) { if (d.weights.isNotEmpty()) weights.value = d.weights }

    fun resetWeightsEqual() { weights.value = mapOf("hres" to 1.0 / 3, "ens" to 1.0 / 3, "graphcast" to 1.0 / 3) }

    // ── helpers ─────────────────────────────────────────────
    fun currentDistricts(): List<District> = (districts.value as? UiState.Ready)?.value?.data?.districts ?: emptyList()

    fun district(id: String?): District? = id?.let { i -> currentDistricts().firstOrNull { it.id == i } }

    fun summary(): LocalInsights.Summary? = (districts.value as? UiState.Ready)?.let { LocalInsights.summary(it.value.data.districts) }

    fun source(): DataSource? = (districts.value as? UiState.Ready)?.value?.source

    private suspend fun loadDistricts(day: Int) {
        _districts.value = UiState.Loading
        _districts.value = load { repo.districts(day) }
        // Keep the selection valid across lead days; default to the highest-risk district.
        val list = currentDistricts()
        if (list.isNotEmpty() && list.none { it.id == selectedDistrictId.value }) {
            selectedDistrictId.value = list.maxByOrNull { it.p_gt_115p6 * 1000 + it.precip_p90_mm }?.id
        }
    }

    private suspend fun ensureGrid(day: Int) {
        val ready = (_grid.value as? UiState.Ready)?.value?.data
        if (ready != null && (_live.value?.leadDay == day)) return
        _grid.value = UiState.Loading
        _grid.value = load { repo.rawGrids(day) }
    }

    private suspend fun <T> load(block: suspend () -> T): UiState<T> =
        try { UiState.Ready(block()) } catch (e: Exception) { UiState.Error(e.message ?: e.javaClass.simpleName) }

    private fun compute(grid: GridSet, w: Map<String, Double>, geo: GeoIndex?): LiveResult {
        val field = LiveBlend.blend(grid, w)
        val stats = LiveBlend.stats(field, grid)
        val px = LiveBlend.toArgb(field, grid.rows, grid.cols)
        val bmp = Bitmap.createBitmap(px, grid.cols, grid.rows, Bitmap.Config.ARGB_8888)
        val tiers = if (geo != null) LiveBlend.approximateTiers(field, grid, geo.centroids()) else emptyMap()
        val counts = Tier.entries.associateWith { t -> tiers.values.count { it == t } }
        return LiveResult(leadDay.value, LiveBlend.normalise(w, grid.models.keys), stats, bmp, tiers, counts)
    }
}
