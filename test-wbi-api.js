// 测试B站WBI API响应格式
import { config } from './dist/config.js';

async function testWBIAPI() {
  console.log('=== 测试B站WBI API响应格式 ===\n');

  const BASE_URL = config.baseUrl;
  
  try {
    console.log('1. 发送请求获取nav数据...');
    const response = await fetch(`${BASE_URL}/x/web-interface/nav`, {
      headers: {
        "User-Agent": config.userAgent,
        "Referer": config.referer,
      }
    });

    console.log('2. 响应状态:', response.status, response.statusText);
    
    if (!response.ok) {
      console.error('请求失败:', response.status);
      return;
    }

    console.log('3. 解析响应数据...');
    const data = await response.json();
    
    console.log('4. 响应数据结构:');
    console.log('   - code:', data.code);
    console.log('   - message:', data.message);
    console.log('   - data存在:', !!data.data);
    
    if (data.data) {
      console.log('5. data字段分析:');
      console.log('   - wbi_img存在:', !!data.data.wbi_img);
      
      if (data.data.wbi_img) {
        console.log('6. wbi_img结构:');
        console.log('   - img_url:', data.data.wbi_img.img_url);
        console.log('   - sub_url:', data.data.wbi_img.sub_url);
        
        // 测试当前的正则表达式
        console.log('7. 测试正则表达式:');
        const imgKeyMatch = data.data.wbi_img.img_url?.match(/([^\/_]+)(?=\.jpg)/);
        const subKeyMatch = data.data.wbi_img.sub_url?.match(/([^\/_]+)(?=\.jpg)/);
        
        console.log('   - imgKeyMatch:', imgKeyMatch);
        console.log('   - subKeyMatch:', subKeyMatch);
        
        if (!imgKeyMatch || !subKeyMatch) {
          console.log('\n❌ 正则表达式匹配失败!');
          console.log('\n8. 尝试其他可能的正则表达式:');
          
          // 尝试更宽松的正则
          const altImgMatch = data.data.wbi_img.img_url?.match(/([a-zA-Z0-9]+)(?=\.[a-zA-Z]+$)/);
          const altSubMatch = data.data.wbi_img.sub_url?.match(/([a-zA-Z0-9]+)(?=\.[a-zA-Z]+$)/);
          
          console.log('   - 备选正则 img:', altImgMatch);
          console.log('   - 备选正则 sub:', altSubMatch);
        }
      } else {
        console.log('\n❌ wbi_img字段不存在!');
        console.log('\n6. data字段所有键:');
        console.log(Object.keys(data.data));
      }
    }

  } catch (error) {
    console.error('测试过程中出错:', error);
  }
}

testWBIAPI();
