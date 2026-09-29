package com.foreblendcast.app.ui.components

import androidx.compose.foundation.Canvas
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
import androidx.compose.foundation.layout.wrapContentHeight
import androidx.compose.foundation.background
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.nativeCanvas
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import java.util.Locale
import kotlin.math.ceil
import kotlin.math.floor
import kotlin.math.log10
import kotlin.math.pow

data class Series(
    val name: String,
    val y: List<Float?>,
    val color: Color,
    val width: Dp = 2.dp,
    val dashed: Boolean = false,
    val markers: Boolean = false,
)

/** Optional shaded band (lower/upper) e.g. q05–q95. */
data class Band(val lower: List<Float?>, val upper: List<Float?>, val color: Color)

/**
 * Compact line chart drawn with Compose Canvas. x positions are the given numeric x values
 * (lead days, scales in km, cost/loss ratios …); nulls break the line.
 */
@Composable
fun LineChart(
    x: List<Float>,
    series: List<Series>,
    modifier: Modifier = Modifier,
    band: Band? = null,
    height: Dp = 180.dp,
    yLabel: String = "",
    xLabel: String = "",
    markerX: Float? = null,
    yMin: Float? = null,
    yMax: Float? = null,
    xTickFormat: (Float) -> String = { v -> if (v == v.toInt().toFloat()) v.toInt().toString() else "%.2f".format(Locale.US, v) },
    showLegend: Boolean = true,
) {
    val density = LocalDensity.current
    val axisColor = MaterialTheme.colorScheme.outline
    val textColor = MaterialTheme.colorScheme.onSurfaceVariant
    val labelPx = with(density) { 10.sp.toPx() }

    val allY = (series.flatMap { it.y } + (band?.lower ?: emptyList()) + (band?.upper ?: emptyList())).filterNotNull()
    val lo = yMin ?: (allY.minOrNull() ?: 0f).let { if (it > 0f) 0f else it }
    val hi0 = yMax ?: (allY.maxOrNull() ?: 1f)
    val hi = if (hi0 <= lo) lo + 1f else niceCeil(hi0)
    val xLo = x.minOrNull() ?: 0f
    val xHi = (x.maxOrNull() ?: 1f).let { if (it <= xLo) xLo + 1f else it }

    Column(modifier.fillMaxWidth()) {
        Canvas(Modifier.fillMaxWidth().height(height)) {
            val padL = labelPx * 3.6f
            val padB = labelPx * 2.4f
            val padT = labelPx * 0.8f
            val padR = labelPx * 1.2f
            val w = size.width - padL - padR
            val h = size.height - padT - padB
            fun px(v: Float) = padL + (v - xLo) / (xHi - xLo) * w
            fun py(v: Float) = padT + (1f - (v - lo) / (hi - lo)) * h

            // grid + y ticks
            val yTicks = 4
            val paint = android.graphics.Paint().apply { color = textColor.hashCode(); textSize = labelPx; isAntiAlias = true }
            paint.color = android.graphics.Color.argb((textColor.alpha * 255).toInt(), (textColor.red * 255).toInt(), (textColor.green * 255).toInt(), (textColor.blue * 255).toInt())
            for (i in 0..yTicks) {
                val v = lo + (hi - lo) * i / yTicks
                val yy = py(v)
                drawLine(axisColor.copy(alpha = 0.35f), Offset(padL, yy), Offset(padL + w, yy), 1f)
                drawContext.canvas.nativeCanvas.drawText(fmtTick(v), 2f, yy + labelPx / 3, paint)
            }
            // x ticks
            val xs = x.distinct().sorted()
            val step = maxOf(1, ceil(xs.size / 6f).toInt())
            xs.forEachIndexed { i, v -> if (i % step == 0 || i == xs.lastIndex) {
                val xx = px(v)
                drawLine(axisColor.copy(alpha = 0.35f), Offset(xx, padT), Offset(xx, padT + h), 1f)
                val t = xTickFormat(v)
                drawContext.canvas.nativeCanvas.drawText(t, xx - paint.measureText(t) / 2, size.height - 2f, paint)
            } }
            drawLine(axisColor, Offset(padL, padT + h), Offset(padL + w, padT + h), 1.5f)
            drawLine(axisColor, Offset(padL, padT), Offset(padL, padT + h), 1.5f)

            // band
            if (band != null) {
                val p = Path(); var started = false
                for (i in x.indices) { val u = band.upper.getOrNull(i) ?: continue; if (!started) { p.moveTo(px(x[i]), py(u)); started = true } else p.lineTo(px(x[i]), py(u)) }
                for (i in x.indices.reversed()) { val l = band.lower.getOrNull(i) ?: continue; p.lineTo(px(x[i]), py(l)) }
                if (started) { p.close(); drawPath(p, band.color) }
            }
            // marker
            if (markerX != null && markerX in xLo..xHi) {
                drawLine(Color(0xFFDC2626), Offset(px(markerX), padT), Offset(px(markerX), padT + h), 2f,
                    pathEffect = PathEffect.dashPathEffect(floatArrayOf(8f, 6f)))
            }
            // series
            for (s in series) {
                val p = Path(); var started = false
                for (i in x.indices) {
                    val v = s.y.getOrNull(i)
                    if (v == null || v.isNaN()) { started = false; continue }
                    if (!started) { p.moveTo(px(x[i]), py(v)); started = true } else p.lineTo(px(x[i]), py(v))
                }
                drawPath(p, s.color, style = Stroke(width = s.width.toPx(), cap = StrokeCap.Round,
                    pathEffect = if (s.dashed) PathEffect.dashPathEffect(floatArrayOf(10f, 8f)) else null))
                if (s.markers) for (i in x.indices) { val v = s.y.getOrNull(i) ?: continue; if (!v.isNaN()) drawCircle(s.color, s.width.toPx() * 1.6f, Offset(px(x[i]), py(v))) }
            }
        }
        if (yLabel.isNotEmpty() || xLabel.isNotEmpty()) {
            Row(Modifier.fillMaxWidth().padding(top = 2.dp)) {
                Text(yLabel, style = MaterialTheme.typography.labelSmall, color = textColor, modifier = Modifier.weight(1f))
                Text(xLabel, style = MaterialTheme.typography.labelSmall, color = textColor)
            }
        }
        if (showLegend) {
            Row(Modifier.fillMaxWidth().padding(top = 6.dp), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                series.forEach { s ->
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Box(Modifier.size(10.dp).clip(CircleShape).background(s.color))
                        Spacer(Modifier.width(4.dp))
                        Text(s.name, style = MaterialTheme.typography.labelSmall, color = textColor)
                    }
                }
            }
        }
    }
}

/** Simple horizontal bar chart (label, value) — used for the verification ladder RMSE. */
@Composable
fun HBarChart(items: List<Triple<String, Float?, Color>>, modifier: Modifier = Modifier, unit: String = "") {
    val max = items.mapNotNull { it.second }.filter { !it.isNaN() }.maxOrNull() ?: 1f
    Column(modifier.fillMaxWidth().wrapContentHeight()) {
        items.forEach { (label, v, color) ->
            val frac = if (v == null || v.isNaN()) 0f else v / max
            BarRow(label, frac, if (v == null || v.isNaN()) "N/A" else "%.2f%s".format(Locale.US, v, unit), color)
        }
    }
}

private fun fmtTick(v: Float): String = when {
    kotlin.math.abs(v) >= 100 -> "%.0f".format(Locale.US, v)
    kotlin.math.abs(v) >= 10 -> "%.0f".format(Locale.US, v)
    kotlin.math.abs(v) >= 1 -> "%.1f".format(Locale.US, v)
    else -> "%.2f".format(Locale.US, v)
}

private fun niceCeil(v: Float): Float {
    if (v <= 0f) return 1f
    val exp = floor(log10(v.toDouble())).toInt()
    val base = 10.0.pow(exp)
    val m = v / base
    val nice = when { m <= 1 -> 1.0; m <= 2 -> 2.0; m <= 2.5 -> 2.5; m <= 5 -> 5.0; else -> 10.0 }
    return (nice * base).toFloat()
}

