# 跨会话可复用上下文：claude-mem OpenClaw 插件集成与验证

> **文档用途**：本文档是"在 OpenClaw 网关上集成 claude-mem 持久记忆插件"这一两周开发任务的跨会话交接手册。新会话开始时，将本文档作为系统上下文注入，即可恢复全部已确认事实、决策、待办和待验证假设，无需重新探索。
>
> **项目标识（claude-mem project 名）**：`openclaw`（默认；多 agent 场景下为 `openclaw-<agentId>`）
> **最后更新**：2026-08-12
> **Skill 版本**：openclaw.plugin.json 声明 13.14.0，package.json/源码日志为 1.0.0（版本不一致，见待办）

---

## 一、已确认事实（经源码阅读与本地测试验证）

### 1.1 插件本质与架构

- claude-mem 是 OpenClaw 网关的**记忆类插件**（`kind: "memory"`，`id: "claude-mem"`），不是独立服务。它通过 HTTP 与一个独立的 **claude-mem worker** 通信，worker 默认监听 `127.0.0.1:37777`。
- 插件入口为 `dist/index.js`（ESM），默认导出一个函数，接收 OpenClaw plugin API 对象。
- 核心数据流：
  - 会话开始 → `POST /api/sessions/init`（2 秒去重窗口，避免重复初始化）
  - 每次构建提示词前 → `GET /api/context/inject?projects=...`，将 worker 返回的时间线文本通过 `appendSystemContext` 注入系统提示词（60 秒按 project 缓存）
  - 工具结果持久化 → `POST /api/sessions/observations`（fire-and-forget，不阻塞；工具响应截断至 1000 字符；`memory_` 前缀工具跳过；cwd 缺失时回退 `process.cwd()`）
  - agent 结束 → `POST /api/sessions/summarize`（**不发送** `/complete`，worker 自行完成）
  - 会话结束 → 清理内部会话映射
  - 网关启动 → 重置熔断器、会话映射、上下文缓存

### 1.2 熔断器行为（已通过单元测试验证）

- 连续 **3 次** worker 请求失败 → 熔断器 OPEN，后续请求静默丢弃（不刷屏日志）
- 冷却 **30 秒** → HALF_OPEN，只放行单个探测请求
- 探测返回 2xx → CLOSED 恢复；非 2xx → 重新 OPEN
- `gateway_start` 事件重置熔断器

### 1.3 注册的命令（源码实际名称，共 5 个）

| 命令名 | 命名风格 | SKILL.md 是否文档化 |
|---|---|---|
| `claude_mem_feed` | 下划线 | 是 |
| `claude_mem_status` | 下划线 | 是 |
| `claude-mem-search` | 连字符 | **否** |
| `claude-mem-recent` | 连字符 | **否** |
| `claude-mem-timeline` | 连字符 | **否** |

- `claude_mem_feed`：无参数显示状态（含连接状态），`on`/`off` 请求启用/停用（需改配置持久化）
- `claude_mem_status`：GET `/api/health`，报告 worker 可达性和端口
- 注意：SKILL.md 第 389 行称"two commands"，实际注册 5 个

### 1.4 注册的事件处理器（7 个）

`before_agent_start`、`session_start`、`after_compaction`、`before_prompt_build`、`tool_result_persist`、`agent_end`、`session_end`、`gateway_start`

### 1.5 配置字段（openclaw.plugin.json configSchema，additionalProperties: false）

| 字段 | 默认值 | 说明 |
|---|---|---|
| `syncMemoryFile` | `true` | 是否启用系统提示词上下文注入 |
| `syncMemoryFileExclude` | `[]` | 排除注入的 agentId 列表 |
| `workerPort` | `37777` | worker HTTP 端口 |
| `workerHost` | `"127.0.0.1"` | worker 主机 |
| `project` | `"openclaw"` | claude-mem 项目名 |
| `observationFeed.enabled` | `false` | 是否启用观察流推送 |
| `observationFeed.channel` | — | 渠道：telegram/discord/slack/signal/whatsapp/line |
| `observationFeed.to` | — | 目标会话/频道 ID |
| `observationFeed.botToken` | — | Telegram bot token（直连 api.telegram.org） |
| `observationFeed.emojis` | 见下 | 表情配置 |

- 默认表情：primary 🦞、claudeCode ⌨️、default 🦀
- project 命名：有 agentId 时为 `openclaw-<agentId>`；上下文注入同时请求 base project 和 agent-scoped project（逗号分隔）

### 1.6 观察流（Observation Feed）

- 后台 SSE 长连接到 worker 的 `/stream`，只处理 `new_observation` 类型事件，其余过滤
- 指数退避重连：1s → 30s 封顶
- 消息长度：普通类型 ≤ 900 字符；重要类型（`security_alert`/`security_note`/`sensitive`/`bugfix`/`decision`）≤ 2200 字符，包含 narrative/facts/concepts
- 渠道发送映射：telegram→`sendMessageTelegram`、discord→`sendMessageDiscord`、slack→`sendMessageSlack`、signal→`sendMessageSignal`、whatsapp→`sendMessageWhatsApp`（支持 verbose 选项）、line→`sendMessageLine`
- 未配置 channel/to 时 service start 记录 "misconfigured" 日志

### 1.7 本地环境与验证结果

- 本机环境：Node v20.19.2、npm 10.8.2、bun 1.3.14；**Docker 不可用**（command not found）
- `npm install`：仅安装 package.json 声明的 devDependencies（typescript、@types/node），无额外依赖
- `npm test`（`tsc && node --test dist/index.test.js`）：**44 个测试全部通过**（8 个 suite，0 失败，耗时约 6.8 秒）
  - 覆盖：插件注册、service start/stop、命令处理、Observation I/O（含 mock worker HTTP 服务器）、before_prompt_build 上下文注入、SSE 流集成、熔断器
- `node test-sse-consumer.js`（冒烟测试）：**2 项失败**——该脚本检查 `claude-mem-feed`/`claude-mem-status`（连字符），但源码注册的是 `claude_mem_feed`/`claude_mem_status`（下划线）。这是冒烟测试脚本本身的命名过时，与 SKILL.md 文档一致的是源码。其余 5 项通过。

### 1.8 已发现的文档/代码不一致（均经核实）

1. **冒烟测试命令名过时**：`test-sse-consumer.js` 检查连字符名，源码和 SKILL.md 用下划线名
2. **版本号三处不一致**：openclaw.plugin.json = 13.14.0，package.json = 1.0.0，源码日志 = v1.0.0
3. **命令数量**：SKILL.md 称 "two commands"，源码注册 5 个（3 个未文档化）
4. **测试数量**：TESTING.md 称 "17 tests"，实际 44 个
5. **TESTING.md 引用不存在的文件**：`test-container.sh` 在 ZIP 中不存在；`mock-worker.js` 不在 src/ 中（tsc 不会生成），但 Dockerfile.e2e 第 43 行尝试 `cp dist/mock-worker.js`
6. **Docker E2E 构建会失败**：因 `dist/mock-worker.js` 无源文件，Dockerfile.e2e 第 43 行 `cp` 会失败
7. **SKILL.md 渠道列表**：文档列 6 种渠道（telegram/discord/slack/signal/whatsapp/line），源码 CHANNEL_SEND_MAP 还包含 imessage（但 SKILL.md 未列）

---

## 二、决策（含约束导致的方案变化）

### 决策 1：验证范围限定为本地单元测试 + 冒烟测试，不执行 Docker E2E

- **原因**：本机 Docker 不可用；E2E 需拉取 `ghcr.io/openclaw/openclaw:main` 镜像（外部依赖）；且 Dockerfile.e2e 本身因缺失 mock-worker 源文件会构建失败
- **替代方案**：单元测试已用 Node 内置 `node:http` 搭建 mock worker 服务器，覆盖了插件与 worker 的全部 HTTP 交互（init/observations/summarize/context inject/SSE stream），验证强度足够

### 决策 2：不连接真实消息渠道账号，只通过 mock 验证投递逻辑

- **原因**：约束要求"若依赖外部账号，只做到安全的模拟或确认前步骤"；Telegram/Discord/Slack 等需要 bot token 和真实账号
- **替代方案**：单元测试中 mock 了全部 6 种渠道的发送函数，验证了 SSE 事件接收、消息格式化、长度截断、渠道分发逻辑；未向任何真实服务发送请求

### 决策 3：不运行真实 claude-mem worker

- **原因**：worker 源码不在本 ZIP 中（SKILL.md 指向 github.com/thedotmack/claude-mem，需 git clone + bun 安装）；约束要求不新增非必要依赖
- **替代方案**：用单元测试中的 mock HTTP 服务器验证插件侧的请求构造和响应处理逻辑

### 决策 4：不执行远程一键安装 `curl -fsSL https://install.cmem.ai/openclaw.sh | bash`

- **原因**：远程管道执行脚本存在安全风险，且依赖外部服务可用性；本地有 `install.sh` 可审阅但未执行（其会修改 ~/.openclaw 等用户目录，属有风险操作）

### 决策 5：不修改任何 Skill 原始文件

- **原因**：约束要求"不修改无关文件"；发现的冒烟测试命名 bug、版本号不一致等问题记录在本文档，不擅自修复
- node_modules 和 dist 是 npm install/tsc 生成的构建产物，非原始文件修改

### 决策 6：不新增任何非必要依赖

- 仅安装 package.json 已声明的 typescript 和 @types/node；测试使用 Node 内置 `node:test`、`node:assert/strict`、`node:http`，未引入 jest/ts-node 等

---

## 三、待办（按 make-plan 方法论分阶段，每阶段自包含、带验证清单）

### Phase 0：文档发现与基线确认 ✅ 已完成

- [x] 通读 SKILL.md（462 行）、TESTING.md（279 行）、子技能 make-plan/SKILL.md、do/SKILL.md
- [x] 通读 src/index.ts（1136 行）、src/index.test.ts（1178 行）
- [x] 通读全部脚本（install.sh、e2e-verify.sh、test-e2e.sh、test-install.sh、Dockerfile.e2e、test-sse-consumer.js）
- [x] 确认 openclaw.plugin.json 配置 schema
- [x] 本地 `npm install && npm test` 通过（44/44）

**验证清单**：
- [x] 插件注册 1 个 service、5 个命令、8 个事件处理器
- [x] tsc 严格模式编译无错误
- [x] 全部单元测试通过

### Phase 1：修复已知不一致（需上游确认后执行）

- [ ] **修复冒烟测试命名**：将 `test-sse-consumer.js` 第 62、69 行的 `claude-mem-feed`/`claude-mem-status` 改为 `claude_mem_feed`/`claude_mem_status`，与源码和 SKILL.md 对齐
- [ ] **统一版本号**：确认 openclaw.plugin.json 的 13.14.0 是否应为 1.0.0（或反之）
- [ ] **补全命令文档**：在 SKILL.md 中补充 `claude-mem-search`、`claude-mem-recent`、`claude-mem-timeline` 三个命令的说明，或确认它们是否为内部命令
- [ ] **修复 Dockerfile.e2e**：补充 `src/mock-worker.ts` 源文件，或修改 Dockerfile 从其他位置获取 mock-worker.js
- [ ] **更新 TESTING.md**：测试数量从 17 改为 44；移除或补充 `test-container.sh` 引用

**验证清单**：
- [ ] `node test-sse-consumer.js` 退出码 0
- [ ] 三个版本号一致
- [ ] `docker build -f Dockerfile.e2e .` 成功（需 Docker 环境）

### Phase 2：真实 worker 集成（需外部环境）

- [ ] 克隆 claude-mem 主仓库：`git clone https://github.com/thedotmack/claude-mem.git`
- [ ] 在仓库目录执行 `bun install && bun run build`
- [ ] 启动 worker：`bun run start`（默认 127.0.0.1:37777）
- [ ] 验证 worker 健康：`curl http://127.0.0.1:37777/api/health`
- [ ] 在 OpenClaw 配置中启用插件（`plugins.slots.memory: "claude-mem"`）
- [ ] 启动 OpenClaw 网关，确认日志出现 "plugin loaded — v1.0.0"

**验证清单**：
- [ ] `/claude_mem_status` 返回 "Status: ok"
- [ ] 新会话首条消息后 worker 收到 `/api/sessions/init`
- [ ] 第二条消息前系统提示词包含 worker 返回的时间线
- [ ] 工具调用后 worker 收到 `/api/sessions/observations`

### Phase 3：观察流渠道验证（需外部账号，仅做确认前步骤）

- [ ] 在 OpenClaw 配置中填写 `observationFeed.enabled: true`、channel、to
- [ ] Telegram 场景：配置 botToken，确认 bot 已被加入目标会话
- [ ] 启动网关，确认日志出现 "SSE stream connected"
- [ ] 触发一次观察（如执行工具调用），确认目标渠道收到推送
- [ ] 验证重要类型（bugfix/decision 等）消息长度 ≤ 2200 字符，普通类型 ≤ 900 字符

**验证清单**：
- [ ] SSE 连接建立且 1-2 秒内收到推送
- [ ] 断网后自动重连（指数退避）
- [ ] `/claude_mem_feed` 显示 "Connection: connected"

### Phase 4：端到端验证（需 Docker 或真实 OpenClaw 环境）

- [ ] 安装 Docker 后执行 `./test-e2e.sh`
- [ ] 或在真实 OpenClaw 环境执行 `e2e-verify.sh` 的各阶段检查
- [ ] 验证插件 doctor 无问题
- [ ] 验证多 agent 场景：agent-scoped project（`openclaw-<agentId>`）上下文隔离

**验证清单**：
- [ ] `plugins list` 显示 claude-mem 且 enabled
- [ ] `plugins doctor` 报告 0 issues
- [ ] E2E 全部检查通过

---

## 四、仍需验证的假设

> 以下假设基于源码阅读推断，但因缺少真实 worker/网关/渠道环境，尚未经端到端验证。

| # | 假设 | 验证方式 | 阻塞条件 |
|---|---|---|---|
| H1 | worker 的 `/api/context/inject` 返回 `text/plain` 时间线文本，格式与插件解析兼容 | 启动真实 worker，检查响应 Content-Type 和正文 | 需克隆 claude-mem 仓库 |
| H2 | worker 的 `/api/search/observations`、`/api/context/recent`、`/api/timeline/by-query` 端点返回插件命令期望的 JSON 结构（items/session_summaries/recent_observations/timeline/anchor 等字段） | 启动真实 worker，调用三个未文档化命令检查输出 | 需真实 worker |
| H3 | OpenClaw 网关的事件对象结构（sessionKey、agentId、workspaceDir、message.content 等）与插件 TypeScript 接口定义一致 | 在真实网关中触发各事件，检查无运行时错误 | 需 OpenClaw 网关 |
| H4 | `openclaw plugins install <dir>` 的安装目录布局与 e2e-verify.sh 假设一致（`/home/node/.openclaw/extensions/`） | 在真实网关执行安装，检查文件位置 | 需 OpenClaw 网关 |
| H5 | 观察流在真实渠道的投递延迟约 1-2 秒，Markdown 格式正确渲染 | Phase 3 真实渠道测试 | 需外部账号 |
| H6 | Docker 场景下 `workerHost: host.docker.internal` 能从容器内访问宿主机 worker | Docker E2E 测试 | 需 Docker |
| H7 | 熔断器 HALF_OPEN 状态在真实 worker 恢复后能正确关闭（单元测试用 mock 时间模拟了 31 秒冷却，真实计时可能有边界差异） | 真实环境停启 worker 观察恢复 | 需真实 worker |
| H8 | `memory_` 前缀工具跳过逻辑覆盖了所有记忆类工具（如 memory_search、memory_recent） | 检查 worker 端是否也有对应过滤 | 需 worker 源码 |
| H9 | 插件在 worker 不可用时不影响 OpenClaw 网关正常运行（fire-and-forget + 熔断器应保证） | 停止 worker 后继续使用网关，确认无阻塞 | 需真实网关 |
| H10 | imessage 渠道在源码 CHANNEL_SEND_MAP 中存在但 SKILL.md 未文档化，是否为可用渠道 | 检查 OpenClaw runtime.channel.imessage 是否存在 | 需 OpenClaw 网关 |

---

## 五、可重复验证命令

以下命令在 `openclaw_skill/openclaw/` 目录下执行，仅依赖 Node.js（≥ 18，内置 node:test 和 fetch）：

```bash
# 1. 安装声明的开发依赖（typescript、@types/node）
npm install

# 2. 编译并运行全部单元测试（预期：44 pass, 0 fail）
npm test

# 3. 冒烟测试（预期：5 OK, 2 FAIL — 已知的命令名过时问题，非插件缺陷）
node test-sse-consumer.js

# 4. 确认构建产物可导入
node -e "import('./dist/index.js').then(m => console.log(typeof m.default))"
# 预期输出：function
```

**验证证据**：见同目录 `verification-evidence.txt`（含测试结果摘要、冒烟测试输出、环境版本）。

---

## 六、反模式守卫（来自 make-plan / do 子技能）

1. **不要凭名称猜测能力**：openclaw 不是"通用记忆工具"，它是 claude-mem 在 OpenClaw 网关上的插件配置 Skill；worker 是独立 HTTP 服务
2. **不要发明 API**：所有 worker 端点、事件名、配置字段必须以源码和 openclaw.plugin.json 为准
3. **不要跳过验证直接提交**：每阶段完成后必须运行验证清单
4. **文档可得 ≠ 已用**：SKILL.md 描述了安装流程，但不代表已在本地执行
5. **验证 > 假设**：第四节的假设在真实环境验证前不得当作事实
6. **不要修改 Skill 原始文件来"修复"问题**：发现的不一致记录在案，等待上游确认
7. **不要连接真实外部账号**：除非用户明确提供凭证并授权，渠道验证只到 mock 层面

---

## 七、文件索引

| 文件 | 说明 |
|---|---|
| `SKILL.md` | 主安装指南（462 行） |
| `TESTING.md` | 测试指南（279 行，部分内容过时） |
| `src/index.ts` | 插件主源码（1136 行） |
| `src/index.test.ts` | 单元测试（1178 行，44 个测试） |
| `openclaw.plugin.json` | 插件清单与配置 schema |
| `package.json` | 依赖声明（typescript ^6.0.3、@types/node ^25.6.2） |
| `tsconfig.json` | TypeScript 严格模式配置 |
| `test-sse-consumer.js` | 冒烟测试（有已知命名 bug） |
| `install.sh` | 本地交互式安装器（需 bun ≥ 1.1.14） |
| `test-install.sh` | 安装流程测试脚本 |
| `e2e-verify.sh` | E2E 验证脚本（4 阶段，在容器/真实网关中运行） |
| `test-e2e.sh` | Docker E2E 构建与运行入口 |
| `Dockerfile.e2e` | E2E 镜像定义（引用缺失的 mock-worker.js） |
| `skills/make-plan/SKILL.md` | 子技能：分阶段实施计划方法论 |
| `skills/do/SKILL.md` | 子技能：子 agent 编排执行方法论 |
