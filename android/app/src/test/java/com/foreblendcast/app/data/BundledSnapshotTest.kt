package com.foreblendcast.app.data

import kotlinx.serialization.json.Json
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/** The snapshot bundled in assets/ must parse with the app's models and hold real values. */
class BundledSnapshotTest {
    private val json = Json {
        ignoreUnknownKeys = true; coerceInputValues = true; explicitNulls = false; isLenient = true; allowSpecialFloatingPointValues = true
    }
    private val assets = listOf("src/main/assets/data", "app/src/main/assets/data").map(::File).first { it.isDirectory }
    private fun read(path: String) = File(assets, path).readText(Charsets.UTF_8)

    @Test fun every_bundled_lead_day_has_districts_with_three_hazards() {
        for (ld in Repository.BUNDLED_LEAD_DAYS) {
            val r = json.decodeFromString(DistrictsResult.serializer(), read("districts_L$ld.json"))
            assertTrue("L$ld districts", r.districts.size > 700)
            assertFalse(r.meta.fixture)
            assertFalse("test year must not be a training year", r.meta.train_years.contains(2022))
            assertTrue("temperature varies", r.districts.mapNotNull { it.tmax_c }.toSet().size > 100)
            assertTrue("wind varies", r.districts.mapNotNull { it.wind_ms }.toSet().size > 20)
            r.districts.forEach { d ->
                assertEquals(1.0, d.weights.values.sum(), 0.01)
                assertNotNull(d.p_heatwave); assertNotNull(d.p_wind_8)
                assertTrue(d.precip_q05_mm!! <= d.precip_q95_mm!!)
            }
            assertTrue(File(assets, "rasters/precip_pm_L$ld.png").isFile)
            assertTrue(File(assets, "rasters/raw_grids_L$ld.json").isFile)
        }
    }

    @Test fun ladder_has_a_real_equal_weight_baseline() {
        val ladder = json.decodeFromString(Ladder.serializer(), read("ladder.json"))
        assertEquals(Repository.BUNDLED_LEAD_DAYS, ladder.lead_days)
        val rows = ladder.rows.associateBy { it.strategy }
        for (key in ladder.lead_days.map { "L$it" }) {
            val equal = rows.getValue("equal_weight").metrics.getValue(key)
            val clim = rows.getValue("climatology").metrics.getValue(key)
            val ours = rows.getValue("context_shrink").metrics.getValue(key)
            assertTrue(equal.rmse!! < clim.rmse!!)
            assertTrue(ours.rmse!! < equal.rmse!!)
            assertTrue("MAE is measured, not 0.8 x RMSE", kotlin.math.abs(ours.mae!! / ours.rmse!! - 0.8) > 0.01)
        }
    }

    @Test fun points_and_verification_files_parse() {
        for ((slug, _) in Repository.CITIES) {
            val p = json.decodeFromString(Points.serializer(), read("points/$slug.json"))
            assertEquals(Repository.BUNDLED_LEAD_DAYS, p.lead_days)
            assertEquals(p.lead_days.size, p.blend.size)
            assertEquals(setOf("hres", "ens", "graphcast"), p.members.keys)
        }
        assertTrue(json.decodeFromString(FssCurve.serializer(), read("fss_curve.json")).leads.isNotEmpty())
        assertTrue(json.decodeFromString(Rev.serializer(), read("rev.json")).rev.isNotEmpty())
        json.decodeFromString(WhereWeLose.serializer(), read("where_we_lose.json")).cells.forEach { assertEquals(2, it.ci.size) }
    }

    @Test fun replay_is_three_cycles_for_one_day() {
        val r = json.decodeFromString(Replay.serializer(), read("replay.json"))
        assertEquals(listOf(5, 3, 1), r.steps.map { it.lead_day })
        assertEquals(3, r.steps.map { it.init }.toSet().size)
        assertEquals(setOf(r.target_date), r.steps.map { it.valid }.toSet())
        r.steps.forEach { assertTrue(File(assets, "rasters/${it.raster}").isFile) }
    }
}
