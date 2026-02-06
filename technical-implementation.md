# 哔哩哔哩MCP工具技术实现文档

## 一、WBI签名修复

### 问题分析
- **根本原因**：硬编码了图片扩展名`.jpg`，而B站API已改为使用`.png`
- **影响范围**：所有需要WBI签名的API请求

### 技术实现
**文件：** `src/bilibili/client.ts`
**修改位置：** 第143-144行

**修改前：**
```typescript
const imgKeyMatch = wbiImg.img_url?.match(/([^\/_]+)(?=\.jpg)/);
const subKeyMatch = wbiImg.sub_url?.match(/([^\/_]+)(?=\.jpg)/);
```

**修改后：**
```typescript
const imgKeyMatch = wbiImg.img_url?.match(/([^\/_]+)(?=\.[a-zA-Z]+$)/);
const subKeyMatch = wbiImg.sub_url?.match(/([^\/_]+)(?=\.[a-zA-Z]+$)/);
```

### 验证结果
- ✅ 支持任意图片扩展名（.jpg、.png等）
- ✅ 兼容性更好，应对B站API变化

## 二、BV号提取函数优化

### 问题分析
- **根本原因**：`extractBVId`函数在多个文件中重复定义
- **影响范围**：代码维护性和一致性

### 技术实现
**创建文件：** `src/utils/bvid.ts`
**主要函数：**
- `extractBVId`：从输入中提取BV号
- `isValidBVId`：验证BV号格式
- `validateBVId`：严格验证BV号
- `normalizeBVId`：标准化BV号输入
- `createVideoUrl`：创建标准视频URL
- `containsBVId`：检查是否包含BV号

**移除的重复代码：**
- `src/bilibili/subtitle.ts`中的`extractBVId`函数
- `src/bilibili/comments.ts`中的`extractBVId`函数

**集成修改：**
- `src/bilibili/subtitle.ts`：导入并使用公共函数
- `src/bilibili/comments.ts`：导入并使用公共函数

### 验证结果
- ✅ 代码重复度降低
- ✅ BV号验证更加严格
- ✅ 函数调用一致性提高

## 三、视频信息缓存实现

### 问题分析
- **根本原因**：未实现视频信息和评论的缓存机制
- **影响范围**：性能和API调用频率

### 技术实现
**创建文件：** `src/utils/cache.ts`
**核心功能：**
- `CacheManager`类：管理视频和评论缓存
- `videoCache`：视频信息缓存
- `commentCache`：评论缓存
- 缓存统计功能

**依赖：**
- 新增`quick-lru`：LRU缓存实现

**集成修改：**
- `src/bilibili/subtitle.ts`：集成视频信息缓存
- `src/bilibili/comments.ts`：集成评论缓存

### 验证结果
- ✅ 重复请求响应速度提升
- ✅ API调用频率减少
- ✅ 缓存过期机制正常

## 四、输入验证增强

### 问题分析
- **根本原因**：输入验证逻辑不够完善
- **影响范围**：安全性和可靠性

### 技术实现
**创建文件：**
- `src/utils/validation.ts`：输入验证
- `src/utils/sanitization.ts`：输入清理
- `src/utils/errors.ts`：错误处理

**核心功能：**
- `validateBVInput`：BV号输入验证
- `validateLanguage`：语言参数验证
- `validateDetailLevel`：详情级别验证
- `sanitizeBVInput`：输入清理
- 增强的错误类型定义

**集成修改：**
- `src/server.ts`：集成输入验证到工具调用

### 验证结果
- ✅ 输入验证更加严格
- ✅ 错误处理更加完善
- ✅ 安全性提高

## 五、请求重试机制实现

### 问题分析
- **根本原因**：未实现请求重试和错误处理机制
- **影响范围**：稳定性和用户体验

### 技术实现
**创建文件：** `src/utils/retry.ts`
**核心功能：**
- `RetryManager`类：管理重试逻辑
- `withRetry`：便捷的重试包装函数
- 指数退避和抖动延迟策略
- 重试统计功能

**集成修改：**
- `src/bilibili/client.ts`：
  - `fetchWithWBI`：集成重试机制
  - `fetchWithoutWBI`：集成重试机制
  - `getSubtitleContent`：集成重试机制
  - `getWBI`：集成重试机制

### 验证结果
- ✅ 网络波动时请求更加稳定
- ✅ 重试策略合理有效
- ✅ 错误处理更加完善

## 六、整体架构改进

### 目录结构优化
```
src/
├── bilibili/              # B站相关功能
│   ├── client.ts         # API客户端
│   ├── comments.ts       # 评论处理
│   ├── subtitle.ts       # 字幕处理
│   └── types.ts          # 类型定义
├── utils/                # 公共工具
│   ├── bvid.ts           # BV号工具
│   ├── cache.ts          # 缓存管理
│   ├── errors.ts         # 错误处理
│   ├── retry.ts          # 重试机制
│   ├── sanitization.ts   # 输入清理
│   └── validation.ts     # 输入验证
├── config.ts             # 配置管理
├── index.ts              # 入口文件
└── server.ts             # MCP服务器
```

### 核心改进点
1. **模块化**：将功能拆分为独立模块
2. **可维护性**：减少代码重复，提高一致性
3. **性能**：实现缓存机制，减少API调用
4. **稳定性**：增加重试机制，提高可靠性
5. **安全性**：增强输入验证，防止错误输入
6. **扩展性**：清晰的模块边界，便于后续功能扩展

## 七、测试覆盖

### 测试文件
- `test-core-functionality.js`：核心功能测试
- `test-bvid-utils.js`：BV号工具测试
- `test-cache.js`：缓存功能测试
- `test-validation.js`：输入验证测试
- `test-retry.js`：重试机制测试

### 测试覆盖范围
1. **功能测试**：所有核心功能正常工作
2. **边界测试**：各种输入边界情况
3. **错误测试**：错误处理和异常情况
4. **性能测试**：响应时间和内存使用
5. **兼容性测试**：不同环境和版本

## 八、总结

### 技术改进
- ✅ 解决了5个高优先级问题
- ✅ 代码质量显著提升
- ✅ 性能和稳定性改善
- ✅ 安全性和可靠性增强

### 业务价值
- ✅ 用户体验更加流畅
- ✅ 系统稳定性提高
- ✅ 维护成本降低
- ✅ 应对B站API变化的能力增强

### 后续建议
1. **监控**：添加API调用监控和日志分析
2. **自动适配**：实现B站API变化的自动检测和适配
3. **扩展**：增加更多视频相关功能
4. **文档**：完善API文档和使用指南

---

**文档版本：** 1.0
**创建日期：** 2026-02-06
**更新日期：** 2026-02-06
