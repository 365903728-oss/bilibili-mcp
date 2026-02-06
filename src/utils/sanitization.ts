/**
 * 输入清理模块
 * 提供输入字符过滤和清理功能
 */

/**
 * 安全字符集：只允许字母、数字、常见符号
 */
const SAFE_CHARACTERS = /^[a-zA-Z0-9\s\-._~:/?#\[\]@!$&'()*+,;=]+$/;

/**
 * 过滤危险字符
 */
export function sanitizeInput(input: string): string {
  if (!input) return input;
  
  // 移除控制字符
  const sanitized = input.replace(/[\x00-\x1F\x7F]/g, '');
  
  // 验证安全字符集
  if (!SAFE_CHARACTERS.test(sanitized)) {
    throw new Error('Input contains unsafe characters');
  }
  
  return sanitized;
}

/**
 * 清理BV号输入
 */
export function sanitizeBVInput(input: string): string {
  const sanitized = sanitizeInput(input);
  // 移除前后空白
  return sanitized.trim();
}
