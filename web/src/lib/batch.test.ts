import { describe, expect, it } from "vitest";
import { describeBatchFlags, effectiveSkipExisting } from "./batch";

describe("batch flags", () => {
  it("explains skip, replace, cleanup, and ids", () => {
    const skip = describeBatchFlags({ skip_existing: true, replace_existing: false, cleanup: false });
    expect(skip).toMatch(/Skip leaves titles/);
    const refresh = describeBatchFlags({
      skip_existing: true,
      replace_existing: false,
      refresh_status: true,
      cleanup: false,
    });
    expect(refresh).toMatch(/Refresh status re-bakes/);
    const replace = describeBatchFlags({
      skip_existing: true,
      replace_existing: true,
      cleanup: true,
      ids: ["demo-jf-1"],
      skip_ids: ["x"],
    });
    expect(replace).toMatch(/Replace overwrites/);
    expect(replace).toMatch(/skip is ignored/);
    expect(replace).toMatch(/Cleanup deletes/);
    expect(replace).toMatch(/Only 1 id/);
    expect(replace).toMatch(/1 id will be ignored/);
  });

  it("treats replace as winning over skip", () => {
    expect(effectiveSkipExisting(true, true)).toBe(false);
    expect(effectiveSkipExisting(true, false)).toBe(true);
  });
});
