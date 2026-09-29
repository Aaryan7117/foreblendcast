package com.foreblendcast.app.blend

import com.foreblendcast.app.data.Bounds
import com.foreblendcast.app.data.Tier
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class LiveBlendTest {
    // 2 rows x 3 cols, row 0 = south
    private val bounds = Bounds(south = 0.0, north = 2.0, west = 0.0, east = 3.0)
    private val grid = GridSet(
        rows = 2, cols = 3,
        land = booleanArrayOf(true, true, true, true, true, false),
        obs = floatArrayOf(10f, 20f, 30f, 40f, 50f, 60f),
        models = mapOf(
            "hres" to floatArrayOf(10f, 20f, 30f, 40f, 50f, 60f),            // perfect
            "ens" to floatArrayOf(0f, 0f, 0f, 0f, 0f, 0f),                   // zero
            "graphcast" to floatArrayOf(20f, 40f, 60f, 80f, 100f, Float.NaN), // double, one gap
        ),
        bounds = bounds,
    )

    @Test fun normalise_scales_to_one_and_drops_unknown_models() {
        val w = LiveBlend.normalise(mapOf("hres" to 2.0, "ens" to 2.0, "pangu" to 5.0), grid.models.keys)
        assertEquals(0.5f, w.getValue("hres"), 1e-6f)
        assertEquals(0.5f, w.getValue("ens"), 1e-6f)
        assertTrue("pangu" !in w)
    }

    @Test fun normalise_all_zero_falls_back_to_equal() {
        val w = LiveBlend.normalise(mapOf("hres" to 0.0, "ens" to 0.0), grid.models.keys)
        assertEquals(0.5f, w.getValue("hres"), 1e-6f)
    }

    @Test fun single_model_blend_has_that_models_rmse() {
        val f = LiveBlend.blend(grid, mapOf("hres" to 1.0, "ens" to 0.0, "graphcast" to 0.0))
        assertEquals(0f, LiveBlend.rmse(f, grid), 1e-6f)
        val z = LiveBlend.blend(grid, mapOf("ens" to 1.0))
        // land cells obs 10,20,30,40,50 -> rmse = sqrt((100+400+900+1600+2500)/5) = sqrt(1100)
        assertEquals(Math.sqrt(1100.0).toFloat(), LiveBlend.rmse(z, grid), 1e-3f)
    }

    @Test fun equal_weights_average_and_nan_members_count_as_zero() {
        val f = LiveBlend.blend(grid, mapOf("hres" to 1.0, "graphcast" to 1.0))
        assertEquals(15f, f[0], 1e-6f)   // (10 + 20) / 2
        assertEquals(30f, f[5], 1e-6f)   // graphcast NaN -> 0.5 * 60
    }

    @Test fun stats_counts_exceedances_on_land_only() {
        val f = LiveBlend.blend(grid, mapOf("graphcast" to 1.0)) // 20,40,60,80,100,NaN->0
        val s = LiveBlend.stats(f, grid)
        assertEquals(5, s.landCells)
        assertEquals(2, s.cellsHeavy)      // 80, 100 > 64.5
        assertEquals(0, s.cellsVeryHeavy)
        assertEquals(100f, s.maxMm, 1e-6f)
        assertEquals(0f, s.perModelRmse.getValue("hres"), 1e-6f)
    }

    @Test fun cell_index_maps_lat_lon_with_row0_south() {
        assertEquals(0, grid.cellIndex(0.5, 0.5))
        assertEquals(5, grid.cellIndex(1.5, 2.5))
        assertEquals(-1, grid.cellIndex(5.0, 0.5))
    }

    @Test fun approximate_tiers_use_centroid_cell() {
        val f = floatArrayOf(10f, 70f, 120f, 250f, 0f, 0f)
        val tiers = LiveBlend.approximateTiers(
            f, grid,
            mapOf("a" to (0.5 to 0.5), "b" to (1.5 to 0.5), "c" to (2.5 to 0.5), "d" to (0.5 to 1.5), "out" to (99.0 to 99.0)),
        )
        assertEquals(Tier.GREEN, tiers["a"])
        assertEquals(Tier.YELLOW, tiers["b"])
        assertEquals(Tier.ORANGE, tiers["c"])
        assertEquals(Tier.RED, tiers["d"])
        assertEquals(Tier.GREEN, tiers["out"])
    }

    @Test fun argb_flips_rows_so_north_is_on_top() {
        val f = floatArrayOf(0f, 0f, 0f, 150f, 150f, 150f) // row 1 (north) wet
        val px = LiveBlend.toArgb(f, 2, 3)
        assertEquals(0, px[3] ushr 24)            // bottom image row = south = transparent
        assertEquals(0xFF, px[0] ushr 24)         // top image row = north = opaque
        assertEquals(0, LiveBlend.rainfallColor(0.2f) ushr 24)
        assertEquals(0xFFBD0026.toInt(), LiveBlend.rainfallColor(300f))
    }

    @Test fun tier_thresholds_match_imd() {
        assertEquals(Tier.GREEN, Tier.forRainfall(64.5))
        assertEquals(Tier.YELLOW, Tier.forRainfall(64.6))
        assertEquals(Tier.ORANGE, Tier.forRainfall(115.7))
        assertEquals(Tier.RED, Tier.forRainfall(204.6))
        assertEquals(Tier.ORANGE, Tier.fromKey("Orange"))
        assertEquals(Tier.GREEN, Tier.fromKey(null))
    }
}
