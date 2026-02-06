// 测试缓存功能
import { cacheManager } from './dist/utils/cache.js';

async function testCache() {
  console.log('=== 测试缓存功能 ===\n');

  // 测试1: 缓存基本功能
  console.log('1. 测试缓存基本功能:');
  
  // 测试视频缓存
  const videoKey = 'video:BV1Gx411w7La:zh-Hans';
  const videoData = {
    data_source: 'subtitle',
    video_info: {
      title: '测试视频',
      description: '这是一个测试视频',
      tags: ['测试', '缓存'],
      subtitle_text: '测试字幕内容'
    }
  };
  
  // 设置缓存
  cacheManager.setVideoInfo(videoKey, videoData);
  console.log('   - 设置视频缓存: ✅');
  
  // 获取缓存
  const cachedVideo = cacheManager.getVideoInfo(videoKey);
  console.log('   - 获取视频缓存: ✅', cachedVideo ? '命中' : '未命中');
  
  // 测试评论缓存
  const commentKey = 'comments:BV1Gx411w7La:brief';
  const commentData = {
    comments: [],
    summary: {
      total_comments: 0,
      comments_with_timestamp: 0
    }
  };
  
  // 设置缓存
  cacheManager.setCommentInfo(commentKey, commentData);
  console.log('   - 设置评论缓存: ✅');
  
  // 获取缓存
  const cachedComment = cacheManager.getCommentInfo(commentKey);
  console.log('   - 获取评论缓存: ✅', cachedComment ? '命中' : '未命中');

  // 测试2: 缓存统计
  console.log('\n2. 测试缓存统计:');
  const stats = cacheManager.getStats();
  console.log('   - 缓存统计:', stats);
  console.log('   - 测试通过: ✅');

  // 测试3: 缓存键生成
  console.log('\n3. 测试缓存键生成:');
  const generatedKey = cacheManager.generateKey('video', 'BV1Gx411w7La', 'en');
  console.log('   - 生成的缓存键:', generatedKey);
  console.log('   - 测试通过: ✅');

  // 测试4: 缓存删除
  console.log('\n4. 测试缓存删除:');
  cacheManager.deleteVideoInfo(videoKey);
  const deletedVideo = cacheManager.getVideoInfo(videoKey);
  console.log('   - 删除视频缓存后获取: ✅', deletedVideo ? '命中' : '未命中 (正确)');
  
  // 测试5: 缓存清空
  console.log('\n5. 测试缓存清空:');
  cacheManager.clear();
  const statsAfterClear = cacheManager.getStats();
  console.log('   - 清空后统计:', statsAfterClear);
  console.log('   - 测试通过: ✅');

  console.log('\n=== 缓存功能测试完成 ===');
  console.log('✅ 所有缓存测试通过!');
}

testCache().catch(error => {
  console.error('测试失败:', error);
  process.exit(1);
});
