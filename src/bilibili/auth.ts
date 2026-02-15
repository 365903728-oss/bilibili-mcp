/**
 * B站认证模块
 * 处理用户登录和认证相关功能
 */

import { config } from '../config.js';
import { credentialManager, BilibiliCredentials } from '../utils/credentials.js';
import { logger } from '../utils/logger.js';

export interface LoginResponse {
  code: number;
  message: string;
  data?: {
    token_info?: {
      mid: string;
      access_token: string;
      refresh_token: string;
      expires_in: number;
    };
  };
}

export interface UserInfo {
  mid: string;
  name: string;
  sex: string;
  face: string;
  sign: string;
  rank: number;
  level: number;
  jointime: number;
  moral: number;
  silence: number;
  coins: number;
  birthday: number;
  identification: number;
  vip: {
    type: number;
    status: number;
    due_date: number;
    vip_pay_type: number;
    theme_type: number;
  };
}

export class BilibiliAuth {
  /**
   * 用户登录
   * @param username 用户名/手机号/邮箱
   * @param password 密码
   */
  static async login(username: string, password: string): Promise<BilibiliCredentials> {
    try {
      logger.info('Attempting to login to Bilibili', { username });

      const response = await fetch('https://passport.bilibili.com/x/passport-login/web/key?hash=qr_login', {
        method: 'GET',
        headers: {
          'User-Agent': config.userAgent,
          'Referer': config.referer,
        },
      });

      const keyData = await response.json();

      if (keyData.code !== 0) {
        throw new Error(`Failed to get login key: ${keyData.message}`);
      }

      const loginData = {
        username,
        password,
        keepalive: true,
        key: keyData.data.hash,
        timestamp: keyData.data.timestamp,
      };

      const loginResponse = await fetch('https://passport.bilibili.com/x/passport-login/web/login', {
        method: 'POST',
        headers: {
          'User-Agent': config.userAgent,
          'Referer': config.referer,
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams(loginData as any).toString(),
      });

      const loginResult = await loginResponse.json() as LoginResponse;

      if (loginResult.code !== 0) {
        throw new Error(`Login failed: ${loginResult.message}`);
      }

      if (!loginResult.data?.token_info) {
        throw new Error('Login successful but no token info received');
      }

      const tokenInfo = loginResult.data.token_info;
      const credentials: BilibiliCredentials = {
        sessdata: tokenInfo.access_token,
        bili_jct: tokenInfo.access_token.substring(0, 32),
        dedeuserid: tokenInfo.mid,
        expiresAt: Date.now() + tokenInfo.expires_in * 1000,
      };

      credentialManager.setCredentials(credentials);
      logger.info('Login successful', { mid: tokenInfo.mid });

      return credentials;
    } catch (error) {
      logger.error('Login failed', { error: error instanceof Error ? error.message : error });
      throw error;
    }
  }

  /**
   * 获取用户信息
   */
  static async getUserInfo(): Promise<UserInfo> {
    try {
      const headers = credentialManager.getAuthHeaders();

      if (!headers['Cookie']) {
        throw new Error('Not logged in');
      }

      const response = await fetch('https://api.bilibili.com/x/space/acc/info', {
        method: 'GET',
        headers: {
          'User-Agent': config.userAgent,
          'Referer': config.referer,
          ...headers,
        },
      });

      const data = await response.json();

      if (data.code !== 0) {
        throw new Error(`Failed to get user info: ${data.message}`);
      }

      return data.data;
    } catch (error) {
      logger.error('Failed to get user info', { error: error instanceof Error ? error.message : error });
      throw error;
    }
  }

  /**
   * 检查登录状态
   */
  static checkLoginStatus(): boolean {
    return credentialManager.isLoggedIn();
  }

  /**
   * 登出
   */
  static logout(): void {
    credentialManager.clearCredentials();
    logger.info('Logged out successfully');
  }

  /**
   * 从环境变量设置凭证
   */
  static setupFromEnv(): boolean {
    const credentials = credentialManager.loadFromEnv();
    if (credentials) {
      logger.info('Credentials loaded from environment variables');
      return true;
    }
    return false;
  }

  /**
   * 检查并刷新登录状态
   */
  static async checkAndRefreshLogin(): Promise<boolean> {
    if (!credentialManager.isLoggedIn()) {
      return false;
    }

    // 如果凭证即将过期，尝试刷新
    if (credentialManager.isExpiringSoon()) {
      logger.warn('Credentials are expiring soon, attempting to refresh');
      try {
        // 获取用户信息来验证凭证是否仍然有效
        await this.getUserInfo();
        // 如果成功，刷新过期时间
        credentialManager.refreshExpiration();
        logger.info('Credentials refreshed successfully');
        return true;
      } catch (error) {
        logger.error('Failed to refresh credentials', { error: error instanceof Error ? error.message : error });
        return false;
      }
    }

    return true;
  }

  /**
   * 验证登录状态
   */
  static async validateLogin(): Promise<boolean> {
    if (!credentialManager.isLoggedIn()) {
      return false;
    }

    try {
      await this.getUserInfo();
      return true;
    } catch (error) {
      logger.error('Login validation failed', { error: error instanceof Error ? error.message : error });
      credentialManager.clearCredentials();
      return false;
    }
  }
}
