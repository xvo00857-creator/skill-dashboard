# 页面结构说明 — 登录页与仪表盘设计系统

## 1. 登录页 `/login`

### 布局结构

```
.auth-layout (flex 分屏, min-height: 100vh)
├── .auth-hero (左侧品牌区, flex:1, 仅 ≥900px 显示)
│   ├── .auth-hero-brand          品牌标识（Logo + 名称）
│   ├── .auth-hero-content        主标语与描述
│   │   ├── h1                    "欢迎回来"
│   │   └── p                     产品描述文案
│   └── .auth-hero-stats          三项数据展示
│       └── .auth-hero-stat ×3    （活跃团队 / 可用性 / 评分）
└── .auth-main (右侧表单区, flex:1)
    └── .auth-card (max-width: 448px)
        ├── .auth-card-header     标题 + 副标题
        ├── .alert.alert-danger   错误提示（默认隐藏）
        ├── form
        │   ├── .form-group       邮箱输入
        │   ├── .form-group       密码输入（含显示/隐藏按钮）
        │   ├── .form-row         记住我 + 忘记密码
        │   └── button.btn-primary 登录按钮
        ├── .divider              "或使用以下方式"
        ├── .btn-social ×2        Google / GitHub 登录
        └── .auth-footer          注册引导链接
```

### 响应式行为

- 视口宽度 ≥ 900px：左右分屏，左侧品牌区可见。
- 视口宽度 < 900px：仅显示右侧表单区，表单居中。

### 交互状态

| 元素 | 状态 | 表现 |
|:---|:---|:---|
| 邮箱/密码输入框 | focus | 边框变主色 + 外发光 |
| 密码显示按钮 | click | 切换 input type |
| 登录按钮 | hover | 主色加深 |
| 登录按钮 | disabled | 透明度 50%，禁止点击 |
| 错误提示 | 表单校验失败 | 显示红色 alert |

---

## 2. 仪表盘页 `/dashboard`

### 布局结构

```
body
├── .sidebar (固定左侧, width: 256px)
│   ├── .sidebar-brand            Logo + 产品名
│   ├── .sidebar-nav
│   │   ├── .sidebar-section-label "主菜单"
│   │   ├── .sidebar-link ×5      仪表盘/用户/项目/分析/任务
│   │   │   └── .sidebar-link-icon 内联 SVG 图标
│   │   ├── .sidebar-section-label "系统"
│   │   └── .sidebar-link         设置
│   └── .sidebar-footer           当前用户信息（头像+姓名+角色）
├── .topbar (固定顶部, left:256px)
│   ├── .topbar-search            搜索框
│   └── .topbar-actions
│       ├── .icon-button          通知（含红点）
│       ├── .icon-button          帮助
│       └── .avatar               用户头像
└── .main (margin-left: 256px, padding-top: 56px)
    └── .content (max-width: 1280px, 居中)
        ├── .page-header
        │   ├── 标题 + 副标题
        │   └── 操作按钮组（导出 / 新建项目）
        ├── .stats-grid (4 列自适应)
        │   └── .card.stat-card ×4
        │       ├── .stat-card-top   标签 + 图标
        │       ├── .stat-card-value 数值
        │       └── .stat-card-change 涨跌百分比
        ├── .chart-grid (2 列)
        │   ├── .card               访问趋势柱状图
        │   │   └── .bar-chart      7 根 CSS 柱
        │   └── .card               流量来源环形图
        │       └── .donut + .legend
        └── .card                   最近注册用户
            └── .table              5 行用户数据
```

### 响应式行为

- 统计卡片：`auto-fit, minmax(14rem, 1fr)`，窄屏自动堆叠。
- 图表区：≥900px 两列，<900px 单列。
- 侧边栏：固定宽度，小屏可通过后续增加汉堡菜单控制（当前为桌面优先）。
- 表格：外层 `.table-wrap` 横向滚动，避免小屏溢出。

### 交互状态

| 元素 | 状态 | 表现 |
|:---|:---|:---|
| 侧边栏链接 | hover | 半透明白底 |
| 侧边栏链接 | active | 主色背景 |
| 搜索框 | focus | 边框高亮（继承 input 样式） |
| 图标按钮 | hover | 浅灰背景 |
| 表格行 | hover | 浅灰背景 |
| 柱状图 | hover | 透明度变化 |
| 按钮 | hover | 背景色变化 |

---

## 3. 文件组织

```
stitch-design-system/
├── tokens/
│   └── design-tokens.css      # 设计令牌（颜色/字体/间距/阴影/布局）
├── components/
│   └── components.css         # 全部可复用组件样式
├── pages/
│   ├── login.html             # 登录页（CSS 内联，自包含）
│   └── dashboard.html         # 仪表盘页（CSS 内联，自包含）
├── docs/
│   ├── component-mapping.md   # 组件映射表
│   ├── page-structure.md      # 本文件
│   └── stitch-sync-plan.md    # Stitch 同步方案
└── scripts/
    └── verify.py              # 无依赖验证脚本
```

## 4. 技术约束

- **零运行时依赖**：不使用 React/Vue/Tailwind/Bootstrap/Chart.js 等任何第三方库。
- **图标**：全部使用内联 SVG（Feather Icons 风格），无图标字体。
- **图表**：柱状图用 div 高度模拟，环形图用 `conic-gradient` 实现，无 JS 图表库。
- **浏览器兼容**：支持现代浏览器（Chrome/Edge/Firefox/Safari 近两年版本）。
- **页面自包含**：`pages/` 下 HTML 内联 CSS，可直接双击打开或上传 Stitch。
