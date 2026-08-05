import fs from "node:fs";
import { describe, expect, it } from "vitest";

describe("publish workflow action integrity", () => {
  it("pins every third-party action to a full immutable commit SHA", () => {
    const workflow = fs.readFileSync(
      new URL("../.github/workflows/publish.yml", import.meta.url),
      "utf8",
    );
    const actionUses = [
      ...workflow.matchAll(/^\s*(?:-\s*)?uses:\s*([^\s#]+).*$/gm),
    ]
      .map((match) => match[1])
      .filter((value) => !value.startsWith("./"));

    expect(actionUses.length).toBeGreaterThan(0);
    for (const action of actionUses) {
      expect(action).toMatch(
        /^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+@[0-9a-f]{40}$/,
      );
    }
  });
});
