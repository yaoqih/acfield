import { defineConfig, type DefaultTheme } from 'vitepress'

// Shared route pairs keep the two navigation trees aligned.
type Item = [path: string, zh: string, en: string]
const sections: [zh: string, en: string, items: Item[]][] = [
  ['认识 ACField', 'Discover ACField', [
    ['/guide/overview', '平台概览', 'Overview'],
    ['/guide/quickstart', '快速开始', 'Quick start'],
    ['/guide/status', '能力与验证状态', 'Capabilities and evidence']
  ]],
  ['设计与思考', 'Design and rationale', [
    ['/design/philosophy', '设计理念', 'Design philosophy'],
    ['/design/architecture', '系统架构', 'Architecture'],
    ['/design/decisions', '关键设计决策', 'Design decisions'],
    ['/design/research', '研究边界与实验有效性', 'Research validity']
  ]],
  ['使用与开发', 'Usage and development', [
    ['/guide/configuration', '运行与配置', 'Configuration'],
    ['/guide/python-sdk', 'Python SDK', 'Python SDK'],
    ['/guide/control', '接入控制算法', 'Controller integration'],
    ['/guide/localization', '视觉定位与标定', 'Localization and calibration'],
    ['/guide/recording', '记录与复现', 'Recording and reproducibility'],
    ['/guide/troubleshooting', '故障排查', 'Troubleshooting']
  ]],
  ['接口参考', 'API reference', [
    ['/reference/api', 'HTTP 与 WebSocket', 'HTTP and WebSocket'],
    ['/reference/protocol', '设备协议与时序', 'Device protocol and timing']
  ]],
  ['参考硬件', 'Reference hardware', [
    ['/hardware/overview', '物料与机械设计', 'Materials and mechanical design'],
    ['/hardware/arena', '场地与相机布置', 'Arena and camera setup'],
    ['/hardware/h200s-camera', 'H200S 相机参数', 'H200S camera parameters'],
    ['/hardware/bringup', '固件与首车验收', 'Firmware and bring-up']
  ]],
  ['共同维护', 'Community and maintenance', [
    ['/community/roadmap', '路线图', 'Roadmap'],
    ['/community/contributing', '贡献与版本维护', 'Contributing and versioning'],
    ['/community/documentation', '文档站与部署', 'Documentation and deployment'],
    ['/community/citation', '引用与许可', 'Citation and licensing']
  ]]
]

function navigation(english: boolean): DefaultTheme.NavItem[] {
  const prefix = english ? '/en' : ''
  return [
    { text: english ? 'Get started' : '开始使用', link: prefix + '/guide/quickstart' },
    { text: english ? 'Design' : '设计与架构', link: prefix + '/design/philosophy' },
    { text: english ? 'Hardware' : '参考硬件', link: prefix + '/hardware/overview' }
  ]
}

function sidebar(english: boolean): DefaultTheme.SidebarItem[] {
  return sections.map(([zh, en, items]) => ({
    text: english ? en : zh,
    items: items.map(([path, zh, en]) => ({
      text: english ? en : zh, link: (english ? '/en' : '') + path
    }))
  }))
}

export default defineConfig({
  title: 'ACField', base: '/acfield/', cleanUrls: true, lastUpdated: true,
  head: [
    ['link', { rel: 'icon', type: 'image/svg+xml', href: '/acfield/favicon.svg' }],
    ['meta', { name: 'theme-color', content: '#123d38' }],
    ['meta', { property: 'og:title', content: 'ACField · AClab' }],
    ['meta', { property: 'og:description', content: 'An Open Multi-Robot Testbed for Multi-Agent Control' }]
  ],
  sitemap: { hostname: 'https://yaoqih.github.io/acfield/' },
  markdown: { lineNumbers: true },
  locales: {
    root: {
      label: '简体中文', lang: 'zh-CN', link: '/',
      description: 'AClab 开放式多机器人实验平台 — 从算法想法走向可解释的实车实验。',
      themeConfig: {
        nav: navigation(false), sidebar: sidebar(false),
        outline: { label: '本页内容', level: [2, 3] },
        editLink: { pattern: 'https://github.com/yaoqih/acfield/edit/main/docs/:path', text: '在 GitHub 上改进此页' },
        lastUpdated: { text: '最后更新' }, docFooter: { prev: '上一篇', next: '下一篇' },
        langMenuLabel: '切换语言', sidebarMenuLabel: '目录',
        returnToTopLabel: '返回顶部', skipToContentLabel: '跳转到正文',
        darkModeSwitchLabel: '外观', lightModeSwitchTitle: '切换到浅色模式', darkModeSwitchTitle: '切换到深色模式',
        footer: { message: '为共同实验而构建 · 由 AClab 维护', copyright: 'Copyright © 2026 AClab contributors · Apache-2.0' }
      }
    },
    en: {
      label: 'English', lang: 'en', link: '/en/',
      description: 'An open multi-robot testbed by AClab, from control ideas to interpretable physical experiments.',
      themeConfig: {
        nav: navigation(true), sidebar: sidebar(true),
        outline: { label: 'On this page', level: [2, 3] },
        editLink: { pattern: 'https://github.com/yaoqih/acfield/edit/main/docs/:path', text: 'Improve this page on GitHub' },
        lastUpdated: { text: 'Last updated' }, docFooter: { prev: 'Previous page', next: 'Next page' },
        langMenuLabel: 'Change language', sidebarMenuLabel: 'Menu',
        returnToTopLabel: 'Return to top', skipToContentLabel: 'Skip to content',
        darkModeSwitchLabel: 'Appearance', lightModeSwitchTitle: 'Switch to light theme', darkModeSwitchTitle: 'Switch to dark theme',
        footer: { message: 'Built for shared experiments. Maintained by AClab.', copyright: 'Copyright © 2026 AClab contributors · Apache-2.0' }
      }
    }
  },
  themeConfig: {
    logo: '/favicon.svg', siteTitle: 'ACField',
    socialLinks: [{ icon: 'github', link: 'https://github.com/yaoqih/acfield' }],
    search: { provider: 'local', options: { locales: {
      root: { translations: {
        button: { buttonText: '搜索文档', buttonAriaLabel: '搜索文档' },
        modal: { displayDetails: '显示详细列表', resetButtonTitle: '清空搜索',
          backButtonTitle: '关闭搜索', noResultsText: '没有找到相关结果',
          footer: { selectText: '选择', navigateText: '切换', closeText: '关闭' } }
      } }
    } } }
  }
})
