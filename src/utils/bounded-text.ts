const ELLIPSIS = "…";

function isUnsafeCodePoint(codePoint: number): boolean {
  return (
    (codePoint >= 0x00 && codePoint <= 0x08) ||
    codePoint === 0x0b ||
    codePoint === 0x0c ||
    (codePoint >= 0x0e && codePoint <= 0x1f) ||
    codePoint === 0x7f ||
    // C1 controls
    (codePoint >= 0x80 && codePoint <= 0x9f) ||
    // zero-width and directional marks
    (codePoint >= 0x200b && codePoint <= 0x200f) ||
    // bidi embeddings, overrides, and isolates
    (codePoint >= 0x202a && codePoint <= 0x202e) ||
    (codePoint >= 0x2066 && codePoint <= 0x2069) ||
    // BOM / zero-width no-break space
    codePoint === 0xfeff ||
    (codePoint >= 0xd800 && codePoint <= 0xdfff)
  );
}

/**
 * Truncate without splitting UTF-8 sequences or UTF-16 surrogate pairs.
 * The input is streamed by code point so a very large string is never copied
 * in full before its security budget is applied.
 */
export function truncateUtf8(
  value: string,
  maxBytes: number,
  suffix = ELLIPSIS,
): string {
  if (!Number.isSafeInteger(maxBytes) || maxBytes < 0) {
    throw new TypeError("maxBytes must be a non-negative safe integer");
  }
  if (maxBytes === 0) return "";

  const suffixBytes = Buffer.byteLength(suffix, "utf8");
  const pieces: string[] = [];
  let bytes = 0;
  let truncated = false;

  for (const codePointText of value) {
    const codePoint = codePointText.codePointAt(0)!;
    if (codePoint >= 0xd800 && codePoint <= 0xdfff) continue;
    const nextBytes = Buffer.byteLength(codePointText, "utf8");
    if (bytes + nextBytes > maxBytes) {
      truncated = true;
      break;
    }
    pieces.push(codePointText);
    bytes += nextBytes;
  }

  if (!truncated) return pieces.join("");
  if (suffixBytes > maxBytes) return "";
  const contentBudget = maxBytes - suffixBytes;
  while (pieces.length > 0 && bytes > contentBudget) {
    bytes -= Buffer.byteLength(pieces.pop()!, "utf8");
  }
  return `${pieces.join("")}${suffix}`;
}

function boundedSanitizedText(
  value: unknown,
  maxBytes: number,
  preserveWhitespace: boolean,
): string {
  if (typeof value !== "string") return "";
  if (!Number.isSafeInteger(maxBytes) || maxBytes < 0) {
    throw new TypeError("maxBytes must be a non-negative safe integer");
  }
  if (maxBytes === 0) return "";

  const suffixBytes = Buffer.byteLength(ELLIPSIS, "utf8");
  const pieces: string[] = [];
  let bytes = 0;
  let truncated = false;
  let started = preserveWhitespace;

  for (const codePointText of value) {
    const codePoint = codePointText.codePointAt(0)!;
    if (isUnsafeCodePoint(codePoint)) continue;
    if (!started && /\s/u.test(codePointText)) continue;
    started = true;
    const nextBytes = Buffer.byteLength(codePointText, "utf8");
    if (bytes + nextBytes > maxBytes) {
      truncated = true;
      break;
    }
    pieces.push(codePointText);
    bytes += nextBytes;
  }

  let output = pieces.join("");
  if (!preserveWhitespace) output = output.trimEnd();
  if (truncated && suffixBytes <= maxBytes) {
    const contentBudget = maxBytes - suffixBytes;
    while (
      pieces.length > 0 &&
      Buffer.byteLength(output, "utf8") > contentBudget
    ) {
      pieces.pop();
      output = pieces.join("");
      if (!preserveWhitespace) output = output.trimEnd();
    }
    output += ELLIPSIS;
  }
  return output;
}

export function boundedRemoteText(
  value: unknown,
  maxBytes: number,
): string {
  return boundedSanitizedText(value, maxBytes, false);
}

export function boundedRemoteTextPreservingWhitespace(
  value: unknown,
  maxBytes: number,
): string {
  return boundedSanitizedText(value, maxBytes, true);
}

/**
 * Remove unsafe code points (C0/C1 controls, bidi controls, zero-width/BOM,
 * unpaired surrogates) without truncation or whitespace changes. Transcript
 * lines must be sanitized without the byte truncation boundedRemoteText
 * applies, so legitimate long subtitle data is preserved.
 */
export function sanitizeRemoteText(value: unknown): string {
  if (typeof value !== "string") return "";
  let output = "";
  for (const codePointText of value) {
    const codePoint = codePointText.codePointAt(0)!;
    if (isUnsafeCodePoint(codePoint)) continue;
    output += codePointText;
  }
  return output;
}

export function boundedFiniteInteger(
  value: unknown,
  fallback = 0,
): number {
  if (
    typeof value !== "number" ||
    !Number.isSafeInteger(value) ||
    value < 0
  ) {
    return fallback;
  }
  return value;
}
