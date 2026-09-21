import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ChromePills } from "./ChromePills";

describe("ChromePills", () => {
  it("renders watch and Seerr-only together", () => {
    render(
      <ChromePills
        watchState="unwatched"
        libraryState="seerr_only"
        availability="requestable"
        source="jellyseerr"
      />,
    );
    expect(screen.getByText("Unwatched").className).toMatch(/chrome-pill/);
    expect(screen.getByText("Seerr only").className).toMatch(/badge-seerr/);
  });

  it("hides Seerr chrome when the title is in the library", () => {
    render(
      <ChromePills watchState="partial" libraryState="in_library" availability="available" source="jellyfin" />,
    );
    expect(screen.getByText("Partly watched")).toBeTruthy();
    expect(screen.queryByText("Seerr only")).toBeNull();
    expect(screen.queryByText("Requestable")).toBeNull();
  });

  it("respects show flags", () => {
    const { rerender } = render(
      <ChromePills
        watchState="unwatched"
        libraryState="seerr_only"
        availability="requestable"
        showWatch={false}
        showSeerr
      />,
    );
    expect(screen.queryByText("Unwatched")).toBeNull();
    expect(screen.getByText("Seerr only")).toBeTruthy();
    rerender(
      <ChromePills
        watchState="unwatched"
        libraryState="seerr_only"
        availability="requestable"
        showWatch
        showSeerr={false}
      />,
    );
    expect(screen.getByText("Unwatched")).toBeTruthy();
    expect(screen.queryByText("Seerr only")).toBeNull();
  });
});
