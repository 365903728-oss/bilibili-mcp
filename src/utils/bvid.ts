/**
 * BV号工具模块
 * 提供BV号的提取、验证和处理功能
 */

/**
 * 从输入字符串中提取BV号
 * 支持直接BV号或包含BV号的URL
 * @param input 输入字符串（BV号或URL）
 * @returns 提取的BV号
 * @throws 当无法提取BV号时抛出错误
 */
export function extractBVId(input: string): string {
  if (!input) {
    throw new Error('Input cannot be empty');
  }

  // 尝试从URL中提取BV号
  const urlMatch = input.match(/(BV[a-zA-Z0-9]{10})/);
  if (urlMatch) {
    return urlMatch[1];
  }

  // 直接验证是否为BV号
  if (/^BV[a-zA-Z0-9]{10}$/.test(input)) {
    return input;
  }

  throw new Error('Invalid Bilibili video ID or URL');
}

/**
 * 验证BV号格式是否正确
 * @param bvid BV号
 * @returns 是否为有效的BV号
 */
export function isValidBVId(bvid: string): boolean {
  if (!bvid) {
    return false;
  }

  // BV号格式：BV + 10个字符（字母数字组合）
  return /^BV[A-Za-z0-9]{10}$/.test(bvid);
}

/**
 * 验证BV号格式并检查基本有效性
 * @param bvid BV号
 * @throws 当BV号无效时抛出错误
 */
export function validateBVId(bvid: string): void {
  if (!bvid) {
    throw new Error('BV ID cannot be empty');
  }
  
  if (bvid.length !== 12) {
    throw new Error(`Invalid BV ID length: expected 12 characters, got ${bvid.length}`);
  }
  
  if (!isValidBVId(bvid)) {
    throw new Error('Invalid BV ID format');
  }
}

/**
 * 标准化BV号输入
 * 清理输入并提取BV号
 * @param input 输入字符串
 * @returns 标准化的BV号
 */
export function normalizeBVId(input: string): string {
  if (!input) {
    throw new Error('Input cannot be empty');
  }

  // 清理输入
  const cleaned = input.trim();
  
  // 提取BV号
  const bvid = extractBVId(cleaned);
  
  // 转换为大写（可选，BV号大小写不敏感）
  return bvid.toUpperCase();
}

/**
 * 从BV号创建标准URL
 * @param bvid BV号
 * @returns Bilibili视频标准URL
 */
export function createVideoUrl(bvid: string): string {
  const normalizedBvid = normalizeBVId(bvid);
  return `https://www.bilibili.com/video/${normalizedBvid}`;
}

/**
 * 检查输入是否包含BV号
 * @param input 输入字符串
 * @returns 是否包含BV号
 */
export function containsBVId(input: string): boolean {
  if (!input) {
    return false;
  }
  return /BV[A-Za-z0-9]{10}/.test(input);
}
