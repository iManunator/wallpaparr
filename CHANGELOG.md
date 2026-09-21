# Changelog

## Unreleased

- **Cleanup no longer deletes wallpapers from other sources.** Running "Cleanup titles no longer in the source list" for one source (e.g. Jellyfin) was also wiping every Seerr-sourced wallpaper in that layout, and vice versa, because cleanup only scoped by layout, not by the source it actually fetched this run.
- Cron schedules now default "Refresh when watch / availability changes" on, same as Generate.
- Settings → Cron / batch has its own "Save settings" button next to "Add cron job", so you don't have to scroll to the bottom of the page after editing schedules.

## 1.0.0 - 2026-09-21

Initial public release.

- **Tonight preview.** See the exact wallpaper Projectivy will show next, picked from the taste mix, before it ever hits the TV.
- **Six layout presets** (Netflix Hero, Prime Cinematic, Google TV Clean, Projectivy Dock, Status Focus, Jellyfin Dense) with TV-safe chrome, plus a full in-page editor for building your own.
- **Optional parallax motion.** Baked H.264 loops with locked chrome over an animated background plate (Subtle / Balanced / Cinematic / Bold), or plain JPEG stills — your choice, per batch or per title.
- **Smart queues and taste profiles.** Unwatched, watched, partly-watched, continue watching, newly added, Seerr trending, requestable, and pinned — combined into weighted taste mixes (`tonight`, `unwatched_heavy`, `cinephile`, `discovery`, or your own), including on the plugin's own pick mode.
- **Jellyfin and Jellyseerr sources**, including Seerr discover categories (trending, popular, upcoming) with an "upcoming" badge, and optional OMDb enrichment (IMDb rating, Rotten Tomatoes, Metacritic, awards).
- **Cron scheduling** — multiple independent jobs, each with its own skip/replace/refresh/cleanup rules; a bad cron expression is rejected on save and surfaced on the dashboard instead of silently never running.
- **Gallery** with search, pin/never-show, and a fullscreen viewer that plays the real baked video when one exists.
- **Projectivy plugin (Android TV)** with basic/advanced settings, multiple pick modes, and deep-link support for Jellyfin, Moonfin, SeerrTV, Fladder, Kodi, Wholphin, and Void.
- **Demo mode** — no Jellyfin required to try it; six license-safe fixture titles seed automatically.
- **Optional HTTP basic auth.** Set `WALLPAPARR_AUTH_USER` / `WALLPAPARR_AUTH_PASSWORD` to gate the web UI and mutating APIs. Unset (the default) is fully open on the LAN. Plugin status/image GETs and `/api/health` always stay open so the TV and Docker healthcheck keep working. `docker-compose.yml` also documents an opt-in `PUID`/`PGID` (default `0:0`/root, so bind-mounts stay writable without an extra chown step).
- **`GET /api/settings` redacts provider API keys** (shown as `********`); saving keeps the stored key unless you type a new one, and a blank field clears it.
- **Hardened generate/gallery paths.** Replacing a title writes the new still before removing the old catalog rows, so a fetch/render failure can't wipe a wallpaper with nothing to show for it. Filenames and proxy ids are confined to their intended folder; JSON writes are atomic with unique temp files and fsync.
- **Hardened outbound fetches.** HTTP requests reject non-http(s) URLs, cap response size, and strip `Authorization`/`X-Emby-Token`/`X-Api-Key` the moment a redirect crosses to a different host. Jellyfin's token is only attached when the request's origin exactly matches the configured server.
- Plugin versionName **1.0.0** (`versionCode` 1). Image `ghcr.io/imanunator/wallpaparr:v1.0.0` / `:1.0.0` / `:latest` from the `v1.0.0` tag.
