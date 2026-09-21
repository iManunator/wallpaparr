export type GalleryFlags = {
  id: string;
  title: string;
  pinned?: boolean;
  hidden?: boolean;
};

export type GalleryDeleteResult = {
  status?: string;
  message?: string;
  deleted?: string[];
  titles?: string[];
  missing?: string[];
  errors?: string[];
  skipped_pinned?: string[];
  skipped_titles?: string[];
  count?: number;
  pinned_kept?: number;
  include_pins?: boolean;
};

export type ConfirmCopy = {
  title: string;
  body: string;
  note: string;
  confirmLabel: string;
  extraLabel: string | null;
  empty: boolean;
};

function noun(count: number, one: string, many: string): string {
  return count === 1 ? one : many;
}

export function deleteSelectedCopy(items: GalleryFlags[]): ConfirmCopy {
  const n = items.length;
  if (!n) {
    return {
      title: "Delete selected?",
      body: "Nothing is selected.",
      note: "",
      confirmLabel: "",
      extraLabel: null,
      empty: true,
    };
  }
  const pinned = items.filter((item) => item.pinned).length;
  const label = n === 1 ? `“${items[0].title}”` : `${n} wallpapers`;
  return {
    title: n === 1 ? `Delete ${label}?` : "Delete selected?",
    body: `Permanently delete ${label}. This cannot be undone.`,
    note: pinned ? `This includes ${pinned} pinned ${noun(pinned, "wallpaper", "wallpapers")}.` : "",
    confirmLabel: n === 1 ? "Delete" : `Delete ${n}`,
    extraLabel: null,
    empty: false,
  };
}

export function deleteAllCopy(items: GalleryFlags[]): ConfirmCopy {
  const total = items.length;
  const pinned = items.filter((item) => item.pinned).length;
  const unpinned = total - pinned;
  const hidden = items.filter((item) => item.hidden && !item.pinned).length;
  if (!total) {
    return {
      title: "Clear gallery?",
      body: "The gallery is already empty.",
      note: "",
      confirmLabel: "",
      extraLabel: null,
      empty: true,
    };
  }
  if (!unpinned) {
    return {
      title: "Clear gallery?",
      body: `All ${pinned} ${noun(pinned, "wallpaper is", "wallpapers are")} pinned. Delete ${pinned === 1 ? "it" : "them"} anyway? This cannot be undone.`,
      note: "Pins are kept unless you choose to delete them.",
      confirmLabel: "",
      extraLabel: `Delete ${pinned} including ${noun(pinned, "pin", "pins")}`,
      empty: false,
    };
  }
  const hiddenBit = hidden ? ` (including ${hidden} never-show)` : "";
  return {
    title: "Clear gallery?",
    body: `Permanently delete ${unpinned} ${noun(unpinned, "wallpaper", "wallpapers")}${hiddenBit}. This cannot be undone.`,
    note: pinned ? `${pinned} pinned ${noun(pinned, "wallpaper", "wallpapers")} will be kept.` : "",
    confirmLabel: pinned ? `Delete ${unpinned} unpinned` : `Delete all ${unpinned}`,
    extraLabel: pinned ? `Delete all ${total} including ${pinned} ${noun(pinned, "pin", "pins")}` : null,
    empty: false,
  };
}

export function filenameStem(filename: string): string {
  const trimmed = filename.trim();
  const dot = trimmed.lastIndexOf(".");
  return dot > 0 ? trimmed.slice(0, dot) : trimmed || "untitled";
}

export type GalleryPreviewSources = {
  stillSrc: string;
  videoSrc: string | null;
  plateSrc: string;
  artworkSrc: string | null;
  chromeSrc: string;
  logoSrc: string | null;
  artCandidates: string[];
};

export function galleryPreviewSources(
  item: {
    layout: string;
    filename: string;
    has_video?: boolean;
    jellyfin_id?: string | null;
    tmdb_id?: string | null;
  },
  urls: {
    wallpaperImage: (layout: string, filename: string) => string;
    mediaArtwork: (itemId: string) => string;
    mediaLogo: (itemId: string, tmdbId?: string | null) => string;
  },
): GalleryPreviewSources {
  const stem = filenameStem(item.filename);
  const stillSrc = urls.wallpaperImage(item.layout, item.filename);
  const plateSrc = urls.wallpaperImage(item.layout, `${stem}_plate.jpg`);
  const chromeSrc = urls.wallpaperImage(item.layout, `${stem}_chrome.png`);
  const videoSrc = item.has_video ? urls.wallpaperImage(item.layout, `${stem}.mp4`) : null;
  const mediaId = item.jellyfin_id || item.tmdb_id || "";
  const artworkSrc = mediaId ? urls.mediaArtwork(mediaId) : null;
  const logoSrc = mediaId ? urls.mediaLogo(mediaId, item.tmdb_id) : null;
  const artCandidates = [artworkSrc, plateSrc, stillSrc].filter((src, index, list): src is string => Boolean(src) && list.indexOf(src) === index);
  return { stillSrc, videoSrc, plateSrc, artworkSrc, chromeSrc, logoSrc, artCandidates };
}

export function formatDeleteToast(result: GalleryDeleteResult | null | undefined, fallback: string): string {
  const text = result?.message?.trim();
  if (text) return text;
  const count = result?.count ?? result?.deleted?.length ?? 0;
  const kept = result?.pinned_kept ?? result?.skipped_pinned?.length ?? 0;
  if (!count && kept) return `Kept ${kept} pinned ${noun(kept, "wallpaper", "wallpapers")}. Nothing else to delete.`;
  if (!count) return fallback;
  let msg = `Deleted ${count} ${noun(count, "wallpaper", "wallpapers")}.`;
  if (kept) msg += ` Kept ${kept} pinned ${noun(kept, "wallpaper", "wallpapers")}.`;
  return msg;
}
