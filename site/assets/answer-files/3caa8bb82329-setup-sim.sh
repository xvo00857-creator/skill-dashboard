#!/usr/bin/env bash
# 可复现的模拟环境搭建脚本
# 场景：特性分支 fix/login-bug 已通过 squash merge 合入 main，
#       但本地和远程特性分支尚未删除（即"已完成修复但尚未发布/清理"的状态）。
# 用本地裸仓库模拟 origin，无需外部账号或网络。
set -euo pipefail

SIM_DIR="$(cd "$(dirname "$0")" && pwd)"
REMOTE_DIR="$SIM_DIR/remote-repo.git"
WORK_DIR="$SIM_DIR/my-project"

# 清理旧环境（仅清理本脚本创建的目录）
rm -rf "$REMOTE_DIR" "$WORK_DIR"

# 1. 创建裸仓库作为模拟远程 origin
git init --bare "$REMOTE_DIR" >/dev/null 2>&1

# 2. 克隆到工作目录
git clone "$REMOTE_DIR" "$WORK_DIR" >/dev/null 2>&1
cd "$WORK_DIR"
git config user.email "dev@example.com"
git config user.name "Dev"

# 3. 在 main 上创建初始提交
git checkout -b main 2>/dev/null || git checkout main
echo "# My Project" > README.md
git add README.md
git commit -m "chore: initial commit" >/dev/null
git push origin main >/dev/null 2>&1

# 4. 创建特性分支并提交修复（模拟"已完成修复"）
git checkout -b fix/login-bug
echo "def login(user, pwd): return user == 'admin' and pwd == 'secret'" > auth.py
git add auth.py
git commit -m "fix(auth): correct login credential check" >/dev/null
echo "import unittest" > test_auth.py
git add test_auth.py
git commit -m "test(auth): add login unit test" >/dev/null
git push origin fix/login-bug >/dev/null 2>&1

# 5. 切回 main，模拟 PR 的 squash merge（squash 后特性分支提交不会出现在 main 历史中）
git checkout main
git merge --squash fix/login-bug >/dev/null
git commit -m "fix(auth): correct login credential check (#42)" >/dev/null
git push origin main >/dev/null 2>&1

echo "=== 模拟环境搭建完成 ==="
echo "远程裸仓库: $REMOTE_DIR"
echo "工作目录:   $WORK_DIR"
echo ""
echo "--- 当前分支 ---"
git branch
echo ""
echo "--- 远程分支 ---"
git branch -r
echo ""
echo "--- main 最近提交 ---"
git log --oneline -5
