# 组件映射表 — 登录页与仪表盘设计系统

> 本文档定义了设计系统中所有可复用组件及其在各页面中的使用情况。
> 所有组件均基于 `tokens/design-tokens.css` 中的设计令牌构建，零运行时依赖。

## 组件清单

| 组件名 | CSS 类名 | 说明 | 变体 |
|:---|:---|:---|:---|
| 按钮 | `.btn` | 通用操作按钮 | `.btn-primary` `.btn-secondary` `.btn-ghost` `.btn-danger` `.btn-block` `.btn-lg` `.btn-sm` |
| 表单输入 | `.form-input` | 文本/邮箱/密码输入框 | `.form-input-error` |
| 表单标签 | `.form-label` | 输入框标签 | — |
| 表单组 | `.form-group` | 标签+输入+提示的容器 | — |
| 复选框 | `.form-check` | 带标签的复选框 | — |
| 卡片 | `.card` | 内容容器 | `.card-header` `.card-body` `.card-footer` `.card-title` |
| 徽章 | `.badge` | 状态/标签标记 | `.badge-primary` `.badge-success` `.badge-warning` `.badge-danger` `.badge-gray` |
| 头像 | `.avatar` | 用户头像（首字母） | `.avatar-sm` `.avatar-lg` |
| 侧边栏 | `.sidebar` | 深色导航侧栏 | `.sidebar-brand` `.sidebar-nav` `.sidebar-link` `.sidebar-section-label` `.sidebar-footer` |
| 顶部栏 | `.topbar` | 搜索+操作栏 | `.topbar-search` `.topbar-actions` `.icon-btn` |
| 统计卡片 | `.stat-card` | 指标展示卡 | `.stat-card-label` `.stat-card-value` `.stat-card-change` |
| 表格 | `.table` | 数据表格 | `.table-wrap` |
| 提示条 | `.alert` | 内联消息 | `.alert-info` `.alert-success` `.alert-warning` `.alert-danger` |
| 分隔线 | `.divider` | 带文字的水平分隔线 | — |
| 社交登录按钮 | `.btn-social` | 第三方登录入口 | — |

## 页面 × 组件映射

### `/login` 登录页

| 区域 | 使用的组件 |
|:---|:---|
| 左侧品牌区 | 自定义布局 `.auth-hero`（使用令牌：颜色、字号、间距） |
| 标题区 | 排版令牌（`.auth-card-header h2/p`） |
| 错误提示 | `.alert .alert-danger` |
| 邮箱输入 | `.form-group` + `.form-label` + `.form-input` |
| 密码输入 | `.form-group` + `.form-label` + `.form-input` + `.form-input-icon` |
| 记住我 | `.form-check`（复选框） |
| 忘记密码 | `.link` |
| 登录按钮 | `.btn .btn-primary .btn-lg .btn-block` |
| 分隔线 | `.divider` |
| 社交登录 | `.btn-social`（Google / GitHub） |
| 注册链接 | `.link` |

### `/dashboard` 仪表盘页

| 区域 | 使用的组件 |
|:---|:---|
| 侧边栏 | `.sidebar` + `.sidebar-brand` + `.sidebar-nav` + `.sidebar-link`（含 `.active`）+ `.sidebar-section-label` + `.sidebar-footer` + `.avatar` |
| 顶部栏 | `.topbar` + `.topbar-search` + `.icon-btn`（含通知红点）+ `.avatar` |
| 页头 | `.page-title` + `.page-subtitle` + `.btn .btn-secondary` + `.btn .btn-primary` |
| 统计卡片行 | `.stats-grid` + `.card .stat-card`（4 个，含 `.stat-card-icon` 变体） |
| 柱状图 | `.card` + 纯 CSS `.bar-chart` / `.bar`（无图表库依赖） |
| 环形图 | `.card` + 纯 CSS `.donut` / `.legend`（conic-gradient，无图表库依赖） |
| 用户表格 | `.card` + `.table-wrap` + `.table` + `.avatar` + `.badge`（4 种状态色） |

## 设计令牌引用关系

```
design-tokens.css
├── 颜色令牌
│   ├── 品牌色 → .btn-primary, .sidebar-link.active, .avatar, .stat-card-icon
│   ├── 中性色 → body, .card, .table, .topbar, .form-input
│   ├── 语义色 → .badge-*, .alert-*, .stat-card-change
│   └── 表面色 → .sidebar(深色), .auth-hero(渐变)
├── 字体令牌 → 全局排版、标题、表格、按钮
├── 间距令牌 → 所有组件的 padding/margin/gap
├── 圆角令牌 → .card(lg), .btn(md), .avatar(full), .badge(full)
├── 阴影令牌 → .card(sm)
├── 布局令牌 → --sidebar-width, --topbar-height, --auth-card-max-width
└── 过渡令牌 → .btn, .sidebar-link, .form-input
```

## 复用原则

1. **令牌优先**：所有颜色、间距、字号必须引用 CSS 自定义属性，禁止硬编码像素值。
2. **单一职责**：每个组件类只负责一个视觉模式，通过修饰类（modifier）组合变体。
3. **零依赖**：不引入任何 CSS 框架、JS 库或图标字体；图标使用内联 SVG。
4. **自包含页面**：`pages/` 下的 HTML 内联全部 CSS，可独立上传到 Stitch 或直接浏览器打开。
