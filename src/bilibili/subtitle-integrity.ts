// 确定性 AI 字幕完整性评估（所有 ai-* 语言；保守语言检查仅针对 ai-zh）。
// 纯函数；阈值由 PRD 冻结（docs/subtitle-integrity-and-scriptable-setup-prd.md），
// 不可配置、不通过 MCP 暴露。此模块绝不记录或返回比较文本、tokens、哈希或签名 URL。
// 同语言下的语义偏差（稳定但主题不符的正文）是接受限制：由调用方的
// force_asr / exclude_ai_subtitles 控制，本模块不做猜测性拒绝。
import type { SubtitleBodyItem } from "./types.js";

type AiSubtitleIntegrityVerdict =
  | { usable: true }
  | { usable: false; reason: string };

/**
 * 归一化后的逐段正文（精确 [from,to,content] 元组），用于跨读取稳定性比较。
 * 只序列化这三个字段：SubtitleBodyItem 还有可选 location，且对象键序可能因
 * 两次读取而异，直接 JSON.stringify(seg) 会把仅此差异的稳定正文误判为不稳定。
 */
function canonicalSubtitleBody(body: SubtitleBodyItem[]): string {
  return body
    .map((seg) => JSON.stringify([seg.from, seg.to, seg.content ?? ""]))
    .join("\n");
}

function bodyText(body: SubtitleBodyItem[]): string {
  return body.map((seg) => seg.content ?? "").join("\n");
}

function countLetters(text: string, pattern: RegExp): number {
  let count = 0;
  for (const ch of text) {
    if (pattern.test(ch)) count += 1;
  }
  return count;
}

// 语言信号（仅 ai-zh）：正文达到 80 个及以上 Unicode 字母、且其中 Han 字母占比低于 10%，
// 视为与 ai-zh 高置信不匹配；其他 ai-* 语言（ai-en/ai-ja/ai-es 等）不因非中文正文被拒绝。
// 阈值不满足则信号 inconclusive，不得拒绝。
function languageMismatch(body: SubtitleBodyItem[]): boolean {
  const text = bodyText(body);
  const letters = countLetters(text, /\p{L}/u);
  if (letters < 80) return false;
  const han = countLetters(text, /\p{Script=Han}/u);
  return han / letters < 0.1;
}

/**
 * 对选中的 ai-* 做无条件完整性评估：稳定性（所有 ai-*）→ 语言（仅 ai-zh）。
 * 任一信号不通过即 unusable（reason 不含任何正文/比较内容）；
 * 阈值不满足的检查一律 inconclusive 通过。
 */
export function assessAiSubtitleIntegrity(
  firstBody: SubtitleBodyItem[],
  secondBody: SubtitleBodyItem[],
  trackLanguage: string,
): AiSubtitleIntegrityVerdict {
  if (canonicalSubtitleBody(firstBody) !== canonicalSubtitleBody(secondBody)) {
    return {
      usable: false,
      reason: "AI subtitle returned inconsistent content across reads",
    };
  }
  if (trackLanguage === "ai-zh" && languageMismatch(firstBody)) {
    return {
      usable: false,
      reason: "AI subtitle body language does not match ai-zh",
    };
  }
  return { usable: true };
}
