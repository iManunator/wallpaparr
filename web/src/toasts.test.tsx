import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ToastProvider, useToasts } from "./toasts";

function Probe() {
  const notify = useToasts();
  return (
    <div>
      <button type="button" onClick={() => notify("ok", "Connected to Jellyfin (Living Room)")}>
        succeed
      </button>
      <button type="button" onClick={() => notify("error", "Jellyfin connection failed: timeout")}>
        fail
      </button>
      <button type="button">outside</button>
    </div>
  );
}

describe("notice popups", () => {
  it("shows a success popup and dismisses with the close button", () => {
    render(
      <ToastProvider>
        <Probe />
      </ToastProvider>,
    );
    fireEvent.click(screen.getByRole("button", { name: "succeed" }));
    expect(screen.getByRole("status")).toHaveTextContent(/Connected to Jellyfin/);
    fireEvent.click(screen.getByRole("button", { name: "Close notification" }));
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("shows an error alert and dismisses on Escape and tap outside", () => {
    render(
      <ToastProvider>
        <Probe />
      </ToastProvider>,
    );
    fireEvent.click(screen.getByRole("button", { name: "fail" }));
    expect(screen.getByRole("alert")).toHaveTextContent(/Jellyfin connection failed/);
    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "fail" }));
    fireEvent.pointerDown(screen.getByRole("button", { name: "outside" }));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
