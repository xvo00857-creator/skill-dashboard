import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'VitePress 文档',
  description: '基于 Vite 和 Vue 3 的静态站点生成器文档',
  lang: 'zh-CN',
  lastUpdated: true,
  cleanUrls: true,
  ignoreDeadLinks: true,

  markdown: {
    lineNumbers: true,
    toc: { level: [1, 2, 3] }
  },

  themeConfig: {
    siteTitle: 'VitePress 文档',

    nav: [
      { text: '指南', link: '/guide/installation', activeMatch: '/guide/' },
      { text: '配置参考', link: '/reference/config', activeMatch: '/reference/' }
    ],

    sidebar: {
      '/guide/': [
        {
          text: '指南',
          items: [
            { text: '安装', link: '/guide/installation' },
            { text: '快速开始', link: '/guide/getting-started' },
            { text: '故障排查', link: '/guide/troubleshooting' }
          ]
        }
      ],
      '/reference/': [
        {
          text: '参考',
          items: [
            { text: '配置参考', link: '/reference/config' }
          ]
        }
      ]
    },

    search: {
      provider: 'local'
    },

    socialLinks: [
      { icon: 'github', link: 'https://github.com/vuejs/vitepress' }
    ],

    footer: {
      message: '基于 MIT 许可证发布',
      copyright: 'Copyright © 2024 VitePress 文档'
    },

    outline: {
      level: [2, 3],
      label: '本页目录'
    },

    docFooter: {
      prev: '上一页',
      next: '下一页'
    },

    lastUpdated: {
      text: '最后更新于',
      formatOptions: {
        dateStyle: 'short',
        timeStyle: 'medium'
      }
    },

    darkModeSwitchLabel: '外观',
    sidebarMenuLabel: '菜单',
    returnToTopLabel: '回到顶部'
  }
})
