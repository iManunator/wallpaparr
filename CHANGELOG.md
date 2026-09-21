# Changelog

## Unreleased

- Generate jobs now keep the selected Jellyseerr category (`seerr_category`) instead of always falling back to trending.
- `/api/health` version is read from the repo `VERSION` file (was a stale `1.2.7`).
- Wallpaper image paths reject directory traversal; missing layouts no longer create empty gallery folders.
- Corrupt `config.json` / `catalog.json` no longer 500 the whole API; JSON writes are atomic.
- `config.example.json` and `.env.example` match runtime settings defaults and documented `SUITE_*` paths.
- CI: `npm ci`, frontend cache, image publish waits for backend/frontend tests, tighter `packages: write` scope.

## 1.0.0 - 2026-09-21

Initial public release.

- **Tonight preview.** See the exact wallpaper Projectivy will show next, picked from the taste mix, before it ever hits the TV.
- **Six layout presets** (Netflix Hero, Prime Cinematic, Google TV Clean, Projectivy Dock, Status Focus, Jellyfin Dense) with TV-safe chrome, plus a full in-page editor for building your own.
- **Optional parallax motion.** Baked H.264 loops with locked chrome over an animated background plate (Subtle / Balanced / Cinematic / Bold), or plain JPEG stills — your choice, per batch or per title.
- **Smart queues and taste profiles.** Unwatched, watched, partly-watched, continue watching, newly added, Seerr trending, requestable, and pinned — combined into weighted taste mixes (`tonight`, `unwatched_heavy`, `cinephile`, `discovery`, or your own).
- **Jellyfin and Jellyseerr sources**, including Seerr discover categories (trending, popular, upcoming) with an "upcoming" badge, and optional OMDb enrichment (IMDb rating, Rotten Tomatoes, Metacritic, awards).
- **Cron scheduling** — multiple independent jobs, each with its own skip/replace/refresh/cleanup rules.
- **Gallery** with search, pin/never-show, and a fullscreen viewer that plays the real baked video when one exists.
- **Projectivy plugin (Android TV)** with basic/advanced settings, multiple pick modes, and deep-link support for Jellyfin, Moonfin, SeerrTV, Fladder, Kodi, Wholphin, and Void.
- **Demo mode** — no Jellyfin required to try it; six license-safe fixture titles seed automatically.
- Plugin versionName **1.0.0** (`versionCode` 1). Image `ghcr.io/imanunator/wallpaparr:v1.0.0` / `:1.0.0` / `:latest` from the `v1.0.0` tag.
