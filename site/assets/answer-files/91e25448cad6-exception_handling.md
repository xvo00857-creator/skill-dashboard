# 异常处理

> 异常分三类：前置/连接类（阻断，不重试）、执行类（按策略重试或降级）、数据类（记录到 anomalies，不阻断）。
> 所有异常均写入运行日志与摘要的 `anomalies` 字段。

## 1. 异常码与处理策略

| 异常码 | 触发阶段 | 触发条件 | 处理策略 | 是否重试 |
|--------|----------|----------|----------|----------|
| E_PREREQ | Step 0 | Rube MCP 不可用（`RUBE_SEARCH_TOOLS` 无响应） | 立即终止，输出缺失项清单，不进入后续步骤 | 否 |
| E_AUTH | Step 2 | Adobe 连接非 ACTIVE / OAuth 未完成 | 返回授权链接，暂停流程，通知负责人手动完成；不模拟授权 | 否（人工完成后下次运行） |
| E_SCHEMA | Step 1/3 | 搜索结果缺少预期工具，或字段与已知 schema 不符 | 终止并记录返回的原始 schema 片段，等待人工确认（禁止猜测字段） | 否 |
| E_PAGINATION | Step 1/3 | 分页拉取中途失败或 token 异常 | 已获取部分丢弃，整步重试，最多 2 次；仍失败则 E_EXEC | 是（2 次） |
| E_EXEC | Step 3 | 工具执行返回错误 / 超时 | 指数退避重试 2 次（间隔 5s、15s）；仍失败则终止并通知负责人 | 是（2 次） |
| E_EMPTY | Step 3 | 收集结果为空（0 条） | 不视为错误；生成"本周无数据"摘要并通知，anomalies 记一条提示 | 否 |
| E_DATA | Step 3 | 单条记录缺字段/类型错/时间无法解析 | 跳过该条，计入 anomalies（含 item_id 与原因），其余继续 | 否 |
| E_NOTIFY | Step 3 | 通知发送失败 | 摘要已生成则重试通知 2 次；仍失败则把通知内容落盘并告警 | 是（2 次） |
| E_PERM | 任意 | 权限不足 / 凭据被撤销 | 立即终止，通知负责人检查 Composio 连接与 Adobe 权限 | 否 |

## 2. SKILL.md 已知陷阱对应的防护

| SKILL.md 陷阱 | 本流程的防护 |
|---------------|--------------|
| 必须先搜索，schema 会变 | 每次运行 Step 1 重新搜索，不缓存 slug；脚本中无硬编码真实 slug |
| 执行前确认连接 ACTIVE | Step 2 强制检查，非 ACTIVE 直接 E_AUTH |
| 字段名/类型严格匹配 schema | E_SCHEMA 检查；字段映射表中的真实字段以搜索结果为准 |
| `memory` 必须传（即使为 `{}`） | `RUBE_MULTI_EXECUTE_TOOL` 调用固定带 `memory: {}` |
| 复用 session_id | Step 1 生成，Step 2/3 复用；新运行新 session |
| 注意分页 token | E_PAGINATION 处理，循环拉取直到无 token |

## 3. 重试与退避

- 仅 E_PAGINATION、E_EXEC、E_NOTIFY 自动重试。
- 退避：第 1 次重试等待 5 秒，第 2 次等待 15 秒（模拟脚本中用 0.1 秒加速，但保留同样次数）。
- 重试只针对幂等读操作；写操作（生成摘要、发送通知）重试前先检查是否已部分成功，避免重复发送。

## 4. 日志与可观测

每次运行在 `output/` 下生成：
- `run_<timestamp>.log`：分步日志（含每步入参/出参摘要、耗时、异常码）。
- `summary_<report_week>.json`：摘要结果（含 anomalies）。
- `notification_<report_week>.txt`：通知内容（模拟模式下不发送，仅落盘）。

日志中不记录 access token、API key 等敏感信息。

## 5. 模拟脚本中的异常注入

`simulate_weekly_report.py` 支持通过参数触发异常分支，用于验证：

| 参数 | 模拟的异常码 | 预期行为 |
|------|--------------|----------|
| `--inject auth_fail` | E_AUTH | Step 2 返回非 ACTIVE，流程暂停并输出授权链接 |
| `--inject empty` | E_EMPTY | 收集结果为空，生成"本周无数据"摘要 |
| `--inject bad_data` | E_DATA | 部分记录缺字段，跳过并计入 anomalies |
| `--inject exec_fail` | E_EXEC | 执行工具失败，重试 2 次后终止 |
| `--inject notify_fail` | E_NOTIFY | 通知失败，重试后落盘并告警 |
| 无参数 | 正常路径 | 完整跑通收集→摘要→通知落盘 |
