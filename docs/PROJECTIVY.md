# Projectivy plugin (Wallpaparr)

Display name: **Wallpaparr**  
Package: **`com.imanunator.wallpaparr`**  
UUID: `dba9a12f-6252-4172-b5a3-8668d0523afb`  
AIDL contract: `tv.projectivy.plugin.wallpaperprovider.api` (unchanged from [upstream sample](https://github.com/spocky/projectivy-plugin-wallpaper-provider)).

## Build

```bash
cd plugin
./gradlew :core:test
./gradlew :app:assembleDebug :app:assembleRelease
```

**Install from the GitHub Release** (durable): [`wallpaparr-plugin-release.apk`](https://github.com/iManunator/wallpaparr/releases/latest/download/wallpaparr-plugin-release.apk).

CI also uploads ephemeral artifact **`wallpaparr-plugin-apk`** (same filenames) on every green Android job. See [INSTALL.md](INSTALL.md) and [RELEASE.md](RELEASE.md).

The `:core` JVM module holds pick-mode mapping, Leanback settings copy, URL rewrite, IMAGE vs VIDEO choice, preload/double-buffer helpers, and deep-link builders so logic is tested without an emulator.

## Home-screen safe zones

Layout DNA chrome stays left of the clock and above the row dock (`SAFE_LEFT` / `SAFE_RIGHT` = 72, `SAFE_TOP` = 96 for logos, `SAFE_BOTTOM` = 220). **Netflix Hero** is the gold title stack (title at 80,70 with a dedicated watch/Seerr row). The other bundled presets follow that rhythm so pills, logos, and titles do not overlap on 16:9.

## IMAGE vs VIDEO

Projectivy `WallpaperType.IMAGE` (0) plays `imageUrl` (JPEG). `WallpaperType.VIDEO` (4) loops `videoUrl` (H.264 MP4). Wallpaparr always keeps the still; motion is an optional sibling file. Plugin setting **Play baked motion (MP4)** picks VIDEO when `videoUrl` is present; **If no MP4, show the JPEG still** uses IMAGE otherwise (off = skip still-only titles and hold the previous wallpaper). Depth layers are baked into the MP4 (Projectivy is not a compositor): ffmpeg pans the artwork plate and overlays static logo/title chrome. Details: [MOTION.md](MOTION.md).

## Smooth MP4 / wallpaper transitions

Projectivy calls `getWallpapers()` and then **replaces** the current player with whatever we return. The AIDL `Wallpaper` object is a single `uri` + `type` — there is no poster, crossfade, or “hold previous frame” field. Returning two items is also a trap: Projectivy caches the list and picks **at random**, which would skip pick-mode ticks.

What the plugin can do:

1. **One item per response.** Always 0 or 1 wallpaper, so pick-mode mapping stays sequential (`exclude`, round-robin counters, mix %).
2. **Hold the last URI** if the next status call fails or the next clip is not ready, instead of `emptyList()` (empty often flashes black).
3. **Double-buffer + disk preload.** After a pick is shown, the plugin fetches the *next* status-API pick and downloads the JPEG/MP4 into app cache, then serves `content://com.imanunator.wallpaparr.media/…` (FileProvider, granted to Projectivy). The next `TimeElapsed` can start from a local file instead of a cold HTTP MP4.
4. **Short Projectivy cache** (`itemsCacheDurationMillis=1000`) so each wallpaper interval asks the plugin again. A long cache would random-cycle a stale batch and break Tonight / round-robin.

**Limit (Projectivy):** swapping IMAGE↔VIDEO or VIDEO→VIDEO still tears down the previous player. A brief hitch can remain even with a local URI. We cannot keep the previous decoded frame on screen once we return a new `Wallpaper`; we only avoid returning empty and avoid making Projectivy open a remote MP4 that has not been fetched yet. Bake `+faststart` on the suite side still matters for the first frame of HTTP playback.

## Settings the plugin sends to the suite

Leanback settings are grouped (Connection, Layouts, What to show, Filters, Mix controls, Motion, Home screen). Each row’s title is the control; the description is either the current value (editable) or a when-to-use hint (checkboxes, pick-mode / client lists). Pick-mode ids are unchanged.

| Setting | Status API |
| --- | --- |
| Primary / secondary / third layout | `layout` (mix and round-robin modes) |
| Tonight’s mix | `pool=taste:tonight` (server taste profile) |
| Continue watching | `pool=continue_watching` |
| Newly added | `sort=latest` + `pool=newly_added` |
| Seerr trending | `pool=source:jellyseerr` + `sort=rating` |
| Pinned titles | `pool=pinned` (no fallback) |
| Genre / age / year | `genre`, `age_rating`, `min_year`, `max_year` |
| Min / max rating | `min_rating`, `max_rating` |
| No-repeat bag depth | `exclude` (every mode) |
| Play baked motion | uses `videoUrl` when `mediaType=video` |

**No-repeat bag (same as Random)** is kept for older saved prefs: the status mapping is `sort=random` plus the global `exclude` bag, which Random already sends.

## Player clients (`ClientIntents.kt`)

Clicking a wallpaper's action opens whichever player the plugin's **Preferred client** setting points at. All logic (which intent to build per client, per URL) lives in `plugin/core/.../ClientIntents.kt`, unit-tested without an emulator. Two behaviors, per client:

- **Deep-link** — opens *this specific title* directly inside the client.
- **Launch** — the client has no public deep-link scheme Wallpaparr can target, so it just brings the app to the foreground on its own home screen; you pick the title yourself from there.

| Client | Package | Library titles (`jellyfin://items/{id}`) | Seerr-only titles (not in library yet) |
| --- | --- | --- | --- |
| **Moonfin** | `org.moonfin.androidtv` | Deep-link via its own `moonfin://item?id={id}` scheme (it's a Flutter app, not a fork of `org.jellyfin.androidtv`, so it has no `StartupActivity` to target) | — |
| **Jellyfin** (Android TV) | `org.jellyfin.androidtv` | Deep-link via a `StartupActivity` VIEW intent (`S.ItemId=`/`S.id=`) — the default when you click a wallpaper | — |
| **SeerrTV** | `ca.devmesh.seerrtv` | Cannot open a Jellyfin item — falls back to the Moonfin deep-link instead | Deep-link via `seerrtv://details/{movie\|tv}/{tmdbId}` (its only registered intent-filter; it does not handle arbitrary Jellyseerr web URLs) |
| **Fladder** | `nl.jknaapen.fladder` | Launch only | Launch only |
| **Kodi** | `org.xbmc.kodi` | Launch only | Launch only |
| **Wholphin** | `com.github.damontecres.wholphin` | Launch only | Launch only |
| **Void** | `com.hritwik.avoid` | Launch (via its Leanback launcher activity) | Launch (via its Leanback launcher activity) |

Seerr-only titles always route through SeerrTV regardless of your preferred client (unless you don't have it installed — see below), since none of the other players can open a title that isn't in the library yet.

**No SeerrTV installed?** Enable **Open Seerr-only titles in browser** in the plugin settings to open the Jellyseerr web page directly instead of trying (and failing) to launch SeerrTV.

## SeerChannel

This plugin only supplies **wallpapers**. Home-screen **Preview Channels** are published by [SeerChannel](https://github.com/iManunator/SeerChannel), which talks to Jellyfin/Jellyseerr directly. Install both if you want rows + cinematic backgrounds. SeerChannel is **not** shipped in Wallpaparr.
