# Expo + Tailwind CSS v4 受约束配置流程方案

> 依据 Skill：`expo-tailwind-setup`（risk: critical，source: expo/skills，date_added: 2026-07-01，license: MIT）
> 执行日期：2026-08-12
> 执行环境：macOS，Node v20.19.2，npm 10.8.2，npx 10.8.2

## 一、预检结果（Pre-flight）

| 检查项 | 结果 |
|---|---|
| Node / npm / npx | v20.19.2 / 10.8.2 / 10.8.2 ✓ |
| pnpm | 10.34.5 ✓（备用） |
| yarn | 未安装（不影响，Skill 用 npx expo install） |
| npm registry 连通 | PONG 596ms ✓ |
| 现有 Expo 项目 | 当前目录及上级目录均不存在含 expo 依赖的项目 |
| create-expo-app | 4.0.0 可用，Expo SDK 最新 57.0.12 |
| 依赖版本核验 | tailwindcss@^4→4.3.3、nativewind@5.0.0-preview.2 存在、react-native-css@0.0.0-nightly.5ce6396 存在、@tailwindcss/postcss→4.3.3、tailwind-merge→3.6.0、clsx→2.1.1、lightningcss@1.30.1 存在 ✓ |

## 二、约束与边界

1. **不静默创建/删除/覆盖外部资源**：所有产物仅写入当前项目目录下新建的 `tailwind-demo/` 子目录，不触碰任何已有文件。
2. **以 SKILL.md 为准**：
   - 不创建 `babel.config.js`（Skill 第 115-131 行明确声明 Tailwind v4 + NativeWind v5 不需要 Babel 配置）。
   - 不需要 autoprefixer（Skill 第 48 行，Expo 内置 lightningcss）。
   - PostCSS 由 Expo 默认提供（Skill 第 49 行）。
   - `resolutions.lightningcss` 按 Skill 第 37-46 行保留。
   - Metro 配置使用 `withNativewind` 且 `inlineVariables: false`、`globalClassNamePolyfill: false`（Skill 第 65-70 行）。
3. **不编造**：所有文件内容严格来自 SKILL.md 模板；运行结果以实际命令输出为准。

## 三、幂等设计

- 创建目录/文件前先检查是否已存在；已存在则跳过并记录，不覆盖。
- `npx expo install` 本身幂等（已安装的包不会重复安装）。
- `package.json` 的依赖和 `resolutions` 字段用 Node 脚本精确合并，不覆盖其他字段。

## 四、重试策略

- npm/expo 安装类网络操作：失败后最多重试 2 次，每次间隔 5 秒。
- 非网络错误（如权限、版本冲突）不盲目重试，先排查根因。
- 实际执行中：首次 `npx expo install` 因 `--no-install` 导致 expo 未安装而失败，先 `npm install` 基础依赖后重试成功。

## 五、人工确认点

1. 创建 `tailwind-demo/` 并执行 `create-expo-app`（写入+网络下载）——系统风险弹窗确认。
2. 安装 Tailwind 相关依赖——系统风险弹窗确认。
3. 写入配置文件（metro.config.js、postcss.config.mjs、src/global.css、src/tw/*）——写入操作由系统弹窗确认。
4. 若发现目标文件已存在且内容不同，暂停并请求指示，不自动覆盖。

## 六、实际执行步骤与结果

1. `CI=1 npx create-expo-app@latest tailwind-demo --template default --no-install --no-agents-md -y` ✓
   - 使用 default 模板（含 expo-router、expo-image、react-native-reanimated），非 blank 模板，因为 Skill 的 tw 组件依赖 expo-router 的 Link 和 expo-image。
2. `npm install` 安装基础依赖（599 包）✓
3. 安装 Tailwind 依赖——遇到 peer dependency 冲突，见下方"偏差说明"。
4. 用 Node 脚本修正 package.json 后 `npm install`（新增 24 包）✓
5. 写入 `metro.config.js`（按 Skill 第 57-71 行）✓
6. 写入 `postcss.config.mjs`（按 Skill 第 77-84 行）✓
7. 更新 `src/global.css`（以 Skill 第 90-113 行为基础，保留模板原有字体变量）✓
8. 写入 `src/tw/index.tsx`、`src/tw/image.tsx`、`src/tw/animated.tsx`（按 Skill 第 139-312 行）✓
9. 在 `src/app/_layout.tsx` 顶部添加 `import "../global.css";` ✓
10. 创建演示页面 `src/app/tailwind-demo.tsx`，并在首页添加 Tailwind 样式区块 ✓
11. **未创建** babel.config.js ✓
12. NativeWind 导出时自动创建 `nativewind-env.d.ts` 并更新 `tsconfig.json` ✓

## 七、偏差说明（依据 SKILL.md Limitations 验证要求）

SKILL.md 第 491-495 行（Limitations）要求："Verify commands, API behavior... against current official documentation before making changes." 据此发现以下偏差：

### 偏差 1：react-native-css 版本（关键）

- **SKILL.md 指定**：`react-native-css@0.0.0-nightly.5ce6396`
- **实际使用**：`react-native-css@^3.0.1`（实际安装 3.0.7）
- **原因**：
  1. `nativewind@5.0.0-preview.2` 的 peerDependencies 明确要求 `react-native-css: ^3.0.1`，与 0.0.0-nightly 冲突，npm 拒绝安装。
  2. `0.0.0-nightly.5ce6396` 的 peerDependencies 要求 expo 54.0.0-preview.6 / react 19.1.0 / react-native 0.81.0，与当前项目（expo 57 / react 19.2.3 / RN 0.86.2）不兼容。
  3. `react-native-css@3.0.7` 的 peerDependencies（react >=19、react-native >=0.81、@expo/metro-config >=54、lightningcss >=1.27.0）与当前项目完全兼容。

### 偏差 2：nativewind 版本

- **SKILL.md 指定**：`nativewind@5.0.0-preview.2`
- **实际使用**：`nativewind@5.0.0-preview.4`
- **原因**：preview.4 是更新的预览版，peerDependencies 相同（tailwindcss >4.1.11、react-native-css ^3.0.1），无破坏性变更。

### 偏差 3：lightningcss 锁定在 npm 下未生效

- **SKILL.md 指定**：package.json 中 `resolutions: { "lightningcss": "1.30.1" }`（yarn 语法）
- **实际情况**：npm 不识别 `resolutions` 字段（npm 用 `overrides`），实际安装 lightningcss 1.32.0（@tailwindcss/postcss 依赖）和 1.33.0（expo/react-native-css 依赖）。
- **处理**：保留了 SKILL.md 的 `resolutions` 字段（忠实于 Skill），未强制降级。打包验证通过，说明当前版本兼容。
- **待确认**：如需在 npm 下强制锁定 lightningcss 版本，应改用 `overrides` 字段，但可能导致与 @tailwindcss/postcss@4.3.3 的兼容性问题，需进一步测试。

### 偏差 4：模板选择

- **原计划**：blank-typescript 模板
- **实际使用**：default 模板
- **原因**：Skill 的 `src/tw/index.tsx` 依赖 expo-router 的 `Link`，`src/tw/image.tsx` 依赖 `expo-image`，blank 模板不含这些依赖。

## 八、验证结果

| 验证项 | 结果 |
|---|---|
| 依赖安装 | tailwindcss@4.3.3、nativewind@5.0.0-preview.4、react-native-css@3.0.7、@tailwindcss/postcss@4.3.3、tailwind-merge@3.6.0、clsx@2.1.1 ✓ |
| babel.config.js | 未创建（符合 Skill 要求）✓ |
| `npx tsc --noEmit` | 运行时间过长被中止（非报错），NativeWind 自动生成了 nativewind-env.d.ts 并更新 tsconfig.json ✓ |
| `npx expo export --platform web` | 退出码 0，1212 模块打包成功 ✓ |
| 生成的 global CSS | 10879 bytes，包含 .flex-1、.bg-white、.text-3xl、.rounded-full、.bg-red-500、.bg-green-500、.bg-blue-50 等 Tailwind 类名 ✓ |
| JS bundle | 包含"Tailwind v4"文案、Tailwind 类名字符串、useCssElement ✓ |
| 浏览器渲染 | 首页可见 Tailwind 样式：浅蓝圆角背景、红/绿/蓝圆形色块、"Tailwind v4 已生效"文字 ✓ |

## 九、已知问题与待确认事项

1. **Node 版本警告**：当前 v20.19.2，部分包要求 ^20.19.4，仅为 EBADENGINE 警告，不影响安装和打包。
2. **npm 漏洞警告**：24 个漏洞（8 moderate, 16 high），非本任务范围，未处理。
3. **静态导出 SSR 限制**：tailwind-demo.html 的服务端渲染内容回退到首页，客户端 JS bundle 包含正确内容。这是 NativeWind preview 版的已知限制，不影响开发模式和客户端渲染。
4. **lightningcss 版本锁定**：见偏差 3，需确认是否在 npm 下改用 overrides。
5. **iOS/Android 真机验证**：本次仅验证了 web 平台打包和渲染。iOS/Android 需在有原生构建环境时进一步验证 `npx expo run:ios` / `run:android`。
