// 测试输入验证功能
import { validateBVInput, validateLanguage, validateDetailLevel } from './dist/utils/validation.js';
import { sanitizeBVInput } from './dist/utils/sanitization.js';

async function testValidation() {
  console.log('=== 测试输入验证功能 ===\n');

  // 测试1: BV输入验证
  console.log('1. 测试BV输入验证:');
  const bvTestCases = [
    'BV1Gx411w7La', // 有效
    'https://www.bilibili.com/video/BV1Gx411w7La', // 有效
    'https://b23.tv/BV1Gx411w7La', // 有效
    '', // 无效
    '1234567890', // 无效
    'https://example.com', // 无效
  ];
  
  for (const testCase of bvTestCases) {
    try {
      validateBVInput(testCase);
      console.log(`   - "${testCase}": ✅ 有效`);
    } catch (error) {
      console.log(`   - "${testCase}": ❌ 无效 - ${error.message}`);
    }
  }

  // 测试2: 语言验证
  console.log('\n2. 测试语言验证:');
  const langTestCases = [
    'zh-Hans', // 有效
    'en', // 有效
    '', // 有效（可选）
    undefined, // 有效（可选）
    'zh', // 有效
    'zh-CN', // 有效
    '123', // 无效
    'zh-Hans-GB', // 无效
  ];
  
  for (const testCase of langTestCases) {
    try {
      validateLanguage(testCase);
      console.log(`   - "${testCase || 'undefined'}": ✅ 有效`);
    } catch (error) {
      console.log(`   - "${testCase || 'undefined'}": ❌ 无效 - ${error.message}`);
    }
  }

  // 测试3: 详情级别验证
  console.log('\n3. 测试详情级别验证:');
  const levelTestCases = [
    'brief', // 有效
    'detailed', // 有效
    '', // 有效（可选）
    undefined, // 有效（可选）
    'invalid', // 无效
  ];
  
  for (const testCase of levelTestCases) {
    try {
      validateDetailLevel(testCase);
      console.log(`   - "${testCase || 'undefined'}": ✅ 有效`);
    } catch (error) {
      console.log(`   - "${testCase || 'undefined'}": ❌ 无效 - ${error.message}`);
    }
  }

  // 测试4: 输入清理
  console.log('\n4. 测试输入清理:');
  const sanitizeTestCases = [
    'BV1Gx411w7La',
    '  BV1Gx411w7La  ',
    'https://www.bilibili.com/video/BV1Gx411w7La',
  ];
  
  for (const testCase of sanitizeTestCases) {
    const sanitized = sanitizeBVInput(testCase);
    console.log(`   - 输入: "${testCase}"`);
    console.log(`   - 清理: "${sanitized}"`);
  }

  console.log('\n=== 输入验证测试完成 ===');
}

testValidation().catch(error => {
  console.error('测试失败:', error);
  process.exit(1);
});
