# Confluence 受约束操作流程方案

> 依据 Skill：`confluence-assistant`（SKILL.md v1.0.0，作者 Waldemar Neto，CC-BY-4.0）
> 生成时间：2026-08-12
> 适用范围：Confluence 页面搜索、创建、更新

---

## 一、能力边界声明（以 SKILL.md 为准）

本 Skill 的真实能力边界如下，任何超出范围的需求不在本流程内执行：

| 能做 | 不能做 |
|------|--------|
| 搜索 Confluence 页面/文档（`search`，Rovo Search 自然语言） | Jira 事项操作 |
| 获取页面详情（`getConfluencePage` / `fetch(ari)`） | 通用网页搜索 |
| 列出空间/空间内页面（`getConfluenceSpaces` / `getPagesInConfluenceSpace`） | 本地文件创建（Skill 明确排除） |
| 创建页面（`createConfluencePage`，body 必须 Markdown） | 删除页面（Skill 未提供删除工具） |
| 更新页面（`updateConfluencePage`，body 必须 Markdown） | 覆盖/静默写入外部资源 |
| 添加评论（Skill 描述中提及，但未给出工具签名） | 使用 HTML 或其他格式写入 body |

**关键依赖**：所有操作通过 Atlassian MCP 工具完成。若运行环境未提供这些 MCP 工具，流程只能停在预检阶段，不得伪造调用结果。

---

## 二、环境预检（Pre-flight Checks）

每次操作前必须逐项通过，任一项失败即中止并报告，不得跳过：

| 编号 | 预检项 | 检查方式 | 失败处理 |
|------|--------|----------|----------|
| P1 | MCP 工具可用性 | 确认 `search`、`getConfluencePage`、`createConfluencePage`、`updateConfluencePage`、`getConfluenceSpaces` 可调用 | 中止，提示环境缺少 Atlassian MCP 连接 |
| P2 | Cloud ID / 站点 URL | 检查对话上下文是否已有 Cloud ID；无则按 SKILL.md 要求询问用户 | 中止，等待用户提供 Cloud ID（UUID）或站点 URL（如 `https://example.atlassian.net/`） |
| P3 | 身份与权限 | 尝试只读操作（如 `search` 或 `getConfluenceSpaces`）验证凭证有效 | 中止，报告权限/认证错误，不重试 |
| P4 | 目标空间存在性 | 创建页面前调用 `getConfluenceSpaces(cloudId, keys=[...])` 确认空间存在 | 中止，列出可用空间供选择 |
| P5 | ID 类型校验 | 区分 Page ID（数字）、Space Key（大写字符串）、Space ID（数字），不混用 | 中止，提示 ID 类型错误 |
| P6 | body 格式校验 | 创建/更新前确认 body 为 Markdown，不含 HTML 标签 | 中止，拒绝写入并要求改为 Markdown |
| P7 | 标题非空与长度 | 标题非空、不含 Confluence 非法字符 | 中止，提示修正 |

---

## 三、幂等设计（Idempotency）

### 3.1 创建页面——先查重再创建

1. 调用 `search("标题关键词")` 或 `getPagesInConfluenceSpace(cloudId, spaceId)` 查找同名/近义页面。
2. 若已存在**完全相同标题**的页面：
   - 默认**不创建**，返回已存在页面的 ID 与链接；
   - 若用户确实要新建，须显式确认"已知存在同名页，仍要创建"。
3. 若不存在，进入人工确认后创建。

### 3.2 更新页面——先比对再更新

1. 调用 `getConfluencePage(cloudId, pageId)` 获取当前内容与版本号。
2. 将待写入 body 与当前 body 做规范化比对（忽略首尾空白）。
3. 若内容**完全相同**：跳过更新，报告"无变更"。
4. 若有差异：生成 diff 预览，进入人工确认后更新。
5. 更新时携带当前版本号，避免覆盖他人并发修改（乐观锁）。

### 3.3 搜索页面——天然幂等

搜索为只读操作，可安全重试，不产生副作用。

---

## 四、重试策略（Retry）

| 错误类型 | 是否重试 | 策略 |
|----------|----------|------|
| 网络超时 / 5xx / 429 限流 | 是 | 指数退避：1s → 2s → 4s，最多 3 次；429 优先读 `Retry-After` |
| 401 / 403 认证授权失败 | 否 | 立即中止，报告权限问题 |
| 404 空间/页面不存在 | 否 | 立即中止，报告目标不存在 |
| 400 参数错误（ID 格式、body 非 Markdown） | 否 | 立即中止，提示修正参数 |
| 版本冲突（更新时他人已修改） | 否自动重试 | 中止，提示用户重新拉取并合并后再更新 |

重试只对**只读操作**和**幂等写入**自动生效；非幂等写入在重试前须重新确认前置状态。

---

## 五、人工确认点（Human-in-the-loop）

以下操作在执行前必须暂停，向用户展示预览并获得明确确认（输入"确认"或"YES"）：

| 确认点 | 展示内容 | 确认方式 |
|--------|----------|----------|
| C1 创建页面前 | 目标空间名/Space ID、标题、完整 Markdown body 预览 | 用户明确确认 |
| C2 更新页面前 | 页面 ID、当前标题、新旧标题（若改）、body diff（增/删行） | 用户明确确认 |
| C3 同名页仍要创建 | 已存在页面的 ID、标题、链接 | 用户明确确认 |
| C4 重试将产生写入时 | 上次失败原因、本次将重试的操作 | 用户明确确认 |

**默认干跑（dry-run）**：未获确认前只输出"将要执行"的计划，不调用任何写入工具。用户可随时说"取消"终止。

---

## 六、标准操作流程

### 6.1 搜索页面

```
预检 P1-P3 → search("自然语言查询") → 整理结果（标题/ID/空间/链接/摘要）→ 返回用户
```

### 6.2 创建页面

```
预检 P1-P7 → 幂等查重(3.1) → [C3 若同名] → [C1 人工确认] → createConfluencePage → 返回新页面 ID 与链接
```

### 6.3 更新页面

```
预检 P1-P3,P5-P6 → getConfluencePage 取当前内容与版本 → 幂等比对(3.2)
  → 无变更: 报告跳过
  → 有变更: [C2 人工确认 diff] → updateConfluencePage(带版本号) → 返回更新结果
```

---

## 七、当前环境状态与阻塞项

> 以下为本次实际检查结果，未编造。

| 检查项 | 结果 |
|--------|------|
| Atlassian MCP 工具（`search`/`getConfluencePage`/`createConfluencePage`/`updateConfluencePage`/`getConfluenceSpaces`） | **不可用**——环境工具表与 tool_search 均未找到 |
| MCP 配置文件（`~/.cursor/mcp.json`、`.mcp.json` 等） | 不存在 |
| Atlassian/Confluence 相关环境变量 | 未设置 |
| `atlassian`/`confluence`/`mcp` CLI | 未安装 |
| Cloud ID / Confluence 站点 URL | 用户未提供，对话上下文无 |
| Confluence 凭证（API Token / OAuth） | 未提供 |

**结论**：预检 P1、P2 未通过，无法对真实 Confluence 执行搜索/创建/更新。本次交付：
1. 本流程方案文档；
2. 一份实现上述全部约束的脚本（含干跑模式）；
3. 一次干跑演示输出（使用明确标注的示例数据，不接触任何外部资源）。

要执行真实操作，需补齐：① 在环境中接入 Atlassian MCP Server；② 提供 Cloud ID 或站点 URL；③ 完成认证；④ 在人工确认点逐项确认。
