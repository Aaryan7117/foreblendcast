package com.foreblendcast.app.map

import android.graphics.Bitmap
import android.graphics.Paint
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.gestures.detectTransformGestures
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.FilterQuality
import androidx.compose.ui.graphics.asComposePath
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.withTransform
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.IntSize
import com.foreblendcast.app.data.Bounds
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlin.math.cos

private const val BASE_W = 1400

/** Equirectangular projection into a fixed bitmap space shared by the base layer and overlays. */
class MapProjection(val west: Double, val south: Double, val east: Double, val north: Double, val width: Int) {
    private val midLat = Math.toRadians((north + south) / 2)
    val height: Int = (width * (north - south) / ((east - west) * cos(midLat))).toInt().coerceAtLeast(1)

    fun x(lon: Double): Float = ((lon - west) / (east - west) * width).toFloat()
    fun y(lat: Double): Float = ((north - lat) / (north - south) * height).toFloat()
    fun lon(px: Float): Double = west + px / width * (east - west)
    fun lat(py: Float): Double = north - py / height * (north - south)
}

private class BaseLayer(val bitmap: Bitmap, val projection: MapProjection)

private fun buildPath(shape: GeoShape, p: MapProjection): android.graphics.Path {
    val path = android.graphics.Path()
    for (ring in shape.rings) {
        var i = 0
        var first = true
        while (i + 1 < ring.size) {
            val x = p.x(ring[i].toDouble()); val y = p.y(ring[i + 1].toDouble())
            if (first) { path.moveTo(x, y); first = false } else path.lineTo(x, y)
            i += 2
        }
        path.close()
    }
    return path
}

private fun renderBase(geo: GeoIndex, fills: Map<String, Color>, neutral: Color, border: Color, cachedPaths: Map<String, android.graphics.Path>, p: MapProjection): Bitmap {
    val bmp = Bitmap.createBitmap(p.width, p.height, Bitmap.Config.ARGB_8888)
    val canvas = android.graphics.Canvas(bmp)
    val fill = Paint(Paint.ANTI_ALIAS_FLAG).apply { style = Paint.Style.FILL }
    val stroke = Paint(Paint.ANTI_ALIAS_FLAG).apply { style = Paint.Style.STROKE; strokeWidth = 1.2f; color = border.toArgbInt() }
    for (s in geo.shapes) {
        val path = cachedPaths[s.id] ?: continue
        fill.color = (fills[s.id] ?: neutral).toArgbInt()
        canvas.drawPath(path, fill)
        canvas.drawPath(path, stroke)
    }
    return bmp
}

private fun Color.toArgbInt(): Int = android.graphics.Color.argb((alpha * 255).toInt(), (red * 255).toInt(), (green * 255).toInt(), (blue * 255).toInt())

/**
 * Pan/zoom choropleth of India's 735 districts drawn from the bundled outlines, with an optional
 * georeferenced raster overlay (pre-rendered PNG or the live blend bitmap). Tap selects a district.
 */
@Composable
fun IndiaMap(
    geo: GeoIndex?,
    fills: Map<String, Color>,
    fillsKey: Any,
    modifier: Modifier = Modifier,
    overlay: Bitmap? = null,
    overlayBounds: Bounds? = null,
    overlayAlpha: Float = 0.78f,
    selectedId: String? = null,
    neutralFill: Color = Color(0xFFE8ECE9),
    onTap: (GeoShape?) -> Unit = {},
) {
    val borderColor = MaterialTheme.colorScheme.outline.copy(alpha = 0.9f)
    val bg = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)
    val projection = remember(geo) { geo?.let { MapProjection(it.west, it.south, it.east, it.north, BASE_W) } }
    val paths = remember(geo) { if (geo != null && projection != null) geo.shapes.associate { it.id to buildPath(it, projection) } else emptyMap() }

    val base by produceState<BaseLayer?>(initialValue = null, geo, fillsKey, neutralFill) {
        val g = geo; val p = projection
        if (g == null || p == null) { value = null; return@produceState }
        value = withContext(Dispatchers.Default) { BaseLayer(renderBase(g, fills, neutralFill, borderColor, paths, p), p) }
    }

    var scale by remember { mutableFloatStateOf(1f) }
    var offset by remember { mutableStateOf(Offset.Zero) }
    var canvasSize by remember { mutableStateOf(IntSize.Zero) }

    // Fit-to-view transform for the base bitmap
    fun fitScale(): Float {
        val p = projection ?: return 1f
        if (canvasSize.width == 0) return 1f
        return minOf(canvasSize.width / p.width.toFloat(), canvasSize.height / p.height.toFloat())
    }
    fun fitOffset(): Offset {
        val p = projection ?: return Offset.Zero
        val s = fitScale()
        return Offset((canvasSize.width - p.width * s) / 2f, (canvasSize.height - p.height * s) / 2f)
    }
    fun total(): Float = fitScale() * scale
    fun totalOffset(): Offset = fitOffset() * 1f + offset

    Box(modifier.background(bg)) {
        Canvas(
            Modifier
                .fillMaxSize()
                .pointerInput(geo) {
                    detectTransformGestures { centroid, pan, zoom, _ ->
                        val newScale = (scale * zoom).coerceIn(1f, 10f)
                        val factor = newScale / scale
                        // keep the point under the fingers fixed while zooming
                        val fo = fitOffset()
                        val pivot = centroid - fo
                        offset = (offset - pivot) * factor + pivot + pan
                        scale = newScale
                        if (scale == 1f) offset = Offset.Zero
                    }
                }
                .pointerInput(geo, base) {
                    detectTapGestures(
                        onDoubleTap = { scale = 1f; offset = Offset.Zero },
                        onTap = { pos ->
                            val g = geo; val p = projection
                            if (g == null || p == null) return@detectTapGestures
                            val t = total(); val o = totalOffset()
                            val bx = (pos.x - o.x) / t; val by = (pos.y - o.y) / t
                            onTap(g.hitTest(p.lon(bx), p.lat(by)))
                        },
                    )
                },
        ) {
            canvasSize = IntSize(size.width.toInt(), size.height.toInt())
            val layer = base ?: return@Canvas
            val t = total(); val o = totalOffset()
            withTransform({ translate(o.x, o.y); scale(t, t, pivot = Offset.Zero) }) {
                drawImage(layer.bitmap.asImageBitmap(), dstSize = IntSize(layer.projection.width, layer.projection.height), filterQuality = FilterQuality.Medium)

                if (overlay != null && overlayBounds != null) {
                    val p = layer.projection
                    val left = p.x(overlayBounds.west); val top = p.y(overlayBounds.north)
                    val right = p.x(overlayBounds.east); val bottom = p.y(overlayBounds.south)
                    drawImage(
                        overlay.asImageBitmap(),
                        dstOffset = IntOffset(left.toInt(), top.toInt()),
                        dstSize = IntSize((right - left).toInt(), (bottom - top).toInt()),
                        alpha = overlayAlpha,
                        filterQuality = FilterQuality.None,
                    )
                }

                if (selectedId != null) {
                    val ap = paths[selectedId]
                    if (ap != null) {
                        val cp = ap.asComposePath()
                        drawPath(cp, Color.White, style = Stroke(width = 5f / t))
                        drawPath(cp, Color(0xFF0E3825), style = Stroke(width = 2.5f / t))
                    }
                }
            }
        }
    }
}
