package com.foreblendcast.app.ui.screens

import android.graphics.Bitmap
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.AssistChip
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
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
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.foreblendcast.app.data.Bounds
import com.foreblendcast.app.data.LocalInsights
import com.foreblendcast.app.data.Tier
import com.foreblendcast.app.map.IndiaMap
import com.foreblendcast.app.ui.AppViewModel
import com.foreblendcast.app.ui.MapLayer
import com.foreblendcast.app.ui.UiState
import com.foreblendcast.app.ui.components.ErrorBox
import com.foreblendcast.app.ui.components.LoadingBox
import com.foreblendcast.app.ui.components.SourceBadge
import com.foreblendcast.app.ui.components.TierChip
import com.foreblendcast.app.ui.components.color
import com.foreblendcast.app.ui.components.fmtMm
import com.foreblendcast.app.ui.components.fmtPct
import com.foreblendcast.app.ui.components.fmtPop
import com.foreblendcast.app.ui.theme.Forest

@Composable
fun HomeScreen(vm: AppViewModel, onOpenDistrict: (String) -> Unit, onOpenReplay: () -> Unit, onOpenSettings: () -> Unit) {
    val districtsState by vm.districts.collectAsStateWithLifecycle()
    val geo by vm.geo.collectAsStateWithLifecycle()
    val leadDay by vm.leadDay.collectAsStateWithLifecycle()
    val layer by vm.layer.collectAsStateWithLifecycle()
    val selectedId by vm.selectedDistrictId.collectAsStateWithLifecycle()
    val leads by vm.availableLeadDays.collectAsStateWithLifecycle()
    val live by vm.live.collectAsStateWithLifecycle()
    val blenderOn by vm.blenderEnabled.collectAsStateWithLifecycle()

    // Raster overlay for non-tier layers (pre-rendered PNG from the API or the bundled snapshot)
    var overlay by remember { mutableStateOf<Bitmap?>(null) }
    var overlayBounds by remember { mutableStateOf<Bounds?>(null) }
    LaunchedEffect(layer, leadDay, blenderOn, live) {
        if (blenderOn && live != null && layer == MapLayer.RAINFALL) {
            overlay = live!!.bitmap
            overlayBounds = runCatching { vm.repo.bounds().data }.getOrNull()
        } else if (layer.png != null) {
            overlay = vm.repo.rasterBitmap("${layer.png}_L$leadDay")?.data
            overlayBounds = runCatching { vm.repo.bounds().data }.getOrNull()
        } else overlay = null
    }

    val districts = (districtsState as? UiState.Ready)?.value?.data?.districts ?: emptyList()
    val meta = (districtsState as? UiState.Ready)?.value?.data?.meta
    val fills: Map<String, Color> = remember(districts, layer, live, blenderOn) {
        when {
            layer == MapLayer.TIERS && blenderOn && live != null -> live!!.approxTiers.mapValues { it.value.color().copy(alpha = 0.9f) }
            layer == MapLayer.TIERS -> districts.associate { it.id to it.tierEnum.color().copy(alpha = if (it.tierEnum == Tier.GREEN) 0.35f else 0.92f) }
            else -> emptyMap()
        }
    }
    val fillsKey = "$layer|$leadDay|${districts.size}|${if (blenderOn) live?.weights.hashCode() else 0}"
    val summary = remember(districts) { if (districts.isEmpty()) null else LocalInsights.summary(districts) }

    Column(Modifier.fillMaxSize()) {
        // Header row
        Row(Modifier.fillMaxWidth().padding(start = 14.dp, end = 4.dp, top = 8.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text("ForeBlendCast", style = MaterialTheme.typography.titleLarge, color = MaterialTheme.colorScheme.primary)
                    Spacer(Modifier.width(8.dp))
                    SourceBadge(vm.source())
                }
                Text(
                    if (meta != null) "Cycle ${meta.cycle} · valid ${LocalInsights.validDate(meta, leadDay)} · truth ${meta.ground_truth}" else "Calibrated multi-model rainfall blend",
                    style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 1,
                )
            }
            IconButton(onClick = onOpenReplay) { Icon(Icons.Filled.PlayArrow, contentDescription = "Assam 2022 replay", tint = MaterialTheme.colorScheme.primary) }
            IconButton(onClick = { vm.refresh() }) { Icon(Icons.Filled.Refresh, contentDescription = "Refresh") }
            IconButton(onClick = onOpenSettings) { Icon(Icons.Filled.Settings, contentDescription = "Settings") }
        }

        // Lead day + layer chips
        Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()).padding(horizontal = 10.dp), horizontalArrangement = Arrangement.spacedBy(6.dp), verticalAlignment = Alignment.CenterVertically) {
            AssistChip(onClick = { vm.selectDistrict("AS-CACHAR") }, label = { Text("📍 Mera Sthan (GPS)") })
            Text("Lead", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            leads.forEach { d ->
                FilterChip(selected = leadDay == d, onClick = { vm.setLeadDay(d) }, label = { Text("D+$d") },
                    colors = FilterChipDefaults.filterChipColors(selectedContainerColor = Forest, selectedLabelColor = Color.White))
            }
            Spacer(Modifier.width(6.dp))
            Text("Layer", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            MapLayer.entries.forEach { l ->
                FilterChip(selected = layer == l, onClick = { vm.setLayer(l) }, label = { Text(l.short) })
            }
        }

        // Map
        Box(Modifier.fillMaxWidth().weight(1f).padding(horizontal = 10.dp, vertical = 6.dp).clip(RoundedCornerShape(14.dp))) {
            IndiaMap(
                geo = geo,
                fills = fills,
                fillsKey = fillsKey,
                modifier = Modifier.fillMaxSize(),
                overlay = overlay,
                overlayBounds = overlayBounds,
                overlayAlpha = if (layer == MapLayer.TIERS) 0f else 0.82f,
                selectedId = selectedId,
                neutralFill = if (layer == MapLayer.TIERS) Color(0xFFE8ECE9) else Color(0xFFF1F4F2),
                onTap = { shape -> if (shape != null) vm.selectDistrict(shape.id) },
            )
            Legend(layer, Modifier.align(Alignment.BottomStart).padding(8.dp))
            if (blenderOn && live != null) {
                Text(
                    "LIVE OVERRIDE · RMSE ${"%.2f".format(live!!.stats.rmse)} mm",
                    Modifier.align(Alignment.TopEnd).padding(8.dp).clip(RoundedCornerShape(6.dp)).background(Forest).padding(horizontal = 8.dp, vertical = 4.dp),
                    color = Color.White, style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.Bold,
                )
            }
            if (districtsState is UiState.Loading) LoadingBox(Modifier.align(Alignment.Center), "Loading forecast…")
        }

        // Bottom panel: tier counts + selected district
        Column(Modifier.fillMaxWidth().verticalScroll(rememberScrollState()).padding(horizontal = 10.dp).padding(bottom = 8.dp)) {
            when (val s = districtsState) {
                is UiState.Error -> ErrorBox(s.message, onRetry = { vm.refresh() })
                else -> {}
            }
            if (summary != null) {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    Tier.entries.forEach { t ->
                        TierCount(t, summary.counts[t] ?: 0, summary.exposed[t] ?: 0, Modifier.weight(1f)) { vm.setTierFilter(t) }
                    }
                }
                Spacer(Modifier.height(8.dp))
            }
            val sel = vm.district(selectedId)
            if (sel != null) {
                Row(
                    Modifier.fillMaxWidth().clip(RoundedCornerShape(12.dp)).background(MaterialTheme.colorScheme.surface)
                        .clickable { onOpenDistrict(sel.id) }.padding(12.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Box(Modifier.size(12.dp).clip(CircleShape).background(sel.tierEnum.color()))
                    Spacer(Modifier.width(10.dp))
                    Column(Modifier.weight(1f)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text("${sel.name}, ${sel.state}", style = MaterialTheme.typography.titleSmall)
                            if (sel.id == "AS-CACHAR") {
                                Spacer(Modifier.width(6.dp))
                                Text("📍 MERA STHAN", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.primary, fontWeight = FontWeight.Bold)
                            }
                        }
                        val hindiTier = when(sel.tierEnum) {
                            Tier.RED -> "लाल चेतावनी (अत्यधिक भारी वर्षा)"
                            Tier.ORANGE -> "नारंगी चेतावनी (भारी वर्षा)"
                            Tier.YELLOW -> "पीली चेतावनी (सतर्क रहें)"
                            Tier.GREEN -> "हरा संकेत (सामान्य मौसम)"
                        }
                        Text(hindiTier, style = MaterialTheme.typography.labelSmall, color = sel.tierEnum.color(), fontWeight = FontWeight.Bold)
                        Text(
                            "P90 ${fmtMm(sel.precip_p90_mm, 0)} · P(>115.6) ${fmtPct(sel.p_gt_115p6)} · ${fmtPop(sel.population)} people · σ ${"%.2f".format(sel.disagreement)}",
                            style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                    TierChip(sel.tierEnum, compact = true)
                }
                Text("Tap a district on the map · tap the card for details, impact cards and SMS", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.padding(top = 4.dp, start = 4.dp))
            }

        }
    }
}

@Composable
private fun TierCount(tier: Tier, count: Int, exposed: Long, modifier: Modifier, onClick: () -> Unit) {
    Column(
        modifier.clip(RoundedCornerShape(10.dp)).background(tier.color().copy(alpha = 0.12f)).clickable(onClick = onClick).padding(8.dp),
    ) {
        Text(tier.key.uppercase(), style = MaterialTheme.typography.labelSmall, color = tier.color(), fontWeight = FontWeight.Bold)
        Text("$count", style = MaterialTheme.typography.titleLarge, color = tier.color())
        Text(fmtPop(exposed), style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

@Composable
private fun Legend(layer: MapLayer, modifier: Modifier) {
    Column(modifier.clip(RoundedCornerShape(8.dp)).background(Color.White.copy(alpha = 0.88f)).padding(8.dp)) {
        Text(layer.label, style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.Bold, color = Color(0xFF1B1F1D))
        Spacer(Modifier.height(4.dp))
        when (layer) {
            MapLayer.TIERS -> Tier.entries.forEach { t -> LegendRow(t.color(), t.label) }
            MapLayer.RAINFALL -> listOf(0xFFDEEBF7 to "0–10 mm", 0xFF9ECAE1 to "10–50", 0xFF4292C6 to "50–100", 0xFF08519C to "100–200", 0xFF08306B to "200+").forEach { LegendRow(Color(it.first), it.second) }
            MapLayer.EXCEEDANCE -> listOf(0xFFFFFFB2 to "≥1%", 0xFFFECC5C to "25%", 0xFFFD8D3C to "50%", 0xFFE31A1C to "75–100%").forEach { LegendRow(Color(it.first), it.second) }
            MapLayer.DISAGREEMENT -> listOf(0xFF1A9850 to "low σ", 0xFFFEE08B to "moderate", 0xFFD73027 to "high σ ≥3").forEach { LegendRow(Color(it.first), it.second) }
        }
    }
}

@Composable
private fun LegendRow(color: Color, label: String) {
    Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.padding(vertical = 1.dp)) {
        Box(Modifier.size(10.dp).clip(RoundedCornerShape(2.dp)).background(color))
        Spacer(Modifier.width(5.dp))
        Text(label, style = MaterialTheme.typography.labelSmall, color = Color(0xFF1B1F1D))
    }
}
