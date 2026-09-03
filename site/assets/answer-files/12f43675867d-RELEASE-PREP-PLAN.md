# prepare-release 受约束流程方案与演示结果

> 生成时间：2026-08-12 09:52 CST
> 依据 Skill：`prepare-release/SKILL.md`（已解压至 `prepare-release-skill/prepare-release/SKILL.md`）

---

## 一、Skill 能力边界与题目假设的冲突

题目要求"完成代码库协作、架构分析与发布准备"。经阅读 SKILL.md，该 Skill 的实际职责为：

1. 确定版本（基于最新 tag 与 `package.json`）
2. 收集自上次 tag 以来的 commits，提取 `release-note` 块与 conventional commit 类型
3. 生成中英双语发布说明（面向终端用户，排除内部重构/CI/依赖/文档等）
4. 更新 `package.json`、`electron-builder.yml`，运行 `pnpm build:builtin-knowledge`
5. 展示给用户审核（dry-run 在此停止）
6. 创建 `release/v{version}` 分支、提交、推送，并通过 `gh-create-pr` skill 创建 PR

**冲突点**：SKILL.md 全文未涉及"架构分析"。该 Skill 不读取源码结构、不做架构图、不分析模块依赖。按题目要求"以该 Skill 的真实能力边界为准，不扩张职责"，本方案**不包含架构分析**；若需要架构分析，应使用其他专门工具或 Skill，不在本次交付范围内。

"代码库协作"在 SKILL.md 中体现为 Step 6 的分支/PR 创建，本方案予以保留，但受当前权限与环境约束（见第三节）。

---

## 二、受约束的完整流程方案

### 流程总览（6 步 + 预检）

```
Step 0 预检 → Step 1 确定版本 → Step 2 收集 commits → Step 3 生成双语发布说明
→ Step 4 更新文件 → Step 5 人工审核（确认点①）→ Step 6 创建分支+PR（确认点②）
```

### Step 0：预检（新增，幂等）

在任何文件修改或远程操作之前，逐项检查：

| 检查项 | 通过标准 | 失败处理 |
|---|---|---|
| git 仓库 | `git rev-parse --is-inside-work-tree` 成功 | 中止，提示在代码库根目录运行 |
| 必要命令 | `git`、`node`、`pnpm` 可用 | 中止，提示安装 |
| PR 工具 | `gh` 可用，或存在 `.agents/skills/gh-create-pr/SKILL.md` | 警告，Step 6 降级为手动 |
| 必要文件 | `package.json`、`electron-builder.yml` 存在 | 中止 |
| 工作区干净 | `git status --porcelain` 为空 | 中止，提示先提交/stash（幂等保护） |
| 远程可访问 | `git fetch --tags --dry-run` 成功（带重试） | 警告，降级为仅本地 tags |
| 目标分支不存在 | 本地/远程均无 `release/v{new}` | 中止，防止重复发布（幂等保护） |
| 目标 tag 不存在 | `git rev-parse v{new}` 失败 | 中止，防止覆盖已有版本 |

### Step 1：确定版本

- 取最新 tag：`git describe --tags --abbrev=0`
- 读 `package.json` 的 `version`
- 按参数计算：`patch`/`minor`/`major` 基于 tag 递增；显式版本号校验 semver 后直接使用
- **回显目标版本给用户**（SKILL.md 明确要求："Always echo the resolved target version back to the user before proceeding with any file edits"）

### Step 2：收集 commits

- `git log <last-tag>..HEAD --format="%H %s" --no-merges`
- 逐条取完整 body，提取 ` ```release-note ` 块内容
- 提取 conventional commit 类型（`feat`/`fix`/`refactor`/`perf`/`docs` 等）
- **跳过规则**（SKILL.md 明确）：
  - 标题以 `🤖 Daily Auto I18N` 开头
  - 标题以 `Merge` 开头
  - 标题以 `chore(deps)` 开头
  - 标题以 `chore: release` 开头
  - release-note 块内容为 `NONE`

### Step 3：生成双语发布说明

- 严格遵循 SKILL.md 格式：`<!--LANG:en-->` 英文段 + `<!--LANG:zh-CN-->` 中文段 + `<!--LANG:END-->`
- 分类：✨ 新功能 / 🐛 问题修复 / 💄 改进 / ⚡ 性能优化（空分类省略）
- **只包含用户可感知的变更**：排除内部重构、CI/构建、依赖更新、文档、开发者体验、无用户影响的技术债
- 每个 commit 恰好一行；不包含 commit hash 或 PR 号
- 组件标签简短：`[Chat]`、`[Models]`、`[Agent]`、`[MCP]`、`[Settings]`、`[Data]`、`[Build]` 等
- 中文翻译自然，非机翻
- **写之前先读 `electron-builder.yml` 中现有 release notes 作为风格参考**（SKILL.md 约束）

### Step 4：更新文件

仅修改三个文件（SKILL.md 硬约束："Never modify files other than..."）：

1. `package.json`：更新 `version` 字段
2. `electron-builder.yml`：替换 `releaseInfo.releaseNotes: |` 下内容，保持 4 空格 YAML 缩进
3. `resources/builtin-agents/cherry-assistant/product-manifest.json`：**不手改**，运行 `pnpm build:builtin-knowledge` 自动生成

### Step 5：人工审核（确认点①）

展示：新版本号、完整发布说明、被修改文件清单。
- 若 `--dry-run`：在此停止
- 否则**等待用户明确确认**后才进入 Step 6（SKILL.md："ask the user to confirm before proceeding to Step 6"）

### Step 6：创建分支和 PR（确认点②）

```bash
git checkout -b release/v{version}
git add package.json electron-builder.yml resources/builtin-agents/cherry-assistant/product-manifest.json
git commit -m "chore: release v{version}"
git push -u origin release/v{version}   # 带重试
```
- 通过 `gh-create-pr` skill 创建 PR；标题 `chore: release v{version}`，base 为 `main`
- PR 正文包含：英文发布说明、commits 列表、review checklist
- **永不直接推送到 main**（SKILL.md 硬约束）
- 报告 PR URL 与后续步骤

### 幂等设计

- 预检阶段检查目标分支/tag 是否已存在，已存在则中止
- 工作区脏时中止，避免覆盖他人改动
- `git push` 前检查远程分支是否已存在
- 所有检查为只读，预检本身可重复运行无副作用

### 重试策略

- 网络操作（`git fetch`、`git push`）最多重试 3 次，间隔 2 秒（可通过 `RETRY_MAX`/`RETRY_DELAY` 调整）
- 重试仅用于幂等的只读/可安全重试操作；`git commit` 不重试（避免重复提交）

### 人工确认点

1. **Step 5**：文件修改后、创建分支前，展示 diff 与发布说明，等待确认
2. **Step 6**：push 与创建 PR 前确认（非 CI 模式）；CI 模式按 SKILL.md 跳过交互确认

---

## 三、当前环境实际状态（预检真实结果）

### 已具备

- `git` 2.50.1、`node` v20.19.2、`pnpm` 10.34.5、`python3` 3.9.6
- 预检脚本 `pre-release-check.sh` 已编写并可执行

### 缺失 / 无法访问（明确标注，未编造）

| 资源 | 状态 | 影响 |
|---|---|---|
| Cherry Studio 代码库 | **不存在**：当前目录非 git 仓库，无 `package.json`、`electron-builder.yml` | 无法执行 Step 1–6 的任何真实操作 |
| `gh` CLI | **未安装** | Step 6 无法自动创建 PR，需手动或安装 |
| 远程仓库 | 无 origin | 无法 push 分支 |
| 现有 release notes 风格参考 | 无 `electron-builder.yml` | 无法读取历史风格 |
| commits 数据 | 无 git 历史 | 无法收集变更、生成发布说明 |

**因此本次未生成任何真实发布说明、未修改任何代码库文件、未创建分支或 PR。** 按题目要求"不得编造数据、文件内容、运行结果"，发布说明内容留待在真实代码库中执行时生成。

### 仍需确认的假设

1. 目标版本升级类型（patch/minor/major 或具体版本号）——题目未指定，默认 patch
2. Cherry Studio 代码库的实际位置与远程地址
3. 是否具备推送权限与 PR 创建权限
4. `gh-create-pr` skill 在实际环境中是否可用

---

## 四、可核验的演示结果

### 演示方式

在当前工作目录真实运行预检脚本（`--dry-run` 模式），脚本应检测到环境缺失并安全退出，不做任何修改。

### 实际运行输出（2026-08-12 09:52 CST，未篡改）

```
========================================
 prepare-release 预检
 时间: 2026-08-12 09:52:24 CST
 参数: version=patch dry-run=1
========================================

### Step 0: 环境预检
[失败] 当前目录不是 git 仓库（也不在父目录中）。SKILL.md Step 1/2/6 依赖 git。
[通过] 命令可用: git (git version 2.50.1 (Apple Git-154))
[通过] 命令可用: node (v20.19.2)
[通过] 命令可用: pnpm (10.34.5)
[警告] 未找到 gh CLI；Step 6 创建 PR 需手动按 .agents/skills/gh-create-pr/SKILL.md 操作或安装 gh。

### 预检汇总
[失败] 预检未通过：缺少 git 仓库。无法继续任何发布步骤。

请在 Cherry Studio 代码库根目录重新运行本脚本。
EXIT_CODE=1
```

### 可核验点

- 退出码为 1（预检失败，安全中止）
- 运行前后工作区无新增/修改文件（脚本只读检查）
- 脚本路径：`release-prep/pre-release-check.sh`
- 复现命令：`bash release-prep/pre-release-check.sh patch --dry-run`

---

## 五、在真实代码库中的执行方式

将 `pre-release-check.sh` 放入 Cherry Studio 代码库根目录后：

```bash
# 1. 预检 + 干跑（不修改文件、不创建分支）
./pre-release-check.sh patch --dry-run

# 2. 预检通过后，完整流程会依次：
#    - 回显目标版本
#    - 收集 commits 并生成双语发布说明
#    - 更新 package.json / electron-builder.yml
#    - 运行 pnpm build:builtin-knowledge
#    - 展示审核内容，等待人工确认
#    - 确认后创建 release/v{version} 分支并创建 PR
```

---

## 六、实际读取的 Skill 文件

- `prepare-release-skill/prepare-release/SKILL.md`（ZIP 内唯一文件，已完整读取，共 176 行）

## 七、实际影响交付结果的 SKILL.md 规则

**规则**（SKILL.md 第 17 行）："Defaults to `patch` if no version is specified. Always echo the resolved target version back to the user before proceeding with any file edits."

**对交付的影响**：题目未指定版本号，本方案默认按 `patch` 处理并在预检输出中回显了 `version=patch`；同时因该规则要求"任何文件编辑前必须先回显版本"，脚本将版本回显置于所有写操作之前，且在预检失败时根本不进入编辑阶段——这直接决定了演示脚本在当前无代码库环境下只能止步于预检，不能越权生成或修改任何文件。

此外，SKILL.md 第 174 行"Never modify files other than `package.json`, `electron-builder.yml`, and the generated `product-manifest.json`"与第 175 行"Never push directly to `main`"是硬约束，本方案严格遵守，未触碰任何其他文件或分支。
