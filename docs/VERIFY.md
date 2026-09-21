# Verify Wallpaparr locally (no Jellyfin, no GHCR)

The owner’s assistant can run this on a machine with Docker. It **builds the repo Dockerfile**; it does not need a published GHCR image or a real media server.

## 1. One command

```bash
./scripts/verify.sh
```

That script prefers **Docker Compose v2** (`docker compose up --build`). `docker-compose.yml` sets `build: .` and `pull_policy: build`, so Compose **always builds from `Dockerfile`** even if GHCR is unpublished.

If the Compose v2 plugin is missing, the same script falls back to:

```bash
mkdir -p data
cp -n config.example.json data/config.json || true
docker build -t wallpaparr:local .
docker run --rm -p 8787:8787 \
  -v "$PWD/data:/data" \
  -e PUBLIC_BASE_URL=http://127.0.0.1:8787 \
  -e SUITE_DATA=/data \
  -e SUITE_LAYOUTS=/data/layouts \
  -e SUITE_GALLERY=/data/gallery \
  -e SUITE_CONFIG=/data/config.json \
  wallpaparr:local
```

You can run those two commands by hand as well.

## 2. Healthcheck

Wait until healthy (the script already waits), or:

```bash
curl -sf http://127.0.0.1:8787/api/health
```

Expected:

```json
{"ok":true,"service":"wallpaparr","version":"1.0.0"}
```

Compose healthcheck: `curl -sf http://127.0.0.1:8787/api/health` inside the container. UI: http://127.0.0.1:8787

## 3. Demo wallpaper status (fixture catalog)

First boot seeds six demo titles into the **Netflix Hero** layout when the catalog is empty (`SUITE_SKIP_SEED` is unset). Generation is last-to-first so `sort=latest` is **Northlight**. No Jellyfin/Seerr keys required.

```bash
curl -sf "http://127.0.0.1:8787/api/wallpaper/status?layout=Netflix%20Hero&sort=latest"
```

Expected fields (tvbgsuite-compatible): `imageUrl`, `actionUrl`, `path`, `title`, `layout`. Demo `title` for `sort=latest` is **Northlight**. Open `imageUrl` in a browser — it is a JPEG painted over a **license-safe cinematic still** (NASA aurora for Northlight), not a synthetic-only gradient.

License-safe demo catalog (Wikimedia Commons: NASA, NARA, Library of Congress, one CC BY-SA photograph):

```bash
curl -sf http://127.0.0.1:8787/api/demo/catalog
curl -sf -o /tmp/northlight.jpg http://127.0.0.1:8787/api/media/artwork/demo-jf-1
ls -l /tmp/northlight.jpg
curl -sf -o /tmp/northlight-logo.png http://127.0.0.1:8787/api/media/logo/demo-jf-1
file /tmp/northlight-logo.png
# Harbor Season has no logo — expect HTTP 404 and title-text fallback:
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8787/api/media/logo/demo-jf-2
```

Tonight + health (same demo catalog):

```bash
curl -sf "http://127.0.0.1:8787/api/tonight?layout=Netflix%20Hero"
curl -sf http://127.0.0.1:8787/api/dashboard
```

## 4. Unit tests (no Docker)

`./scripts/test.sh` creates `backend/.venv` if it is missing (PEP 668 / distro Python), installs pytest there, then runs backend / frontend / plugin `:core` tests.

```bash
# equivalent first-time setup
python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements-dev.txt
cd web && npm ci && cd ..

./scripts/test.sh
```

If `python3 -m venv` fails, install `python3-venv` (Debian/Ubuntu) and retry.

## 5. Plugin APK

**Primary:** GitHub **Release** asset [`wallpaparr-plugin-release.apk`](https://github.com/iManunator/wallpaparr/releases/latest/download/wallpaparr-plugin-release.apk) (tag `v1.0.0` after it is published). See [RELEASE.md](RELEASE.md).

CI also uploads:

1. Artifact **`wallpaparr-plugin-apk`** on green **CI** runs
2. Files: **`wallpaparr-plugin-release.apk`** (sideload) and `wallpaparr-plugin-debug.apk`

Image artifact on PR runs: **`wallpaparr-image`** (`wallpaparr-image.tar.gz`). Pushes to `main` publish `ghcr.io/imanunator/wallpaparr:latest` instead.

Sideload: `adb install -r wallpaparr-plugin-release.apk`, then Projectivy → Wallpaper → **Wallpaparr**.
