# Agent Mail 自动化 — 受约束流程方案

> 依据 Skill：`agent-mail-automation`（via Rube MCP / Composio Agent Mail toolkit）
> 生成时间：2026-08-12（Asia/Shanghai）
> 约束原则：仅使用现有权限与已提供数据；不静默创建、删除或覆盖外部资源；不编造数据、文件内容、运行结果或外部事实。

---

## 一、能力边界声明（以 SKILL.md 为准）

该 Skill 的真实能力边界：

1. **唯一通道**：通过 Rube MCP 暴露的三个工具操作 Agent Mail——
   - `RUBE_SEARCH_TOOLS`：发现可用工具与最新 schema
   - `RUBE_MANAGE_CONNECTIONS`：检查/建立 `agent_mail` toolkit 连接
   - `RUBE_MULTI_EXECUTE_TOOL`：按发现的 tool_slug 与 schema 执行
   - 辅助：`RUBE_REMOTE_WORKBENCH`（批量）、`RUBE_GET_TOOL_SCHEMAS`（完整 schema）
2. **强制前置条件**（SKILL.md 第 16–18 行、第 73–74 行）：
   - Rube MCP 必须已连接（`RUBE_SEARCH_TOOLS` 可响应）；
   - `agent_mail` 连接状态必须为 **ACTIVE**；
   - **必须先调用 `RUBE_SEARCH_TOOLS` 获取当前 schema**，不得硬编码 tool slug 或参数。
3. **该 Skill 不负责**：本地 SMTP/IMAP 直连、绕过 MCP 的 HTTP 调用、在未授权情况下配置 MCP 服务器、代替用户完成 OAuth 授权。

> 题目中"表格分类：自动化与工具"仅为分类标签，不扩展上述职责。若题目假设与 SKILL.md 冲突，以 SKILL.md 为准。

---

## 二、当前环境预检结果（实测，非推断）

| 预检项 | 方法 | 结果 |
|--------|------|------|
| Rube MCP 工具是否可用 | `tool_search` 检索 `RUBE_SEARCH_TOOLS` 等 | **不可用**，未返回任何 Rube 工具 |
| MCP 端点可达性 | `curl https://rube.app/mcp` | **失败**：`Could not resolve host: rube.app`（DNS 解析失败） |
| 本地 MCP 配置 | 检查 `~/.cursor/mcp.json`、`~/.config/claude*/`、`~/.doubao/` | **未发现** MCP 配置文件 |
| 相关环境变量 | `env \| grep -iE "rube\|composio\|mcp"` | **未发现** 相关变量 |

**结论**：前置条件不满足。按 SKILL.md 规则，**不进入任何邮件执行阶段**。
本次可交付的"可核验演示结果"即上述预检本身（见 `precheck-demo.sh` 与 `precheck-demo-结果.txt`），
任何人可重新运行脚本复现，不涉及任何外部资源变更。

---

## 三、受约束执行流程（预检 → 确认 → 执行 → 验证）

### 阶段 0：预检（Pre-check，全部为只读）

| 编号 | 检查项 | 通过标准 | 失败处理 |
|------|--------|----------|----------|
| P0-1 | Rube MCP 可用性 | `RUBE_SEARCH_TOOLS` 可正常响应 | 停止；提示需先添加 `https://rube.app/mcp` 为 MCP server |
| P0-2 | 工具发现 | 用具体 use_case 调用 `RUBE_SEARCH_TOOLS`，返回 tool_slug 与 schema | 停止；不凭记忆硬编码 slug/参数（SKILL.md 第 73 行） |
| P0-3 | 连接状态 | `RUBE_MANAGE_CONNECTIONS(toolkits:["agent_mail"])` 返回 **ACTIVE** | 若未 ACTIVE，返回授权链接，**由用户本人完成 OAuth**；不得代填凭据 |
| P0-4 | 参数完整性 | 待执行参数与搜索返回 schema 的字段名、类型逐一匹配 | 停止；补齐后重新走 P0-2 |
| P0-5 | 影响面评估 | 标注每个工具调用是"只读"还是"写操作（发送/创建/删除/修改）" | 写操作进入阶段 1 人工确认 |

### 阶段 1：计划与人工确认（Human-in-the-loop）

1. 生成**执行计划**：工具 slug、参数摘要（敏感值脱敏）、操作类型、影响对象、是否分页。
2. **人工确认点**（强制）：
   - 任何**发送邮件、创建草稿、删除邮件、修改标签/文件夹**等写操作，必须向用户展示计划并获得明确"确认执行"后才继续；
   - 只读操作（列出邮件、读取单封、搜索）可免确认，但仍记录日志；
   - 批量操作（`RUBE_REMOTE_WORKBENCH`）无论读写，一律先确认批量范围与上限。
3. 用户拒绝或超时未确认 → 终止该操作，不换写法重试。

### 阶段 2：执行（Execution，含幂等与重试）

**幂等设计**
- 为每个写操作生成幂等键：`idempotency_key = SHA256(操作类型 + 目标对象 + 参数规范化JSON)`；
- 执行前在本地日志中检索该键：已存在且结果成功 → 跳过，直接返回已有结果（不重复发送/创建）；
- 幂等键与结果写入本地执行日志（见阶段 3），不写入外部系统。

**重试策略**
- 可重试错误（网络超时、5xx、429 限流）：指数退避，间隔 2s/4s/8s，**最多 3 次**；
- 不可重试错误（schema 校验失败 4xx、认证失败、权限不足）：立即停止并上报，不重试；
- 重试必须复用同一 `session_id`（SKILL.md 第 77 行）；
- `RUBE_MULTI_EXECUTE_TOOL` 必须携带 `memory` 参数，即使为空对象 `{}`（SKILL.md 第 76 行）。

**分页**
- 检查响应中的分页 token；存在则继续拉取，直到无下一页（SKILL.md 第 78 行）；
- 批量拉取设置上限（默认 100 条），超过需再次人工确认。

### 阶段 3：验证与记录（Verify & Log）

1. 校验返回结构是否符合预期（字段、状态）；
2. 写本地日志（仅本地，不外发），每条记录包含：
   `时间 | session_id | 工具slug | 操作类型(读/写) | 幂等键 | 参数摘要(脱敏) | 结果状态 | 重试次数 | 错误信息(若有)`；
3. 向用户汇报：成功/失败、影响对象数量、日志位置；
4. 任何与预期不符的结果 → 标记异常，不自动回滚外部资源，交由用户决定。

---

## 四、仍需确认的假设与不可访问资源

| 项 | 状态 | 说明 |
|----|------|------|
| Rube MCP server 已配置 | **未满足** | 当前环境 DNS 无法解析 rube.app，且无 MCP 配置；需用户在客户端添加 `https://rube.app/mcp` 后重启/重连 |
| agent_mail 连接为 ACTIVE | **无法验证** | 依赖 P0-1 通过；未 ACTIVE 时需用户本人走 OAuth 授权链接 |
| 具体邮件操作目标 | **未提供** | 题目未指定要读/发/搜哪封邮件；P0-2 需具体 use_case 才能发现对应工具 |
| 实际 tool_slug 与 schema | **不得编造** | SKILL.md 明确要求先搜索再用；在 `RUBE_SEARCH_TOOLS` 成功返回前，本方案不出现任何具体 slug 或参数字段名 |
| 账号邮箱地址 | **未读取/未使用** | 未访问任何邮箱数据 |

---

## 五、本次实际读取的 Skill 文件

- `agent-mail-automation/SKILL.md`（ZIP 内唯一文件，相对路径：`agent-mail-automation/SKILL.md`）

## 六、实际影响交付结果的 SKILL.md 规则（至少一条）

1. **第 73 行"Always search first … Never hardcode tool slugs or arguments without calling `RUBE_SEARCH_TOOLS`"**：
   因为当前无法调用 `RUBE_SEARCH_TOOLS`，本方案**拒绝编造**任何具体工具 slug 和邮件参数字段，所有执行步骤以占位与"搜索后填充"表示——这直接决定了本次只能交付预检与流程方案，不能产出伪造的"已读邮件/已发邮件"演示结果。
2. **第 74 行"Check connection … ACTIVE status before executing tools"**：
   预检确认连接不可用后，流程在阶段 0 即停止，未执行任何写操作，符合"不静默创建/删除/覆盖外部资源"的约束。
3. **第 76–78 行**（memory 参数、session 复用、分页）已写入阶段 2 的执行规范。
