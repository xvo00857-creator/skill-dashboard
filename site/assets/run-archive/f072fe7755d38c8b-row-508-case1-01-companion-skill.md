# companion-skill 评测报告：针对「整理研究资料并生成汇报」的最小可用技能组合筛选

## 一、输入假设与验收标准

### 1.1 输入假设

| 编号 | 假设项 | 具体内容 |
|------|--------|----------|
| A1 | 评测对象 | `companion-skill`（分类：自动化与工具），ZIP 包内实际项目名为 `xiaoyue-companion-skill`，版本 `0.2.0-lite` |
| A2 | 目标需求 | 「整理研究资料并生成汇报」——包含资料检索、阅读解析、结构化整理、汇报产出四个核心环节 |
| A3 | 运行环境 | 当前为 Doubao/SuperDoubao 多智能体环境（Linux Ubuntu 22.04），非 OpenClaw 框架 |
| A4 | 可用资源 | 系统已预装技能库（含搜索、文档、表格、幻灯片、可视化等技能），具备本地文件读写与命令执行能力 |
| A5 | 权限边界 | 无智谱 AI API Key、无飞书应用凭据、无 OpenClaw 运行时；不发起浏览器登录或外部付费操作 |

### 1.2 验收标准

| 编号 | 验收点 | 通过条件 |
|------|--------|----------|
| V1 | 能力边界准确 | companion-skill 的实际能力以源代码为准，不凭文档宣称或技能名称推断 |
| V2 | 需求拆解完整 | 「整理研究资料并生成汇报」被拆解为可独立验证的子任务，每个子任务有明确的技能匹配 |
| V3 | 最小组合可执行 | 推荐的技能组合在当前环境下可直接调用，不依赖缺失的外部框架或凭据 |
| V4 | 兼容性说明清晰 | 明确指出 companion-skill 与当前环境的不兼容点及原因 |
| V5 | 验证方法可复现 | 每个推荐技能给出可执行的验证命令或调用方式 |
| V6 | 缺失项如实报告 | 不编造已完成状态，明确列出无法验证的部分及原因 |

---

## 二、companion-skill 实际能力盘点（基于源代码核验）

### 2.1 已实现能力

| 能力模块 | 实现文件 | 实际行为 | 依赖 |
|----------|----------|----------|------|
| 陪伴对话生成 | `src/companion.ts` | 调用 `glm-4-flash`，基于人设提示词和场景模板生成 1-3 句温暖回应；保留最近 3 轮对话历史；API 失败时有降级回应 | `zhipuai-sdk-nodejs-v4`、`ZHIPU_API_KEY` |
| 场景识别 | `src/scene-detector.ts` | 基于中文关键词匹配（累/开心/咖啡/健身等）和任务进度，判断 work/life/mood 三类场景及子类型，决定是否需要配图 | 无外部依赖 |
| 图片生成（AI 模式） | `src/image-generator.ts` | 调用 `cogview-3-flash` REST API，按 9 种预设场景提示词生成 1280x1280 图片，自动缓存到本地 | `axios`、`ZHIPU_API_KEY`、网络访问 `open.bigmodel.cn` |
| 图片生成（静态模式） | `src/image-generator.ts` | 从 `assets/reference/` 目录按文件名映射返回本地图片路径；目录不存在时自动创建 | 无外部依赖（但需预置图片文件） |
| 图片分析（多模态） | `src/companion.ts` | 调用 `glm-4v-flash`，接受图片 URL 或 base64，返回文字描述 | `zhipuai-sdk-nodejs-v4`、`ZHIPU_API_KEY` |
| 主入口调度 | `src/index.ts` | 暴露 `execute()` 函数，支持 `accompany`/`generate-photo`/`chat` 三种 action；统一错误处理 | 上述全部模块 |

### 2.2 文档宣称但源代码未实现的能力

| 文档宣称 | 实际情况 |
|----------|----------|
| 「通过飞书发送图片和温暖的消息」 | 源代码中**无任何飞书 API 调用**。`index.ts` 的 `execute()` 仅返回 `{ success, message, imageUrl }`，发送动作需由 OpenClaw Gateway 或上层调用方完成 |
| 「assets/reference/ 参考图片库」 | ZIP 包中**不存在 `assets/` 目录**，静态模式下所有图片路径都会指向不存在的文件 |
| 「tests/companion.test.ts」 | SKILL.md 文件结构中列出，但 ZIP 包中**不存在 `tests/` 目录**；实际测试脚本为 `src/test.ts` |
| 「src/prompts/scenes.ts」 | SKILL.md 文件结构中列出，但 ZIP 包中**不存在该文件**；场景模板实际定义在 `src/prompts/personality.ts` 的 `SCENE_TEMPLATES` 中 |
| `npm run test:generate` 脚本 | README/QUICKSTART/INSTALL 中多次提及，但 `package.json` 的 `scripts` 中**无此脚本**；批量生图逻辑写在 `src/test.ts` 中，需通过 `node dist/test.js --generate-library` 触发 |

### 2.3 关键依赖与环境要求

- **运行时**：Node.js >= 18.0.0
- **npm 依赖**：`zhipuai-sdk-nodejs-v4@^0.1.12`、`axios@^1.6.0`、`dotenv@^16.3.1`
- **必需环境变量**：`ZHIPU_API_KEY`（无此 Key 时 `execute()` 直接抛出错误并返回失败）
- **可选环境变量**：`XIAOYUE_PERSONALITY`（friendly/professional/casual）、`XIAOYUE_PHOTO_MODE`（static/ai）、`FEISHU_APP_ID`、`FEISHU_APP_SECRET`
- **目标框架**：OpenClaw（需配置 `~/.openclaw/openclaw.json` 和 `~/.openclaw/workspace/SOUL.md`）
- **硬编码路径**：`src/test.ts` 中引用 Windows 路径 `D:\tool\StepFun\resources\chat.png`，在 Linux 环境下该测试分支会被跳过

### 2.4 安全隐患

- `INSTALL.md` 和 `QUICKSTART.md` 中**明文硬编码了一个智谱 AI API Key**（`da8df5ba...`），该 Key 已暴露在文档中，应视为已泄露
- `.env.example` 中 `FEISHU_APP_ID` 和 `FEISHU_APP_SECRET` 为空，但代码中并未实际使用这两个变量

---

## 三、需求拆解与技能匹配

### 3.1 「整理研究资料并生成汇报」子任务拆解

```
整理研究资料并生成汇报
├── 阶段1：资料获取
│   ├── 1.1 公开网络资料检索
│   ├── 1.2 企业内部资料检索（如涉及）
│   └── 1.3 网页/文档内容抓取与解析
├── 阶段2：资料阅读与理解
│   ├── 2.1 长文档分段读取
│   ├── 2.2 关键信息提取与摘要
│   └── 2.3 多来源信息交叉比对
├── 阶段3：结构化整理
│   ├── 3.1 信息分类与标签化
│   ├── 3.2 数据表格化
│   └── 3.3 逻辑框架搭建
└── 阶段4：汇报生成
    ├── 4.1 文档型汇报（飞书文档/Word）
    ├── 4.2 演示型汇报（PPT/幻灯片）
    └── 4.3 数据可视化（图表）
```

### 3.2 companion-skill 与各子任务的匹配度

| 子任务 | companion-skill 匹配度 | 原因 |
|--------|------------------------|------|
| 1.1 公开网络资料检索 | **不匹配** | 无任何搜索/爬虫能力，场景识别仅做关键词匹配，不发起网络请求 |
| 1.2 企业内部资料检索 | **不匹配** | 无企业知识库检索能力 |
| 1.3 网页/文档内容抓取 | **不匹配** | 无 HTTP 抓取能力（axios 仅用于调用智谱图片 API） |
| 2.1 长文档分段读取 | **不匹配** | 无文件读取/解析能力 |
| 2.2 关键信息提取 | **不匹配** | 对话生成模型可做摘要，但 Skill 的提示词被锁定为「温暖陪伴」人设，不适合专业信息提取 |
| 2.3 多来源交叉比对 | **不匹配** | 无多文档处理能力 |
| 3.1 信息分类标签化 | **弱匹配** | 场景识别模块可做简单关键词分类，但仅支持 3 类 9 子型，且与研究资料分类无关 |
| 3.2 数据表格化 | **不匹配** | 无表格生成能力 |
| 3.3 逻辑框架搭建 | **不匹配** | 无大纲/框架生成能力 |
| 4.1 文档型汇报 | **不匹配** | 无文档生成能力 |
| 4.2 演示型汇报 | **不匹配** | 无幻灯片生成能力 |
| 4.3 数据可视化 | **不匹配** | 无图表生成能力；图片生成仅用于「生活照片」场景 |

**结论：companion-skill 在「整理研究资料并生成汇报」的全部 12 个子任务中，0 个核心匹配，1 个弱匹配，11 个不匹配。它不是该需求的可用技能。**

companion-skill 唯一可能的辅助角色是：在耗时任务执行期间，通过陪伴对话缓解用户等待焦虑，并通过飞书发送进度通知。但这属于「体验增强」而非「任务执行」，且飞书发送能力在源代码中并未实现。

---

## 四、最小可用技能组合推荐

### 4.1 组合方案

基于当前环境已预装的技能库，针对「整理研究资料并生成汇报」推荐以下最小可用组合：

| 阶段 | 子任务 | 推荐技能 | 技能类型 | 必要性 |
|------|--------|----------|----------|--------|
| 资料获取 | 公开网络检索 | `general_search` | 系统工具 | **必需** |
| 资料获取 | 企业内部检索（可选） | `doubao-enterprise-search` | 预装技能 | 条件必需（涉及内部资料时） |
| 资料获取 | 网页/文档抓取 | `web.fetch` | 系统工具 | **必需** |
| 资料理解 | 长文档读取 | `Read`（本地文件）+ `web.fetch`（在线文档分页） | 系统工具 | **必需** |
| 结构化整理 | 数据表格化 | `lark-sheets` | 预装技能 | 推荐（有结构化数据时） |
| 汇报生成 | 文档型汇报 | `lark-doc` | 预装技能 | **必需二选一** |
| 汇报生成 | 演示型汇报 | `lark-slides-pro` | 预装技能 | **必需二选一** |
| 汇报生成 | 数据可视化 | `doubao-visualization` | 预装技能 | 推荐（有数据图表需求时） |

### 4.2 最小核心组合（3 个工具/技能）

如果只保留最核心、不可替代的能力，最小组合为：

1. **`general_search`** — 资料检索入口
2. **`web.fetch`** — 网页/文档内容抓取与长文分页读取
3. **`lark-doc`**（或 `lark-slides-pro`）— 汇报产出

这 3 项覆盖了「检索 → 阅读 → 产出」的完整闭环，其余均为增强项。

### 4.3 companion-skill 不在组合中的理由

1. **能力不重叠**：companion-skill 的核心能力（陪伴对话、生活照生成、情绪场景识别）与研究资料整理无功能重叠
2. **框架不兼容**：companion-skill 为 OpenClaw 框架设计，依赖 `skills.call()` 调用方式和 `openclaw.json` 配置，当前环境无 OpenClaw 运行时
3. **凭据缺失**：必需的 `ZHIPU_API_KEY` 在当前环境未配置，且文档中硬编码的 Key 应视为已泄露不可用
4. **依赖未安装**：npm 包 `zhipuai-sdk-nodejs-v4` 等未在当前环境安装，`npm install` 需网络且可能失败
5. **静态资源缺失**：ZIP 包中无 `assets/reference/` 图片目录，静态模式也无法正常返回图片

---

## 五、兼容性分析

### 5.1 companion-skill 与当前环境的兼容性矩阵

| 维度 | companion-skill 要求 | 当前环境 | 兼容性 |
|------|---------------------|----------|--------|
| 操作系统 | 文档示例为 Windows（`D:\tool\...`、PowerShell），代码本身跨平台 | Linux Ubuntu 22.04 | 代码可运行，测试脚本中 Windows 路径分支会跳过 |
| 运行时 | Node.js >= 18.0.0 | Python 3.12.9 为主，Node.js 状态未验证 | 需额外确认 Node.js 版本 |
| 框架 | OpenClaw | Doubao/SuperDoubao 多智能体 | **不兼容**，调用方式和配置体系完全不同 |
| 包管理 | npm | 以 pip 为主，npm 状态未验证 | 需额外确认 |
| API 凭据 | 智谱 AI API Key（必需） | 未配置 | **不满足** |
| 网络访问 | 需访问 `open.bigmodel.cn` | 有网络访问能力 | 理论可行，但无 Key 无法验证 |
| 静态资源 | `assets/reference/` 目录及图片文件 | ZIP 中未包含 | **缺失** |
| 飞书集成 | 需 OpenClaw Gateway 或飞书应用凭据 | 有飞书技能但接口不同 | **不兼容**，companion-skill 本身无飞书调用代码 |

### 5.2 推荐技能组合与当前环境的兼容性

| 技能/工具 | 兼容性 | 说明 |
|-----------|--------|------|
| `general_search` | 完全兼容 | 系统内置工具，可直接调用 |
| `web.fetch` | 完全兼容 | 系统内置工具，支持分页读取 |
| `Read` | 完全兼容 | 系统内置工具，支持本地文件和图片 |
| `lark-doc` | 完全兼容 | 预装技能，支持飞书文档创建与编辑 |
| `lark-slides-pro` | 完全兼容 | 预装技能，支持幻灯片创建与编辑 |
| `lark-sheets` | 完全兼容 | 预装技能，支持表格创建与分析 |
| `doubao-visualization` | 完全兼容 | 预装技能，支持多种图表生成 |
| `doubao-enterprise-search` | 条件兼容 | 需企业内部知识库有相关资料，且需先读取技能说明 |

---

## 六、安装与调用顺序

### 6.1 推荐最小组合的调用顺序

```
步骤1：general_search
  │  输入：研究主题关键词
  │  输出：相关网页链接列表 + 摘要片段
  ▼
步骤2：web.fetch（对步骤1的高价值链接逐个抓取）
  │  输入：URL + 分页参数（长文需 offset 续读）
  │  输出：网页/文档全文内容
  ▼
步骤3：信息提取与结构化（在对话上下文中完成，无需额外工具）
  │  输入：步骤2的全文内容
  │  输出：分类整理后的要点、数据、引用
  ▼
步骤4（可选）：lark-sheets
  │  输入：结构化数据
  │  输出：飞书表格（用于数据对比和汇总）
  ▼
步骤5（可选）：doubao-visualization
  │  输入：数据 + 图表类型
  │  输出：可视化图表图片
  ▼
步骤6：lark-doc 或 lark-slides-pro
     输入：整理后的要点 + 可选表格/图表
     输出：飞书文档汇报 或 飞书幻灯片汇报
```

### 6.2 companion-skill 若强行使用的安装顺序（仅作记录，不推荐）

> 以下步骤在当前环境下**无法完整执行**，因缺少 OpenClaw 框架和 API Key。列出仅为说明其安装链路。

```
1. cd ~/.openclaw/skills
2. git clone <repo> xiaoyue-companion
3. cd xiaoyue-companion && npm install
4. cp .env.example .env  # 填入有效 ZHIPU_API_KEY
5. npm run build
6. npm test  # 验证功能（需 API Key，且 Windows 路径测试会跳过）
7. 编辑 ~/.openclaw/openclaw.json 启用 Skill
8. 编辑 ~/.openclaw/workspace/SOUL.md 添加人设
9. openclaw restart
```

---

## 七、验证方法

### 7.1 推荐组合的可执行验证

| 技能 | 验证方法 | 预期结果 |
|------|----------|----------|
| `general_search` | 调用 `general_search` 传入任意研究关键词 | 返回包含标题、URL、摘要的搜索结果列表 |
| `web.fetch` | 对 `general_search` 返回的某条 URL 调用 `web.fetch`（snippet 模式或 pagination 模式） | 返回网页正文内容或相关片段 |
| `lark-doc` | 先读取 `lark-doc/SKILL.md`，再按指引创建一篇包含标题和正文的测试文档 | 返回飞书文档链接，文档可访问且内容正确 |
| `lark-slides-pro` | 先读取 `lark-slides-pro/SKILL.md`，再按指引创建一页测试幻灯片 | 返回幻灯片链接，页面可访问且内容正确 |
| `lark-sheets` | 先读取 `lark-sheets/SKILL.md`，再按指引创建一个含表头和数据的测试表格 | 返回表格链接，数据正确写入 |
| `doubao-visualization` | 先读取 `doubao-visualization/SKILL.md`，再按指引生成一个简单柱状图 | 返回图表图片，数据映射正确 |

### 7.2 companion-skill 的验证（当前环境下受限）

| 验证项 | 方法 | 当前环境结果 |
|--------|------|-------------|
| TypeScript 编译 | `npm install && npm run build` | **未执行**：未安装 npm 依赖，且非目标任务必要步骤 |
| 场景识别单元测试 | 直接运行 `src/scene-detector.ts` 的逻辑（纯函数，无外部依赖） | **可验证**：该模块不依赖 API，可通过代码审查确认其关键词匹配逻辑 |
| 对话生成测试 | `npm test`（需 `ZHIPU_API_KEY`） | **无法验证**：无有效 API Key |
| 图片生成测试 | 设置 `XIAOYUE_PHOTO_MODE=ai` 后调用 | **无法验证**：无 API Key，且 AI 生图会产生费用 |
| 静态图片模式 | 设置 `XIAOYUE_PHOTO_MODE=static` 后调用 | **无法验证**：ZIP 中无 `assets/reference/` 目录和图片文件 |
| 飞书消息发送 | 代码审查 | **确认未实现**：源代码中无飞书 API 调用 |

### 7.3 场景识别模块的代码级验证结论

通过阅读 `src/scene-detector.ts`，确认以下逻辑：

- `detectMood()`：基于 5 组关键词（开心/累/激动/专注/默认）返回情绪标签，逻辑简单可预测
- `isWorkRelated()`：消息含「工作/代码/项目/任务/文件/调试/开发」或 `progress > 0` 时判定为工作场景
- `isLifeRelated()`：消息含「咖啡/健身/周末/休闲/逛街/吃饭」时判定为生活场景
- `detectWorkScene()`：进一步按「咖啡/调试/默认办公」分子类型，`needsPhoto` 由进度和情绪共同决定
- `detectLifeScene()`：按「健身/咖啡/周末/一般」分子类型，多数情况 `needsPhoto = true`

该模块可独立运行，不依赖任何外部 API 或资源。

---

## 八、缺失项与已完成范围报告

### 8.1 已完成范围

| 项目 | 状态 | 说明 |
|------|------|------|
| ZIP 解压 | 已完成 | 19 个文件全部解压到 `/home/user/.super_doubao/super-doubao-runtime/workspace/companion-skill-extracted/companion-skill/` |
| SKILL.md 完整阅读 | 已完成 | 884 token，全文阅读 |
| 全部辅助文档阅读 | 已完成 | README.md、README-LITE.md、INSTALL.md、QUICKSTART.md、CHANGELOG.md、RETHINK.md、.env.example、package.json、tsconfig.json |
| 全部源代码阅读 | 已完成 | index.ts、companion.ts、image-generator.ts、scene-detector.ts、prompts/personality.ts、test.ts |
| 能力边界梳理 | 已完成 | 区分了已实现能力、文档宣称但未实现能力、关键依赖 |
| 需求拆解 | 已完成 | 拆解为 4 阶段 12 子任务 |
| 技能匹配分析 | 已完成 | companion-skill 与 12 子任务逐一匹配，结论为 0 核心匹配 |
| 最小可用组合推荐 | 已完成 | 核心 3 项 + 推荐增强项 |
| 兼容性分析 | 已完成 | companion-skill 与当前环境 9 维度对比；推荐组合兼容性确认 |
| 调用顺序 | 已完成 | 推荐组合 6 步调用链路 |
| 验证方法 | 已完成 | 推荐组合 6 项验证方法；companion-skill 7 项验证状态 |
| 本报告生成 | 已完成 | 本文档 |

### 8.2 缺失项与阻断原因

| 缺失项 | 影响 | 原因 |
|--------|------|------|
| 有效 `ZHIPU_API_KEY` | 无法验证对话生成、图片生成、图片分析功能 | 当前环境未配置；文档中硬编码的 Key 已暴露，应视为无效 |
| OpenClaw 框架运行时 | 无法按 SKILL.md 描述的方式调用 Skill | 当前环境为 Doubao/SuperDoubao，非 OpenClaw |
| `assets/reference/` 目录及图片文件 | 静态图片模式无法返回有效图片 | ZIP 包中未包含该目录 |
| `tests/` 目录 | SKILL.md 中描述的测试文件不存在 | ZIP 包中实际测试脚本为 `src/test.ts` |
| `src/prompts/scenes.ts` | SKILL.md 文件结构中列出但不存在 | 场景模板实际合并在 `personality.ts` 中 |
| `npm run test:generate` 脚本 | 文档中多次提及但 package.json 中无此脚本 | 文档与代码不一致 |
| 飞书发送功能实现 | 文档宣称「通过飞书发送」但代码中无实现 | 该功能需由 OpenClaw Gateway 或上层调用方完成 |
| Node.js/npm 环境验证 | 未确认当前环境 Node.js 版本是否 >= 18 | 非本任务核心目标，且 companion-skill 不被推荐使用 |
| 实际编译与运行测试 | 未执行 `npm install && npm run build && npm test` | 缺少 API Key，即使编译成功也无法通过功能测试；且非目标任务必要步骤 |

### 8.3 不假装成功声明

- **未执行** companion-skill 的编译、安装或运行，因此**不声称**其在当前环境下可运行
- **未调用** 智谱 AI 的任何 API，因此**不声称**对话生成、图片生成或图片分析功能正常
- **未创建** 任何飞书文档、幻灯片或表格作为本报告的附属产物，本报告本身即为交付物
- **未验证** 推荐组合中各技能的实际调用效果，仅给出了验证方法；实际使用时需按各技能的 SKILL.md 指引操作

---

## 九、最终结论

1. **companion-skill 不适用于「整理研究资料并生成汇报」需求**。其核心能力为虚拟伴侣对话、生活场景图片生成和情绪场景识别，与资料检索、文档解析、结构化整理、汇报生成无功能重叠。

2. **companion-skill 与当前环境不兼容**。它为 OpenClaw 框架设计，依赖智谱 AI API Key、npm 依赖和特定目录结构，当前环境均不满足。

3. **最小可用技能组合为**：`general_search`（检索）+ `web.fetch`（抓取/阅读）+ `lark-doc` 或 `lark-slides-pro`（汇报产出）。如有结构化数据或图表需求，可增加 `lark-sheets` 和 `doubao-visualization`。

4. **companion-skill 唯一可能的辅助价值**是在耗时任务期间提供情感陪伴，但该价值不属于「整理研究资料并生成汇报」的核心路径，且其飞书发送能力在源代码中并未实现，因此不纳入最小组合。
