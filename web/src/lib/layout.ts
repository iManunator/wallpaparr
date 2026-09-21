export type Layer = {
  id: string;
  slot: string;
  x: number;
  y: number;
  width?: number | null;
  height?: number | null;
  font_size: number;
  color: string;
  font_weight: string;
  max_items?: number | null;
  visible: boolean;
  align: string;
};

export type GradientStop = {
  color: string;
  position: number;
  opacity: number;
};

export type LayoutBackground = {
  mode: string;
  color: string;
  fade_left: number;
  fade_right: number;
  fade_top: number;
  fade_bottom: number;
  fade_softness: number;
  brightness: number;
  gradient_type: "linear" | "radial" | string;
  gradient_angle: number;
  gradient_opacity: number;
  gradient_stops: GradientStop[];
  vignette: number;
  overlay_color: string;
  overlay_opacity: number;
};

export type Layout = {
  name: string;
  canvas_width: number;
  canvas_height: number;
  background: LayoutBackground;
  layers: Layer[];
  preset?: boolean;
  preset_id?: string | null;
  description?: string;
  title_display?: "auto" | "logo" | "text";
  logo_max_width?: number;
  logo_max_height?: number;
  logo_padding?: number;
  show_watch_badge?: boolean;
  show_seerr_badge?: boolean;
  dna_revision?: number;
};

export type WallpaperRecord = {
  id: string;
  layout: string;
  filename: string;
  title: string;
  year?: number | null;
  rating: number;
  genres: string[];
  official_rating: string;
  watch_state: string;
  library_state: string;
  availability?: string;
  source: string;
  jellyfin_id?: string | null;
  tmdb_id?: string | null;
  imdb_id?: string | null;
  has_video: boolean;
  parallax_style?: string | null;
  action_url?: string | null;
  pinned?: boolean;
  hidden?: boolean;
};

export type CronJob = {
  name?: string;
  enabled?: boolean;
  cron?: string;
  layout?: string;
  source?: string;
  seerr_category?: string;
  skip_existing?: boolean;
  replace_existing?: boolean;
  refresh_status?: boolean;
  cleanup?: boolean;
  motion?: boolean;
  limit?: number;
  ids?: string[] | string;
  skip_ids?: string[] | string;
};

export type AppSettings = {
  public_base_url: string;
  timezone: string;
  motion_wallpapers: boolean;
  motion_quality: string;
  motion_style: string;
  motion_intensity: number;
  motion_duration: number | null;
  motion_fps: number;
  overwrite_existing: boolean;
  editor_theme: string;
  motion_preset?: string;
  light_leak?: boolean;
  motion_vary?: boolean;
  motion_edge_fade?: boolean;
  motion_edge_fade_seconds?: number;
  motion_fly_in?: boolean;
  motion_fly_in_seconds?: number;
  taste_profile?: string;
  taste_weights?: Record<string, number>;
  overlays_enabled?: boolean;
  overlay_clock?: boolean;
  overlays?: Array<Record<string, unknown>>;
  title_display?: "auto" | "logo" | "text";
  jellyfin: Record<string, string>;
  jellyseerr: Record<string, string>;
  tmdb: Record<string, string>;
  omdb: Record<string, string>;
  cron_jobs: CronJob[];
};

export type GenerateRequest = {
  layout: string;
  source: string;
  limit: number;
  skip_existing: boolean;
  replace_existing: boolean;
  refresh_status?: boolean;
  cleanup: boolean;
  motion: boolean;
  ids?: string[];
  skip_ids?: string[];
  seerr_category?: string;
};

export const SLOTS = [
  "title",
  "year",
  "genres",
  "runtime",
  "rating",
  "overview",
  "watch_status",
  "seerr_status",
  "source",
  "age",
  "media_type",
  "imdb_rating",
  "rotten_tomatoes",
  "metacritic",
  "awards",
] as const;

export function emptyLayout(name = "Untitled"): Layout {
  return {
    name,
    canvas_width: 1920,
    canvas_height: 1080,
    background: {
      mode: "backdrop",
      color: "#050505",
      fade_left: 0.42,
      fade_right: 0.05,
      fade_top: 0.08,
      fade_bottom: 0.38,
      fade_softness: 0.45,
      brightness: 1,
      gradient_type: "linear",
      gradient_angle: 90,
      gradient_opacity: 0.55,
      gradient_stops: [
        { color: "#050505", position: 0, opacity: 0.88 },
        { color: "#050505", position: 0.42, opacity: 0.28 },
        { color: "#050505", position: 1, opacity: 0 },
      ],
      vignette: 0.22,
      overlay_color: "#000000",
      overlay_opacity: 0.08,
    },
    layers: [
      {
        id: "title",
        slot: "title",
        x: 80,
        y: 80,
        width: 860,
        font_size: 64,
        color: "#ffffff",
        font_weight: "bold",
        visible: true,
        align: "left",
      },
      {
        id: "watch",
        slot: "watch_status",
        x: 80,
        y: 220,
        font_size: 22,
        color: "#7ad0c4",
        font_weight: "regular",
        visible: true,
        align: "left",
      },
    ],
    title_display: "auto",
    logo_max_width: 1200,
    logo_max_height: 450,
    logo_padding: 25,
    show_watch_badge: true,
    show_seerr_badge: true,
  };
}

export function validateLayout(layout: Layout): string[] {
  const errors: string[] = [];
  if (!layout.name.trim()) errors.push("Layout name is required");
  if (layout.canvas_width < 1280 || layout.canvas_height < 720) {
    errors.push("Canvas must be at least 1280×720");
  }
  if (!layout.layers.length) errors.push("Add at least one layer");
  const ids = new Set<string>();
  for (const layer of layout.layers) {
    if (!layer.id.trim()) errors.push("Every layer needs an id");
    if (ids.has(layer.id)) errors.push(`Duplicate layer id: ${layer.id}`);
    ids.add(layer.id);
    if (layer.x < 0 || layer.y < 0) errors.push(`Layer ${layer.id} is off-canvas`);
  }
  const bg = layout.background;
  if (bg.gradient_opacity < 0 || bg.gradient_opacity > 1) errors.push("Gradient opacity must be 0–1");
  if (bg.vignette < 0 || bg.vignette > 1) errors.push("Vignette must be 0–1");
  for (const stop of bg.gradient_stops || []) {
    if (stop.position < 0 || stop.position > 1) errors.push("Gradient stops must sit between 0% and 100%");
  }
  return errors;
}

export function reorderLayer<T>(layers: T[], index: number, delta: number): T[] {
  const target = index + delta;
  if (target < 0 || target >= layers.length) return layers;
  const next = layers.slice();
  const [item] = next.splice(index, 1);
  next.splice(target, 0, item);
  return next;
}

export function removeLayer<T>(layers: T[], index: number): T[] {
  return layers.filter((_, i) => i !== index);
}

/** New selected index after removeLayer(index); clamps and shifts to keep
 * pointing at the same surviving layer instead of drifting to its neighbour. */
export function selectionAfterRemove(selected: number, removedIndex: number, remainingCount: number): number {
  const shifted = removedIndex < selected ? selected - 1 : selected;
  return Math.min(shifted, Math.max(remainingCount - 1, 0));
}

export function duplicateLayout(layout: Layout, newName: string): Layout {
  return {
    ...layout,
    name: newName,
    preset: false,
    preset_id: null,
  };
}

export function normalizeLayout(raw: Partial<Layout> | Layout | null | undefined): Layout {
  const base = emptyLayout(raw?.name || "Untitled");
  if (!raw) return base;
  return {
    ...base,
    ...raw,
    name: raw.name || base.name,
    canvas_width: raw.canvas_width || base.canvas_width,
    canvas_height: raw.canvas_height || base.canvas_height,
    background: { ...base.background, ...(raw.background || {}) },
    layers: raw.layers?.length ? raw.layers : base.layers,
    title_display: raw.title_display === "logo" || raw.title_display === "text" ? raw.title_display : "auto",
    logo_max_width: raw.logo_max_width || base.logo_max_width,
    logo_max_height: raw.logo_max_height || base.logo_max_height,
    logo_padding: raw.logo_padding || base.logo_padding,
    show_watch_badge: raw.show_watch_badge !== false,
    show_seerr_badge: raw.show_seerr_badge !== false,
  };
}
