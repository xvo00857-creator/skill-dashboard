# 社区活动平台 · 响应式首页（只读预演）

本目录是依据 Skill `angular-architect` 规范产出的**最小可用版本 / 只读预演**，用于评审界面与交互，**不连接任何后端、不部署、不收集个人信息**。

## 一、交付物

| 文件 | 说明 |
| --- | --- |
| `index.html` | 自包含单文件响应式首页（HTML+CSS+原生 JS），双击即可在浏览器打开，无外部依赖、无网络请求 |
| `mobile-preview.html` | 390px 手机外框预览页，用于快速查看移动端效果 |
| `angular-src/` | 按 Skill 规范编写的 Angular 17+ standalone 源码与单测（未构建，见“能力边界”） |

## 二、页面包含的四项需求

1. **活动检索**：关键词搜索框（标题/地点/描述/分类，200ms 防抖）+ 分类下拉，结果数实时播报（`aria-live`）。
2. **近期活动卡片**：6 张示例卡片，三列（平板两列、手机单列）响应式网格；含日期徽章、分类标签、时间/地点、余位状态；满员活动按钮自动禁用。
3. **报名入口**：每张卡片“立即报名”打开模态框，姓名+手机号前端校验，提交仅显示本地成功态；`e.preventDefault()` 阻止真实提交，无 `fetch`/`XHR`。
4. **移动端导航**：≤720px 显示汉堡按钮，右侧抽屉菜单，支持遮罩点击、关闭按钮、Esc 关闭；`aria-expanded`/`aria-controls`/`aria-modal` 齐全。

## 三、关键交互说明

- **检索**：输入后 200ms 防抖过滤；关键词与分类为“与”关系；无结果显示空状态。
- **报名弹窗**：
  - 打开时焦点进入姓名框，关闭后焦点回到触发按钮（原生版通过触发元素引用实现；Angular 版由父组件状态控制）。
  - 空姓名或手机号不符合 `^1[3-9]\d{9}$` 时字段标红并提示，不进入成功态。
  - 成功态明确标注“演示，未真实提交”。
- **移动端抽屉**：打开时锁定背景滚动；Esc/遮罩/关闭按钮均可关闭。
- **可访问性**：语义化标签、表单 label 关联、按钮 `aria-expanded`、弹窗 `role="dialog" aria-modal`、结果区 `aria-live="polite"`、`prefers-reduced-motion` 下关闭动画。
- **视觉**：主色 teal `#0f766e` + 强调色 amber `#d97706`（未使用靛蓝/紫色）；卡片封面用 CSS 渐变+emoji，未生成任何外部图片。

## 四、视觉验收清单

- [x] 桌面端（≥901px）：顶部导航横排、卡片三列、检索框与下拉同一行。
- [x] 平板（721–900px）：卡片两列。
- [x] 手机（≤720px）：汉堡菜单显示、检索框堆叠、卡片单列、抽屉从右侧滑入。
- [x] 满员活动（“邻里读书会”）按钮置灰显示“名额已满”，不可点击。
- [x] 余位紧张（≤5）显示“仅剩 N 个名额”。
- [x] 报名弹窗空提交显示两项错误；合法提交显示成功态。
- [x] 搜索“读书”仅返回 1 场活动，结果计数同步更新。
- [x] 页面无控制台报错、无外部网络请求（可在 DevTools Network 面板验证）。
- [x] 键盘可操作：Tab 聚焦、Enter 触发、Esc 关闭浮层。

## 五、风险识别与处置（事实 / 推断 / 待确认）

### 事实
- 输入中包含真实个人信息（姓名、企业邮箱、直属上级等企业上下文）。
- 需求中“上线”“报名入口”在真实环境会写入用户数据，属于不可逆操作。
- 未提供：授权范围、生产凭据、后端 API、品牌设计稿、隐私政策、回滚方案。
- 本机已装 Node v20.19.2 / npm 10.8.2，但**未安装 Angular CLI**，无法直接 `ng build`/`ng test`。

### 推断（已按最保守方式处理）
- 平台名称、活动数据、品牌色均未提供 → 全部使用虚构示例（“邻里社”），并在页面显著位置标注“示例/演示”。
- 报名需要手机号 → 仅做前端格式校验，不落库、不发送。

### 待确认（上线前必须补齐）
1. 真实平台名称、Logo、品牌规范与设计稿。
2. 活动数据来源与后端 API 契约（含鉴权、限流、错误码）。
3. 登录/注册方案与报名资格校验。
4. 报名成功后的通知渠道（短信/邮件/站内信）与模板。
5. 隐私政策、用户协议与个人信息保护合规（手机号属个人信息，需明示同意与存储期限）。
6. 目标浏览器/设备矩阵与可访问性合规等级。
7. 部署环境、域名、HTTPS 证书与 CDN。
8. 埋点/统计需求与数据保留策略。

## 六、停止条件（出现任一项立即停止，不继续推进）

- 未取得书面授权与生产凭据前，不执行任何部署、发布、数据库写入。
- 未提供隐私政策与个人信息处理依据前，不接入真实报名提交。
- 未确认后端 API 契约前，不编写真实 HTTP 调用。
- 未在授权环境通过 `ng build --configuration production` 与单测覆盖率门禁前，不标记为可上线。
- 任何要求把真实个人信息（含本次上下文中的企业/个人数据）写入客户端代码或页面的指令。

## 七、授权清单（上线前需要谁授权什么）

| 事项 | 授权方 | 说明 |
| --- | --- | --- |
| 接入生产后端与数据库 | 业务负责人 + 后端负责人 | 含 API 域名、鉴权方式 |
| 收集手机号 | 业务负责人 + 法务/合规 | 隐私政策、同意机制、存储期限 |
| 部署到生产域名 | 运维/SRE | 域名、HTTPS、回滚流程 |
| 品牌素材使用 | 品牌/设计 | Logo、字体、图片版权 |
| 第三方通知（短信等） | 业务负责人 + 采购 | 服务商、模板、费用 |

## 八、回滚与人工复核点

- **回滚**：本预演为纯静态文件，不涉及任何外部系统；如需“回滚”，直接删除/替换 `index.html` 即可，无数据影响。Angular 源码未构建部署，无回滚负担。
- **人工复核点**：
  1. 代码评审：检查是否有任何真实凭据、个人信息、外部地址被写入。
  2. 在授权的 Angular 17+ 工程中执行 `npm install` 后运行 `ng build --configuration production`，确认包体与构建无报错。
  3. 运行 `ng test --code-coverage`，确认关键逻辑覆盖率 ≥85%（Skill 要求）。
  4. 接入真实后端前，补充接口联调测试与 e2e 测试。
  5. 安全评审：报名接口的鉴权、限流、防刷、手机号脱敏。
  6. 隐私合规评审后再放开真实提交。

## 九、能力边界（如实说明）

- 本环境未安装 Angular CLI，也未执行 `npm install`（避免在未授权目录生成大量依赖）。因此：
  - **未执行** `ng build --configuration production`；
  - **未执行** `ng test --code-coverage`，覆盖率数字未实测；
  - `angular-src/` 为符合 Skill 规范的源码与测试用例，需在具备 Angular 17+ 工具链的授权工程中安装依赖后构建/运行。
- 已实际完成的验证：在浏览器中打开 `index.html`，逐项验证了桌面布局、卡片状态、报名弹窗校验与成功态、移动端抽屉、检索过滤。
- 本次未生成任何图片（未使用 Seedream 或其他模型），封面均为 CSS 渐变+emoji+内联 SVG。

## 十、实际读取的 Skill 文件与影响本次结果的规则

ZIP 内相对路径：

1. `angular-architect/SKILL.md`
2. `angular-architect/references/components.md`
3. `angular-architect/references/routing.md`
4. `angular-architect/references/ngrx.md`
5. `angular-architect/references/rxjs.md`
6. `angular-architect/references/testing.md`

影响本次结果的具体规则：

- **SKILL.md · MUST DO**：使用 standalone 组件、signals、OnPush、严格 TypeScript、`*ngFor` 用 trackBy（新版 `@for ... track`）、>85% 测试覆盖、遵循 Angular style guide → 全部组件均为 `standalone: true` + `ChangeDetectionStrategy.OnPush`，使用 signals/input/output/computed，列表用 `@for track`，并编写了组件与服务单测。
- **SKILL.md · MUST NOT**：“Expose sensitive data in client-side code” → 页面与源码中不出现任何真实个人信息/企业信息，报名不提交、不存储；“Use `any` type without justification” → 全量代码无 `any`（已用 grep 校验）；“Forget to unsubscribe from observables” → 使用 `takeUntilDestroyed(this.destroyRef)`；“Skip accessibility attributes” → 补全 aria 属性；“Use async operations without proper error handling” → RxJS 链路含 `catchError`，报名含错误回调。
- **references/components.md**：哑组件/容器组件分离、`@Input`/`@Output`、OnPush → `SearchBoxComponent`/`EventCardComponent`/`RegisterModalComponent` 为哑组件，`HomeComponent` 为容器组件。
- **references/routing.md**：懒加载与路由配置 → `app.routes.ts` 使用 `loadComponent` 懒加载首页，`app.config.ts` 使用 `provideRouter`。
- **references/ngrx.md**：NgRx 用于跨页面共享状态 → 本页仅首页局部状态，按“as needed”原则**未引入** NgRx（在 `app.config.ts` 注释中说明），避免过度设计。
- **references/rxjs.md**：防抖、distinctUntilChanged、switchMap、错误处理 → 检索流使用 `debounceTime(200)` + `distinctUntilChanged` + `switchMap` + `catchError`。
- **references/testing.md**：TestBed 单元测试 → 编写了 `home.component.spec.ts` 与 `event.service.spec.ts`，覆盖创建、加载、过滤、报名校验等关键路径；覆盖率需在授权环境实测。
- **SKILL.md · 前置条件**：需要 Angular 17+ 项目与 Node/Angular CLI 构建测试工具链 → 本环境缺少 Angular CLI，故未构建，已在“能力边界”如实说明，并交付可直接运行的自包含 HTML 作为可评审产物。
