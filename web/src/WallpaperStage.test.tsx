import type { CSSProperties } from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SampleLockedChrome, WallpaperStage } from "./WallpaperStage";

describe("WallpaperStage layers", () => {
  it("animates the background image and keeps chrome in the foreground", () => {
    render(
      <WallpaperStage
        artSrc="/art.jpg"
        artAlt="Backdrop"
        motionOn
        motionVars={{ "--motion-duration": "8s" } as CSSProperties}
        lightLeak
      >
        <SampleLockedChrome title="Northlight" />
      </WallpaperStage>,
    );
    const art = screen.getByRole("img", { name: "Backdrop" });
    expect(art.className).toMatch(/motion-art/);
    expect(art.closest(".stage-bg")).toBeTruthy();
    expect(art.closest(".stage-fg")).toBeNull();
    const title = screen.getByText("Northlight");
    expect(title.closest(".stage-fg")).toBeTruthy();
    expect(title.closest(".stage-bg")).toBeNull();
    expect(title.className).not.toMatch(/motion-art/);
    expect(screen.getByText("Unwatched").closest(".stage-fg")).toBeTruthy();
    expect(screen.getByText("Unwatched").className).toMatch(/chrome-pill/);
    expect(screen.getByText("Unwatched").closest(".chrome-pills")).toBeTruthy();
    expect(screen.getByText("Unwatched").closest(".chrome-pills-sample")).toBeTruthy();
    expect(document.querySelector(".stage-frame")).toBeTruthy();
    expect(document.querySelector(".motion-leak")?.closest(".stage-bg")).toBeTruthy();
  });

  it("does not Ken-Burns a baked VIDEO element", () => {
    const { container } = render(
      <WallpaperStage videoSrc="/loop.mp4" artSrc="/art.jpg" artAlt="Backdrop" motionOn>
        <span className="locked">Title</span>
      </WallpaperStage>,
    );
    expect(container.querySelector("video")).toBeTruthy();
    expect(container.querySelector(".motion-art")).toBeNull();
    expect(screen.getByText("Title").closest(".stage-fg")).toBeTruthy();
  });

  it("shows Seerr-only chrome next to watch when the title is requestable", () => {
    render(
      <WallpaperStage artSrc="/art.jpg" artAlt="Backdrop">
        <SampleLockedChrome
          title="Signal Country"
          watchState="unwatched"
          libraryState="seerr_only"
          availability="requestable"
          source="jellyseerr"
        />
      </WallpaperStage>,
    );
    const seerr = screen.getByText("Seerr only");
    expect(seerr.closest(".stage-fg")).toBeTruthy();
    expect(seerr.className).toMatch(/badge-seerr/);
    expect(seerr.closest(".chrome-pills")?.textContent).toMatch(/Unwatched/);
  });

  it("omits Seerr chrome for in-library titles", () => {
    render(
      <WallpaperStage artSrc="/art.jpg" artAlt="Backdrop">
        <SampleLockedChrome title="Northlight" libraryState="in_library" availability="available" source="jellyfin" />
      </WallpaperStage>,
    );
    expect(screen.getByText("Unwatched")).toBeTruthy();
    expect(screen.queryByText("Seerr only")).toBeNull();
    expect(screen.queryByText("Requestable")).toBeNull();
    expect(screen.queryByText("On Seerr")).toBeNull();
  });
});
