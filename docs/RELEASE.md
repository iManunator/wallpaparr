# Shipping Wallpaparr (GHCR + GitHub Release APK)

The product version lives in `VERSION`. Binaries are **not** committed to git. They are published by GitHub Actions.

| What you want | Where it lives |
| --- | --- |
| Container image | [`ghcr.io/imanunator/wallpaparr`](https://github.com/iManunator/wallpaparr/pkgs/container/wallpaparr) |
| Finished plugin APK | GitHub **Release** asset `wallpaparr-plugin-release.apk` (not the Actions artifact, which expires) |
| Source | this repository (`main`) |

## Permissions (why `packages: write` exists)

Both workflows declare:

```yaml
permissions:
  contents: read   # CI — checkout
  packages: write  # GHCR push with GITHUB_TOKEN
```

Release also needs `contents: write` so it can create the GitHub Release and upload APKs.

| Workflow | Trigger | GHCR | APK |
| --- | --- | --- | --- |
| [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) | `push` to `main`, PRs, `workflow_dispatch` | **Yes on `main`** — tags `:latest`, `:ci`, `:sha-<git>`. PRs **build** the image and upload artifact `wallpaparr-image` (no push). | Actions artifact `wallpaparr-plugin-apk` (ephemeral) |
| [`.github/workflows/release.yml`](../.github/workflows/release.yml) | `v*` tag push (or `workflow_dispatch`) | **Yes** — `:latest`, `:vX.Y.Z`, `:X.Y.Z`, `:sha-<git>` | **GitHub Release assets** (durable): `wallpaparr-plugin-release.apk` + debug |

The image is named **`wallpaparr`** (lowercase). GHCR package names are case-sensitive and must be lowercase.

OCI labels `org.opencontainers.image.source` / `.url` point at this repo so GitHub **links the package** under the repository Packages sidebar. Login uses `github.actor` + `secrets.GITHUB_TOKEN` against `ghcr.io`.

If a GHCR push is denied, check **Settings → Actions → General → Workflow permissions** (must allow read/write) and that the workflow YAML still has `packages: write`. First publish creates the package; visibility is already **public** for `wallpaparr`.

## Tag a release — ship after the version bump lands on `main`

**Do not retag earlier versions.** After bumping `VERSION` (and `plugin/app/build.gradle.kts`, `web/package.json`) and landing that on `main`, e.g. for `1.0.0`:

```bash
git checkout main
git pull origin main
git tag -a v1.0.0 -m "Wallpaparr 1.0.0"
git push origin v1.0.0
```

The **Release** workflow then publishes:

- Image: `ghcr.io/imanunator/wallpaparr:v1.0.0`, `:1.0.0`, and `:latest`
- GitHub Release: `https://github.com/iManunator/wallpaparr/releases/tag/v1.0.0`
- Primary APK: `wallpaparr-plugin-release.apk`

For the next ship, bump `VERSION` + `CHANGELOG.md` and tag the next version the same way.

`workflow_dispatch` on Release (from `main`) rebuilds and pushes `:latest` without creating a GitHub Release. Use a `v*` tag when you want the APK on the Releases page.

## Pull the published image

```bash
docker pull ghcr.io/imanunator/wallpaparr:latest
docker pull ghcr.io/imanunator/wallpaparr:1.0.0
```

Compose in this repo still **builds the Dockerfile** by default (`pull_policy: build`) so `./scripts/verify.sh` works before GHCR exists. To run the published image:

```bash
export PUBLIC_BASE_URL=http://YOUR_LAN_IP:8787
docker compose pull
# or:
docker run --rm -p 8787:8787 \
  -e PUBLIC_BASE_URL=http://YOUR_LAN_IP:8787 \
  -v "$PWD/data:/data" \
  ghcr.io/imanunator/wallpaparr:latest
```

## Download the plugin APK

Primary:

```text
https://github.com/iManunator/wallpaparr/releases/latest/download/wallpaparr-plugin-release.apk
```

CI also uploads ephemeral artifact **`wallpaparr-plugin-apk`**. Sideload:

```bash
adb connect TV_IP
adb install -r wallpaparr-plugin-release.apk
```

Then Projectivy → Appearance → Wallpaper → **Wallpaparr**.

## What we refuse to put in git

APKs and container tarballs are large binaries. They belong on **Releases** / **GHCR** / Actions artifacts — not in git history.
