import { useEffect, useState, type CSSProperties } from "react";
import { api } from "./lib/api";
import { errorToast } from "./lib/messages";
import {
  clampIntensity,
  describeMotion,
  intensityFromPreset,
  MOTION_PRESET_ORDER,
  motionPreviewVars,
  PRESET_DURATION,
  type MotionStyle,
} from "./lib/motion";
import { QUEUE_LABELS, TASTE_PRESETS } from "./lib/queues";
import { watchBadge } from "./lib/watch";
import { ChromePills } from "./ChromePills";
import { WallpaperStage } from "./WallpaperStage";
import { useToasts } from "./toasts";

export type TonightPayload = {
  status: {
    imageUrl?: string | null;
    title?: string | null;
    mediaType?: string;
    videoUrl?: string | null;
    queue?: string | null;
    pinned?: boolean;
    layout?: string | null;
    path?: string | null;
    watchState?: string | null;
    libraryState?: string | null;
    availability?: string | null;
    seerrStatus?: string | null;
    source?: string | null;
  };
  queues: Array<{ id: string; label: string; count: number; titles: string[] }>;
  profile: string;
  motion: { style?: string; preset?: string; intensity?: number; light_leak?: boolean; vary?: boolean; seed?: string };
  preview?: { artworkUrl?: string | null; itemId?: string | null; layered?: boolean };
};

const PREVIEW_INTENSITY = MOTION_PRESET_ORDER;

function titleCase(value: string): string {
  return value ? value[0].toUpperCase() + value.slice(1) : value;
}

type TonightPageProps = {
  onEdit: (layout: string) => void;
  onGenerate?: () => void;
  onSettings?: () => void;
  onGallery?: () => void;
};

const FALLBACK_LAYOUT = "Netflix Hero";

export function TonightPage({ onEdit, onGenerate, onSettings, onGallery }: TonightPageProps) {
  const notify = useToasts();
  const [payload, setPayload] = useState<TonightPayload | null>(null);
  const [error, setError] = useState("");
  const [previewPreset, setPreviewPreset] = useState("");
  async function load() {
    try {
      // No layout filter — tonight's pick can come from any layout, so a
      // baked VIDEO under a different layout than the last one still shows up.
      const data = (await api.tonight()) as TonightPayload;
      setPayload(data);
      setError("");
    } catch (err) {
      const toast = errorToast(err, "Could not load tonight");
      setError(toast.text);
      notify(toast.kind, toast.text);
    }
  }
  useEffect(() => {
    void load();
  }, []);
  const image = payload?.status?.imageUrl;
  const video = payload?.status?.videoUrl;
  const artwork = payload?.preview?.artworkUrl;
  const queueId = payload?.status?.queue || "";
  const queueLabel = queueId ? QUEUE_LABELS[queueId] || queueId : "Tonight’s mix";
  const watch = watchBadge(payload?.status?.watchState);
  const queueDuplicatesWatch =
    (queueId === "unwatched" && watch?.id === "unwatched") ||
    (queueId === "continue_watching" && watch?.id === "partial");
  const showQueueBadge = Boolean(queueLabel) && !queueDuplicatesWatch;
  const motionStyle = (payload?.motion?.style || "parallax") as MotionStyle;
  const motionPreset = previewPreset || payload?.motion?.preset || "balanced";
  const intensity = intensityFromPreset(motionPreset) || clampIntensity(payload?.motion?.intensity ?? 0.55);
  const duration = PRESET_DURATION[motionPreset] || 12;
  const motionVars = motionPreviewVars(motionStyle, intensity, duration, {
    vary: payload?.motion?.vary !== false,
    seed: payload?.motion?.seed,
    preset: motionPreset,
  });
  const tonightPath = typeof payload?.status?.path === "string" ? payload.status.path : "";
  const layeredArt = Boolean(!video && artwork);
  const hasPick = Boolean(image || artwork || tonightPath);
  // Baked stills/VIDEO already paint title + status pills; only layer them for CSS artwork preview.
  const showTitleChrome = layeredArt || !hasPick;
  const title = payload?.status?.title || "";
  const pickedLayout = payload?.status?.layout || FALLBACK_LAYOUT;
  const profile = payload?.profile || "tonight";
  const mix = TASTE_PRESETS[profile] || TASTE_PRESETS.tonight;
  const chrome = {
    watchState: payload?.status?.watchState,
    libraryState: payload?.status?.libraryState,
    availability: payload?.status?.availability,
    source: payload?.status?.source,
  };

  const motionNote = video
    ? "Baked VIDEO is what Projectivy will play."
    : layeredArt
      ? `CSS preview only — ${describeMotion(motionStyle, intensity, duration)}. Bake to send an MP4 to the TV.`
      : "Still IMAGE. Bake motion if you want a VIDEO loop on the TV.";

  return (
    <section className="tonight-page">
      <header className="tonight-header">
        <h1>Tonight</h1>
        <p className="lede">The next wallpaper Projectivy will show, picked from taste:{profile}.</p>
      </header>

      <div className="tonight-hero">
        <WallpaperStage
          wrapClassName="tv-preview"
          ariaLabel="Projectivy home screen preview"
          artSrc={layeredArt ? artwork : image}
          artAlt={title || "Wallpaper"}
          videoSrc={video}
          motionOn={layeredArt}
          motionVars={motionVars as CSSProperties}
          lightLeak={Boolean(payload?.motion?.light_leak)}
        >
          {!video && (
            <div className="tv-chrome">
              <div className="tv-top">
                <span className="tv-logo">projectivy</span>
                <span className="tv-clock">9:41</span>
              </div>
              <div className="tv-hero-meta">
                {showQueueBadge && <span className="badge">{queueLabel}</span>}
                {showTitleChrome && <ChromePills {...chrome} />}
                {payload?.status?.pinned && <span className="badge">Pinned</span>}
                {payload?.status?.mediaType === "video" && <span className="badge badge-video">VIDEO</span>}
                {showTitleChrome && <h2>{title || "Waiting for a title"}</h2>}
                <p>Behind the guide · {pickedLayout}</p>
              </div>
              <div className="tv-rows">
                <div className="tv-row-label">Continue watching</div>
                <div className="tv-posters">
                  <span />
                  <span />
                  <span />
                  <span />
                  <span />
                </div>
              </div>
              <div className="tv-dock" />
            </div>
          )}
        </WallpaperStage>
        <div className="tonight-pick">
          <p className="tonight-kicker">Up next</p>
          <div className="tonight-pick-title">
            {!hasPick && <strong>No pick yet</strong>}
            {showQueueBadge && <span className="badge">{queueLabel}</span>}
            <ChromePills {...chrome} />
            {payload?.status?.mediaType === "video" && <span className="badge badge-video">VIDEO</span>}
          </div>
          <p className="muted">{motionNote}</p>
        </div>
      </div>

      {error && <p className="error">{error}</p>}

      {!hasPick && (
        <p className="tonight-empty muted">
          No wallpapers generated yet.
          {onGenerate && (
            <>
              {" "}
              <button type="button" className="btn tiny" onClick={onGenerate}>
                Open Generate
              </button>
            </>
          )}
        </p>
      )}

      <div className="tonight-actions" role="group" aria-label="Tonight actions">
        <button className="btn" type="button" onClick={() => onEdit(pickedLayout)}>
          Open in editor
        </button>
        {onSettings && (
          <button className="btn ghost" type="button" onClick={onSettings}>
            Edit tonight taste
          </button>
        )}
        {onGallery && (
          <button className="btn ghost" type="button" onClick={onGallery}>
            Open gallery
          </button>
        )}
      </div>

      {layeredArt && (
        <div className="tonight-secondary" role="group" aria-label="Preview intensity">
          <p className="tonight-label">Preview intensity</p>
          <div className="chip-row tonight-chips">
            {PREVIEW_INTENSITY.map((preset) => (
              <button
                key={preset}
                type="button"
                className={`chip ${motionPreset === preset ? "active" : ""}`}
                onClick={() => setPreviewPreset(preset)}
              >
                {titleCase(preset)}
              </button>
            ))}
          </div>
          <p className="muted">Changes this CSS preview only. Bake uses the motion preset in Settings.</p>
        </div>
      )}

      <aside className="tonight-mix" aria-label="Tonight’s mix">
        <p>
          <strong>taste:{profile}</strong>
          <span className="muted">
            {" "}
            ·{" "}
            {Object.entries(mix)
              .map(([id, weight]) => `${weight}% ${QUEUE_LABELS[id] || id}`)
              .join(" · ")}
          </span>
        </p>
        {(payload?.queues || []).length > 0 && (
          <div className="tonight-queues">
            {(payload?.queues || []).map((queue) => (
              <span className="chip quiet" key={queue.id} title={queue.titles.join(", ") || "Empty"}>
                {queue.label} <strong>{queue.count}</strong>
              </span>
            ))}
          </div>
        )}
      </aside>
    </section>
  );
}
