# Changelog

## Unreleased

- Replace/generate no longer deletes the previous still before the new JPEG is on disk (a render failure used to wipe the title). Still-only replace also removes a leftover sibling MP4 so the TV cannot keep playing stale motion.
- Gallery delete confines filenames with `Path.name` (same as wallpaper GET) and no longer mkdir's empty layout folders as a side effect of delete.
- Jellyfin API keys are attached only when the artwork URL's origin matches the configured server — a lookalike host no longer receives the MediaBrowser token.
- Catalog/settings/ops atomic writes use unique temp names (no same-pid collision) and fsync before rename.
- `MotionProfile()` encode defaults now match `AppSettings` (24 fps, 15s, balanced intensity, fly-in on, 1.0s edge fade).
- HTTP fetches reject non-http(s) URLs and cap response size. Generate `limit` is 1–200.
- Cron generate failures are recorded on the dashboard (`cron.last.ok: false`) instead of only raising in the scheduler thread.
- Optional HTTP basic auth via `WALLPAPARR_AUTH_USER` / `WALLPAPARR_AUTH_PASSWORD` (plugin wallpaper GETs stay open). Compose documents optional `PUID`/`PGID` (default 0:0).
- Docs: POST blank API key clears (does not keep); ids search pulls 200 titles, not 40.

- Motion bake fallbacks now match `AppSettings` (24 fps, balanced, 15s loop, fly-in on) instead of the old 30 fps / cinematic / quality-duration tables when a field is missing.
- Invalid cron expressions are rejected on save and listed on the dashboard instead of being skipped with no warning.
- `GET /api/settings` redacts provider API keys; a round-trip save keeps the stored secret unless you type a new one (or clear the field).
- Layout JSON writes use the same atomic tempfile+rename path as catalog/settings; a truncated layout file no longer 500s the API.
- Plugin status requests can send `profile` / `queue`; Tonight's mix follows the configured taste profile and slider weights.
- CI image publish waits on Android tests; Release workflow `packages: write` is job-scoped.
- README rewritten in a less brochure-y voice. Docs version examples catch up to 1.0.1.

## 1.0.1 - 2026-09-21

- **Generate jobs no longer drop the Jellyseerr category.** Async batches now keep `seerr_category` (e.g. "Upcoming movies") instead of always falling back to trending; cron jobs already forwarded it correctly.
- **`/api/health` version fixed.** It was reading a stale hardcoded `1.2.7`; now reads the repo `VERSION` file, so it correctly reports `1.0.1`.
- **Wallpaper path resolution hardened.** A sibling folder like `Netflix Hero-extra/` could be read as if it were inside `Netflix Hero/`; fixed with proper path containment instead of a string-prefix check.
- **Corrupt `config.json` / `catalog.json` no longer 500 the whole API.** JSON writes are now atomic (sibling tempfile + rename), and a broken file is left on disk instead of being silently overwritten.
- `config.example.json` and `.env.example` now match the app's actual runtime defaults, and document the `SUITE_*` container paths.
- CI: `packages: write` scoped to just the image-publish job (was workflow-wide), image publish now waits on backend + frontend tests, `npm ci` everywhere for reproducible installs.
- Frontend error toasts now parse FastAPI's `{detail: [...]}` validation-error array instead of assuming `detail` is always a string.
- README: a short "What you need" section, one LAN-URL warning, and a note that mutating APIs are unauthenticated by design on a home LAN.
- Plugin versionName **1.0.1** (`versionCode` 2). Image `ghcr.io/imanunator/wallpaparr:v1.0.1` / `:1.0.1` / `:latest` from the `v1.0.1` tag.

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
