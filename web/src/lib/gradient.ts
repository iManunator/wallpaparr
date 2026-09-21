import type { CSSProperties } from "react";
import type { GradientStop, Layout, LayoutBackground } from "./layout";

export function hexAlpha(color: string, alpha: number): string {
  const raw = (color || "#000000").replace("#", "");
  const full = raw.length === 3 ? raw.split("").map((ch) => ch + ch).join("") : raw;
  const r = Number.parseInt(full.slice(0, 2), 16) || 0;
  const g = Number.parseInt(full.slice(2, 4), 16) || 0;
  const b = Number.parseInt(full.slice(4, 6), 16) || 0;
  const a = Math.max(0, Math.min(1, alpha));
  return `rgba(${r}, ${g}, ${b}, ${a})`;
}

function pct(value: number): string {
  return `${Math.round(Math.max(0, Math.min(1, value)) * 100)}%`;
}

export function defaultStops(color = "#050505"): GradientStop[] {
  return [
    { color, position: 0, opacity: 0.9 },
    { color, position: 0.45, opacity: 0.28 },
    { color, position: 1, opacity: 0 },
  ];
}

export function cssGradient(bg: LayoutBackground): string {
  const master = bg.gradient_opacity ?? 0;
  const stops = (bg.gradient_stops?.length ? bg.gradient_stops : defaultStops(bg.color))
    .slice()
    .sort((a, b) => a.position - b.position)
    .map((stop) => `${hexAlpha(stop.color, stop.opacity * master)} ${pct(stop.position)}`);
  if ((bg.gradient_type || "linear") === "radial") {
    return `radial-gradient(ellipse at center, ${stops.join(", ")})`;
  }
  return `linear-gradient(${bg.gradient_angle ?? 90}deg, ${stops.join(", ")})`;
}

export function stageOverlayStyle(bg: LayoutBackground): CSSProperties {
  const layers: string[] = [];
  if ((bg.gradient_opacity || 0) > 0.001) layers.push(cssGradient(bg));
  if ((bg.overlay_opacity || 0) > 0.001) {
    layers.push(`linear-gradient(${hexAlpha(bg.overlay_color || "#000", bg.overlay_opacity)}, ${hexAlpha(bg.overlay_color || "#000", bg.overlay_opacity)})`);
  }
  if ((bg.vignette || 0) > 0.001) {
    const inner = Math.round((1 - bg.vignette) * 42);
    layers.push(
      `radial-gradient(ellipse at center, transparent ${inner}%, ${hexAlpha("#000000", bg.vignette * 0.88)} 100%)`,
    );
  }
  const wash = hexAlpha(bg.color || "#050505", 0.88);
  const washMid = hexAlpha(bg.color || "#050505", 0.32);
  layers.push(`linear-gradient(90deg, ${wash} 0%, ${washMid} ${pct(bg.fade_left)}, transparent ${pct(bg.fade_left + 0.18)})`);
  layers.push(`linear-gradient(270deg, ${hexAlpha(bg.color, 0.65)} 0%, transparent ${pct(bg.fade_right)})`);
  layers.push(`linear-gradient(180deg, ${hexAlpha(bg.color, 0.5)} 0%, transparent ${pct(bg.fade_top)})`);
  layers.push(`linear-gradient(0deg, ${hexAlpha(bg.color, 0.72)} 0%, transparent ${pct(bg.fade_bottom)})`);
  return {
    backgroundImage: layers.join(", "),
    filter: bg.brightness && bg.brightness !== 1 ? `brightness(${bg.brightness})` : undefined,
  };
}

export type LookPreset = {
  id: string;
  label: string;
  blurb: string;
  patch: Partial<LayoutBackground>;
};

export const LOOK_PRESETS: LookPreset[] = [
  {
    id: "hero",
    label: "Hero fade",
    blurb: "Heavy left wash for Netflix-style metadata.",
    patch: {
      fade_left: 0.48,
      fade_bottom: 0.42,
      fade_top: 0.1,
      fade_right: 0.04,
      fade_softness: 0.45,
      vignette: 0.18,
      overlay_opacity: 0.06,
      gradient_type: "linear",
      gradient_angle: 90,
      gradient_opacity: 0.62,
      gradient_stops: [
        { color: "#050505", position: 0, opacity: 0.92 },
        { color: "#050505", position: 0.4, opacity: 0.3 },
        { color: "#050505", position: 1, opacity: 0 },
      ],
    },
  },
  {
    id: "bottom-card",
    label: "Bottom card",
    blurb: "Prime-style floor gradient under a low title.",
    patch: {
      fade_left: 0.16,
      fade_right: 0.16,
      fade_top: 0.06,
      fade_bottom: 0.58,
      vignette: 0.12,
      overlay_opacity: 0.08,
      gradient_type: "linear",
      gradient_angle: 180,
      gradient_opacity: 0.8,
      gradient_stops: [
        { color: "#0b1018", position: 0, opacity: 0 },
        { color: "#0b1018", position: 0.45, opacity: 0.15 },
        { color: "#0b1018", position: 1, opacity: 0.92 },
      ],
    },
  },
  {
    id: "spotlight",
    label: "Radial spotlight",
    blurb: "Artwork pops in the center; chrome sits in the dark.",
    patch: {
      fade_left: 0.2,
      fade_right: 0.2,
      fade_top: 0.16,
      fade_bottom: 0.22,
      vignette: 0.55,
      overlay_opacity: 0.1,
      gradient_type: "radial",
      gradient_angle: 0,
      gradient_opacity: 0.7,
      gradient_stops: [
        { color: "#000000", position: 0, opacity: 0 },
        { color: "#000000", position: 0.45, opacity: 0.15 },
        { color: "#000000", position: 1, opacity: 0.82 },
      ],
    },
  },
  {
    id: "letterbox",
    label: "Letterbox",
    blurb: "Cinema bars on top and bottom.",
    patch: {
      fade_left: 0.08,
      fade_right: 0.08,
      fade_top: 0.22,
      fade_bottom: 0.22,
      vignette: 0.28,
      overlay_opacity: 0.05,
      gradient_type: "linear",
      gradient_angle: 180,
      gradient_opacity: 0.45,
      gradient_stops: [
        { color: "#000000", position: 0, opacity: 0.85 },
        { color: "#000000", position: 0.22, opacity: 0 },
        { color: "#000000", position: 0.78, opacity: 0 },
        { color: "#000000", position: 1, opacity: 0.85 },
      ],
    },
  },
];

export function applyLook(layout: Layout, preset: LookPreset): Layout {
  return {
    ...layout,
    background: { ...layout.background, ...preset.patch },
  };
}
