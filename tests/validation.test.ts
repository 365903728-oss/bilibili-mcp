import { describe, expect, it } from "vitest";
import {
  validateBoolean,
  validateBVInput,
  validateCommentLimit,
  validateCommentSort,
  validateContextSegments,
  validateDetailLevel,
  validateLanguage,
  validateLength,
  validateMaxMatches,
  validatePage,
  validateQuery,
  validateSearchLimit,
  validateTimestampRange,
} from "../src/utils/validation.js";

describe("validateBVInput", () => {
  it("accepts plain BV id", () => {
    expect(() => validateBVInput("BV1T6PQzQErF")).not.toThrow();
  });

  it("accepts Bilibili video URL", () => {
    expect(() =>
      validateBVInput("https://www.bilibili.com/video/BV1T6PQzQErF/"),
    ).not.toThrow();
  });

  it("accepts b23.tv short link", () => {
    expect(() => validateBVInput("https://b23.tv/abc123")).not.toThrow();
  });

  it("rejects input without BV or bilibili URL", () => {
    expect(() => validateBVInput("hello")).toThrow(
      "Input must contain BV ID or Bilibili URL",
    );
  });
});

describe("validateLanguage", () => {
  it("does nothing when lang is undefined", () => {
    expect(() => validateLanguage(undefined)).not.toThrow();
  });

  it("accepts two-letter language code", () => {
    expect(() => validateLanguage("en")).not.toThrow();
  });

  it("accepts language code with region subtag", () => {
    expect(() => validateLanguage("zh-Hans")).not.toThrow();
  });

  it("rejects Chinese characters", () => {
    expect(() => validateLanguage("中文")).toThrow(
      "Invalid language code format",
    );
  });

  it("rejects numeric-only input", () => {
    expect(() => validateLanguage("1234")).toThrow(
      "Invalid language code format",
    );
  });
});

describe("validateDetailLevel", () => {
  it("does nothing when level is undefined", () => {
    expect(() => validateDetailLevel(undefined)).not.toThrow();
  });

  it("accepts brief", () => {
    expect(() => validateDetailLevel("brief")).not.toThrow();
  });

  it("accepts detailed", () => {
    expect(() => validateDetailLevel("detailed")).not.toThrow();
  });

  it("rejects full", () => {
    expect(() => validateDetailLevel("full")).toThrow(
      'Invalid detail level: must be "brief" or "detailed"',
    );
  });

  it("rejects arbitrary string", () => {
    expect(() => validateDetailLevel("summary")).toThrow(
      'Invalid detail level: must be "brief" or "detailed"',
    );
  });
});

describe("validateCommentLimit", () => {
  it("does nothing when limit is undefined", () => {
    expect(() => validateCommentLimit(undefined)).not.toThrow();
  });

  it("accepts minimum value 1", () => {
    expect(() => validateCommentLimit(1)).not.toThrow();
  });

  it("accepts maximum value 50", () => {
    expect(() => validateCommentLimit(50)).not.toThrow();
  });

  it("rejects 0", () => {
    expect(() => validateCommentLimit(0)).toThrow(
      "Comment limit must be between 1 and 50",
    );
  });

  it("rejects negative value", () => {
    expect(() => validateCommentLimit(-1)).toThrow(
      "Comment limit must be between 1 and 50",
    );
  });

  it("rejects non-integer", () => {
    expect(() => validateCommentLimit(1.5)).toThrow(
      "Comment limit must be an integer between 1 and 50",
    );
  });

  it("rejects value above 50", () => {
    expect(() => validateCommentLimit(51)).toThrow(
      "Comment limit must be between 1 and 50",
    );
  });

  it("rejects non-number input", () => {
    expect(() =>
      validateCommentLimit("10" as unknown as number),
    ).toThrow("Comment limit must be an integer between 1 and 50");
  });
});

describe("validateCommentSort", () => {
  it("does nothing when sort is undefined", () => {
    expect(() => validateCommentSort(undefined)).not.toThrow();
  });

  it("accepts hot", () => {
    expect(() => validateCommentSort("hot")).not.toThrow();
  });

  it("accepts time", () => {
    expect(() => validateCommentSort("time")).not.toThrow();
  });

  it("rejects unknown value", () => {
    expect(() => validateCommentSort("latest")).toThrow(
      'Invalid comment sort: must be "hot" or "time"',
    );
  });

  it("rejects empty string", () => {
    expect(() => validateCommentSort("")).toThrow(
      'Invalid comment sort: must be "hot" or "time"',
    );
  });
});

describe("validateLength", () => {
  it("throws when required input is empty", () => {
    expect(() => validateLength("")).toThrow("Input is required");
  });

  it("throws when input exceeds maxLength", () => {
    expect(() => validateLength("a".repeat(257), { maxLength: 256 })).toThrow(
      "Input must not exceed",
    );
  });

  it("passes for valid input within limits", () => {
    expect(() =>
      validateLength("hello", { maxLength: 100, minLength: 1 }),
    ).not.toThrow();
  });
});

describe("validatePage", () => {
  it("does nothing when page is undefined", () => {
    expect(() => validatePage(undefined)).not.toThrow();
  });

  it("accepts positive integer 1", () => {
    expect(() => validatePage(1)).not.toThrow();
  });

  it("accepts large page number", () => {
    expect(() => validatePage(999)).not.toThrow();
  });

  it("rejects 0", () => {
    expect(() => validatePage(0)).toThrow("page must be a positive integer");
  });

  it("rejects negative", () => {
    expect(() => validatePage(-1)).toThrow("page must be a positive integer");
  });

  it("rejects non-integer", () => {
    expect(() => validatePage(1.5)).toThrow("page must be a positive integer");
  });

  it("rejects string", () => {
    expect(() => validatePage("2" as unknown as number)).toThrow(
      "page must be a positive integer",
    );
  });
});

describe("validateTimestampRange", () => {
  it("does nothing when both are undefined", () => {
    expect(() => validateTimestampRange(undefined, undefined)).not.toThrow();
  });

  it("accepts valid range start < end", () => {
    expect(() => validateTimestampRange(10, 30)).not.toThrow();
  });

  it("accepts start equals end", () => {
    expect(() => validateTimestampRange(10, 10)).not.toThrow();
  });

  it("rejects end < start", () => {
    expect(() => validateTimestampRange(30, 10)).toThrow(
      "end_seconds must be >= start_seconds",
    );
  });

  it("rejects negative start", () => {
    expect(() => validateTimestampRange(-1, 10)).toThrow(
      "start_seconds must be a finite non-negative number",
    );
  });

  it("rejects NaN start", () => {
    expect(() => validateTimestampRange(NaN, 10)).toThrow(
      "start_seconds must be a finite non-negative number",
    );
  });

  it("rejects Infinity", () => {
    expect(() => validateTimestampRange(Infinity, 10)).toThrow(
      "start_seconds must be a finite non-negative number",
    );
  });

  it("accepts only end_seconds without start_seconds", () => {
    expect(() => validateTimestampRange(undefined, 30)).not.toThrow();
  });
});

describe("validateQuery", () => {
  it.each([undefined, "hello", "你好世界", "a".repeat(100)])(
    "accepts %j",
    (value) => expect(() => validateQuery(value)).not.toThrow(),
  );

  it.each([
    ["a".repeat(101), "query must not exceed 100 characters"],
    ["   ", "query must not be empty"],
    [123 as unknown as string, "query must be a string"],
  ])("rejects %j", (value, message) => {
    expect(() => validateQuery(value)).toThrow(message);
  });
});

describe("validateSearchLimit", () => {
  it.each([undefined, 1, 5, 10])("accepts %j", (value) => {
    expect(() => validateSearchLimit(value)).not.toThrow();
  });

  it.each([
    [0, "limit must be between 1 and 10"],
    [11, "limit must be between 1 and 10"],
    [1.5, "limit must be an integer between 1 and 10"],
    ["5" as unknown as number, "limit must be an integer between 1 and 10"],
  ])("rejects %j", (value, message) => {
    expect(() => validateSearchLimit(value)).toThrow(message);
  });
});

describe("validateMaxMatches", () => {
  it.each([undefined, 1, 10, 20])("accepts %j", (value) => {
    expect(() => validateMaxMatches(value)).not.toThrow();
  });

  it.each([
    [0, "max_matches must be between 1 and 20"],
    [21, "max_matches must be between 1 and 20"],
    [5.5, "max_matches must be an integer between 1 and 20"],
    ["10" as unknown as number, "max_matches must be an integer between 1 and 20"],
  ])("rejects %j", (value, message) => {
    expect(() => validateMaxMatches(value)).toThrow(message);
  });
});

describe("validateContextSegments", () => {
  it.each([undefined, 0, 1, 5])("accepts %j", (value) => {
    expect(() => validateContextSegments(value)).not.toThrow();
  });

  it.each([
    [-1, "context_segments must be between 0 and 5"],
    [6, "context_segments must be between 0 and 5"],
    [1.5, "context_segments must be an integer between 0 and 5"],
    ["1" as unknown as number, "context_segments must be an integer between 0 and 5"],
  ])("rejects %j", (value, message) => {
    expect(() => validateContextSegments(value)).toThrow(message);
  });
});

describe("validateBoolean", () => {
  it("does nothing when value is undefined", () => {
    expect(() => validateBoolean(undefined, "test")).not.toThrow();
  });

  it("accepts true", () => {
    expect(() => validateBoolean(true, "test")).not.toThrow();
  });

  it("accepts false", () => {
    expect(() => validateBoolean(false, "test")).not.toThrow();
  });

  it("rejects string", () => {
    expect(() => validateBoolean("true", "flag")).toThrow(
      "flag must be a boolean",
    );
  });

  it("rejects number", () => {
    expect(() => validateBoolean(1, "flag")).toThrow(
      "flag must be a boolean",
    );
  });
});
