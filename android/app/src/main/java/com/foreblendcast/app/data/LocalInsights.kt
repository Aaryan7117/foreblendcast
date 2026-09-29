package com.foreblendcast.app.data

import java.util.Locale

/**
 * Derivations that must also work with the bundled snapshot (no server):
 *  - tier counts / exposed population
 *  - persona impact cards (identical wording to api/store.py)
 *  - a small on-device copy of the deterministic copilot router
 * Everything reports numbers straight from the district records; nothing is invented.
 */
object LocalInsights {

    const val DISCLAIMER = "⚠️ EXERCISE — This is a prototype output from SIH26081 ForeBlendCast. NOT an official IMD warning."

    data class Summary(
        val counts: Map<Tier, Int>,
        val exposed: Map<Tier, Long>,
        val total: Int,
        val topByRisk: List<District>,
        val topByDisagreement: List<District>,
    )

    fun summary(districts: List<District>, topN: Int = 10): Summary {
        val counts = Tier.entries.associateWith { t -> districts.count { it.tierEnum == t } }
        val exposed = Tier.entries.associateWith { t -> districts.filter { it.tierEnum == t }.sumOf { it.population } }
        val top = districts.sortedWith(compareByDescending<District> { it.p_gt_115p6 }.thenByDescending { it.precip_p90_mm }).take(topN)
        val dis = districts.sortedByDescending { it.disagreement }.take(5)
        return Summary(counts, exposed, districts.size, top, dis)
    }

    fun impactCards(d: District): List<ImpactCard> {
        val popM = d.population / 1e6
        return when (d.tierEnum) {
            Tier.RED -> listOf(
                ImpactCard("farmer", "Farmer", "Do not spray pesticides. Delay all sowing activities immediately. Harvest mature crops if possible."),
                ImpactCard("fisher", "Fisher", "Do not venture into the sea. Secure boats in safe harbors."),
                ImpactCard("dm", "District Magistrate", "Pre-position NDRF teams. Mobilize evacuation for low-lying areas. Approx. ${"%.1f".format(Locale.US, popM)}M exposed."),
                ImpactCard("citizen", "Citizen", "Avoid rivers and low-lying areas. Stay indoors during heavy downpours."),
            )
            Tier.ORANGE -> listOf(
                ImpactCard("farmer", "Farmer", "Postpone irrigation and fertilizer application. Check drainage in fields."),
                ImpactCard("fisher", "Fisher", "Avoid deep-sea fishing. Return to coast if weather deteriorates."),
                ImpactCard("dm", "District Magistrate", "Keep SDRF on standby. Alert block development officers in flood-prone zones."),
                ImpactCard("citizen", "Citizen", "Avoid unnecessary travel during rain. Keep emergency kits ready."),
            )
            else -> listOf(
                ImpactCard("farmer", "Farmer", "Normal farming activities can continue. Monitor upcoming forecasts."),
                ImpactCard("fisher", "Fisher", "Normal fishing activities allowed. Carry safety equipment."),
                ImpactCard("dm", "District Magistrate", "Standard operational readiness. Review district disaster management plans."),
                ImpactCard("citizen", "Citizen", "Normal routine. Follow standard weather advisories."),
            )
        }
    }

    /** English SMS text, same template as the server (used only for offline preview). */
    fun smsTextEn(d: District, validDate: String): String {
        val prob = Math.round(d.p_gt_115p6 * 100)
        val popLakh = "%.1f".format(Locale.US, d.population / 1e5)
        return "[EXERCISE] ${d.tier.uppercase()} Rain alert: ${d.name}, $validDate. $prob% chance >115mm (${"%.0f".format(Locale.US, d.precip_p90_mm)}mm expected). ${popLakh}L people exposed. Avoid rivers/low areas. -SIH26081, not IMD"
    }

    /** Valid date string ("15 Jun") from the cycle "2022-06-14T00Z" plus the lead. */
    fun validDate(meta: Meta, leadDay: Int): String {
        val m = Regex("""(\d{4})-(\d{2})-(\d{2})""").find(meta.cycle) ?: return "D+$leadDay"
        val (y, mo, d) = m.destructured
        val cal = java.util.GregorianCalendar(y.toInt(), mo.toInt() - 1, d.toInt())
        cal.add(java.util.Calendar.DAY_OF_MONTH, leadDay)
        return java.text.SimpleDateFormat("d MMM yyyy", Locale.US).format(cal.time)
    }

    // ── on-device copilot (subset of api/main.py deterministic router) ──
    private fun pct(x: Double) = "%.1f%%".format(Locale.US, x * 100)

    fun copilot(question: String, districts: List<District>, ladder: Ladder?, leadDay: Int): CopilotResponse {
        val q = question.lowercase(Locale.US)
        val mentioned = districts.sortedByDescending { it.name.length }.filter { q.contains(it.name.lowercase(Locale.US)) }
        val intent = detectIntent(q)
        val sources = mutableListOf("results/districts_L$leadDay.json")

        val answer: String = when {
            intent == "list_alerts" -> listAlerts(districts)
            intent == "explain_ladder" -> { sources += "results/ladder.json"; explainLadder(ladder, leadDay) }
            mentioned.isEmpty() -> {
                val s = summary(districts)
                "I could not identify a specific district in your question. Currently there are **${s.counts[Tier.RED]} RED** and **${s.counts[Tier.ORANGE]} ORANGE** alert districts for Lead Day $leadDay.\n\nTry: \"Why is Nalbari red?\", \"Blend weights for Kamrup\", \"Show all red alert districts\"."
            }
            else -> {
                val d = mentioned.first()
                when (intent) {
                    "explain_weights" -> explainWeights(d)
                    "explain_lomo" -> explainLomo(d)
                    "explain_population" -> "**Exposure data for ${d.name}:**\n\n• Population: **${"%,d".format(Locale.US, d.population)}** (${"%.1f".format(Locale.US, d.population / 1e6)}M)\n• Source: ${d.population_source.ifBlank { "WorldPop" }}\n• Alert tier: **${d.tier.uppercase()}**"
                    "explain_impact" -> "**What ${d.tier.uppercase()} means for ${d.name}:**\n\n" + impactCards(d).joinToString("\n") { "• **${it.label}**: ${it.action}" }
                    "explain_disagreement" -> "**Model disagreement for ${d.name}:** σ = **${"%.3f".format(Locale.US, d.disagreement)}**\n\n" + (if (d.disagreement > 15) "This is **very high** disagreement." else if (d.disagreement > 5) "This is **moderate** disagreement." else "This is **low** disagreement — models agree.") + "\n\nCurrent blend relies most on **${d.dominantModel.uppercase()}** (${pct(d.weights[d.dominantModel] ?: 0.0)})."
                    "explain_rainfall", "explain_probability" -> "**Rainfall forecast for ${d.name}:**\n\n• Expected precipitation (P90): **${"%.1f".format(Locale.US, d.precip_p90_mm)} mm** in 24h\n• Alert tier: **${d.tier.uppercase()}**\n• P(>64.5mm): **${pct(d.p_gt_64p5)}**\n• P(>115.6mm): **${pct(d.p_gt_115p6)}**\n• P(>204.5mm): **${pct(d.p_gt_204p5)}**"
                    else -> explainTier(d)
                }
            }
        }
        return CopilotResponse(answer, DISCLAIMER, sources, intent, mentioned.map { it.name }, "on-device")
    }

    private fun detectIntent(q: String): String {
        fun any(vararg w: String) = w.any { q.contains(it) }
        return when {
            any("list", "show", "all", "which", "how many", "count") && any("red", "orange", "alert", "warning", "danger") -> "list_alerts"
            any("why", "reason", "how come", "explain") && any("red", "orange", "alert", "warning", "tier") -> "explain_tier"
            any("tier", "alert", "level", "status", "colour", "color") -> "check_tier"
            any("verification", "ladder", "skill", "rmse", "mae", "fss", "accura", "how good", "how well", "performance") -> "explain_ladder"
            any("disagree", "spread", "uncertain", "confidence", "trust") -> "explain_disagreement"
            any("lomo", "leave-one", "leave one", "sensitivity", "remove", "without", "drop") -> "explain_lomo"
            any("weight", "blend", "model", "contribution", "dominant", "important") -> "explain_weights"
            any("probability", "chance", "likelihood", "prob", "how likely") -> "explain_probability"
            any("population", "people", "exposed", "vulnerab") -> "explain_population"
            any("impact", "farmer", "fisher", "what should", "advice", "do i") -> "explain_impact"
            any("rain", "precip", "mm", "how much") -> "explain_rainfall"
            else -> "district_summary"
        }
    }

    private fun explainTier(d: District): String {
        val lomo = d.mostCriticalModel
        val sb = StringBuilder()
        sb.append("**${d.name}** is at **${d.tier.uppercase()}** alert level. Here is why, based on the blend results:\n\n")
        sb.append("• **P(rain > 115.6mm)** = ${pct(d.p_gt_115p6)} — calibrated probability of very heavy rainfall.\n")
        sb.append("• **P(rain > 64.5mm)** = ${pct(d.p_gt_64p5)}\n")
        sb.append("• **P(rain > 204.5mm)** = ${pct(d.p_gt_204p5)}\n")
        sb.append("• **Expected precip (P90)** = ${"%.1f".format(Locale.US, d.precip_p90_mm)} mm in the next 24h.\n\n")
        sb.append("**Blend weights**: HRES=${pct(d.weights["hres"] ?: 0.0)}, ENS=${pct(d.weights["ens"] ?: 0.0)}, GraphCast=${pct(d.weights["graphcast"] ?: 0.0)}.\n\n")
        if (lomo.isNotEmpty()) sb.append("**LOMO sensitivity**: removing **${lomo.uppercase()}** changes RMSE by ${"%+.1f".format(Locale.US, d.lomo_rmse_increase_pct[lomo] ?: 0.0)}%.\n\n")
        sb.append("**Model disagreement (σ)** = ${"%.3f".format(Locale.US, d.disagreement)}. ")
        sb.append(if (d.disagreement > 5) "High disagreement — treat with caution." else "Models are in reasonable agreement.")
        return sb.toString()
    }

    private fun explainWeights(d: District): String {
        val lines = d.weights.entries.sortedByDescending { it.value }.joinToString("\n") { (m, w) -> "• **${m.uppercase()}**: ${pct(w)} ${"█".repeat((w * 20).toInt())}" }
        val sh = d.shrinkage
        return "**Blend weights for ${d.name}:**\n\n$lines\n\n**Shrinkage**: level = ${sh?.level_used ?: "N/A"}, n_eff = ${sh?.n_eff?.toInt() ?: "N/A"}. Reason: ${sh?.reason ?: "N/A"}"
    }

    private fun explainLomo(d: District): String {
        val lines = d.lomo_rmse_increase_pct.entries.sortedByDescending { it.value }.joinToString("\n") { (m, p) ->
            val e = if (p > 5) "🔴" else if (p > 0) "🟡" else "🟢"
            "• $e Remove **${m.uppercase()}**: RMSE changes by **${"%+.1f".format(Locale.US, p)}%**"
        }
        return "**Leave-One-Model-Out (LOMO) analysis for ${d.name}:**\n\n$lines\n\n→ **${d.mostCriticalModel.uppercase()}** is the most valuable model here."
    }

    private fun listAlerts(districts: List<District>): String {
        val red = districts.filter { it.tierEnum == Tier.RED }
        val orange = districts.filter { it.tierEnum == Tier.ORANGE }
        val sb = StringBuilder("**Alert summary:** ${red.size} RED, ${orange.size} ORANGE districts.\n\n")
        if (red.isNotEmpty()) { sb.append("**🔴 RED Alert Districts:**\n"); red.forEach { sb.append("  • ${it.name}, ${it.state} — P(>115mm)=${Math.round(it.p_gt_115p6 * 100)}%, Pop=${"%.1f".format(Locale.US, it.population / 1e6)}M\n") } }
        if (orange.isNotEmpty()) { sb.append("\n**🟠 ORANGE Alert Districts:**\n"); orange.forEach { sb.append("  • ${it.name}, ${it.state} — P(>115mm)=${Math.round(it.p_gt_115p6 * 100)}%, Pop=${"%.1f".format(Locale.US, it.population / 1e6)}M\n") } }
        val total = (red + orange).sumOf { it.population }
        sb.append("\n**Total exposed population: ${"%,d".format(Locale.US, total)} (${"%.1f".format(Locale.US, total / 1e6)}M)**")
        return sb.toString()
    }

    private fun explainLadder(ladder: Ladder?, leadDay: Int): String {
        if (ladder == null) return "Verification ladder data not available."
        val key = if (ladder.rows.any { it.metrics.containsKey("L$leadDay") }) "L$leadDay" else "L1"
        fun f(x: Double?) = if (x == null || x.isNaN() || x.isInfinite()) "N/A" else "%.3f".format(Locale.US, x)
        val sb = StringBuilder("**Verification Ladder (Lead Day ${key.drop(1)}):**\n\n| Rung | Strategy | RMSE | MAE | FSS 64.5mm (~83km) |\n|---|---|---|---|---|\n")
        ladder.rows.forEach { r -> val m = r.metrics[key]; sb.append("| ${r.rung} | ${r.strategy} | ${f(m?.rmse)} | ${f(m?.mae)} | ${f(m?.fss50)} |\n") }
        sb.append("\n→ Lower RMSE/MAE is better. Higher FSS is better. Ground truth: ERA5.")
        return sb.toString()
    }
}
