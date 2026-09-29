package com.foreblendcast.app.data

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class LocalInsightsTest {
    private fun d(id: String, tier: String, p: Double, pop: Long, dis: Double = 1.0) = District(
        id = id,
        name = id.substringAfter('-').lowercase().replaceFirstChar { it.uppercase() },
        state = "Assam", tier = tier, p_gt_115p6 = p, precip_p90_mm = p * 200,
        population = pop, disagreement = dis,
        weights = mapOf("hres" to 0.6, "ens" to 0.3, "graphcast" to 0.1),
        lomo_rmse_increase_pct = mapOf("hres" to 9.0, "ens" to 1.0, "graphcast" to -2.0),
    )
    private val list = listOf(d("AS-NALBARI", "red", 0.72, 800_000), d("AS-KAMRUP", "orange", 0.5, 1_500_000, 7.0), d("AS-BAKSA", "green", 0.01, 900_000))

    @Test fun summary_counts_and_exposure() {
        val s = LocalInsights.summary(list)
        assertEquals(1, s.counts[Tier.RED])
        assertEquals(1, s.counts[Tier.ORANGE])
        assertEquals(0, s.counts[Tier.YELLOW])
        assertEquals(1_500_000L, s.exposed[Tier.ORANGE])
        assertEquals("AS-NALBARI", s.topByRisk.first().id)
        assertEquals("AS-KAMRUP", s.topByDisagreement.first().id)
    }

    @Test fun impact_cards_follow_tier() {
        assertTrue(LocalInsights.impactCards(list[0])[2].action.contains("0.8M exposed"))
        assertTrue(LocalInsights.impactCards(list[1])[0].action.startsWith("Postpone"))
        assertTrue(LocalInsights.impactCards(list[2])[3].action.startsWith("Normal"))
    }

    @Test fun valid_date_from_cycle() {
        assertEquals("15 Jun 2022", LocalInsights.validDate(Meta(cycle = "2022-06-14T00Z"), 1))
        assertEquals("19 Jun 2022", LocalInsights.validDate(Meta(cycle = "2022-06-14T00Z"), 5))
        assertEquals("D+3", LocalInsights.validDate(Meta(cycle = ""), 3))
    }

    @Test fun sms_text_matches_server_template() {
        val t = LocalInsights.smsTextEn(list[0], "15 Jun")
        assertTrue(t, t.startsWith("[EXERCISE] RED Rain alert: Nalbari, 15 Jun. 72% chance >115mm"))
        assertTrue(t, t.contains("8.0L people exposed"))
    }

    @Test fun copilot_router_intents() {
        val why = LocalInsights.copilot("Why is Nalbari red?", list, null, 1)
        assertEquals("explain_tier", why.intent_detected)
        assertEquals(listOf("Nalbari"), why.districts_matched)
        assertTrue(why.answer, why.answer.contains("72.0%"))

        val all = LocalInsights.copilot("Show all red alert districts", list, null, 1)
        assertEquals("list_alerts", all.intent_detected)
        assertTrue(all.answer, all.answer.contains("1 RED, 1 ORANGE"))

        val w = LocalInsights.copilot("What are the blend weights for Kamrup?", list, null, 1)
        assertEquals("explain_weights", w.intent_detected)
        assertTrue(w.answer, w.answer.contains("HRES**: 60.0%"))

        val lomo = LocalInsights.copilot("LOMO sensitivity for Kamrup", list, null, 1)
        assertEquals("explain_lomo", lomo.intent_detected)
        assertTrue(lomo.answer, lomo.answer.contains("+9.0%"))

        val none = LocalInsights.copilot("hello there", list, null, 1)
        assertTrue(none.answer, none.answer.contains("could not identify"))
        assertEquals("on-device", none.mode)

        val ladder = Ladder(rows = listOf(LadderRow("blend", "context_shrink_pm", mapOf("L1" to MetricValues(rmse = 5.54, mae = 4.43, fss50 = 0.61)))))
        val acc = LocalInsights.copilot("How accurate is the blend?", list, ladder, 1)
        assertTrue(acc.sources.contains("results/ladder.json"))
        assertTrue(acc.answer, acc.answer.contains("5.540"))
    }
}
