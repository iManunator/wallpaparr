package com.imanunator.wallpaparr.core

data class PickMode(
    val id: String,
    val label: String,
    val group: String,
    /** One-line Leanback description: what it does and when to use it. */
    val help: String,
)

data class ResolvedQuery(
    val layout: String,
    val sort: String,
    val pool: String? = null,
    val minYear: String? = null,
    val minRating: Float? = null,
    val profile: String? = null,
    val queue: String? = null,
)

object WallpaperPickModes {
    val ALL: List<PickMode> = listOf(
        PickMode(
            "tonight", "Tonight's mix", "Smart",
            "Best default. Taste-weighted pick — the same mix the web Tonight page previews.",
        ),
        PickMode(
            "continue_watching", "Continue watching", "Smart",
            "Titles you started but have not finished. Same pool as the Continue queue.",
        ),
        PickMode(
            "newly_added", "Newly added", "Smart",
            "Most recently generated stills in this layout. Use after a fresh Generate batch.",
        ),
        PickMode(
            "seerr_trending", "Seerr trending", "Smart",
            "Jellyseerr/Seerr titles, highest rating first. Discovery when the library is thin.",
        ),
        PickMode(
            "pinned", "Pinned titles", "Smart",
            "Only gallery pins. An empty pin list shows nothing — it does not fall back.",
        ),
        PickMode(
            "unwatched", "Unwatched only", "Watch / Library",
            "Never-played titles in this layout. Good for a ‘what should I start?’ wall.",
        ),
        PickMode(
            "partial", "Partly watched", "Watch / Library",
            "In-progress titles only (same idea as Continue watching, without the smart queue extras).",
        ),
        PickMode(
            "watched", "Watched only", "Watch / Library",
            "Finished titles. Use when you want familiar posters, not new ones.",
        ),
        PickMode(
            "in_library", "In Jellyfin library", "Watch / Library",
            "Anything already in the library. Skips Seerr-only / requestable titles.",
        ),
        PickMode(
            "seerr_only", "Seerr only (not in library)", "Watch / Library",
            "On Seerr but not in Jellyfin. Advertise requestable titles on the home screen.",
        ),
        PickMode(
            "requestable", "Requestable on Seerr", "Watch / Library",
            "Seerr titles you can still request. Narrower than Seerr only.",
        ),
        PickMode(
            "available_seerr", "Available on Seerr", "Watch / Library",
            "Marked available on Seerr. Use when availability metadata is filled in.",
        ),
        PickMode(
            "source_jellyfin", "From Jellyfin", "Source",
            "Catalog rows tagged jellyfin. Prefer In Jellyfin library unless you filter by ingest source.",
        ),
        PickMode(
            "source_seerr", "From Seerr", "Source",
            "Catalog rows tagged jellyseerr/seerr, random order. Seerr trending sorts by rating instead.",
        ),
        PickMode(
            "source_plex", "From Plex (catalog tag)", "Source",
            "Rows tagged plex (demo catalog includes some). Skip unless your suite actually stores Plex sources.",
        ),
        PickMode(
            "recent_years", "Recent years", "Source",
            "Random titles from the last N years. Set Recent-years window below (default 3).",
        ),
        PickMode(
            "high_rated", "Above minimum rating", "Source",
            "Highest rated first, cut off by Minimum rating below. Set that value first or this matches Highest rating.",
        ),
        PickMode(
            "random", "Random", "Sort",
            "Any title in this layout. Filters and the no-repeat bag still apply.",
        ),
        PickMode(
            "latest", "Newest generated", "Sort",
            "Most recently baked still first. Use right after Generate / Bake motion.",
        ),
        PickMode(
            "oldest", "Oldest generated", "Sort",
            "Oldest still first. Useful to cycle through a large library evenly.",
        ),
        PickMode(
            "rating_high", "Highest rating", "Sort",
            "Best rated first. Does not require Minimum rating — that filter still applies if you set it.",
        ),
        PickMode(
            "rating_low", "Lowest rating", "Sort",
            "Lowest rated first. Novelty / ‘so-bad-it’s-good’ wall.",
        ),
        PickMode(
            "year_new", "Newest year", "Sort",
            "Newest release year first. Different from Newest generated (file date vs title year).",
        ),
        PickMode(
            "year_old", "Oldest year", "Sort",
            "Oldest release year first. Pair with a year range if you want a decade wall.",
        ),
        PickMode(
            "alt_random_latest", "Alternate random ↔ newest", "Mix",
            "Even ticks random, odd ticks newest generated. No extra layouts needed.",
        ),
        PickMode(
            "alt_library_unwatched", "Alternate library ↔ unwatched", "Mix",
            "Flips each rotate between in-library and unwatched. Keeps the wall mixed.",
        ),
        PickMode(
            "alt_library_seerr", "Alternate library ↔ Seerr-only", "Mix",
            "Flips each rotate between in-library and Seerr-only titles.",
        ),
        PickMode(
            "alt_two_layouts", "Alternate two layouts", "Mix",
            "Flips Primary and Secondary layout each rotate. Fill Secondary layout below.",
        ),
        PickMode(
            "mix_weighted", "Weighted mix: newest vs random", "Mix",
            "Each rotate rolls against Weighted mix % below (that percent newest, the rest random).",
        ),
        PickMode(
            "layout_round_robin", "Layout round-robin", "Mix",
            "Cycles Primary → Secondary → Third each rotate. Fill the extra layout fields.",
        ),
        PickMode(
            "genre_round_robin", "Genre round-robin", "Mix",
            "Cycles the comma-separated Genre filter each rotate. Fill Genre filter first.",
        ),
        PickMode(
            "no_repeat_bag", "No-repeat bag (same as Random)", "Mix",
            "Random from this layout while skipping recently shown files. Random already uses the bag depth below — this mode is the same status-API mapping, kept for older TVs.",
        ),
    )

    fun byId(id: String): PickMode? = ALL.firstOrNull { it.id == id }

    fun at(index: Int): PickMode? = ALL.getOrNull(index)

    fun indexOf(id: String): Int = ALL.indexOfFirst { it.id == id }

    fun labelFor(id: String): String = byId(id)?.label ?: id

    fun helpFor(id: String): String = byId(id)?.help.orEmpty()

    fun resolve(
        modeId: String,
        primaryLayout: String,
        secondaryLayout: String,
        thirdLayout: String,
        mixRatio: Int,
        recentYears: Int,
        counter: Int,
        currentYear: Int,
        minRating: Float = 0f,
    ): ResolvedQuery {
        val primary = primaryLayout
        val secondary = secondaryLayout.ifBlank { primary }
        val third = thirdLayout.ifBlank { secondary }
        val odd = counter % 2 == 0
        return when (modeId) {
            "tonight" -> ResolvedQuery(primary, "random", pool = "taste:tonight")
            "continue_watching" -> ResolvedQuery(primary, "random", pool = "continue_watching", queue = "continue_watching")
            "newly_added" -> ResolvedQuery(primary, "latest", pool = "newly_added", queue = "newly_added")
            "seerr_trending" -> ResolvedQuery(primary, "rating", pool = "source:jellyseerr", queue = "seerr_trending")
            "pinned" -> ResolvedQuery(primary, "random", pool = "pinned", queue = "pinned")
            "latest" -> ResolvedQuery(primary, "latest")
            "oldest" -> ResolvedQuery(primary, "oldest")
            "rating_high" -> ResolvedQuery(primary, "rating")
            "rating_low" -> ResolvedQuery(primary, "rating_asc")
            "year_new" -> ResolvedQuery(primary, "year")
            "year_old" -> ResolvedQuery(primary, "year_asc")
            "unwatched" -> ResolvedQuery(primary, "random", pool = "unwatched", queue = "unwatched")
            "partial" -> ResolvedQuery(primary, "random", pool = "partial")
            "watched" -> ResolvedQuery(primary, "random", pool = "watched")
            "in_library" -> ResolvedQuery(primary, "random", pool = "in_library")
            "seerr_only" -> ResolvedQuery(primary, "random", pool = "seerr_only")
            "requestable" -> ResolvedQuery(primary, "random", pool = "requestable", queue = "requestable")
            "available_seerr" -> ResolvedQuery(primary, "random", pool = "available")
            "source_jellyfin" -> ResolvedQuery(primary, "random", pool = "source:jellyfin")
            "source_seerr" -> ResolvedQuery(primary, "random", pool = "source:jellyseerr")
            "source_plex" -> ResolvedQuery(primary, "random", pool = "source:plex")
            "recent_years" -> {
                val year = currentYear - recentYears.coerceIn(1, 50)
                ResolvedQuery(primary, "random", minYear = year.toString())
            }
            "high_rated" -> ResolvedQuery(primary, "rating", minRating = minRating)
            "alt_random_latest" ->
                if (odd) ResolvedQuery(primary, "random") else ResolvedQuery(primary, "latest")
            "alt_library_unwatched" ->
                if (odd) ResolvedQuery(primary, "random", pool = "in_library")
                else ResolvedQuery(primary, "random", pool = "unwatched")
            "alt_library_seerr" ->
                if (odd) ResolvedQuery(primary, "random", pool = "in_library")
                else ResolvedQuery(primary, "random", pool = "seerr_only")
            "alt_two_layouts" ->
                if (odd) ResolvedQuery(primary, "random") else ResolvedQuery(secondary, "random")
            "mix_weighted" -> {
                val useLatest = (counter % 100) < mixRatio.coerceIn(0, 100)
                if (useLatest) ResolvedQuery(primary, "latest") else ResolvedQuery(primary, "random")
            }
            "layout_round_robin" -> {
                val layouts = listOf(primary, secondary, third).distinct().filter { it.isNotBlank() }
                if (layouts.isEmpty()) ResolvedQuery(primary, "random")
                else ResolvedQuery(layouts[counter % layouts.size], "random")
            }
            // Genre is applied by the plugin from the filter CSV; mapping is random + that filter.
            "genre_round_robin" -> ResolvedQuery(primary, "random")
            // Exclude bag is always sent on /status; this id stays for older saved prefs.
            "no_repeat_bag" -> ResolvedQuery(primary, "random")
            else -> ResolvedQuery(primary, "random")
        }
    }

    fun nextGenreForRoundRobin(genreCsv: String, counter: Int): String? {
        val genres = genreCsv.split(",").map { it.trim() }.filter { it.isNotEmpty() }
        if (genres.isEmpty()) return null
        return genres[counter % genres.size]
    }
}
