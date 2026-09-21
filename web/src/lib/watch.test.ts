import { describe, expect, it } from "vitest";
import { badgeClass, normalizeWatchState, watchBadge } from "./watch";

describe("watch badges", () => {
  it("normalizes jellyfin and demo aliases", () => {
    expect(normalizeWatchState("unplayed")).toBe("unwatched");
    expect(normalizeWatchState("in-progress")).toBe("partial");
    expect(normalizeWatchState("played")).toBe("watched");
    expect(normalizeWatchState("")).toBeNull();
  });

  it("returns distinct labels for the three states", () => {
    expect(watchBadge("unwatched")?.label).toBe("Unwatched");
    expect(watchBadge("partial")?.label).toBe("Partly watched");
    expect(watchBadge("watched")?.label).toBe("Watched");
    expect(watchBadge("unwatched")?.color).not.toBe(watchBadge("watched")?.color);
  });

  it("styles watch and video pills", () => {
    expect(badgeClass("Unwatched")).toContain("unwatched");
    expect(badgeClass("Partly watched")).toContain("partial");
    expect(badgeClass("Continue")).toContain("partial");
    expect(badgeClass("Watched")).toContain("watched");
    expect(badgeClass("VIDEO")).toContain("badge-video");
    expect(badgeClass("Seerr only")).toContain("seerr_only");
    expect(badgeClass("Requestable")).toContain("requestable");
    expect(badgeClass("Pinned")).toContain("badge");
  });
});
