package com.foreblendcast.app.blend

import com.foreblendcast.app.data.Bounds
import com.foreblendcast.app.data.RawGrids
import com.foreblendcast.app.data.Tier
import kotlin.math.floor
import kotlin.math.sqrt

/**
 * Per-model gridded fields for one lead day, unpacked into flat float arrays.
 * Row 0 is the SOUTHERN-most row (same convention as results/rasters/raw_grids_L*.json).
 */
class GridSet(
    val rows: Int,
    val cols: Int,
    val land: BooleanArray,
    val obs: FloatArray,
    val models: Map<String, FloatArray>,
    val bounds: Bounds,
) {
    val size: Int get() = rows * cols
    val modelNames: List<String> get() = models.keys.toList()

    /** Flat index of the grid cell containing (lat, lon), or -1 when outside the grid. */
    fun cellIndex(lat: Double, lon: Double): Int {
        val dLat = (bounds.north - bounds.south) / rows
        val dLon = (bounds.east - bounds.west) / cols
        val r = floor((lat - bounds.south) / dLat).toInt()
        val c = floor((lon - bounds.west) / dLon).toInt()
        if (r < 0 || r >= rows || c < 0 || c >= cols) return -1
        return r * cols + c
    }

    companion object {
        fun from(raw: RawGrids, fallbackBounds: Bounds): GridSet {
            val rows = raw.shape[0]
            val cols = raw.shape[1]
            val n = rows * cols
            val land = BooleanArray(n) { i -> (raw.land_mask.getOrNull(i) ?: 0.0) >= 0.5 }
            val obs = FloatArray(n) { i -> raw.obs.getOrNull(i)?.toFloat() ?: Float.NaN }
            val models = raw.models.mapValues { (_, v) -> FloatArray(n) { i -> v.getOrNull(i)?.toFloat() ?: Float.NaN } }
            return GridSet(rows, cols, land, obs, models, raw.bounds ?: fallbackBounds)
        }
    }
}

data class BlendStats(
    val rmse: Float,
    val mae: Float,
    val perModelRmse: Map<String, Float>,
    val cellsHeavy: Int,
    val cellsVeryHeavy: Int,
    val cellsExtremelyHeavy: Int,
    val maxMm: Float,
    val landCells: Int,
)

/**
 * The live "forecaster override": a weighted mean of the member fields plus verification
 * against the ERA5 grid that ships with them. Pure Kotlin so it is unit-testable and can
 * run on every slider tick.
 */
object LiveBlend {

    /** Normalise non-negative weights to sum to one, keeping only models present in the grid. */
    fun normalise(weights: Map<String, Double>, available: Collection<String>): Map<String, Float> {
        val kept = weights.filterKeys { it in available }.mapValues { maxOf(0.0, it.value) }
        val total = kept.values.sum()
        if (total <= 0.0) return kept.keys.associateWith { 1f / kept.size }
        return kept.mapValues { (it.value / total).toFloat() }
    }

    fun blend(grid: GridSet, weights: Map<String, Double>): FloatArray {
        val w = normalise(weights, grid.models.keys)
        val out = FloatArray(grid.size)
        for ((model, wt) in w) {
            if (wt == 0f) continue
            val f = grid.models.getValue(model)
            for (i in 0 until grid.size) {
                val v = f[i]
                if (!v.isNaN()) out[i] += wt * v
            }
        }
        return out
    }

    fun rmse(field: FloatArray, grid: GridSet): Float {
        var s = 0.0
        var n = 0
        for (i in 0 until grid.size) {
            if (!grid.land[i]) continue
            val o = grid.obs[i]
            if (o.isNaN()) continue
            val d = field[i] - o
            s += d * d
            n++
        }
        return if (n == 0) Float.NaN else sqrt(s / n).toFloat()
    }

    fun mae(field: FloatArray, grid: GridSet): Float {
        var s = 0.0
        var n = 0
        for (i in 0 until grid.size) {
            if (!grid.land[i]) continue
            val o = grid.obs[i]
            if (o.isNaN()) continue
            s += kotlin.math.abs(field[i] - o)
            n++
        }
        return if (n == 0) Float.NaN else (s / n).toFloat()
    }

    fun stats(field: FloatArray, grid: GridSet): BlendStats {
        var heavy = 0
        var veryHeavy = 0
        var extreme = 0
        var mx = 0f
        var landCells = 0
        for (i in 0 until grid.size) {
            if (!grid.land[i]) continue
            landCells++
            val v = field[i]
            if (v > Tier.HEAVY_MM) heavy++
            if (v > Tier.VERY_HEAVY_MM) veryHeavy++
            if (v > Tier.EXTREMELY_HEAVY_MM) extreme++
            if (v > mx) mx = v
        }
        val perModel = grid.models.mapValues { (_, f) -> rmse(f, grid) }
        return BlendStats(rmse(field, grid), mae(field, grid), perModel, heavy, veryHeavy, extreme, mx, landCells)
    }

    /**
     * Approximate district tiers from a blended field by sampling the grid cell under each
     * district centroid. Labelled "approximate" in the UI: the pipeline uses an area-weighted
     * 90th percentile over all cells in the district, which needs the fraction grid we do not ship.
     */
    fun approximateTiers(field: FloatArray, grid: GridSet, centroids: Map<String, Pair<Double, Double>>): Map<String, Tier> {
        val out = HashMap<String, Tier>(centroids.size)
        for ((id, c) in centroids) {
            val idx = grid.cellIndex(c.second, c.first)
            out[id] = if (idx < 0) Tier.GREEN else Tier.forRainfall(field[idx].toDouble())
        }
        return out
    }

    /**
     * ARGB pixels for a field, row 0 at the TOP of the image (north). Same ramp as the web
     * live blender: transparent <0.5 mm, pale green → green → amber → red → dark red at 200+ mm.
     */
    fun toArgb(field: FloatArray, rows: Int, cols: Int): IntArray {
        val px = IntArray(rows * cols)
        for (r in 0 until rows) {
            val imgRow = rows - 1 - r
            for (c in 0 until cols) {
                px[imgRow * cols + c] = rainfallColor(field[r * cols + c])
            }
        }
        return px
    }

    fun rainfallColor(mm: Float): Int {
        if (mm.isNaN() || mm < 0.5f) return 0x00000000
        fun lerp(a: Int, b: Int, f: Float) = (a + f * (b - a)).toInt().coerceIn(0, 255)
        fun argb(r: Int, g: Int, b: Int) = (0xFF shl 24) or (r shl 16) or (g shl 8) or b
        return when {
            mm < 10f -> { val f = mm / 10f; argb(lerp(247, 199, f), lerp(252, 233, f), lerp(240, 192, f)) }
            mm < 50f -> { val f = (mm - 10f) / 40f; argb(lerp(199, 116, f), lerp(233, 196, f), lerp(192, 118, f)) }
            mm < 100f -> { val f = (mm - 50f) / 50f; argb(lerp(116, 254, f), lerp(196, 178, f), lerp(118, 76, f)) }
            mm < 200f -> { val f = (mm - 100f) / 100f; argb(lerp(254, 240, f), lerp(178, 59, f), lerp(76, 32, f)) }
            else -> argb(189, 0, 38)
        }
    }
}
