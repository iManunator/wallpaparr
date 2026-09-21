<p align="center">
  <img src="docs/screenshots/logo.svg" alt="Wallpaparr" width="480"/>
</p>

<p align="center">
  Cinematic live wallpapers for Projectivy, baked from your Jellyfin / Jellyseerr library.<br/>
  Stills, or optional <em>parallax VIDEO</em> loops if you want the home screen to actually move.
</p>

<p align="center">
  <a href="https://github.com/iManunator/wallpaparr/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/iManunator/wallpaparr/actions/workflows/ci.yml/badge.svg"></a>
  <a href="https://github.com/iManunator/wallpaparr/actions/workflows/release.yml"><img alt="Release" src="https://github.com/iManunator/wallpaparr/actions/workflows/release.yml/badge.svg"></a>
  <a href="https://github.com/iManunator/wallpaparr/releases/latest"><img alt="Latest release" src="https://img.shields.io/github/v/release/iManunator/wallpaparr?display_name=tag&sort=semver&label=release"></a>
  <a href="https://github.com/iManunator/wallpaparr/pkgs/container/wallpaparr"><img alt="GHCR" src="https://img.shields.io/badge/ghcr.io-imanunator%2Fwallpaparr-0ea5e9?logo=docker&logoColor=white"></a>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-e2b657"></a>
  <img alt="Version 1.0.1" src="https://img.shields.io/badge/version-1.0.1-7ad0c4"/>
</p>

<p align="center">
  <a href="https://ko-fi.com/Z3W827EG1B"><img alt="ko-fi" src="https://ko-fi.com/img/githubbutton_sm.svg"></a>
</p>

<p align="center">
  <a href="#what-you-need">What you need</a> ·
  <a href="#downloads">Downloads</a> ·
  <a href="#get-it-running">Get it running</a> ·
  <a href="#connect-your-library-and-generate">Connect your library</a> ·
  <a href="#the-tv-plugin">TV plugin</a> ·
  <a href="docs/REFERENCE.md">Full reference</a> ·
  <a href="docs/INSTALL.md">Install details</a> ·
  <a href="CHANGELOG.md">Changelog</a>
</p>

It's an *arr* box for the home screen: titles in, wallpaper out, Projectivy plays it on the TV.

---

## Tonight, on your home screen

<p align="center">
  <img src="docs/screenshots/wallpaparr-demo.gif" alt="Wallpaparr parallax VIDEO wallpaper — Netflix Hero chrome over a real baked loop" width="100%"/>
</p>

<p align="center">
  <em>A real baked parallax loop, not a mockup — Netflix Hero chrome over a license-safe demo still. Same pipeline that runs against your Jellyfin/Seerr library.</em>
</p>

You get a small server plus a Projectivy plugin. The server pulls titles, bakes a 16:9 wallpaper (title, rating, watch status, optional motion), and the plugin feeds that to the TV. Open Tonight in the web UI and you're looking at the next frame Projectivy will show.

| Page | What it's for |
| --- | --- |
| **Tonight** | Home. Live preview of whatever the TV will show next. |
| **Gallery** | Every still you've baked. Pin, hide, delete, or open full-screen (plays the MP4 when there is one). |
| **Editor** | Layout, fonts, colors, badges, motion. Six presets if you don't want to start from a blank canvas. |
| **Generate** | Pull a batch from Jellyfin/Jellyseerr and bake it. That's the whole job. |
| **Settings** | URLs and API keys, taste mix, motion defaults, cron. |
| **Dashboard** | Gallery size, last cron, whether the providers actually answered. |

---

## What you need

- **Docker** (or Compose) on a machine the TV can reach on the LAN
- **Projectivy** on the Android TV / Google TV, if you want the plugin
- **Jellyfin** and/or **Jellyseerr/Seerr** only when you're ready for your own titles — demo mode runs with neither

The box is a container on **`:8787`** with a `data/` volume. The plugin lives on the TV.

---

## Downloads

| Get | Link |
| --- | --- |
| **Plugin APK (primary)** | [`wallpaparr-plugin-release.apk`](https://github.com/iManunator/wallpaparr/releases/latest/download/wallpaparr-plugin-release.apk) on the [latest GitHub Release](https://github.com/iManunator/wallpaparr/releases/latest) |
| **Container** | [`ghcr.io/imanunator/wallpaparr:latest`](https://github.com/iManunator/wallpaparr/pkgs/container/wallpaparr) |

```bash
docker pull ghcr.io/imanunator/wallpaparr:latest
adb install -r wallpaparr-plugin-release.apk
```

Older tags, debug APKs, and CI artifacts: [Downloads in the full reference](docs/REFERENCE.md) or [docs/RELEASE.md](docs/RELEASE.md).

---

## Get it running

```bash
mkdir -p data && cp -n config.example.json data/config.json || true
docker run --name wallpaparr --restart unless-stopped -d -p 8787:8787 \
  -e PUBLIC_BASE_URL=http://YOUR_LAN_IP:8787 \
  -v "$PWD/data:/data" \
  ghcr.io/imanunator/wallpaparr:latest
```

Open **http://127.0.0.1:8787** on the host. Tonight is the home page. Nothing configured yet? It seeds a demo catalog of license-safe stills so you can see it working — no Jellyfin required. Same walkthrough: **[docs/VERIFY.md](docs/VERIFY.md)**.

Give `PUBLIC_BASE_URL` (and the plugin's Server URL) the host's LAN IP or a hostname the TV can resolve. `127.0.0.1` / `localhost` only works from the host itself; the TV can't loop back into your laptop. Browsing the UI from the host is fine on loopback.

There's no login. Settings, generate, and delete are open on purpose — this is a home-LAN box. Don't put `:8787` on the internet unless you've put auth on a reverse proxy in front of it.

Compose, building from source, or parking the gallery on a different disk: **[docs/INSTALL.md](docs/INSTALL.md)**.

---

## Connect your library and generate

When the demo stills get old:

1. **Settings** — Jellyfin URL + API key, and/or Jellyseerr URL + API key. Hit **Test** next to each before you walk away.
2. **Generate** — Source `Jellyfin` (or `Jellyseerr`, or `All configured`), pick a layout, **Run batch**. That pulls titles and bakes a wallpaper for each.
3. **Gallery** — your artwork, ratings, and watch status should be there.
4. Optional: check **Bake parallax / motion VIDEO** on the batch (or bake later per title) if you want looping motion instead of stills.
5. Optional: **Settings → Cron / batch** so new/trending titles generate themselves. A bad cron expression is rejected on save instead of quietly never running.

That's the loop: connect → generate → maybe schedule. Editor, taste mix, and queues only change *how* the wallpapers look and get picked.

---

## The TV plugin

1. Sideload [`wallpaparr-plugin-release.apk`](https://github.com/iManunator/wallpaparr/releases/latest/download/wallpaparr-plugin-release.apk).
2. Projectivy → Appearance → Wallpaper → **Wallpaparr**.
3. Server URL: the same LAN URL as `PUBLIC_BASE_URL` (e.g. `http://YOUR_LAN_IP:8787`).
4. Pick mode **Tonight's mix**. Turn on **Play baked motion (MP4)** if you baked any.

```bash
adb connect TV_IP
adb install -r wallpaparr-plugin-release.apk
```

Package `com.imanunator.wallpaparr`. Pick modes and deep links: [docs/PROJECTIVY.md](docs/PROJECTIVY.md).

---

## Docs

| Doc | What's in it |
| --- | --- |
| [Reference](docs/REFERENCE.md) | Feature list, architecture, API contract, Wallpaparr vs SeerChannel |
| [Install](docs/INSTALL.md) | Docker/Compose, separate-disk gallery, plugin, tvbgsuite migration |
| [Release / GHCR / APK](docs/RELEASE.md) | How `:latest` publishes, tagging, permissions |
| [Verify](docs/VERIFY.md) | Demo mode with no Jellyfin and no GHCR |
| [API](docs/API.md) | Status contract plus editor/ops endpoints |
| [Motion](docs/MOTION.md) | IMAGE vs VIDEO, parallax bake, intensity |
| [Overlays](docs/OVERLAYS.md) | Clock / HA / news hooks |
| [Projectivy plugin](docs/PROJECTIVY.md) | Pick modes, UUID, deep links (Moonfin, SeerrTV, browser fallback) |
| [Changelog](CHANGELOG.md) | Version history |

---

## Credits

- Projectivy wallpaper plugin contract: [spocky/projectivy-plugin-wallpaper-provider](https://github.com/spocky/projectivy-plugin-wallpaper-provider)
- Prior WebGUI work: [androidtvbackgroundWebGui](https://github.com/iManunator/androidtvbackgroundWebGui)

MIT © 2026 iManunator
