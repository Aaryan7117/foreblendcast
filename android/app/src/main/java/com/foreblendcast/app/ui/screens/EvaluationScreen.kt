package com.foreblendcast.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.foreblendcast.app.data.Repository
import com.foreblendcast.app.ui.AppViewModel
import com.foreblendcast.app.ui.UiState
import com.foreblendcast.app.ui.components.Band
import com.foreblendcast.app.ui.components.ErrorBox
import com.foreblendcast.app.ui.components.HBarChart
import com.foreblendcast.app.ui.components.LineChart
import com.foreblendcast.app.ui.components.LoadingBox
import com.foreblendcast.app.ui.components.SectionCard
import com.foreblendcast.app.ui.components.Series
import com.foreblendcast.app.ui.components.SourceBadge
import com.foreblendcast.app.ui.components.fmtNum
import com.foreblendcast.app.ui.components.modelColor
import com.foreblendcast.app.ui.components.modelLabel
import com.foreblendcast.app.ui.theme.Forest
import com.foreblendcast.app.ui.theme.Rain
import java.util.Locale

@Composable
fun EvaluationScreen(vm: AppViewModel) {
    LaunchedEffect(Unit) { vm.ensureEvaluationLoaded() }
    val ladder by vm.ladder.collectAsStateWithLifecycle()
    val fss by vm.fss.collectAsStateWithLifecycle()
    val rev by vm.rev.collectAsStateWithLifecycle()
    val wwl by vm.wwl.collectAsStateWithLifecycle()
    val points by vm.points.collectAsStateWithLifecycle()
    val city by vm.pointsCity.collectAsStateWithLifecycle()
    val leadDay by vm.leadDay.collectAsStateWithLifecycle()

    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = 12.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Row(Modifier.fillMaxWidth().padding(top = 8.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text("Verification", style = MaterialTheme.typography.titleLarge, color = MaterialTheme.colorScheme.primary)
                Text("Leakage-free ladder · held-out years · truth ERA5", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            SourceBadge((ladder as? UiState.Ready)?.value?.source)
        }

        // ── Ladder ──
        when (val s = ladder) {
            is UiState.Loading -> LoadingBox()
            is UiState.Error -> ErrorBox(s.message, onRetry = { vm.refresh(); vm.ensureEvaluationLoaded() })
            is UiState.Ready -> {
                val l = s.value.data
                val key = if (l.rows.any { it.metrics.containsKey("L$leadDay") }) "L$leadDay" else (l.rows.firstOrNull()?.metrics?.keys?.firstOrNull() ?: "L1")
                val order = mapOf("ceiling" to 0, "blend" to 1, "single" to 2, "baseline" to 3, "floor" to 4)
                val rows = l.rows.sortedWith(compareBy<com.foreblendcast.app.data.LadderRow> { order[it.rung] ?: 9 }.thenBy { it.metrics[key]?.rmse ?: 999.0 })
                val gain = l.headline.pct_of_achievable_gain[key]
                SectionCard("Baseline ladder · lead ${key.drop(1)}", subtitle = "Best single: ${modelLabel(l.headline.best_single)} · ours: ${modelLabel(l.headline.ours)}" + (if (l.headline.test_years.isNotEmpty()) " · test ${l.headline.test_years.joinToString("+")}" else "")) {
                    HBarChart(rows.map { r -> Triple("${modelLabel(r.strategy)} (${r.rung})", r.metrics[key]?.rmse?.toFloat(), if (r.rung == "blend") Forest else if (r.rung == "ceiling") Rain else modelColor(r.strategy).copy(alpha = 0.7f)) }, unit = " mm")
                    Spacer(Modifier.height(8.dp))
                    Row(Modifier.horizontalScroll(rememberScrollState())) {
                        Column {
                            LadderHeader()
                            rows.forEach { r -> LadderLine(r.rung, modelLabel(r.strategy), r.metrics[key]) }
                        }
                    }
                    if (gain != null) Text("Gap to the oracle captured: ${"%.0f".format(Locale.US, gain)}% (best single model → oracle span)", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.padding(top = 6.dp))
                    val ci = rows.firstOrNull { it.rung == "blend" }?.metrics?.get(key)?.ci_rmse_vs_best_single
                    if (ci != null && ci.size == 2) Text("Bootstrap 95% CI, blend RMSE − best single: [${fmtNum(ci[0], 2)}, ${fmtNum(ci[1], 2)}] mm", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        }

        // ── Plume / meteogram ──
        SectionCard("Rainfall plume", subtitle = "Members, blend and q05–q95 band vs. lead day", trailing = { }) {
            Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                Repository.CITIES.forEach { (slug, label) -> FilterChip(selected = city == slug, onClick = { vm.setPointsCity(slug) }, label = { Text(label) }) }
            }
            Spacer(Modifier.height(6.dp))
            when (val p = points) {
                is UiState.Loading -> LoadingBox()
                is UiState.Error -> ErrorBox(p.message)
                is UiState.Ready -> {
                    val d = p.value.data
                    val x = d.lead_days.map { it.toFloat() }
                    val series = d.members.map { (m, v) -> Series(modelLabel(m), v.map { it?.toFloat() }, modelColor(m), width = 1.5.dp, dashed = m == "ens") } +
                        Series("ForeBlendCast", d.blend.map { it?.toFloat() }, Forest, width = 2.5.dp, markers = true) +
                        Series("ERA5 obs", d.obs.map { it?.toFloat() }, Color(0xFF64748B), width = 1.5.dp, dashed = true)
                    LineChart(x, series, band = Band(d.q05.map { it?.toFloat() }, d.q95.map { it?.toFloat() }, Forest.copy(alpha = 0.10f)), yLabel = "mm / 24 h", xLabel = "lead day", markerX = leadDay.toFloat())
                    Text("${d.city} (${d.lat}°N, ${d.lon}°E) · gaps = leads not archived", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        }

        // ── FSS ──
        when (val s = fss) {
            is UiState.Ready -> {
                val leadsAvail = s.value.data.leads.keys
                val key = if ("L$leadDay" in leadsAvail) "L$leadDay" else leadsAvail.firstOrNull()
                val entries = key?.let { s.value.data.leads[it] } ?: emptyList()
                if (entries.isNotEmpty()) SectionCard("Fractions skill score vs. scale", subtitle = "Lead ${key?.drop(1)} · dotted = useful-skill line 0.5 + f0/2") {
                    val x = entries.first().scales_km.map { it.toFloat() }
                    val cols = listOf(Color(0xFF16A34A), Color(0xFFF59E0B), Color(0xFFEA580C), Color(0xFFDC2626))
                    val series = entries.mapIndexed { i, e -> Series("> ${e.threshold_mm} mm", e.fss.map { it.toFloat() }, cols[i % cols.size], markers = true) } +
                        Series("useful", entries.first().scales_km.map { entries.first().fss_useful.toFloat() }, Color.Gray, width = 1.dp, dashed = true)
                    LineChart(x, series, yLabel = "FSS", xLabel = "neighbourhood km", yMin = 0f, yMax = 1f)
                }
            }
            is UiState.Error -> ErrorBox("FSS: ${s.message}")
            else -> {}
        }

        // ── REV ──
        when (val s = rev) {
            is UiState.Ready -> {
                val r = s.value.data
                val curves: Map<String, List<Double>> = if (r.curves.isNotEmpty()) r.curves else if (r.rev.isNotEmpty()) mapOf("blend" to r.rev) else emptyMap()
                if (curves.isNotEmpty() && r.cost_loss.isNotEmpty()) SectionCard("Relative economic value", subtitle = "Value of acting on P(>64.5 mm) across cost/loss ratios" + (r.headline_cl?.let { " · headline C/L $it" } ?: "")) {
                    LineChart(r.cost_loss.map { it.toFloat() }, curves.map { (k, v) -> Series(modelLabel(k), v.map { it.toFloat() }, if (k == "blend") Forest else modelColor(k)) }, yLabel = "REV", xLabel = "cost / loss", yMin = 0f, yMax = 1f, xTickFormat = { "%.1f".format(Locale.US, it) })
                }
            }
            is UiState.Error -> ErrorBox("REV: ${s.message}")
            else -> {}
        }

        // ── Where we lose ──
        when (val s = wwl) {
            is UiState.Ready -> {
                val cells = s.value.data.cells.filter { it.lead_day == leadDay || s.value.data.cells.none { c -> c.lead_day == leadDay } }
                SectionCard("Where we lose", subtitle = "Regimes where a single model beats the blend — reported, not hidden") {
                    if (cells.isEmpty()) Text("No cells where a single model significantly beats the blend at this lead.", style = MaterialTheme.typography.bodySmall)
                    cells.forEach { c ->
                        Column(Modifier.fillMaxWidth().padding(vertical = 4.dp).clip(RoundedCornerShape(8.dp)).background(MaterialTheme.colorScheme.surfaceVariant).padding(8.dp)) {
                            Text("${c.district} · D+${c.lead_day} · ${c.season} ${c.regime}", style = MaterialTheme.typography.labelMedium)
                            Text("Blend ${fmtNum(c.blend_rmse, 2)} vs ${modelLabel(c.best_single)} ${fmtNum(c.best_single_rmse, 2)} mm RMSE" + (if (c.ci.size == 2) " · CI [${fmtNum(c.ci[0], 2)}, ${fmtNum(c.ci[1], 2)}]" else ""), style = MaterialTheme.typography.bodySmall)
                            if (c.reason.isNotBlank()) Text(c.reason, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            if (c.override_available) Text("Override available", style = MaterialTheme.typography.labelSmall, color = Forest)
                        }
                    }
                }
            }
            is UiState.Error -> ErrorBox("Where-we-lose: ${s.message}")
            else -> {}
        }

        // ── Provenance ──
        (ladder as? UiState.Ready)?.value?.data?.meta?.let { m ->
            SectionCard("Provenance", subtitle = "Every results file carries this block") {
                listOf(
                    "Cycle" to m.cycle, "Generated" to m.generated_utc, "Commit" to m.git_commit, "Fixture" to m.fixture.toString(),
                    "Truth" to m.ground_truth, "Models" to m.models_used.joinToString(", "), "Strategy" to m.strategy,
                    "Window" to m.accumulation_window_utc + " UTC", "District agg." to m.district_aggregation, "Status" to m.status,
                ).forEach { (k, v) ->
                    Row(Modifier.padding(vertical = 1.dp)) {
                        Text(k, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.width(92.dp))
                        Text(v, style = MaterialTheme.typography.bodySmall, fontFamily = FontFamily.Monospace)
                    }
                }
            }
        }
        Spacer(Modifier.height(12.dp))
    }
}

@Composable
private fun LadderHeader() {
    Row {
        listOf("Rung" to 64, "Strategy" to 110, "RMSE" to 56, "MAE" to 56, "FSS" to 56, "Bias" to 56, "REV" to 56, "days" to 44).forEach { (h, w) ->
            Text(h, style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.Bold, modifier = Modifier.width(w.dp))
        }
    }
}

@Composable
private fun LadderLine(rung: String, strategy: String, m: com.foreblendcast.app.data.MetricValues?) {
    val bold = rung == "blend"
    val alpha = if (rung == "floor" || rung == "ceiling") 0.6f else 1f
    Row(Modifier.padding(vertical = 2.dp)) {
        val style = MaterialTheme.typography.bodySmall.copy(fontFamily = FontFamily.Monospace, fontWeight = if (bold) FontWeight.Bold else FontWeight.Normal, color = MaterialTheme.colorScheme.onSurface.copy(alpha = alpha))
        Text(rung, style = style, modifier = Modifier.width(64.dp))
        Text(strategy, style = style, modifier = Modifier.width(110.dp), maxLines = 1)
        Text(fmtNum(m?.rmse, 2), style = style, modifier = Modifier.width(56.dp))
        Text(fmtNum(m?.mae, 2), style = style, modifier = Modifier.width(56.dp))
        Text(fmtNum(m?.fss50, 2), style = style, modifier = Modifier.width(56.dp))
        Text(fmtNum(m?.freq_bias_64p5, 2), style = style, modifier = Modifier.width(56.dp))
        Text(fmtNum(m?.rev_cl0p1, 2), style = style, modifier = Modifier.width(56.dp))
        Text(m?.n_days?.toString() ?: "–", style = style, modifier = Modifier.width(44.dp))
    }
}
