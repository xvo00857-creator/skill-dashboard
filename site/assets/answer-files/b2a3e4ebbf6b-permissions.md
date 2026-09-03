# Linear 渠道集成 —— 权限说明

## 1. Linear 侧权限

### 1.1 OAuth 应用（推荐）

在 [Linear Settings > API > OAuth Applications](https://linear.app/settings/api/applications/new) 创建应用：

| 项目 | 值 | 说明 |
|------|-----|------|
| Developer URL | 团队仓库地址 | 如 `https://github.com/your-org/nanoclaw` |
| Callback URL | `http://localhost` | Client Credentials 模式不使用回调，但字段必填 |
| Grant types | 启用 **Client credentials** | 创建后在应用详情页开启；不开启则 token 交换返回 401 |

**所需 OAuth scopes**（适配器默认值，见 `@chat-adapter/linear` 类型定义）：

- `read` — 读取 issue、评论等
- `write` — 写入操作
- `comments:create` — 在 issue 上发表评论（机器人回复的核心权限）
- `issues:create` — 创建 issue（可选，机器人主动建单时需要）

使用 OAuth 应用身份的优势：机器人以独立应用身份发言，不会把你自己的评论过滤为自身消息。

### 1.2 Personal API Key（备选，更简单）

在 [Settings > Security & Access](https://linear.app/settings/account/security) 创建：

- 权限范围选择 **Only select permissions**，勾选 Create comments（至少）
- 选择可访问的团队

**限制**：机器人以你的身份发言，你自己发表的评论会被适配器作为自身消息过滤，不会触发回复；其他团队成员的评论正常触发。

### 1.3 Webhook 权限

- 创建 Webhook 需要 **Linear 工作区管理员**权限
- 路径：Settings > API > Webhooks > New webhook
- 事件勾选 **Comment**（`mode: comments` 模式必需）
- Team 选择要监控的团队
- Webhook 创建后立即复制 **signing secret**（离开页面后不可再查看）

## 2. 服务端权限

### 2.1 环境变量

| 变量 | 必填 | 敏感度 | 说明 |
|------|------|--------|------|
| `LINEAR_CLIENT_ID` | OAuth 时必填 | 中 | OAuth 应用 ID，不算秘密但不应公开 |
| `LINEAR_CLIENT_SECRET` | OAuth 时必填 | **高** | OAuth 应用密钥，等同密码 |
| `LINEAR_API_KEY` | API Key 时必填 | **高** | 个人 API 密钥 |
| `LINEAR_WEBHOOK_SECRET` | 必填 | **高** | Webhook HMAC 签名密钥，用于验证请求确实来自 Linear |
| `LINEAR_TEAM_KEY` | 必填 | 低 | 团队标识（如 ENG） |
| `LINEAR_BOT_USERNAME` | 必填 | 低 | 机器人显示名 |

- 所有密钥写入 `.env`，该文件不得提交版本库（Skill 使用 set-if-absent 语义，不覆盖已有值）
- `.env` 需同步到容器：`mkdir -p data/env && cp .env data/env/env`

### 2.2 网络

- Webhook 接收端需要**公网可访问的 HTTPS 地址**（Linear 不向 localhost 推送）
- 默认端口 3000，路径 `/webhook/linear`
- 出站方向需要能访问 `https://api.linear.app`（GraphQL API）

### 2.3 发送者策略（sender policy）

通过 `ncl messaging-groups create` 的 `--unknown-sender-policy` 控制：

| 策略 | 适用场景 | 效果 |
|------|----------|------|
| `public` | 私有 Linear 工作区 | 任何能评论的人都能与机器人对话（工作区本身已有访问控制） |
| `strict` | 公开 Linear 工作区 | 仅已注册成员可与机器人对话，其他人的评论被忽略 |

选择 `strict` 时，需额外通过成员注册流程将允许对话的人员加入（参见 GitHub skill 的 add member 流程）。

## 3. 会话隔离

- `--session-mode per-thread`：每个 issue 评论线程获得独立的 agent 会话，上下文互不串扰
- `--engage-mode pattern --engage-pattern .`：匹配所有评论（Linear OAuth 应用无法被 @提及，因此响应每条评论而非仅 @提及）
- 每个 Linear issue 的评论线程天然就是一个独立对话
