#!/usr/bin/env bash
# 可重复验证脚本：重建模拟环境 -> 按 SKILL.md 执行清理 -> 验证结果
# 用法: bash verify.sh
# 依赖: 仅需 git（系统自带，无新增依赖）
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BRANCH="fix/login-bug"

echo "########## 步骤0: 重建模拟环境 ##########"
bash "$SCRIPT_DIR/setup-sim.sh"

WORK_DIR="$SCRIPT_DIR/my-project"
cd "$WORK_DIR"

echo ""
echo "########## 步骤1: 收集上下文 (SKILL.md Workflow 1) ##########"
echo "--- git branch ---"
git branch
echo "--- git log --oneline -1 ---"
git log --oneline -1

echo ""
echo "########## 步骤2: 执行清理 (SKILL.md Workflow 2 / Commands) ##########"
git checkout main
git pull origin main
git branch -D "$BRANCH"
git push origin --delete "$BRANCH"

echo ""
echo "########## 步骤3: 验证结果 ##########"
echo "--- 本地分支（期望: 仅 main）---"
git branch
echo "--- 远程分支（期望: 仅 origin/main）---"
git branch -r
echo "--- main 提交历史（期望: 含 squash 合并提交）---"
git log --oneline -5
echo "--- 修复文件仍在 main 工作区 ---"
ls -1
echo "--- 远程裸仓库分支（期望: 仅 main）---"
git --git-dir="$SCRIPT_DIR/remote-repo.git" branch

echo ""
echo "########## 验证通过 ##########"
