import { describe, expect, it } from "vitest";
import { formatOpsTime, queueBadges, TASTE_PRESETS } from "./queues";

describe("queue badges", () => {
  it("labels watch, seerr, pin, and video states", () => {
    expect(
      queueBadges({
        watch_state: "unwatched",
        library_state: "seerr_only",
        availability: "requestable",
        source: "jellyseerr",
        pinned: true,
        has_video: true,
      }),
    ).toEqual(["Pinned", "Unwatched", "Requestable", "Seerr", "VIDEO"]);
  });

  it("labels continue watching", () => {
    expect(
      queueBadges({
        watch_state: "partial",
        library_state: "in_library",
        source: "jellyfin",
        has_video: false,
      }),
    ).toEqual(["Partly watched"]);
  });

  it("labels watched titles", () => {
    expect(
      queueBadges({
        watch_state: "played",
        library_state: "in_library",
        source: "jellyfin",
        has_video: false,
      }),
    ).toEqual(["Watched"]);
  });

  it("formats ops recency", () => {
    expect(formatOpsTime(undefined)).toBe("never");
    expect(formatOpsTime(Date.now() / 1000 - 10)).toBe("just now");
    expect(TASTE_PRESETS.tonight.unwatched).toBe(30);
  });
});
