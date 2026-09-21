package com.imanunator.wallpaparr

import android.content.Context
import com.imanunator.wallpaparr.core.PreparedWallpaper
import com.imanunator.wallpaparr.core.WallpaperDoubleBuffer
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicInteger

/**
 * Process-wide double-buffer so settings / refresh broadcasts can drop a
 * stale preload, and the bound service can keep the last frame.
 */
object WallpaperSession {
    val buffer = WallpaperDoubleBuffer<PreparedWallpaper>()
    val generation = AtomicInteger(0)
    @Volatile var preloadInFlight: Boolean = false

    @Volatile private var preloader: MediaPreloader? = null
    @Volatile private var executor: ExecutorService? = null

    fun preloader(context: Context): MediaPreloader {
        preloader?.let { return it }
        synchronized(this) {
            preloader?.let { return it }
            return MediaPreloader(context.applicationContext).also { preloader = it }
        }
    }

    fun executor(): ExecutorService {
        executor?.let { return it }
        synchronized(this) {
            executor?.let { return it }
            return Executors.newSingleThreadExecutor { runnable ->
                Thread(runnable, "wallpaparr-preload").apply { isDaemon = true }
            }.also { executor = it }
        }
    }

    fun invalidate() {
        generation.incrementAndGet()
        preloadInFlight = false
        buffer.invalidate()
    }
}
