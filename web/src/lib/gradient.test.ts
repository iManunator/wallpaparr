import { describe, expect, it } from "vitest";
import { cssGradient, hexAlpha, LOOK_PRESETS, stageOverlayStyle } from "./gradient";
import { emptyLayout } from "./layout";
import { errorToast, generateToast, providerToast } from "./messages";

describe("gradient css", () => {
  it("builds a linear gradient from stops", () => {
    const bg = emptyLayout().background;
    bg.gradient_type = "linear";
    bg.gradient_angle = 90;
    bg.gradient_opacity = 1;
    expect(cssGradient(bg)).toMatch(/linear-gradient\(90deg/);
    expect(hexAlpha("#ff0000", 0.5)).toBe("rgba(255, 0, 0, 0.5)");
  });

  it("includes vignette and edge fades on the stage", () => {
    const style = stageOverlayStyle({
      ...emptyLayout().background,
      gradient_opacity: 0.4,
      vignette: 0.5,
      overlay_opacity: 0.1,
    });
    expect(String(style.backgroundImage)).toMatch(/radial-gradient/);
    expect(String(style.backgroundImage)).toMatch(/linear-gradient/);
  });

  it("has cinematic look presets", () => {
    expect(LOOK_PRESETS.map((row) => row.id)).toEqual(expect.arrayContaining(["hero", "spotlight", "letterbox"]));
  });
});

describe("toast copy", () => {
  it("maps provider payloads", () => {
    expect(providerToast({ ok: true, message: "Connected to Jellyfin (Box)" })).toEqual({
      kind: "ok",
      text: "Connected to Jellyfin (Box)",
    });
    expect(providerToast({ ok: false, message: "Could not reach Jellyfin: nope" }).kind).toBe("error");
  });

  it("maps generate payloads", () => {
    expect(generateToast({ count: 2, message: "Created 2 stills for Netflix Hero." }).kind).toBe("ok");
    expect(generateToast({ count: 0, message: "No new stills.", warnings: ["x"] }).kind).toBe("info");
  });

  it("parses fastapi error JSON", () => {
    expect(errorToast(new Error('{"detail":"Layout not found"}'), "fail").text).toBe("Layout not found");
    expect(
      errorToast(
        new Error('{"detail":[{"loc":["body","limit"],"msg":"Input should be a valid integer"}]}'),
        "fail",
      ).text,
    ).toBe("Input should be a valid integer");
  });
});
