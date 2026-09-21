package com.imanunator.wallpaparr

import android.app.Service
import android.content.Intent
import android.os.IBinder
import android.util.Log
import com.imanunator.wallpaparr.core.ClientIntents
import com.imanunator.wallpaparr.core.MediaChoice
import com.imanunator.wallpaparr.core.PreparedWallpaper
import com.imanunator.wallpaparr.core.UrlSupport
import com.imanunator.wallpaparr.core.WallpaperPickModes
import com.imanunator.wallpaparr.core.WallpaperTransition
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import tv.projectivy.plugin.wallpaperprovider.api.Event
import tv.projectivy.plugin.wallpaperprovider.api.IWallpaperProviderService
import tv.projectivy.plugin.wallpaperprovider.api.Wallpaper
import tv.projectivy.plugin.wallpaperprovider.api.WallpaperDisplayMode
import tv.projectivy.plugin.wallpaperprovider.api.WallpaperType
import java.util.Calendar

class WallpaperProviderService : Service() {

    override fun onCreate() {
        super.onCreate()
        PreferencesManager.init(this)
        WallpaperSession.buffer.seedShowing(lastPreparedFromPrefs())
    }

    override fun onBind(intent: Intent): IBinder = binder

    private fun createApi(serverUrl: String): ApiService {
        val base = UrlSupport.normalizeServerUrl(serverUrl)
        return Retrofit.Builder()
            .baseUrl(base)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(ApiService::class.java)
    }

    private fun fetchStatus(
        api: ApiService,
        layout: String,
        genre: String?,
        age: String?,
        minYear: String?,
        maxYear: String?,
        minRating: Float?,
        maxRating: Float?,
        sort: String?,
        pool: String?,
        exclude: String?,
    ): WallpaperStatus? {
        val response = api.getWallpaperStatus(
            layout, genre, age, minYear, maxYear, minRating, maxRating, sort, pool, exclude,
        ).execute()
        if (!response.isSuccessful) return null
        val body = response.body() ?: return null
        return body.copy(imageUrl = UrlSupport.rewriteMediaUrl(body.imageUrl, PreferencesManager.serverUrl))
    }

    private fun lastPreparedFromPrefs(): PreparedWallpaper? {
        val uri = PreferencesManager.lastWallpaperUri
        if (uri.isBlank()) return null
        val remote = PreferencesManager.lastWallpaperRemoteUri.ifBlank { uri }
        return PreparedWallpaper(
            remoteUri = remote,
            playbackUri = uri,
            isVideo = PreferencesManager.lastWallpaperIsVideo || uri.contains(".mp4", ignoreCase = true),
            title = PreferencesManager.lastWallpaperTitle.ifBlank { null },
            author = PreferencesManager.lastWallpaperAuthor.ifBlank { null },
            actionUri = PreferencesManager.lastWallpaperAction.ifBlank { null },
            path = PreferencesManager.lastWallpaperPath.ifBlank { null },
        )
    }

    private fun persistShown(prepared: PreparedWallpaper) {
        PreferencesManager.lastWallpaperUri = prepared.playbackUri
        PreferencesManager.lastWallpaperRemoteUri = prepared.remoteUri
        PreferencesManager.lastWallpaperAuthor = prepared.author.orEmpty()
        PreferencesManager.lastWallpaperTitle = prepared.title.orEmpty()
        PreferencesManager.lastWallpaperAction = prepared.actionUri.orEmpty()
        PreferencesManager.lastWallpaperPath = prepared.path.orEmpty()
        PreferencesManager.lastWallpaperIsVideo = prepared.isVideo
        PreferencesManager.rememberShownPath(prepared.path ?: prepared.remoteUri)
    }

    private fun toWallpaper(prepared: PreparedWallpaper): Wallpaper {
        return Wallpaper(
            uri = prepared.playbackUri,
            type = if (prepared.isVideo) WallpaperType.VIDEO else WallpaperType.IMAGE,
            displayMode = WallpaperDisplayMode.CROP,
            title = prepared.title,
            author = prepared.author,
            actionUri = prepared.actionUri,
        )
    }

    private fun buildPrepared(status: WallpaperStatus, author: String, cacheTimeoutMs: Long): PreparedWallpaper? {
        val videoUrl = UrlSupport.rewriteMediaUrl(status.videoUrl, PreferencesManager.serverUrl)
        val imageUrl = UrlSupport.rewriteMediaUrl(status.imageUrl, PreferencesManager.serverUrl)
        val chosen = MediaChoice.choose(
            imageUrl = imageUrl,
            videoUrl = videoUrl,
            mediaType = status.mediaType,
            preferMotion = PreferencesManager.preferMotion,
            fallbackStill = PreferencesManager.fallbackStill,
        ) ?: return null
        val action = ClientIntents.resolveActionUri(
            PreferencesManager.preferredClient,
            status.actionUrl,
            PreferencesManager.seerrOpensInBrowser,
        )
        val preloader = WallpaperSession.preloader(this)
        val playback = if (cacheTimeoutMs > 0) {
            preloader.ensureCached(chosen.uri, cacheTimeoutMs)
        } else {
            preloader.playbackUri(chosen.uri)
        }
        return PreparedWallpaper(
            remoteUri = chosen.uri,
            playbackUri = playback,
            isVideo = chosen.isVideo,
            title = status.title,
            author = author,
            actionUri = action,
            path = status.path,
            stillRemoteUri = imageUrl,
        )
    }

    private fun pickPrepared(cacheTimeoutMs: Long = MediaPreloader.DISPLAY_TIMEOUT_MS): PreparedWallpaper? {
        val serverUrl = PreferencesManager.serverUrl
        if (serverUrl.isBlank()) return null
        val counter = PreferencesManager.wallpaperRotateCounter
        val pickMode = PreferencesManager.wallpaperPickMode
        val resolved = WallpaperPickModes.resolve(
            modeId = pickMode,
            primaryLayout = PreferencesManager.selectedLayout,
            secondaryLayout = PreferencesManager.secondaryLayout,
            thirdLayout = PreferencesManager.thirdLayout,
            mixRatio = PreferencesManager.mixRatio,
            recentYears = PreferencesManager.recentYears,
            counter = counter,
            currentYear = Calendar.getInstance().get(Calendar.YEAR),
            minRating = PreferencesManager.minRating,
        )
        var genreFilter = PreferencesManager.genreFilter.ifEmpty { null }
        if (pickMode == "genre_round_robin") {
            genreFilter = WallpaperPickModes.nextGenreForRoundRobin(
                PreferencesManager.genreFilter, counter,
            ) ?: genreFilter
        }
        val (parsedMin, parsedMax) = UrlSupport.parseYearRange(PreferencesManager.yearFilter)
        val minYear = resolved.minYear ?: parsedMin
        val maxYear = if (resolved.minYear != null) null else parsedMax
        val api = createApi(serverUrl)
        val imageLayouts = runCatching { api.getLayoutsWithImages().execute().body().orEmpty() }
            .getOrDefault(emptyList())
        val allLayouts = runCatching { api.getLayouts().execute().body().orEmpty() }
            .getOrDefault(emptyList())
        val layoutPool = imageLayouts.ifEmpty { allLayouts }
        fun match(wanted: String) = layoutPool.firstOrNull { it.equals(wanted, true) }
            ?: allLayouts.firstOrNull { it.equals(wanted, true) }
        val preferred = match(PreferencesManager.selectedLayout)
        val layoutToUse = when (pickMode) {
            "layout_round_robin" -> {
                val pool = listOfNotNull(
                    preferred,
                    match(PreferencesManager.secondaryLayout),
                    match(PreferencesManager.thirdLayout),
                ).ifEmpty { layoutPool }
                pool[counter % pool.size.coerceAtLeast(1)]
            }
            "alt_two_layouts" -> {
                val a = preferred ?: layoutPool.firstOrNull().orEmpty()
                val b = match(PreferencesManager.secondaryLayout) ?: layoutPool.getOrNull(1) ?: a
                if (counter % 2 == 0) a else b
            }
            else -> match(resolved.layout) ?: preferred ?: layoutPool.firstOrNull().orEmpty()
        }
        if (layoutToUse.isBlank()) return null
        var status = fetchStatus(
            api, layoutToUse, genreFilter,
            PreferencesManager.ageFilter.ifEmpty { null },
            minYear, maxYear,
            PreferencesManager.minRating.takeIf { it > 0f } ?: resolved.minRating,
            PreferencesManager.maxRating.takeIf { it < 10f },
            resolved.sort, resolved.pool, PreferencesManager.excludeQueryValue(),
        )
        if (status?.imageUrl.isNullOrBlank()) {
            // Relax filters but keep excluding the just-shown wallpaper(s) —
            // dropping exclude here would defeat no-repeat for any reason
            // other than the layout genuinely having nothing else to show.
            status = fetchStatus(
                api, layoutToUse, null, null, null, null, null, null,
                "random", null, PreferencesManager.excludeQueryValue(),
            )
        }
        if (status?.imageUrl.isNullOrBlank()) {
            for (alt in layoutPool) {
                if (alt.equals(layoutToUse, true)) continue
                status = fetchStatus(
                    api, alt, null, null, null, null, null, null,
                    "random", null, PreferencesManager.excludeQueryValue(),
                )
                if (!status?.imageUrl.isNullOrBlank()) break
            }
        }
        PreferencesManager.wallpaperRotateCounter = WallpaperTransition.nextCounter(counter)
        val body = status ?: return null
        return buildPrepared(body, WallpaperPickModes.labelFor(pickMode), cacheTimeoutMs)
    }

    private fun schedulePreload() {
        if (WallpaperSession.preloadInFlight) return
        val gen = WallpaperSession.generation.get()
        WallpaperSession.preloadInFlight = true
        WallpaperSession.executor().execute {
            try {
                if (gen != WallpaperSession.generation.get()) return@execute
                val prepared = pickPrepared(MediaPreloader.PREFETCH_TIMEOUT_MS) ?: return@execute
                if (gen != WallpaperSession.generation.get()) return@execute
                WallpaperSession.buffer.offerPreload(prepared)
                if (prepared.stillRemoteUri != null && prepared.isVideo) {
                    WallpaperSession.preloader(this).prefetch(prepared.stillRemoteUri)
                }
            } catch (e: Exception) {
                Log.e("Wallpaparr", "preload failed", e)
            } finally {
                if (gen == WallpaperSession.generation.get()) {
                    WallpaperSession.preloadInFlight = false
                }
            }
        }
    }

    private fun wallpapersForEvent(event: Event?): List<Wallpaper> {
        var forceRefresh = false
        if (event is Event.LauncherIdleModeChanged) {
            if (!event.isIdle) {
                if (PreferencesManager.refreshOnIdleExit) {
                    forceRefresh = true
                } else {
                    val held = WallpaperSession.buffer.snapshotShowing() ?: lastPreparedFromPrefs()
                    return WallpaperTransition.displayList(held, null).map { toWallpaper(it) }
                }
            } else {
                // Hold the current frame — empty lists flash black in Projectivy.
                val held = WallpaperSession.buffer.snapshotShowing() ?: lastPreparedFromPrefs()
                return WallpaperTransition.displayList(held, null).map { toWallpaper(it) }
            }
        }

        if (event is Event.TimeElapsed || event == null || forceRefresh) {
            val allowBlocking = forceRefresh ||
                WallpaperSession.buffer.snapshotShowing() == null ||
                !WallpaperSession.preloadInFlight
            val shown = try {
                WallpaperSession.buffer.takeForDisplay(allowBlocking) {
                    pickPrepared(MediaPreloader.DISPLAY_TIMEOUT_MS)
                }
            } catch (e: Exception) {
                Log.e("Wallpaparr", "getWallpapers failed", e)
                WallpaperSession.buffer.snapshotShowing() ?: lastPreparedFromPrefs()
            }
            if (shown != null && shown.playbackUri != PreferencesManager.lastWallpaperUri) {
                persistShown(shown)
            }
            schedulePreload()
            val held = shown ?: WallpaperSession.buffer.snapshotShowing() ?: lastPreparedFromPrefs()
            return WallpaperTransition.displayList(shown, held).map { toWallpaper(it) }
        }
        return WallpaperTransition.displayList(
            null,
            WallpaperSession.buffer.snapshotShowing() ?: lastPreparedFromPrefs(),
        ).map { toWallpaper(it) }
    }

    private val binder = object : IWallpaperProviderService.Stub() {
        override fun getWallpapers(event: Event?): List<Wallpaper> = wallpapersForEvent(event)

        override fun getPreferences(): String = PreferencesManager.export()
        override fun setPreferences(params: String) {
            PreferencesManager.import(params)
            WallpaperSession.invalidate()
        }
    }
}
