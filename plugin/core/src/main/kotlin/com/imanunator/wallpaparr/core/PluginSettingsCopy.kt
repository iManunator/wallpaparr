package com.imanunator.wallpaparr.core

/**
 * Leanback Guided Step copy. Titles stay short (TV list rows truncate);
 * [hint] is the description / edit helper — what it does and when to use it.
 */
data class SettingCopy(
    val title: String,
    val hint: String,
)

object PluginSettingsCopy {
    val CONNECTION = SettingCopy(
        "Connection",
        "Where this TV fetches stills and baked MP4s. The box must reach the suite on your LAN.",
    )
    val SERVER = SettingCopy(
        "Server URL",
        "Wallpaparr on the LAN, e.g. http://192.168.1.10:8787 — never 127.0.0.1 (that is the TV itself).",
    )

    val LAYOUTS = SettingCopy(
        "Layouts",
        "Collection folders from the suite. Mix modes use Secondary / Third; leave them blank if you only need one look.",
    )
    val PRIMARY_LAYOUT = SettingCopy(
        "Primary layout",
        "Main collection (e.g. Netflix Hero). Used by every pick mode unless a mix selects another folder.",
    )
    val SECONDARY_LAYOUT = SettingCopy(
        "Secondary layout",
        "Used by Alternate two layouts and Layout round-robin. Leave blank if you are not mixing folders.",
    )
    val THIRD_LAYOUT = SettingCopy(
        "Third layout",
        "Used only by Layout round-robin (third stop). Leave blank to cycle two folders, or one.",
    )

    val WHAT_TO_SHOW = SettingCopy(
        "What to show",
        "Pick mode maps to the wallpaper status API (sort / pool). Filters below still apply.",
    )
    val PICK_MODE = SettingCopy(
        "Wallpaper pick mode",
        "What the next rotate asks the suite for. Tonight’s mix matches the web preview.",
    )

    val FILTERS = SettingCopy(
        "Filters",
        "Narrow the pool. Empty means no extra filter. Genre round-robin also reads the genre list.",
    )
    val GENRE = SettingCopy(
        "Genre filter",
        "Comma-separated, e.g. Action,Drama. Substring match. Genre round-robin cycles these one per rotate.",
    )
    val AGE = SettingCopy(
        "Age rating filter",
        "Comma-separated, e.g. PG-13,R. Matches catalog official ratings (PG-13 equals pg13).",
    )
    val YEAR = SettingCopy(
        "Year or range",
        "One year (2019) or a range (2005-2010). Ignored when pick mode is Recent years (that uses the window below).",
    )
    val MIN_RATING = SettingCopy(
        "Minimum rating",
        "0–10. 0 means no cutoff. Required for Above minimum rating mode; also applied as a filter on other modes.",
    )
    val MAX_RATING = SettingCopy(
        "Maximum rating",
        "0–10. 10 means no cutoff. Use with Minimum rating to keep a band, e.g. 7–9.",
    )

    val MIX = SettingCopy(
        "Mix controls",
        "Only some pick modes read these. Safe to leave at defaults otherwise.",
    )
    val MIX_RATIO = SettingCopy(
        "Weighted mix % newest",
        "0–100. Used by Weighted mix: that percent of rotates are newest generated, the rest random. 30 is a good default.",
    )
    val RECENT_YEARS = SettingCopy(
        "Recent-years window",
        "Used by Recent years. 3 means this year minus 3 (e.g. 2023 when the clock is 2026).",
    )
    val EXCLUDE = SettingCopy(
        "No-repeat bag depth",
        "Skip this many recently shown files on every mode (status API exclude=). 5 is typical; 1 repeats sooner.",
    )

    val MOTION = SettingCopy(
        "Motion (IMAGE vs VIDEO)",
        "Projectivy plays one type at a time. The suite always keeps a JPEG; MP4 is optional.",
    )
    val PREFER_MOTION = SettingCopy(
        "Play baked motion (MP4)",
        "On: loop videoUrl when the suite has an MP4. Off: always show the JPEG still.",
    )
    val FALLBACK_STILL = SettingCopy(
        "If no MP4, show the JPEG still",
        "On (recommended): still-only titles stay on screen. Off: skip titles with no clip (previous wallpaper is held).",
    )

    val HOME = SettingCopy(
        "Home screen",
        "What happens when you click the wallpaper, and when the launcher leaves idle.",
    )
    val CLIENT = SettingCopy(
        "Open titles in",
        "Jellyfin and Moonfin deep-link library titles. Seerr-only wallpapers open SeerrTV. Other apps only launch (no title-level link).",
    )
    val IDLE = SettingCopy(
        "New wallpaper when leaving idle",
        "On: pick a fresh wallpaper after screensaver/idle. Off: keep the last one so the home screen does not hitch.",
    )
    val SEERR_BROWSER_FALLBACK = SettingCopy(
        "Open Seerr-only titles in browser",
        "On: Seerr-only wallpapers (not yet in your library) open the Jellyseerr page in a browser instead of SeerrTV. Off (default): opens SeerrTV.",
    )

    val ADVANCED = SettingCopy(
        "Advanced settings",
        "Secondary/third layout, pick mode, filters, mix controls, and a few less-common toggles.",
    )
}
