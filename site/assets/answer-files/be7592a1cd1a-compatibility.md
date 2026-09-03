# 兼容性与版本演进说明

> 来源说明：基于通用 API 版本演进实践，非 accelerate Skill 内容。

## 版本策略

- URL 路径版本：`/v1/` 为当前稳定版；不兼容变更走 `/v2/`。
- v1 内的所有变更必须向后兼容：
  - 新增**可选**字段 → 兼容（客户端应忽略未知字段）。
  - 新增**可选**查询参数/Header → 兼容。
  - 新增枚举值 → 兼容（客户端应能处理未知枚举，按默认/未知处理）。
  - 新增响应头 → 兼容。
- 禁止的破坏性变更（必须走 v2）：
  - 删除或重命名字段。
  - 修改字段类型。
  - 把可选字段改为必填。
  - 改变错误码语义或 HTTP 状态码语义。
  - 改变分页默认值导致行为变化。

## 演进路线（示例）

| 版本 | 变更 | 兼容性 |
|------|------|--------|
| v1.0 | 初始发布：batchCreate, listTasks, getTask | — |
| v1.1 | Task 新增 `tags`（可选数组）、listTasks 新增 `tag` 过滤 | 向后兼容 |
| v1.2 | 新增 `POST /tasks/{id}:cancel` | 新增端点，兼容 |
| v2.0 | payload 结构强类型化、错误码重构 | 不兼容，走 /v2/ |

## 弃用流程

1. 响应头加 `Deprecation: true` 与 `Sunset: <date>`（RFC 8594 / 9111 风格）。
2. 文档标注替代方案。
3. 至少保留 6 个月重叠期。
4. 监控仍在使用旧版的客户端并主动通知。

## 幂等性契约

- `POST /tasks:batch` 要求 `Idempotency-Key` header。
- 服务端保存 (key, request_hash, response) 24 小时。
- 相同 key + 相同 body → 返回首次响应，`X-Idempotent-Replay: true`。
- 相同 key + 不同 body → 409。
- 网络重试、超时重发均安全；客户端**不应**在重试时更换 key。
- 幂等键范围为单租户/单用户，不跨账号。

## 分页契约

- 使用**游标分页**（cursor-based），不使用 offset，避免深翻页性能问题与数据漂移。
- `limit` 上限 200，默认 50。
- `next_cursor: null` 表示无更多页；客户端**不得**通过总页数推断结束。
- 游标不透明，客户端不应解析或构造。
- `total_count` 为可选近似值（可能滞后），仅用于展示，不用于翻页控制。

## 最小权限

| 端点 | 所需 scope |
|------|-----------|
| POST /tasks:batch | `tasks:write` |
| GET /tasks | `tasks:read` |
| GET /tasks/{id} | `tasks:read` |

- 遵循 PoLA（最小权限原则）：读/写分离。
- JWT 中 `scope` claim 为空格分隔字符串，如 `"tasks:read tasks:write"`。
- 无对应 scope → 403 `INSUFFICIENT_SCOPE`，不泄露资源存在性。
- 服务端不接受 query/body 中传入的身份信息，一律以认证 token 为准。

## 错误码稳定性

- 错误码 `code` 为字符串常量，客户端可依赖其做分支判断。
- `message` 仅用于日志/调试，可能变化，客户端不应解析。
- 字段级错误放在 `details[]`，每项含 `field`（JSONPath 风格，如 `tasks[0].type`）与 `issue`。
- 所有错误响应含 `request_id`，用于追踪。
