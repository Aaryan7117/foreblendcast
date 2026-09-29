package com.foreblendcast.app.map

import com.foreblendcast.app.data.GeoCompact
import com.foreblendcast.app.data.GeoDistrict
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class GeoIndexTest {
    private val square = GeoDistrict("SQ", "Square", "S", "R", listOf(1.0, 1.0), listOf(listOf(0.0, 0.0, 2.0, 0.0, 2.0, 2.0, 0.0, 2.0, 0.0, 0.0)))
    private val small = GeoDistrict("SM", "Small", "S", "R", listOf(0.5, 0.5), listOf(listOf(0.0, 0.0, 1.0, 0.0, 1.0, 1.0, 0.0, 1.0, 0.0, 0.0)))
    private val tri = GeoDistrict("TR", "Tri", "S", "R", listOf(10.6, 10.3), listOf(listOf(10.0, 10.0, 12.0, 10.0, 10.0, 12.0, 10.0, 10.0)))
    private val index = GeoIndex.from(GeoCompact(listOf(0.0, 0.0, 12.0, 12.0), listOf(square, small, tri)))

    @Test fun point_in_ring() {
        val ring = floatArrayOf(0f, 0f, 2f, 0f, 2f, 2f, 0f, 2f, 0f, 0f)
        assertTrue(GeoShape.pointInRing(ring, 1f, 1f))
        assertFalse(GeoShape.pointInRing(ring, 3f, 1f))
    }

    @Test fun hit_test_prefers_smallest_overlapping_shape() {
        assertEquals("SM", index.hitTest(0.5, 0.5)?.id)   // inside both -> smaller bbox wins
        assertEquals("SQ", index.hitTest(1.5, 1.5)?.id)
        assertEquals("TR", index.hitTest(10.5, 10.5)?.id)
        assertNull(index.hitTest(11.9, 11.9))              // outside the triangle's hypotenuse
        assertNull(index.hitTest(50.0, 50.0))
    }

    @Test fun bounds_and_centroids() {
        assertEquals(0.0, index.west, 1e-9)
        assertEquals(12.0, index.north, 1e-9)
        assertEquals(1.0 to 1.0, index.centroids()["SQ"])
        assertEquals("Square", index["SQ"]?.name)
    }
}
