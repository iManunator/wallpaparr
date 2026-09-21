import { describe, expect, it } from "vitest";
import { idleJob, isActiveJob, jobLabel, jobToast } from "./jobs";

describe("job progress helpers", () => {
  it("treats queued and running as active", () => {
    expect(isActiveJob(idleJob())).toBe(false);
    expect(isActiveJob({ ...idleJob(), status: "queued" })).toBe(true);
    expect(isActiveJob({ ...idleJob(), status: "running", done: 3, total: 12 })).toBe(true);
    expect(isActiveJob({ ...idleJob(), status: "done" })).toBe(false);
  });

  it("shows count and current title while running", () => {
    const label = jobLabel({
      ...idleJob(),
      kind: "generate",
      status: "running",
      done: 3,
      total: 12,
      current: "Northlight",
    });
    expect(label).toMatch(/3\/12/);
    expect(label).toMatch(/Northlight/);
  });

  it("toasts generate and motion results", () => {
    const gen = jobToast({
      ...idleJob(),
      kind: "generate",
      status: "done",
      message: "Created 2 stills for Netflix Hero.",
      created: ["Northlight", "Harbor Season"],
      result: { count: 2, message: "Created 2 stills for Netflix Hero." },
    });
    expect(gen.kind).toBe("ok");
    expect(gen.text).toMatch(/Created 2 stills/);

    const bake = jobToast({
      ...idleJob(),
      kind: "motion",
      status: "done",
      created: ["northlight.jpg"],
      result: { count: 1, generated: ["northlight.jpg"], message: "Baked parallax VIDEO for northlight.jpg." },
    });
    expect(bake.kind).toBe("ok");
    expect(bake.text).toMatch(/Baked parallax VIDEO/);

    const fail = jobToast({
      ...idleJob(),
      kind: "generate",
      status: "error",
      error: "A job is already running",
    });
    expect(fail.kind).toBe("error");
    expect(fail.text).toMatch(/already running/);
  });
});
