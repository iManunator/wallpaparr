import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";

type GalleryFixture = {
  id: string;
  layout: string;
  filename: string;
  title: string;
  year: number;
  rating: number;
  genres: string[];
  official_rating: string;
  watch_state: string;
  library_state: string;
  source: string;
  jellyfin_id?: string;
  has_video: boolean;
  pinned: boolean;
  hidden: boolean;
};

const fromItem: GalleryFixture = {
  id: "1",
  layout: "Netflix Hero",
  filename: "from.jpg",
  title: "From",
  year: 2022,
  rating: 8.5,
  genres: ["Horror"],
  official_rating: "TV-MA",
  watch_state: "unwatched",
  library_state: "in_library",
  source: "jellyfin",
  jellyfin_id: "demo-jf-1",
  has_video: false,
  pinned: false,
  hidden: false,
};

const harborItem: GalleryFixture = {
  ...fromItem,
  id: "2",
  filename: "harbor.jpg",
  title: "Harbor Season",
  year: 2022,
  watch_state: "partial",
  pinned: true,
  hidden: false,
};

const relayItem: GalleryFixture = {
  ...fromItem,
  id: "3",
  filename: "relay.jpg",
  title: "Night Relay",
  year: 2021,
  watch_state: "unwatched",
  pinned: false,
  hidden: true,
};

const galleryItems: GalleryFixture[] = [];
let tonightServesVideo = false;

function seedGallery(items: GalleryFixture[]) {
  galleryItems.splice(0, galleryItems.length, ...items.map((item) => ({ ...item })));
}

function deleteMessage(deleted: GalleryFixture[], skipped: GalleryFixture[], includePins: boolean) {
  if (!deleted.length && !skipped.length) return "Gallery is already empty.";
  if (!deleted.length && skipped.length) {
    return `Kept ${skipped.length} pinned wallpaper${skipped.length === 1 ? "" : "s"}. Nothing else to delete.`;
  }
  const msg =
    deleted.length === 1 ? `Deleted “${deleted[0].title}”.` : `Deleted ${deleted.length} wallpapers.`;
  if (skipped.length && !includePins) {
    return `${msg} Kept ${skipped.length} pinned wallpaper${skipped.length === 1 ? "" : "s"}.`;
  }
  return msg;
}

seedGallery([fromItem]);

vi.stubGlobal(
  "fetch",
  vi.fn(async (input: RequestInfo, init?: RequestInit) => {
    const url = String(input);
    const method = (init?.method || "GET").toUpperCase();
    let body: unknown = [];
    if (url.includes("/api/jobs/latest")) {
      body = {
        id: null,
        kind: null,
        status: "idle",
        total: 0,
        done: 0,
        current: null,
        message: "",
        created: [],
        failed: [],
        skipped: [],
        error: null,
        result: null,
        percent: 0,
      };
    } else if (url.includes("/api/jobs") && method === "POST") {
      const payload = JSON.parse(String(init?.body || "{}")) as { kind?: string };
      if (payload.kind === "motion" || payload.kind === "generate-motion") {
        body = {
          id: "m1",
          kind: "motion",
          status: "done",
          total: 1,
          done: 1,
          current: null,
          message: "Baked parallax VIDEO for northlight.jpg on Netflix Hero (cinematic).",
          created: ["northlight.jpg"],
          failed: [],
          skipped: [],
          error: null,
          percent: 100,
          result: {
            status: "ok",
            generated: ["northlight.jpg"],
            count: 1,
            style: "parallax",
            message: "Baked parallax VIDEO for northlight.jpg on Netflix Hero (cinematic).",
          },
        };
      } else if (payload.kind === "cron") {
        body = {
          id: "c1",
          kind: "cron",
          status: "done",
          total: 1,
          done: 1,
          current: null,
          message: "Created 1 still for Netflix Hero (Northlight).",
          created: ["Northlight"],
          failed: [],
          skipped: [],
          error: null,
          percent: 100,
          result: { count: 1, created: ["Northlight"], message: "Created 1 still for Netflix Hero (Northlight)." },
        };
      } else {
        body = {
          id: "g1",
          kind: "generate",
          status: "done",
          total: 2,
          done: 2,
          current: null,
          message: "Created 2 stills for Netflix Hero (Northlight, Harbor Season).",
          created: ["Northlight", "Harbor Season"],
          failed: [],
          skipped: [],
          error: null,
          percent: 100,
          result: {
            count: 2,
            created: ["Northlight", "Harbor Season"],
            message: "Created 2 stills for Netflix Hero (Northlight, Harbor Season).",
          },
        };
      }
    } else if (url.includes("/api/gallery/") && url.includes("/flag") && method === "POST") {
      const id = decodeURIComponent(url.split("/api/gallery/")[1].split("/")[0]);
      const payload = JSON.parse(String(init?.body || "{}")) as { pinned?: boolean; hidden?: boolean };
      const rec = galleryItems.find((item) => item.id === id);
      if (rec) {
        if ("pinned" in payload) rec.pinned = Boolean(payload.pinned);
        if ("hidden" in payload) rec.hidden = Boolean(payload.hidden);
      }
      body = { status: "ok", record: rec || galleryItems[0] };
    } else if (url.includes("/api/gallery/delete-all") && method === "POST") {
      const payload = JSON.parse(String(init?.body || "{}")) as { include_pins?: boolean };
      const includePins = Boolean(payload.include_pins);
      const skipped = includePins ? [] : galleryItems.filter((item) => item.pinned);
      const deleted = includePins ? [...galleryItems] : galleryItems.filter((item) => !item.pinned);
      seedGallery(skipped);
      body = {
        status: "ok",
        message: deleteMessage(deleted, skipped, includePins),
        deleted: deleted.map((item) => item.id),
        titles: deleted.map((item) => item.title),
        skipped_pinned: skipped.map((item) => item.id),
        count: deleted.length,
        pinned_kept: skipped.length,
        include_pins: includePins,
        missing: [],
        errors: [],
      };
    } else if (url.includes("/api/gallery/delete") && method === "POST") {
      const payload = JSON.parse(String(init?.body || "{}")) as { ids?: string[]; all?: boolean; include_pins?: boolean };
      if (payload.all) {
        const includePins = Boolean(payload.include_pins);
        const skipped = includePins ? [] : galleryItems.filter((item) => item.pinned);
        const deleted = includePins ? [...galleryItems] : galleryItems.filter((item) => !item.pinned);
        seedGallery(skipped);
        body = {
          status: "ok",
          message: deleteMessage(deleted, skipped, includePins),
          deleted: deleted.map((item) => item.id),
          titles: deleted.map((item) => item.title),
          skipped_pinned: skipped.map((item) => item.id),
          count: deleted.length,
          pinned_kept: skipped.length,
          include_pins: includePins,
          missing: [],
          errors: [],
        };
      } else {
        const ids = new Set(payload.ids || []);
        const deleted = galleryItems.filter((item) => ids.has(item.id));
        const missing = [...ids].filter((id) => !galleryItems.some((item) => item.id === id));
        seedGallery(galleryItems.filter((item) => !ids.has(item.id)));
        body = {
          status: "ok",
          message: deleteMessage(deleted, [], true),
          deleted: deleted.map((item) => item.id),
          titles: deleted.map((item) => item.title),
          missing,
          count: deleted.length,
          errors: [],
        };
      }
    } else if (url.includes("/api/gallery/") && method === "DELETE") {
      const id = decodeURIComponent(url.split("/api/gallery/")[1].split("?")[0]);
      const found = galleryItems.find((item) => item.id === id);
      seedGallery(galleryItems.filter((item) => item.id !== id));
      body = {
        status: "ok",
        message: found ? `Deleted “${found.title}”.` : "Deleted 0 wallpapers.",
        deleted: found ? [id] : [],
        titles: found ? [found.title] : [],
        count: found ? 1 : 0,
        missing: found ? [] : [id],
        errors: [],
      };
    } else if (url.includes("/api/gallery")) {
      body = galleryItems;
    }
    if (url.includes("/api/media?")) {
      if (url.includes("jellyfin")) {
        body = [
          {
            title: "From",
            year: 2022,
            overview: "A town that will not let you leave.",
            rating: 8.5,
            genres: ["Horror", "Drama"],
            official_rating: "TV-MA",
            runtime: "52m",
            watch_state: "unwatched",
            library_state: "in_library",
            availability: "available",
            source: "jellyfin",
            jellyfin_id: "from1",
            backdrop_url: "http://jf:8096/Items/from1/Images/Backdrop",
          },
        ];
      } else {
        body = [
          {
            title: "Northlight",
            year: 2024,
            overview: "A cartographer maps a city that rearranges itself after dusk.",
            rating: 8.4,
            genres: ["Sci-Fi", "Mystery"],
            official_rating: "PG-13",
            runtime: "2h 11m",
            watch_state: "unwatched",
            library_state: "in_library",
            availability: "available",
            source: "jellyfin",
            jellyfin_id: "demo-jf-1",
          },
          {
            title: "Signal Country",
            year: 2023,
            overview: "A radio host in the desert starts receiving tomorrow's news.",
            rating: 7.6,
            genres: ["Thriller", "Sci-Fi"],
            official_rating: "TV-MA",
            runtime: "52m",
            watch_state: "unwatched",
            library_state: "seerr_only",
            availability: "requestable",
            source: "jellyseerr",
            jellyfin_id: "demo-jf-4",
          },
        ];
      }
    }
    if (url.includes("/api/settings/test/")) {
      body = { ok: true, message: "Connected to Jellyfin (Living Room)", server: "Living Room" };
    }
    if (url.includes("/api/generate")) {
      body = { count: 2, created: ["Northlight", "Harbor Season"], message: "Created 2 stills for Netflix Hero (Northlight, Harbor Season)." };
    }
    if (url.includes("/api/wallpaper/generate-motion")) {
      body = {
        status: "ok",
        generated: ["northlight.jpg"],
        count: 1,
        style: "parallax",
        message: "Baked parallax VIDEO for northlight.jpg on Netflix Hero (cinematic).",
      };
    }
    if (url.includes("/api/cron/run")) {
      body = { count: 1, created: ["Northlight"], message: "Created 1 still for Netflix Hero (Northlight)." };
    }
    if (url.includes("/api/layouts/list")) body = ["Netflix Hero", "Projectivy Dock"];
    if (url.includes("/api/layouts/load")) {
      body = {
        name: "Netflix Hero",
        canvas_width: 1920,
        canvas_height: 1080,
        background: {
          mode: "backdrop",
          color: "#000",
          fade_left: 0.4,
          fade_right: 0.05,
          fade_top: 0.08,
          fade_bottom: 0.3,
          fade_softness: 0.4,
          brightness: 1,
          gradient_type: "linear",
          gradient_angle: 90,
          gradient_opacity: 0.4,
          gradient_stops: [],
          vignette: 0.1,
          overlay_color: "#000000",
          overlay_opacity: 0,
        },
        layers: [
          {
            id: "title",
            slot: "title",
            x: 80,
            y: 80,
            font_size: 64,
            color: "#ffffff",
            font_weight: "bold",
            visible: true,
            align: "left",
          },
        ],
        title_display: "auto",
      };
    }
    if (url.includes("/api/tonight")) {
      const parsed = new URL(url, "http://localhost");
      const shuffled = Boolean(parsed.searchParams.get("exclude"));
      body = {
        status: {
          title: shuffled ? "Harbor Season" : "Northlight",
          imageUrl: shuffled
            ? "/api/wallpaper/image/Netflix%20Hero/harbor.jpg"
            : "/api/wallpaper/image/Netflix%20Hero/northlight.jpg",
          videoUrl: tonightServesVideo
            ? "/api/wallpaper/video/Netflix%20Hero/northlight.mp4"
            : null,
          mediaType: tonightServesVideo ? "video" : "image",
          queue: shuffled ? "continue_watching" : "unwatched",
          pinned: false,
          path: shuffled ? "harbor.jpg" : "northlight.jpg",
          watchState: shuffled ? "partial" : "unwatched",
          libraryState: "in_library",
          availability: "available",
          source: "jellyfin",
        },
        queues: [
          { id: "unwatched", label: "Unwatched", count: 2, titles: ["Northlight"] },
          { id: "continue_watching", label: "Continue watching", count: 1, titles: ["Harbor Season"] },
          { id: "seerr_trending", label: "Seerr trending", count: 1, titles: ["Relay"] },
        ],
        profile: "tonight",
        motion: { style: "parallax", preset: "cinematic", intensity: 0.55, light_leak: true, vary: true, seed: "demo-jf-1" },
        preview: {
          artworkUrl: shuffled ? "/api/media/artwork/demo-jf-2" : "/api/media/artwork/demo-jf-1",
          itemId: shuffled ? "demo-jf-2" : "demo-jf-1",
          layered: true,
        },
      };
    }
    if (url.includes("/api/dashboard")) {
      body = {
        ok: true,
        gallery: { count: 6, videos: 1, pinned: 0, hidden: 0 },
        cron: { jobs: 0, last: null, last_generate: null, errors: [] },
        providers: { demo: { configured: true } },
        motion: { preset: "cinematic", style: "parallax" },
        taste: { profile: "tonight" },
      };
    }
    if (url.includes("/api/settings") && !url.includes("/api/settings/test/")) {
      body = {
        public_base_url: "http://127.0.0.1:8787",
        timezone: "UTC",
        motion_wallpapers: true,
        motion_quality: "light",
        motion_style: "parallax",
        motion_intensity: 0.55,
        motion_duration: null,
        motion_fps: 30,
        overwrite_existing: false,
        editor_theme: "cinema",
        motion_preset: "cinematic",
        light_leak: true,
        motion_vary: true,
        taste_profile: "tonight",
        overlays_enabled: false,
        jellyfin: {},
        jellyseerr: {},
        tmdb: {},
        cron_jobs: [],
        title_display: "auto",
      };
    }
    return {
      ok: true,
      json: async () => body,
      text: async () => JSON.stringify(body),
    };
  }),
);

class ProbeImage {
  onload: ((ev?: Event) => void) | null = null;
  onerror: ((ev?: Event) => void) | null = null;
  naturalWidth = 900;
  naturalHeight = 140;
  set src(value: string) {
    const ok = String(value).includes("demo-jf-1");
    queueMicrotask(() => {
      if (ok) this.onload?.(new Event("load"));
      else this.onerror?.(new Event("error"));
    });
  }
}
vi.stubGlobal("Image", ProbeImage);

describe("Tonight page", () => {
  beforeEach(() => {
    tonightServesVideo = false;
  });

  it("tells a one-pick story with outcome-labeled primary actions", async () => {
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Tonight" })).toBeInTheDocument();
    expect(screen.getByText(/next wallpaper Projectivy will show/i)).toBeInTheDocument();
    expect(screen.getAllByText(/taste:tonight/).length).toBeGreaterThan(0);
    expect(screen.getByText("Up next")).toBeInTheDocument();
    expect((await screen.findAllByText("Northlight")).length).toBeGreaterThan(0);

    const stage = screen.getByLabelText("Projectivy home screen preview");
    const art = stage.querySelector("img");
    expect(art?.className).toMatch(/motion-art/);
    expect(art?.getAttribute("src") || "").toMatch(/artwork/);
    expect(stage.querySelector(".tv-hero-meta")?.closest(".stage-fg")).toBeTruthy();
    expect(art?.closest(".stage-bg")).toBeTruthy();
    expect(stage.querySelector(".chrome-pills")).toBeTruthy();
    expect(document.querySelector(".tonight-hero")).toBeTruthy();
    expect(screen.getAllByText("Northlight").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Unwatched").length).toBeGreaterThan(0);

    const actions = screen.getByRole("group", { name: "Tonight actions" });
    expect(within(actions).getByRole("button", { name: "Open in editor" })).toBeInTheDocument();
    expect(within(actions).getByRole("button", { name: "Edit tonight taste" })).toBeInTheDocument();
    expect(within(actions).getByRole("button", { name: "Open gallery" })).toBeInTheDocument();
    expect(within(actions).queryByRole("button", { name: "Netflix Hero" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Bake motion for this layout" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Shuffle tonight" })).not.toBeInTheDocument();
    expect(screen.queryByRole("group", { name: "Launcher look" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /Taste/ })).not.toBeInTheDocument();

    const intensity = screen.getByRole("group", { name: "Preview intensity" });
    expect(within(intensity).getByRole("button", { name: "Cinematic" })).toBeInTheDocument();
    expect(screen.getByText(/Changes this CSS preview only/i)).toBeInTheDocument();
    expect(screen.getByText(/30% Unwatched/)).toBeInTheDocument();
    expect(screen.getAllByText(/Seerr trending/).length).toBeGreaterThan(0);
  });

  it("does not repeat the movie name once the baked VIDEO already shows it", async () => {
    tonightServesVideo = true;
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Tonight" })).toBeInTheDocument();
    const stage = screen.getByLabelText("Projectivy home screen preview");
    expect(stage.querySelector("video")).toBeTruthy();
    // Baked VIDEO plays clean — no simulated launcher chrome on top of it.
    expect(stage.querySelector(".tv-chrome")).toBeNull();
    expect(stage.querySelector(".tv-hero-meta")).toBeNull();
    expect(stage.querySelector(".chrome-pills")).toBeNull();
    expect(screen.getByText("VIDEO")).toBeInTheDocument();
    expect(screen.queryByText("Northlight")).not.toBeInTheDocument();
    expect(screen.getByText(/Baked VIDEO is what Projectivy will play/i)).toBeInTheDocument();
  });

  it("adjusts the preview intensity and opens the editor on the tonight layout", async () => {
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Tonight" })).toBeInTheDocument();
    expect((await screen.findAllByText("Northlight")).length).toBeGreaterThan(0);
    const stage = screen.getByLabelText("Projectivy home screen preview");
    expect(stage.querySelector("img")?.style.getPropertyValue("--motion-duration")).toBe("15s");
    const beforeZoom = stage.querySelector("img")?.style.getPropertyValue("--motion-zoom-to");
    fireEvent.click(screen.getByRole("button", { name: "Bold" }));
    expect(stage.querySelector("img")?.style.getPropertyValue("--motion-duration")).toBe("15s");
    expect(stage.querySelector("img")?.style.getPropertyValue("--motion-zoom-to")).not.toBe(beforeZoom);

    fireEvent.click(screen.getByRole("button", { name: "Open in editor" }));
    expect(await screen.findByRole("heading", { name: "Layout editor" })).toBeInTheDocument();
  });

  it("sends taste editing to Settings without exposing generate knobs", async () => {
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Tonight" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Edit tonight taste" }));
    expect(await screen.findByRole("heading", { name: "Settings" })).toBeInTheDocument();
    expect(screen.getByText(/Taste profile/i)).toBeInTheDocument();
  });

  it("links to the gallery from tonight", async () => {
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Tonight" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Open gallery" }));
    expect(await screen.findByRole("heading", { name: "Gallery" })).toBeInTheDocument();
  });
});

describe("App smoke", () => {
  beforeEach(() => {
    seedGallery([fromItem]);
  });

  it("renders tonight preview and can open the gallery", async () => {
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Tonight" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Wallpaparr" })).toBeInTheDocument();
    expect(screen.getAllByText("Northlight").length).toBeGreaterThan(0);
    const tonightStage = screen.getByLabelText("Projectivy home screen preview");
    const tonightArt = tonightStage.querySelector("img");
    expect(tonightArt?.className).toMatch(/motion-art/);
    expect(tonightArt?.getAttribute("src") || "").toMatch(/artwork/);
    expect(tonightStage.querySelector(".tv-hero-meta")?.closest(".stage-fg")).toBeTruthy();
    expect(tonightArt?.closest(".stage-bg")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Open in editor" })).toBeInTheDocument();
    expect(screen.getAllByText("Unwatched").length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: "Gallery" }));
    expect(await screen.findByRole("heading", { name: "Gallery" })).toBeInTheDocument();
    expect(screen.getByText(/1 wallpaper/)).toBeInTheDocument();
    expect(screen.getByText(/0 selected/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Select all" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Delete selected" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Delete all" })).toBeInTheDocument();
    expect(screen.getAllByText("Unwatched").length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "Pin" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Never show" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Delete" })).toBeInTheDocument();
    expect(screen.getByLabelText("Select From")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /View From full screen/i }));
    expect(screen.getByRole("dialog", { name: /From full screen/i })).toBeInTheDocument();
    const lightboxArt = screen.getByRole("img", { name: /From artwork/i });
    expect(lightboxArt.className).not.toMatch(/motion-art/);
    expect(lightboxArt.closest(".stage-bg")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Pause" })).not.toBeInTheDocument();
    expect(screen.getByText("IMAGE")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Delete" }).length).toBeGreaterThan(1);
    fireEvent.click(screen.getByRole("button", { name: "Close full screen" }));
    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    const confirm = screen.getByRole("dialog", { name: /Delete “From”/i });
    expect(confirm).toHaveTextContent(/cannot be undone/i);
    fireEvent.click(within(confirm).getByRole("button", { name: "Delete" }));
    expect((await screen.findAllByText(/Deleted/)).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: "Editor" }));
    expect(await screen.findByRole("heading", { name: "Layout editor" })).toBeInTheDocument();
    expect(await screen.findByRole("img", { name: /Northlight artwork/i })).toBeInTheDocument();
    const art = screen.getByRole("img", { name: /Northlight artwork/i });
    expect(art.className).toMatch(/motion-art/);
    expect(art.closest(".stage-bg")).toBeTruthy();
    expect(document.querySelector(".stage-frame.editor-stage")).toBeTruthy();
    expect(screen.getByLabelText("Demo preview")).toBeInTheDocument();
    expect(screen.getByLabelText("Title display")).toBeInTheDocument();
    expect(await screen.findByRole("img", { name: /Northlight logo/i })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /Northlight logo/i }).closest(".stage-fg")).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Title display"), { target: { value: "text" } });
    expect(screen.queryByRole("img", { name: /Northlight logo/i })).not.toBeInTheDocument();
    expect(screen.getByLabelText("Gradient type")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Motion on" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Watch badge" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Seerr badge" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Bake motion for this layout" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Status Focus" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Full screen" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Generate" }));
    expect(await screen.findByRole("heading", { name: "Generate" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Show advanced options" }));
    expect(screen.getByText(/Skip leaves titles/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Vary motion slightly per wallpaper/i)).toBeChecked();
    fireEvent.click(screen.getByRole("button", { name: "Run batch" }));
    expect((await screen.findAllByText(/Created 2 stills/)).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: "Bake motion for this layout" }));
    expect((await screen.findAllByText(/Baked parallax VIDEO/)).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: "Dashboard" }));
    expect(await screen.findByRole("heading", { name: "Health" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Settings" }));
    expect(await screen.findByRole("heading", { name: "Settings" })).toBeInTheDocument();
    expect(screen.getByText(/Taste profile/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Show advanced settings" }));
    expect(screen.getByLabelText("Default title display")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Overlay widgets/i })).toBeInTheDocument();
    expect(screen.getByText(/Intensity preset/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Vary motion slightly per wallpaper/i)).toBeChecked();
    expect(screen.getByLabelText("Schedule 1 layout")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add cron job" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Run now" }));
    expect((await screen.findAllByText(/Created 1 still/)).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: "Test Jellyfin" }));
    expect((await screen.findAllByText(/Connected to Jellyfin/)).length).toBeGreaterThan(0);
  });

  it("clamps generate limit to 200 before posting a job", async () => {
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Generate" }));
    expect(await screen.findByRole("heading", { name: "Generate" })).toBeInTheDocument();
    fireEvent.change(screen.getByDisplayValue("8"), { target: { value: "5000" } });
    const fetchMock = vi.mocked(fetch);
    const before = fetchMock.mock.calls.length;
    fireEvent.click(screen.getByRole("button", { name: "Run batch" }));
    expect((await screen.findAllByText(/Created 2 stills/)).length).toBeGreaterThan(0);
    const posted = fetchMock.mock.calls.slice(before).flatMap(([, init]) => {
      if (!init || String(init.method || "").toUpperCase() !== "POST") return [];
      try {
        return [JSON.parse(String(init.body || "{}"))];
      } catch {
        return [];
      }
    });
    const generate = posted.find((payload) => payload.kind === "generate");
    expect(generate?.limit).toBe(200);
  });
});

async function openGallery() {
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Gallery" }));
  expect(await screen.findByRole("heading", { name: "Gallery" })).toBeInTheDocument();
}

describe("gallery delete UX", () => {
  beforeEach(() => {
    seedGallery([fromItem, harborItem, relayItem]);
  });

  it("selects all visible stills, shows the count, and cancels delete selected", async () => {
    await openGallery();
    expect(screen.getByText(/2 wallpaper/)).toBeInTheDocument();
    expect(screen.getByText(/0 selected/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Select all" }));
    expect(screen.getByText(/2 selected/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Delete selected" }));
    const dialog = screen.getByRole("dialog", { name: "Delete selected?" });
    expect(dialog).toHaveTextContent(/Permanently delete 2 wallpapers/);
    expect(dialog).toHaveTextContent(/cannot be undone/i);
    expect(dialog).toHaveTextContent(/1 pinned wallpaper/);
    fireEvent.click(within(dialog).getByRole("button", { name: "Cancel" }));
    expect(screen.queryByRole("dialog", { name: "Delete selected?" })).not.toBeInTheDocument();
    expect(screen.getByText("From")).toBeInTheDocument();
    expect(screen.getByText("Harbor Season")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Clear selection" }));
    expect(screen.getByText(/0 selected/)).toBeInTheDocument();
  });

  it("deletes the selection after confirm and toasts success", async () => {
    await openGallery();
    fireEvent.click(screen.getByLabelText("Select From"));
    fireEvent.click(screen.getByRole("button", { name: "Delete selected" }));
    fireEvent.click(within(screen.getByRole("dialog", { name: /Delete “From”/i })).getByRole("button", { name: "Delete" }));
    expect(await screen.findByRole("status")).toHaveTextContent(/Deleted “From”/);
    expect(screen.queryByText("From")).not.toBeInTheDocument();
    expect(screen.getByText("Harbor Season")).toBeInTheDocument();
  });

  it("delete all skips pins by default and keeps pin / never-show actions nearby", async () => {
    await openGallery();
    expect(screen.getByRole("button", { name: "Pin" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Unpin" })).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Never show" }).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: "Delete all" }));
    const dialog = screen.getByRole("dialog", { name: "Clear gallery?" });
    expect(dialog).toHaveTextContent(/Permanently delete 2 wallpapers/);
    expect(dialog).toHaveTextContent(/never-show/);
    expect(dialog).toHaveTextContent(/cannot be undone/i);
    expect(dialog).toHaveTextContent(/1 pinned wallpaper will be kept/);
    fireEvent.click(within(dialog).getByRole("button", { name: "Delete 2 unpinned" }));
    expect(await screen.findByRole("status")).toHaveTextContent(/Kept 1 pinned wallpaper/);
    expect(screen.queryByText("From")).not.toBeInTheDocument();
    expect(screen.getByText("Harbor Season")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Unpin" })).toBeInTheDocument();
  });

  it("offers an explicit delete-all including pins danger option", async () => {
    await openGallery();
    fireEvent.click(screen.getByRole("button", { name: "Delete all" }));
    const dialog = screen.getByRole("dialog", { name: "Clear gallery?" });
    fireEvent.click(within(dialog).getByRole("button", { name: "Delete all 3 including 1 pin" }));
    expect(await screen.findByRole("status")).toHaveTextContent(/Deleted 3 wallpapers/);
    expect(screen.getByText(/No wallpapers yet/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Delete all" })).toBeDisabled();
  });

  it("shows an empty gallery and keeps delete all disabled", async () => {
    seedGallery([]);
    await openGallery();
    expect(screen.getByText(/No wallpapers yet/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Delete all" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Select all" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Delete selected" })).toBeDisabled();
    expect(screen.getByText(/0 wallpaper/)).toBeInTheDocument();
  });
});

