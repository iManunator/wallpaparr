export type SeerrKind = "seerr_only" | "requestable" | "on_seerr" | "upcoming";

export const LIBRARY_SEERR_ONLY = new Set(["seerr_only", "not_in_library"]);
export const AVAIL_REQUESTABLE = new Set(["requestable", "not_available"]);
export const AVAIL_UPCOMING = new Set(["upcoming"]);
export const SOURCE_SEERR = new Set(["jellyseerr", "seerr"]);
export const LIBRARY_IN = new Set(["in_library", "available"]);

export const SEERR_TONES: Record<SeerrKind, { label: string; color: string }> = {
  seerr_only: { label: "Seerr only", color: "#c4a5ff" },
  requestable: { label: "Requestable", color: "#f0a36b" },
  on_seerr: { label: "On Seerr", color: "#8eb4ff" },
  upcoming: { label: "Upcoming", color: "#f2c94c" },
};

function norm(value?: string | null): string {
  return (value || "").trim().toLowerCase().replace(/[\s-]+/g, "_");
}

export function seerrKind(
  libraryState?: string | null,
  availability?: string | null,
  source?: string | null,
): SeerrKind | null {
  const library = norm(libraryState);
  const avail = norm(availability);
  const src = norm(source);
  const inLibrary = LIBRARY_IN.has(library);
  if (AVAIL_UPCOMING.has(avail)) return "upcoming";
  if (LIBRARY_SEERR_ONLY.has(library)) return "seerr_only";
  if (AVAIL_REQUESTABLE.has(avail)) return "requestable";
  if (SOURCE_SEERR.has(src) && !inLibrary) return "on_seerr";
  return null;
}

export function seerrBadge(
  libraryState?: string | null,
  availability?: string | null,
  source?: string | null,
): { id: SeerrKind; label: string; color: string } | null {
  const kind = seerrKind(libraryState, availability, source);
  if (!kind) return null;
  return { id: kind, ...SEERR_TONES[kind] };
}
