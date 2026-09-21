import { useEffect, useState } from "react";
import { ChromePills } from "./ChromePills";
import { WallpaperStage } from "./WallpaperStage";
import { api } from "./lib/api";
import { galleryPreviewSources } from "./lib/gallery";
import type { WallpaperRecord } from "./lib/layout";
import { useToasts } from "./toasts";

export type ViewerItem = {
  src: string;
  title: string;
  subtitle?: string;
  watchState?: string;
  libraryState?: string;
  availability?: string;
  source?: string;
  id?: string;
  pinned?: boolean;
  hidden?: boolean;
  videoSrc?: string | null;
  stillSrc?: string;
  jellyfin_id?: string | null;
  tmdb_id?: string | null;
  imdb_id?: string | null;
  filename?: string;
  hasVideo?: boolean;
  layout?: string;
};

export function wallpaperSlide(item: WallpaperRecord): ViewerItem {
  const preview = galleryPreviewSources(item, api);
  return {
    src: preview.stillSrc,
    stillSrc: preview.stillSrc,
    title: item.title,
    subtitle: [item.year, item.layout].filter(Boolean).join(" · "),
    watchState: item.watch_state,
    libraryState: item.library_state,
    availability: item.availability,
    source: item.source,
    id: item.id,
    pinned: item.pinned,
    hidden: item.hidden,
    jellyfin_id: item.jellyfin_id,
    tmdb_id: item.tmdb_id,
    imdb_id: item.imdb_id,
    filename: item.filename,
    videoSrc: preview.videoSrc,
    hasVideo: Boolean(item.has_video && preview.videoSrc),
    layout: item.layout,
  };
}

export function FullscreenViewer({
  items,
  index,
  onClose,
  onIndex,
  onPin,
  onHide,
  onDelete,
}: {
  items: ViewerItem[];
  index: number;
  onClose: () => void;
  onIndex: (next: number) => void;
  onPin?: (item: ViewerItem) => void;
  onHide?: (item: ViewerItem) => void;
  onDelete?: (item: ViewerItem) => void;
}) {
  const notify = useToasts();
  const item = items[index];
  const [paused, setPaused] = useState(false);
  const [videoFailed, setVideoFailed] = useState(false);

  useEffect(() => {
    setPaused(false);
    setVideoFailed(false);
  }, [item?.id, item?.videoSrc, item?.src]);

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
      if (!items.length) return;
      if (event.key === "ArrowRight") onIndex((index + 1) % items.length);
      if (event.key === "ArrowLeft") onIndex((index - 1 + items.length) % items.length);
      if (event.key === " " || event.key === "k") {
        event.preventDefault();
        setPaused((current) => !current);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [index, items, onClose, onIndex]);

  if (!item) return null;

  const stillSrc = item.stillSrc || item.src;
  const useVideo = Boolean(item.videoSrc && !videoFailed);
  const modeLabel = useVideo ? "VIDEO" : "IMAGE";

  return (
    <div className="lightbox" role="dialog" aria-modal="true" aria-label={`${item.title} full screen`} onClick={onClose}>
      <button type="button" className="lightbox-close btn ghost tiny" onClick={onClose} aria-label="Close full screen">
        Close
      </button>
      {items.length > 1 && (
        <>
          <button
            type="button"
            className="lightbox-nav prev btn ghost"
            aria-label="Previous wallpaper"
            onClick={(event) => {
              event.stopPropagation();
              onIndex((index - 1 + items.length) % items.length);
            }}
          >
            ‹
          </button>
          <button
            type="button"
            className="lightbox-nav next btn ghost"
            aria-label="Next wallpaper"
            onClick={(event) => {
              event.stopPropagation();
              onIndex((index + 1) % items.length);
            }}
          >
            ›
          </button>
        </>
      )}
      <figure className="lightbox-frame" onClick={(event) => event.stopPropagation()}>
        <WallpaperStage
          className="lightbox-stage"
          wrapClassName="tv-preview"
          ariaLabel={`${item.title} ${useVideo ? "VIDEO" : "still image"}`}
          artSrc={stillSrc}
          artAlt={`${item.title} artwork`}
          videoSrc={useVideo ? item.videoSrc : null}
          paused={paused}
          onVideoError={() => {
            setVideoFailed(true);
            notify("error", "Could not play VIDEO. Showing the still image.");
          }}
        />
        <figcaption>
          {item.subtitle ? <span className="muted">{item.subtitle}</span> : null}
          <ChromePills
            watchState={item.watchState}
            libraryState={item.libraryState}
            availability={item.availability}
            source={item.source}
          />
          <span className={`badge ${useVideo ? "badge-video" : ""}`}>{modeLabel}</span>
        </figcaption>
        <div className="lightbox-actions" onClick={(event) => event.stopPropagation()}>
          {useVideo && (
            <button type="button" className="btn ghost tiny" onClick={() => setPaused((current) => !current)}>
              {paused ? "Play" : "Pause"}
            </button>
          )}
          {onPin && (
            <button type="button" className="btn ghost tiny" onClick={() => onPin(item)}>
              {item.pinned ? "Unpin" : "Pin"}
            </button>
          )}
          {onHide && (
            <button type="button" className="btn ghost tiny" onClick={() => onHide(item)}>
              {item.hidden ? "Allow again" : "Never show"}
            </button>
          )}
          {onDelete && (
            <button type="button" className="btn danger tiny" onClick={() => onDelete(item)}>
              Delete
            </button>
          )}
        </div>
      </figure>
    </div>
  );
}
