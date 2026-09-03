# 每周 Adobe 数据收集 → 摘要 → 通知：流程定义

> 本流程基于 `adobe-automation` Skill（通过 Rube MCP / Composio 操作 Adobe）。
> Skill 要求的固定模式：**发现工具 → 检查连接 → 执行工具**，不得跳过或硬编码工具 slug。

## 0. 前置条件检查（运行前必须全部满足）

| 编号 | 前置条件 | 检查方式 | 当前状态（本次评测环境） |
|------|----------|----------|--------------------------|
| P1 | Rube MCP 已连接，`RUBE_SEARCH_TOOLS` 可调用 | 调用 `RUBE_SEARCH_TOOLS` 看是否有响应 | **未满足**：当前环境无 RUBE_* 工具 |
| P2 | Adobe toolkit 连接状态为 ACTIVE | `RUBE_MANAGE_CONNECTIONS(toolkits=["adobe"])` | **未满足**：P1 未满足，无法检查 |
| P3 | Adobe 侧已配置 API key 凭据（Composio 文档要求） | 连接流程中由 Composio 托管 OAuth | **未满足**：无 Adobe 账号授权 |

> P1–P3 任一不满足时，流程不得进入真实执行阶段，只能运行安全模拟（见第 5 节）。

## 1. 总体流程

```
[定时触发：每周一 09:00]
        │
        ▼
[Step 1] RUBE_SEARCH_TOOLS  ← 发现本周可用 Adobe 工具及最新 schema
        │  （use_case 按本周任务具体化，禁止硬编码 slug）
        ▼
[Step 2] RUBE_MANAGE_CONNECTIONS(toolkits=["adobe"])  ← 确认连接 ACTIVE
        │   ├─ 非 ACTIVE → 返回授权链接，流程暂停并通知负责人手动完成
        │   └─ ACTIVE → 继续
        ▼
[Step 3] RUBE_MULTI_EXECUTE_TOOL  ← 执行本周工作流（可多工具串行）
        │   tools: [收集数据, 生成摘要, 通知负责人]
        │   memory: {}  ← 即使为空也必须传（Skill 已知陷阱）
        │   session_id: 复用 Step 1 生成的 session
        ▼
[Step 4] 结果校验与落盘  ← 检查分页、字段完整性、退出码
        │
        ▼
[完成 / 异常分支]
```

## 2. Step 1：发现工具（每次运行必做）

按 Skill 要求，**工具 schema 会变化，禁止硬编码**。每次运行先搜索：

```
RUBE_SEARCH_TOOLS
queries: [{use_case: "weekly collect adobe assets data and generate summary", known_fields: ""}]
session: {generate_id: true}
```

- 记录返回的 `session_id`，后续步骤复用。
- 从返回结果中提取三类工具的真实 `tool_slug` 与输入 schema：
  1. **数据收集类**：列出/读取 Adobe 云端文件、文档元数据或表格数据（具体 slug 以搜索结果为准）。
  2. **摘要生成类**：创建/写入文档或 PDF（具体 slug 以搜索结果为准）。
  3. **通知类**：分享文档、发送邮件或消息（若 Adobe toolkit 无通知能力，需在同一 session 中额外搜索通知类 toolkit，如 email/im；不得臆造）。
- 若搜索结果含 `schemaRef`，用 `RUBE_GET_TOOL_SCHEMAS` 取完整 schema。
- 若返回分页 token，继续拉取直到取完（Skill 已知陷阱：分页）。

## 3. Step 2：检查 Adobe 连接

```
RUBE_MANAGE_CONNECTIONS
toolkits: ["adobe"]
session_id: "<Step 1 的 session_id>"
```

- 状态为 `ACTIVE` → 进入 Step 3。
- 状态非 ACTIVE → 返回的授权链接需由负责人手动完成 OAuth；流程暂停，记录异常 `E_AUTH`，不重试、不模拟授权。

## 4. Step 3：执行每周工作流

通过一次 `RUBE_MULTI_EXECUTE_TOOL` 按序执行（tools 数组顺序即执行顺序）：

```
RUBE_MULTI_EXECUTE_TOOL
tools: [
  { tool_slug: "<搜索得到的收集工具 slug>", arguments: { /* 严格按搜索结果 schema */ } },
  { tool_slug: "<搜索得到的摘要工具 slug>", arguments: { /* 引用上一步输出字段，见字段映射表 */ } },
  { tool_slug: "<搜索得到的通知工具 slug>", arguments: { /* 引用摘要输出，见字段映射表 */ } }
]
memory: {}
session_id: "<Step 1 的 session_id>"
```

执行约束（来自 SKILL.md 已知陷阱）：
- 字段名与类型严格使用搜索结果中的 schema，不得自行推断。
- `memory` 必须传，即使为空对象 `{}`。
- 同一工作流复用同一 `session_id`；新一周的运行生成新 session。
- 批量操作可用 `RUBE_REMOTE_WORKBENCH` + `run_composio_tool()`，但仍需先搜索 schema。

## 5. 安全模拟模式（本次评测实际执行的模式）

由于 P1–P3 均未满足，本次**不进行任何真实 Adobe 调用**，改为：

- 用 Python 标准库实现一个离线模拟器 `simulate_weekly_report.py`，按上述四步打印相同结构的日志；
- 工具 slug 标记为 `MOCK_*`，不冒充真实工具；
- 输入使用本地 `mock_data/` 下的样例数据；
- 输出写入本地 `output/` 目录；
- 支持异常注入参数，用于验证异常处理分支。

模拟器与真实流程的差异：

| 环节 | 真实流程 | 模拟模式 |
|------|----------|----------|
| Step 1 | 真实调用 RUBE_SEARCH_TOOLS | 返回内置的 mock 工具清单（明确标注 MOCK） |
| Step 2 | 真实检查 Adobe 连接 | 返回 `MOCK_ACTIVE`，并在日志中声明非真实连接 |
| Step 3 | 真实调用 Adobe API | 读写本地 mock JSON，不触网 |
| 通知 | 真实发送给负责人 | 只生成通知内容文件，不发送 |

## 6. 定时触发（上线后）

- 建议用系统 cron 或任务调度器，每周一 09:00（Asia/Shanghai）执行。
- 本次评测环境不创建真实定时任务（避免在未满足前置条件时产生误触发）。
- 上线时的 cron 示例（待 P1–P3 满足后启用）：
  ```
  0 9 * * 1 cd /path/to/weekly-adobe-report && /usr/bin/python3 run_real.py >> output/cron.log 2>&1
  ```
