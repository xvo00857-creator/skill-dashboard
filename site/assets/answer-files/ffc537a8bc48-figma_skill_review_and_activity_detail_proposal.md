# Figma Skill 能力核查与"活动详情"组件方案（只读预演版）

> 生成时间：2026-08-12 ｜ 状态：**只读预演，未连接 Figma，未执行任何写入操作**

---

## 一、Skill 真实能力确认（基于实际文件）

| 项目 | 内容 |
|---|---|
| Skill 名称 | `figma`（版本 1.0.0，来源 github.com/openai/skills） |
| 核心用途 | 通过 Figma MCP 服务器获取设计上下文、截图、变量/样式与资源，并将 Figma 节点翻译为生产代码 |
| 连接方式 | Streamable HTTP，地址 `https://mcp.figma.com/mcp`，Bearer Token 鉴权 |
| 链接驱动 | 必须提供 Figma frame/layer 链接，服务端从 URL 提取 node ID；客户端不浏览页面 |
| 核心工具 | `get_design_context`（结构化设计数据+默认 React+Tailwind 代码）、`get_variable_defs`（颜色/间距/排版变量）、`get_metadata`（节点层级大纲）、`get_screenshot`（节点截图）、`get_code_connect_map`（节点→代码组件映射）、`add_code_connect_map`（**写入**映射关系）、`whoami`（身份验证）等 |
| 强制流程 | ① `get_design_context` → ② 过大时先 `get_metadata` 再按需重取 → ③ `get_screenshot` → ④ 两者齐备后才下载资源/开始实现 → ⑤ 转为项目约定 → ⑥ 对照截图做 1:1 验证 |
| 明确不适用 | 像素级精确代码实现应使用 `figma-implement-design`（本 Skill 不含该能力） |

---

## 二、前置条件检查结果

| 前置条件 | 要求 | 当前状态 | 结论 |
|---|---|---|---|
| Figma frame/layer 链接 | 必须提供指向精确节点的 URL | **未提供**（唯一附件为 Skill 自身 ZIP，非设计文件） | 阻塞 |
| `FIGMA_OAUTH_TOKEN` 环境变量 | 非空有效 token | **未设置**（已验证 `$FIGMA_OAUTH_TOKEN` 为空） | 阻塞 |
| MCP 服务器注册 | agent 配置中添加 `[mcp_servers.figma]` | **未发现配置**（常见配置目录均无） | 阻塞 |
| RMCP client 功能 | OAuth over streamable HTTP 需要 | 无法验证（依赖上述配置） | 阻塞 |
| 网络可达性 | 访问 `mcp.figma.com` | 未测试（无 token 测试无意义） | 待验证 |
| Figma MCP 工具在当前环境可用 | 工具可被调用 | **不可用**（`tool_search` 检索 "figma mcp design context" 无结果） | 阻塞 |

**结论：全部 5 项硬前置条件均不满足，无法执行任何 Figma 数据读取操作。**

---

## 三、冲突、缺失信息与风险识别

### 3.1 未核实事实

| 编号 | 描述 | 判定 |
|---|---|---|
| F-1 | "从现有设计文件中读取按钮、颜色、排版与间距规范"——但输入中**不存在任何设计文件或 Figma 链接**，无法验证该文件是否存在、是否包含所述规范 | 未核实，当前为伪前提 |
| F-2 | "与既有系统一致"——未提供既有系统代码仓库、组件库或设计系统文档，无法判断一致性基准 | 未核实 |

### 3.2 个人敏感信息

| 编号 | 描述 | 处理方式 |
|---|---|---|
| P-1 | 执行环境上下文中附带了企业人员信息（姓名、邮箱、部门、直属上级等） | **不纳入任何交付物**，不用于 Figma 身份推断，不在文档中复述 |

### 3.3 不可逆 / 高风险操作

| 编号 | 操作 | 风险 | 当前处置 |
|---|---|---|---|
| R-1 | `add_code_connect_map` 会向 Figma 文件写入/更新节点与代码组件的映射关系 | 修改远程 Figma 文件，无内置回滚；在无授权范围、无生产凭据、无回滚方案时执行属于不可逆操作 | **不执行**，列入授权清单待批 |
| R-2 | 基于未验证的"既有规范"直接生成生产组件代码并合入 | 可能引入与真实设计系统不一致的 token、组件，污染代码库 | **不执行**，仅输出只读方案 |

### 3.4 缺失信息清单

1. 目标 Figma 文件/frame 的 URL（含 node ID）
2. Figma OAuth Token 及对应账号的访问权限范围
3. 目标代码仓库位置与技术栈（React/Vue/其他、样式方案、组件库路径）
4. "活动详情"页面的业务需求（字段、交互、状态、边界场景）
5. 既有设计系统 token 命名约定与组件清单
6. 授权范围（只读 / 可写入 code connect / 可提交代码）
7. 回滚方案与人工复核负责人

---

## 四、事实 / 推断 / 待确认项分类

| 类别 | 项 |
|---|---|
| **事实**（已验证） | Skill 文件内容；`FIGMA_OAUTH_TOKEN` 未设置；MCP 未配置；当前环境无 Figma MCP 工具；未收到 Figma 链接或设计文件 |
| **推断**（基于 Skill 文档的合理预期，非实测） | 若连接成功，`get_variable_defs` 可返回颜色/间距/排版变量；`get_design_context` 可返回节点结构与默认代码；`get_screenshot` 可返回视觉参考 |
| **待确认** | 目标设计文件是否存在及其中是否有按钮/颜色/排版/间距规范；"活动详情"页面需求；目标代码仓库与技术栈；账号权限；授权范围 |

---

## 五、安全范围内最小可用交付

> 以下内容为**只读预演框架**，不含任何从 Figma 实际读取的数据。所有具体数值标注为"待 Figma 读取后填充"，不得视为真实设计规范。

### 5.1 设计规范摘要模板（待 `get_variable_defs` + `get_design_context` 填充）

```
## 按钮规范
| 变体 | 用途 | 背景色 token | 文字色 token | 圆角 token | 高度 token | 内边距 token | 字号/字重 token | Figma node |
|------|------|-------------|-------------|-----------|-----------|-------------|----------------|------------|
| 主要按钮 | 待确认 | 待填充 | 待填充 | 待填充 | 待填充 | 待填充 | 待填充 | 待填充 |
| 次要按钮 | 待确认 | 待填充 | 待填充 | 待填充 | 待填充 | 待填充 | 待填充 | 待填充 |
| 文字按钮 | 待确认 | 待填充 | 待填充 | 待填充 | 待填充 | 待填充 | 待填充 | 待填充 |
| 禁用态 | — | 待填充 | 待填充 | — | — | — | 待填充 | 待填充 |

## 颜色规范
| token 名 | 色值 | 用途 | Figma variable ID |
|----------|------|------|-------------------|
| 待填充 | 待填充 | 待填充 | 待填充 |

## 排版规范
| 层级 | 字号 token | 行高 token | 字重 token | 用途 | Figma node |
|------|-----------|-----------|-----------|------|------------|
| 待填充 | 待填充 | 待填充 | 待填充 | 待填充 | 待填充 |

## 间距规范
| token 名 | 数值 | 典型用途 |
|----------|------|----------|
| 待填充 | 待填充 | 待填充 |
```

### 5.2 "活动详情"页面组件方案（通用建议，非从设计文件推导）

> **声明**：以下为活动详情页的通用组件拆解建议，不代表已读取到的既有系统规范。待 Figma 连接成功后，须用 5.1 中真实 token 替换所有占位，并通过 `get_code_connect_map` 优先复用既有组件。

**页面区块拆解（自上而下）：**

| 区块 | 建议组件 | 复用优先 | 说明 |
|------|---------|---------|------|
| 顶部导航栏 | 既有 NavBar / PageHeader 组件 | 必须复用 | 返回按钮 + 标题"活动详情" + 右侧操作位 |
| 活动头图 | 既有 Image / Banner 组件 | 必须复用 | 按既有图片圆角、比例规范；待 Figma 确认比例 |
| 活动标题区 | 既有 Typography 标题样式 | 必须复用 | 标题 + 副标题/标签，使用既有排版 token |
| 活动状态标签 | 既有 Tag / Badge 组件 | 必须复用 | 如"进行中/已结束/未开始"，颜色取自既有语义色 token |
| 时间地点信息 | 既有 List / InfoRow 组件 | 必须复用 | 图标 + 文本行，间距遵循既有间距 token |
| 活动详情正文 | 既有 RichText / Content 组件 | 必须复用 | 富文本渲染，排版遵循既有正文样式 |
| 报名/参与按钮区 | 既有 Button 组件（主要/次要变体） | 必须复用 | 底部固定栏，使用既有按钮 token，不新建按钮样式 |
| 分享/收藏 | 既有 IconButton 组件 | 必须复用 | 图标取自 Figma payload，不引入新图标包（Skill 明确禁止） |

**组件方案原则（依据 SKILL.md 实现规则）：**
- 复用既有按钮、输入、排版、图标容器组件，不重复造轮子
- 使用项目的颜色系统、排版阶梯、间距 token，不硬编码数值
- Figma MCP 返回的 React+Tailwind 仅作设计与行为表达，最终代码须转为项目约定
- 图标资源使用 Figma payload 中的 localhost 源，不新增图标包，不使用占位符
- 遵守既有路由、状态管理、数据获取模式

### 5.3 来源节点追踪表（待填充）

| 交付项 | Figma frame/layer URL | node ID | 获取工具 | 截图留存 |
|--------|----------------------|---------|---------|---------|
| 按钮-主要 | 待提供 | 待提取 | get_design_context + get_screenshot | 待留存 |
| 颜色变量 | 待提供 | 待提取 | get_variable_defs | — |
| 排版变量 | 待提供 | 待提取 | get_variable_defs | — |
| 间距变量 | 待提供 | 待提取 | get_variable_defs | — |
| 活动详情参考 frame | 待提供 | 待提取 | get_design_context + get_screenshot | 待留存 |

### 5.4 一致性检查清单（实现完成后逐项验证）

- [ ] 所有颜色引用项目 token，无硬编码色值
- [ ] 所有字号/行高/字重引用排版 token，无硬编码
- [ ] 所有 margin/padding 引用间距 token，无硬编码
- [ ] 按钮使用既有 Button 组件变体，未新建样式
- [ ] 图标来自 Figma payload，未引入新图标包
- [ ] 页面布局与 Figma 截图 1:1 比对通过（`get_screenshot` 对照）
- [ ] 响应式/断点行为与既有页面一致
- [ ] 路由、状态管理、数据获取模式与仓库既有模式一致
- [ ] 无个人敏感信息写入代码或注释
- [ ] Code connect 映射（如执行）经人工复核确认

---

## 六、停止条件、授权清单、回滚与人工复核点

### 6.1 停止条件（满足任一即停）

1. 无法提供有效 Figma 链接或 OAuth Token
2. Token 对应账号对目标文件无读取权限
3. `whoami` 返回身份与预期不符
4. 目标文件中找不到所述按钮/颜色/排版/间距规范
5. 要求执行写入操作（`add_code_connect_map`、代码提交）但未获书面授权
6. 发现输入中包含的个人敏感信息被要求写入交付物或代码
7. 任何步骤返回错误且无法在当前权限内解决

### 6.2 授权清单（须逐项确认后方可执行）

| # | 操作 | 类型 | 需要授权 |
|---|------|------|---------|
| 1 | 使用 Figma OAuth Token 连接 MCP | 只读 | 是（token 本身即授权） |
| 2 | 读取目标 Figma 文件节点数据 | 只读 | 是（账号须有文件访问权） |
| 3 | 截图与资源下载到本地 | 只读 | 是 |
| 4 | `add_code_connect_map` 写入映射 | **写入** | 是（须明确授权范围） |
| 5 | 在代码仓库创建/修改组件文件 | 写入 | 是（须指定仓库与分支） |
| 6 | 提交代码 / 创建 MR | 写入 | 是（须指定目标分支与评审人） |

### 6.3 回滚方案

| 操作 | 回滚方式 |
|------|---------|
| `add_code_connect_map` | Figma 无内置回滚；执行前须截图/导出现有 code connect map（`get_code_connect_map`）作为备份，写入后如异常由人工在 Figma 中手动恢复 |
| 代码仓库改动 | 在独立分支开发，不合入主干；异常时删除分支即可；合入前须经 MR 评审 |
| 本地文件 | 所有产物生成在独立工作目录，不覆盖既有文件；异常时删除目录 |

### 6.4 人工复核点

1. **Token 与权限复核**：连接后由人工确认 `whoami` 身份正确、权限范围符合预期
2. **规范数据复核**：`get_variable_defs` 返回的 token 清单由设计/前端负责人确认完整性
3. **组件映射复核**：任何 code connect 写入前，由人工核对节点与组件对应关系
4. **视觉复核**：实现完成后由人工对照 Figma 截图确认 1:1
5. **代码复核**：MR 须经至少一名团队成员 review，重点检查 token 复用与敏感信息

---

## 七、实际读取的 Skill 文件清单

| ZIP 内相对路径 | 读取状态 | 对本次结果的影响 |
|---|---|---|
| `figma/SKILL.md` | 已完整读取（51 行） | 确定强制流程（get_design_context → get_metadata → get_screenshot → 实现 → 验证）；确定"复用既有组件/token、不新增图标包、不使用占位符"等实现规则；确定本 Skill 不负责像素级实现 |
| `figma/references/figma-mcp-config.md` | 已完整读取（43 行） | 确定前置条件：`FIGMA_OAUTH_TOKEN` 环境变量、MCP 服务器配置、RMCP client、region header；确定 token 未设置即无法连接 |
| `figma/references/figma-tools-and-prompts.md` | 已完整读取（37 行） | 确定可用工具清单与各自用途；识别 `add_code_connect_map` 为写入型工具（不可逆风险）；确定链接驱动机制 |
| `figma/LICENSE.txt` | 已完整读取（Apache 2.0） | 确认 Skill 为 Apache 2.0 许可，不影响本次分析结论 |

### 影响本次结果的具体规则

1. **SKILL.md 第 19 行**："Run get_design_context first"——无 Figma 链接则第一步即无法执行，构成硬阻塞。
2. **SKILL.md 第 45-46 行**："The server is link-based... always ensure the link points to the exact node/variant"——必须提供精确节点 URL，当前缺失。
3. **figma-mcp-config.md 第 16 行**："The bearer token must be available as `FIGMA_OAUTH_TOKEN`"——已验证未设置，无法鉴权。
4. **figma-tools-and-prompts.md 第 14 行**：`add_code_connect_map` "Adds/updates a mapping"——属写入操作，在无授权时不执行。
5. **SKILL.md 第 40 行**："DO NOT import/add new icon packages"——组件方案中图标须来自 Figma payload。
6. **SKILL.md 第 30-31 行**："Reuse existing components... Use the project's color system, typography scale, and spacing tokens"——组件方案以复用为原则，不新建样式。

---

## 八、结论

当前无法执行"从现有设计文件读取规范"的核心任务，原因是 **Figma 链接、OAuth Token、MCP 配置三项硬前置条件全部缺失**，且当前环境无 Figma MCP 工具可用。本文档已交付：

- 可立即使用的设计规范摘要模板（待数据填充）
- "活动详情"页面组件方案框架（通用建议，标注为推断）
- 来源节点追踪表与一致性检查清单
- 停止条件、授权清单、回滚方案与人工复核点

**下一步所需最小输入**：一个目标 Figma frame/layer 链接 + 有效的 `FIGMA_OAUTH_TOKEN` + MCP 服务器配置。补齐后可按 SKILL.md 强制流程执行只读读取，再进入组件实现阶段。
