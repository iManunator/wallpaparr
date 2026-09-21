# Parallax / live VIDEO wallpapers

Projectivy wallpaper plugins return **one** wallpaper at a time (a 1-item list). The AIDL type is either:

| Type | Constant | What this suite serves |
| --- | --- | --- |
| **IMAGE** | `0` | JPEG still (`imageUrl` → `/api/wallpaper/image/{layout}/{file}.jpg`) |
| **VIDEO** | `4` | Looping H.264 MP4 (`videoUrl` → same path with `.mp4`) |

Projectivy does **not** composite depth layers itself. A “parallax wallpaper” is therefore a **baked VIDEO**: ffmpeg animates an artwork **plate** under **static** metadata chrome, muxed as `yuv420p` + `+faststart` so Android TV can loop it.

## Layers (the model)

Treat every wallpaper as two layers. Intensity presets only change the **background**.

| Layer | Content | Motion |
| --- | --- | --- |
| **Background** | Backdrop / still art (the plate), optional padded light-leak | Subtle pan / zoom / parallax drift. Subtle / Cinematic / Bold change amplitude and loop length. |
| **Foreground / target** | Logo or title text, watch badges, Seerr/requestable chips, metadata, overlay widgets, **and static atmosphere** (vignette, letterbox shadows, edge gradients) | **Static.** Pinned in layout DNA / safe-zone coordinates. Never Ken-Burns with the plate. |

IMAGE stills can bake chrome into the JPEG (nothing moves). VIDEO **must** keep chrome locked: animate the plate, then overlay the chrome PNG each frame.

Watch status (**Unwatched** / **Continue** / **Watched**) is part of that locked chrome when `watch_state` is known. Layout DNA `show_watch_badge` defaults on; turn it off in the editor to omit the pill from stills and VIDEO. Pills are capsules with equal padding so the label is centered on 16:9 chrome.

Seerr / requestable status uses the same locked layer. When a title is **not in the library**, a chip paints next to the watch pill from existing catalog fields (`library_state`, `availability`, `source`):

| Metadata | Chrome label |
| --- | --- |
| `library_state` `seerr_only` / `not_in_library` | **Seerr only** |
| `availability` `requestable` / `not_available` | **Requestable** |
| Seerr source and not in library | **On Seerr** |

In-library titles skip the chip. Layout DNA `show_seerr_badge` defaults on; turn it off in the editor to hide it from stills and VIDEO. Demo **Signal Country** is the mixed Seerr-only / requestable fixture.

## IMAGE vs VIDEO in this suite

1. **Generate always writes a JPEG.** Stills remain first-class. The gallery, in-page editor preview, and `imageUrl` never go away. Jellyfin stills composite over downloaded Backdrop (then Primary) art.
2. **Motion is optional.** Enable *Generate VIDEO loops* in Settings, check *Bake parallax / motion VIDEO* on a batch, tap **Bake motion for this layout** on Generate or the editor, or `POST /api/wallpaper/generate-motion` (`path=` = one filename).
3. **`GET /api/wallpaper/status`** (tvbgsuite-compatible) always returns `imageUrl` + `actionUrl` + `path` when a title is selected. When a sibling MP4 exists:
   - `videoUrl` is set
   - `mediaType` is `"video"`
   - extra fields: `parallaxStyle` (`parallax` \| `kenburns` \| `drift`), `motionDuration` (seconds)
4. **The plugin chooses.** *Play baked motion (MP4)* uses `videoUrl` when present. *If no MP4, show the JPEG still* uses `imageUrl` if the clip is missing. Projectivy then plays IMAGE or VIDEO accordingly. On rotate, the plugin preloads the next file and holds the previous URI until that pick is ready; Projectivy still swaps players (no AIDL crossfade). See [PROJECTIVY.md](PROJECTIVY.md).

```
status ──imageUrl──► JPEG  ──► WallpaperType.IMAGE
      └─videoUrl──► MP4   ──► WallpaperType.VIDEO   (if prefer-motion)
```

`videoUrl` is set only when a real MP4 exists on disk.

## Styles

Styles describe **how the background moves**. Chrome stays locked for every style.

| Style | Background look |
| --- | --- |
| **parallax** (default) | Stronger Ken-Burns on the plate; optional light-leak wash **under** locked chrome. Chrome overlay `x=0,y=0`. |
| **kenburns** | Classic slow zoom/pan of the **artwork plate**, then the same static chrome overlay. Never zoompan a text-burned JPEG. |
| **drift** | Larger pan, tiny zoom of the plate; chrome still pinned. |

Intensity presets **Subtle / Cinematic / Bold** (0.16 / 0.55 / 0.96) change **background** zoom and pan enough to see on a TV (same amplitude as the CSS preview). Duration defaults to **15s** (`motion_duration`, clamp 2–24s) regardless of quality tier. Bake uses a **CSS-like ping-pong** (ease in at the start, peak mid-loop, ease out to a seamless join) — it does **not** zoom out past the cover crop. Plate motion is **subpixel bicubic** (Pillow `EXTENT` on a 2× working plate) — not ffmpeg `zoompan`, which is nearest-neighbour and stair-steps slow pans. Default **24 fps** CFR (`motion_fps`), H.264 Main @ L4.0 `yuv420p` `+faststart`, **no B-frames**, **no scenecut**. Parallax may add a padded **light-leak** wash on the **background** (under locked chrome, never scraping the frame edge — not title chrome, not vignette). Unknown styles (including the typo “parrallelx”) normalize to **parallax**.

## Per-wallpaper variety

**Vary motion slightly per wallpaper** (Settings and Generate; **default on**) gives each title a mild, seeded drift so loops are not identical: pan direction / axis bias, tiny intensity jitter, start phase, and a little pan-vs-zoom mix — still inside the chosen Subtle / Cinematic / Bold family. Chrome, vignette, and letterbox stay locked. The seed is the title’s id, then filename, then name, so a re-bake of the same item is stable. The CSS preview uses the same helper (`vary_motion_profile` / `varyMotionProfile`) so Tonight, editor, Generate, Settings, and gallery lightbox match the bake. Turn the toggle **off** for the exact CSS-matched ease/amplitude path (no randomness). Additive settings field `motion_vary`.

## Edge fade

**Fade to black at clip start/end** (Settings; **default on**) blends the first and last frames of every baked MP4 towards black (`edge_fade_frames` / `apply_edge_fade` in `motion.py`, capped at a quarter of the clip). Projectivy tears down and recreates its player on every wallpaper swap — there is no crossfade in the AIDL contract (see [PROJECTIVY.md](PROJECTIVY.md)) — so that swap otherwise lands as a hard cut mid-scene. Fading each clip's own edges toward black makes the cut land on near-black frames instead, reading as an intentional transition. **Fade duration seconds** (default 1.0, range 0.1–2.5) controls how long that fade runs. This only touches the encode: it does not change Ken-Burns amplitude, chrome, or the CSS preview. Turn the toggle **off** to bake at full brightness throughout. Additive settings fields `motion_edge_fade` / `motion_edge_fade_seconds`.

**Fly-in intro** (Settings; **experimental, default on**) adds a fast zoom-in swoop over the first **Fly-in duration seconds** (default 1.0) of the clip, on top of the normal Ken Burns curve (`fly_in_boost` in `motion.py`). The swoop decays as `(1 − p)²` over that window, so both its value and its rate of change reach exactly zero at the window's end — it hands off to the ordinary parallax drift with no positional or velocity jump, instead of a visible cut between two different motions. Additive settings fields `motion_fly_in` / `motion_fly_in_seconds`.

The web UI plays a **CSS motion preview** of the same layered model on Tonight, the layout editor, Generate, Settings, and the **Gallery lightbox**. Grid thumbs stay static JPEGs. Opening a gallery item plays the baked sibling MP4 when it exists (looping, muted; chrome already in the file). If there is no clip, the lightbox pans the artwork plate and keeps title/logo/badges locked in `.stage-fg` — it does not Ken-Burns the composited JPEG. A failed VIDEO load toasts and falls back to that CSS preview. The CSS loop returns to the start frame (no bounce). That preview is not what Projectivy plays — bake a VIDEO (ffmpeg) for the real loop. Projectivy **IMAGE** is the JPEG; **VIDEO** is only advertised when the sibling MP4 exists (`videoUrl` stays null otherwise).

## Editor preview size

The 16:9 stage is **contained** in its panel (`object-fit: contain` behavior):

- `.stage-frame` is `width: 100%`, centered, `overflow: hidden` so the stage cannot cause horizontal scroll.
- The 16:9 box is `width: min(100%, calc(var(--stage-max-height) * 16 / 9))` with `--stage-max-height: min(68dvh, calc(100dvh - chrome))` (tighter on small screens).
- Artwork inside the stage uses `object-fit: cover`; the **stage** letterboxes in the panel, not the wallpaper inside the stage.

Frontend tests in `web/src/lib/stage.test.ts` lock this contract (no parent overflow, 16:9 aspect, CSS contain rules).

## Bake pipeline

```
render_plate (RGB art, no vignette)  ─┐
                                      ├─ subpixel Ken Burns (bicubic EXTENT @2× working plate)
optional light-leak (padded, under)  ─┤     + locked chrome composite per frame
render_chrome (RGBA logo/text/pills   ─┘     → raw RGB → x264 CFR Main L4.0  ─► title.mp4
              + locked vignette / letterbox / edge fades)
render_still  ─► title.jpg     (always; chrome baked static)
```

Requires `ffmpeg` in the image (`libx264`). If ffmpeg is missing, generation still succeeds with the JPEG.

The Ken Burns path matches the editor CSS loop: zoom **in** only (never below the cover crop), ping-pong ease (`sin(πt)²`, not a bipolar `sin(2πt)` zoom-out), zoom/pan amplitude from the same `--motion-zoom-*` / `--motion-x` numbers as `web/src/lib/motion.ts`, default **24 fps**. Frames are resampled with **subpixel bicubic** windows (CSS-like), then encoded **CFR** with **B-frames off** and **scenecut off** so a TV loop does not hitch at a mid-pan keyframe or at the join. Quality presets pick an x264 speed (`fast` / `medium` / `slow`) and a target bitrate (2.8 / 4 / 5.5 Mbps) with 2× VBV maxrate headroom, always **H.264 Main 4.0 yuv420p +faststart** for Projectivy / Android TV. Duration defaults to **15s** (`motion_duration`) so the loop is not shorter than the CSS preview.

**Do not** Ken-Burns the composited JPEG. A later “Bake motion” pass re-fetches the original backdrop (demo still or Jellyfin Backdrop/Primary) as the plate. Additive bake fields: `layered`, `chrome_locked`.

## Plugin / TV notes

- Set Projectivy’s wallpaper interval; the plugin answers `TimeElapsed` and optional idle-exit refresh.
- `PUBLIC_BASE_URL` must be a LAN URL the TV can reach. The plugin rewrites `127.0.0.1` / `localhost` image URLs to the configured server.
- Video loops are 1080p H.264 Main @ L4.0, no audio, faststart — aimed at Android TV / Google TV.
