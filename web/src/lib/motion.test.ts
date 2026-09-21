import { describe, expect, it } from "vitest";
import {
  clampIntensity,
  defaultDuration,
  describeMotion,
  intensityFromPreset,
  motionPreviewVars,
  motionSeedKey,
  nearestMotionPreset,
  shouldPreferVideo,
  varyMotionProfile,
} from "./motion";

describe("motion options", () => {
  it("clamps intensity", () => {
    expect(clampIntensity(-1)).toBe(0);
    expect(clampIntensity(2)).toBe(1);
    expect(clampIntensity(0.4)).toBe(0.4);
  });

  it("describes parallax loops", () => {
    expect(describeMotion("parallax", 0.55, 6)).toMatch(/chrome stays locked/);
    expect(describeMotion("kenburns", 0.55, 6)).toMatch(/chrome locked/);
    expect(defaultDuration("cinematic")).toBe(15);
  });

  it("selects VIDEO vs IMAGE like the plugin", () => {
    expect(shouldPreferVideo({ preferMotion: true, hasVideo: true, fallbackStill: true })).toBe("video");
    expect(shouldPreferVideo({ preferMotion: true, hasVideo: false, fallbackStill: true })).toBe("image");
    expect(shouldPreferVideo({ preferMotion: false, hasVideo: true, fallbackStill: true })).toBe("image");
    expect(shouldPreferVideo({ preferMotion: true, hasVideo: false, fallbackStill: false })).toBe("none");
    expect(shouldPreferVideo({ preferMotion: false, hasVideo: true, fallbackStill: false })).toBe("video");
  });

  it("defaults duration from AppSettings, not quality tier", () => {
    expect(defaultDuration("light")).toBe(15);
    expect(defaultDuration("standard")).toBe(15);
    expect(defaultDuration("cinematic")).toBe(15);
  });

  it("maps intensity presets", () => {
    expect(intensityFromPreset("subtle")).toBe(0.16);
    expect(intensityFromPreset("balanced")).toBe(0.355);
    expect(intensityFromPreset("bold")).toBe(0.96);
    expect(nearestMotionPreset(0.9)).toBe("bold");
    expect(nearestMotionPreset(0.3)).toBe("balanced");
    expect(nearestMotionPreset(0.16)).toBe("subtle");
  });

  it("builds CSS motion preview variables that change with intensity", () => {
    const subtle = motionPreviewVars("parallax", 0.16, 16);
    const bold = motionPreviewVars("parallax", 0.96, 10);
    expect(Number(bold["--motion-zoom-to"])).toBeGreaterThan(Number(subtle["--motion-zoom-to"]));
    expect(Math.abs(parseFloat(bold["--motion-x"]))).toBeGreaterThan(Math.abs(parseFloat(subtle["--motion-x"])));
    expect(subtle["--motion-duration"]).toBe("16s");
  });

  it("cinematic zoom/pan matches the ffmpeg bake contract", () => {
    const parallax = motionPreviewVars("parallax", 0.55, 12);
    expect(parallax["--motion-zoom-from"]).toBe("1.04");
    expect(Number(parallax["--motion-zoom-to"])).toBeCloseTo(1 + 0.55 * 0.18, 4);
    expect(parallax["--motion-x"]).toBe("-2.64%");
    expect(parallax["--motion-delay"]).toBeUndefined();
    const kenburns = motionPreviewVars("kenburns", 0.55, 12);
    expect(kenburns["--motion-zoom-from"]).toBe("1.015");
    expect(Number(kenburns["--motion-zoom-to"])).toBeCloseTo(1 + 0.55 * 0.22, 4);
  });

  it("toggle off keeps the exact CSS path even with a seed", () => {
    const off = motionPreviewVars("parallax", 0.55, 12, { vary: false, seed: "demo-jf-1", preset: "cinematic" });
    const plain = motionPreviewVars("parallax", 0.55, 12);
    expect(off).toEqual(plain);
    expect(off["--motion-x"]).toBe("-2.64%");
  });

  it("toggle on uses the same seeded helper as the bake", () => {
    const a = varyMotionProfile(
      { style: "parallax", intensity: 0.55, duration: 12, preset: "cinematic" },
      { enabled: true, seed: "demo-jf-1" },
    );
    const b = varyMotionProfile(
      { style: "parallax", intensity: 0.55, duration: 12, preset: "cinematic" },
      { enabled: true, seed: "demo-jf-1" },
    );
    const c = varyMotionProfile(
      { style: "parallax", intensity: 0.55, duration: 12, preset: "cinematic" },
      { enabled: true, seed: "demo-jf-2" },
    );
    const off = varyMotionProfile(
      { style: "parallax", intensity: 0.55, duration: 12, preset: "cinematic" },
      { enabled: false, seed: "demo-jf-1" },
    );
    expect(a).toEqual(b);
    expect(a).not.toEqual(c);
    expect(off.intensity).toBe(0.55);
    expect(off.panXSign).toBe(1);
    expect(off.phase).toBe(0);
    expect(a.intensity).toBeGreaterThanOrEqual(0.4);
    expect(a.intensity).toBeLessThanOrEqual(0.72);
    const css = motionPreviewVars("parallax", 0.55, 12, { vary: true, seed: "demo-jf-1", preset: "cinematic" });
    const panPct = 4.8 * a.intensity * a.panScale;
    expect(css["--motion-x"]).toBe(`${(-panPct * a.panXSign).toFixed(2)}%`);
    expect(css["--motion-delay"]).toBe(`${(-(a.phase * 12)).toFixed(3)}s`);
    expect(motionSeedKey("demo-jf-1", "Northlight")).toBe("demo-jf-1");
    expect(a).toMatchObject({
      intensity: 0.5582,
      panXSign: -1,
      panYSign: 1,
      panYRatio: 0.1025,
      phase: 0.5727,
      zoomScale: 0.9996,
      panScale: 1.0543,
    });
    expect(css["--motion-x"]).toBe("2.82%");
    expect(css["--motion-y"]).toBe("0.29%");
    expect(css["--motion-zoom-to"]).toBe("1.1005");
    expect(css["--motion-delay"]).toBe("-6.872s");
  });
});
