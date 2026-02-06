# BV号提取函数优化方案

## 问题分析

### 表现
- ❌ 重复代码：`subtitle.ts`和`comments.ts`中都有完全相同的`extractBVId`函数
- ❌ 维护成本高：修改一处需要同步修改多处
- ❌ 一致性风险：不同文件中的实现可能出现不一致

### 影响
- 代码质量下降：违反DRY（Don't Repeat Yourself）原则
- 维护难度增加：修改需要同步到多个文件
- 潜在bug：不同实现可能导致行为不一致

### 根本原因
- 缺少公共工具模块
- 开发过程中直接复制粘贴代码
- 没有统一的工具函数管理

## 改进方案

### 1. 创建公共BV号工具模块
**实施步骤**：
1. 创建 `src/utils/bvid.ts` 文件
2. 将 `extractBVId` 函数移动到该模块
3. 增强函数功能，添加更严格的验证
4. 导出函数供其他模块使用

**具体实现**：
```typescript
// src/utils/bvid.ts
/**
 * 从 BV 号或 URL 中提取 BV 号
 * @param input - Bilibili 视频 BV 号或完整 URL
 * @returns 提取的 BV 号
 * @throws 当输入无效时抛出错误
 */
export function extractBVId(input: string): string {
  // 验证输入长度
  if (!input || input.length > 256) {
    throw new Error("Invalid input length for Bilibili video ID or URL");
  }

  // 匹配 BV 号格式：BV1xx4x1x7xx 或类似格式
  const match = input.match(/(BV[a-zA-Z0-9]{10})/);
  if (!match) {
    throw new Error("Invalid Bilibili video ID or URL");
  }

  return match[1];
}

/**
 * 验证 BV 号格式是否有效
 * @param bvid - BV 号
 * @returns 是否有效
 */
export function isValidBVId(bvid: string): boolean {
  return /^BV[a-zA-Z0-9]{10}$/.test(bvid);
}

/**
 * 标准化 BV 号输入
 * @param input - BV 号或 URL
 * @returns 标准化的 BV 号
 * @throws 当输入无效时抛出错误
 */
export function normalizeBVId(input: string): string {
  const bvid = extractBVId(input);
  if (!isValidBVId(bvid)) {
    throw new Error("Extracted BV ID is invalid");
  }
  return bvid;
}
```

### 2. 更新调用点
**实施步骤**：
1. 修改 `subtitle.ts`，使用公共模块
2. 修改 `comments.ts`，使用公共模块
3. 移除重复的函数定义

**具体修改**：
```typescript
// 在 subtitle.ts 和 comments.ts 中
// 原代码
function extractBVId(input: string): string {
  const match = input.match(/(BV[a-zA-Z0-9]{10})/);
  if (!match) {
    throw new Error("Invalid Bilibili video ID or URL");
  }
  return match[1];
}

// 修改后
import { extractBVId } from '../utils/bvid.js';
```

### 3. 增强输入验证
**实施步骤**：
1. 在公共模块中添加输入长度限制
2. 添加特殊字符过滤
3. 实现更严格的BV号格式验证

**具体实现**：
- 输入长度限制：最大256字符
- 特殊字符处理：过滤危险字符
- 格式验证：确保BV号格式正确

## 技术实现细节

### 关键修改点
- **新增文件**：`src/utils/bvid.ts`
- **修改文件**：
  - `src/bilibili/subtitle.ts`
  - `src/bilibili/comments.ts`

### 依赖关系
- 无外部依赖，仅使用内置功能
- 依赖TypeScript编译环境

### 测试策略
1. **单元测试**：测试不同格式的BV号和URL
2. **边界测试**：测试空输入、过长输入、无效格式
3. **集成测试**：测试在实际模块中的使用

## 预期效果

### 功能改进
- ✅ 消除代码重复
- ✅ 统一验证逻辑
- ✅ 增强输入验证

### 质量提升
- ✅ 代码质量改善
- ✅ 维护成本降低
- ✅ 一致性增强

### 安全性提升
- ✅ 输入长度限制
- ✅ 格式验证增强
- ✅ 错误处理改进

## 风险评估

### 潜在风险
- **兼容性风险**：修改可能影响现有功能
- **依赖风险**：新增模块依赖关系
- **测试风险**：需要确保所有调用点正常工作

### 应对策略
- **渐进式修改**：先创建模块，再逐步更新调用点
- **全面测试**：确保所有功能正常工作
- **回滚方案**：保留原代码作为备份

## 实施时间

### 时间估计
- **创建模块**：30分钟
- **更新调用点**：20分钟
- **测试验证**：30分钟

### 优先级
**高优先级**：虽然不影响功能，但严重影响代码质量

## 成功指标

- ✅ 代码重复消除
- ✅ 验证逻辑统一
- ✅ 所有调用点正常工作
- ✅ 测试覆盖完整
