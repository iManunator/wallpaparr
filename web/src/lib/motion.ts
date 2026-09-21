export type MotionStyle = "parallax" | "kenburns" | "drift";

/** Match backend AppSettings / profile_from_settings first-run defaults. */
export const DEFAULT_MOTION_DURATION = 15;
export const DEFAULT_MOTION_FPS = 24;
export const DEFAULT_MOTION_PRESET = "balanced";

export function clampIntensity(value: number): number {
  if (Number.isNaN(value)) return 0.55;
  return Math.min(1, Math.max(0, value));
}

export function defaultDuration(_quality?: string): number {
  return DEFAULT_MOTION_DURATION;
}

export function describeMotion(style: MotionStyle, intensity: number, duration: number): string {
  const depth =
    intensity >= 0.7 ? "bold" : intensity >= 0.45 ? "cinematic" : intensity >= 0.28 ? "balanced" : "subtle";
  const label =
    style === "parallax"
      ? "Parallax (artwork drifts; chrome stays locked)"
      : style === "drift"
        ? "Drift (slow pan of artwork; chrome locked)"
        : "Ken Burns (zoom/pan artwork; chrome locked)";
  return `${label} · ${depth} · ${duration}s loop`;
}

export const INTENSITY_PRESETS: Record<string, number> = {
  subtle: 0.16,
  balanced: 0.355,
  cinematic: 0.55,
  bold: 0.96,
};

/** UI order for Settings / Editor / Tonight intensity chips. */
export const MOTION_PRESET_ORDER = ["subtle", "balanced", "cinematic", "bold"] as const;

export const PRESET_DURATION: Record<string, number> = {
  subtle: 16,
  balanced: 14,
  cinematic: 12,
  bold: 10,
};

/** Stay inside Subtle / Balanced / Cinematic / Bold; matched in backend/app/motion.py. */
const PRESET_BAND: Record<string, [number, number]> = {
  subtle: [0.1, 0.28],
  balanced: [0.29, 0.42],
  cinematic: [0.43, 0.72],
  bold: [0.82, 1],
};
const INTENSITY_JITTER = 0.08;
const ZOOM_SCALE_SPAN = 0.06;
const PAN_SCALE_SPAN = 0.06;
const PAN_Y_RATIO_MIN = 0.1;
const PAN_Y_RATIO_MAX = 0.18;
const DEFAULT_PAN_Y_RATIO = 0.14;

export function intensityFromPreset(name: string | null | undefined): number {
  return INTENSITY_PRESETS[(name || DEFAULT_MOTION_PRESET).toLowerCase()] ?? INTENSITY_PRESETS[DEFAULT_MOTION_PRESET];
}

export function nearestMotionPreset(value: number): string {
  const intensity = clampIntensity(value);
  return Object.entries(INTENSITY_PRESETS).reduce((best, [name, amount]) =>
    Math.abs(amount - intensity) < Math.abs(INTENSITY_PRESETS[best] - intensity) ? name : best,
  DEFAULT_MOTION_PRESET);
}

export type VariedMotion = {
  style: MotionStyle;
  intensity: number;
  duration: number;
  panXSign: number;
  panYSign: number;
  panYRatio: number;
  phase: number;
  zoomScale: number;
  panScale: number;
  preset?: string;
};

export function motionSeedKey(...parts: Array<string | null | undefined>): string {
  for (const part of parts) {
    const text = String(part || "").trim();
    if (text) return text.toLowerCase();
  }
  return "wallpaparr";
}

export function fnv1a32(text: string): number {
  let h = 0x811c9dc5;
  const bytes = new TextEncoder().encode(text || "");
  for (const byte of bytes) {
    h ^= byte;
    h = Math.imul(h, 0x01000193);
  }
  return h >>> 0;
}

function lcg32(seed: number): () => number {
  let state = seed >>> 0;
  return () => {
    state = (Math.imul(1664525, state) + 1013904223) >>> 0;
    return state / 4294967296;
  };
}

function lerp(lo: number, hi: number, t: number): number {
  return lo + (hi - lo) * t;
}

export function identityMotion(
  style: MotionStyle,
  intensity: number,
  duration: number,
  preset?: string,
): VariedMotion {
  return {
    style,
    intensity: clampIntensity(intensity),
    duration,
    panXSign: 1,
    panYSign: 1,
    panYRatio: DEFAULT_PAN_Y_RATIO,
    phase: 0,
    zoomScale: 1,
    panScale: 1,
    preset,
  };
}

/** Mild seeded drift. Off is identity. Same helper as backend ``vary_motion_profile``. */
export function varyMotionProfile(
  base: { style: MotionStyle; intensity: number; duration: number; preset?: string },
  opts: { enabled?: boolean; seed?: string } = {},
): VariedMotion {
  const identity = identityMotion(base.style, base.intensity, base.duration, base.preset);
  if (!opts.enabled) return identity;
  const rng = lcg32(fnv1a32(motionSeedKey(opts.seed)));
  const jitter = lerp(-INTENSITY_JITTER, INTENSITY_JITTER, rng());
  let intensity = Math.min(1, Math.max(0, identity.intensity * (1 + jitter)));
  const name = (base.preset || "").trim().toLowerCase();
  if (PRESET_BAND[name]) {
    const [lo, hi] = PRESET_BAND[name];
    intensity = Math.min(hi, Math.max(lo, intensity));
  }
  const panXSign = rng() < 0.5 ? -1 : 1;
  const panYSign = rng() < 0.5 ? -1 : 1;
  const panYRatio = Number(lerp(PAN_Y_RATIO_MIN, PAN_Y_RATIO_MAX, rng()).toFixed(4));
  const phase = Number(rng().toFixed(4));
  const zoomScale = Number(lerp(1 - ZOOM_SCALE_SPAN, 1 + ZOOM_SCALE_SPAN, rng()).toFixed(4));
  const panScale = Number(lerp(1 - PAN_SCALE_SPAN, 1 + PAN_SCALE_SPAN, rng()).toFixed(4));
  return {
    ...identity,
    intensity: Number(intensity.toFixed(4)),
    panXSign,
    panYSign,
    panYRatio,
    phase,
    zoomScale,
    panScale,
  };
}

function motionPreviewVarsFromProfile(profile: VariedMotion): Record<string, string> {
  const i = clampIntensity(profile.intensity);
  const style = profile.style;
  const zoom =
    style === "kenburns" ? 1 + i * 0.22 : style === "drift" ? 1 + i * 0.08 : 1 + i * 0.18;
  const zoomFrom = style === "parallax" ? 1.04 : 1.015;
  const identity =
    profile.panXSign === 1 &&
    profile.panYSign === 1 &&
    Math.abs(profile.panScale - 1) < 1e-9 &&
    Math.abs(profile.zoomScale - 1) < 1e-9 &&
    Math.abs(profile.panYRatio - DEFAULT_PAN_Y_RATIO) < 1e-9 &&
    Math.abs(profile.phase) < 1e-9;
  let zoomTo = zoom;
  let signedX: number;
  let signedY: number;
  if (identity) {
    const panX = style === "drift" ? i * 7.4 : i * 4.8;
    const panY = style === "drift" ? i * 2.6 : i * 1.7;
    signedX = -panX;
    signedY = panY * 0.4;
  } else {
    const panX = (style === "drift" ? i * 7.4 : i * 4.8) * profile.panScale;
    signedX = -panX * profile.panXSign;
    signedY = panX * profile.panYRatio * profile.panYSign;
    const amp = Math.max(0.008, (zoom - zoomFrom) * profile.zoomScale);
    zoomTo = zoomFrom + amp;
  }
  const vars: Record<string, string> = {
    "--motion-zoom-from": style === "parallax" ? "1.04" : "1.015",
    "--motion-zoom-to": identity ? String(zoomTo) : String(Number(zoomTo.toFixed(4))),
    "--motion-x": `${signedX.toFixed(2)}%`,
    "--motion-y": `${signedY.toFixed(2)}%`,
    "--motion-duration": `${Math.max(2, profile.duration)}s`,
  };
  if (!identity) {
    vars["--motion-delay"] = `${(-(profile.phase * Math.max(2, profile.duration))).toFixed(3)}s`;
  }
  return vars;
}

export function motionPreviewVars(
  style: MotionStyle,
  intensity: number,
  duration: number,
  opts?: { vary?: boolean; seed?: string; preset?: string },
): Record<string, string> {
  const i = clampIntensity(intensity);
  if (!opts?.vary) {
    const zoom =
      style === "kenburns" ? 1 + i * 0.22 : style === "drift" ? 1 + i * 0.08 : 1 + i * 0.18;
    const panX = style === "drift" ? i * 7.4 : i * 4.8;
    const panY = style === "drift" ? i * 2.6 : i * 1.7;
    return {
      "--motion-zoom-from": style === "parallax" ? "1.04" : "1.015",
      "--motion-zoom-to": String(zoom),
      "--motion-x": `-${panX.toFixed(2)}%`,
      "--motion-y": `${(panY * 0.4).toFixed(2)}%`,
      "--motion-duration": `${Math.max(2, duration)}s`,
    };
  }
  return motionPreviewVarsFromProfile(
    varyMotionProfile(
      { style, intensity: i, duration, preset: opts.preset },
      { enabled: true, seed: opts.seed },
    ),
  );
}

export function shouldPreferVideo(opts: {
  preferMotion: boolean;
  hasVideo: boolean;
  fallbackStill: boolean;
}): "video" | "image" | "none" {
  if (opts.preferMotion && opts.hasVideo) return "video";
  if (opts.fallbackStill) return "image";
  if (opts.hasVideo) return "video";
  return "none";
}
