# Agiled 自动化受约束流程方案

> 依据 Skill：`agiled-automation`（`agiled-automation/SKILL.md`）
> 生成时间：2026-08-12
> 约束原则：仅使用现有权限与已提供数据；不静默创建、删除或覆盖外部资源；无法访问的资源与待确认假设均显式标注。

---

## 一、能力边界声明（以 SKILL.md 为准）

本 Skill 的唯一执行通道是 **Rube MCP（Composio Agiled toolkit）**，不包含任何直连 Agiled REST API 的备用路径。SKILL.md 明确规定：

1. **前置条件**：Rube MCP 必须已连接（`RUBE_SEARCH_TOOLSS` 可用），且通过 `RUBE_MANAGE_CONNECTIONS` 建立的 `agiled` 连接状态为 ACTIVE。
2. **强制先搜索**：每次执行前必须调用 `RUBE_SEARCH_TOOLS` 获取当前工具 schema，禁止硬编码 tool slug 或参数。
3. **强制 memory 参数**：`RUBE_MULTI_EXECUTE_TOOL` 调用必须包含 `memory`（即使为空 `{}`）。
4. **Session 复用**：同一工作流复用 session ID，新工作流生成新 ID。
5. **分页处理**：检查响应中的分页 token，持续拉取直到完成。

**当前环境预检结果（2026-08-12 实测）**：

| 预检项 | 结果 |
|--------|------|
| `RUBE_SEARCH_TOOLS` 等 MCP 工具在当前工具集中可用 | 否（tool_search 未找到） |
| RUBE 相关环境变量 | 无 |
| 常见 MCP 客户端配置文件 | 未找到 |
| `https://rube.app/mcp` 网络可达性 | DNS 解析失败（Could not resolve host: rube.app） |

**结论**：SKILL.md 的两个前置条件均不满足，当前**无法执行任何真实 Agiled 操作**。本方案交付的是"就绪后即可运行"的受约束编排流程，以及一次证明预检机制生效的可核验演示。不编造任何 Agiled 数据或调用结果。

---

## 二、受约束自动化流程

### 阶段 0：预检（Preflight，必须全部通过才继续）

| 编号 | 检查项 | 通过标准 | 失败处理 |
|------|--------|----------|----------|
| P0 | Rube MCP 工具可用性 | `RUBE_SEARCH_TOOLS` 可调用 | 停止；提示在客户端添加 `https://rube.app/mcp` 为 MCP server |
| P1 | 工具发现 | `RUBE_SEARCH_TOOLS` 返回非空工具列表 | 重试最多 3 次（指数退避）；仍失败则停止 |
| P2 | Agiled 连接状态 | `RUBE_MANAGE_CONNECTIONS(toolkits=["agiled"])` 返回 ACTIVE | 若返回 auth link，**暂停并交人工完成授权**；不自动轮询 |
| P3 | 网络连通性 | rube.app 可达（若 P0 已通过则此项通常满足） | 停止并提示网络/DNS 问题 |
| P4 | 输入数据校验 | 批处理输入文件存在、字段完整、无重复幂等键 | 停止并报告具体校验错误 |

### 阶段 1：工具发现（每次工作流必做，对应 SKILL.md "Always search first"）

```
RUBE_SEARCH_TOOLS
queries: [{use_case: "<本次具体 Agiled 任务，如 create invoice>"}]
session: {generate_id: true}
```

- 记录返回的 `tool_slug`、输入 schema、推荐执行计划、已知陷阱。
- **不硬编码** slug 与字段名；以本次返回为准。
- 若工具含 `schemaRef`，用 `RUBE_GET_TOOL_SCHEMAS` 取完整 schema。

### 阶段 2：连接确认

```
RUBE_MANAGE_CONNECTIONS
toolkits: ["agiled"]
session_id: "<阶段1返回的 session_id>"
```

- 状态非 ACTIVE 时，将 auth link 交人工，**等待人工确认后**才继续。

### 阶段 3：批处理执行（幂等 + 重试 + 人工确认点）

#### 3.1 幂等设计

- 每条输入记录分配一个**幂等键** `idempotency_key = "<workflow_id>:<record_unique_id>"`。
- 执行前检查本地状态文件 `state/<workflow_id>.jsonl`：
  - 该键已标记 `success` → **跳过**（不重复调用外部工具）。
  - 该键标记 `failed` 且在重试窗口内 → 进入重试。
  - 无记录 → 执行。
- 状态文件采用 append-only JSONL，每行一条状态变更，崩溃后可重放恢复。

#### 3.2 重试策略

- 仅对**可重试错误**（网络超时、429、5xx）重试；对 4xx 参数/权限错误立即失败并记录。
- 最多 3 次重试，间隔 2s → 4s → 8s（指数退避）。
- 重试时复用同一 `idempotency_key` 与 session_id。

#### 3.3 人工确认点

- **首批确认**：批处理开始前，先以第 1 条记录展示将调用的 tool_slug 与参数，**经人工确认后**才批量执行剩余记录。
- **连接授权**：阶段 2 非 ACTIVE 时暂停。
- **破坏性操作**：若发现操作涉及删除/覆盖（如 delete 类 tool_slug），逐条暂停等待确认，不批量执行。

#### 3.4 执行调用

```
RUBE_MULTI_EXECUTE_TOOL
tools: [{
  tool_slug: "<阶段1发现的 slug>",
  arguments: {<严格按 schema 构造>}
}]
memory: {}
session_id: "<阶段1的 session_id>"
```

- 逐条执行（不盲目并发），每条结果立即写入状态文件。
- 检查响应分页 token，若有则继续拉取直到完成（SKILL.md 分页要求）。

### 阶段 4：恢复与收尾

- 中断后重跑同一命令：预检通过后，脚本读取状态文件，跳过 `success` 记录，仅重试 `failed`/未处理记录。
- 输出汇总：成功数、跳过数、失败数、失败记录清单（含错误原因）。
- **不自动回滚**外部已创建的资源；如需回滚，列出清单交人工决定。

---

## 三、目录与文件约定（本地，可安全创建）

```
agiled-run/
├── input/            # 批处理输入数据（JSONL），由使用方提供
├── state/            # append-only 状态文件，支持恢复
├── logs/             # 每次运行日志
└── agiled_preflight.sh  # 预检与编排脚本
```

以上均为本地工作目录内文件，不涉及外部资源的创建/删除/覆盖。

---

## 四、待确认假设（需使用方确认后才能进入真实执行）

1. **Rube MCP 接入方式**：需在当前 Agent 客户端配置中添加 `https://rube.app/mcp` 作为 MCP server；当前环境未配置且 DNS 不可达，需使用方确认网络环境与客户端支持情况。
2. **Agiled 账号授权**：连接 `agiled` toolkit 时需人工通过 auth link 完成 OAuth 授权，账号与权限范围未知。
3. **具体业务任务**：本次未指定要执行的 Agiled 操作类型（如创建发票、管理客户、项目等）及输入数据；`input/` 目录为空，无批处理数据。
4. **幂等键透传**：Agiled/Composio 工具 schema 是否原生支持幂等键字段，需在阶段 1 工具发现后确认；若不支持，幂等仅靠本地状态文件保证。

---

## 五、本次可核验演示

由于预检未通过，演示内容为：**运行预检脚本，验证其在前置条件不满足时安全中止、不产生任何外部调用**。详见同目录 `agiled_preflight.sh` 及运行输出 `logs/preflight-demo.log`。
