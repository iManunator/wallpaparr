# Install Wallpaparr

SeerChannel (Preview Channel rows) is **not** part of this suite. Wallpaparr ships the **wallpaper server** + **Projectivy wallpaper plugin APK**. For home-screen rows, install [SeerChannel](https://github.com/iManunator/SeerChannel) separately.

## Downloads

| Artifact | Where |
| --- | --- |
| **Plugin APK** | [`wallpaparr-plugin-release.apk`](https://github.com/iManunator/wallpaparr/releases/latest/download/wallpaparr-plugin-release.apk) on the [GitHub Release](https://github.com/iManunator/wallpaparr/releases/latest) |
| **Container** | [`ghcr.io/imanunator/wallpaparr`](https://github.com/iManunator/wallpaparr/pkgs/container/wallpaparr) (`:latest` from `main`, `:1.0.0` from tag `v1.0.0`) |

Packaging, `packages: write`, and the exact tag command: **[RELEASE.md](RELEASE.md)**.

## Local verify (offline demo, no Jellyfin)

Step-by-step for an assistant machine: [VERIFY.md](VERIFY.md)

```bash
./scripts/verify.sh
```

This **builds the Dockerfile** via `docker compose up --build` (`pull_policy: build`; GHCR is not required). Without Compose v2, use `docker build -t wallpaparr:local .` and `docker run` as in [VERIFY.md](VERIFY.md). The script waits for health, then curls:

| Check | URL |
| --- | --- |
| Health | `http://127.0.0.1:8787/api/health` |
| Demo wallpaper | `http://127.0.0.1:8787/api/wallpaper/status?layout=Netflix%20Hero&sort=latest` |
| Demo catalog | `http://127.0.0.1:8787/api/demo/catalog` |
| Demo still | `http://127.0.0.1:8787/api/media/artwork/demo-jf-1` |
| UI | `http://127.0.0.1:8787` |

Empty data dirs auto-seed a demo catalog.

Unit tests: `./scripts/test.sh` (creates `backend/.venv` if needed).

## 1. Server — Docker Compose

```bash
git clone https://github.com/iManunator/wallpaparr.git
cd wallpaparr
mkdir -p data
cp config.example.json data/config.json
cp .env.example .env                      # PUBLIC_BASE_URL must be a LAN URL the TV can open
docker compose up --build -d
```

Open `http://YOUR_LAN_IP:8787`. `config.example.json` matches the server's default settings (taste mix, motion preset, OMDb key slot). `.env.example` documents `PUBLIC_BASE_URL` plus optional `SUITE_*` container paths.

### Storing the gallery (stills + MP4s) on a different disk

The container itself can run anywhere (an SSD-backed pool, for example) while the generated wallpapers — the JPEGs and any baked parallax MP4s under `data/gallery/` — live on a separate, larger disk (an HDD). This is a plain Docker bind-mount, nothing app-specific.

Everything under `/data` is controlled by env vars, each with a default relative to `SUITE_DATA` (`/data` in the container):

| Env var | Default | Contents |
| --- | --- | --- |
| `SUITE_DATA` | `/data` | Root data dir |
| `SUITE_CONFIG` | `$SUITE_DATA/config.json` | Settings |
| `SUITE_LAYOUTS` | `$SUITE_DATA/layouts` | Saved layout JSON |
| `SUITE_GALLERY` | `$SUITE_DATA/gallery` | **Generated stills + MP4s — the big one** |

Since `SUITE_GALLERY` already resolves to `/data/gallery` inside the container, the simplest way to put it on a different disk is to bind-mount your HDD path *over* that subdirectory, on top of the normal `/data` mount — no env var changes needed:

```bash
docker run -d --name wallpaparr --restart unless-stopped -p 8787:8787 \
  -e PUBLIC_BASE_URL=http://YOUR_LAN_IP:8787 \
  -v "$PWD/data:/data" \
  -v /mnt/hdd/wallpaparr-gallery:/data/gallery \
  ghcr.io/imanunator/wallpaparr:latest
```

Or in `docker-compose.yml`, add a second volume line under the existing one:

```yaml
    volumes:
      - ./data:/data
      - /mnt/hdd/wallpaparr-gallery:/data/gallery
```

`config.json` and the layout JSON stay on the fast disk (`./data`), only the (much larger, disk-hungry) generated images/video move to the HDD. Create the HDD-side folder once (`mkdir -p /mnt/hdd/wallpaparr-gallery`) before the first start — Docker will happily bind-mount an empty directory, but a missing parent path fails the mount. If you're migrating an existing install, stop the container, `rsync -a data/gallery/ /mnt/hdd/wallpaparr-gallery/`, add the extra mount line, then start it again.

### Tag a GitHub Release (GHCR + APKs)

**Do not retag earlier versions.** After 1.0.0 is on `main`, tag `v1.0.0` so Release + GHCR publish `wallpaparr-plugin-release.apk` and `:v1.0.0` / `:1.0.0` / `:latest`.

`.github/workflows/release.yml` runs on `v*` tags: pushes `ghcr.io/imanunator/wallpaparr:<tag>` and `:latest` (`packages: write`), then attaches **`wallpaparr-plugin-release.apk`** (and debug) to a GitHub Release (`contents: write`). Details: [RELEASE.md](RELEASE.md).

```bash
git checkout main
git pull origin main
git tag -a v1.0.0 -m "Wallpaparr 1.0.0"
git push origin v1.0.0
```

Merges to **main** also run CI, which pushes GHCR `:latest` when the event is not a pull request.

### Pull a published image (after a release / main build)

```bash
docker pull ghcr.io/imanunator/wallpaparr:latest
# or ghcr.io/imanunator/wallpaparr:1.0.0

export PUBLIC_BASE_URL=http://YOUR_LAN_IP:8787
docker compose pull
docker compose up -d
```

Load a CI image artifact (PR / Actions, artifact name **`wallpaparr-image`**):

```bash
gzip -dc wallpaparr-image.tar.gz | docker load
docker run --rm -p 8787:8787 \
  -e PUBLIC_BASE_URL=http://YOUR_LAN_IP:8787 \
  -v "$PWD/data:/data" \
  ghcr.io/imanunator/wallpaparr:ci
```

## 2. Plugin APK (Android TV / Projectivy)

Download **one** of (prefer the Release — Actions artifacts expire):

- GitHub **Release** asset (primary): [`wallpaparr-plugin-release.apk`](https://github.com/iManunator/wallpaparr/releases/latest/download/wallpaparr-plugin-release.apk)
- GitHub **Actions** artifact **`wallpaparr-plugin-apk`** (same filenames; ephemeral)
- Local: `cd plugin && ./gradlew :app:assembleRelease` → `plugin/app/build/outputs/apk/release/app-release.apk`

Install on the TV:

```bash
adb connect TV_IP
adb install -r wallpaparr-plugin-release.apk
```

Then:

1. Projectivy → Appearance → Wallpaper → **Wallpaparr**
2. Plugin settings → **Server URL** `http://YOUR_LAN_IP:8787`
3. Pick layout, pick mode, filters, preferred client (Jellyfin / Moonfin / …)
4. Enable **Play baked motion (MP4)** if you baked MP4s; keep **If no MP4, show the JPEG still** on
5. Set Projectivy’s wallpaper change interval (the plugin answers `TimeElapsed`)

Package: `com.imanunator.wallpaparr`  
UUID: `dba9a12f-6252-4172-b5a3-8668d0523afb`

## 3. Generate wallpapers

In the web UI: **Generate** → Demo (or Jellyfin / Seerr) → optional *Bake parallax / motion VIDEO*.  
Jellyfin batches download **Backdrop**, then **Primary**, so titles get real library art instead of a gradient with metadata only. Use **Replace existing** to rebuild stills that were generated before that fetch existed.

**Editor** stays an in-page 16:9 stage. With Jellyfin connected, pick a title under **Jellyfin preview** to place layers on the real backdrop. Click a generated still in **Gallery** (or the strip under the editor) for a full-screen view — pin, never-show, or delete from the card or lightbox. The gallery toolbar can **Select all**, **Delete selected**, or **Delete all** (skips pins unless you choose the explicit including-pins option; both paths confirm with a count). Generate shows a live `3/12` progress bar (current title + toast when the batch finishes).

Cron lives under **Settings**. Skip/replace matches Jellyfin, TMDB, and IMDb ids.

## Migrating from TV Background Suite

The older plugin (`com.butch708.projectivy.tvbgsuite`) talked to Flask on port **5000**. Wallpaparr uses **8787** and `com.imanunator.wallpaparr`, so both can be installed side by side. `/api/wallpaper/status` query params stay compatible.
