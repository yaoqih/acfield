import DefaultTheme from 'vitepress/theme'
import { h } from 'vue'
import { useData } from 'vitepress'
import './custom.css'
export default {
  extends: DefaultTheme,
  Layout: {
    setup() {
      const { frontmatter, lang } = useData()
      return () => h(DefaultTheme.Layout, null, {
        'doc-after': () => h('p', { class: 'platform-revision' }, [
          lang.value === 'zh-CN' ? '构建版本 ' : 'Build revision ',
          h('a', {
            href: frontmatter.value.platformCommit
              ? `https://github.com/yaoqih/acfield/tree/${frontmatter.value.platformCommit}`
              : 'https://github.com/yaoqih/acfield',
          }, frontmatter.value.platformRevision),
        ]),
      })
    },
  },
}
