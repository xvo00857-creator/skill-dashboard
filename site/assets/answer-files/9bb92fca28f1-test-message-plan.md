# Linear 渠道集成 —— 测试消息方案

## 测试前提

- NanoClaw 服务已重启并加载 Linear 渠道（`pnpm run build` 通过，服务重启完成）
- Webhook 已在 Linear 创建，URL 指向公网服务，事件勾选 Comment
- `.env` 中凭证已填写真实值
- 消息组与 wiring 已创建（`ncl messaging-groups list` 可见 `linear:<TEAM_KEY>`）

> 新建 Webhook 后 Linear 可能延迟 1-5 分钟才开始推送，属正常现象。

## 测试用例

### TC-01：基本评论触发（冒烟）

| 项 | 内容 |
|----|------|
| 操作 | 在监控团队的任意 issue 下发表一条评论，如：`你好，请确认你能收到这条消息` |
| 预期 | 机器人在同一 issue 评论线程中回复，无需 @提及 |
| 验证点 | 机器人回复出现在同一 issue；回复内容与评论相关 |
| 超时 | 发表后等待 5 分钟（新 webhook 延迟） |

### TC-02：每个 issue 线程独立

| 项 | 内容 |
|----|------|
| 操作 | 在 issue A 评论 `我们用的是什么数据库？`，在 issue B 评论 `刚才的问题答案是什么？` |
| 预期 | issue B 的回复不应引用 issue A 的上下文（per-thread 隔离） |
| 验证点 | 两个 issue 的回复各自独立，不串上下文 |

### TC-03：回复嵌套（comment thread）

| 项 | 内容 |
|----|------|
| 操作 | 在 issue 的某条评论下使用回复功能（嵌套回复），而非顶层评论 |
| 预期 | 机器人在该评论的嵌套线程中回复 |
| 验证点 | 线程 ID 格式为 `linear:<issueId>:c:<commentId>`，回复挂在正确的父评论下 |

### TC-04：Webhook 签名验证（安全）

| 项 | 内容 |
|----|------|
| 操作 | 用错误签名向 `/webhook/linear` 发送 POST（模拟伪造请求） |
| 预期 | 返回 400，请求被拒绝，机器人不产生任何回复 |
| 本地预演 | `node verify-webhook.mjs`（已在本地验证签名逻辑，见验证结果） |

### TC-05：自身消息过滤

| 项 | 内容 |
|----|------|
| 操作（OAuth 模式） | 以机器人应用身份发表评论 |
| 预期 | 机器人不回复自己的评论 |
| 操作（API Key 模式） | 你自己发表评论 |
| 预期 | 机器人不回复你自己的评论（设计如此）；其他成员评论正常触发 |

### TC-06：非 create 事件忽略

| 项 | 内容 |
|----|------|
| 操作 | 编辑或删除一条已有评论 |
| 预期 | 机器人不响应（适配器仅处理 `action=create`） |

### TC-07：strict 发送者策略（如选用）

| 项 | 内容 |
|----|------|
| 操作 | 未注册成员在 issue 下评论 |
| 预期 | 机器人不响应；已注册成员评论正常响应 |

## 本地可重复验证（无需真实 Linear 账号）

以下命令在 `linear-integration/` 目录执行，零外部依赖：

```bash
# 1. 配置结构校验（使用模拟凭证）
node verify-config.mjs .env.linear

# 2. Webhook 签名机制验证（模拟 Linear 签名/验签/篡改/重放）
node verify-webhook.mjs

# 3. 在真实 NanoClaw 项目中验证集成完整性
bash verify-project.sh /path/to/nanoclaw
```

## 端到端验证（需要真实账号，部署后执行）

```bash
# 确认消息组已创建
ncl messaging-groups list | grep linear

# 确认 wiring 已创建
ncl wirings list | grep linear

# 查看服务日志确认 webhook 到达
# macOS:
launchctl kickstart -k gui/$(id -u)/$(launchd_label)
# Linux:
systemctl --user restart $(systemd_unit)
```

在 Linear issue 中发表评论后，检查：
1. 机器人在 1-5 分钟内回复
2. 服务日志无签名验证错误
3. 回复位于正确的评论线程
