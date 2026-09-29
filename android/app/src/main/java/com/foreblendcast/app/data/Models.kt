package com.foreblendcast.app.data

import kotlinx.serialization.Serializable

/*
 * Wire models. Field names match the JSON emitted by the pipeline (the results directory JSON) and the
 * FastAPI service (api/main.py) exactly, so the same classes parse both the bundled snapshot
 * and live responses. Every field has a default so partial / compact payloads still parse.
 */

@Serializable
data class Meta(
    val cycle: String = "",
    val generated_utc: String = "",
    val git_commit: String = "",
    val fixture: Boolean = false,
    val ground_truth: String = "",
    val models_used: List<String> = emptyList(),
    val availability_pattern: String = "",
    val strategy: String = "",
    val accumulation_window_utc: String = "",
    val district_aggregation: String = "",
    val status: String = "",
    val ground_truth_detail: String = "",
    val train_years: List<Int> = emptyList(),
    val season: String = "",
    val temperature_definition: String = "",
    val tier_probability_thresholds: Map<String, Double> = emptyMap(),
)

@Serializable
data class Shrinkage(
    val level_used: String = "",
    val n_eff: Double = 0.0,
    val reason: String = "",
    val lambda: Double? = null,
)

@Serializable
data class District(
    val id: String,
    val name: String,
    val state: String = "",
    val precip_p90_mm: Double = 0.0,
    val region: String = "",
    /** 2 m temperature at 12 UTC (17:30 IST): a proxy for the daily maximum. */
    val tmax_c: Double? = null,
    val t2m_anomaly_c: Double? = null,
    val wind_ms: Double? = null,
    val p_hot_40: Double? = null,
    val p_heatwave: Double? = null,
    val p_wind_8: Double? = null,
    val p_wind_10p8: Double? = null,
    val high_wind: Boolean = false,
    val precip_q05_mm: Double? = null,
    val precip_q95_mm: Double? = null,
    val season: String = "",
    val regime: String = "",
    val p_gt_64p5: Double = 0.0,
    val p_gt_115p6: Double = 0.0,
    val p_gt_204p5: Double = 0.0,
    val tier: String = "green",
    val heatwave: Boolean = false,
    val population: Long = 0,
    val population_source: String = "",
    val disagreement: Double = 0.0,
    val weights: Map<String, Double> = emptyMap(),
    val lomo_rmse_increase_pct: Map<String, Double> = emptyMap(),
    val shrinkage: Shrinkage? = null,
    val dominant_model: String? = null,
    val lead_day: Int? = null,
) {
    val tierEnum: Tier get() = Tier.fromKey(tier)
    val dominantModel: String get() = dominant_model ?: (weights.maxByOrNull { it.value }?.key ?: "")
    val mostCriticalModel: String get() = lomo_rmse_increase_pct.maxByOrNull { it.value }?.key ?: ""
}

@Serializable
data class DistrictsResult(
    val meta: Meta = Meta(),
    val lead_day: Int = 1,
    val count: Int = 0,
    val districts: List<District> = emptyList(),
)

@Serializable
data class DistrictLeads(val district: String = "", val leads: List<District> = emptyList())

@Serializable
data class MetricValues(
    val rmse: Double? = null,
    val mae: Double? = null,
    val fss50: Double? = null,
    val freq_bias_64p5: Double? = null,
    val rev_cl0p1: Double? = null,
    val n_days: Int? = null,
    val ci_rmse_vs_best_single: List<Double?>? = null,
    val ci_rmse_vs_equal_weight: List<Double?>? = null,
    val bias: Double? = null,
    val brier: Double? = null,
)

@Serializable
data class LadderRow(
    val rung: String = "",
    val strategy: String = "",
    val metrics: Map<String, MetricValues> = emptyMap(),
)

@Serializable
data class LadderHeadline(
    val best_single: String = "",
    val ours: String = "",
    val pct_of_achievable_gain: Map<String, Double> = emptyMap(),
    val test_years: List<Int> = emptyList(),
    val rmse_change_vs_equal_weight_pct: Map<String, Double> = emptyMap(),
    val rmse_change_vs_best_single_pct: Map<String, Double> = emptyMap(),
)

@Serializable
data class Ladder(
    val meta: Meta = Meta(),
    val variable: String = "precip",
    val lead_days: List<Int> = emptyList(),
    val rows: List<LadderRow> = emptyList(),
    val headline: LadderHeadline = LadderHeadline(),
    val fss_scale_km: Int? = null,
)

@Serializable
data class FssEntry(
    val threshold_mm: Double = 0.0,
    val scales_km: List<Double> = emptyList(),
    val neighbourhoods: List<Int> = emptyList(),
    val fss: List<Double> = emptyList(),
    val f0: Double = 0.0,
    val fss_useful: Double = 0.5,
)

@Serializable
data class FssCurve(val meta: Meta = Meta(), val leads: Map<String, List<FssEntry>> = emptyMap())

@Serializable
data class Rev(
    val meta: Meta = Meta(),
    val cost_loss: List<Double> = emptyList(),
    val rev: List<Double> = emptyList(),
    val curves: Map<String, List<Double>> = emptyMap(),
    val headline_cl: Double? = null,
)

@Serializable
data class WhereWeLoseCell(
    val district: String = "",
    val lead_day: Int = 0,
    val season: String = "",
    val regime: String = "",
    val blend_rmse: Double = 0.0,
    val best_single: String = "",
    val best_single_rmse: Double = 0.0,
    val ci: List<Double> = emptyList(),
    val significant: Boolean = false,
    val n_days: Int? = null,
    val reason: String = "",
    val override_available: Boolean = false,
)

@Serializable
data class WhereWeLose(val meta: Meta = Meta(), val cells: List<WhereWeLoseCell> = emptyList())

@Serializable
data class Points(
    val meta: Meta = Meta(),
    val city: String = "",
    val lat: Double = 0.0,
    val lon: Double = 0.0,
    val variable: String = "precip",
    val lead_days: List<Int> = emptyList(),
    val members: Map<String, List<Double?>> = emptyMap(),
    val blend: List<Double?> = emptyList(),
    val q05: List<Double?> = emptyList(),
    val q95: List<Double?> = emptyList(),
    val disagreement: List<Double?> = emptyList(),
    val obs: List<Double?> = emptyList(),
)

@Serializable
data class ReplayVerification(
    val hits: Int = 0,
    val misses: Int = 0,
    val false_alarms: Int = 0,
    val rmse_mm: Double? = null,
)

@Serializable
data class ReplayStep(
    val lead_day: Int = 0,
    val init: String = "",
    val valid: String = "",
    val raster: String = "",
    val blend_peak_mm: Double? = null,
    val member_peak_mm: Map<String, Double?> = emptyMap(),
    val max_p_gt_64p5: Double? = null,
    val max_p_gt_115p6: Double? = null,
    val tiers: Map<String, Int> = emptyMap(),
    val verification: ReplayVerification? = null,
)

@Serializable
data class ReplayTruth(
    val raster: String = "",
    val observed_peak_mm: Double? = null,
    val districts_with_heavy_rain: Int = 0,
    val districts_in_focus: Int = 0,
    val definition: String = "",
)

@Serializable
data class Replay(
    val meta: Meta = Meta(),
    val event: String = "",
    val target_date: String = "",
    val states: List<String> = emptyList(),
    val steps: List<ReplayStep> = emptyList(),
    val verification: ReplayTruth? = null,
    val note: String = "",
)

@Serializable
data class Bounds(val south: Double, val north: Double, val west: Double, val east: Double)

@Serializable
data class RawGrids(
    val shape: List<Int>,
    val land_mask: List<Double> = emptyList(),
    val obs: List<Double?> = emptyList(),
    val models: Map<String, List<Double?>> = emptyMap(),
    val bounds: Bounds? = null,
    val lead_day: Int? = null,
)

@Serializable
data class GeoDistrict(
    val id: String,
    val name: String,
    val state: String = "",
    val region: String = "",
    val c: List<Double> = emptyList(),
    val rings: List<List<Double>> = emptyList(),
)

@Serializable
data class GeoCompact(val bounds: List<Double> = emptyList(), val districts: List<GeoDistrict> = emptyList())

@Serializable
data class ImpactCard(val persona: String, val label: String, val action: String)

@Serializable
data class ImpactResponse(
    val district: District,
    val valid_date: String = "",
    val cards: List<ImpactCard> = emptyList(),
    val disclaimer: String = "",
)

@Serializable
data class CopilotRequest(val question: String, val lead_day: Int = 1)

@Serializable
data class CopilotResponse(
    val answer: String,
    val disclaimer: String = "",
    val sources: List<String> = emptyList(),
    val intent_detected: String? = null,
    val districts_matched: List<String> = emptyList(),
    val mode: String = "",
)

@Serializable
data class CopilotSuggestions(val suggestions: List<String> = emptyList())

@Serializable
data class SmsPreview(
    val district_id: String = "",
    val language: String = "en",
    val text: String = "",
    val chars: Int = 0,
    val encoding: String = "",
    val segments: Int = 1,
)

@Serializable
data class SmsDispatchRequest(
    val district_id: String,
    val phone: String,
    val language: String = "en",
    val lead_day: Int = 1,
    val dry_run: Boolean = false,
)

@Serializable
data class SmsDispatchResponse(
    val status: String = "",
    val message: String = "",
    val text: String = "",
    val delivery: String = "",
    val detail: String? = null,
    val chars: Int = 0,
    val encoding: String = "",
    val segments: Int = 1,
)

@Serializable
data class SubscriptionRequest(val phone: String, val district_id: String, val language: String = "en")

@Serializable
data class SubscriptionResponse(val status: String = "", val district_id: String = "", val count: Int = 0)

@Serializable
data class Health(
    val status: String = "",
    val version: String = "",
    val available_lead_days: List<Int> = emptyList(),
    val cycle: String? = null,
    val fixture: Boolean? = null,
    val copilot_llm: Boolean = false,
    val sms_gateway_configured: Boolean = false,
)

@Serializable
data class LiveBlendRequest(val lead_day: Int, val weights: Map<String, Double>)

@Serializable
data class LiveBlendResponse(
    val lead_day: Int = 0,
    val weights_used: Map<String, Double> = emptyMap(),
    val rmse_mm: Double? = null,
    val mae_mm: Double? = null,
    val per_model_rmse_mm: Map<String, Double?> = emptyMap(),
    val cells_gt_64p5: Int = 0,
    val cells_gt_115p6: Int = 0,
    val cells_gt_204p5: Int = 0,
    val max_blend_mm: Double? = null,
)

@Serializable
data class AlertItem(
    val id: String,
    val name: String,
    val state: String = "",
    val tier: String = "green",
    val p_gt_115p6: Double = 0.0,
    val precip_p90_mm: Double = 0.0,
    val population: Long = 0,
    val severity: String = "",
    val certainty: String = "",
    val headline: String = "",
    val instruction: String = "",
)

@Serializable
data class AlertsResponse(
    val lead_day: Int = 1,
    val cycle: String? = null,
    val valid_date: String = "",
    val count: Int = 0,
    val alerts: List<AlertItem> = emptyList(),
    val status: String = "",
    val disclaimer: String = "",
)

/** IMD hazard tiers. Thresholds are 24 h rainfall in mm. */
enum class Tier(val key: String, val label: String, val range: String, val argb: Long) {
    RED("red", "Red Alert", "Extremely heavy (>204.5 mm)", 0xFFDC2626),
    ORANGE("orange", "Orange Alert", "Very heavy (115.6–204.5 mm)", 0xFFEA580C),
    YELLOW("yellow", "Yellow Alert", "Heavy (64.5–115.6 mm)", 0xFFF59E0B),
    GREEN("green", "Green / Normal", "No warning (<64.5 mm)", 0xFF16A34A);

    companion object {
        const val HEAVY_MM = 64.5
        const val VERY_HEAVY_MM = 115.6
        const val EXTREMELY_HEAVY_MM = 204.5

        fun fromKey(key: String?): Tier = entries.firstOrNull { it.key.equals(key, ignoreCase = true) } ?: GREEN

        /** Tier for a 24 h rainfall amount using the IMD thresholds (same rule as the pipeline). */
        fun forRainfall(mm: Double): Tier = when {
            mm > EXTREMELY_HEAVY_MM -> RED
            mm > VERY_HEAVY_MM -> ORANGE
            mm > HEAVY_MM -> YELLOW
            else -> GREEN
        }
    }
}

/** Where a payload came from — shown in the UI so nobody mistakes the snapshot for live data. */
enum class DataSource { LIVE, SNAPSHOT }

data class Sourced<T>(val data: T, val source: DataSource, val error: String? = null)
