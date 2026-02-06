// 性能分析脚本
import { getVideoInfoWithSubtitle } from './dist/bilibili/subtitle.js';
import { getVideoCommentsData } from './dist/bilibili/comments.js';
import { config } from './dist/config.js';

async function performanceAnalysis() {
  console.log('=== 哔哩哔哩MCP工具性能分析 ===\n');

  // 1. 分析配置参数对性能的影响
  console.log('1. 配置参数分析:');
  console.log('   ⏱️  限流间隔:', config.rateLimitMs, 'ms');
  console.log('   ⌛ 超时时间:', config.requestTimeoutMs, 'ms');
  console.log('   📦 缓存大小:', config.maxCacheSize);
  console.log('   ⚡ WBI缓存过期时间:', config.wbiCacheExpirationMs / 1000, '秒');
  console.log('');

  // 2. 分析代码结构中的性能瓶颈
  console.log('2. 代码结构性能分析:');
  
  // 检查重复的BV号提取
  console.log('   🔍 重复的BV号提取:');
  console.log('   - 问题: subtitle.js和comments.js中都有extractBVId函数');
  console.log('   - 影响: 代码重复，维护成本高');
  console.log('   - 建议: 提取到公共工具模块');
  console.log('');

  // 检查网络请求并发
  console.log('   🔄 网络请求并发:');
  console.log('   - 现状: 使用throttledFetch确保串行请求，避免被B站限流');
  console.log('   - 优点: 防止API限制');
  console.log('   - 缺点: 串行请求可能影响性能');
  console.log('');

  // 检查缓存策略
  console.log('   📚 缓存策略分析:');
  console.log('   - WBI缓存: 存在，1小时过期');
  console.log('   - 视频信息缓存: 不存在');
  console.log('   - 评论缓存: 不存在');
  console.log('   - 影响: 重复请求相同视频时会重新获取数据');
  console.log('');

  // 3. 测试实际性能（模拟）
  console.log('3. 性能测试:');
  const testBvid = 'BV1Gx411w7La';
  
  // 测试视频信息获取性能
  console.log('   📹 视频信息获取测试:');
  const startTime1 = Date.now();
  try {
    await getVideoInfoWithSubtitle(testBvid);
    const endTime1 = Date.now();
    console.log('   - 执行时间:', endTime1 - startTime1, 'ms');
  } catch (error) {
    console.log('   - 执行时间: 无法测试（网络或API问题）');
  }
  console.log('');

  // 测试评论获取性能
  console.log('   💬 评论获取测试:');
  const startTime2 = Date.now();
  try {
    await getVideoCommentsData(testBvid, 'brief');
    const endTime2 = Date.now();
    console.log('   - 执行时间:', endTime2 - startTime2, 'ms');
  } catch (error) {
    console.log('   - 执行时间: 无法测试（网络或API问题）');
  }
  console.log('');

  // 4. 分析内存使用
  console.log('4. 内存使用分析:');
  const memoryUsage = process.memoryUsage();
  console.log('   📊 堆内存使用:', Math.round(memoryUsage.heapUsed / 1024 / 1024 * 100) / 100, 'MB');
  console.log('   📈 堆内存总量:', Math.round(memoryUsage.heapTotal / 1024 / 1024 * 100) / 100, 'MB');
  console.log('   🚀 外部内存:', Math.round(memoryUsage.external / 1024 / 1024 * 100) / 100, 'MB');
  console.log('');

  // 5. 性能优化建议
  console.log('5. 性能优化建议:');
  console.log('   ✅ 高优先级:');
  console.log('   1. 实现视频信息缓存，减少重复网络请求');
  console.log('   2. 优化WBI签名逻辑，减少计算开销');
  console.log('   3. 合并重复的BV号提取函数');
  console.log('');
  console.log('   📋 中优先级:');
  console.log('   1. 优化限流策略，在保证不被限制的前提下提高并发');
  console.log('   2. 实现评论缓存机制');
  console.log('   3. 优化字幕处理逻辑，减少内存使用');
  console.log('');
  console.log('   💡 低优先级:');
  console.log('   1. 优化错误处理，减少不必要的错误日志');
  console.log('   2. 提高代码可读性，便于后续维护');
  console.log('');

  console.log('=== 性能分析完成 ===');
}

performanceAnalysis();
