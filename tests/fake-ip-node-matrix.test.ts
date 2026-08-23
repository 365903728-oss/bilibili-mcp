import fs from "node:fs";
import { describe, expect, it } from "vitest";

const packageJson = JSON.parse(
  fs.readFileSync(new URL("../package.json", import.meta.url), "utf8"),
) as { scripts?: Record<string, string> };
const verifyWorkflow = fs.readFileSync(
  new URL("../.github/workflows/verify.yml", import.meta.url),
  "utf8",
);

describe("Fake-IP Node compatibility gate", () => {
  it("defines the focused DNS, download aggregation, and MCP error suite", () => {
    expect(packageJson.scripts?.["test:fake-ip"]).toBe(
      "vitest run tests/pinned-https.test.ts tests/asr-transcription.test.ts tests/server-error-next-steps.test.ts",
    );
  });

  it("runs the focused suite on Node 20, 22, and 25 before Required passes", () => {
    expect(verifyWorkflow).toContain("fake_ip_node:");
    expect(verifyWorkflow).toContain("node-version: [20, 22, 25]");
    expect(verifyWorkflow).toContain("npm run test:fake-ip");
    expect(verifyWorkflow).toMatch(/required:[\s\S]*needs:[\s\S]*- fake_ip_node/);
    expect(verifyWorkflow).toContain("FAKE_IP_NODE_RESULT:");
  });
});
