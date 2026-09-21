import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { CHROME_PILL, CHROME_PILL_FALLBACK, CHROME_PILL_SAMPLE, keepWatchSlot } from "./chrome";

const cssPath = join(dirname(fileURLToPath(import.meta.url)), "../styles/app.css");

describe("chrome pill geometry contract", () => {
  it("documents equal padding, flex centering, and capsule radius", () => {
    const css = readFileSync(cssPath, "utf8");
    const pill = css.match(/\.chrome-pill\s*\{[^}]+\}/)?.[0] || "";
    expect(pill).toMatch(/display:\s*inline-flex/);
    expect(pill).toMatch(/align-items:\s*center/);
    expect(pill).toMatch(/justify-content:\s*center/);
    expect(pill).toMatch(/line-height:\s*1/);
    expect(pill).toMatch(new RegExp(`padding:\\s*${CHROME_PILL.padYEm}em\\s+${CHROME_PILL.padXEm}em`));
    expect(pill).toMatch(new RegExp(`min-height:\\s*${CHROME_PILL.minHeightEm}em`));
    expect(pill).toMatch(/border-radius:\s*999px/);
    expect(pill).toMatch(/box-sizing:\s*border-box/);
    const row = css.match(/\.chrome-pills\s*\{[^}]+\}/)?.[0] || "";
    expect(row).toMatch(/display:\s*inline-flex/);
    expect(row).toMatch(/align-items:\s*center/);
    expect(row).toMatch(new RegExp(`gap:\\s*${CHROME_PILL.gapEm}em`));
    const fallback = css.match(/\.chrome-pills-fallback\s*\{[^}]+\}/)?.[0] || "";
    expect(fallback).toMatch(new RegExp(`left:\\s*${CHROME_PILL_FALLBACK.leftPercent}%`));
    expect(fallback).toMatch(new RegExp(`top:\\s*${CHROME_PILL_FALLBACK.topPercent}%`));
    const sample = css.match(/\.chrome-pills-sample\s*\{[^}]+\}/)?.[0] || "";
    expect(sample).toMatch(new RegExp(`left:\\s*${CHROME_PILL_SAMPLE.leftPercent}%`));
    expect(sample).toMatch(new RegExp(`top:\\s*${CHROME_PILL_SAMPLE.topPercent}%`));
  });

  it("keeps the watch-slot chip when only Seerr chrome is on", () => {
    expect(keepWatchSlot(true, true, false)).toBe(true);
    expect(keepWatchSlot(false, true, false)).toBe(true);
    expect(keepWatchSlot(false, true, true)).toBe(false);
    expect(keepWatchSlot(false, false, false)).toBe(false);
    expect(keepWatchSlot(true, false, false)).toBe(true);
  });
});
