package com.foreblendcast.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.foreblendcast.app.data.District
import com.foreblendcast.app.data.Tier
import com.foreblendcast.app.ui.AppViewModel
import com.foreblendcast.app.ui.UiState
import com.foreblendcast.app.ui.components.ErrorBox
import com.foreblendcast.app.ui.components.LoadingBox
import com.foreblendcast.app.ui.components.SourceBadge
import com.foreblendcast.app.ui.components.TierChip
import com.foreblendcast.app.ui.components.color
import com.foreblendcast.app.ui.components.fmtMm
import com.foreblendcast.app.ui.components.fmtPct
import com.foreblendcast.app.ui.components.fmtPop
import java.util.Locale

private enum class Sort(val label: String) { RISK("Risk"), RAIN("Rain"), POP("Exposed"), SPREAD("Spread"), NAME("A–Z") }

@Composable
fun DistrictsScreen(vm: AppViewModel, onOpenDistrict: (String) -> Unit) {
    val state by vm.districts.collectAsStateWithLifecycle()
    val query by vm.query.collectAsStateWithLifecycle()
    val tierFilter by vm.tierFilter.collectAsStateWithLifecycle()
    val leadDay by vm.leadDay.collectAsStateWithLifecycle()
    var sort by remember { mutableStateOf(Sort.RISK) }

    Column(Modifier.fillMaxSize().padding(horizontal = 12.dp)) {
        Row(Modifier.fillMaxWidth().padding(top = 8.dp), verticalAlignment = Alignment.CenterVertically) {
            Text("Districts · D+$leadDay", style = MaterialTheme.typography.titleLarge, color = MaterialTheme.colorScheme.primary, modifier = Modifier.weight(1f))
            SourceBadge(vm.source())
        }
        OutlinedTextField(
            value = query, onValueChange = vm::setQuery, singleLine = true,
            placeholder = { Text("Search district, state or ID…") },
            modifier = Modifier.fillMaxWidth().padding(vertical = 6.dp), shape = RoundedCornerShape(12.dp),
        )
        Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            FilterChip(selected = tierFilter == null, onClick = { vm.setTierFilter(null) }, label = { Text("All") })
            Tier.entries.forEach { t ->
                FilterChip(
                    selected = tierFilter == t, onClick = { vm.setTierFilter(if (tierFilter == t) null else t) },
                    label = { Text(t.key.replaceFirstChar { it.uppercase() }) },
                    leadingIcon = { Box(Modifier.size(8.dp).clip(CircleShape).background(t.color())) },
                )
            }
        }
        Row(Modifier.fillMaxWidth().padding(vertical = 4.dp), horizontalArrangement = Arrangement.spacedBy(6.dp), verticalAlignment = Alignment.CenterVertically) {
            Text("Sort", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Sort.entries.forEach { s -> FilterChip(selected = sort == s, onClick = { sort = s }, label = { Text(s.label) }) }
        }

        when (val s = state) {
            is UiState.Loading -> LoadingBox()
            is UiState.Error -> ErrorBox(s.message, onRetry = { vm.refresh() })
            is UiState.Ready -> {
                val q = query.trim().lowercase(Locale.US)
                val rows = remember(s, q, tierFilter, sort) {
                    var list = s.value.data.districts
                    if (tierFilter != null) list = list.filter { it.tierEnum == tierFilter }
                    if (q.isNotEmpty()) list = list.filter { it.name.lowercase(Locale.US).contains(q) || it.state.lowercase(Locale.US).contains(q) || it.id.lowercase(Locale.US).contains(q) }
                    when (sort) {
                        Sort.RISK -> list.sortedWith(compareBy<District> { it.tierEnum.ordinal }.thenByDescending { it.p_gt_115p6 }.thenByDescending { it.precip_p90_mm })
                        Sort.RAIN -> list.sortedByDescending { it.precip_p90_mm }
                        Sort.POP -> list.sortedWith(compareBy<District> { it.tierEnum.ordinal }.thenByDescending { it.population })
                        Sort.SPREAD -> list.sortedByDescending { it.disagreement }
                        Sort.NAME -> list.sortedBy { it.name }
                    }
                }
                Text("${rows.size} of ${s.value.data.districts.size} districts", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.padding(bottom = 4.dp))
                LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(bottom = 12.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    items(rows, key = { it.id }) { d -> DistrictRow(d) { vm.selectDistrict(d.id); onOpenDistrict(d.id) } }
                }
            }
        }
    }
}

@Composable
fun DistrictRow(d: District, onClick: () -> Unit) {
    Row(
        Modifier.fillMaxWidth().clip(RoundedCornerShape(12.dp)).background(MaterialTheme.colorScheme.surface).clickable(onClick = onClick).padding(12.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Box(Modifier.width(6.dp).height(40.dp).clip(RoundedCornerShape(3.dp)).background(d.tierEnum.color()))
        Spacer(Modifier.width(10.dp))
        Column(Modifier.weight(1f)) {
            Text(d.name, style = MaterialTheme.typography.titleSmall)
            Text(d.state, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(
                "P90 ${fmtMm(d.precip_p90_mm, 0)} · P>115 ${fmtPct(d.p_gt_115p6)} · ${fmtPop(d.population)}",
                style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        Column(horizontalAlignment = Alignment.End) {
            TierChip(d.tierEnum, compact = true)
            Spacer(Modifier.height(4.dp))
            Text("σ ${"%.2f".format(Locale.US, d.disagreement)}", style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.SemiBold, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}
