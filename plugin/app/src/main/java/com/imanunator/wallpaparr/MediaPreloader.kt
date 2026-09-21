package com.imanunator.wallpaparr

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.util.Log
import androidx.core.content.FileProvider
import com.imanunator.wallpaparr.core.MediaCacheNames
import com.imanunator.wallpaparr.core.WallpaperTransition
import java.io.File
import java.io.FileOutputStream
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.TimeUnit

/**
 * Downloads the next IMAGE/VIDEO onto disk so Projectivy can start from a
 * local content:// URI instead of stalling on HTTP. The AIDL contract has no
 * preload or crossfade field — this is the plugin-side double-buffer.
 */
class MediaPreloader(private val context: Context) {
    private val dir: File = File(context.cacheDir, CACHE_DIR).apply { mkdirs() }

    fun cachedPlaybackUri(remoteUrl: String?): String? {
        if (remoteUrl.isNullOrBlank()) return null
        val file = File(dir, MediaCacheNames.fileNameFor(remoteUrl))
        if (!file.exists() || file.length() <= MIN_BYTES) return null
        return uriFor(file)?.toString()
    }

    fun playbackUri(remoteUrl: String): String {
        return WallpaperTransition.preferCachedUri(remoteUrl, cachedPlaybackUri(remoteUrl))
    }

    /**
     * Download [remoteUrl] if missing. Returns a content:// URI when the file
     * is on disk, otherwise the original HTTP URL.
     */
    fun ensureCached(remoteUrl: String, timeoutMs: Long): String {
        val existing = cachedPlaybackUri(remoteUrl)
        if (existing != null) return existing
        val file = download(remoteUrl, timeoutMs) ?: return remoteUrl
        return uriFor(file)?.toString() ?: remoteUrl
    }

    fun prefetch(remoteUrl: String?) {
        if (remoteUrl.isNullOrBlank()) return
        if (cachedPlaybackUri(remoteUrl) != null) return
        download(remoteUrl, PREFETCH_TIMEOUT_MS)
    }

    private fun download(remoteUrl: String, timeoutMs: Long): File? {
        val name = MediaCacheNames.fileNameFor(remoteUrl)
        val dest = File(dir, name)
        if (dest.exists() && dest.length() > MIN_BYTES) return dest
        val tmp = File(dir, "$name.part")
        var connection: HttpURLConnection? = null
        return try {
            connection = (URL(remoteUrl).openConnection() as HttpURLConnection).apply {
                instanceFollowRedirects = true
                connectTimeout = CONNECT_TIMEOUT_MS
                readTimeout = timeoutMs.toInt().coerceAtLeast(CONNECT_TIMEOUT_MS)
                setRequestProperty("Accept", "*/*")
            }
            val code = connection.responseCode
            if (code !in 200..299) {
                Log.w(TAG, "preload HTTP $code for $remoteUrl")
                return null
            }
            connection.inputStream.use { input ->
                FileOutputStream(tmp).use { output ->
                    val buf = ByteArray(32 * 1024)
                    var total = 0L
                    val deadline = System.nanoTime() + TimeUnit.MILLISECONDS.toNanos(timeoutMs)
                    while (true) {
                        if (System.nanoTime() > deadline) {
                            Log.w(TAG, "preload timed out for $remoteUrl")
                            tmp.delete()
                            return null
                        }
                        val read = input.read(buf)
                        if (read < 0) break
                        output.write(buf, 0, read)
                        total += read
                        if (total > MAX_BYTES) {
                            Log.w(TAG, "preload too large ($total) for $remoteUrl")
                            tmp.delete()
                            return null
                        }
                    }
                    output.flush()
                }
            }
            if (tmp.length() <= MIN_BYTES) {
                tmp.delete()
                return null
            }
            if (dest.exists()) dest.delete()
            if (!tmp.renameTo(dest)) {
                tmp.copyTo(dest, overwrite = true)
                tmp.delete()
            }
            evictOld()
            dest
        } catch (e: Exception) {
            Log.w(TAG, "preload failed for $remoteUrl", e)
            tmp.delete()
            null
        } finally {
            connection?.disconnect()
        }
    }

    private fun uriFor(file: File): Uri? {
        return try {
            val uri = FileProvider.getUriForFile(context, AUTHORITY, file)
            context.grantUriPermission(
                SettingsActivity.PROJECTIVY,
                uri,
                Intent.FLAG_GRANT_READ_URI_PERMISSION,
            )
            uri
        } catch (e: Exception) {
            Log.w(TAG, "FileProvider failed for ${file.name}", e)
            null
        }
    }

    private fun evictOld() {
        val files = dir.listFiles { f -> f.isFile && !f.name.endsWith(".part") } ?: return
        if (files.size <= MAX_FILES) return
        files.sortedBy { it.lastModified() }
            .take(files.size - MAX_FILES)
            .forEach { it.delete() }
    }

    companion object {
        private const val TAG = "Wallpaparr"
        const val AUTHORITY = "com.imanunator.wallpaparr.media"
        private const val CACHE_DIR = "wallpaparr-preload"
        private const val MIN_BYTES = 64L
        private const val MAX_BYTES = 40L * 1024L * 1024L
        private const val MAX_FILES = 4
        private const val CONNECT_TIMEOUT_MS = 5_000
        const val DISPLAY_TIMEOUT_MS = 6_000L
        const val PREFETCH_TIMEOUT_MS = 25_000L
    }
}
