// 测试 USER_AGENT 环境变量加载
import { config } from './dist/config.js';

console.log('当前 userAgent 配置:', config.userAgent);
console.log('USER_AGENT 环境变量:', process.env.USER_AGENT);
console.log('是否使用了环境变量:', process.env.USER_AGENT && config.userAgent === process.env.USER_AGENT);
