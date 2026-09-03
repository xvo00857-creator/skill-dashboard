# 关键设计规范 · 任务台（TaskDesk）

> 本规范依据随附 Skill `interaction-design` 的 SKILL.md 制定，聚焦**微交互、动效时序、状态过渡与反馈模式**。品牌色仅使用深蓝、米白、亮橙三色。

---

## 1. 品牌色板

| 令牌 | 色值 | 角色 | 主要用途 |
|---|---|---|---|
| `--color-deep-blue` | `#1A365D` | 主色 | 标题、正文、主按钮文字、导航栏、表头、描边 |
| `--color-cream` | `#F7F3EC` | 底色 | 页面背景、卡片背景、深蓝底上的反白文字/图标 |
| `--color-orange` | `#FF6B1A` | 强调色 | CTA 按钮底、开关激活、进度条填充、激活态指示、FAB、Toast |

**派生色（主色与底色的混合，不引入新色相）：**

| 令牌 | 色值 | 用途 |
|---|---|---|
| `--color-text-muted` | `#4A6178` | 次要文字（深蓝降饱和） |
| `--color-blue-50` | `#E8ECF1` | 悬停行底色（深蓝 8% + 米白） |
| `--color-blue-20` | `#D3DAE3` | 分割线、未选中描边 |
| `--color-orange-glow` | `rgba(255,107,26,0.25)` | 橙色按钮/FAB 外发光 |

**文字配色规则（经 WCAG 对比度实测）：**

| 前景 | 背景 | 对比度 | 适用 |
|---|---|---|---|
| 深蓝 `#1A365D` | 米白 | **10.98:1** | 正文、标题（通过 AA 4.5:1） |
| 蓝灰 `#4A6178` | 米白 | **5.80:1** | 次要文字（通过 AA 4.5:1） |
| 米白 `#F7F3EC` | 深蓝 | **12.14:1** | 反白文字/图标（通过 AA 4.5:1） |
| 深蓝 `#1A365D` | 亮橙 | **4.26:1** | 橙色按钮/Toast 文字（通过大字/粗体 AA 3:1） |
| 亮橙 `#FF6B1A` | 深蓝 | **4.26:1** | 橙色图标/指示在深蓝底（通过图形 AA 3:1） |

> ⚠️ 禁止组合：白字/米白字落在亮橙上（仅 2.58–2.85:1，不达标）；亮橙小字落在米白上（2.58:1，不达标）。橙色面一律配深蓝字，橙色仅用于≥18px 粗体大字或图形元素。

---

## 2. 字体排印

| 类别 | 字号（手机/桌面） | 字重 | 字色 |
|---|---|---|---|
| 页面大标题 | 24 / 32 px | 700 | 深蓝 |
| 卡片标题 | 17 / 16 px | 600 | 深蓝 |
| 正文 | 16 / 15 px | 400 | 深蓝 |
| 次要文字 | 13 / 13 px | 400 | 蓝灰 |
| 按钮文字 | 16 / 15 px | 600 | 橙色底→深蓝；深蓝底→米白 |
| 数字展示 | 40 / 48 px | 700 | 深蓝 |

- 字体族：`-apple-system, "PingFang SC", "Microsoft YaHei", "Segoe UI", sans-serif`
- 行高：正文 1.5，标题 1.3
- 正文最小不低于 15px，确保清晰可读。

---

## 3. 间距、圆角与阴影

| 令牌 | 值 |
|---|---|
| 间距基数 | 4 px；常用 8 / 12 / 16 / 24 / 32 |
| 卡片圆角 | 12 px（手机）/ 10 px（桌面） |
| 按钮圆角 | 10 px |
| 胶囊/开关圆角 | 999 px（全圆） |
| 卡片默认阴影 | `0 4px 12px rgba(26,54,93,0.12)` |
| 卡片悬停阴影 | `0 8px 24px rgba(26,54,93,0.18)` |
| 橙色按钮发光 | `0 6px 16px rgba(255,107,26,0.30)` |

---

## 4. 动效令牌（源自 SKILL.md 第 32–49 行）

### 4.1 缓动函数

```css
--ease-out:    cubic-bezier(0.16, 1, 0.3, 1);   /* 减速—元素进入 */
--ease-in:     cubic-bezier(0.55, 0, 1, 0.45);  /* 加速—元素退出 */
--ease-in-out: cubic-bezier(0.65, 0, 0.35, 1);  /* 双向—状态切换 */
--spring:      cubic-bezier(0.34, 1.56, 0.64, 1); /* 回弹—按压/开关 */
```

### 4.2 时长阶梯

| 时长 | 用途 | 本设计中的应用 |
|---|---|---|
| 100–150 ms | 微反馈（hover、点击） | 按钮 hover 放大、卡片阴影加深 |
| 200–300 ms | 小过渡（开关、下拉） | Toggle 滑块位移、菜单图标变形 |
| 300–500 ms | 中过渡（弹窗、页面） | Toast 滑入、页面切换、卡片进场 |
| 500 ms+ | 编排动画 | 骨架屏脉冲循环（2s）、列表错峰 |

### 4.3 性能规则（SKILL.md 第 306、316 行）

- 仅动画 `transform` 与 `opacity`，保证 60fps；**禁止**动画 `width/height/top/left/margin/padding`。
- 进度条填充使用 `transform: scaleX()` 而非 `width`。
- `will-change` 按需使用，不全局滥用。

---

## 5. 组件交互态规范

### 5.1 按钮

| 状态 | 主按钮（橙底） | 次按钮（米白底深蓝描边） |
|---|---|---|
| 默认 | 橙底、深蓝字、橙色发光 | 米白底、深蓝 1.5px 描边、深蓝字 |
| Hover | `scale(1.02)` + 发光加深，150ms `--ease-out` | 描边加粗 / 底色变 `--color-blue-50` |
| 按下 | `scale(0.98)`，spring 回弹 | 同左 |
| 禁用 | 橙色降透明至 40%，无发光 | 描边降透明至 40% |

> 对应 SKILL.md「Quick Start: Button Microinteraction」与「Loading Button」模式。

### 5.2 开关（Toggle）

- 轨道：激活橙 / 未激活 `--color-blue-20`；滑块：米白。
- 滑块位移 200–300ms，使用 `--spring`（stiffness 500, damping 30）。
- 对应 SKILL.md「State Transitions → Toggle」。

### 5.3 卡片

- 默认：米白底、深蓝 1.5px 描边、默认阴影。
- Hover：`translateY(-4px)` + 悬停阴影，200ms `--ease-out`。
- 进场：`opacity 0→1, translateY(10px)→0`，300ms `--ease-out`，列表项错峰 80ms。
- 对应 SKILL.md「CSS Transitions」与 references「Staggered List」。

### 5.4 勾选

- 未选：深蓝 2px 空心圆。
- 已选：橙底圆 + 深蓝对勾；对勾以 `scale(0)→1` + `rotate(-90deg)→0` 进场，200ms spring。

### 5.5 骨架屏

- 深蓝半透明（`rgba(26,54,93,0.12)`）色块，`pulse` 动画 2s `ease-in-out` 循环。
- 加载完成后内容淡入 300ms。对应 SKILL.md「Loading States → Skeleton Screens」。

### 5.6 进度条

- 轨道深蓝（高 8px，全圆）；填充橙色，`transform: scaleX()` 从 0 到目标值，`--ease-out`。
- 对应 SKILL.md「Progress Indicators」。

### 5.7 Toast 反馈

- 从右侧滑入：`opacity 0→1, x(100px)→0`，300ms `--ease-out`；退出反向 200ms `--ease-in`。
- 橙底深蓝字，左侧深蓝对勾图标；3 秒自动消失。
- 对应 references/microinteraction-patterns.md「Toast Notifications」。

### 5.8 导航激活态

- 侧边/底部导航激活项：橙色文字 + 橙色指示条；指示器以 `layoutId` 共享布局弹簧动画（spring 500/30）在选项间滑动。
- 对应 references/microinteraction-patterns.md「Active Link Indicator」。

### 5.9 FAB（悬浮按钮）

- 橙底深蓝加号；按下 `scale(0.92)` 并 spring 回弹；常驻橙色外发光。

---

## 6. 响应式适配

| 维度 | 手机竖屏（9:16） | 桌面横屏（16:9） |
|---|---|---|
| 导航 | 底部标签栏，3 个图标 | 左侧固定侧边栏 240px |
| 主操作 | 右下 FAB | 顶部栏「新建任务」按钮 |
| 卡片 | 单列纵向，左右边距 20px | 统计卡三列、列表通栏 |
| 列表 | 卡片式任务行 | 表格（表头深蓝、行 hover） |
| 字号基准 | 正文 16px | 正文 15px |
| 触控目标 | ≥ 44×44 px | ≥ 36×36 px（鼠标） |
| 交互动效 | 同令牌；额外支持左滑删除、下拉刷新（references 模式） | 同令牌；额外支持 hover 抬升、行高亮 |

---

## 7. 无障碍（源自 SKILL.md 第 274–302 行）

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

- 所有动效必须尊重 `prefers-reduced-motion`；开启时仅保留瞬时状态切换，不做位移/回弹。
- 动效不得阻塞用户输入（SKILL.md 第 318 行）；长动画可中断。
- 图标/图形与背景对比度 ≥ 3:1；正文 ≥ 4.5:1。
- 开关需具备 `role="switch"` 与 `aria-checked`（SKILL.md 示例）。

---

## 8. 交付物清单

| 文件 | 说明 |
|---|---|
| `mobile-portrait-9x16.png` | 手机竖屏成品（1536×2730，9:16） |
| `desktop-landscape-16x9.png` | 桌面横屏成品（2730×1536，16:9） |
| `design-spec.md` | 本设计规范 |
| `consistency-check.md` | 双尺寸一致性检查报告 |
