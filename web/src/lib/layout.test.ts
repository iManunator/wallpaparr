import { describe, expect, it } from "vitest";
import {
  duplicateLayout,
  emptyLayout,
  normalizeLayout,
  removeLayer,
  reorderLayer,
  selectionAfterRemove,
  validateLayout,
} from "../lib/layout";
import { shouldSkipExisting } from "../lib/skip";
import { buildStatusQuery, parseYearRange, rememberShownPath } from "../lib/wallpaperQuery";

describe("layout validation", () => {
  it("accepts a named layout with layers", () => {
    expect(validateLayout(emptyLayout("Hero"))).toEqual([]);
  });

  it("rejects blank names and empty layers", () => {
    const layout = emptyLayout(" ");
    layout.name = " ";
    layout.layers = [];
    expect(validateLayout(layout).join(" ")).toMatch(/name/i);
  });

  it("duplicateLayout clears preset flags", () => {
    const copy = duplicateLayout({ ...emptyLayout("A"), preset: true, preset_id: "a" }, "B");
    expect(copy.name).toBe("B");
    expect(copy.preset).toBe(false);
  });

  it("normalizeLayout fills gradient defaults", () => {
    const layout = normalizeLayout({ name: "Hero", layers: emptyLayout().layers } as never);
    expect(layout.background.gradient_type).toBe("linear");
    expect(layout.background.vignette).toBeGreaterThanOrEqual(0);
    expect(layout.canvas_width).toBe(1920);
    expect(layout.title_display).toBe("auto");
    expect(layout.show_watch_badge).toBe(true);
    expect(layout.show_seerr_badge).toBe(true);
  });

  it("normalizeLayout preserves dna_revision", () => {
    const layout = normalizeLayout({ name: "Hero", dna_revision: 1 } as never);
    expect(layout.dna_revision).toBe(1);
  });

  it("normalizeLayout keeps watch badge off when explicitly disabled", () => {
    const layout = normalizeLayout({ name: "Hero", show_watch_badge: false } as never);
    expect(layout.show_watch_badge).toBe(false);
  });

  it("normalizeLayout keeps seerr badge off when explicitly disabled", () => {
    const layout = normalizeLayout({ name: "Hero", show_seerr_badge: false } as never);
    expect(layout.show_seerr_badge).toBe(false);
  });
});

describe("wallpaper query builder", () => {
  it("encodes rating, year, and age filters", () => {
    const url = buildStatusQuery({
      layout: "Prime Cinematic",
      sort: "rating",
      pool: "seerr_only",
      age_rating: "PG-13",
      min_year: "2020",
      max_year: "2025",
      min_rating: 8,
      max_rating: 9.5,
    });
    expect(url).toContain("age_rating=PG-13");
    expect(url).toContain("min_year=2020");
    expect(url).toContain("max_year=2025");
    expect(url).toContain("min_rating=8");
    expect(url).toContain("max_rating=9.5");
    expect(url).toContain("pool=seerr_only");
  });

  it("omits zero min rating and full-scale max rating", () => {
    const url = buildStatusQuery({ layout: "Hero", sort: "random", min_rating: 0, max_rating: 10 });
    expect(url).not.toContain("min_rating");
    expect(url).not.toContain("max_rating");
  });

  it("encodes Projectivy status params", () => {
    const url = buildStatusQuery({
      layout: "Netflix Hero",
      sort: "latest",
      pool: "unwatched",
      genre: "Sci-Fi",
      exclude: "northlight.jpg",
    });
    expect(url).toContain("/api/wallpaper/status?");
    expect(url).toContain("layout=Netflix+Hero");
    expect(url).toContain("sort=latest");
    expect(url).toContain("pool=unwatched");
    expect(url).toContain("exclude=northlight.jpg");
  });

  it("encodes taste profile and smart queue", () => {
    const url = buildStatusQuery({
      layout: "Projectivy Dock",
      sort: "random",
      profile: "tonight",
      queue: "unwatched",
    });
    expect(url).toContain("profile=tonight");
    expect(url).toContain("queue=unwatched");
  });

  it("parses year ranges", () => {
    expect(parseYearRange("2005-2010")).toEqual({ min: "2005", max: "2010" });
    expect(parseYearRange("2024")).toEqual({ min: "2024", max: "2024" });
  });

  it("keeps a no-repeat bag of recent paths", () => {
    expect(rememberShownPath(["a.jpg", "b.jpg"], "c.jpg", 2)).toEqual(["c.jpg", "a.jpg"]);
  });
});

describe("skip existing by media id", () => {
  it("skips matching jellyfin ids", () => {
    expect(
      shouldSkipExisting([{ title: "Old", jellyfin_id: "jf-1" }], { title: "New", jellyfin_id: "jf-1" }, true),
    ).toBe(true);
  });

  it("does not skip when disabled", () => {
    expect(
      shouldSkipExisting([{ title: "Old", jellyfin_id: "jf-1" }], { title: "New", jellyfin_id: "jf-1" }, false),
    ).toBe(false);
  });
});

describe("layer editing", () => {
  it("reorderLayer moves an item and leaves the rest in place", () => {
    expect(reorderLayer(["a", "b", "c"], 0, 1)).toEqual(["b", "a", "c"]);
    expect(reorderLayer(["a", "b", "c"], 2, -1)).toEqual(["a", "c", "b"]);
  });

  it("reorderLayer is a no-op past either end", () => {
    const layers = ["a", "b", "c"];
    expect(reorderLayer(layers, 0, -1)).toBe(layers);
    expect(reorderLayer(layers, 2, 1)).toBe(layers);
  });

  it("removeLayer drops only the targeted index", () => {
    expect(removeLayer(["a", "b", "c"], 1)).toEqual(["a", "c"]);
  });

  it("selectionAfterRemove shifts down past the removed index", () => {
    // Selected layer was after the removed one — its array position shifted.
    expect(selectionAfterRemove(3, 1, 4)).toBe(2);
  });

  it("selectionAfterRemove leaves selection alone when removal was after it", () => {
    expect(selectionAfterRemove(1, 3, 4)).toBe(1);
  });

  it("selectionAfterRemove clamps when the last layer is removed", () => {
    expect(selectionAfterRemove(2, 2, 2)).toBe(1);
  });

  it("selectionAfterRemove clamps to 0 when the list becomes empty", () => {
    expect(selectionAfterRemove(0, 0, 0)).toBe(0);
  });
});
