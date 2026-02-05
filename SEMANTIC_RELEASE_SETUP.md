# Semantic Release 配置说明

## 首次使用前的设置

### 1. 配置 GitHub Token

Semantic Release 需要 GitHub token 来创建 releases：

1. 访问：https://github.com/settings/tokens
2. 点击 **"Generate new token"**（classic）
3. 选择权限：
   - ✅ **repo** (完整的 repository 权限）
4. 命名：`semantic-release`
5. 点击 **"Generate token"**
6. 复制 token（只显示一次！）

### 2. 配置环境变量（可选）

#### 方式 A：本地运行
```bash
export GITHUB_TOKEN=你的_github_token
npm run release
```

#### 方式 B：GitHub Actions 运行（可选）

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    branches:
      - master

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: actions/setup-node@v4
        with:
          node-version: '20'

      - run: npm ci
      - run: npm run build

      - name: Release
        run: npm run release
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GIT_CREDENTIALS: ${{ secrets.GITHUB_TOKEN }}
          NPM_TOKEN: ${{ secrets.NPM_TOKEN }}
```

## 使用方法

### Conventional Commits 格式

Semantic Release 根据 commit message 自动确定版本号：

- `fix:` 补丁版本（1.0.1 → 1.0.2）
- `feat:` 次版本（1.0.0 → 1.1.0）
- `BREAKING CHANGE:` 或 `feat!:` 主要版本（1.0.0 → 2.0.0）

### 发布命令

```bash
# 在本地手动发布
npm run release

# 或在 GitHub Actions 中自动发布
# 推送包含 conventional commit 的更改会自动触发
```

### Commit 示例

```bash
# 功能更新 → 1.1.0
git commit -m "feat: add new feature"

# Bug 修复 → 1.0.2
git commit -m "fix: resolve authentication issue"

# 破坏性变更 → 2.0.0
git commit -m "feat!: change API structure"
```

## 优势

1. **自动化**：自动处理版本号
2. **Changelog**：自动生成更新日志
3. **Release Notes**：自动创建 GitHub Release
4. **npm 发布**：自动发布到 npm
5. **Git Tags**：自动创建版本标签

## 注意事项

- 首次发布需要手动触发（或添加一个发布 commit）
- 之后的发布会根据 commit 自动处理
- 不需要手动修改 package.json 中的版本号
- 首次运行会提示输入 npm token
