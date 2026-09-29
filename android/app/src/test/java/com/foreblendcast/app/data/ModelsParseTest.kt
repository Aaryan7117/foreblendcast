package com.foreblendcast.app.data

import kotlinx.serialization.json.Json
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** Parses the exact JSON shapes the pipeline / API emit, including NaN and Infinity in the ladder. */
class ModelsParseTest {
    private val json = Json {
        ignoreUnknownKeys = true; coerceInputValues = true; explicitNulls = false; isLenient = true; allowSpecialFloatingPointValues = true
    }

    @Test fun district_full_and_compact() {
        val full = """{"id":"AS-NALBARI","name":"Nalbari","state":"Assam","precip_p90_mm":181.2,"tmax_c":0.0,"wind_ms":0.0,"p_gt_64p5":0.98,"p_gt_115p6":0.72,"p_gt_204p5":0.21,"tier":"red","heatwave":false,"population":771639,"population_source":"WorldPop 2020","disagreement":6.1,"weights":{"hres":0.5,"ens":0.3,"graphcast":0.2},"lomo_rmse_increase_pct":{"hres":12.0,"ens":-1.5,"graphcast":3.0},"shrinkage":{"level_used":"national","n_eff":50,"reason":"prototype_single_cycle"}}"""
        val d = json.decodeFromString(District.serializer(), full)
        assertEquals(Tier.RED, d.tierEnum)
        assertEquals("hres", d.dominantModel)
        assertEquals("hres", d.mostCriticalModel)
        assertEquals(50.0, d.shrinkage!!.n_eff, 0.0)

        val compact = """{"id":"AS-NALBARI","name":"Nalbari","state":"Assam","tier":"orange","precip_p90_mm":120.0,"p_gt_64p5":0.9,"p_gt_115p6":0.55,"p_gt_204p5":0.05,"population":771639,"disagreement":2.0,"heatwave":false,"dominant_model":"ens"}"""
        val c = json.decodeFromString(District.serializer(), compact)
        assertEquals("ens", c.dominantModel)
        assertTrue(c.weights.isEmpty())
        assertEquals(Tier.ORANGE, c.tierEnum)
    }

    @Test fun ladder_with_nan_and_infinity() {
        val txt = """{"meta":{"cycle":"2022-06-14T00Z","fixture":false},"variable":"precip","lead_days":[1],"rows":[{"rung":"single","strategy":"graphcast","metrics":{"L1":{"rmse":NaN,"mae":NaN,"fss50":0.708,"freq_bias_64p5":Infinity,"rev_cl0p1":0.0,"n_days":183}}},{"rung":"blend","strategy":"context_shrink_pm","metrics":{"L1":{"rmse":5.54,"mae":4.432,"fss50":0.609,"ci_rmse_vs_best_single":[0.5577,1.3872]}}}],"headline":{"best_single":"graphcast","ours":"context_shrink_pm","pct_of_achievable_gain":{"L1":0.0},"test_years":[2020,2022]}}"""
        val l = json.decodeFromString(Ladder.serializer(), txt)
        assertTrue(l.rows[0].metrics["L1"]!!.rmse!!.isNaN())
        assertTrue(l.rows[0].metrics["L1"]!!.freq_bias_64p5!!.isInfinite())
        assertEquals(2, l.rows[1].metrics["L1"]!!.ci_rmse_vs_best_single!!.size)
        assertEquals(listOf(2020, 2022), l.headline.test_years)
    }

    @Test fun points_with_nulls_and_raw_grids() {
        val p = json.decodeFromString(Points.serializer(), """{"city":"Mumbai","lat":19.07,"lon":72.88,"lead_days":[1,2],"members":{"hres":[1.36,null]},"blend":[1.78,null],"q05":[0.5,null],"q95":[3.0,null],"disagreement":[0.3,0.0],"obs":[3.65,4.65]}""")
        assertNull(p.blend[1])
        assertEquals(1.36, p.members["hres"]!![0]!!, 0.0)
        val g = json.decodeFromString(RawGrids.serializer(), """{"shape":[1,2],"land_mask":[1,0],"obs":[2.5,null],"models":{"hres":[1,2.5]},"row0":"south"}""")
        assertEquals(listOf(1, 2), g.shape)
        assertEquals(1.0, g.land_mask[0], 0.0)
        assertNull(g.obs[1])
    }

    @Test fun copilot_sms_and_health_responses() {
        val c = json.decodeFromString(CopilotResponse.serializer(), """{"answer":"**Nalbari** is RED","disclaimer":"EXERCISE","sources":["results/districts_L1.json"],"intent_detected":"explain_tier","districts_matched":["Nalbari"],"mode":"deterministic"}""")
        assertEquals("explain_tier", c.intent_detected)
        val s = json.decodeFromString(SmsDispatchResponse.serializer(), """{"status":"success","message":"SMS mock","text":"[EXERCISE] RED","delivery":"mock","detail":"no gateway","chars":100,"encoding":"GSM-7","segments":1}""")
        assertEquals("mock", s.delivery)
        val h = json.decodeFromString(Health.serializer(), """{"status":"ok","version":"1.1.0","available_lead_days":[1,3,5],"cycle":"2022-06-14T00Z","fixture":false,"copilot_llm":true,"sms_gateway_configured":false}""")
        assertEquals(listOf(1, 3, 5), h.available_lead_days)
    }
}
