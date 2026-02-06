# 视频信息缓存实现方案

## 问题分析

### 表现
- ❌ 每次调用都会产生重复网络请求
- ❌ 性能下降，响应时间长
- ❌ API负担增加，可能触发限流
- ❌ 网络不稳定时容易失败

### 影响
- 核心功能性能差：视频信息和评论获取慢
- 用户体验下降：等待时间长
- 系统稳定性降低：频繁网络请求
- API使用效率低：重复获取相同数据

### 根本原因
- 缺少缓存机制：无任何数据缓存
- 无状态设计：每次请求都重新获取
- 网络依赖强：完全依赖实时网络

## 改进方案

### 1. 选择缓存库
**实施步骤**：
1. 安装 `quick-lru` 依赖
2. 配置TypeScript支持
3. 创建缓存管理模块

**依赖选择**：
- **quick-lru**：轻量级LRU缓存，适合内存缓存
- **版本**：^6.1.2
- **安装命令**：`npm install quick-lru`

### 2. 创建缓存管理模块
**实施步骤**：
1. 创建 `src/utils/cache.ts` 文件
2. 实现缓存管理器
3. 配置缓存策略

**具体实现**：
```typescript
// src/utils/cache.ts
import QuickLRU from 'quick-lru';
import { config } from '../config.js';

interface CacheOptions {
  maxSize: number;
  maxAge: number;
}

class CacheManager {
  private videoCache: QuickLRU<string, any>;
  private commentCache: QuickLRU<string, any>;
  private cacheStats = {
    hits: 0,
    misses: 0,
    sets: 0,
    deletes: 0
  };

  constructor() {
    const defaultOptions: CacheOptions = {
      maxSize: config.maxCacheSize || 100,
      maxAge: 60 * 60 * 1000 // 1 hour
    };

    this.videoCache = new QuickLRU({
      ...defaultOptions,
      maxSize: config.maxCacheSize || 100,
      maxAge: 60 * 60 * 1000 // 1 hour for video info
    });

    this.commentCache = new QuickLRU({
      ...defaultOptions,
      maxSize: config.maxCacheSize || 100,
      maxAge: 30 * 60 * 1000 // 30 minutes for comments
    });
  }

  // 视频信息缓存
  getVideoInfo(key: string): any {
    const value = this.videoCache.get(key);
    if (value) {
      this.cacheStats.hits++;
    } else {
      this.cacheStats.misses++;
    }
    return value;
  }

  setVideoInfo(key: string, value: any): void {
    this.videoCache.set(key, value);
    this.cacheStats.sets++;
  }

  deleteVideoInfo(key: string): void {
    this.videoCache.delete(key);
    this.cacheStats.deletes++;
  }

  // 评论缓存
  getCommentInfo(key: string): any {
    const value = this.commentCache.get(key);
    if (value) {
      this.cacheStats.hits++;
    } else {
      this.cacheStats.misses++;
    }
    return value;
  }

  setCommentInfo(key: string, value: any): void {
    this.commentCache.set(key, value);
    this.cacheStats.sets++;
  }

  deleteCommentInfo(key: string): void {
    this.commentCache.delete(key);
    this.cacheStats.deletes++;
  }

  // 缓存统计
  getStats(): typeof this.cacheStats {
    return { ...this.cacheStats };
  }

  // 清除所有缓存
  clear(): void {
    this.videoCache.clear();
    this.commentCache.clear();
    this.cacheStats = {
      hits: 0,
      misses: 0,
      sets: 0,
      deletes: 0
    };
  }

  // 生成缓存键
  generateKey(prefix: string, ...args: any[]): string {
    const keyParts = [prefix, ...args.map(arg => typeof arg === 'object' ? JSON.stringify(arg) : String(arg))];
    return keyParts.join(':');
  }
}

// 导出单例实例
export const cacheManager = new CacheManager();
```

### 3. 集成到现有代码
**实施步骤**：
1. 修改 `subtitle.ts`，集成视频信息缓存
2. 修改 `comments.ts`，集成评论缓存
3. 添加缓存键生成逻辑

**具体修改**：

#### 视频信息缓存集成
```typescript
// src/bilibili/subtitle.ts
import { cacheManager } from '../utils/cache.js';
import { extractBVId } from '../utils/bvid.js';

export async function getVideoInfoWithSubtitle(
  bvidOrUrl: string,
  preferredLang?: string
): Promise<SubtitleData> {
  try {
    const bvid = extractBVId(bvidOrUrl);
    
    // 生成缓存键
    const cacheKey = cacheManager.generateKey('video', bvid, preferredLang);
    
    // 尝试从缓存获取
    const cachedData = cacheManager.getVideoInfo(cacheKey);
    if (cachedData) {
      console.log(`Cache hit for video ${bvid}`);
      return cachedData;
    }

    // 缓存未命中，正常获取
    console.log(`Cache miss for video ${bvid}, fetching from API`);
    
    // 现有逻辑...
    const videoData = await getVideoInfo(bvid);
    // ... 处理逻辑 ...
    const result = {
      data_source: dataSource,
      video_info: {
        title,
        description,
        tags,
        subtitle_text: subtitleText
      }
    };
    
    // 存入缓存
    cacheManager.setVideoInfo(cacheKey, result);
    
    return result;
  } catch (error) {
    // 错误处理...
  }
}
```

#### 评论缓存集成
```typescript
// src/bilibili/comments.ts
import { cacheManager } from '../utils/cache.js';
import { extractBVId } from '../utils/bvid.js';

export async function getVideoCommentsData(
  bvidOrUrl: string,
  detailLevel: CommentDetailLevel = "brief"
): Promise<CommentData> {
  try {
    const bvid = extractBVId(bvidOrUrl);
    
    // 生成缓存键
    const cacheKey = cacheManager.generateKey('comments', bvid, detailLevel);
    
    // 尝试从缓存获取
    const cachedData = cacheManager.getCommentInfo(cacheKey);
    if (cachedData) {
      console.log(`Cache hit for comments ${bvid}`);
      return cachedData;
    }

    // 缓存未命中，正常获取
    console.log(`Cache miss for comments ${bvid}, fetching from API`);
    
    // 现有逻辑...
    // ... 处理逻辑 ...
    const result = {
      comments: processedComments,
      summary: {
        total_comments: processedComments.length,
        comments_with_timestamp: commentsWithTimestamp
      }
    };
    
    // 存入缓存
    cacheManager.setCommentInfo(cacheKey, result);
    
    return result;
  } catch (error) {
    // 错误处理...
  }
}
```

### 4. 缓存策略配置
**实施步骤**：
1. 配置缓存大小和过期时间
2. 实现缓存统计
3. 添加缓存监控

**具体配置**：
- **视频信息**：最大100条，1小时过期
- **评论信息**：最大100条，30分钟过期
- **缓存键**：基于BV号和参数
- **统计**：缓存命中率、 miss率

## 技术实现细节

### 关键修改点
- **新增文件**：`src/utils/cache.ts`
- **修改文件**：
  - `src/bilibili/subtitle.ts`
  - `src/bilibili/comments.ts`
- **依赖**：`quick-lru` ^6.1.2

### 缓存键设计
| 类型 | 缓存键格式 | 示例 |
|------|-----------|------|
| 视频信息 | `video:{bvid}:{lang}` | `video:BV1Gx411w7La:zh-Hans` |
| 评论信息 | `comments:{bvid}:{detail}` | `comments:BV1Gx411w7La:brief` |

### 测试策略
1. **单元测试**：测试缓存基本功能
2. **集成测试**：测试缓存与API集成
3. **性能测试**：测试缓存对性能的影响
4. **边界测试**：测试缓存过期、容量限制

## 预期效果

### 性能改进
- ⚡ **响应时间**：减少50-70%（缓存命中时几乎无延迟）
- ⚡ **网络请求**：减少60-80%（重复请求被缓存拦截）
- ⚡ **系统负载**：显著降低（减少网络I/O）

### 功能改进
- ✅ **稳定性**：网络不稳定时仍可工作
- ✅ **可靠性**：缓存作为网络故障的缓冲
- ✅ **一致性**：相同请求返回相同结果

### 系统改进
- 📈 **API使用效率**：大幅提高
- 📈 **系统吞吐量**：显著提升
- 📈 **用户体验**：响应速度快

## 风险评估

### 潜在风险
- **内存使用**：缓存可能增加内存占用
- **数据一致性**：缓存数据可能不是最新
- **错误处理**：缓存逻辑可能引入新错误
- **依赖风险**：新增外部依赖

### 应对策略
- **内存控制**：限制缓存大小，使用LRU策略
- **过期策略**：合理设置TTL，确保数据新鲜度
- **错误隔离**：缓存错误不影响核心功能
- **依赖管理**：固定版本，定期更新

## 实施时间

### 时间估计
- **依赖安装**：5分钟
- **缓存模块实现**：1小时
- **集成到现有代码**：30分钟
- **测试验证**：45分钟

### 优先级
**高优先级**：直接影响性能和用户体验

## 成功指标

- ⚡ **缓存命中率**：≥ 70%
- ⚡ **响应时间**：减少 ≥ 50%
- ⚡ **网络请求**：减少 ≥ 60%
- ✅ **功能完整性**：无功能损失
- ✅ **系统稳定性**：无稳定性下降
