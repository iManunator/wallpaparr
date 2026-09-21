import { describe, expect, it } from "vitest";
import { seerrBadge, seerrKind } from "./seerr";

describe("seerr chrome", () => {
  it("labels seerr-only titles even when they are also requestable", () => {
    expect(seerrKind("seerr_only", "requestable", "jellyseerr")).toBe("seerr_only");
    expect(seerrBadge("seerr_only", "requestable", "jellyseerr")?.label).toBe("Seerr only");
  });

  it("labels requestable titles that are not in the library", () => {
    expect(seerrKind("not_in_library", "requestable", "tmdb")).toBe("seerr_only");
    expect(seerrKind("", "requestable", "tmdb")).toBe("requestable");
    expect(seerrBadge("", "not_available")?.label).toBe("Requestable");
  });

  it("labels on-seerr when the source is Seerr and the title is not in library", () => {
    expect(seerrKind("", "", "seerr")).toBe("on_seerr");
    expect(seerrBadge(undefined, undefined, "jellyseerr")?.label).toBe("On Seerr");
  });

  it("hides the chip for in-library titles", () => {
    expect(seerrBadge("in_library", "available", "jellyseerr")).toBeNull();
    expect(seerrBadge("in_library", "available", "jellyfin")).toBeNull();
  });
});
