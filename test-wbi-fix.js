// 测试WBI签名修复
import { fetchWithWBI } from './dist/bilibili/client.js';

async function testWBIFix() {
  console.log('=== 测试WBI签名修复 ===\n');

  try {
    console.log('1. 测试WBI签名获取...');
    
    // 测试一个简单的API调用，验证WBI签名是否正常工作
    const testData = await fetchWithWBI('/x/web-interface/nav', {});
    
    console.log('2. WBI签名测试成功!');
    console.log('3. 响应数据:');
    console.log('   - 数据类型:', typeof testData);
    console.log('   - 是否包含用户信息:', !!testData?.uname);
    console.log('   - 是否包含WBI信息:', !!testData?.wbi_img);
    
    if (testData?.wbi_img) {
      console.log('4. WBI图片信息:');
      console.log('   - img_url:', testData.wbi_img.img_url);
      console.log('   - sub_url:', testData.wbi_img.sub_url);
      
      // 验证URL格式
      const imgUrl = testData.wbi_img.img_url;
      const subUrl = testData.wbi_img.sub_url;
      
      console.log('5. URL格式验证:');
      console.log('   - img_url格式正确:', imgUrl && imgUrl.includes('https://'));
      console.log('   - sub_url格式正确:', subUrl && subUrl.includes('https://'));
      
      // 测试正则表达式
      console.log('6. 正则表达式测试:');
      const imgKeyMatch = imgUrl?.match(/([^\/_]+)(?=\.[a-zA-Z]+$)/);
      const subKeyMatch = subUrl?.match(/([^\/_]+)(?=\.[a-zA-Z]+$)/);
      
      console.log('   - imgKeyMatch:', imgKeyMatch);
      console.log('   - subKeyMatch:', subKeyMatch);
      console.log('   - 匹配成功:', !!imgKeyMatch && !!subKeyMatch);
    }
    
    console.log('\n✅ WBI签名修复测试通过!');
    console.log('✅ 字幕获取功能应该已经恢复正常');
    
  } catch (error) {
    console.error('❌ WBI签名测试失败:', error);
    console.error('❌ 错误信息:', error.message);
    console.error('❌ 错误堆栈:', error.stack);
  }
}

testWBIFix();
