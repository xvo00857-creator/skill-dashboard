# 分析与迁移方案：为现有 mcp-use 应用新增工具提供方

> 本文档所有结论均基于实际读取的 Skill 文件内容，未读取或 Skill 未覆盖的部分已显式标注。

---

## 1. Skill 真实能力确认（基于文件内容，非简介）

### 1.1 已弃用声明（来自 SKILL.md frontmatter）

SKILL.md 第 1-8 行明确声明：

```
DEPRECATED: This skill has been replaced by `mcp-app-builder`.
Check if `mcp-app-builder` is available in the skills folder. If not, install it:
`npx skills install mcp-use/mcp-use --skill mcp-app-builder`
Use `mcp-app-builder` instead of this skill.
```

**影响**：本 Skill 已被标记弃用。Skill 建议迁移至 `mcp-app-builder`，但本次评测仍按本 Skill 文件执行。

### 1.2 Skill 实际覆盖范围

| 能力域 | 覆盖？ | 来源文件 |
|--------|--------|----------|
| MCP Server 工具定义（`server.tool()`） | 是 | server-and-widgets.md |
| React Widget 组件开发 | 是 | server-and-widgets.md, components-api.md |
| 项目脚手架（`npx create-mcp-use-app`） | 是 | setup.md |
| CSP / 外部域名白名单 | 是 | csp-and-metadata.md |
| Widget 持久化状态 | 是 | state-and-context.md |
| 显示模式 / 主题 / 响应式 | 是 | ui-guidelines.md |
| 环境变量读取（`process.env`） | 仅一处示例 | setup.md（`process.env.MCP_URL`） |
| 多提供方抽象层 / Provider Registry | 否 | -- |
| 密钥管理（Vault / 密钥轮换 / .gitignore） | 否 | -- |
| 契约测试框架 / 模式 | 否 | -- |
| 接口版本化 / 向后兼容策略 | 否 | -- |
| LLM 模型提供方切换（OpenAI/Anthropic 等） | 否 | -- |

### 1.3 关键前提条件（来自 setup.md）

- Node.js / npm 环境
- `npx create-mcp-use-app@latest` 可访问 npm registry
- ChatGPT Plus/Pro/Business/Enterprise 账号 + Developer Mode（连接 ChatGPT 时）
- 部署需要 `npx mcp-use login && npm run deploy`

### 1.4 对本次场景的映射

场景要求："为现有应用增加一个新的模型或工具提供方"。

- **"工具提供方"** -> 在 mcp-use 语义下，映射为新增一个 `server.tool()` 定义，该工具封装对外部 API 的调用。这是 Skill 覆盖的核心能力。
- **"模型提供方"** -> Skill 构建的是运行在 ChatGPT 内的 App，不涉及 LLM 模型提供方的抽象/切换。**Skill 不覆盖此场景**。
- 以下方案按"新增外部 API 工具提供方"执行，即：在现有 MCP server 上新增一个调用第三方服务的 tool。

---

## 2. SKILL.md 规定的执行流程（严格遵循）

SKILL.md 的 "Before You Code" -> "Setup" -> "Implementation" 流程：

1. **discover.md** - 澄清需求（Phase 1-5）
2. **architecture.md** - 决定 tool vs widget
3. **setup.md** - 脚手架与运行（现有应用跳过）
4. **server-and-widgets.md** - 实现 server handler
5. **state-and-context.md** - 状态管理（本场景不需要）
6. **csp-and-metadata.md** - CSP 与元数据
7. **components-api.md** - 组件 API（本场景不需要 widget）

---

## 3. 最小实现补丁

### 3.1 场景假设（模拟输入，已标注）

> **[模拟]** 假设现有应用是一个天气查询 MCP app，已有 `get-weather` tool 调用 OpenWeatherMap API。现需新增一个 "AI 天气摘要"工具提供方，调用另一个 LLM API（占位符 `https://api.example-llm.com/v1/chat/completions`）对天气数据生成自然语言摘要。
>
> 此为最小模拟输入，不代表真实 API 存在。真实使用时替换为实际提供方端点和密钥。

### 3.2 架构决策（依据 architecture.md）

| 决策点 | 判断 | 依据 |
|--------|------|------|
| 需要 widget 吗？ | 否（纯文本摘要输出） | architecture.md Step 2: "Output is simple text" -> tool only |
| 工具命名 | `summarize-weather`（动词开头） | architecture.md: "Both widgets and tools start with a verb" |
| 是否与现有 tool 重复？ | 否（get-weather 返回原始数据，summarize-weather 生成摘要） | architecture.md: "Don't duplicate" |
| 懒加载？ | 否，一次返回完整摘要 | architecture.md: "Don't lazy-load" |

### 3.3 变更文件清单

```
index.ts                                        # 新增 server.tool() 定义
.env.example                                    # 新增环境变量模板（不入库真实密钥）
.gitignore                                      # 确保 .env 被忽略
tests/summarize-weather.contract.test.ts        # 契约测试（Skill 未覆盖，补充）
```

### 3.4 向后兼容策略

- **不修改**现有 `get-weather` tool 的 schema 或行为
- 新 tool `summarize-weather` 为**纯新增**，不影响现有调用方
- 新 tool 的 schema 字段均有默认值，确保 LLM 不传参时不崩溃
- 若未来需修改 `get-weather`，应新增 `get-weather-v2` 而非原地修改（标准工程实践，非 Skill 规定）

---

## 4. 安全检查清单

依据 csp-and-metadata.md 的 "Security Best Practices" 及通用安全实践：

| 检查项 | 状态 | 依据 |
|--------|------|------|
| API 密钥不入库（.env + .gitignore） | 方案中包含 | 通用实践（setup.md 使用 process.env） |
| CSP connectDomains 指定精确域名 | 方案中包含 | csp-and-metadata.md: "Specify exact domains", "Avoid wildcards" |
| 所有外部资源使用 HTTPS | 方案中包含 | csp-and-metadata.md: "Use HTTPS for all resources" |
| 不使用 unsafe-eval | 方案中包含 | csp-and-metadata.md: "Never use 'unsafe-eval'" |
| Tool annotations 标记 readOnlyHint | 方案中包含 | server-and-widgets.md 示例 |
| 错误信息不泄露密钥 | 方案中包含 | 错误处理脱敏 |
| 输入验证（zod schema） | 方案中包含 | server-and-widgets.md 所有示例使用 zod |

---

## 5. 未覆盖项诚实声明

以下内容 Skill 文件未提供指导，方案中使用标准工程实践并标注：

1. **契约测试**：Skill 无测试相关章节。补充的测试文件使用标准 Node.js test runner，非 Skill 规定。
2. **密钥管理**：Skill 仅在 setup.md 出现 `process.env.MCP_URL` 一处环境变量用法，无 .env / .gitignore / secret rotation 指导。
3. **多提供方抽象**：Skill 无 provider registry / factory pattern 示例。若需支持多个 LLM 提供方动态切换，需额外设计抽象层。
4. **迁移现有部署**：Skill 的 setup.md 仅覆盖新项目脚手架和 `npm run deploy`，无现有应用迁移步骤。
5. **真实外部 API 调用**：方案中 URL 为占位符，未实际调用任何外部服务。
