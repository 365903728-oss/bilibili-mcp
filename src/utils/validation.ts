/**
 * 输入验证模块
 * 提供统一的输入验证功能
 */

export interface ValidationOptions {
  maxLength?: number;
  minLength?: number;
  required?: boolean;
}

/**
 * 验证字符串长度
 */
export function validateLength(
  input: string | undefined,
  options: ValidationOptions = {}
): void {
  const { maxLength = 256, minLength = 1, required = true } = options;
  
  if (required && !input) {
    throw new Error('Input is required');
  }
  
  if (input) {
    if (input.length < minLength) {
      throw new Error(`Input must be at least ${minLength} characters long`);
    }
    
    if (input.length > maxLength) {
      throw new Error(`Input must not exceed ${maxLength} characters`);
    }
  }
}

/**
 * 验证BV号或URL输入
 */
export function validateBVInput(input: string): void {
  validateLength(input, {
    maxLength: 256,
    minLength: 1,
    required: true
  });
  
  // 基本格式验证
  if (!input.includes('BV') && !input.includes('bilibili.com') && !input.includes('b23.tv')) {
    throw new Error('Input must contain BV ID or Bilibili URL');
  }
}

/**
 * 验证语言参数
 */
export function validateLanguage(lang?: string): void {
  if (lang) {
    validateLength(lang, {
      maxLength: 10,
      minLength: 2,
      required: false
    });
    
    // 语言代码格式验证
    if (!/^[a-z]{2}(-[A-Za-z]{2,})?$/.test(lang)) {
      throw new Error('Invalid language code format');
    }
  }
}

/**
 * 验证评论详情级别
 */
export function validateDetailLevel(level?: string): void {
  if (level && !['brief', 'detailed'].includes(level)) {
    throw new Error('Invalid detail level: must be "brief" or "detailed"');
  }
}
