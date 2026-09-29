package com.foreblendcast.app.map

import com.foreblendcast.app.data.GeoCompact
import com.foreblendcast.app.data.GeoDistrict

/** One district's simplified outline: rings as flat [x0,y0,x1,y1,…] lon/lat arrays plus a bbox. */
class GeoShape(
    val id: String,
    val name: String,
    val state: String,
    val centroidLon: Double,
    val centroidLat: Double,
    val rings: List<FloatArray>,
    val minX: Float,
    val minY: Float,
    val maxX: Float,
    val maxY: Float,
) {
    fun contains(lon: Double, lat: Double): Boolean {
        if (lon < minX || lon > maxX || lat < minY || lat > maxY) return false
        for (ring in rings) if (pointInRing(ring, lon.toFloat(), lat.toFloat())) return true
        return false
    }

    companion object {
        /** Ray-casting point-in-polygon on a flat ring array. */
        fun pointInRing(ring: FloatArray, x: Float, y: Float): Boolean {
            val n = ring.size / 2
            if (n < 3) return false
            var inside = false
            var j = n - 1
            for (i in 0 until n) {
                val xi = ring[2 * i]; val yi = ring[2 * i + 1]
                val xj = ring[2 * j]; val yj = ring[2 * j + 1]
                val intersects = (yi > y) != (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi
                if (intersects) inside = !inside
                j = i
            }
            return inside
        }
    }
}

/** Spatial lookup over all district outlines (bbox pre-filter, then ray casting). */
class GeoIndex(val shapes: List<GeoShape>, val west: Double, val south: Double, val east: Double, val north: Double) {
    private val byId: Map<String, GeoShape> = shapes.associateBy { it.id }

    operator fun get(id: String): GeoShape? = byId[id]

    fun hitTest(lon: Double, lat: Double): GeoShape? {
        // Smallest bbox wins when outlines overlap slightly after simplification.
        var best: GeoShape? = null
        var bestArea = Float.MAX_VALUE
        for (s in shapes) {
            if (!s.contains(lon, lat)) continue
            val area = (s.maxX - s.minX) * (s.maxY - s.minY)
            if (area < bestArea) { bestArea = area; best = s }
        }
        return best
    }

    fun centroids(): Map<String, Pair<Double, Double>> = shapes.associate { it.id to (it.centroidLon to it.centroidLat) }

    companion object {
        fun from(geo: GeoCompact): GeoIndex {
            val shapes = geo.districts.map(::toShape)
            val b = geo.bounds
            val west = b.getOrNull(0) ?: shapes.minOf { it.minX }.toDouble()
            val south = b.getOrNull(1) ?: shapes.minOf { it.minY }.toDouble()
            val east = b.getOrNull(2) ?: shapes.maxOf { it.maxX }.toDouble()
            val north = b.getOrNull(3) ?: shapes.maxOf { it.maxY }.toDouble()
            return GeoIndex(shapes, west, south, east, north)
        }

        private fun toShape(d: GeoDistrict): GeoShape {
            var minX = Float.MAX_VALUE; var minY = Float.MAX_VALUE
            var maxX = -Float.MAX_VALUE; var maxY = -Float.MAX_VALUE
            val rings = d.rings.map { r ->
                val arr = FloatArray(r.size) { r[it].toFloat() }
                var i = 0
                while (i + 1 < arr.size) {
                    val x = arr[i]; val y = arr[i + 1]
                    if (x < minX) minX = x; if (x > maxX) maxX = x
                    if (y < minY) minY = y; if (y > maxY) maxY = y
                    i += 2
                }
                arr
            }
            val cx = d.c.getOrNull(0) ?: ((minX + maxX) / 2.0)
            val cy = d.c.getOrNull(1) ?: ((minY + maxY) / 2.0)
            return GeoShape(d.id, d.name, d.state, cx, cy, rings, minX, minY, maxX, maxY)
        }
    }
}
