export type WatchKind = "unwatched" | "partial" | "watched";

export const WATCH_UNWATCHED = new Set(["unwatched", "unplayed"]);
export const WATCH_PARTIAL = new Set(["partial", "partially_watched", "inprogress", "in_progress"]);
export const WATCH_WATCHED = new Set(["watched", "played"]);

export const WATCH_TONES: Record<WatchKind, { label: string; color: string }> = {
  unwatched: { label: "Unwatched", color: "#7ad0c4" },
  partial: { label: "Partly watched", color: "#e2b657" },
  watched: { label: "Watched", color: "#87c38f" },
};

export function normalizeWatchState(value?: string | null): WatchKind | null {
  const key = (value || "").trim().toLowerCase().replace(/[\s-]+/g, "_");
  if (WATCH_UNWATCHED.has(key)) return "unwatched";
  if (WATCH_PARTIAL.has(key)) return "partial";
  if (WATCH_WATCHED.has(key)) return "watched";
  return null;
}

export function watchBadge(value?: string | null): { id: WatchKind; label: string; color: string } | null {
  const kind = normalizeWatchState(value);
  if (!kind) return null;
  return { id: kind, ...WATCH_TONES[kind] };
}

export function badgeClass(label: string): string {
  if (label === "Unwatched") return "chrome-pill badge badge-watch unwatched";
  if (label === "Partly watched" || label === "Continue") return "chrome-pill badge badge-watch partial";
  if (label === "Watched") return "chrome-pill badge badge-watch watched";
  if (label === "Seerr only") return "chrome-pill badge badge-seerr seerr_only";
  if (label === "Requestable") return "chrome-pill badge badge-seerr requestable";
  if (label === "On Seerr") return "chrome-pill badge badge-seerr on_seerr";
  if (label === "VIDEO") return "chrome-pill badge badge-video";
  return "chrome-pill badge";
}
