# 输入验证增强方案

## 问题分析

### 表现
- ❌ BV号验证正则表达式不够严格
- ❌ 缺少输入长度限制
- ❌ 缺少特殊字符过滤
- ❌ 错误信息不够详细

### 影响
- **安全风险**：可能接受恶意输入
- **功能异常**：无效输入导致错误
- **系统稳定性**：异常输入可能崩溃
- **用户体验**：错误提示不明确

### 根本原因
- 验证逻辑简单：仅基本正则匹配
- 无长度限制：可能接受过长输入
- 无字符过滤：可能包含危险字符
- 错误处理粗：错误信息不够详细

## 改进方案

### 1. 增强BV号验证
**实施步骤**：
1. 改进BV号正则表达式
2. 实现更严格的格式验证
3. 添加校验和验证

**具体实现**：
```typescript
// src/utils/bvid.ts
export function isValidBVId(bvid: string): boolean {
  // 更严格的BV号格式验证
  // BV号格式：BV + 10个字符（字母数字组合）
  return /^BV[A-Za-z0-9]{10}$/.test(bvid);
}

/**
 * 验证BV号格式并检查基本有效性
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
  
  // 可选：添加更复杂的验证逻辑
  // 例如：检查字符集、校验和等
}
```

### 2. 添加输入长度限制
**实施步骤**：
1. 为所有输入参数添加长度限制
2. 实现统一的长度验证函数
3. 集成到验证流程中

**具体实现**：
```typescript
// src/utils/validation.ts
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
    minLength: 2,
    required: true
  });
  
  // 基本格式验证
  if (!input.includes('BV') && !input.includes('bilibili.com')) {
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
    if (!/^[a-z]{2}(-[A-Z]{2})?$/.test(lang)) {
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
```

### 3. 实现特殊字符过滤
**实施步骤**：
1. 创建字符过滤函数
2. 定义安全字符集
3. 集成到输入处理流程

**具体实现**：
```typescript
// src/utils/sanitization.ts

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
```

### 4. 增强错误处理
**实施步骤**：
1. 定义详细的错误类型
2. 实现统一的错误处理
3. 提供友好的错误信息

**具体实现**：
```typescript
// src/utils/errors.ts
export class ValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ValidationError';
  }
}

export class BVIdError extends ValidationError {
  constructor(message: string) {
    super(message);
    this.name = 'BVIdError';
  }
}

export class InputLengthError extends ValidationError {
  constructor(message: string) {
    super(message);
    this.name = 'InputLengthError';
  }
}

export class UnsafeInputError extends ValidationError {
  constructor(message: string) {
    super(message);
    this.name = 'UnsafeInputError';
  }
}

/**
 * 安全地处理输入验证错误
 */
export function handleValidationError(error: unknown): never {
  if (error instanceof ValidationError) {
    throw error;
  }
  
  if (error instanceof Error) {
    throw new ValidationError(`Validation failed: ${error.message}`);
  }
  
  throw new ValidationError('Unknown validation error');
}
```

### 5. 集成到现有代码
**实施步骤**：
1. 修改 `server.ts`，添加输入验证
2. 修改 `subtitle.ts`，使用增强的验证
3. 修改 `comments.ts`，使用增强的验证
4. 统一错误处理流程

**具体修改**：

#### 服务器输入验证
```typescript
// src/server.ts
import { validateBVInput, validateLanguage, validateDetailLevel } from './utils/validation.js';
import { sanitizeBVInput } from './utils/sanitization.js';

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case "get_video_info": {
        const bvidOrUrl = args?.bvid_or_url as string;
        const preferredLang = args?.preferred_lang as string | undefined;

        // 输入验证
        try {
          validateBVInput(bvidOrUrl);
          validateLanguage(preferredLang);
          // 清理输入
          const sanitizedInput = sanitizeBVInput(bvidOrUrl);
        } catch (error) {
          return {
            content: [{
              type: "text",
              text: JSON.stringify({
                error: true,
                message: error instanceof Error ? error.message : "Invalid input",
                code: "VALIDATION_ERROR"
              }, null, 2)
            }],
            isError: true
          };
        }

        // 现有逻辑...
      }

      case "get_video_comments": {
        const bvidOrUrl = args?.bvid_or_url as string;
        const detailLevel = (args?.detail_level as "brief" | "detailed") || "brief";

        // 输入验证
        try {
          validateBVInput(bvidOrUrl);
          validateDetailLevel(detailLevel);
          // 清理输入
          const sanitizedInput = sanitizeBVInput(bvidOrUrl);
        } catch (error) {
          return {
            content: [{
              type: "text",
              text: JSON.stringify({
                error: true,
                message: error instanceof Error ? error.message : "Invalid input",
                code: "VALIDATION_ERROR"
              }, null, 2)
            }],
            isError: true
          };
        }

        // 现有逻辑...
      }

      // ...
    }
  } catch (error) {
    // 错误处理...
  }
});
```

## 技术实现细节

### 关键修改点
- **新增文件**：
  - `src/utils/validation.ts`
  - `src/utils/sanitization.ts`
- **修改文件**：
  - `src/utils/bvid.ts` (增强)
  - `src/utils/errors.ts` (扩展)
  - `src/server.ts` (集成)
  - `src/bilibili/subtitle.ts` (使用)
  - `src/bilibili/comments.ts` (使用)

### 验证规则汇总

| 输入类型 | 验证规则 | 错误处理 |
|---------|---------|----------|
| BV号/URL | 非空、长度≤256、包含BV或URL | 详细错误信息 |
| 语言参数 | 可选、长度≤10、格式正确 | 格式验证错误 |
| 详情级别 | 可选、只能是brief/detailed | 取值范围错误 |
| 通用输入 | 无危险字符、长度限制 | 安全验证错误 |

### 测试策略
1. **单元测试**：测试各种验证函数
2. **边界测试**：测试空值、超长输入、特殊字符
3. **集成测试**：测试完整的验证流程
4. **安全测试**：测试注入攻击、XSS等

## 预期效果

### 安全改进
- 🔒 **输入验证**：严格验证所有输入
- 🔒 **长度限制**：防止过长输入攻击
- 🔒 **字符过滤**：防止注入攻击
- 🔒 **错误处理**：详细安全的错误信息

### 功能改进
- ✅ **可靠性**：减少无效输入导致的错误
- ✅ **稳定性**：防止异常输入崩溃
- ✅ **用户体验**：明确的错误提示
- ✅ **可维护性**：统一的验证逻辑

### 系统改进
- 📈 **安全性**：显著提升
- 📈 **稳定性**：明显增强
- 📈 **可维护性**：大幅改善
- 📈 **用户信任**：有效提升

## 风险评估

### 潜在风险
- **兼容性**：严格验证可能拒绝之前接受的输入
- **性能**：额外验证可能 slightly 影响性能
- **实现复杂度**：增加代码复杂度
- **测试覆盖**：需要更全面的测试

### 应对策略
- **渐进式实施**：先宽松后严格
- **性能优化**：优化验证逻辑
- **代码组织**：模块化设计
- **全面测试**：覆盖所有验证场景

## 实施时间

### 时间估计
- **创建验证模块**：45分钟
- **增强BV号验证**：30分钟
- **集成到现有代码**：45分钟
- **测试验证**：60分钟

### 优先级
**高优先级**：直接影响系统安全性

## 成功指标

- 🔒 **输入验证覆盖率**：100%
- 🔒 **安全漏洞**：0个
- ✅ **验证成功率**：≥ 99%
- ✅ **错误处理**：详细准确
- 📈 **系统稳定性**：显著提升
