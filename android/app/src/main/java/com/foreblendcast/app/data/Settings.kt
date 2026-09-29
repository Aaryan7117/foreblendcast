package com.foreblendcast.app.data

import android.content.Context
import android.content.SharedPreferences
import com.foreblendcast.app.BuildConfig
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow

/** Small persisted settings: API base URL, phone number and SMS language for the demo. */
class Settings(context: Context) {
    private val prefs: SharedPreferences = context.getSharedPreferences("foreblendcast", Context.MODE_PRIVATE)

    private val _baseUrl = MutableStateFlow(prefs.getString(KEY_BASE_URL, null) ?: BuildConfig.DEFAULT_API_BASE_URL)
    val baseUrl: StateFlow<String> = _baseUrl

    private val _phone = MutableStateFlow(prefs.getString(KEY_PHONE, "") ?: "")
    val phone: StateFlow<String> = _phone

    private val _language = MutableStateFlow(prefs.getString(KEY_LANGUAGE, "en") ?: "en")
    val language: StateFlow<String> = _language

    fun setBaseUrl(value: String) {
        val v = normalizeUrl(value)
        prefs.edit().putString(KEY_BASE_URL, v).apply()
        _baseUrl.value = v
    }

    fun setPhone(value: String) {
        prefs.edit().putString(KEY_PHONE, value.trim()).apply()
        _phone.value = value.trim()
    }

    fun setLanguage(value: String) {
        prefs.edit().putString(KEY_LANGUAGE, value).apply()
        _language.value = value
    }

    companion object {
        private const val KEY_BASE_URL = "base_url"
        private const val KEY_PHONE = "phone"
        private const val KEY_LANGUAGE = "language"

        val LANGUAGES = listOf("en" to "English", "hi" to "हिन्दी", "mr" to "मराठी", "ta" to "தமிழ்", "te" to "తెలుగు")

        fun normalizeUrl(raw: String): String {
            var v = raw.trim().trimEnd('/')
            if (v.isNotEmpty() && !v.startsWith("http://") && !v.startsWith("https://")) v = "http://$v"
            return v
        }
    }
}
