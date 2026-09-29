package com.foreblendcast.app.data

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.KSerializer
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.IOException
import java.util.concurrent.TimeUnit

/** Thrown for any non-2xx response so callers can show the server's `detail`. */
class ApiException(val code: Int, message: String) : IOException("HTTP $code: $message")

/**
 * Thin OkHttp + kotlinx.serialization client for the ForeBlendCast API.
 * The base URL is read on every call so a change in Settings applies immediately.
 */
class ApiClient(private val baseUrlProvider: () -> String) {

    val json: Json = Json {
        ignoreUnknownKeys = true
        coerceInputValues = true
        explicitNulls = false
        isLenient = true
        allowSpecialFloatingPointValues = true // ladder.json carries NaN / Infinity on disk
    }

    private val http = OkHttpClient.Builder()
        .connectTimeout(8, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .callTimeout(45, TimeUnit.SECONDS)
        .retryOnConnectionFailure(true)
        .build()

    fun baseUrl(): String = baseUrlProvider().trim().trimEnd('/')

    fun url(path: String): String = baseUrl() + (if (path.startsWith("/")) path else "/$path")

    suspend fun <T> get(path: String, serializer: KSerializer<T>): T = withContext(Dispatchers.IO) {
        val req = Request.Builder().url(url(path)).header("Accept", "application/json").build()
        http.newCall(req).execute().use { resp ->
            val body = resp.body.string()
            if (!resp.isSuccessful) throw ApiException(resp.code, extractDetail(body))
            json.decodeFromString(serializer, body)
        }
    }

    suspend fun getText(path: String): String = withContext(Dispatchers.IO) {
        val req = Request.Builder().url(url(path)).build()
        http.newCall(req).execute().use { resp ->
            val body = resp.body.string()
            if (!resp.isSuccessful) throw ApiException(resp.code, extractDetail(body))
            body
        }
    }

    suspend fun getBytes(path: String): ByteArray = withContext(Dispatchers.IO) {
        val req = Request.Builder().url(url(path)).build()
        http.newCall(req).execute().use { resp ->
            if (!resp.isSuccessful) throw ApiException(resp.code, "binary fetch failed")
            resp.body.bytes()
        }
    }

    suspend fun <B, T> post(path: String, body: B, bodySerializer: KSerializer<B>, serializer: KSerializer<T>): T =
        withContext(Dispatchers.IO) {
            val payload = json.encodeToString(bodySerializer, body).toRequestBody(JSON_MEDIA)
            val req = Request.Builder().url(url(path)).post(payload).header("Accept", "application/json").build()
            http.newCall(req).execute().use { resp ->
                val text = resp.body.string()
                if (!resp.isSuccessful) throw ApiException(resp.code, extractDetail(text))
                json.decodeFromString(serializer, text)
            }
        }

    suspend fun delete(path: String): String = withContext(Dispatchers.IO) {
        val req = Request.Builder().url(url(path)).delete().build()
        http.newCall(req).execute().use { resp ->
            val text = resp.body.string()
            if (!resp.isSuccessful) throw ApiException(resp.code, extractDetail(text))
            text
        }
    }

    private fun extractDetail(body: String): String = try {
        val el = json.parseToJsonElement(body)
        val obj = el as? kotlinx.serialization.json.JsonObject
        val detail = obj?.get("detail")
        when (detail) {
            is kotlinx.serialization.json.JsonPrimitive -> detail.content
            null -> body.take(200)
            else -> detail.toString().take(200)
        }
    } catch (_: Exception) {
        body.take(200).ifBlank { "request failed" }
    }

    companion object {
        private val JSON_MEDIA = "application/json; charset=utf-8".toMediaType()
    }
}
