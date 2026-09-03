# 权限边界说明 — issue-triage-summary

本文档说明 `issue-triage-summary` 工作流的权限模型、写入路径和网络边界。

## 1. 总体安全模型

工作流采用 gh-aw 的**只读 Agent + 安全输出（safe-outputs）**模式：

- **Agent 主任务**：仅持有 `contents: read` 和 `issues: read`，不能直接调用任何 GitHub 写入 API。
- **写入操作**：全部通过 `safe-outputs` 声明，由独立的、权限受限的框架作业执行，与 Agent 沙箱隔离。
- **网络出口**：仅允许 `defaults`（GitHub/Copilot 基础设施、CA 证书、JSON Schema），不访问任何第三方域名。

## 2. GitHub Token 权限矩阵

| 权限范围 | Agent 主任务 | safe-outputs 作业 | 说明 |
|---|---|---|---|
| `contents` | `read` | — | 读取仓库文件（如需） |
| `issues` | `read` | `write`（仅 add-labels / add-comment 作业） | Agent 只读；写权限由框架按需授予安全输出作业 |
| `pull-requests` | 未授予 | — | 本工作流不涉及 PR |
| `actions` | 未授予 | — | 不读取 CI 运行记录 |
| `discussions` | 未授予 | — | 不涉及 Discussion |
| `metadata` | 默认 read | 默认 read | GitHub Actions 隐式授予 |

**明确禁止**：Agent 任务不持有 `issues: write`、`contents: write`、`pull-requests: write`。根据 gh-aw 约束，授予这些写权限会导致编译失败。

## 3. 安全输出（写入路径）

### 3.1 add-labels

| 配置项 | 值 | 作用 |
|---|---|---|
| `allowed` | `bug, enhancement, documentation, question, duplicate, invalid, good first issue, help wanted` | Agent 只能从这 8 个标签中选择；不能创建新标签或添加列表外标签 |
| `max` | `3` | 每次运行最多添加 3 个标签 |
| `target` | `triggering`（默认） | 只对触发本次运行的 Issue 操作 |

### 3.2 add-comment

| 配置项 | 值 | 作用 |
|---|---|---|
| `max` | `1` | 每次运行最多发布 1 条评论 |
| `target` | `triggering`（默认） | 只评论触发本次运行的 Issue |

### 3.3 全局输出约束

| 配置项 | 值 | 作用 |
|---|---|---|
| `mentions` | `false` | 转义所有 `@用户`，防止意外通知 |
| `max-bot-mentions` | `0` | 中和 `fixes #123` / `closes #456` 等机器人触发短语，防止意外关闭 Issue |

> Issue 编号引用（如 `#42`）保持可用，用于标注疑似重复；这是有意保留的交叉引用能力。

## 4. 工具与命令边界

| 工具 | 配置 | 边界 |
|---|---|---|
| GitHub 读取 | `tools.github.mode: gh-proxy`，`toolsets: [default]` | Agent 通过预认证的 `gh` 读取 Issue/标签/搜索；不启用 `users`、`projects` 等额外工具集 |
| Bash | 允许列表 `[mkdir, gh, jq, cat]` | 因工作流读取不可信的 Issue 正文，按 gh-aw 安全规范使用窄允许列表，防止 shell 注入扩大影响面 |
| MCP 服务器 | 未配置 | 不引入任何第三方 MCP |
| Playwright | 未启用 | 不需要浏览器 |
| 网络 | `network.allowed: [defaults]` | 仅基础设施域名；不允许 npm/pypi/docker 等生态出口 |

## 5. 触发边界

| 触发器 | 范围 |
|---|---|
| `issues.types: [opened]` | 仅新 Issue 打开时触发；不在编辑/关闭/重开时重复运行 |
| `workflow_dispatch` | 手动触发，用于对单个 Issue 重新分拣 |
| `skip-bots: [dependabot, renovate]` | 跳过 Dependabot 和 Renovate 创建的 Issue |

## 6. 数据边界

- **预取数据**：Agent 在 `steps:` 中通过 `gh` + `jq` 预取 3 个紧凑 JSON 文件到 `/tmp/gh-aw/data/`（当前 Issue、仓库标签列表、相似 Issue），Agent 读取这些文件而非广泛在线查询。
- **不可信输入处理**：Issue 编号通过环境变量 `ISSUE_NUMBER` 传入 `run:` 脚本，不直接拼接到脚本文本中；Issue 标题通过 shell 变量传递给 `gh search`，降低 shell 注入风险。
- **数据保留**：预取数据仅存于运行时临时目录，随作业结束销毁；不使用外部存储或缓存。

## 7. 部署前确认清单

在真实仓库启用前，需人工确认：

1. 仓库中已存在 `allowed` 列表中的标签（或接受 gh-aw 自动创建缺失标签的默认行为）。
2. 仓库已启用 GitHub Agentic Workflows（gh-aw）并安装 `gh aw` CLI。
3. 确认 `GITHUB_TOKEN` 对 Issue 有读取权限（默认即有）。
4. 如需跨仓库分拣，需额外配置 `target-repo` / `allowed-repos`（当前未配置，仅本仓库）。
5. 无需配置任何 Secret：本工作流不依赖外部 API、第三方服务或自定义 Token。
