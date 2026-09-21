import { useEffect, useRef, type CSSProperties, type ReactNode, type Ref } from "react";
import { ChromePills } from "./ChromePills";

type WallpaperStageProps = {
  stageRef?: Ref<HTMLDivElement | null>;
  className?: string;
  wrapClassName?: string;
  artSrc?: string | null;
  artAlt?: string;
  videoSrc?: string | null;
  motionOn?: boolean;
  motionVars?: CSSProperties;
  lightLeak?: boolean;
  paused?: boolean;
  children?: ReactNode;
  ariaLabel?: string;
  onVideoError?: () => void;
  onArtError?: () => void;
};

/**
 * Layered 16:9 stage: background art may Ken-Burns; foreground children stay pinned.
 * The frame uses object-fit:contain sizing so the stage never blows out the panel.
 * Baked VIDEO is played as-is (chrome already in the file) — never Ken-Burned.
 */
export function WallpaperStage({
  stageRef,
  className,
  wrapClassName = "canvas-wrap",
  artSrc,
  artAlt = "",
  videoSrc,
  motionOn = false,
  motionVars,
  lightLeak = false,
  paused = false,
  children,
  ariaLabel,
  onVideoError,
  onArtError,
}: WallpaperStageProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const moving = Boolean(motionOn && !videoSrc && artSrc);
  useEffect(() => {
    const el = videoRef.current;
    if (!el) return;
    try {
    if (paused) {
      el.pause();
      return;
    }
    const play = el.play?.();
    if (play && typeof play.catch === "function") play.catch(() => undefined);
  } catch {
    /* jsdom / autoplay */
  }
  }, [paused, videoSrc]);
  const artStyle = moving
    ? ({ ...motionVars, animationPlayState: paused ? "paused" : "running" } as CSSProperties)
    : undefined;
  return (
    <div className={`stage-frame ${className || ""}`.trim()}>
      <div className={wrapClassName} ref={stageRef} aria-label={ariaLabel}>
        <div className="stage-bg">
          {videoSrc ? (
            <video
              ref={videoRef}
              className="canvas-art tv-art"
              src={videoSrc}
              autoPlay
              muted
              loop
              playsInline
              aria-label={artAlt || "Wallpaper video"}
              onError={() => onVideoError?.()}
            />
          ) : artSrc ? (
            <img
              className={`canvas-art tv-art ${moving ? "motion-art" : ""}`}
              style={artStyle}
              src={artSrc}
              alt={artAlt}
              onError={() => onArtError?.()}
            />
          ) : (
            <div className="tv-art tv-art-empty">Generate a batch to fill tonight</div>
          )}
          {moving && lightLeak && !paused ? <div className="motion-leak" /> : null}
        </div>
        <div className="stage-fg">{children}</div>
      </div>
    </div>
  );
}

export function SampleLockedChrome({
  title = "Northlight",
  watchState = "unwatched",
  libraryState,
  availability,
  source,
  titlePct,
  badgePct,
}: {
  title?: string;
  watchState?: string;
  libraryState?: string;
  availability?: string;
  source?: string;
  /** Position the title/badges to match a real layout instead of the
   * generic Netflix-Hero-shaped default (percent of canvas width/height). */
  titlePct?: { x: number; y: number };
  badgePct?: { x: number; y: number };
}) {
  return (
    <div className="sample-chrome" aria-hidden="true">
      <ChromePills
        className="chrome-pills-sample"
        watchState={watchState}
        libraryState={libraryState}
        availability={availability}
        source={source}
        style={badgePct ? { left: `${badgePct.x}%`, top: `${badgePct.y}%` } : undefined}
      />
      <strong className="sample-title" style={titlePct ? { left: `${titlePct.x}%`, top: `${titlePct.y}%` } : undefined}>
        {title}
      </strong>
    </div>
  );
}
