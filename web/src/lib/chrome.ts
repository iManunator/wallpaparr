/** Shared TV-safe chrome pill geometry (web CSS + Pillow bake). */
export const CHROME_PILL = {
  padXEm: 0.72,
  padYEm: 0.32,
  minHeightEm: 1.65,
  gapEm: 0.5,
  radius: "999px",
  display: "inline-flex",
} as const;

export const CHROME_PILL_FALLBACK = {
  leftPercent: 4.2,
  topPercent: 29.4,
} as const;

export const CHROME_PILL_SAMPLE = {
  leftPercent: 6,
  topPercent: 8,
} as const;

/** Keep the watch-slot chip when Seerr still needs that DNA position. */
export function keepWatchSlot(
  showWatch: boolean,
  showSeerr: boolean,
  hasSeerrLayer: boolean,
): boolean {
  return showWatch || (showSeerr && !hasSeerrLayer);
}
