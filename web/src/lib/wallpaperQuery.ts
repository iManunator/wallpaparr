export type WallpaperQuery = {
  layout: string;
  sort: string;
  pool?: string;
  genre?: string;
  age_rating?: string;
  min_year?: string;
  max_year?: string;
  min_rating?: number;
  max_rating?: number;
  exclude?: string;
  profile?: string;
  queue?: string;
};

export function parseYearRange(yearFilter: string): { min?: string; max?: string } {
  const raw = yearFilter.trim();
  if (!raw) return {};
  if (raw.includes("-")) {
    const [min, max] = raw.split("-", 2).map((p) => p.trim());
    return { min, max };
  }
  return { min: raw, max: raw };
}

export function buildStatusQuery(input: WallpaperQuery): string {
  const params = new URLSearchParams();
  params.set("layout", input.layout);
  if (input.sort) params.set("sort", input.sort);
  if (input.pool) params.set("pool", input.pool);
  if (input.genre) params.set("genre", input.genre);
  if (input.age_rating) params.set("age_rating", input.age_rating);
  if (input.min_year) params.set("min_year", input.min_year);
  if (input.max_year) params.set("max_year", input.max_year);
  if (input.min_rating && input.min_rating > 0) params.set("min_rating", String(input.min_rating));
  if (input.max_rating != null && input.max_rating < 10) params.set("max_rating", String(input.max_rating));
  if (input.exclude) params.set("exclude", input.exclude);
  if (input.profile) params.set("profile", input.profile);
  if (input.queue) params.set("queue", input.queue);
  return `/api/wallpaper/status?${params.toString()}`;
}

export function rememberShownPath(recent: string[], path: string, depth: number): string[] {
  const next = [path, ...recent.filter((item) => item && item !== path)];
  return next.slice(0, Math.max(1, depth));
}
