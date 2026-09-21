package com.imanunator.wallpaparr.core

import java.net.URI

object UrlSupport {
    fun normalizeServerUrl(raw: String): String {
        var url = raw.trim()
        if (url.isEmpty()) return url
        if (!url.startsWith("http://") && !url.startsWith("https://")) {
            url = "http://$url"
        }
        while (url.endsWith("/")) {
            url = url.dropLast(1)
        }
        return "$url/"
    }

    fun rewriteMediaUrl(mediaUrl: String?, serverUrl: String): String? {
        if (mediaUrl.isNullOrBlank()) return mediaUrl
        val base = serverUrl.trimEnd('/')
        return try {
            val media = URI(mediaUrl)
            val host = media.host?.lowercase().orEmpty()
            if (host in listOf("localhost", "127.0.0.1", "0.0.0.0", "::1") || host.isEmpty()) {
                val baseUri = URI(base)
                URI(
                    baseUri.scheme,
                    baseUri.userInfo,
                    baseUri.host,
                    baseUri.port,
                    media.path,
                    media.query,
                    media.fragment,
                ).toString()
            } else {
                mediaUrl
            }
        } catch (_: Exception) {
            mediaUrl
        }
    }

    fun parseYearRange(yearFilter: String): Pair<String?, String?> {
        val raw = yearFilter.trim()
        if (raw.isEmpty()) return null to null
        return if (raw.contains("-")) {
            val parts = raw.split("-", limit = 2)
            parts.getOrNull(0)?.trim() to parts.getOrNull(1)?.trim()
        } else {
            raw to raw
        }
    }

    fun excludeQuery(recentCsv: String, depth: Int): String? {
        val paths = recentCsv.split(",").map { it.trim() }.filter { it.isNotEmpty() }
        return paths.take(depth.coerceIn(1, 50)).joinToString(",").ifBlank { null }
    }

    fun rememberShownPath(recentCsv: String, path: String?, depth: Int): String {
        if (path.isNullOrBlank()) return recentCsv
        val list = recentCsv.split(",")
            .map { it.trim() }
            .filter { it.isNotEmpty() && it != path }
            .toMutableList()
        list.add(0, path)
        return list.take(depth.coerceIn(1, 50)).joinToString(",")
    }

    fun parseJellyfinItemId(actionUrl: String?): String? {
        if (actionUrl.isNullOrBlank()) return null
        if (!actionUrl.startsWith("jellyfin://items/")) return null
        val id = actionUrl.substringAfter("jellyfin://items/")
        return id.ifBlank { null }
    }

    /** Seerr / Jellyseerr web deep links look like …/movie/123 or …/tv/456. */
    fun isSeerrActionUrl(actionUrl: String?): Boolean {
        if (actionUrl.isNullOrBlank()) return false
        if (actionUrl.startsWith("jellyfin://")) return false
        return try {
            val path = URI(actionUrl).path?.lowercase().orEmpty()
            path.contains("/movie/") || path.contains("/tv/") ||
                path.matches(Regex(".*/(movie|tv)/\\d+/?$")) ||
                path.matches(Regex("^/(movie|tv)/\\d+/?$"))
        } catch (_: Exception) {
            false
        }
    }

    fun shouldUseVideo(preferMotion: Boolean, mediaType: String?, videoUrl: String?): Boolean {
        if (!preferMotion || videoUrl.isNullOrBlank()) return false
        return mediaType.equals("video", ignoreCase = true) ||
            videoUrl.contains(".mp4", ignoreCase = true)
    }
}
