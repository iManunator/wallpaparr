import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { FullscreenViewer, type ViewerItem } from "./FullscreenViewer";
import { ToastProvider } from "./toasts";

const stillItem: ViewerItem = {
  id: "1",
  src: "/api/wallpaper/image/Netflix%20Hero/from.jpg",
  stillSrc: "/api/wallpaper/image/Netflix%20Hero/from.jpg",
  title: "From",
  subtitle: "2022 · Netflix Hero",
  watchState: "unwatched",
  hasVideo: false,
  videoSrc: null,
};

const videoItem: ViewerItem = {
  ...stillItem,
  id: "6",
  title: "Night Relay",
  src: "/api/wallpaper/image/Prime%20Cinematic/relay.jpg",
  stillSrc: "/api/wallpaper/image/Prime%20Cinematic/relay.jpg",
  videoSrc: "/api/wallpaper/image/Prime%20Cinematic/relay.mp4",
  hasVideo: true,
};

function renderViewer(item: ViewerItem) {
  return render(
    <ToastProvider>
      <FullscreenViewer items={[item]} index={0} onClose={() => undefined} onIndex={() => undefined} />
    </ToastProvider>,
  );
}

async function ready(title: string) {
  return screen.findByRole("dialog", { name: new RegExp(`${title} full screen`, "i") });
}

describe("gallery lightbox", () => {
  it("plays a baked sibling MP4 when has_video", async () => {
    const { container } = renderViewer(videoItem);
    const dialog = await ready("Night Relay");
    const video = container.querySelector("video") as HTMLVideoElement | null;
    expect(video).toBeTruthy();
    expect(video?.getAttribute("src")).toMatch(/relay\.mp4$/);
    expect(video?.loop).toBe(true);
    expect(video?.muted).toBe(true);
    expect(within(dialog).getByText("VIDEO")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Pause" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Close full screen" })).toBeInTheDocument();
  });

  it("shows the actual generated still image for a still-only item, with no simulated chrome", async () => {
    const { container } = renderViewer(stillItem);
    const dialog = await ready("From");
    const art = screen.getByRole("img", { name: /From artwork/i });
    expect(art.getAttribute("src")).toBe("/api/wallpaper/image/Netflix%20Hero/from.jpg");
    expect(art.className).not.toMatch(/motion-art/);
    expect(container.querySelector(".sample-chrome")).toBeNull();
    expect(within(dialog).getByText("IMAGE")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Pause" })).not.toBeInTheDocument();
    expect(container.querySelector("video")).toBeNull();
  });

  it("shows Seerr-only chrome next to the watch pill in the caption", async () => {
    renderViewer({
      ...stillItem,
      libraryState: "seerr_only",
      availability: "requestable",
      source: "jellyseerr",
    });
    await ready("From");
    expect(screen.getAllByText("Unwatched").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Seerr only").length).toBeGreaterThan(0);
  });

  it("falls back to the still image and toasts when VIDEO fails to load", async () => {
    const { container } = renderViewer(videoItem);
    await ready("Night Relay");
    const video = container.querySelector("video");
    expect(video).toBeTruthy();
    fireEvent.error(video as HTMLVideoElement);
    expect(await screen.findByRole("alert")).toHaveTextContent(/Could not play VIDEO/);
    expect(container.querySelector("video")).toBeNull();
    const art = screen.getByRole("img", { name: /Night Relay artwork/i });
    expect(art.getAttribute("src")).toBe("/api/wallpaper/image/Prime%20Cinematic/relay.jpg");
    expect(within(screen.getByRole("dialog")).getByText("IMAGE")).toBeInTheDocument();
  });
});
