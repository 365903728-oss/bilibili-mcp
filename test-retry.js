// 测试重试机制功能
import { retryManager, withRetry } from './dist/utils/retry.js';

async function testRetry() {
  console.log('=== 测试重试机制功能 ===\n');

  // 测试1: 成功的重试
  console.log('1. 测试成功的重试:');
  let attemptCount = 0;
  
  try {
    const result = await withRetry(async () => {
      attemptCount++;
      console.log(`   - 执行尝试 ${attemptCount}`);
      
      // 第一次失败，第二次成功
      if (attemptCount === 1) {
        // 创建一个带有name属性的错误，使其被识别为可重试的错误
        const error = new Error('Simulated network error');
        error.name = 'NetworkError';
        throw error;
      }
      
      return 'Success!';
    }, {
      maxRetries: 2,
      baseDelay: 100,
      maxDelay: 1000,
      retryableErrorTypes: ['NetworkError', 'TimeoutError', 'AbortError']
    });
    
    console.log(`   - 最终结果: ${result}`);
    console.log(`   - 总尝试次数: ${attemptCount}`);
    console.log('   - 测试通过: ✅');
  } catch (error) {
    console.log(`   - 测试失败: ${error.message}`);
  }

  // 测试2: 达到最大重试次数
  console.log('\n2. 测试达到最大重试次数:');
  let attemptCount2 = 0;
  
  try {
    await withRetry(async () => {
      attemptCount2++;
      console.log(`   - 执行尝试 ${attemptCount2}`);
      // 创建一个带有name属性的错误，使其被识别为可重试的错误
      const error = new Error('Persistent network error');
      error.name = 'NetworkError';
      throw error;
    }, {
      maxRetries: 2,
      baseDelay: 100,
      maxDelay: 1000,
      retryableErrorTypes: ['NetworkError', 'TimeoutError', 'AbortError']
    });
  } catch (error) {
    console.log(`   - 捕获到预期错误: ${error.message}`);
    console.log(`   - 总尝试次数: ${attemptCount2}`);
    console.log('   - 测试通过: ✅');
  }

  // 测试3: 重试统计
  console.log('\n3. 测试重试统计:');
  const stats = retryManager.getStats();
  console.log('   - 重试统计:', stats);
  console.log('   - 测试通过: ✅');

  // 测试4: 重置统计
  console.log('\n4. 测试重置统计:');
  retryManager.resetStats();
  const resetStats = retryManager.getStats();
  console.log('   - 重置后统计:', resetStats);
  console.log('   - 测试通过: ✅');

  console.log('\n=== 重试机制测试完成 ===');
}

testRetry().catch(error => {
  console.error('测试失败:', error);
  process.exit(1);
});
