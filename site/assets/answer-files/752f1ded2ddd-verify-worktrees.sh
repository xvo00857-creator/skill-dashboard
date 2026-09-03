#!/usr/bin/env bash
# =============================================================================
# using-git-worktrees 可重复验证脚本
#
# 用途：在本地沙盒中完整验证"两个并行任务的 git worktree 隔离工作区"方案。
# 依赖：仅需 git 和 bash，不安装任何第三方依赖，不依赖外部账号，不执行 push。
# 用法：bash verify-worktrees.sh
#
# 验证内容：
#   1. 安全验证（.worktrees 必须被 .gitignore 忽略）
#   2. 为两个并行任务创建 worktree
#   3. 隔离性验证（各 worktree 文件/提交互不可见，同分支不可重复检出）
#   4. 同步策略（rebase / merge 两种方式）
#   5. 安全清理（干净才可移除、有改动被拒绝、prune 残留）
# =============================================================================
set -euo pipefail

SANDBOX="$(mktemp -d)/worktree-demo"
echo "==> 沙盒目录: $SANDBOX"
echo

# ---------------------------------------------------------------------------
# 0. 创建主仓库
# ---------------------------------------------------------------------------
echo "== [0/6] 创建沙盒主仓库 =="
mkdir -p "$SANDBOX" && cd "$SANDBOX"
git init -b main
git config user.email "demo@example.com"
git config user.name "Demo User"
echo "# Worktree Demo" > README.md
echo "console.log('main app');" > app.js
git add . && git commit -m "初始提交"
echo

# ---------------------------------------------------------------------------
# 1. 安全验证：.worktrees 必须被 git 忽略（Skill Step 1b Safety Verification）
# ---------------------------------------------------------------------------
echo "== [1/6] 安全验证：.worktrees 必须被 .gitignore 忽略 =="
if git check-ignore -q .worktrees 2>/dev/null; then
    echo "    .worktrees 已被忽略"
else
    echo "    .worktrees 未忽略 → 写入 .gitignore 并提交"
    echo ".worktrees/" >> .gitignore
    git add .gitignore && git commit -m "chore: 忽略 .worktrees 目录"
fi
echo

# ---------------------------------------------------------------------------
# 2. 为两个并行任务创建 worktree
# ---------------------------------------------------------------------------
echo "== [2/6] 创建两个并行任务的 worktree =="
git worktree add ".worktrees/feature-user-auth"   -b "feature/user-auth"
git worktree add ".worktrees/bugfix-payment-timeout" -b "bugfix/payment-timeout"
git worktree list
echo

# ---------------------------------------------------------------------------
# 3. 隔离性验证
# ---------------------------------------------------------------------------
echo "== [3/6] 验证隔离性 =="
# 任务 A 提交 auth.js
( cd .worktrees/feature-user-auth
  echo "function login(u,p){return true;}" > auth.js
  git add auth.js && git commit -q -m "feat(auth): 添加登录函数" )
# 任务 B 提交 payment.js
( cd .worktrees/bugfix-payment-timeout
  echo "function pay(o){return 'ok';}" > payment.js
  git add payment.js && git commit -q -m "fix(payment): 修复支付超时" )

echo "    feature-user-auth 文件: $(ls -1 .worktrees/feature-user-auth | tr '\n' ' ')"
echo "    bugfix-payment-timeout 文件: $(ls -1 .worktrees/bugfix-payment-timeout | tr '\n' ' ')"

# 断言：A 不应有 payment.js，B 不应有 auth.js
[ ! -f .worktrees/feature-user-auth/payment.js ] || { echo "FAIL: 隔离失败"; exit 1; }
[ ! -f .worktrees/bugfix-payment-timeout/auth.js ] || { echo "FAIL: 隔离失败"; exit 1; }
echo "    ✓ 文件隔离正确"

# 同分支不可重复检出
if git worktree add ".worktrees/dup" feature/user-auth 2>/dev/null; then
    echo "FAIL: 同分支不应可重复检出"; exit 1
else
    echo "    ✓ 同分支重复检出被 git 正确拒绝"
fi
echo

# ---------------------------------------------------------------------------
# 4. 同步策略：main 有新提交后，rebase 与 merge 两种方式
# ---------------------------------------------------------------------------
echo "== [4/6] 验证同步策略 =="
echo "const v='1.1.0';" > version.js
git add version.js && git commit -q -m "chore: 版本号更新到 1.1.0"

( cd .worktrees/feature-user-auth && git rebase main -q )
echo "    ✓ feature/user-auth rebase main 成功"
( cd .worktrees/bugfix-payment-timeout && git merge main --no-edit -q )
echo "    ✓ bugfix/payment-timeout merge main 成功"
echo

# ---------------------------------------------------------------------------
# 5. 安全清理
# ---------------------------------------------------------------------------
echo "== [5/6] 验证安全清理 =="
# 有未提交改动时 remove 必须被拒绝
echo "// dirty" >> .worktrees/bugfix-payment-timeout/payment.js
if git worktree remove .worktrees/bugfix-payment-timeout 2>/dev/null; then
    echo "FAIL: 有改动时不应允许移除"; exit 1
else
    echo "    ✓ 有未提交改动时 remove 被拒绝"
fi
( cd .worktrees/bugfix-payment-timeout && git checkout -- payment.js )

# 干净后移除；任务 A 合并后删分支
git merge feature/user-auth --no-edit -q >/dev/null 2>&1 || true
git worktree remove .worktrees/feature-user-auth
git branch -d feature/user-auth
git worktree remove .worktrees/bugfix-payment-timeout
git worktree prune
echo "    ✓ worktree 已移除，prune 完成"
echo

# ---------------------------------------------------------------------------
# 6. 最终状态
# ---------------------------------------------------------------------------
echo "== [6/6] 最终状态 =="
echo "    worktree 列表:"
git worktree list | sed 's/^/      /'
echo "    分支列表: $(git branch | tr '\n' ' ')"
echo
echo "==> 全部验证通过 ✓"
echo "==> 沙盒目录（可手动删除）: $SANDBOX"
