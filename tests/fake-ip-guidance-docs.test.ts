import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

const readDoc = (name: string): string =>
  readFileSync(new URL(`../docs/${name}`, import.meta.url), "utf8");

describe("ASR Fake-IP DNS troubleshooting docs", () => {
  it.each([
    ["tool-reference.md", /ASR Fake-IP DNS 诊断/, /等待用户明确选择/],
    ["tool-reference.en.md", /ASR Fake-IP DNS troubleshooting/, /wait for the user's explicit choice/i],
  ])("documents the bounded user-choice flow in %s", (name, heading, waitForChoice) => {
    const doc = readDoc(name);

    expect(doc).toContain("`ASR_FAKE_IP_DNS`");
    expect(doc).toMatch(heading);
    expect(doc).toContain("198.18.0.0/15");
    expect(doc).toContain("`+.bilivideo.com`");
    expect(doc).toContain("`+.bilivideo.cn`");
    expect(doc).toContain("`fake-ip-filter`");
    expect(doc).toContain("`redir-host`");
    expect(doc).toMatch(/TUN/i);
    expect(doc).toMatch(/Human Subtitle|人工字幕/);
    expect(doc).toMatch(/Bilibili AI (Subtitle|字幕)/);
    expect(doc).toMatch(/video description|视频简介/i);
    expect(doc).toMatch(/public DoH|公共 DoH/i);
    expect(doc).toMatch(waitForChoice);
  });
});
