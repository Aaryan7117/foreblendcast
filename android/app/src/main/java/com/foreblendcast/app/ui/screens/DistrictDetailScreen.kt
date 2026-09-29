package com.foreblendcast.app.ui.screens

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
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Button
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.foreblendcast.app.data.District
import com.foreblendcast.app.data.LocalInsights
import com.foreblendcast.app.data.Settings
import com.foreblendcast.app.data.SmsDispatchRequest
import com.foreblendcast.app.data.Tier
import com.foreblendcast.app.ui.AppViewModel
import com.foreblendcast.app.ui.UiState
import com.foreblendcast.app.ui.components.BarRow
import com.foreblendcast.app.ui.components.LoadingBox
import com.foreblendcast.app.ui.components.SectionCard
import com.foreblendcast.app.ui.components.SourceBadge
import com.foreblendcast.app.ui.components.StatTile
import com.foreblendcast.app.ui.components.TierChip
import com.foreblendcast.app.ui.components.color
import com.foreblendcast.app.ui.components.fmtMm
import com.foreblendcast.app.ui.components.fmtPct
import com.foreblendcast.app.ui.components.fmtPop
import com.foreblendcast.app.ui.components.modelColor
import com.foreblendcast.app.ui.components.modelLabel
import com.foreblendcast.app.ui.theme.TierGreen
import com.foreblendcast.app.ui.theme.TierOrange
import com.foreblendcast.app.ui.theme.TierRed
import kotlinx.coroutines.launch
import java.util.Locale

@Composable
fun DistrictDetailScreen(vm: AppViewModel, districtId: String, onBack: () -> Unit, onAskCopilot: (String) -> Unit, onOpenBlender: () -> Unit) {
    val state by vm.districts.collectAsStateWithLifecycle()
    val leadDay by vm.leadDay.collectAsStateWithLifecycle()
    val leads by vm.availableLeadDays.collectAsStateWithLifecycle()
    val d = (state as? UiState.Ready)?.value?.data?.districts?.firstOrNull { it.id == districtId }
    val meta = (state as? UiState.Ready)?.value?.data?.meta

    Column(Modifier.fillMaxSize()) {
        Row(Modifier.fillMaxWidth().padding(end = 8.dp), verticalAlignment = Alignment.CenterVertically) {
            IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back") }
            Column(Modifier.weight(1f)) {
                Text(d?.name ?: districtId, style = MaterialTheme.typography.titleLarge, color = MaterialTheme.colorScheme.primary)
                Text(d?.state ?: "", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            SourceBadge(vm.source())
        }
        if (state is UiState.Loading || d == null) { LoadingBox(); return }

        Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = 12.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            // Lead-day strip
            Row(horizontalArrangement = Arrangement.spacedBy(6.dp), verticalAlignment = Alignment.CenterVertically) {
                Text("Lead", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                leads.forEach { ld -> FilterChip(selected = leadDay == ld, onClick = { vm.setLeadDay(ld) }, label = { Text("D+$ld") }) }
                if (meta != null) Text("valid ${LocalInsights.validDate(meta, leadDay)}", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }

            // Tier banner
            Row(
                Modifier.fillMaxWidth().clip(RoundedCornerShape(12.dp)).background(d.tierEnum.color().copy(alpha = 0.12f)).padding(12.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column(Modifier.weight(1f)) {
                    Text(d.tierEnum.label, style = MaterialTheme.typography.titleMedium, color = d.tierEnum.color())
                    Text(d.tierEnum.range, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    if (d.heatwave) Text("Heatwave likely", style = MaterialTheme.typography.labelSmall, color = TierOrange)
                    if (d.high_wind) Text("Strong wind likely", style = MaterialTheme.typography.labelSmall, color = TierOrange)
                }
                TierChip(d.tierEnum)
            }

            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                StatTile("P90 rain 24h", fmtMm(d.precip_p90_mm, 1), Modifier.weight(1f), sub = if (d.precip_q05_mm != null && d.precip_q95_mm != null) "90% interval ${fmtMm(d.precip_q05_mm, 0)}–${fmtMm(d.precip_q95_mm, 0)}" else "area-weighted P90")
                StatTile("Exposed", fmtPop(d.population), Modifier.weight(1f), sub = d.population_source.ifBlank { "WorldPop" })
                StatTile("Disagreement", "%.2f".format(Locale.US, d.disagreement), Modifier.weight(1f), sub = if (d.disagreement > 2) "high vs training norm" else if (d.disagreement > 1.5) "above training norm" else "normal", accent = if (d.disagreement > 2) TierRed else null)
            }

            if (d.tmax_c != null || d.wind_ms != null) {
                SectionCard("Heat and wind", subtitle = "Temperature is the 12 UTC (17:30 IST) value, a proxy for Tmax") {
                    d.tmax_c?.let { t -> Text("Temperature %.1f °C%s".format(Locale.US, t, d.t2m_anomaly_c?.let { a -> " (%+.1f °C vs normal)".format(Locale.US, a) } ?: ""), style = MaterialTheme.typography.bodySmall) }
                    d.p_hot_40?.let { BarRow("P(≥ 40 °C) hot day", it.toFloat(), fmtPct(it, 1), Tier.YELLOW.color()) }
                    d.p_heatwave?.let { BarRow("P(heatwave)", it.toFloat(), fmtPct(it, 1), Tier.ORANGE.color()) }
                    d.wind_ms?.let { w -> Text("Wind %.1f m/s (%.0f km/h), district P90".format(Locale.US, w, w * 3.6), style = MaterialTheme.typography.bodySmall) }
                    d.p_wind_8?.let { BarRow("P(≥ 8 m/s) fresh wind", it.toFloat(), fmtPct(it, 1), Tier.YELLOW.color()) }
                    d.p_wind_10p8?.let { BarRow("P(≥ 10.8 m/s) strong wind", it.toFloat(), fmtPct(it, 1), Tier.ORANGE.color()) }
                }
            }

            SectionCard("Exceedance probabilities", subtitle = "Calibrated on training years") {
                BarRow("P(> 64.5 mm) heavy", d.p_gt_64p5.toFloat(), fmtPct(d.p_gt_64p5, 1), Tier.YELLOW.color())
                BarRow("P(> 115.6 mm) very heavy", d.p_gt_115p6.toFloat(), fmtPct(d.p_gt_115p6, 1), Tier.ORANGE.color())
                BarRow("P(> 204.5 mm) extremely heavy", d.p_gt_204p5.toFloat(), fmtPct(d.p_gt_204p5, 1), Tier.RED.color())
            }

            SectionCard("Blend weights", subtitle = "Context-aware shrinkage · ${d.shrinkage?.level_used ?: "n/a"} level, n_eff ${d.shrinkage?.n_eff?.toInt() ?: 0}",
                trailing = { TextButton(onClick = { vm.adoptDistrictWeights(d); vm.setBlenderEnabled(true); onOpenBlender() }) { Text("Override") } }) {
                d.weights.entries.sortedByDescending { it.value }.forEach { (m, w) -> BarRow(modelLabel(m), w.toFloat(), fmtPct(w, 1), modelColor(m)) }
                if (!d.shrinkage?.reason.isNullOrBlank()) Text("Reason: ${d.shrinkage?.reason}", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }

            SectionCard("Leave-one-model-out sensitivity", subtitle = "RMSE change on training days when a model is removed") {
                val maxAbs = d.lomo_rmse_increase_pct.values.maxOfOrNull { kotlin.math.abs(it) }?.takeIf { it > 0 } ?: 1.0
                d.lomo_rmse_increase_pct.entries.sortedByDescending { it.value }.forEach { (m, p) ->
                    BarRow("Remove ${modelLabel(m)}", (kotlin.math.abs(p) / maxAbs).toFloat(), "%+.1f%%".format(Locale.US, p), if (p > 5) TierRed else if (p > 0) TierOrange else TierGreen)
                }
                if (d.mostCriticalModel.isNotEmpty()) Text("Most critical model: ${modelLabel(d.mostCriticalModel)}", style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.SemiBold)
            }

            SectionCard("What this means for you", subtitle = "Impact-based guidance per persona") {
                LocalInsights.impactCards(d).forEach { c ->
                    Row(Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
                        Text(c.label, style = MaterialTheme.typography.labelMedium, modifier = Modifier.width(96.dp), color = MaterialTheme.colorScheme.primary)
                        Text(c.action, style = MaterialTheme.typography.bodySmall, modifier = Modifier.weight(1f))
                    }
                }
            }

            SmsCard(vm, d, leadDay, meta?.let { LocalInsights.validDate(it, leadDay) } ?: "")

            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(onClick = { onAskCopilot("Why is ${d.name} ${d.tier}?") }, modifier = Modifier.weight(1f)) { Text("Ask copilot why") }
                OutlinedButton(onClick = { onAskCopilot("LOMO sensitivity for ${d.name}") }, modifier = Modifier.weight(1f)) { Text("Explain LOMO") }
            }
            Spacer(Modifier.height(16.dp))
        }
    }
}

@Composable
private fun SmsCard(vm: AppViewModel, d: District, leadDay: Int, validDate: String) {
    val scope = rememberCoroutineScope()
    val phoneSaved by vm.settings.phone.collectAsStateWithLifecycle()
    val langSaved by vm.settings.language.collectAsStateWithLifecycle()
    var phone by remember(phoneSaved) { mutableStateOf(phoneSaved) }
    var lang by remember(langSaved) { mutableStateOf(langSaved) }
    var preview by remember { mutableStateOf<String?>(null) }
    var previewMeta by remember { mutableStateOf("") }
    var status by remember { mutableStateOf<String?>(null) }
    var busy by remember { mutableStateOf(false) }

    LaunchedEffect(d.id, lang, leadDay) {
        preview = null
        val r = runCatching { vm.repo.smsPreview(d.id, lang, leadDay) }
        preview = r.getOrNull()?.text ?: if (lang == "en") LocalInsights.smsTextEn(d, validDate) else null
        previewMeta = r.getOrNull()?.let { "${it.chars} chars · ${it.encoding} · ${it.segments} segment(s)" } ?: (if (lang == "en") "offline preview" else "server needed for this language")
    }

    SectionCard("SMS alert", subtitle = "Demo path: Android SMS gateway · production: CAP 1.2 → NDMA SACHET") {
        Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            Settings.LANGUAGES.forEach { (code, label) -> FilterChip(selected = lang == code, onClick = { lang = code; vm.settings.setLanguage(code) }, label = { Text(label) }) }
        }
        Spacer(Modifier.height(6.dp))
        Box(Modifier.fillMaxWidth().clip(RoundedCornerShape(10.dp)).background(MaterialTheme.colorScheme.surfaceVariant).padding(10.dp)) {
            Text(preview ?: "Generating preview…", style = MaterialTheme.typography.bodySmall)
        }
        Text(previewMeta, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Spacer(Modifier.height(6.dp))
        OutlinedTextField(value = phone, onValueChange = { phone = it }, label = { Text("Phone (+91…)") }, singleLine = true, modifier = Modifier.fillMaxWidth())
        Spacer(Modifier.height(6.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(
                enabled = !busy && phone.isNotBlank(),
                onClick = {
                    busy = true; status = null
                    vm.settings.setPhone(phone)
                    scope.launch {
                        val r = runCatching { vm.repo.smsDispatch(SmsDispatchRequest(d.id, phone.trim(), lang, leadDay)) }
                        status = r.fold({ "Server says: ${it.message}${it.detail?.let { d -> " ($d)" } ?: ""}" }, { "Failed: ${it.message}" })
                        busy = false
                    }
                },
                modifier = Modifier.weight(1f),
            ) { Text(if (busy) "Sending…" else "Send alert SMS") }
            OutlinedButton(
                enabled = !busy && phone.isNotBlank(),
                onClick = {
                    scope.launch {
                        val r = runCatching { vm.repo.subscribe(com.foreblendcast.app.data.SubscriptionRequest(phone.trim(), d.id, lang)) }
                        status = r.fold({ "Subscribed ${phone.trim()} to ${d.name}" }, { "Subscribe failed: ${it.message}" })
                    }
                },
            ) { Text("Subscribe") }
        }
        if (status != null) Text(status!!, style = MaterialTheme.typography.bodySmall, color = if (status!!.startsWith("Failed") || status!!.contains("failed")) TierRed else MaterialTheme.colorScheme.primary, modifier = Modifier.padding(top = 6.dp))
        Text("Every message carries the EXERCISE tag. 160 chars GSM-7, 70 chars per segment in Indian scripts.", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.padding(top = 4.dp))
    }
}

@Suppress("unused")
private val neutral = Color.Gray
