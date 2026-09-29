package com.foreblendcast.app.ui.screens

import android.graphics.Bitmap
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Button
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.foreblendcast.app.data.Bounds
import com.foreblendcast.app.data.Replay
import com.foreblendcast.app.map.IndiaMap
import com.foreblendcast.app.ui.AppViewModel
import com.foreblendcast.app.ui.components.SectionCard
import com.foreblendcast.app.ui.components.StatTile
import com.foreblendcast.app.ui.theme.Forest
import kotlinx.coroutines.delay
import java.util.Locale

private data class Step(val label: String, val raster: String, val date: String, val title: String, val body: String, val metrics: List<Pair<String, String>>)

private fun mm(x: Double?) = if (x == null) "—" else "%.0f mm".format(Locale.US, x)
private fun pct(x: Double?) = if (x == null) "—" else "%.0f%%".format(Locale.US, x * 100)

/** Every number comes from results/replay.json, written by the pipeline. */
private fun stepsOf(r: Replay): List<Step> {
    val where = r.states.joinToString(" & ")
    val out = r.steps.map { s ->
        val flagged = listOf("red", "orange", "yellow").sumOf { s.tiers[it] ?: 0 }
        val v = s.verification
        Step(
            "D+${s.lead_day}", s.raster.removeSuffix(".png"), "Cycle ${s.init} 00Z · D+${s.lead_day}",
            "Lead day ${s.lead_day}: forecast for ${s.valid}",
            "Issued from the ${s.init} cycle with weights frozen on earlier years. $flagged of the $where districts are at yellow or above " +
                "(${s.tiers["red"] ?: 0} red, ${s.tiers["orange"] ?: 0} orange, ${s.tiers["yellow"] ?: 0} yellow)." +
                (if (v != null) " Verified afterwards: ${v.hits} hits, ${v.misses} misses, ${v.false_alarms} false alarms." else ""),
            listOf("Blend peak" to mm(s.blend_peak_mm), "Max P(≥64.5)" to pct(s.max_p_gt_64p5), "RMSE" to (v?.rmse_mm?.let { "%.1f mm".format(Locale.US, it) } ?: "—")),
        )
    }.toMutableList()
    r.verification?.let { v ->
        out += Step(
            "Truth", v.raster.removeSuffix(".png"), "${r.target_date} · ERA5", "What ERA5 recorded",
            "${v.districts_with_heavy_rain} of ${v.districts_in_focus} districts in $where had heavy rain (${v.definition}). ${r.note}",
            listOf("ERA5 peak" to mm(v.observed_peak_mm), "Heavy-rain districts" to v.districts_with_heavy_rain.toString()),
        )
    }
    return out
}

/** Case replay: three successive cycles for one target day, then the truth raster. */
@Composable
fun ReplayScreen(vm: AppViewModel, onBack: () -> Unit) {
    val geo by vm.geo.collectAsStateWithLifecycle()
    var idx by remember { mutableIntStateOf(0) }
    var playing by remember { mutableStateOf(false) }
    var overlay by remember { mutableStateOf<Bitmap?>(null) }
    var bounds by remember { mutableStateOf<Bounds?>(null) }
    var steps by remember { mutableStateOf<List<Step>>(emptyList()) }
    var failed by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) {
        bounds = runCatching { vm.repo.bounds().data }.getOrNull()
        runCatching { stepsOf(vm.repo.replay().data) }.onSuccess { steps = it }.onFailure { failed = true }
    }
    if (steps.isEmpty()) {
        Column(Modifier.fillMaxSize().padding(16.dp)) {
            IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back") }
            Text(if (failed) "The replay has not been generated by the pipeline." else "Loading replay…", style = MaterialTheme.typography.bodyMedium)
        }
        return
    }
    val step = steps[idx.coerceIn(0, steps.size - 1)]
    LaunchedEffect(idx, steps) { overlay = vm.repo.rasterBitmap(step.raster)?.data }
    LaunchedEffect(playing) { while (playing) { delay(2200); idx = (idx + 1) % steps.size; if (idx == 0) playing = false } }

    Column(Modifier.fillMaxSize()) {
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back") }
            Column(Modifier.weight(1f)) {
                Text("Assam–Meghalaya 2022 replay", style = MaterialTheme.typography.titleLarge, color = MaterialTheme.colorScheme.primary)
                Text("Out-of-sample case study · held-out test year", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
        Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = 12.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                steps.forEachIndexed { i, s ->
                    FilterChip(selected = i == idx, onClick = { idx = i; playing = false }, label = { Text(s.label) },
                        colors = FilterChipDefaults.filterChipColors(selectedContainerColor = Forest, selectedLabelColor = Color.White))
                }
                Spacer(Modifier.weight(1f))
                if (playing) OutlinedButton(onClick = { playing = false }) { Text("Pause") } else Button(onClick = { idx = 0; playing = true }) { Text("Play") }
            }
            Box(Modifier.fillMaxWidth().height(320.dp).clip(RoundedCornerShape(14.dp))) {
                IndiaMap(geo = geo, fills = emptyMap(), fillsKey = "replay", modifier = Modifier.fillMaxSize(), overlay = overlay, overlayBounds = bounds, overlayAlpha = 0.85f, neutralFill = Color(0xFFF1F4F2))
                Text(step.date, Modifier.align(Alignment.TopStart).padding(8.dp).clip(RoundedCornerShape(6.dp)).background(Forest).padding(horizontal = 8.dp, vertical = 4.dp), color = Color.White, style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.Bold)
            }
            SectionCard(step.title, subtitle = step.date) {
                Text(step.body, style = MaterialTheme.typography.bodyMedium)
                Spacer(Modifier.height(8.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) { step.metrics.forEach { (k, v) -> StatTile(k, v, Modifier.weight(1f)) } }
            }
            Text("Each frame is the blend from a different cycle, all valid for the same day, then the ERA5 24 h accumulation. 2022 is a held-out test year. Pinch to zoom into the north-east.", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Spacer(Modifier.height(12.dp))
        }
    }
}
