# 文档站与部署

文档使用 VitePress，源文件位于 `docs/`，与代码一同评审。GitHub Pages 只托管静态网站，不运行控制服务。

## 本地预览

```bash
npm ci
npm run docs:dev
# 构建与预览生产产物
npm run docs:build
npm run docs:preview
```

构建输出为 `docs/.vitepress/dist/`，不提交到 Git。站点支持本地全文搜索、深浅色模式、移动端导航和编辑链接。

## GitHub Actions

`.github/workflows/docs.yml` 在 main 提交、PR 与手动触发时构建。PR 只检查构建；main 与手动运行在构建成功后部署，使用 GitHub 原生 Pages artifact 与短期身份令牌，不需要保存个人访问令牌。

首次需要在仓库 **Settings → Pages → Build and deployment → Source** 选择 **GitHub Actions**。维护者也可以通过 GitHub API 创建 `build_type=workflow` 的 Pages 站点。启用后，后续 main 提交自动更新。

当前站点地址：**https://yaoqih.github.io/acfield/**。项目站点的 `base` 为 `/acfield/`，配置位于 `docs/.vitepress/config.mts`。仓库改名、迁移组织或使用自定义域名时，要一起调整 base、站点地图、站点图标与引用 URL。

## 编辑内容

操作指南说明用户如何完成任务；设计文档说明选型理由、代价与改变条件；参考页描述准确接口与参数；能力状态页区分实现、软件验证和实物证据。

本地构建会检查 Markdown 链接。改动首页或布局后还应检查桌面与移动端，确认可读性、图片和导航。新增页面时加入侧栏；不要把计划功能写成已交付能力。
