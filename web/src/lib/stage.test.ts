import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { STAGE_ASPECT, fitStageContain, stageAspectRatio, stageOverflowsParent } from "./stage";

const cssPath = join(dirname(fileURLToPath(import.meta.url)), "../styles/app.css");

describe("16:9 stage contain", () => {
  it("never exceeds parent width or remaining viewport height", () => {
    const phone = { width: 358, height: 844 };
    const fitted = fitStageContain(phone.width, phone.height, 280);
    expect(stageOverflowsParent(fitted, { width: phone.width, height: phone.height })).toBe(false);
    expect(fitted.width).toBeLessThanOrEqual(phone.width);
    expect(Math.abs(stageAspectRatio(fitted) - STAGE_ASPECT)).toBeLessThan(0.01);

    const desktop = fitStageContain(1100, 900, 288);
    expect(desktop.width).toBeLessThanOrEqual(1100);
    expect(desktop.height).toBeLessThanOrEqual(900 - 288);
    expect(stageOverflowsParent(desktop, { width: 1100, height: 900 })).toBe(false);
  });

  it("shrinks to viewport height on a wide but short panel", () => {
    const wide = fitStageContain(1600, 700, 220);
    expect(wide.width).toBeLessThan(1600);
    expect(wide.height).toBeLessThanOrEqual(700 * 0.68 + 0.5);
    expect(Math.abs(stageAspectRatio(wide) - STAGE_ASPECT)).toBeLessThan(0.01);
  });

  it("documents the CSS contain approach (no page blowout)", () => {
    const css = readFileSync(cssPath, "utf8");
    expect(css).toMatch(/--stage-max-height/);
    expect(css).toMatch(/width:\s*min\(100%,\s*calc\(var\(--stage-max-height\) \* 16 \/ 9\)\)/);
    expect(css).toMatch(/\.stage-fg\s*\{[^}]*transform:\s*none/);
    expect(css).toMatch(/\.stage-bg\s*\{[^}]*overflow:\s*hidden/);
    expect(css).toMatch(/\.motion-art\s*\{/);
    expect(css).toMatch(/\.tonight-hero\s*\{[^}]*overflow:\s*hidden/);
    const fgBlock = css.match(/\.stage-fg\s*\{[^}]+\}/)?.[0] || "";
    expect(fgBlock).toMatch(/transform:\s*none/);
    expect(fgBlock).not.toMatch(/animation:\s*wallpaparr-kenburns/);
  });
});
