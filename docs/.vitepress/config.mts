import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'ACField',
  description: 'AClab 开放式多机器人实验平台 — 从算法想法走向可解释的实车实验。',
  lang: 'zh-CN',
  base: '/acfield/',
  cleanUrls: true,
  lastUpdated: true,
  head: [
    ['link', { rel: 'icon', type: 'image/svg+xml', href: '/acfield/favicon.svg' }],
    ['meta', { name: 'theme-color', content: '#123d38' }],
    ['meta', { property: 'og:title', content: 'ACField · AClab' }],
    ['meta', { property: 'og:description', content: 'An Open Multi-Robot Testbed for Multi-Agent Control' }]
  ],
  sitemap: { hostname: 'https://yaoqih.github.io/acfield/' },
  markdown: { lineNumbers: true },
  themeConfig: {
    logo: '/favicon.svg',
    siteTitle: 'ACField',
    nav: [
      { text: '开始使用', link: '/guide/quickstart' },
      { text: '设计与架构', link: '/design/philosophy' },
      { text: '参考硬件', link: '/hardware/overview' },
      { text: 'English', link: '/en/' }
    ],
    sidebar: [
      { text: '认识 ACField', items: [
        { text: '平台概览', link: '/guide/overview' },
        { text: '快速开始', link: '/guide/quickstart' },
        { text: '能力与验证状态', link: '/guide/status' }
      ] },
      { text: '设计与思考', items: [
        { text: '设计理念', link: '/design/philosophy' },
        { text: '系统架构', link: '/design/architecture' },
        { text: '关键设计决策', link: '/design/decisions' },
        { text: '研究边界与实验有效性', link: '/design/research' }
      ] },
      { text: '使用与开发', items: [
        { text: '运行与配置', link: '/guide/configuration' },
        { text: '接入控制算法', link: '/guide/control' },
        { text: '视觉定位与标定', link: '/guide/localization' },
        { text: '记录与复现', link: '/guide/recording' },
        { text: '故障排查', link: '/guide/troubleshooting' }
      ] },
      { text: '接口参考', items: [
        { text: 'HTTP 与 WebSocket', link: '/reference/api' },
        { text: '设备协议与时序', link: '/reference/protocol' }
      ] },
      { text: '参考硬件', items: [
        { text: '物料与机械设计', link: '/hardware/overview' },
        { text: '固件与首车验收', link: '/hardware/bringup' }
      ] },
      { text: '共同维护', items: [
        { text: '路线图', link: '/community/roadmap' },
        { text: '贡献与版本维护', link: '/community/contributing' },
        { text: '文档站与部署', link: '/community/documentation' },
        { text: '引用与许可', link: '/community/citation' }
      ] }
    ],
    socialLinks: [{ icon: 'github', link: 'https://github.com/yaoqih/acfield' }],
    search: { provider: 'local' },
    outline: { label: '本页内容', level: [2, 3] },
    editLink: { pattern: 'https://github.com/yaoqih/acfield/edit/main/docs/:path', text: '在 GitHub 上改进此页' },
    lastUpdated: { text: '最后更新' },
    docFooter: { prev: '上一篇', next: '下一篇' },
    footer: { message: 'Built for shared experiments. Maintained by AClab.', copyright: 'Copyright © 2026 AClab contributors · Apache-2.0' }
  }
})
