# add-matrix Skill — 受约束流程方案与演示结果

## 1. Skill 真实能力边界（重要）

`add-matrix` **不是数学意义上的"矩阵加法"工具**。按 `SKILL.md` 原文，它的职责是：

> Add Matrix channel integration via Chat SDK. Works with any Matrix homeserver.

即为 **NanoClaw** 项目通过 Chat SDK bridge 添加 **Matrix**（开源即时通讯协议，matrix.org 那一套）渠道支持。它面向一个真实的 NanoClaw 代码仓库工作，包含 5 个机械 Apply 步骤和一组人工凭证步骤。本次交付严格以此为准，未扩展到矩阵运算、未替用户注册账号、未访问任何真实 Matrix 服务器。

## 2. SKILL.md 步骤到自动化流程的映射

| SKILL.md 步骤 | 指令栅栏 | 自动化动作 | 幂等保证 | 风险/确认点 |
|---|---|---|---|---|
| 1. 复制 adapter | `nc:copy from-branch:channels` | `git show channels:src/channels/matrix*.ts` 写入 `src/channels/` | 分支为 canonical，可重复覆盖 | 覆盖已存在文件前需确认 |
| 2. 注册 adapter | `nc:append to:src/channels/index.ts` | 追加 `import './matrix.js';` | `grep -qxF` 检测，已存在则跳过 | 仅追加一行 |
| 3. 安装依赖 | `nc:dep` | `pnpm add @beeper/chat-adapter-matrix@0.2.0` | 已装 0.2.0 则跳过 | 修改 node_modules/lockfile，需确认；网络操作带 3 次指数退避重试 |
| 4. 修补 ESM | `nc:run effect:external` | node 脚本为 `matrix-js-sdk/lib/*` 导入补 `.js` | 正则只匹配无 `.js` 的导入，重跑安全 | 每次 `pnpm install` 后需重跑 |
| 5. 构建/测试 | `nc:run effect:build/test` | `pnpm run build` + `vitest run matrix-registration` | 只读校验 | 失败即中止 |
| 凭证 | `nc:prompt` / `nc:env-set` | 交互收集 base_url/user_id/bot_username 及 A 或 B 认证块，upsert 到 `.env` | 按键 upsert，不产生重复行 | 写入 `.env` 前确认；bot 必须为独立账号 |

## 3. 受约束机制

- **预检（preflight）**：执行前校验目标是 git 仓库、存在 `channels` 分支、分支上确有两个 adapter 文件、存在 `package.json` 与 `src/channels/`、node/pnpm/git 可用。任一不满足即安全退出，不做任何修改。
- **幂等（idempotent）**：步骤 2/3/4/凭证均为幂等；整脚本可重复运行。
- **重试（retry）**：仅对网络操作 `pnpm add` 做最多 3 次、2/4 秒退避重试；本地文件操作不重试。
- **人工确认（human gate）**：覆盖文件、`pnpm add`、写 `.env` 前均需确认；非交互模式下遇确认点直接中止（除非显式 `--yes`）。
- **干跑（dry-run）**：`--dry-run` 只打印动作不落盘。
- **边界**：不静默创建/删除/覆盖外部资源；不替用户在 Element 注册 bot；不做端到端投递验证（SKILL.md 明确该步需人工）。

## 4. 当前环境真实状态与可执行性

实测（2026-08-12，macOS）：

- node v20.19.2、pnpm 10.34.5、git 2.50.1 均可用。
- 当前工作目录**不是** NanoClaw 仓库：无 `.git`、无 `channels` 分支、无 `package.json`、无 `src/channels/`。
- 因此 Apply 步骤 1–5 **无法在当前环境真实落地**。脚本如实停在预检并返回退出码 1，未编造任何复制/安装/构建/测试结果。

> 注：SKILL.md 步骤 4 的修补动机是 "Node 22 strict ESM resolution"，当前机为 node 20；该 patch 在 node 20 下同样可运行且幂等，但真实构建验证需在目标仓库的 node 版本下进行。

## 5. 一次可核验的演示结果

所有演示均在 `mktemp -d` 临时目录中运行，不触碰外部资源，可重跑核验。

### 演示 A/B/C（`demo-idempotency.sh`）
- **A 步骤2 幂等**：第 1 次执行追加 `import './matrix.js';`，第 2 次检测到已存在并跳过。
- **B 步骤4 幂等**：第 1 次把 `from "matrix-js-sdk/lib/client"` 修补为 `.../client.js`；第 2 次输出"已修补过，无需改动（幂等）"。
- **C 预检拦截**：对"有 git 但无 channels 分支"的目录，预检报"缺少 channels 分支"并退出。

### 演示 D/E（`demo-credentials.sh`，使用 `apply-fixtures.json` 假值）
- **D 全流程 dry-run**：在一个仅含占位文件的最小仓库上，预检 4 项全过，步骤 1–6 以 dry-run 走完，未写盘、未联网。
- **E .env upsert 幂等**：用 fixtures 假值写入；重复写入不产生重复行；更新 `MATRIX_BASE_URL` 为新值时原地更新；最终 `.env` 为 3 行、每键 1 行；`MATRIX_PASSWORD` 在日志中脱敏为 `***`。

`.env` 最终内容（均为 fixtures 假值，无真实凭证）：
```
MATRIX_BASE_URL=https://matrix2.example.com
MATRIX_USER_ID=@nanoclaw:example.com
MATRIX_PASSWORD=fake-password
```

## 6. 仍需确认的假设 / 无法访问的资源

1. **目标 NanoClaw 仓库路径未知**：需用户提供真实仓库（含 `channels` 分支）后用 `--repo <path>` 执行。
2. **真实 Matrix bot 凭证缺失**：需人工在 Element 注册独立 bot 账号并选择 Option A（用户名+密码）或 Option B（access token）；脚本不代劳。
3. **端到端消息投递未验证**：SKILL.md 明确需服务启动后人工对真实 homeserver 验证。
4. **Option A/B 同时设置时的优先级**：SKILL.md 未定义同时存在 `MATRIX_PASSWORD` 与 `MATRIX_ACCESS_TOKEN` 时 adapter 取哪个；fixtures 注释要求程序化 apply 回答所有 prompt，但生产环境应二选一。脚本在 `--auth-method all` 时会打印警告。
5. **`/manage-channels` 等后续命令**属于 NanoClaw 运行时交互，不在本脚本范围内。

## 7. 文件清单

- `apply-matrix-channel.sh` — 受约束执行器（预检/幂等/重试/确认/干跑）
- `lib/env-upsert.mjs` — `.env` 幂等 upsert 辅助
- `demo-idempotency.sh` — 步骤 2/4 幂等 + 预检拦截演示
- `demo-credentials.sh` — 全流程 dry-run + 凭证 upsert 演示
- `README-受约束流程方案.md` — 本文档

## 8. 实际读取的 Skill 文件（相对路径）

- `add-matrix/SKILL.md`
- `add-matrix/REMOVE.md`
- `add-matrix/apply-fixtures.json`

## 9. 实际影响交付结果的 SKILL.md 规则（至少一条）

> SKILL.md 第 13–14 行："Every directive is idempotent, so the whole skill is safe to re-run; anything a parser can't apply falls back to the prose beside it."

这条规则直接决定了交付形态：执行器把每个 `nc:` 指令都实现为可重跑的幂等操作（步骤 2 的 grep 跳过、步骤 3 的版本检测、步骤 4 的正则只补缺失扩展名、凭证的 upsert），并在无法机械应用的环节（bot 注册、端到端验证）保留为人工 prose 步骤而非伪造自动化。

另一条关键规则是第 39–41 行的**固定版本策略**："Pinned to an exact version — the supply-chain policy rejects ranges and `latest`"，因此步骤 3 严格使用 `@beeper/chat-adapter-matrix@0.2.0`，未使用 `^`/`~`/`latest`。
