# version-bump 受约束发布流程方案

> 本方案基于随包提供的 `version-bump` Skill 真实能力边界制定，未执行任何对外部资源的创建、删除、覆盖或发布操作。所有"已执行"项均有本机命令输出可核验；所有"未执行/不可达"项均明确标注。

---

## 一、预检结论（实际执行，可核验）

| 检查项 | 结果 | 说明 |
|---|---|---|
| node | ✅ v20.19.2 | 可运行 changelog 脚本 |
| npm | ✅ 10.8.2 | 可做只读查询；**未执行 publish** |
| git | ✅ 2.50.1 | 可用 |
| gh (GitHub CLI) | ❌ 未安装 | SKILL.md 第 8 步 `gh release create` 无法执行 |
| 当前目录是否 git 仓库 | ❌ 否 | 无 `.git`，不存在 8 个清单文件 |
| `~/Scripts/claude-mem/` | ❌ 不存在 | SKILL.md 第 11 步 Discord 通知无法执行 |
| npm 上 `claude-mem` 包 | ⚠️ 只读可查，最新公开版 13.15.0 | 无法确认即本 Skill 目标仓库；**未发布** |
| 随包脚本 `scripts/generate_changelog.js` | ❌ 语法错误，无法运行 | 见下文"演示结果" |

**结论：完整发布工作流在当前环境不具备执行条件。** 本方案只交付"受约束的流程设计 + 一次可核验的组件演示"，不伪造任何版本号变更、提交、标签、推送、发布或通知。

---

## 二、Skill 能力边界与题目假设的冲突（以 SKILL.md 为准）

1. **Skill 目标项目是 `claude-mem`**（SKILL.md 第 17、41、47 行多次出现 `npx claude-mem@X.Y.Z`），不是任意代码库。题目要求"代码库协作、架构分析与发布准备"，但 Skill 本身是一个**面向固定项目、固定 8 个清单文件路径**的版本号提升脚本，不承担通用架构分析职责。架构分析仅限于"版本字符串在 8 个清单中的传播路径"。
2. **npm 发布必须人工**（SKILL.md 第 36–48 行）：维护者提出 npm 安全顾虑，agent **禁止**执行 `npm publish` / `np` / `npm run release:*`。这是硬性边界，本方案严格遵守。
3. **脚本文件名不一致**：SKILL.md 第 55 行写 `scripts/generate-changelog.js`（连字符），随包实际文件为 `scripts/generate_changelog.js`（下划线）。若 `package.json` 的 `changelog:generate` 脚本按文档写连字符，会直接 `MODULE_NOT_FOUND`。
4. **脚本不直接拉取 GitHub API**：SKILL.md 第 55 行称脚本"pulls releases from the GitHub API"，但实际脚本只从 **stdin** 读取 JSON（`fs.readFileSync(0, 'utf8')`）。API 获取应由 npm 脚本包装层完成，脚本本身无网络能力。
5. **随包脚本存在语法错误**（见第四节），第 9 步在修复前必然失败。

---

## 三、受约束的发布流程（含预检 / 幂等 / 重试 / 人工确认点）

### 阶段 0 — 预检（全部通过才继续）

| # | 检查 | 命令 / 方式 | 失败处理 |
|---|---|---|---|
| 0.1 | 在目标仓库根目录 | `git rev-parse --is-inside-work-tree` | 停止，提示切换目录 |
| 0.2 | 工作区干净 | `git status --porcelain` 为空 | 停止，先处理未提交改动 |
| 0.3 | 在 main 分支且与远端同步 | `git rev-parse --abbrev-ref HEAD` = main；`git fetch && git status -sb` 无 ahead/behind | 停止 |
| 0.4 | 远端可识别 owner/repo | `git remote -v` | 停止 |
| 0.5 | 8 个清单文件全部存在 | 逐文件 `test -f` | 停止，列出缺失项 |
| 0.6 | 工具齐全 | `command -v node npm git gh` | gh 缺失 → 第 8 步转人工 |
| 0.7 | npm 已登录（仅查询，不发布） | `npm whoami` | 失败不阻塞，但第 7 步需人工 |
| 0.8 | changelog 脚本可运行 | `node --check scripts/generate_changelog.js` | **当前失败** → 必须先修复并经人工确认 |
| 0.9 | 旧版本号在 8 个文件中均存在 | `git grep -l "\"version\": \"<OLD>\""` 列出 8 个 | 少于 8 → 停止，人工核对是否新增清单 |

### 阶段 1 — 版本分析与发布说明（人工确认点 ①）

- 按变更判定 PATCH / MINOR / MAJOR（SKILL.md 第 14 行）。
- 先写发布说明（SKILL.md 第 8 行 IMPORTANT）。
- **暂停，向人工展示**：变更类型、旧版本 → 新版本、发布说明全文，等待确认后才动手改文件。

### 阶段 2 — 更新版本号（幂等）

- 幂等检查：若 `git grep -l "\"version\": \"<NEW>\""` 已列出全部 8 个文件，且旧版本 0 命中，则视为本步已完成，直接跳过。
- 否则逐文件替换 8 个清单中的版本字符串；**不触碰 `CHANGELOG.md`**（SKILL.md 第 30 行，它由脚本重新生成）。
- 校验：
  - `git grep -n "\"version\": \"<NEW>\""` → 必须 8 处
  - `git grep -n "\"version\": \"<OLD>\""` → 必须 0 处

### 阶段 3 — 构建与同步（重试）

- 执行 `npm run build-and-sync`（SKILL.md 第 32 行；不得用 `npm run build`，否则本地 marketplace/worker 不同步）。
- 失败重试：最多 2 次（间隔 10s、30s 指数退避）；仍失败则停止，不进入提交。构建产物按 SKILL.md 第 10 行 CRITICAL 规则一并提交。

### 阶段 4 — 提交（幂等）

- 幂等检查：若最近一条提交已是 `chore: bump version to X.Y.Z`，跳过。
- 否则 `git add -A && git commit -m "chore: bump version to X.Y.Z"`。

### 阶段 5 — 打标签（幂等）

- 幂等检查：`git tag -l vX.Y.Z` 非空则跳过。
- 否则 `git tag -a vX.Y.Z -m "Version X.Y.Z"`。

### 阶段 6 — 推送（人工确认点 ② + 重试）

- **推送前暂停**，向人工确认分支与标签将推送到 `origin`。
- `git push origin main && git push origin vX.Y.Z`。
- 网络失败重试：最多 3 次（10s / 30s / 60s 退避）；冲突或鉴权失败不重试，交人工。

### 阶段 7 — npm 发布（人工确认点 ③，Skill 强制人工）

- **agent 不得执行 `npm publish` / `np` / `npm run release:*`**（SKILL.md 第 38–39 行）。
- 停止并告知人工：版本已提交、打标签、推送，需由其执行：
  ```bash
  npm publish   # 由人工执行；prepublishOnly 会重新构建
  ```
- 等待人工确认后，agent 仅做只读校验：
  ```bash
  npm view claude-mem@X.Y.Z version   # 应输出 X.Y.Z
  ```
- 若发布构建改动了本地产物，再跑一次 `npm run build-and-sync`（SKILL.md 第 49 行）。

### 阶段 8 — GitHub Release（人工确认点 ④，工具缺失则转人工）

- 若 `gh` 可用且已认证：先 `gh release view vX.Y.Z` 幂等检查，存在则跳过；否则 `gh release create vX.Y.Z --title "vX.Y.Z" --notes "<RELEASE_NOTES>"`。
- **当前环境 `gh` 未安装** → 本步骤转人工：在 GitHub 网页以标签 vX.Y.Z 创建 Release，粘贴发布说明。

### 阶段 9 — 重新生成 Changelog（依赖修复）

- 前提：阶段 0.8 的脚本语法问题已修复，且文件名与 `package.json` 中 `changelog:generate` 的路径一致。
- 执行 `npm run changelog:generate`（实际为 `node scripts/generate_changelog.js`，从 stdin 读 release JSON）。
- 注意脚本行为边界（经演示验证）：
  - 最多输出 50 条 release（`slice(0, 50)`，超出静默截断）；
  - `published_at` 字段缺失会抛错（无防御性校验）；
  - 纯函数、同输入同输出，可安全重跑（幂等）。

### 阶段 10 — 同步 Changelog（幂等）

- `git add CHANGELOG.md && git commit -m "chore: update changelog for vX.Y.Z" && git push origin main`。
- 若 `CHANGELOG.md` 无 diff 则跳过。

### 阶段 11 — Discord 通知（人工确认点 ⑤，路径缺失则转人工）

- SKILL.md 第 57–61 行要求在 `~/Scripts/claude-mym/` 下执行（该目录存放含 webhook 的 `.env`）。
- **当前环境该目录不存在** → 转人工：由维护者在其本机执行 `npm run discord:notify vX.Y.Z`。
- agent 不得自行编造 webhook 或发送通知。

### 阶段 12 — 终检

- `git status` 必须干净（SKILL.md 第 62 行 CRITICAL：结束时无未提交/未推送内容）。
- 汇总：8 文件版本一致、标签已推送、npm 已由人工发布并校验、GitHub Release 已建、Changelog 已推送、通知已发、工作区干净。

---

## 四、一次可核验的演示结果

### 4.1 演示对象

随包真实脚本 `version-bump/scripts/generate_changelog.js`（从 stdin 读取 GitHub release JSON 数组，生成 Markdown Changelog）。

### 4.2 原脚本语法校验（真实输出）

```
$ node --check version-bump-skill/version-bump/scripts/generate_changelog.js
SyntaxError: Invalid or unexpected token
    at line 8:  process.stderr.write('No input received on stdin
```

`cat -vet` 证实：第 8–9 行单引号字符串内含真实换行；第 24–26 行 `lines.join('` 后为真实换行；第 28–29 行以反引号开头却以单引号 `');` 结尾。**原脚本在 Node v20 下无法运行，SKILL.md 第 9 步在修复前必然失败。**

### 4.3 修复副本（仅改字符串转义，逻辑不变）

为验证脚本**预期**行为，在 `demo/generate_changelog.fixed.js` 建了明确标注的修复副本（**未改动 Skill 原文件**），`node --check` 通过。

### 4.4 用例结果（合成测试数据，非真实 release）

输入文件：`demo/releases.sample.json`（3 条合成 release）。

| 用例 | 输入 | 结果 | 退出码 |
|---|---|---|---|
| A 正常 | 3 条合法 release | 生成 `# Changelog` + 3 个版本段落，输出已存 `demo/CHANGELOG.sample.md` | 0 |
| B 空输入 | 空 stdin | `No input received on stdin` | 1 |
| C 非法 JSON | `not json` | `Unexpected token 'o' ... is not valid JSON` | 1 |
| D 缺字段 | 缺 `published_at` | `Cannot read properties of undefined (reading 'split')` | 1 |

### 4.5 幂等性

同输入两次运行，输出 sha256 均为 `87f1dc1b6e17ae4c208a8e22369ccb2f7b3c4f67fdc1d79a010ff10b69e`，**幂等**。

### 4.6 截断行为

输入 60 条 release，输出仅 50 个版本段落（`slice(0, 50)` 静默截断）。

---

## 五、无法访问的资源与仍需确认的假设

| 项 | 状态 | 需人工确认 |
|---|---|---|
| claude-mem 目标 git 仓库 | 未提供，当前目录非 git 仓库 | 提供仓库路径或克隆地址 |
| 8 个清单文件 | 不存在 | 确认是否仍为 SKILL.md 所列 8 个，或有新增 |
| 旧版本号 / 新版本号 | 未给定 | 确认变更类型与目标版本 |
| `gh` CLI | 未安装 | 安装并认证，或第 8 步转人工 |
| npm 发布凭据 / 2FA | 按 Skill 必须人工 | 维护者本人执行 `npm publish` |
| `~/Scripts/claude-mem/.env` (Discord webhook) | 目录不存在 | 维护者本机执行通知 |
| `package.json` 中 `changelog:generate` 实际指向的文件名 | 未提供 | 确认是连字符还是下划线，需与实际文件对齐 |
| npm 上 `claude-mem@13.15.0` 是否为本项目 | 无法确认 | 维护者确认 |
| 原脚本语法错误是否为打包/压缩损坏 | 无法确认 | 建议从上游重新获取或按修复副本修正后提交 |

---

## 六、实际读取的 Skill 文件（相对路径）

1. `version-bump/SKILL.md`
2. `version-bump/scripts/generate_changelog.js`

（均位于解压目录 `version-bump-skill/` 下；ZIP 内仅含这两个文件。）

---

## 七、实际影响交付结果的 SKILL.md 规则（至少一条）

**规则：SKILL.md 第 36–48 行——npm 发布必须交接给人工，agent 禁止执行 `npm publish`（及 `np`、`npm run release:*`）。**

对交付的实际影响：
- 本方案的阶段 7 设计为"停止 + 告知人工命令 + 等待确认后只读校验"，而非自动发布；
- 演示中我也只做了 `npm view claude-mem version` 只读查询，未执行任何发布；
- 这直接决定了"发布准备"只能做到"提交/打标签/推送就绪 + 发布说明交付"，真正的 npm 发布动作不在本次可交付范围内。

另一条同样影响结果的规则是第 10 行 CRITICAL"提交一切（含构建产物），结束时 `git status` 必须干净"——它使阶段 3 必须用 `build-and-sync` 而非 `build`，并设阶段 12 终检；但因无仓库，该规则本次只能体现在流程设计中，未能实跑。

---

## 八、演示产物清单（均在本机工作目录）

- `demo/releases.sample.json` — 合成测试输入
- `demo/generate_changelog.fixed.js` — 明确标注的修复副本（未改 Skill 原文件）
- `demo/CHANGELOG.sample.md` — 用例 A 的真实输出
