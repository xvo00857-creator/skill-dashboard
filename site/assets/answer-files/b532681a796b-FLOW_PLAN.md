# Agencyzoom 自动化受约束流程方案

> 依据：`agencyzoom-automation/SKILL.md`（通过随附 ZIP 解压获得）
> 原则：以 SKILL.md 的真实能力边界为准；预检未通过不执行、不编造结果、不静默改动外部资源。

---

## 1. 能力边界（不可逾越）

本 Skill 的唯一能力路径是：**通过 Rube MCP（Composio 的 Agencyzoom 工具包）操作 Agencyzoom**。SKILL.md 明确规定：

1. 必须先确认 `RUBE_SEARCH_TOOLS` 可响应；
2. 必须通过 `RUBE_MANAGE_CONNECTIONS` 确认 `agencyzoom` 工具包连接状态为 **ACTIVE**；
3. 必须先调用 `RUBE_SEARCH_TOOLS` 获取**当前**工具 schema，**不得硬编码**工具 slug 或参数；
4. 执行使用 `RUBE_MULTI_EXECUTE_TOOL`，且必须带 `memory` 参数（即使为空 `{}`）；
5. 批量操作使用 `RUBE_REMOTE_WORKBENCH` 的 `run_composio_tool()`；
6. 注意分页：响应中出现分页 token 时必须持续拉取直到完整。

**本方案不提供**：绕过 Rube MCP 直接调用 Agencyzoom API 的能力、任何未在 schema 中声明的操作、对外部资源的静默创建/删除/覆盖。

---

## 2. 当前环境预检结论（2026-08-12 实测）

| 预检项 | 结果 | 证据 |
|--------|------|------|
| `RUBE_SEARCH_TOOLS` 等工具在当前 agent 工具集可用 | 不通过 | `tool_search` 仅返回 `scholar_search`、`visual_search`，无任何 `RUBE_*` 工具 |
| `rube` / `composio` CLI | 不存在 | `which rube` / `which composio` 无输出 |
| Rube/MCP 相关环境变量 | 不存在 | `env \| grep -i -E 'rube\|mcp'` 无输出 |
| MCP 客户端配置含 `rube.app/mcp` | 不存在 | 未找到 `~/.cursor/mcp.json`、`~/.config/mcp*` 等配置 |
| `https://rube.app/mcp` 端点连通性 | 不可达 | `curl` 返回 `Could not resolve host: rube.app`（DNS 失败） |

**结论**：SKILL.md 的前提条件（Rube MCP 已连接、Agencyzoom 连接 ACTIVE）**均不满足**。因此本次只能交付流程方案、编排脚本与"预检失败并安全退出"的可核验演示；**不会**产生任何 Agencyzoom 侧的真实读写，也不会编造工具返回或业务数据。

### 解除阻塞所需的人工操作（需用户确认/执行）
1. 在所用 MCP 客户端配置中添加 `https://rube.app/mcp` 作为 MCP server（SKILL.md 原文：无需 API key，添加端点即可），并重启客户端使工具生效；
2. 确认当前网络可解析并访问 `rube.app`（当前 DNS 不可达，可能需要网络环境调整）；
3. 客户端加载 Rube MCP 后，按 SKILL.md 调用 `RUBE_MANAGE_CONNECTIONS`，若返回鉴权链接则由人工完成 Agencyzoom 授权，直到状态为 ACTIVE；
4. 提供真实的批处理任务清单（当前仅有占位模板 `tasks.example.json`，不得当作真实数据执行）。

---

## 3. 受约束的执行流程（九阶段）

脚本 `agencyzoom_flow.py` 将流程固化为以下阶段，每个阶段有明确的进入条件、失败处理与可恢复点：

| 阶段 | 动作 | 对应 SKILL.md | 守门规则 |
|------|------|---------------|----------|
| 0. PRECHECK | 探测 Rube MCP 工具可用性、端点连通性、连接状态 | "Verify Rube MCP is available" | 任一关键项失败 → `BLOCKED`，立即安全退出，不进入后续阶段 |
| 1. DISCOVER | 调用 `RUBE_SEARCH_TOOLS`，按每个任务的 `use_case` 获取当前 slug 与 schema | "Always call RUBE_SEARCH_TOOLS first" | 不得使用缓存/hardcode 的 slug；schema 缺失对应任务则该任务标记 `BLOCKED` |
| 2. CONNECT | 调用 `RUBE_MANAGE_CONNECTIONS(toolkits:["agencyzoom"])` | "Check connection ... ACTIVE" | 非 ACTIVE → 输出鉴权链接并 `BLOCKED`，等待人工授权后重跑 |
| 3. PLAN | 用 DISCOVER 返回的 schema 逐字段校验任务参数；区分 read/write | "Schema compliance" | 参数不合规任务标记 `FAILED`（不可重试），不进入执行 |
| 4. CONFIRM | 列出所有计划调用（尤其 write 操作），等待人工输入确认 | 题目要求的人工确认点 | 非交互环境或未确认 → 不执行 write；`--yes` 仅在预检全过且用户显式指定时生效 |
| 5. EXECUTE | `RUBE_MULTI_EXECUTE_TOOL` 批量执行，带 `memory:{}`、session 复用 | "Core Workflow Pattern Step 3" | 见第 4 节幂等与重试 |
| 6. VERIFY | 检查分页 token 并持续拉取；校验返回结构 | "Pagination" | 分页未拉完 → 继续拉取；结构异常 → 重试或 `FAILED` |
| 7. REPORT | 输出成功/失败/阻塞/死信清单与状态文件 | 可恢复自动化 | 状态文件持久化，支持 `--resume` |

---

## 4. 幂等、重试、可恢复设计

### 4.1 幂等
- 每个任务生成 **idempotency key** = `sha256(tool_slug + json.dumps(arguments, sort_keys=True))`；
- 状态文件（`.azflow/state.json`）按 key 记录 `PENDING/SUCCEEDED/FAILED/BLOCKED`；
- 重跑或 `--resume` 时，`SUCCEEDED` 的任务**跳过**，不重复调用；
- read 操作天然幂等；write 操作依赖 key 去重，避免重复创建。

### 4.2 重试
- 仅对**可重试错误**重试：网络超时、连接重置、HTTP 429/5xx、MCP 返回的临时错误；
- 指数退避：`delay = min(base * 2^n, max_delay)`，默认 base=1s、max_delay=30s；
- 默认最大重试 3 次（`--max-retries` 可调）；
- 参数校验失败、schema 不匹配、鉴权失败等**不可重试错误**立即标记 `FAILED`/`BLOCKED`，不浪费重试。

### 4.3 可恢复
- 每完成一个任务立即落盘状态文件（原子写入：写临时文件后 `os.replace`）；
- `--resume` 从状态文件恢复，只处理未 `SUCCEEDED` 项；
- 中断（Ctrl+C / 进程被杀）后重跑不会丢失已成功项，也不会重复执行。

### 4.4 人工确认点
- CONFIRM 阶段打印完整执行计划：任务编号、use_case、解析出的 tool_slug、读/写类型、关键参数摘要；
- 对 write 类操作要求显式输入 `yes`；
- 预检 BLOCKED 状态下，即使 `--yes` 也**不允许**跳过安全门。

---

## 5. 批处理任务文件格式

任务文件为 JSON 数组。注意：按 SKILL.md，**任务文件只描述业务意图，不写死 tool_slug**，slug 由 DISCOVER 阶段动态获取。

```json
[
  {
    "task_id": "example-read-001",
    "use_case": "列出 Agencyzoom 中的客户记录",
    "operation_type": "read",
    "params": {"limit": 10}
  },
  {
    "task_id": "example-write-001",
    "use_case": "（占位示例，需替换为真实意图）",
    "operation_type": "write",
    "params": {}
  }
]
```

> `tasks.example.json` 仅为格式模板，其中的 `use_case` 与参数均为占位，不代表真实 Agencyzoom 数据，也不会在预检未通过时执行。

---

## 6. 运行方式

```bash
# 预检 + 演示（预检失败会安全退出，不产生外部写操作）
python3 agencyzoom_flow.py --task-file tasks.example.json --state-dir ./.azflow

# 断点续跑
python3 agencyzoom_flow.py --task-file tasks.example.json --state-dir ./.azflow --resume

# 在 Rube MCP 已就绪且已人工核对计划后，跳过交互确认（仍受预检约束）
python3 agencyzoom_flow.py --task-file real_tasks.json --state-dir ./.azflow --yes
```

---

## 7. 不编造承诺

- 本方案不声称已连接 Agencyzoom、不声称已执行任何 Rube 工具、不包含任何虚构的客户/保单/返回数据；
- 脚本在 MCP 工具不可用时返回 `BLOCKED` 并写明原因，而非伪造成功结果；
- 所有"仍需确认的假设"见第 2 节"解除阻塞所需的人工操作"。
