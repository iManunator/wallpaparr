package com.imanunator.wallpaparr.core

import java.security.MessageDigest

/**
 * One wallpaper we are prepared to hand to Projectivy.
 * [remoteUri] is the HTTP URL from the status API; [playbackUri] may be a
 * local content:// after preload. AIDL Wallpaper has a single uri + type —
 * there is no poster / crossfade field.
 */
data class PreparedWallpaper(
    val remoteUri: String,
    val playbackUri: String,
    val isVideo: Boolean,
    val title: String? = null,
    val author: String? = null,
    val actionUri: String? = null,
    val path: String? = null,
    val stillRemoteUri: String? = null,
)

/**
 * Plugin-side double-buffer. Projectivy caches the *list* returned by
 * getWallpapers() and then picks **at random** from that list, so we always
 * return **at most one** item. Returning [next, previous] would skip rotates.
 *
 * Hold-frame: if the incoming pick is missing, keep [showing] so we never
 * hand back an empty list (empty → Projectivy often flashes black).
 * Idle-mode transitions must also hold the current frame for the same reason.
 */
class WallpaperDoubleBuffer<T> {
    private val lock = Any()
    private var showing: T? = null
    private var preloaded: T? = null

    fun snapshotShowing(): T? = synchronized(lock) { showing }

    fun snapshotPreloaded(): T? = synchronized(lock) { preloaded }

    fun hasPreload(): Boolean = synchronized(lock) { preloaded != null }

    /**
     * @param allowBlocking when false and a frame is already showing, skip
     *   [loadIfEmpty] and hold (caller should be preloading in the background).
     */
    fun takeForDisplay(allowBlocking: Boolean, loadIfEmpty: () -> T?): T? {
        synchronized(lock) {
            val ready = preloaded
            if (ready != null) {
                preloaded = null
                showing = ready
                return ready
            }
            if (showing != null && !allowBlocking) {
                return showing
            }
        }
        val loaded = loadIfEmpty()
        synchronized(lock) {
            if (loaded != null) showing = loaded
            return showing
        }
    }

    fun offerPreload(value: T?) {
        if (value == null) return
        synchronized(lock) { preloaded = value }
    }

    fun seedShowing(value: T?) {
        if (value == null) return
        synchronized(lock) {
            if (showing == null) showing = value
        }
    }

    fun invalidate() {
        synchronized(lock) {
            showing = null
            preloaded = null
        }
    }
}

object WallpaperTransition {
    /**
     * What to return from getWallpapers(). Always 0 or 1 items so Projectivy
     * cannot randomly resurrect the previous URI and skip a pick-mode tick.
     */
    fun <T> displayList(incoming: T?, previous: T?): List<T> {
        val shown = incoming ?: previous
        return if (shown == null) emptyList() else listOf(shown)
    }

    fun preferCachedUri(remoteUri: String, cachedPlaybackUri: String?): String {
        val cached = cachedPlaybackUri?.trim().orEmpty()
        return cached.ifBlank { remoteUri }
    }

    fun isLocalPlayback(uri: String): Boolean {
        val value = uri.lowercase()
        return value.startsWith("content://") || value.startsWith("file:")
    }

    /**
     * Background preload should fetch the *next* pick-mode counter, not the
     * one we just displayed.
     */
    fun nextCounter(displayedCounter: Int): Int = displayedCounter + 1
}

object MediaCacheNames {
    fun fileNameFor(remoteUrl: String): String {
        val ext = extensionFor(remoteUrl)
        val digest = MessageDigest.getInstance("SHA-256")
            .digest(remoteUrl.toByteArray(Charsets.UTF_8))
        val hash = digest.joinToString("") { byte -> "%02x".format(byte) }.take(24)
        return "$hash.$ext"
    }

    fun extensionFor(remoteUrl: String): String {
        val path = remoteUrl.substringBefore('?').lowercase()
        return when {
            path.endsWith(".mp4") || path.endsWith(".m4v") -> "mp4"
            path.endsWith(".jpg") || path.endsWith(".jpeg") -> "jpg"
            path.endsWith(".png") -> "png"
            path.endsWith(".webp") -> "webp"
            else -> "bin"
        }
    }
}
