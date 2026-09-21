package com.imanunator.wallpaparr.core

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test

class WallpaperPickModesTest {
    @Test
    fun unwatchedMapsToPool() {
        val q = WallpaperPickModes.resolve("unwatched", "Hero", "", "", 30, 3, 0, 2026)
        assertEquals("random", q.sort)
        assertEquals("unwatched", q.pool)
        assertEquals("Hero", q.layout)
    }

    @Test
    fun seerrSourcePool() {
        val q = WallpaperPickModes.resolve("source_seerr", "Hero", "", "", 30, 3, 0, 2026)
        assertEquals("source:jellyseerr", q.pool)
    }

    @Test
    fun altTwoLayoutsFlipsWithCounter() {
        val even = WallpaperPickModes.resolve("alt_two_layouts", "A", "B", "", 30, 3, 0, 2026)
        val odd = WallpaperPickModes.resolve("alt_two_layouts", "A", "B", "", 30, 3, 1, 2026)
        assertEquals("A", even.layout)
        assertEquals("B", odd.layout)
    }

    @Test
    fun mixWeightedUsesRatio() {
        val latest = WallpaperPickModes.resolve("mix_weighted", "A", "", "", 100, 3, 0, 2026)
        val random = WallpaperPickModes.resolve("mix_weighted", "A", "", "", 0, 3, 0, 2026)
        assertEquals("latest", latest.sort)
        assertEquals("random", random.sort)
    }

    @Test
    fun layoutRoundRobin() {
        val first = WallpaperPickModes.resolve("layout_round_robin", "A", "B", "C", 30, 3, 0, 2026)
        val second = WallpaperPickModes.resolve("layout_round_robin", "A", "B", "C", 30, 3, 1, 2026)
        val third = WallpaperPickModes.resolve("layout_round_robin", "A", "B", "C", 30, 3, 2, 2026)
        assertEquals("A", first.layout)
        assertEquals("B", second.layout)
        assertEquals("C", third.layout)
    }

    @Test
    fun genreRoundRobin() {
        assertEquals("Action", WallpaperPickModes.nextGenreForRoundRobin("Action,Drama", 0))
        assertEquals("Drama", WallpaperPickModes.nextGenreForRoundRobin("Action,Drama", 1))
        assertNull(WallpaperPickModes.nextGenreForRoundRobin("", 0))
    }

    @Test
    fun recentYearsComputesMinYear() {
        val q = WallpaperPickModes.resolve("recent_years", "A", "", "", 30, 3, 0, 2026)
        assertEquals("2023", q.minYear)
    }

    @Test
    fun tonightMapsToTastePool() {
        val q = WallpaperPickModes.resolve("tonight", "Hero", "", "", 30, 3, 0, 2026)
        assertEquals("taste:tonight", q.pool)
        assertEquals("random", q.sort)
    }

    @Test
    fun continueWatchingAndNewlyAdded() {
        val watching = WallpaperPickModes.resolve("continue_watching", "Hero", "", "", 30, 3, 0, 2026)
        val newest = WallpaperPickModes.resolve("newly_added", "Hero", "", "", 30, 3, 0, 2026)
        val trending = WallpaperPickModes.resolve("seerr_trending", "Hero", "", "", 30, 3, 0, 2026)
        val pinned = WallpaperPickModes.resolve("pinned", "Hero", "", "", 30, 3, 0, 2026)
        assertEquals("continue_watching", watching.pool)
        assertEquals("latest", newest.sort)
        assertEquals("newly_added", newest.pool)
        assertEquals("source:jellyseerr", trending.pool)
        assertEquals("rating", trending.sort)
        assertEquals("pinned", pinned.pool)
    }

    @Test
    fun everyModeHasUniqueIdLabelAndHelp() {
        val ids = WallpaperPickModes.ALL.map { it.id }
        assertEquals(ids.size, ids.toSet().size)
        WallpaperPickModes.ALL.forEach { mode ->
            assertTrue(mode.label.isNotBlank(), mode.id)
            assertTrue(mode.help.length > 20, mode.id)
            assertTrue(mode.group.isNotBlank(), mode.id)
        }
    }

    @Test
    fun everyModeResolvesWithoutThrowingAndUnknownIsRandom() {
        WallpaperPickModes.ALL.forEach { mode ->
            val q = WallpaperPickModes.resolve(mode.id, "Hero", "Prime", "Dock", 40, 5, 0, 2026, 7f)
            assertEquals(
                if (mode.id == "alt_two_layouts" || mode.id == "layout_round_robin") {
                    q.layout.isNotBlank()
                } else {
                    q.layout == "Hero" || q.layout.isNotBlank()
                },
                true,
                mode.id,
            )
            assertTrue(q.sort.isNotBlank(), mode.id)
        }
        val unknown = WallpaperPickModes.resolve("not_a_real_mode", "Hero", "", "", 30, 3, 0, 2026)
        assertEquals("random", unknown.sort)
        assertEquals("Hero", unknown.layout)
        assertNull(unknown.pool)
    }

    @Test
    fun noRepeatBagAndGenreRoundRobinStayRandomOnTheStatusApi() {
        val bag = WallpaperPickModes.resolve("no_repeat_bag", "Hero", "", "", 30, 3, 0, 2026)
        val genre = WallpaperPickModes.resolve("genre_round_robin", "Hero", "", "", 30, 3, 0, 2026)
        val random = WallpaperPickModes.resolve("random", "Hero", "", "", 30, 3, 0, 2026)
        assertEquals(random, bag)
        assertEquals(random, genre)
    }

    @Test
    fun indexLookupMatchesIdAndRenamesDoNotBreakById() {
        WallpaperPickModes.ALL.forEachIndexed { index, mode ->
            assertEquals(mode, WallpaperPickModes.at(index))
            assertEquals(index, WallpaperPickModes.indexOf(mode.id))
            assertEquals(mode, WallpaperPickModes.byId(mode.id))
        }
        assertNull(WallpaperPickModes.at(-1))
        assertNull(WallpaperPickModes.byId("missing"))
        assertEquals("Tonight's mix", WallpaperPickModes.labelFor("tonight"))
    }

    @Test
    fun highRatedUsesMinRatingAndSeerrOnlyKeepsPool() {
        val rated = WallpaperPickModes.resolve("high_rated", "Hero", "", "", 30, 3, 0, 2026, 8.5f)
        assertEquals("rating", rated.sort)
        assertEquals(8.5f, rated.minRating)
        val seerr = WallpaperPickModes.resolve("seerr_only", "Hero", "", "", 30, 3, 0, 2026)
        assertEquals("seerr_only", seerr.pool)
    }
}

class UrlSupportTest {
    @Test
    fun normalizeAddsSchemeAndSlash() {
        assertEquals("http://192.168.1.9:8787/", UrlSupport.normalizeServerUrl("192.168.1.9:8787"))
        assertEquals("http://192.168.1.9:8787/", UrlSupport.normalizeServerUrl("http://192.168.1.9:8787///"))
    }

    @Test
    fun rewriteLocalhostToLanHost() {
        val rewritten = UrlSupport.rewriteMediaUrl(
            "http://127.0.0.1:8787/api/wallpaper/image/Hero/a.jpg",
            "http://192.168.1.9:8787/",
        )
        assertEquals("http://192.168.1.9:8787/api/wallpaper/image/Hero/a.jpg", rewritten)
    }

    @Test
    fun parseYearRange() {
        assertEquals("2005" to "2010", UrlSupport.parseYearRange("2005-2010"))
        assertEquals("2024" to "2024", UrlSupport.parseYearRange("2024"))
    }

    @Test
    fun jellyfinItemId() {
        assertEquals("abc", UrlSupport.parseJellyfinItemId("jellyfin://items/abc"))
        assertNull(UrlSupport.parseJellyfinItemId("https://example/item"))
    }

    @Test
    fun detectsSeerrActionUrls() {
        assertTrue(UrlSupport.isSeerrActionUrl("http://seerr:5055/movie/1"))
        assertTrue(UrlSupport.isSeerrActionUrl("https://host/tv/99"))
        assertFalse(UrlSupport.isSeerrActionUrl("jellyfin://items/1"))
        assertFalse(UrlSupport.isSeerrActionUrl("http://example.com/other"))
    }

    @Test
    fun preferMotionVideo() {
        assertTrue(UrlSupport.shouldUseVideo(true, "video", "http://x/a.mp4"))
        assertFalse(UrlSupport.shouldUseVideo(false, "video", "http://x/a.mp4"))
        assertFalse(UrlSupport.shouldUseVideo(true, "image", null))
    }

    @Test
    fun excludeBag() {
        val remembered = UrlSupport.rememberShownPath("a.jpg,b.jpg", "c.jpg", 2)
        assertEquals("c.jpg,a.jpg", remembered)
        assertEquals("c.jpg,a.jpg", UrlSupport.excludeQuery(remembered, 5))
    }
}

class StatusRequestTest {
    @Test
    fun omitsBlankOptionalParams() {
        val map = StatusRequest(layout = "Hero", sort = "random", genre = "", minRating = 0f).toQueryMap()
        assertEquals("Hero", map["layout"])
        assertEquals("random", map["sort"])
        assertFalse(map.containsKey("genre"))
        assertFalse(map.containsKey("min_rating"))
    }

    @Test
    fun includesProfileAndQueue() {
        val map = StatusRequest(layout = "Hero", profile = "tonight", queue = "unwatched").toQueryMap()
        assertEquals("tonight", map["profile"])
        assertEquals("unwatched", map["queue"])
    }
}

class ClientIntentsTest {
    @Test
    fun jellyfinDeepLinkContainsItemId() {
        val uri = ClientIntents.deepLinkIntent("org.jellyfin.androidtv", "item-9")
        assertTrue(uri!!.contains("S.ItemId=item-9"))
        assertTrue(uri.contains("org.jellyfin.androidtv"))
    }

    @Test
    fun moonfinDeepLinkUsesItsOwnScheme() {
        // Moonfin is a Flutter app with no StartupActivity — it registers
        // moonfin://item?id=... as its own VIEW intent-filter.
        val uri = ClientIntents.deepLinkIntent(ClientIntents.MOONFIN_PACKAGE, "abc")
        assertEquals("moonfin://item?id=abc", uri)
    }

    @Test
    fun launchOnlyClientsHaveNoDeepLink() {
        assertNull(ClientIntents.deepLinkIntent("org.xbmc.kodi", "x"))
    }

    @Test
    fun seerrHttpActionOpensSeerrTvOwnScheme() {
        // SeerrTV only registers seerrtv://details/{movie|tv}/{tmdbId} — it does
        // not handle arbitrary http(s) URLs even when package-targeted.
        val uri = ClientIntents.resolveActionUri(
            ClientIntents.MOONFIN_PACKAGE,
            "http://192.168.1.10:5055/movie/550",
        )
        assertEquals("seerrtv://details/movie/550", uri)
    }

    @Test
    fun seerrTvActionForTvShowUsesTvMediaType() {
        val uri = ClientIntents.resolveActionUri(
            ClientIntents.MOONFIN_PACKAGE,
            "http://192.168.1.10:5055/tv/1399",
        )
        assertEquals("seerrtv://details/tv/1399", uri)
    }

    @Test
    fun seerrBrowserFallbackOpensRawUrlInsteadOfSeerrTv() {
        val uri = ClientIntents.resolveActionUri(
            ClientIntents.MOONFIN_PACKAGE,
            "http://192.168.1.10:5055/movie/550",
            seerrBrowserFallback = true,
        )
        assertEquals("http://192.168.1.10:5055/movie/550", uri)
    }

    @Test
    fun jellyfinActionUsesMoonfinIr() {
        val uri = ClientIntents.resolveActionUri(
            ClientIntents.MOONFIN_PACKAGE,
            "jellyfin://items/jf-42",
        )
        assertEquals("moonfin://item?id=jf-42", uri)
    }
}

class MediaChoiceTest {
    @Test
    fun prefersVideoWhenClipExists() {
        val chosen = MediaChoice.choose(
            imageUrl = "http://x/a.jpg",
            videoUrl = "http://x/a.mp4",
            mediaType = "video",
            preferMotion = true,
            fallbackStill = true,
        )
        assertEquals(true, chosen!!.isVideo)
        assertTrue(chosen.uri.endsWith(".mp4"))
    }

    @Test
    fun fallsBackToStillWhenMotionMissing() {
        val chosen = MediaChoice.choose(
            imageUrl = "http://x/a.jpg",
            videoUrl = null,
            mediaType = "image",
            preferMotion = true,
            fallbackStill = true,
        )
        assertEquals(false, chosen!!.isVideo)
    }

    @Test
    fun returnsNullWhenNothingAvailable() {
        val chosen = MediaChoice.choose(
            imageUrl = null,
            videoUrl = null,
            mediaType = "image",
            preferMotion = true,
            fallbackStill = true,
        )
        assertNull(chosen)
    }

    @Test
    fun stillPreferredWhenMotionDisabled() {
        val chosen = MediaChoice.choose(
            imageUrl = "http://x/a.jpg",
            videoUrl = "http://x/a.mp4",
            mediaType = "video",
            preferMotion = false,
            fallbackStill = true,
        )
        assertEquals(false, chosen!!.isVideo)
    }

    @Test
    fun blankVideoUrlDoesNotCountAsMotion() {
        val chosen = MediaChoice.choose(
            imageUrl = "http://x/a.jpg",
            videoUrl = "",
            mediaType = "video",
            preferMotion = true,
            fallbackStill = true,
        )
        assertEquals(false, chosen!!.isVideo)
        assertTrue(chosen.uri.endsWith(".jpg"))
    }

    @Test
    fun skipsStillWhenMotionPreferredAndFallbackOff() {
        val chosen = MediaChoice.choose(
            imageUrl = "http://x/a.jpg",
            videoUrl = null,
            mediaType = "image",
            preferMotion = true,
            fallbackStill = false,
        )
        assertNull(chosen)
    }

    @Test
    fun lastResortVideoWhenNoStillExists() {
        val chosen = MediaChoice.choose(
            imageUrl = null,
            videoUrl = "http://x/a.mp4",
            mediaType = "video",
            preferMotion = false,
            fallbackStill = true,
        )
        assertEquals(true, chosen!!.isVideo)
    }
}

class WallpaperTransitionTest {
    @Test
    fun displayListIsNeverTwoItemsSoProjectivyCannotSkipARotate() {
        val a = PreparedWallpaper("http://a.mp4", "content://a", true)
        val b = PreparedWallpaper("http://b.mp4", "content://b", true)
        assertEquals(listOf(b), WallpaperTransition.displayList(b, a))
        assertEquals(listOf(a), WallpaperTransition.displayList(null, a))
        assertEquals(emptyList<PreparedWallpaper>(), WallpaperTransition.displayList(null, null))
    }

    @Test
    fun preferCachedUriFallsBackToHttp() {
        assertEquals("http://x/a.mp4", WallpaperTransition.preferCachedUri("http://x/a.mp4", null))
        assertEquals("http://x/a.mp4", WallpaperTransition.preferCachedUri("http://x/a.mp4", "  "))
        assertEquals("content://wallpaparr/a", WallpaperTransition.preferCachedUri("http://x/a.mp4", "content://wallpaparr/a"))
        assertTrue(WallpaperTransition.isLocalPlayback("content://com.imanunator.wallpaparr.media/a"))
        assertFalse(WallpaperTransition.isLocalPlayback("http://192.168.1.9:8787/a.mp4"))
    }

    @Test
    fun nextCounterAdvancesPickModeTicks() {
        assertEquals(1, WallpaperTransition.nextCounter(0))
        assertEquals(8, WallpaperTransition.nextCounter(7))
    }

    @Test
    fun doubleBufferConsumesPreloadWithoutReloading() {
        val buffer = WallpaperDoubleBuffer<String>()
        var loads = 0
        buffer.offerPreload("next")
        val shown = buffer.takeForDisplay(allowBlocking = true) {
            loads += 1
            "blocking"
        }
        assertEquals("next", shown)
        assertEquals(0, loads)
        assertEquals("next", buffer.snapshotShowing())
        assertFalse(buffer.hasPreload())
    }

    @Test
    fun doubleBufferHoldsPreviousWhenIncomingFails() {
        val buffer = WallpaperDoubleBuffer<String>()
        buffer.takeForDisplay(true) { "first" }
        val held = buffer.takeForDisplay(true) { null }
        assertEquals("first", held)
    }

    @Test
    fun doubleBufferHoldSkipsBlockingWhenAFrameIsOnScreen() {
        val buffer = WallpaperDoubleBuffer<String>()
        buffer.takeForDisplay(true) { "first" }
        var loads = 0
        val held = buffer.takeForDisplay(allowBlocking = false) {
            loads += 1
            "should-not-run"
        }
        assertEquals("first", held)
        assertEquals(0, loads)
    }

    @Test
    fun invalidateDropsBothBuffers() {
        val buffer = WallpaperDoubleBuffer<String>()
        buffer.takeForDisplay(true) { "first" }
        buffer.offerPreload("next")
        buffer.invalidate()
        assertNull(buffer.snapshotShowing())
        assertFalse(buffer.hasPreload())
    }
}

class MediaCacheNamesTest {
    @Test
    fun hashesUrlAndKeepsVideoExtension() {
        val name = MediaCacheNames.fileNameFor("http://tv/api/wallpaper/image/Hero/northlight-demo.mp4")
        assertTrue(name.endsWith(".mp4"))
        assertEquals(24 + ".mp4".length, name.length)
        assertEquals(
            name,
            MediaCacheNames.fileNameFor("http://tv/api/wallpaper/image/Hero/northlight-demo.mp4"),
        )
        assertTrue(
            MediaCacheNames.fileNameFor("http://tv/other.mp4") != name,
        )
    }

    @Test
    fun jpegAndQueryString() {
        assertEquals("jpg", MediaCacheNames.extensionFor("http://x/a.JPG?token=1"))
        assertEquals("png", MediaCacheNames.extensionFor("http://x/a.png"))
        assertEquals("bin", MediaCacheNames.extensionFor("http://x/a"))
    }
}

class PluginSettingsCopyTest {
    @Test
    fun everyLeanbackFieldHasATitleAndWhenToUseHint() {
        val fields = listOf(
            PluginSettingsCopy.CONNECTION,
            PluginSettingsCopy.SERVER,
            PluginSettingsCopy.LAYOUTS,
            PluginSettingsCopy.PRIMARY_LAYOUT,
            PluginSettingsCopy.SECONDARY_LAYOUT,
            PluginSettingsCopy.THIRD_LAYOUT,
            PluginSettingsCopy.WHAT_TO_SHOW,
            PluginSettingsCopy.PICK_MODE,
            PluginSettingsCopy.FILTERS,
            PluginSettingsCopy.GENRE,
            PluginSettingsCopy.AGE,
            PluginSettingsCopy.YEAR,
            PluginSettingsCopy.MIN_RATING,
            PluginSettingsCopy.MAX_RATING,
            PluginSettingsCopy.MIX,
            PluginSettingsCopy.MIX_RATIO,
            PluginSettingsCopy.RECENT_YEARS,
            PluginSettingsCopy.EXCLUDE,
            PluginSettingsCopy.MOTION,
            PluginSettingsCopy.PREFER_MOTION,
            PluginSettingsCopy.FALLBACK_STILL,
            PluginSettingsCopy.HOME,
            PluginSettingsCopy.CLIENT,
            PluginSettingsCopy.IDLE,
        )
        val titles = fields.map { it.title }
        assertEquals(titles.size, titles.toSet().size)
        fields.forEach { field ->
            assertTrue(field.title.isNotBlank())
            assertTrue(field.hint.length > 24, field.title)
        }
    }
}

class ClientIntentsHelpTest {
    @Test
    fun everyClientHasHelpAndIndexLookup() {
        ClientIntents.SUPPORTED.forEachIndexed { index, client ->
            assertTrue(client.help.length > 20, client.name)
            assertEquals(client, ClientIntents.at(index))
        }
        assertNull(ClientIntents.at(99))
        assertEquals(ClientType.DEEP_LINK, ClientIntents.SUPPORTED.first { it.name == "Jellyfin" }.type)
        assertEquals(ClientType.LAUNCH, ClientIntents.SUPPORTED.first { it.name == "Kodi" }.type)
    }
}
