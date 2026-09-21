package com.imanunator.wallpaparr

import android.content.Context
import android.content.SharedPreferences
import androidx.preference.PreferenceManager
import com.imanunator.wallpaparr.core.UrlSupport
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.boolean
import kotlinx.serialization.json.booleanOrNull
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.float
import kotlinx.serialization.json.floatOrNull
import kotlinx.serialization.json.int
import kotlinx.serialization.json.intOrNull
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.long
import kotlinx.serialization.json.longOrNull

object PreferencesManager {
    lateinit var preferences: SharedPreferences

    fun init(context: Context) {
        if (!::preferences.isInitialized) {
            preferences = PreferenceManager.getDefaultSharedPreferences(context)
        }
    }

    private fun SharedPreferences.put(key: String, value: Any?) {
        edit().apply {
            when (value) {
                is String? -> putString(key, value)
                is Int -> putInt(key, value)
                is Boolean -> putBoolean(key, value)
                is Float -> putFloat(key, value)
                is Long -> putLong(key, value)
            }
            apply()
        }
    }

    var serverUrl: String
        get() = preferences.getString("server_url_key", "http://192.168.1.100:8787") ?: ""
        set(value) = preferences.put("server_url_key", UrlSupport.normalizeServerUrl(value))

    var selectedLayout: String
        get() = preferences.getString("selected_layout_key", "") ?: ""
        set(value) = preferences.put("selected_layout_key", value)

    var secondaryLayout: String
        get() = preferences.getString("secondary_layout_key", "") ?: ""
        set(value) = preferences.put("secondary_layout_key", value)

    var thirdLayout: String
        get() = preferences.getString("third_layout_key", "") ?: ""
        set(value) = preferences.put("third_layout_key", value)

    var genreFilter: String
        get() = preferences.getString("genre_filter_key", "") ?: ""
        set(value) = preferences.put("genre_filter_key", value)

    var ageFilter: String
        get() = preferences.getString("age_filter_key", "") ?: ""
        set(value) = preferences.put("age_filter_key", value)

    var yearFilter: String
        get() = preferences.getString("year_filter_key", "") ?: ""
        set(value) = preferences.put("year_filter_key", value)

    var minRating: Float
        get() = preferences.getFloat("pref_min_rating", 0f)
        set(value) = preferences.put("pref_min_rating", value)

    var maxRating: Float
        get() = preferences.getFloat("pref_max_rating", 10f)
        set(value) = preferences.put("pref_max_rating", value)

    var refreshOnIdleExit: Boolean
        get() = preferences.getBoolean("pref_refresh_on_idle_exit", true)
        set(value) = preferences.put("pref_refresh_on_idle_exit", value)

    var preferMotion: Boolean
        get() = preferences.getBoolean("pref_prefer_motion", true)
        set(value) = preferences.put("pref_prefer_motion", value)

    var fallbackStill: Boolean
        get() = preferences.getBoolean("pref_fallback_still", true)
        set(value) = preferences.put("pref_fallback_still", value)

    var wallpaperPickMode: String
        get() = preferences.getString("wallpaper_pick_mode", "tonight") ?: "tonight"
        set(value) = preferences.put("wallpaper_pick_mode", value)

    var mixRatio: Int
        get() = preferences.getInt("wallpaper_mix_ratio", 30)
        set(value) = preferences.put("wallpaper_mix_ratio", value)

    var recentYears: Int
        get() = preferences.getInt("wallpaper_recent_years", 3)
        set(value) = preferences.put("wallpaper_recent_years", value)

    var excludeDepth: Int
        get() = preferences.getInt("wallpaper_exclude_depth", 5)
        set(value) = preferences.put("wallpaper_exclude_depth", value)

    var wallpaperRotateCounter: Int
        get() = preferences.getInt("wallpaper_rotate_counter", 0)
        set(value) = preferences.put("wallpaper_rotate_counter", value)

    var recentWallpaperPaths: String
        get() = preferences.getString("wallpaper_recent_paths", "") ?: ""
        set(value) = preferences.put("wallpaper_recent_paths", value)

    var lastWallpaperUri: String
        get() = preferences.getString("last_wallpaper_uri", "") ?: ""
        set(value) = preferences.put("last_wallpaper_uri", value)

    var lastWallpaperRemoteUri: String
        get() = preferences.getString("last_wallpaper_remote_uri", "") ?: ""
        set(value) = preferences.put("last_wallpaper_remote_uri", value)

    var lastWallpaperAuthor: String
        get() = preferences.getString("last_wallpaper_author", "") ?: ""
        set(value) = preferences.put("last_wallpaper_author", value)

    var lastWallpaperTitle: String
        get() = preferences.getString("last_wallpaper_title", "") ?: ""
        set(value) = preferences.put("last_wallpaper_title", value)

    var lastWallpaperAction: String
        get() = preferences.getString("last_wallpaper_action", "") ?: ""
        set(value) = preferences.put("last_wallpaper_action", value)

    var lastWallpaperPath: String
        get() = preferences.getString("last_wallpaper_path", "") ?: ""
        set(value) = preferences.put("last_wallpaper_path", value)

    var lastWallpaperIsVideo: Boolean
        get() = preferences.getBoolean("last_wallpaper_is_video", false)
        set(value) = preferences.put("last_wallpaper_is_video", value)

    var preferredClient: String
        get() = preferences.getString("preferred_client_key", "org.jellyfin.androidtv") ?: ""
        set(value) = preferences.put("preferred_client_key", value)

    var seerrOpensInBrowser: Boolean
        get() = preferences.getBoolean("pref_seerr_opens_in_browser", false)
        set(value) = preferences.put("pref_seerr_opens_in_browser", value)

    fun rememberShownPath(path: String?) {
        recentWallpaperPaths = UrlSupport.rememberShownPath(recentWallpaperPaths, path, excludeDepth)
    }

    fun excludeQueryValue(): String? = UrlSupport.excludeQuery(recentWallpaperPaths, excludeDepth)

    fun export(): String {
        val obj = buildJsonObject {
            preferences.all.forEach { (key, value) ->
                when (value) {
                    is Int -> put(key, JsonPrimitive(value))
                    is Long -> put(key, JsonPrimitive(value))
                    is Float -> put(key, JsonPrimitive(value))
                    is Boolean -> put(key, JsonPrimitive(value))
                    is String -> put(key, JsonPrimitive(value))
                }
            }
        }
        return obj.toString()
    }

    fun import(params: String): Boolean {
        return try {
            val element = Json.parseToJsonElement(params)
            if (element is JsonObject) {
                val editor = preferences.edit()
                element.forEach { (key, value) ->
                    if (value is JsonPrimitive) {
                        when {
                            value.isString -> editor.putString(key, value.content)
                            value.booleanOrNull != null -> editor.putBoolean(key, value.boolean)
                            value.intOrNull != null -> editor.putInt(key, value.int)
                            value.floatOrNull != null -> editor.putFloat(key, value.float)
                            value.longOrNull != null -> editor.putLong(key, value.long)
                        }
                    } else if (value is JsonArray) {
                        editor.putStringSet(key, value.mapTo(mutableSetOf()) { it.jsonPrimitive.content })
                    }
                }
                editor.apply()
            }
            true
        } catch (_: Exception) {
            false
        }
    }
}
