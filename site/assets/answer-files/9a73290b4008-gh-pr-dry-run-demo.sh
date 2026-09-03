#!/usr/bin/env bash
# gh-create-pr 干跑演示脚本（dry-run）
# 严格遵循 gh-create-pr/SKILL.md 的工作流，增加预检/幂等/重试/人工确认点。
# 本脚本不执行任何对外部资源的写操作：不 push、不创建 PR、不安装软件。
# 演示场景为【假设的用户可见 bug 修复】，仅用于验证模板填充逻辑，不代表真实改动。

set -euo pipefail

echo "============================================================"
echo " gh-create-pr 干跑演示（DRY-RUN，不创建任何外部资源）"
echo "============================================================"
echo ""

# ---------- 演示用假设输入（真实场景应由 git 状态推导） ----------
DEMO_REMOTE="origin"
DEMO_HEAD="fix/offline-provider-refresh-crash"
DEMO_BASE="main"
DEMO_TITLE="fix: handle empty provider list response when offline"
# 注意：以下为假设场景，无对应真实代码改动
DEMO_TEMPLATE="/tmp/cherry-pr-template-demo.md"

# ---------- 预检 P1-P5 ----------
echo ">>> [预检 P1] 是否在 git 工作树内"
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "    通过"
else
  echo "    失败：当前目录不是 git 仓库（预期：演示环境无真实仓库）"
fi
echo ""

echo ">>> [预检 P3] gh CLI 是否安装"
if command -v gh >/dev/null 2>&1; then
  echo "    通过：$(gh --version | head -1)"
else
  echo "    失败：gh 未安装（预期：演示环境未安装）"
fi
echo ""

echo ">>> [预检 P4] gh 认证状态"
if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
  echo "    通过"
else
  echo "    跳过/失败：gh 不可用，无法检查认证"
fi
echo ""

echo ">>> [预检 P5] PR 模板是否存在"
if [ -f "$DEMO_TEMPLATE" ]; then
  echo "    通过：${DEMO_TEMPLATE}（$(wc -c < "$DEMO_TEMPLATE") bytes，只读获取自公开仓库）"
else
  echo "    失败：模板不存在"
  exit 1
fi
echo ""

# ---------- 幂等 I1：分支是否已推送（演示中模拟） ----------
echo ">>> [幂等 I1] 检查 head 分支是否已推送至远端"
echo "    将执行：git ls-remote --heads $DEMO_REMOTE $DEMO_HEAD"
echo "    （干跑：不执行；真实环境若已存在则跳过 push）"
echo ""

# ---------- 幂等 I2：PR 是否已存在（演示中模拟） ----------
echo ">>> [幂等 I2] 检查是否已存在 open PR"
echo "    将执行：gh pr list --head $DEMO_HEAD --state open --json number,url"
echo "    （干跑：不执行；真实环境若已存在则改用 gh pr edit，不重复创建）"
echo ""

# ---------- 步骤 5：用 heredoc 写 PR body 到临时文件 ----------
echo ">>> [步骤 5] 按模板结构生成 PR body（heredoc 方式，不跳过任何章节）"
pr_body_file="/tmp/gh-pr-body-$(date +%s).md"
trap 'rm -f "$pr_body_file"' EXIT

cat > "$pr_body_file" <<'EOF'
<!-- Template from https://github.com/kubevirt/kubevirt/blob/main/.github/PULL_REQUEST_TEMPLATE.md?-->
<!--  Thanks for sending a pull request!  Here are some tips for you:
1. Consider creating this PR as draft: https://github.com/CherryHQ/cherry-studio/blob/main/CONTRIBUTING.md
-->

> ### Branch strategy
>
> - Active development targets `main`.
> - v1 maintenance targets `v1`; forward-port fixes to `main` separately when needed.

### What this PR does

Before this PR:
Refreshing the provider list while offline could crash the app because an empty/error response was not guarded.

After this PR:
The refresh path handles empty and error responses gracefully and shows an inline error message instead of crashing.

<!-- (optional, in `fixes #<issue number>(, fixes #<issue_number>, ...)` format, will close the issue(s) when PR gets merged)*: -->

Fixes #N/A

### Why we need it and why it was done in this way

The following tradeoffs were made:
N/A

The following alternatives were considered:
N/A

Links to places where the discussion took place: N/A

### Breaking changes

<!-- optional -->

N/A

### Special notes for your reviewer

<!-- optional -->

N/A

### Checklist

This checklist is not enforcing, but it's a reminder of items that could be relevant to every PR.
Approvers are expected to review this list.

- [x] Branch: This PR targets the correct branch — `main` for active development, `v1` for v1 maintenance fixes
- [x] PR: The PR description is expressive enough and will help future contributors
- [x] Code: [Write code that humans can understand](https://en.wikiquote.org/wiki/Martin_Fowler#code_for_humans) and [Keep it simple](https://en.wikipedia.org/wiki/KISS_principle)
- [x] Refactor: You have [left the code cleaner than you found it (Boy Scout Rule)](https://learning.oreilly.com/library/view/97-things-every/9780596809519/ch08.html)
- [x] Upgrade: Impact of this change on upgrade flows was considered and addressed if required
- [x] Documentation: A [user-guide update](https://docs.cherry-ai.com) was considered and is present (link) or not required. Check this only when the PR introduces or changes a user-facing feature or behavior.
- [x] Self-review: I have reviewed my own code (e.g., via [`/gh-pr-review`](/.claude/skills/gh-pr-review/SKILL.md), `gh pr diff`, or GitHub UI) before requesting review from others

### Release note

<!--  Write your release note:
1. Enter your extended release note in the below block. If the PR requires additional action from users switching to the new release, include the string "action required".
2. If no release note is required, just write "NONE".
3. Only include user-facing changes (new features, bug fixes visible to users, UI changes, behavior changes). For CI, maintenance, internal refactoring, build tooling, or other non-user-facing work, write "NONE".
-->

```release-note
Fix a crash that could occur when refreshing the provider list while offline; an inline error is now shown instead.
```
EOF

echo "    已写入临时文件：$pr_body_file"
echo ""

# ---------- 步骤 6：预览（cat，按 SKILL.md 要求用 Bash cat 而非 Read 工具） ----------
echo ">>> [步骤 6 / 人工确认 C3] PR body 全文预览（等待人工确认后才会创建）"
echo "------------------------------------------------------------"
cat "$pr_body_file"
echo "------------------------------------------------------------"
echo ""

# ---------- 结构合规自检（可核验） ----------
echo ">>> [合规自检] 校验模板章节未被跳过"
missing=0
for section in "### What this PR does" "### Why we need it and why it was done in this way" \
                "### Breaking changes" "### Special notes for your reviewer" \
                "### Checklist" "### Release note" '```release-note'; do
  if grep -qF "$section" "$pr_body_file"; then
    echo "    [OK] 保留章节：$section"
  else
    echo "    [缺失] $section"
    missing=1
  fi
done
if [ "$missing" -eq 0 ]; then
  echo "    结果：全部章节与 release-note 代码块均保留，结构与模板一致。"
else
  echo "    结果：存在缺失，禁止创建 PR。"
fi
echo ""

# ---------- 步骤 7：打印将执行的创建命令（不执行） ----------
echo ">>> [步骤 7 / 人工确认 C4] 待人工确认后将执行的命令（本次干跑不执行）："
echo "    gh pr create --base $DEMO_BASE --head $DEMO_HEAD --title \"$DEMO_TITLE\" --body-file \"$pr_body_file\""
echo ""
echo ">>> [重试策略] 若上述命令返回 5xx/网络错误，将按 2s/4s/8s 退避重试最多 3 次；"
echo "    若返回 401/403/404/422，则不重试，直接交人工处理。"
echo ""

# ---------- 步骤 8：清理 ----------
echo ">>> [步骤 8] 清理临时文件"
rm -f "$pr_body_file"
echo "    已删除：$pr_body_file"
echo ""

echo "============================================================"
echo " 干跑演示结束。未执行任何 push / PR 创建 / 软件安装。"
echo "============================================================"
