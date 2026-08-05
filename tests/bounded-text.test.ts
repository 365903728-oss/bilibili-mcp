import { describe, expect, it } from "vitest";
import {
  boundedRemoteText,
  boundedRemoteTextPreservingWhitespace,
  sanitizeRemoteText,
} from "../src/utils/bounded-text.js";

describe("boundedRemoteText unsafe code point removal", () => {
  it.each([
    ["C0 controls", "\u0000a\u0008b\u000e\u001fc", "abc"],
    ["C1 controls", "a\u0080b\u009fc", "abc"],
    ["zero-width and directional marks", "a\u200bb\u200cc\u200dd\u200ee\u200ff", "abcdef"],
    ["bidi embeddings and overrides", "a\u202ab\u202bc\u202cd\u202de\u202ef", "abcdef"],
    ["bidi isolates", "a\u2066b\u2067c\u2068d\u2069e", "abcde"],
    ["BOM", "\ufeffa\ufeff", "a"],
    ["unpaired surrogate", "a\ud800b", "ab"],
  ])("removes %s", (_case, input, expected) => {
    expect(boundedRemoteText(input, 512)).toBe(expected);
  });

  it("preserves CJK, emoji, and internal whitespace", () => {
    expect(boundedRemoteText("  中文\u0009emoji😀\u000a", 512)).toBe("中文\u0009emoji😀");
    expect(boundedRemoteTextPreservingWhitespace("\u000a中文 😀\u000a", 512)).toBe(
      "\u000a中文 😀\u000a",
    );
  });

  it("applies the byte budget after removing unsafe code points", () => {
    expect(boundedRemoteText("aaaa\u200bb", 5)).toBe("aaaab");
  });
});
describe("sanitizeRemoteText", () => {
  it("removes unsafe code points without truncation or whitespace changes", () => {
    const long = "中".repeat(20_000);
    expect(sanitizeRemoteText(`${long}\u202e\u200b\ufeff`)).toBe(long);
  });

  it("preserves tab, newline, CJK, and emoji", () => {
    expect(sanitizeRemoteText("中文\u0009emoji😀\u000a")).toBe("中文\u0009emoji😀\u000a");
  });

  it("returns an empty string for non-string input", () => {
    expect(sanitizeRemoteText(42)).toBe("");
    expect(sanitizeRemoteText(undefined)).toBe("");
  });
});
