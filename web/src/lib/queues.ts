import type { WallpaperRecord } from "./layout";
import { watchBadge } from "./watch";

export const QUEUE_LABELS: Record<string, string> = {
  unwatched: "Unwatched",
  continue_watching: "Continue watching",
  watched: "Watched",
  newly_added: "Newly added",
  seerr_trending: "Seerr trending",
  requestable: "Requestable",
  pinned: "Pinned",
};

export const TASTE_PRESETS: Record<string, Record<string, number>> = {
  tonight: { unwatched: 30, continue_watching: 20, watched: 15, newly_added: 20, seerr_trending: 15 },
  unwatched_heavy: { unwatched: 70, continue_watching: 20, newly_added: 10 },
  cinephile: { unwatched: 40, newly_added: 20, seerr_trending: 40 },
  discovery: { requestable: 50, seerr_trending: 50 },
};

export const LAYOUT_DNA = [
  { name: "Netflix Hero", blurb: "Top-left hero chrome over a heavy fade — logo when available" },
  { name: "Prime Cinematic", blurb: "Low, centered title card over a deep bottom gradient" },
  { name: "Google TV Clean", blurb: "Minimal top-right chrome, lots of artwork breathing room" },
  { name: "Projectivy Dock", blurb: "Safe zones below the clock, above the row dock" },
  { name: "Status Focus", blurb: "Watch-state and library badges anchored bottom-right" },
  { name: "Jellyfin Dense", blurb: "Packed bottom-left chrome for library browsing" },
];

export function queueBadges(record: Pick<WallpaperRecord, "watch_state" | "library_state" | "source" | "pinned" | "hidden" | "has_video"> & { availability?: string }): string[] {
  const badges: string[] = [];
  const watch = (record.watch_state || "").toLowerCase();
  const library = (record.library_state || "").toLowerCase();
  const availability = (record.availability || "").toLowerCase();
  const source = (record.source || "").toLowerCase();
  if (record.pinned) badges.push("Pinned");
  if (record.hidden) badges.push("Never show");
  const watchPill = watchBadge(watch);
  if (watchPill) badges.push(watchPill.label);
  if (availability === "requestable" || availability === "not_available" || library === "seerr_only") {
    badges.push("Requestable");
  }
  if (source === "jellyseerr" || source === "seerr") badges.push("Seerr");
  if (record.has_video) badges.push("VIDEO");
  return badges;
}

export function formatOpsTime(at: number | null | undefined): string {
  if (!at) return "never";
  const delta = Date.now() / 1000 - at;
  if (delta < 90) return "just now";
  if (delta < 3600) return `${Math.round(delta / 60)}m ago`;
  if (delta < 86400) return `${Math.round(delta / 3600)}h ago`;
  return `${Math.round(delta / 86400)}d ago`;
}
