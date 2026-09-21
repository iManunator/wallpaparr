import { useEffect, useMemo, useRef, useState, type CSSProperties, type MouseEvent as ReactMouseEvent } from "react";
import { FullscreenViewer, wallpaperSlide } from "./FullscreenViewer";
import { api } from "./lib/api";
import { applyLook, LOOK_PRESETS, stageOverlayStyle } from "./lib/gradient";
import {
  duplicateLayout,
  normalizeLayout,
  removeLayer,
  reorderLayer,
  selectionAfterRemove,
  SLOTS,
  validateLayout,
  type AppSettings,
  type Layout,
  type WallpaperRecord,
} from "./lib/layout";
import { errorToast } from "./lib/messages";
import { clampIntensity, defaultDuration, describeMotion, intensityFromPreset, MOTION_PRESET_ORDER, motionPreviewVars, motionSeedKey, type MotionStyle } from "./lib/motion";
import { prefersLogo, smartResizeLogo, clampLogoRect, tagShift } from "./lib/logo";
import { keepWatchSlot } from "./lib/chrome";
import { LAYOUT_DNA } from "./lib/queues";
import { seerrBadge } from "./lib/seerr";
import { watchBadge } from "./lib/watch";
import { WatchBadge } from "./WatchBadge";
import { SeerrBadge } from "./SeerrBadge";
import { ChromePills } from "./ChromePills";
import { WallpaperStage } from "./WallpaperStage";
import { useJobs } from "./JobProgress";
import { useToasts } from "./toasts";

type MediaRow = {
  title?: string;
  year?: number | null;
  overview?: string;
  rating?: number;
  genres?: string[];
  official_rating?: string;
  runtime?: string;
  watch_state?: string;
  library_state?: string;
  availability?: string;
  source?: string;
  jellyfin_id?: string | null;
  tmdb_id?: string | null;
  backdrop_url?: string | null;
  poster_url?: string | null;
  logo_url?: string | null;
  media_type?: string | null;
};

const SAMPLE: Record<string, string> = {
  title: "Northlight",
  year: "2024",
  genres: "Sci-Fi  ·  Mystery",
  runtime: "2h 11m",
  rating: "★ 8.4",
  overview: "A cartographer maps a city that rearranges itself after dusk.",
  watch_status: "Unwatched",
  source: "Jellyfin",
  age: "PG-13",
  media_type: "Movie",
};

function sampleFromMedia(item: MediaRow): Record<string, string> {
  const genres = (item.genres || []).slice(0, 3).join("  ·  ");
  const watch = watchBadge(item.watch_state);
  const seerr = seerrBadge(item.library_state, item.availability, item.source);
  const source = item.source || "demo";
  return {
    title: item.title || "Untitled",
    year: item.year ? String(item.year) : "",
    genres,
    runtime: item.runtime || "",
    rating: item.rating ? `★ ${Number(item.rating).toFixed(1)}` : "",
    overview: item.overview || "",
    watch_status: watch?.label || "",
    seerr_status: seerr?.label || "",
    source: source.charAt(0).toUpperCase() + source.slice(1),
    age: item.official_rating || "",
    media_type: (item.media_type || "movie").toLowerCase() === "tv" ? "Series" : "Movie",
  };
}

function mediaKey(item: MediaRow): string {
  return String(item.jellyfin_id || item.tmdb_id || item.title || "");
}

export function EditorPage({ initialLayout }: { initialLayout?: string } = {}) {
  const notify = useToasts();
  const { run, busy } = useJobs();
  const stageRef = useRef<HTMLDivElement | null>(null);
  const [names, setNames] = useState<string[]>([]);
  const [layout, setLayout] = useState<Layout>(normalizeLayout(null));
  const [selected, setSelected] = useState(0);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [previewSource, setPreviewSource] = useState<"demo" | "jellyfin">("demo");
  const [catalog, setCatalog] = useState<MediaRow[]>([]);
  const [created, setCreated] = useState<WallpaperRecord[]>([]);
  const [previewId, setPreviewId] = useState("");
  const [viewer, setViewer] = useState<number | null>(null);
  const [motionOn, setMotionOn] = useState(true);
  const [motionStyle, setMotionStyle] = useState<MotionStyle>("parallax");
  const [motionPreset, setMotionPreset] = useState("balanced");
  const [lightLeak, setLightLeak] = useState(true);
  const [motionVary, setMotionVary] = useState(true);
  const [duration, setDuration] = useState(6);
  const [logoSrc, setLogoSrc] = useState("");
  const [logoNatural, setLogoNatural] = useState<{ w: number; h: number } | null>(null);
  const [baseSettings, setBaseSettings] = useState<AppSettings | null>(null);

  useEffect(() => {
    api.layouts().then(async (list) => {
      setNames(list);
      const preferred =
        initialLayout && list.includes(initialLayout)
          ? initialLayout
          : list.includes("Netflix Hero")
            ? "Netflix Hero"
            : list[0];
      if (preferred) setLayout(normalizeLayout(await api.layout(preferred)));
    });
    api
      .settings()
      .then((settings) => {
        setBaseSettings(settings);
        setMotionStyle((settings.motion_style || "parallax") as MotionStyle);
        setMotionPreset(settings.motion_preset || "balanced");
        setLightLeak(Boolean(settings.light_leak));
        setMotionVary(settings.motion_vary !== false);
        setDuration(Number(settings.motion_duration || defaultDuration(settings.motion_quality || "light")));
        setMotionOn(settings.motion_wallpapers !== false);
      })
      .catch(() => undefined);
  }, [initialLayout]);

  useEffect(() => {
    api
      .media(previewSource, 16)
      .then((rows) => {
        const usable = (rows as MediaRow[]).filter((row) => mediaKey(row));
        setCatalog(usable);
        if (usable[0]) setPreviewId(mediaKey(usable[0]));
      })
      .catch(() => setCatalog([]));
  }, [previewSource]);

  useEffect(() => {
    api.gallery(layout.name).then(setCreated).catch(() => setCreated([]));
  }, [layout.name]);

  const errors = useMemo(() => validateLayout(layout), [layout]);
  const showWatch = layout.show_watch_badge !== false;
  const showSeerr = layout.show_seerr_badge !== false;
  const hasWatchLayer = layout.layers.some(
    (row) => row.visible && (row.slot === "watch_status" || row.slot === "watch_state"),
  );
  const hasSeerrLayer = layout.layers.some(
    (row) => row.visible && (row.slot === "seerr_status" || row.slot === "seerr_state"),
  );

  async function deleteCreated(item: WallpaperRecord) {
    if (!window.confirm(`Delete “${item.title}”? This cannot be undone.`)) return;
    try {
      const out = await api.deleteGallery(item.id);
      notify("ok", out.message || `Deleted “${item.title}”.`);
      const next = await api.gallery(layout.name);
      setCreated(next);
      if (viewer !== null) setViewer(next.length ? Math.min(viewer, next.length - 1) : null);
    } catch (err) {
      const toast = errorToast(err, "Could not delete");
      notify(toast.kind, toast.text);
    }
  }
  const layer = layout.layers[selected];
  const preview = catalog.find((row) => mediaKey(row) === previewId) || catalog[0];
  const sample = preview ? sampleFromMedia(preview) : SAMPLE;
  const artId = preview ? mediaKey(preview) : "demo-jf-1";
  const artSrc = api.mediaArtwork(artId);
  const createdSlides = created.map(wallpaperSlide);
  const intensity = intensityFromPreset(motionPreset) || clampIntensity(0.55);
  const previewDuration = duration || defaultDuration();
  const motionVars = motionPreviewVars(motionStyle, intensity, previewDuration, {
    vary: motionVary,
    seed: motionSeedKey(preview?.jellyfin_id, preview?.tmdb_id, artId, preview?.title),
    preset: motionPreset,
  });
  const showLogo = prefersLogo(layout.title_display) && Boolean(logoSrc);
  const titleLayer = layout.layers.find((row) => row.slot === "title");
  const logoBox = (() => {
    if (!showLogo || !logoNatural || !titleLayer) return null;
    const maxW = Math.min(layout.logo_max_width || 1200, titleLayer.width || 860, layout.canvas_width - 144);
    const maxH = Math.min(layout.logo_max_height || 450, titleLayer.height || 450, layout.canvas_height - 316);
    const sized = smartResizeLogo(logoNatural.w, logoNatural.h, maxW, maxH);
    return clampLogoRect(titleLayer.x, titleLayer.y, sized.width, sized.height, layout.canvas_width, layout.canvas_height);
  })();
  const metaYs = layout.layers.filter((row) => row.slot !== "title").map((row) => row.y);
  const logoShift =
    logoBox && titleLayer && metaYs.length
      ? tagShift(logoBox.y, logoBox.height, Math.min(...metaYs), layout.logo_padding || 25)
      : 0;

  useEffect(() => {
    if (!prefersLogo(layout.title_display) || !artId) {
      setLogoSrc("");
      setLogoNatural(null);
      return;
    }
    const url = api.mediaLogo(artId, preview?.tmdb_id, preview?.media_type || "movie");
    let cancelled = false;
    const probe = new window.Image();
    probe.onload = () => {
      if (cancelled) return;
      setLogoSrc(url);
      setLogoNatural({ w: probe.naturalWidth, h: probe.naturalHeight });
    };
    probe.onerror = () => {
      if (cancelled) return;
      setLogoSrc("");
      setLogoNatural(null);
      if (layout.title_display === "logo") {
        notify("info", "No logo for this title — showing the name.");
      }
    };
    probe.src = url;
    return () => {
      cancelled = true;
    };
  }, [artId, layout.title_display, notify, preview?.media_type, preview?.tmdb_id]);

  async function load(name: string) {
    setLayout(normalizeLayout(await api.layout(name)));
    setSelected(0);
  }

  async function resetToDefault() {
    if (!layout.preset) return;
    if (!window.confirm(`Reset "${layout.name}" to its default layout? This discards any saved customizations.`)) return;
    try {
      await api.resetLayout(layout.name);
      await load(layout.name);
      notify("ok", `Reset “${layout.name}” to default.`);
    } catch (err) {
      const toast = errorToast(err, "Could not reset layout");
      notify(toast.kind, toast.text);
    }
  }

  async function deleteLayout() {
    if (layout.preset) return;
    if (!window.confirm(`Delete "${layout.name}"? This cannot be undone.`)) return;
    try {
      await api.deleteLayout(layout.name);
      const remaining = await api.layouts();
      setNames(remaining);
      await load(remaining[0]);
      notify("ok", `Deleted “${layout.name}”.`);
    } catch (err) {
      const toast = errorToast(err, "Could not delete layout");
      notify(toast.kind, toast.text);
    }
  }

  function moveLayer(index: number, delta: number) {
    const layers = reorderLayer(layout.layers, index, delta);
    if (layers === layout.layers) return;
    setLayout({ ...layout, layers });
    setSelected(index + delta);
  }

  function deleteLayer(index: number) {
    const target = layout.layers[index];
    if (!target) return;
    if (!window.confirm(`Delete layer “${target.id}” (${target.slot})?`)) return;
    const layers = removeLayer(layout.layers, index);
    setLayout({ ...layout, layers });
    setSelected((prev) => selectionAfterRemove(prev, index, layers.length));
  }

  async function save() {
    setError("");
    if (errors.length) {
      setError(errors.join(" · "));
      notify("error", errors[0]);
      return;
    }
    try {
      await api.saveLayout(layout);
      setNames(await api.layouts());
      const mergedSettings: AppSettings = {
        ...(baseSettings || ((await api.settings()) as AppSettings)),
        motion_style: motionStyle,
        motion_preset: motionPreset,
        light_leak: lightLeak,
        motion_vary: motionVary,
        motion_duration: duration,
      };
      await api.saveSettings(mergedSettings);
      setBaseSettings(mergedSettings);
      const text = `Saved “${layout.name}”`;
      setStatus(text);
      notify("ok", text);
    } catch (err) {
      const toast = errorToast(err, "Could not save layout");
      setError(toast.text);
      notify(toast.kind, toast.text);
    }
  }

  function patchBackground(patch: Partial<Layout["background"]>) {
    setLayout({ ...layout, background: { ...layout.background, ...patch } });
  }

  function startDrag(event: ReactMouseEvent<HTMLDivElement>, index: number) {
    event.preventDefault();
    event.stopPropagation();
    setSelected(index);
    const stage = stageRef.current;
    if (!stage) return;
    const rect = stage.getBoundingClientRect();
    const current = layout.layers[index];
    const originX = event.clientX;
    const originY = event.clientY;
    function onMove(moveEvent: MouseEvent) {
      const dx = ((moveEvent.clientX - originX) / rect.width) * layout.canvas_width;
      const dy = ((moveEvent.clientY - originY) / rect.height) * layout.canvas_height;
      const next = {
        ...current,
        x: Math.max(0, Math.round(current.x + dx)),
        y: Math.max(0, Math.round(current.y + dy)),
      };
      setLayout((prev) => ({
        ...prev,
        layers: prev.layers.map((row, i) => (i === index ? next : row)),
      }));
    }
    function onUp() {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    }
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
  }

  return (
    <section>
      <h1>Layout editor</h1>
      <p className="lede">
        Flagship 16:9 stage for Projectivy: the preview always fits this panel. Artwork pans/zooms; logo, title, watch
        badges, and Seerr chips stay locked. Drag metadata chips. Save persists the layout JSON.
      </p>
      <div className="grid two">
        <div className="card">
          <div className="row" style={{ marginBottom: 12 }}>
            <select value={layout.name} onChange={(e) => load(e.target.value)} aria-label="Layout">
              {names.map((name) => (
                <option key={name}>{name}</option>
              ))}
            </select>
            <button className="btn ghost tiny" onClick={() => setLayout(duplicateLayout(layout, `${layout.name} copy`))}>
              Duplicate
            </button>
            <button className="btn tiny" onClick={save}>
              Save layout
            </button>
            {layout.preset && (
              <button
                className="btn ghost tiny"
                title="Discard saved customizations and restore this preset's original layout"
                onClick={resetToDefault}
              >
                Reset to default
              </button>
            )}
            {!layout.preset && (
              <button
                className="btn ghost tiny"
                title="Delete this saved layout"
                onClick={deleteLayout}
              >
                Delete layout
              </button>
            )}
            <button
              className="btn ghost tiny"
              disabled={busy || created.length === 0}
              onClick={async () => {
                try {
                  const out = await run({ kind: "motion", layout: layout.name });
                  setStatus(out.message || "Baked motion.");
                  setCreated(await api.gallery(layout.name));
                } catch (err) {
                  setStatus(errorToast(err, "Motion bake failed").text);
                }
              }}
            >
              Bake motion for this layout
            </button>
          </div>
          <div className="chip-row">
            {LAYOUT_DNA.map((preset) => (
              <button
                key={preset.name}
                type="button"
                className={`chip ${layout.name === preset.name ? "active" : ""}`}
                title={preset.blurb}
                onClick={() => load(preset.name)}
              >
                {preset.name}
              </button>
            ))}
          </div>
          <div className="row" style={{ marginBottom: 12 }}>
            <label className="inline">
              Preview source
              <select
                value={previewSource}
                aria-label="Preview source"
                onChange={(e) => setPreviewSource(e.target.value as "demo" | "jellyfin")}
              >
                <option value="demo">Demo catalog</option>
                <option value="jellyfin">Jellyfin</option>
              </select>
            </label>
            <label className="inline">
              Title display
              <select
                value={layout.title_display || "auto"}
                aria-label="Title display"
                onChange={(e) =>
                  setLayout({ ...layout, title_display: e.target.value as "auto" | "logo" | "text" })
                }
              >
                <option value="auto">Auto</option>
                <option value="logo">Logo</option>
                <option value="text">Title text</option>
              </select>
            </label>
          </div>
          {catalog.length > 0 && (
            <>
              <label>{previewSource === "jellyfin" ? "Jellyfin preview" : "Demo preview"}</label>
              <select
                value={previewId}
                onChange={(e) => setPreviewId(e.target.value)}
                aria-label={previewSource === "jellyfin" ? "Jellyfin preview" : "Demo preview"}
              >
                {catalog.map((item) => (
                  <option key={mediaKey(item)} value={mediaKey(item)}>
                    {item.title}
                    {item.year ? ` (${item.year})` : ""}
                  </option>
                ))}
              </select>
            </>
          )}
          {previewSource === "jellyfin" && catalog.length === 0 && (
            <p className="muted">No Jellyfin artwork yet — connect Jellyfin in Settings, or preview the demo catalog.</p>
          )}
          <label>Layout name</label>
          <input value={layout.name} onChange={(e) => setLayout({ ...layout, name: e.target.value })} />
          <div className="editor-toolbar">
            <div className="toolbar-group">
              <span className="toolbar-group-label">Motion</span>
              <button type="button" className={`chip ${motionOn ? "active" : ""}`} onClick={() => setMotionOn((v) => !v)}>
                {motionOn ? "Motion on" : "Motion off"}
              </button>
              {MOTION_PRESET_ORDER.map((preset) => (
                <button
                  key={preset}
                  type="button"
                  className={`chip ${motionPreset === preset ? "active" : ""}`}
                  onClick={() => setMotionPreset(preset)}
                >
                  {preset[0].toUpperCase() + preset.slice(1)}
                </button>
              ))}
            </div>
            <div className="toolbar-group">
              <span className="toolbar-group-label">Badges</span>
              <button
                type="button"
                className={`chip ${layout.show_watch_badge !== false ? "active" : ""}`}
                onClick={() => setLayout({ ...layout, show_watch_badge: layout.show_watch_badge === false })}
              >
                Watch badge
              </button>
              <button
                type="button"
                className={`chip ${layout.show_seerr_badge !== false ? "active" : ""}`}
                onClick={() => setLayout({ ...layout, show_seerr_badge: layout.show_seerr_badge === false })}
              >
                Seerr badge
              </button>
            </div>
          </div>
          <div style={{ marginTop: 14 }}>
            <WallpaperStage
              stageRef={stageRef}
              className="editor-stage"
              artSrc={artSrc}
              artAlt={`${preview?.title || "Library"} artwork`}
              motionOn={motionOn}
              motionVars={motionVars as CSSProperties}
              lightLeak={lightLeak}
            >
              <div className={`canvas-stage ${artSrc ? "has-art" : ""}`} style={stageOverlayStyle(layout.background)}>
                {layout.layers
                  .map((item, index) => ({ item, index }))
                  .filter(({ item }) => {
                    if (!item.visible) return false;
                    const watchSlot = item.slot === "watch_status" || item.slot === "watch_state";
                    const seerrSlot = item.slot === "seerr_status" || item.slot === "seerr_state";
                    if (watchSlot && !keepWatchSlot(showWatch, showSeerr, hasSeerrLayer)) return false;
                    if (seerrSlot && !showSeerr) return false;
                    return true;
                  })
                  .map(({ item, index }) => {
                    const isLogoTitle = Boolean(item.slot === "title" && showLogo && logoBox);
                    const isWatch = item.slot === "watch_status" || item.slot === "watch_state";
                    const isSeerr = item.slot === "seerr_status" || item.slot === "seerr_state";
                    const y = isLogoTitle && logoBox ? logoBox.y : item.y + (item.slot === "title" ? 0 : logoShift);
                    const x = isLogoTitle && logoBox ? logoBox.x : item.x;
                    return (
                      <div
                        key={item.id}
                        className={`layer-chip ${index === selected ? "selected" : ""} ${isLogoTitle ? "is-logo" : ""} ${isWatch ? "is-watch" : ""} ${isSeerr ? "is-seerr" : ""}`}
                        onMouseDown={(event) => startDrag(event, index)}
                        style={{
                          left: `${(x / layout.canvas_width) * 100}%`,
                          top: `${(y / layout.canvas_height) * 100}%`,
                          // cqw (not a fixed multiplier) so text scales with the
                          // box's actual rendered size, same as the x/y/width
                          // percentages below — the stage isn't a fixed pixel size.
                          fontSize: `max(10px, ${(item.font_size / layout.canvas_width) * 100}cqw)`,
                          fontWeight: item.font_weight === "bold" ? 700 : 500,
                          color: item.color,
                          width: isLogoTitle && logoBox ? `${(logoBox.width / layout.canvas_width) * 100}%` : undefined,
                          maxWidth: item.width ? `${(item.width / layout.canvas_width) * 100}%` : undefined,
                          maxHeight: item.height ? `${(item.height / layout.canvas_height) * 100}%` : undefined,
                          overflow: item.slot === "overview" || item.width ? "hidden" : undefined,
                          whiteSpace: item.slot === "overview" ? "normal" : "nowrap",
                          textOverflow: item.slot === "overview" ? undefined : "ellipsis",
                        }}
                      >
                        {isLogoTitle ? (
                          <img className="stage-logo" src={logoSrc} alt={`${sample.title || "Title"} logo`} />
                        ) : isWatch ? (
                          <>
                            {showWatch ? <WatchBadge state={preview?.watch_state || sample.watch_status} /> : null}
                            {showSeerr && !hasSeerrLayer ? (
                              <SeerrBadge
                                libraryState={preview?.library_state}
                                availability={preview?.availability}
                                source={preview?.source}
                              />
                            ) : null}
                          </>
                        ) : isSeerr ? (
                          <SeerrBadge
                            libraryState={preview?.library_state}
                            availability={preview?.availability}
                            source={preview?.source}
                          />
                        ) : (
                          sample[item.slot] || item.slot
                        )}
                      </div>
                    );
                  })}
              </div>
              {(showWatch && !hasWatchLayer) || (showSeerr && !hasSeerrLayer && !hasWatchLayer) ? (
                <ChromePills
                  className="chrome-pills-fallback"
                  watchState={preview?.watch_state || sample.watch_status}
                  libraryState={preview?.library_state}
                  availability={preview?.availability}
                  source={preview?.source}
                  showWatch={showWatch && !hasWatchLayer}
                  showSeerr={showSeerr && !hasSeerrLayer && !hasWatchLayer}
                />
              ) : null}
            </WallpaperStage>
          </div>
          <p className="muted">
            {describeMotion(motionStyle, intensity, previewDuration)}
            {lightLeak ? " · light leak" : ""}. Intensity {motionPreset} moves the <strong>background</strong> only —
            logo, title, and badges stay pinned. Bake VIDEO for this layout so Projectivy can play a real MP4 (
            <code>videoUrl</code> is set only when the file exists).
          </p>
          {created.length > 0 && (
            <div className="created-strip">
              <div className="row" style={{ justifyContent: "space-between" }}>
                <strong>Generated for this layout</strong>
                <span className="muted">{created.length} stills · click for full screen</span>
              </div>
              <div className="created-row">
                {created.map((item, index) => (
                  <button
                    type="button"
                    key={item.id}
                    className="created-thumb"
                    onClick={() => setViewer(index)}
                    aria-label={`View ${item.title} full screen`}
                  >
                    <img src={api.wallpaperImage(item.layout, item.filename)} alt={item.title} />
                    <ChromePills
                      watchState={item.watch_state}
                      libraryState={item.library_state}
                      availability={item.availability}
                      source={item.source}
                    />
                  </button>
                ))}
              </div>
            </div>
          )}
          {status && <p className="status">{status}</p>}
          {error && <p className="error">{error}</p>}
        </div>
        <div className="card">
          <h3>Look</h3>
          <div className="chip-row">
            {LOOK_PRESETS.map((preset) => (
              <button
                key={preset.id}
                type="button"
                className="chip"
                title={preset.blurb}
                onClick={() => setLayout(applyLook(layout, preset))}
              >
                {preset.label}
              </button>
            ))}
          </div>
          <label>Gradient type</label>
          <select
            value={layout.background.gradient_type || "linear"}
            onChange={(e) => patchBackground({ gradient_type: e.target.value })}
            aria-label="Gradient type"
          >
            <option value="linear">Linear</option>
            <option value="radial">Radial</option>
          </select>
          {layout.background.gradient_type !== "radial" && (
            <>
              <label>Angle ({Math.round(layout.background.gradient_angle || 0)}°)</label>
              <input
                type="range"
                min={0}
                max={360}
                value={layout.background.gradient_angle || 0}
                onChange={(e) => patchBackground({ gradient_angle: Number(e.target.value) })}
                aria-label="Gradient angle"
              />
            </>
          )}
          <label>Gradient opacity</label>
          <input
            type="range"
            min={0}
            max={1}
            step={0.01}
            value={layout.background.gradient_opacity || 0}
            onChange={(e) => patchBackground({ gradient_opacity: Number(e.target.value) })}
            aria-label="Gradient opacity"
          />
          <div className="row" style={{ justifyContent: "space-between", marginTop: 8 }}>
            <strong>Stops</strong>
            <button
              type="button"
              className="btn ghost tiny"
              onClick={() =>
                patchBackground({
                  gradient_stops: [
                    ...(layout.background.gradient_stops || []),
                    { color: layout.background.color, position: 0.5, opacity: 0.4 },
                  ],
                })
              }
            >
              Add stop
            </button>
          </div>
          {(layout.background.gradient_stops || []).map((stop, index) => (
            <div className="stop-row" key={`${stop.position}-${index}`}>
              <input
                type="color"
                value={stop.color.length === 7 ? stop.color : "#000000"}
                onChange={(e) => {
                  const stops = (layout.background.gradient_stops || []).slice();
                  stops[index] = { ...stop, color: e.target.value };
                  patchBackground({ gradient_stops: stops });
                }}
                aria-label={`Stop ${index + 1} color`}
              />
              <input
                type="range"
                min={0}
                max={1}
                step={0.01}
                value={stop.position}
                onChange={(e) => {
                  const stops = (layout.background.gradient_stops || []).slice();
                  stops[index] = { ...stop, position: Number(e.target.value) };
                  patchBackground({ gradient_stops: stops });
                }}
                aria-label={`Stop ${index + 1} position`}
              />
              <input
                type="range"
                min={0}
                max={1}
                step={0.01}
                value={stop.opacity}
                onChange={(e) => {
                  const stops = (layout.background.gradient_stops || []).slice();
                  stops[index] = { ...stop, opacity: Number(e.target.value) };
                  patchBackground({ gradient_stops: stops });
                }}
                aria-label={`Stop ${index + 1} opacity`}
              />
              <button
                type="button"
                className="btn ghost tiny"
                onClick={() =>
                  patchBackground({
                    gradient_stops: (layout.background.gradient_stops || []).filter((_, i) => i !== index),
                  })
                }
              >
                ×
              </button>
            </div>
          ))}
          <label>Vignette</label>
          <input
            type="range"
            min={0}
            max={1}
            step={0.01}
            value={layout.background.vignette || 0}
            onChange={(e) => patchBackground({ vignette: Number(e.target.value) })}
            aria-label="Vignette"
          />
          <label>Overlay opacity</label>
          <div className="row">
            <input
              type="color"
              value={layout.background.overlay_color || "#000000"}
              onChange={(e) => patchBackground({ overlay_color: e.target.value })}
              aria-label="Overlay color"
            />
            <input
              type="range"
              min={0}
              max={1}
              step={0.01}
              value={layout.background.overlay_opacity || 0}
              onChange={(e) => patchBackground({ overlay_opacity: Number(e.target.value) })}
              aria-label="Overlay opacity"
            />
          </div>
          <label>Edge fades (left / right / top / bottom)</label>
          <div className="fade-grid">
            {(["fade_left", "fade_right", "fade_top", "fade_bottom"] as const).map((key) => (
              <input
                key={key}
                type="range"
                min={0}
                max={0.8}
                step={0.01}
                value={layout.background[key]}
                onChange={(e) => patchBackground({ [key]: Number(e.target.value) })}
                aria-label={key.replace("fade_", "Fade ")}
              />
            ))}
          </div>
          <label>Softness / brightness / wash</label>
          <div className="row">
            <input
              type="range"
              min={0.05}
              max={1}
              step={0.01}
              value={layout.background.fade_softness}
              onChange={(e) => patchBackground({ fade_softness: Number(e.target.value) })}
              aria-label="Fade softness"
            />
            <input
              type="range"
              min={0.4}
              max={1.4}
              step={0.01}
              value={layout.background.brightness}
              onChange={(e) => patchBackground({ brightness: Number(e.target.value) })}
              aria-label="Brightness"
            />
            <input
              type="color"
              value={layout.background.color || "#050505"}
              onChange={(e) => patchBackground({ color: e.target.value })}
              aria-label="Wash color"
            />
          </div>
          <div className="row" style={{ justifyContent: "space-between", marginTop: 18 }}>
            <strong>Layers</strong>
            <button
              className="btn ghost tiny"
              onClick={() =>
                setLayout({
                  ...layout,
                  layers: [
                    ...layout.layers,
                    {
                      id: `layer-${layout.layers.length + 1}`,
                      slot: "year",
                      x: 80,
                      y: 200,
                      font_size: 24,
                      color: "#ffffff",
                      font_weight: "regular",
                      visible: true,
                      align: "left",
                    },
                  ],
                })
              }
            >
              Add layer
            </button>
          </div>
          <div className="layer-list" style={{ marginTop: 10 }}>
            {layout.layers.map((item, index) => (
              <div key={item.id} className="row" style={{ gap: 4, marginBottom: 4 }}>
                <button
                  className={`layer-item ${index === selected ? "selected" : ""}`}
                  style={{ flex: 1 }}
                  onClick={() => setSelected(index)}
                >
                  {item.id} · {item.slot}
                </button>
                <button
                  className="btn ghost tiny"
                  title="Move up"
                  aria-label={`Move ${item.id} up`}
                  disabled={index === 0}
                  onClick={() => moveLayer(index, -1)}
                >
                  ↑
                </button>
                <button
                  className="btn ghost tiny"
                  title="Move down"
                  aria-label={`Move ${item.id} down`}
                  disabled={index === layout.layers.length - 1}
                  onClick={() => moveLayer(index, 1)}
                >
                  ↓
                </button>
                <button
                  className="btn ghost tiny"
                  title="Delete layer"
                  aria-label={`Delete ${item.id}`}
                  onClick={() => deleteLayer(index)}
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
          {layer && (
            <div className="grid" style={{ marginTop: 14 }}>
              <label>Slot</label>
              <select
                value={layer.slot}
                onChange={(e) => {
                  const layers = layout.layers.slice();
                  layers[selected] = { ...layer, slot: e.target.value };
                  setLayout({ ...layout, layers });
                }}
              >
                {SLOTS.map((slot) => (
                  <option key={slot}>{slot}</option>
                ))}
              </select>
              <div className="row">
                <div>
                  <label>X</label>
                  <input
                    type="number"
                    value={layer.x}
                    onChange={(e) => {
                      const layers = layout.layers.slice();
                      layers[selected] = { ...layer, x: Number(e.target.value) };
                      setLayout({ ...layout, layers });
                    }}
                  />
                </div>
                <div>
                  <label>Y</label>
                  <input
                    type="number"
                    value={layer.y}
                    onChange={(e) => {
                      const layers = layout.layers.slice();
                      layers[selected] = { ...layer, y: Number(e.target.value) };
                      setLayout({ ...layout, layers });
                    }}
                  />
                </div>
                <div>
                  <label>Size</label>
                  <input
                    type="number"
                    value={layer.font_size}
                    onChange={(e) => {
                      const layers = layout.layers.slice();
                      layers[selected] = { ...layer, font_size: Number(e.target.value) };
                      setLayout({ ...layout, layers });
                    }}
                  />
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
      {viewer !== null && (
        <FullscreenViewer
          items={createdSlides}
          index={viewer}
          onClose={() => setViewer(null)}
          onIndex={setViewer}
          onPin={async (slide) => {
            const item = created.find((row) => row.id === slide.id);
            if (!item) return;
            await api.flag(item.id, { pinned: !item.pinned });
            setCreated(await api.gallery(layout.name));
          }}
          onHide={async (slide) => {
            const item = created.find((row) => row.id === slide.id);
            if (!item) return;
            await api.flag(item.id, { hidden: !item.hidden });
            setCreated(await api.gallery(layout.name));
          }}
          onDelete={(slide) => {
            const item = created.find((row) => row.id === slide.id);
            if (item) void deleteCreated(item);
          }}
        />
      )}
    </section>
  );
}
