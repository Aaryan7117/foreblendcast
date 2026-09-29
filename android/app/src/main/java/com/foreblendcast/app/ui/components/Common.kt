package com.foreblendcast.app.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.foreblendcast.app.data.DataSource
import com.foreblendcast.app.data.Tier
import com.foreblendcast.app.ui.theme.TierGreen
import com.foreblendcast.app.ui.theme.TierOrange
import com.foreblendcast.app.ui.theme.TierRed
import com.foreblendcast.app.ui.theme.TierYellow
import java.util.Locale

fun Tier.color(): Color = when (this) {
    Tier.RED -> TierRed
    Tier.ORANGE -> TierOrange
    Tier.YELLOW -> TierYellow
    Tier.GREEN -> TierGreen
}

fun Tier.softColor(): Color = color().copy(alpha = 0.14f)

fun fmtPct(x: Double, digits: Int = 0): String = "%.${digits}f%%".format(Locale.US, x * 100)
fun fmtMm(x: Double, digits: Int = 1): String = "%.${digits}f mm".format(Locale.US, x)
fun fmtPop(p: Long): String = when {
    p >= 10_000_000 -> "%.1f Cr".format(Locale.US, p / 1e7)
    p >= 100_000 -> "%.1f L".format(Locale.US, p / 1e5)
    else -> "%,d".format(Locale.US, p)
}
fun fmtNum(x: Double?, digits: Int = 3): String = if (x == null || x.isNaN() || x.isInfinite()) "N/A" else "%.${digits}f".format(Locale.US, x)
fun modelLabel(key: String): String = when (key.lowercase(Locale.US)) {
    "hres" -> "IFS HRES"
    "ens" -> "IFS ENS"
    "graphcast" -> "GraphCast"
    "pangu" -> "Pangu"
    "blend", "context_shrink_pm" -> "ForeBlendCast"
    "equal_weight" -> "Equal weights"
    "climatology" -> "Climatology"
    "oracle" -> "Oracle"
    "persistence" -> "Persistence"
    "inverse_error" -> "Inverse error"
    else -> key.replaceFirstChar { it.uppercase() }
}
fun modelColor(key: String): Color = when (key.lowercase(Locale.US)) {
    "hres" -> Color(0xFF1D4ED8)
    "ens" -> Color(0xFF7C3AED)
    "graphcast" -> Color(0xFFD97706)
    "pangu" -> Color(0xFFDB2777)
    else -> Color(0xFF0E3825)
}

@Composable
fun ExerciseBanner(modifier: Modifier = Modifier) {
    Row(
        modifier
            .fillMaxWidth()
            .background(Color(0xFFFFF4E5))
            .padding(horizontal = 12.dp, vertical = 6.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Box(Modifier.size(8.dp).clip(CircleShape).background(TierOrange))
        Spacer(Modifier.width(8.dp))
        Text(
            "EXERCISE — prototype output, not an official IMD warning",
            style = MaterialTheme.typography.labelSmall,
            color = Color(0xFF7C2D12),
        )
    }
}

@Composable
fun SourceBadge(source: DataSource?, modifier: Modifier = Modifier, error: String? = null) {
    val (label, color) = when (source) {
        DataSource.LIVE -> "LIVE API" to TierGreen
        DataSource.SNAPSHOT -> "SNAPSHOT" to TierOrange
        null -> "…" to Color.Gray
    }
    Row(modifier, verticalAlignment = Alignment.CenterVertically) {
        Box(Modifier.size(7.dp).clip(CircleShape).background(color))
        Spacer(Modifier.width(5.dp))
        Text(label, style = MaterialTheme.typography.labelSmall, color = color, fontWeight = FontWeight.Bold)
        if (source == DataSource.SNAPSHOT && !error.isNullOrBlank()) {
            Spacer(Modifier.width(6.dp))
            Text("· server: ${error.take(40)}", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 1)
        }
    }
}

@Composable
fun TierChip(tier: Tier, modifier: Modifier = Modifier, compact: Boolean = false) {
    Box(
        modifier
            .clip(RoundedCornerShape(6.dp))
            .background(tier.color())
            .padding(horizontal = if (compact) 6.dp else 8.dp, vertical = if (compact) 2.dp else 4.dp),
    ) {
        Text(
            if (compact) tier.key.uppercase() else tier.label.uppercase(),
            color = Color.White,
            style = MaterialTheme.typography.labelSmall,
            fontWeight = FontWeight.Bold,
        )
    }
}

@Composable
fun SectionCard(
    title: String,
    modifier: Modifier = Modifier,
    subtitle: String? = null,
    trailing: (@Composable () -> Unit)? = null,
    content: @Composable () -> Unit,
) {
    Card(
        modifier.fillMaxWidth(),
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
        border = androidx.compose.foundation.BorderStroke(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.5f)),
    ) {
        Column(Modifier.padding(14.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text(title, style = MaterialTheme.typography.titleSmall)
                    if (subtitle != null) Text(subtitle, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                trailing?.invoke()
            }
            Spacer(Modifier.height(10.dp))
            content()
        }
    }
}

@Composable
fun StatTile(label: String, value: String, modifier: Modifier = Modifier, sub: String? = null, accent: Color? = null) {
    Column(
        modifier
            .clip(RoundedCornerShape(10.dp))
            .background(accent?.copy(alpha = 0.12f) ?: MaterialTheme.colorScheme.surfaceVariant)
            .padding(10.dp),
    ) {
        Text(label.uppercase(), style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(value, style = MaterialTheme.typography.titleMedium, color = accent ?: MaterialTheme.colorScheme.onSurface, fontWeight = FontWeight.Bold)
        if (sub != null) Text(sub, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

@Composable
fun LoadingBox(modifier: Modifier = Modifier, text: String = "Loading…") {
    Column(modifier.fillMaxWidth().padding(24.dp), horizontalAlignment = Alignment.CenterHorizontally) {
        CircularProgressIndicator(Modifier.size(28.dp), strokeWidth = 3.dp)
        Spacer(Modifier.height(8.dp))
        Text(text, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

@Composable
fun ErrorBox(message: String, modifier: Modifier = Modifier, onRetry: (() -> Unit)? = null) {
    Column(
        modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(12.dp))
            .background(TierRed.copy(alpha = 0.08f))
            .border(1.dp, TierRed.copy(alpha = 0.3f), RoundedCornerShape(12.dp))
            .padding(14.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text("Could not load data", style = MaterialTheme.typography.titleSmall, color = TierRed)
        Text(message, style = MaterialTheme.typography.bodySmall, textAlign = TextAlign.Center, color = MaterialTheme.colorScheme.onSurfaceVariant)
        if (onRetry != null) { Spacer(Modifier.height(8.dp)); Button(onClick = onRetry) { Text("Retry") } }
    }
}

/** Horizontal bar with label + value, used for weights and LOMO. */
@Composable
fun BarRow(label: String, fraction: Float, valueText: String, color: Color, modifier: Modifier = Modifier) {
    Column(modifier.fillMaxWidth().padding(vertical = 3.dp)) {
        Row {
            Text(label, style = MaterialTheme.typography.bodySmall, modifier = Modifier.weight(1f))
            Text(valueText, style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.SemiBold)
        }
        Spacer(Modifier.height(3.dp))
        Box(Modifier.fillMaxWidth().height(8.dp).clip(RoundedCornerShape(4.dp)).background(color.copy(alpha = 0.15f))) {
            Box(Modifier.fillMaxWidth(fraction.coerceIn(0f, 1f)).height(8.dp).clip(RoundedCornerShape(4.dp)).background(color))
        }
    }
}

/**
 * Minimal renderer for the copilot's markdown subset: **bold**, "• / → / -" bullets and
 * pipe tables (rendered monospace). Enough for the grounded answers; no external library.
 */
@Composable
fun MarkdownText(text: String, modifier: Modifier = Modifier) {
    val lines = text.split('\n')
    Column(modifier) {
        var i = 0
        while (i < lines.size) {
            val line = lines[i]
            if (line.trimStart().startsWith("|")) {
                val tableLines = mutableListOf<String>()
                while (i < lines.size && lines[i].trimStart().startsWith("|")) { tableLines += lines[i]; i++ }
                MarkdownTable(tableLines)
                continue
            }
            if (line.isBlank()) { Spacer(Modifier.height(6.dp)); i++; continue }
            val trimmed = line.trimStart()
            val bullet = trimmed.startsWith("•") || trimmed.startsWith("→") || trimmed.startsWith("- ")
            Row(Modifier.padding(start = if (bullet) 6.dp else 0.dp, top = 1.dp, bottom = 1.dp)) {
                Text(inlineBold(trimmed.replace("**", "\u0000")), style = MaterialTheme.typography.bodyMedium)
            }
            i++
        }
    }
}

private fun inlineBold(markedText: String) = buildAnnotatedString {
    // \u0000 toggles bold on/off (placed by the caller for each "**").
    var bold = false
    markedText.split('\u0000').forEachIndexed { idx, seg ->
        if (idx > 0) bold = !bold
        if (bold) withStyle(SpanStyle(fontWeight = FontWeight.Bold)) { append(seg) } else append(seg)
    }
}

@Composable
private fun MarkdownTable(rows: List<String>) {
    val cells = rows.map { r -> r.trim().trim('|').split('|').map { it.trim() } }
        .filter { r -> r.none { c -> c.isNotEmpty() && c.all { ch -> ch == '-' || ch == ':' } } || r.any { it.isEmpty() } }
        .filter { r -> !r.all { c -> c.all { ch -> ch == '-' || ch == ':' } } }
    Column(
        Modifier
            .fillMaxWidth()
            .padding(vertical = 6.dp)
            .horizontalScroll(rememberScrollState())
            .border(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.5f), RoundedCornerShape(8.dp))
            .padding(8.dp),
    ) {
        cells.forEachIndexed { ri, r ->
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                r.forEach { c ->
                    Text(
                        c.replace("**", ""),
                        fontFamily = FontFamily.Monospace,
                        fontSize = 11.5.sp,
                        fontWeight = if (ri == 0) FontWeight.Bold else FontWeight.Normal,
                        modifier = Modifier.width(92.dp),
                        maxLines = 1,
                    )
                }
            }
        }
    }
}
