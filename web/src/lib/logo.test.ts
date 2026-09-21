import { describe, expect, it } from "vitest";
import { clampLogoRect, normalizeTitleDisplay, prefersLogo, PROJECTIVY_SAFE, smartResizeLogo, tagShift } from "./logo";

describe("title display", () => {
  it("normalizes unknown values to auto", () => {
    expect(normalizeTitleDisplay("auto")).toBe("auto");
    expect(normalizeTitleDisplay("logo")).toBe("logo");
    expect(normalizeTitleDisplay("text")).toBe("text");
    expect(normalizeTitleDisplay("nope")).toBe("auto");
  });

  it("prefers a logo unless the mode is text", () => {
    expect(prefersLogo("auto")).toBe(true);
    expect(prefersLogo("logo")).toBe(true);
    expect(prefersLogo("text")).toBe(false);
  });
});

describe("smart resize and safe zone", () => {
  it("shrinks tall logos more than wide ones", () => {
    const wide = smartResizeLogo(2400, 200);
    expect(wide.width).toBeLessThanOrEqual(1200);
    const tall = smartResizeLogo(200, 800);
    expect(tall.height).toBeLessThanOrEqual(Math.round(450 * 0.6));
  });

  it("keeps the logo inside Projectivy dock / clock margins", () => {
    const box = clampLogoRect(-20, 0, 400, 120, 1920, 1080);
    expect(box.x).toBeGreaterThanOrEqual(PROJECTIVY_SAFE.left);
    expect(box.y).toBeGreaterThanOrEqual(PROJECTIVY_SAFE.top);
    const low = clampLogoRect(1800, 1000, 400, 200, 1920, 1080);
    expect(low.x + low.width).toBeLessThanOrEqual(1920 - PROJECTIVY_SAFE.right);
    expect(low.y + low.height).toBeLessThanOrEqual(1080 - PROJECTIVY_SAFE.bottom);
  });

  it("keeps padding between logo and tags", () => {
    expect(tagShift(70, 180, 220, 25)).toBe(55);
    expect(tagShift(70, 80, 220, 25)).toBe(0);
  });
});
