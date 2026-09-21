# Overlay widgets

Overlays are **off by default** (`overlays_enabled: false`). They are composited onto generated JPEGs and onto the parallax chrome layer so a clock card stays still while artwork drifts.

## Clock (shipped)

Settings → Overlay widgets → enable overlays + clock card. Renders local time; works in demo/offline mode. No network.

## Hooks (demo cards, not live integrations)

`settings.overlays` is a list of `{ kind, x, y, width, height, opacity, config }` objects. Kinds:

| kind | What ships today |
| --- | --- |
| `clock` | Local time card |
| `ha` / `ha_entity` | Draws a demo “HA · 72°” card (extension point for a future REST/WebSocket fetch) |
| `news` | Demo headline card |
| `json` | Demo text card |

Live Home Assistant / RSS fetches are **not** shipped: if we cannot test a network integration offline, we do not pretend it works. Point a future provider at these kinds, keep `overlays_enabled` as the feature flag, and add fixtures before enabling I/O.

Example `config.json` fragment:

```json
{
  "overlays_enabled": true,
  "overlay_clock": true,
  "overlays": [
    { "kind": "news", "x": 80, "y": 820, "width": 420, "height": 88, "config": { "headline": "Festival lights return" } }
  ]
}
```
