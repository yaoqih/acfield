# 文档站与部署

文档使用 VitePress，源文件位于 `docs/`，与代码一同评审。GitHub Pages 只托管静态网站，不运行控制服务。

## 本地预览 {#local-preview}

```bash
npm ci
npm run docs:dev
# 构建与预览生产产物
npm run docs:build
npm run docs:preview
```

构建输出为 `docs/.vitepress/dist/`，不提交到 Git。站点支持本地全文搜索、深浅色模式、移动端导航和编辑链接。

## 双语内容与导航 {#languages-and-navigation}

中文页面直接位于 `docs/`，英文对应页在 `docs/en/` 下保持相同相对路径，例如 `guide/python-sdk.md` 与 `en/guide/python-sdk.md`。两种语言均有完整首页、导航和文档树。

VitePress 的 `locales` 配置语言菜单、导航、侧栏、搜索和界面文字。切换语言会进入当前主题的对应页；手机端在导航菜单中选择语言。英文正文中的站内链接应留在英文目录内。

新增或修改文档时同步维护两种语言，并保持对应章节锚点一致。共同导航路径位于 `docs/.vitepress/config.mts`。需要验证双向切换，不要用普通英文首页链接代替语言系统。

提交前运行浏览器回归检查：

```bash
npx playwright install chromium
npm run docs:build
npm run docs:test
```

检查覆盖页面与章节对应关系、语言双向切换、英文导航和搜索、手机端菜单。测试会自动启动生产预览；可用 `DOCS_TEST_URL` 指向已部署站点复查。

## GitHub Actions {#github-actions}

`.github/workflows/docs.yml` 在 main 提交、PR 与手动触发时构建并运行浏览器回归检查。PR 只验证；main 与手动运行在验证通过后部署，使用 GitHub 原生 Pages artifact 与短期身份令牌，不需要保存个人访问令牌。

首次需要在仓库 **Settings → Pages → Build and deployment → Source** 选择 **GitHub Actions**。维护者也可以通过 GitHub API 创建 `build_type=workflow` 的 Pages 站点。启用后，后续 main 提交自动更新。

当前站点地址：**https://yaoqih.github.io/acfield/**。项目站点的 `base` 为 `/acfield/`，配置位于 `docs/.vitepress/config.mts`。仓库改名、迁移组织或使用自定义域名时，要一起调整 base、站点地图、站点图标与引用 URL。

## 编辑内容 {#editing-content}

操作指南说明用户如何完成任务；设计文档说明选型理由、代价与改变条件；参考页描述准确接口与参数；能力状态页区分实现、软件验证和实物证据。

本地构建会检查 Markdown 链接。改动首页或布局后还应检查桌面与移动端，确认可读性、图片和导航。新增页面时加入侧栏；不要把计划功能写成已交付能力。
