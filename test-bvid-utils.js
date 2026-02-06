// 测试BV号工具模块
import { 
  extractBVId, 
  isValidBVId, 
  validateBVId, 
  normalizeBVId,
  createVideoUrl,
  containsBVId
} from './dist/utils/bvid.js';

async function testBVIDUtils() {
  console.log('=== 测试BV号工具模块 ===\n');

  // 测试用例
  const testCases = [
    'BV1Gx411w7La', // 直接BV号
    'https://www.bilibili.com/video/BV1Gx411w7La', // 完整URL
    'https://b23.tv/BV1Gx411w7La', // 短链接
    'BV1234567890', // 格式正确但可能不存在的BV号
  ];

  console.log('1. 测试extractBVId函数:');
  testCases.forEach((testCase, index) => {
    try {
      const bvid = extractBVId(testCase);
      console.log(`   ${index + 1}. 输入: "${testCase}"`);
      console.log(`      提取: "${bvid}"`);
      console.log(`      状态: ✅ 成功`);
    } catch (error) {
      console.log(`   ${index + 1}. 输入: "${testCase}"`);
      console.log(`      错误: ${error.message}`);
      console.log(`      状态: ❌ 失败`);
    }
  });

  console.log('\n2. 测试isValidBVId函数:');
  const validityTests = [
    'BV1Gx411w7La', // 有效
    'BV1234567890', // 有效
    'bv1gx411w7la', // 有效（小写）
    'BV1', // 无效（太短）
    'BV1Gx411w7La1', // 无效（太长）
    '1234567890', // 无效（无BV前缀）
    '', // 无效（空）
  ];
  validityTests.forEach((testCase, index) => {
    const isValid = isValidBVId(testCase);
    console.log(`   ${index + 1}. "${testCase}": ${isValid ? '✅ 有效' : '❌ 无效'}`);
  });

  console.log('\n3. 测试validateBVId函数:');
  const validationTests = [
    'BV1Gx411w7La', // 有效
    'BV1234567890', // 有效
    'BV1', // 无效
    '', // 无效
  ];
  validationTests.forEach((testCase, index) => {
    try {
      validateBVId(testCase);
      console.log(`   ${index + 1}. "${testCase}": ✅ 验证通过`);
    } catch (error) {
      console.log(`   ${index + 1}. "${testCase}": ❌ 验证失败 - ${error.message}`);
    }
  });

  console.log('\n4. 测试normalizeBVId函数:');
  const normalizeTests = [
    'BV1Gx411w7La',
    '  BV1Gx411w7La  ', // 带空白
    'https://www.bilibili.com/video/BV1Gx411w7La',
  ];
  normalizeTests.forEach((testCase, index) => {
    try {
      const normalized = normalizeBVId(testCase);
      console.log(`   ${index + 1}. 输入: "${testCase}"`);
      console.log(`      输出: "${normalized}"`);
      console.log(`      状态: ✅ 成功`);
    } catch (error) {
      console.log(`   ${index + 1}. 输入: "${testCase}"`);
      console.log(`      错误: ${error.message}`);
      console.log(`      状态: ❌ 失败`);
    }
  });

  console.log('\n5. 测试createVideoUrl函数:');
  try {
    const url = createVideoUrl('BV1Gx411w7La');
    console.log(`   输入: "BV1Gx411w7La"`);
    console.log(`   输出: "${url}"`);
    console.log(`   状态: ✅ 成功`);
  } catch (error) {
    console.log(`   错误: ${error.message}`);
    console.log(`   状态: ❌ 失败`);
  }

  console.log('\n6. 测试containsBVId函数:');
  const containsTests = [
    'BV1Gx411w7La',
    'https://www.bilibili.com/video/BV1Gx411w7La',
    '这是一个视频 BV1Gx411w7La',
    '普通文本',
    '',
  ];
  containsTests.forEach((testCase, index) => {
    const contains = containsBVId(testCase);
    console.log(`   ${index + 1}. "${testCase}": ${contains ? '✅ 包含' : '❌ 不包含'}`);
  });

  console.log('\n=== 测试完成 ===');
}

testBVIDUtils().catch(error => {
  console.error('测试失败:', error);
  process.exit(1);
});
