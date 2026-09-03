#!/usr/bin/env bash
# 可重复验证脚本 — 在 cc-wf-studio 沙盒根目录运行
# 用法: bash ../verify.sh
set -euo pipefail

echo "===== 1. 分支与提交 ====="
git branch --show-current
git log main..HEAD --oneline

echo ""
echo "===== 2. 工作树干净 ====="
test -z "$(git status --porcelain)" && echo "CLEAN" || { echo "DIRTY"; git status --porcelain; exit 1; }

echo ""
echo "===== 3. 变更范围（仅 vscode + changeset）====="
git diff main...HEAD --name-only

echo ""
echo "===== 4. Changeset 识别 ====="
pnpm changeset status

echo ""
echo "===== 5. 类型检查 ====="
pnpm check

echo ""
echo "===== 6. 完整构建 ====="
pnpm build

echo ""
echo "===== 7. 回归测试 ====="
node dist/vscode/src/changelog.test.js

echo ""
echo "===== 全部验证通过 ====="
