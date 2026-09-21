import type { GalleryDeleteResult } from "./gallery";
import type { AppSettings, GenerateRequest, Layout, WallpaperRecord } from "./layout";

export type JobSnapshot = {
  id: string | null;
  kind: string | null;
  status: string;
  total: number;
  done: number;
  current: string | null;
  message: string;
  created: string[];
  failed: string[];
  skipped: string[];
  error: string | null;
  result: Record<string, unknown> | null;
  percent: number;
  cancel_requested?: boolean;
};

async function json<T>(input: RequestInfo, init?: RequestInit): Promise<T> {
  const response = await fetch(input, {
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    ...init,
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || response.statusText);
  }
  return response.json() as Promise<T>;
}

export const api = {
  layouts: () => json<string[]>("/api/layouts/list"),
  layout: (name: string) => json<Layout>(`/api/layouts/load/${encodeURIComponent(name)}`),
  saveLayout: (layout: Layout) =>
    json<{ status: string }>("/api/layouts/save", { method: "POST", body: JSON.stringify(layout) }),
  resetLayout: (name: string) =>
    json<{ status: string; layout: Layout }>(`/api/layouts/reset/${encodeURIComponent(name)}`, { method: "POST" }),
  deleteLayout: (name: string) =>
    json<{ status: string }>(`/api/layouts/delete/${encodeURIComponent(name)}`, { method: "POST" }),
  gallery: (layout?: string) =>
    json<WallpaperRecord[]>(layout ? `/api/gallery?layout=${encodeURIComponent(layout)}` : "/api/gallery"),
  settings: () => json<AppSettings>("/api/settings"),
  saveSettings: (settings: AppSettings) =>
    json("/api/settings", { method: "POST", body: JSON.stringify(settings) }),
  generate: (body: GenerateRequest) =>
    json("/api/generate", { method: "POST", body: JSON.stringify(body) }),
  generateMotion: (layout: string, path?: string) => {
    const params = new URLSearchParams({ layout });
    if (path) params.set("path", path);
    return json(`/api/wallpaper/generate-motion?${params.toString()}`, { method: "POST" });
  },
  runCron: (body: Record<string, unknown>) =>
    json("/api/cron/run", { method: "POST", body: JSON.stringify(body) }),
  jobsLatest: () => json<JobSnapshot>("/api/jobs/latest"),
  job: (id: string) => json<JobSnapshot>(`/api/jobs/${encodeURIComponent(id)}`),
  startJob: (body: Record<string, unknown>) =>
    json<JobSnapshot>("/api/jobs", { method: "POST", body: JSON.stringify(body) }),
  cancelJob: (id: string) =>
    json<JobSnapshot>(`/api/jobs/${encodeURIComponent(id)}/cancel`, { method: "POST" }),
  deleteGallery: (id: string) =>
    json<GalleryDeleteResult>(`/api/gallery/${encodeURIComponent(id)}`, { method: "DELETE" }),
  deleteGalleryMany: (ids: string[]) =>
    json<GalleryDeleteResult>("/api/gallery/delete", {
      method: "POST",
      body: JSON.stringify({ ids }),
    }),
  deleteGalleryAll: (opts?: { includePins?: boolean; layout?: string }) =>
    json<GalleryDeleteResult>("/api/gallery/delete-all", {
      method: "POST",
      body: JSON.stringify({
        include_pins: Boolean(opts?.includePins),
        layout: opts?.layout || undefined,
      }),
    }),
  options: () => json<Record<string, unknown>>("/api/options"),
  media: (source: string, limit = 12) =>
    json<Array<Record<string, unknown>>>(`/api/media?source=${encodeURIComponent(source)}&limit=${limit}`),
  mediaArtwork: (itemId: string, kind = "backdrop") =>
    `/api/media/artwork/${encodeURIComponent(itemId)}?kind=${encodeURIComponent(kind)}`,
  mediaLogo: (itemId: string, tmdbId?: string | null, mediaType = "movie") => {
    const params = new URLSearchParams({ media_type: mediaType });
    if (tmdbId) params.set("tmdb_id", tmdbId);
    return `/api/media/logo/${encodeURIComponent(itemId)}?${params.toString()}`;
  },
  testProvider: (name: string, draft?: Record<string, string>) =>
    json(`/api/settings/test/${name}`, {
      method: "POST",
      body: JSON.stringify(draft || {}),
    }),
  wallpaperImage: (layout: string, filename: string) =>
    `/api/wallpaper/image/${encodeURIComponent(layout)}/${encodeURIComponent(filename)}`,
  flag: (id: string, body: { pinned?: boolean; hidden?: boolean }) =>
    json<{ status: string; record: WallpaperRecord }>(`/api/gallery/${encodeURIComponent(id)}/flag`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  tonight: (layout?: string, exclude?: string) => {
    const params = new URLSearchParams();
    if (layout) params.set("layout", layout);
    if (exclude) params.set("exclude", exclude);
    return json<{
      status: Record<string, unknown>;
      queues: Array<{ id: string; label: string; count: number; titles: string[] }>;
      profile: string;
      motion: Record<string, unknown>;
    }>(`/api/tonight?${params.toString()}`);
  },
  dashboard: () => json<Record<string, unknown>>("/api/dashboard"),
  demoCatalog: () =>
    json<{
      ok: boolean;
      count: number;
      note: string;
      items: Array<{ title: string; license: string; artist: string; artwork_url: string }>;
    }>("/api/demo/catalog"),
  queues: (layout?: string) =>
    json<Array<{ id: string; label: string; count: number; titles: string[] }>>(
      layout ? `/api/queues?layout=${encodeURIComponent(layout)}` : "/api/queues",
    ),
};
