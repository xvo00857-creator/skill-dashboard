# 授权清单、停止条件、回滚与人工复核点

## 一、授权清单（运行前必须逐项满足）

| 编号 | 授权项 | 状态 | 说明 |
|------|--------|------|------|
| A1 | Rube MCP 已连接 | 未满足 | 需在客户端配置 `https://rube.app/mcp`，且 `RUBE_SEARCH_TOOLS` 可响应 |
| A2 | Ably toolkit 连接为 ACTIVE | 未满足 | 需通过 `RUBE_MANAGE_CONNECTIONS` 完成 Ably 授权，状态显示 ACTIVE |
| A3 | 目标 Ably 频道已授权 | 未满足 | 当前为占位符 `PLACEHOLDER_CHANNEL_NEEDS_AUTHORIZATION`，需填入经团队确认的频道名 |
| A4 | 待办数据源已授权 | 未满足 | 需明确数据源（如飞书任务、Jira 等）及其访问凭据；当前仅使用本地模拟 JSON |
| A5 | 团队成员知情同意 | 未确认 | 自动收集并汇总个人待办属于工作数据处理，需团队负责人确认范围与频率 |
| A6 | 发送频率与时间窗口 | 未确认 | 需明确每周何时运行、是否仅工作日、是否允许重复提醒 |
| A7 | 数据最小化确认 | 未确认 | 摘要中仅应包含任务 ID、标题、截止日期、逾期天数、优先级，不应包含个人联系方式等 |

## 二、停止条件（命中任一立即中止，不发送）

1. Rube MCP 未连接或 `RUBE_SEARCH_TOOLS` 不可用。
2. Ably toolkit 连接状态非 ACTIVE。
3. 目标频道为占位符或未在授权清单中。
4. 数据源中包含未脱敏的真实个人敏感信息（手机号、邮箱、身份证等）。
5. `DRY_RUN=false` 但人工未在终端输入大写 `CONFIRM`。
6. 待办数据为空、解析失败，或逾期项数量异常（如超过总数 50%，可能是数据错误）。
7. 工具 schema 与预期不符（按 SKILL.md 要求，必须先 `RUBE_SEARCH_TOOLS` 获取最新 schema，不得硬编码）。
8. 分页响应未取完（按 SKILL.md 已知陷阱，需检查分页 token 并继续获取直到完整）。

## 三、回滚方案

### 3.1 可回滚部分
- **本地文件**：`digest_preview.txt` 可直接删除；脚本和配置可通过版本控制回退。
- **数据读取**：本流程为只读读取待办数据，不修改源系统，无需回滚。
- **配置变更**：频道名、运行频率等配置项可随时改回。

### 3.2 不可回滚部分及缓解
- **Ably 消息发布不可撤回**：消息一旦通过 `ABLY_PUBLISH_MESSAGE_TO_CHANNEL` 发布，订阅者立即收到，无法撤销。
  - 缓解 1：默认 `DRY_RUN=true`，仅生成本地预览。
  - 缓解 2：发送前强制人工确认（大写 `CONFIRM`）。
  - 缓解 3：先发布到仅管理员可见的"审核频道"，确认无误后再由人工转发到团队频道。
  - 缓解 4：若误发，立即在频道发布更正消息，并通知频道管理员；Ably 本身不支持消息撤回。
- **推送通知**（如使用 `ABLY_PUBLISH_PUSH_NOTIFICATION`）：同样不可撤回，且直达设备，风险更高；本最小版本不启用推送。

### 3.3 紧急停止
- 立即中断脚本进程（Ctrl+C）。
- 若已连接 Rube MCP，可通过 `RUBE_MANAGE_CONNECTIONS` 断开 Ably 连接，阻止后续执行。
- 通知 Ably 应用管理员，必要时在 Ably 控制台禁用对应频道或密钥。

## 四、人工复核点

| 复核点 | 位置 | 复核内容 |
|--------|------|----------|
| R1 | 数据加载后 | 确认待办数据完整、无异常字段、无敏感信息泄露 |
| R2 | 逾期筛选后 | 确认逾期项合理（排除已完成、已延期审批通过的项） |
| R3 | 摘要生成后 | 逐行阅读摘要内容，确认措辞得当、无错误归因 |
| R4 | 发送前 | 确认目标频道正确、消息内容无误，输入 `CONFIRM` |
| R5 | 发送后 | 确认消息已正确送达；如发现错误，立即发布更正 |

## 五、真实接入步骤（满足全部授权后）

1. 在 MCP 客户端添加 `https://rube.app/mcp`，确认 `RUBE_SEARCH_TOOLS` 可响应。
2. 调用 `RUBE_MANAGE_CONNECTIONS`（toolkits: `["ably"]`），按返回的授权链接完成 Ably 连接，确认状态 ACTIVE。
3. 调用 `RUBE_SEARCH_TOOLS`（use_case: "publish message to Ably channel"）获取 `ABLY_PUBLISH_MESSAGE_TO_CHANNEL` 的最新 schema。
4. 将 `todo_digest.py` 中的 `_ably_publish_stub()` 替换为通过 `RUBE_MULTI_EXECUTE_TOOL` 按 schema 调用真实工具，携带 `memory: {}` 与复用的 `session_id`。
5. 将 `load_todos()` 替换为已授权的任务系统读取逻辑（注意分页）。
6. 先以 `DRY_RUN=true` 运行至少一个完整周期，确认无误后再考虑关闭干跑。
7. 首次真实发送建议使用审核频道，经人工确认后再转发。
