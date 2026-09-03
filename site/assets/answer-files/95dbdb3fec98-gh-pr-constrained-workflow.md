# gh-create-pr 受约束流程方案

> 本方案严格依据 `gh-create-pr/SKILL.md` 制定。该 Skill 的真实能力边界是：
> **按仓库 `.github/pull_request_template.md` 模板规范创建或更新 GitHub PR**。
> 它不包含通用架构分析、版本打标签、CI/CD 发布编排等职责；题目中"架构分析"不在本 Skill 范围内，
> "发布准备"仅覆盖 PR 模板内的 Release note 与 Documentation 勾选规则。

## 0. 能力边界声明（与题目假设的冲突点）

| 题目期望 | Skill 实际能力 | 处理方式 |
|---|---|---|
| 代码库协作 | 覆盖：分支推送、base/head 判定、PR 创建 | 纳入流程 |
| 架构分析 | **不覆盖**：SKILL.md 无任何架构分析步骤 | 明确标注为超范围，不编造分析结论 |
| 发布准备 | 部分覆盖：Release note 块与 Documentation 勾选规则 | 仅覆盖模板内部分；打 tag、发版等不覆盖 |

## 1. 预检（Pre-flight Checks）

在任何写操作前依次执行，任一失败即中止并报告，不继续后续步骤：

| 编号 | 检查项 | 命令 | 失败处理 |
|---|---|---|---|
| P1 | 当前在 git 工作树内 | `git rev-parse --is-inside-work-tree` | 中止，提示先 `cd` 到仓库 |
| P2 | 当前在分支上（非 detached HEAD） | `git symbolic-ref --quiet HEAD` | 中止，提示先 checkout 分支 |
| P3 | `gh` CLI 已安装 | `command -v gh` | 中止，提示安装 GitHub CLI（不代为安装） |
| P4 | `gh` 已认证 | `gh auth status` | 中止，提示 `gh auth login` |
| P5 | PR 模板存在 | `test -f .github/pull_request_template.md` | 中止，提示模板缺失 |
| P6 | 远端存在 | `git remote get-url <remote>` | 中止/询问 |
| P7 | 当前分支已有提交（非空分支） | `git rev-parse --verify HEAD` | 中止 |
| P8 | 工作区是否干净（仅提示，不阻断） | `git status --porcelain` | 提示有未提交改动 |

## 2. 幂等（Idempotency）

| 编号 | 幂等点 | 做法 |
|---|---|---|
| I1 | 分支是否已推送 | `git ls-remote --heads <remote> <head>` 已存在则跳过 push |
| I2 | PR 是否已存在 | `gh pr list --head <head> --state open --json number,url`；若已存在则改为 `gh pr edit` 更新，不重复创建 |
| I3 | 临时文件 | 用 `trap 'rm -f "$pr_body_file"' EXIT` 保证清理；文件名带时间戳避免冲突 |
| I4 | 重复执行 | 同一 head 分支重复运行脚本不会产生第二个 PR |

## 3. 重试（Retry）

仅对瞬时错误重试，对确定性错误（认证失败、模板缺失、权限不足）立即失败并交人工处理：

| 操作 | 可重试错误 | 策略 |
|---|---|---|
| `git push` | 网络超时、5xx、连接重置 | 最多 3 次，指数退避（2s/4s/8s） |
| `gh pr create` | HTTP 5xx、网络错误 | 最多 3 次，指数退避 |
| `gh pr create` | 401/403/404、422 校验错误 | **不重试**，直接报错交人工 |
| `gh auth status` | 任意失败 | 不重试，交人工 |

## 4. 人工确认点（Human-in-the-loop）

| 编号 | 确认点 | 触发条件 | Skill 依据 |
|---|---|---|---|
| C1 | 远端选择 | 远端不是 `origin` 时 | SKILL.md 步骤 3 |
| C2 | base 分支确认 | base 不是默认值（`main` 或 fork 场景的 `upstream/main`）时 | SKILL.md 步骤 4 |
| C3 | PR body 全文预览确认 | **始终触发**，除非用户明确放弃预览 | SKILL.md 步骤 6 及 Constraints："Never create the PR before showing the full final body" |
| C4 | 最终创建确认 | 预览后、执行 `gh pr create` 前 | 受约束模式额外增加 |

## 5. 流程步骤（与 SKILL.md 一一对应）

1. **读模板**：`cat .github/pull_request_template.md`，保留全部章节与 markdown 结构。
2. **收集上下文**：base/head、改动范围、关联 issue、测试状态、破坏性变更、release note 内容。
3. **推送分支**：先查 I1；未推送则 `git push -u <remote> <head>`（可重试）。
4. **判定 base**：
   - 官方仓库 `CherryHQ/cherry-studio` 为 origin → 默认 `main`；
   - head 为 `hotfix/*` 且为关键用户可见修复 → base 必须为 `v1`；
   - fork 为 origin → 默认目标 `upstream/main`（始终假设合入 cherry-studio/main）；
   - 非默认 base 需 C2 确认。
5. **写 PR body 到临时文件**：用单个 Bash heredoc（SKILL.md 指定方式，规避 Windows 路径问题）；
   严格按模板结构填写，不适用项写 `N/A` 或 `None`，**不跳过任何章节**。
6. **预览**：`cat "$pr_body_file"`，展示文件路径，等待 C3 确认。
7. **创建 PR**：确认后执行 `gh pr create --base <base> --head <head> --title "<title>" --body-file "$pr_body_file"`。
8. **清理**：`rm -f "$pr_body_file"`（trap 兜底）。
9. **报告**：输出 PR URL、title/base/head 及后续事项。

## 6. Release note 与 Documentation 勾选规则（SKILL.md 表格）

| 变更类型 | Release note | Docs 勾选 |
|---|---|---|
| 新用户可见功能/设置/UI | 描述变更 | 是 |
| 用户可见的 bug 修复 | 描述修复 | 行为改变时勾选 |
| 行为/默认值变更 | 描述 + `action required` | 是 |
| 用户可见依赖的安全修复 | 描述修复 | 用法改变时勾选 |
| CI / GitHub Actions | `NONE` | 否 |
| 内部重构（用户无感知） | `NONE` | 否 |
| 开发/构建工具变更 | `NONE` | 否 |
| 仅开发依赖升级 | `NONE` | 否 |
| 仅测试/代码风格 | `NONE` | 否 |

## 7. 本次环境预检结果（真实执行）

| 检查项 | 结果 |
|---|---|
| P1 git 工作树 | **失败**：当前目录不是 git 仓库 |
| P3 gh CLI | **失败**：`gh` 未安装（command not found） |
| P4 gh 认证 | 无法检查（gh 不存在） |
| P5 PR 模板 | 本地不存在；已只读获取公开模板用于干跑演示 |
| git 身份 | `user.name` / `user.email` 均未配置 |

**结论**：本次不具备真实创建 PR 的条件。按"不能静默创建外部资源"要求，不安装 gh、不初始化仓库、
不创建真实 PR。下文提供干跑演示以验证模板填充与流程编排逻辑，所有写操作步骤均只打印不执行。
