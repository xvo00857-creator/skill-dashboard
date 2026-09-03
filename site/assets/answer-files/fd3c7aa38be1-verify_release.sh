#!/usr/bin/env bash
# 可重复验证脚本 — 验证 fix/release-1.2.1 分支的修复
# 用法: bash verify_release.sh
# 前置条件: 在仓库根目录执行，已安装 python3 和 pytest
set -euo pipefail

echo "========================================="
echo " 1.2.1 发布验证"
echo "========================================="

# 1. 确认当前分支
BRANCH=$(git branch --show-current)
echo ""
echo "[1/6] 当前分支: $BRANCH"
if [ "$BRANCH" != "fix/release-1.2.1" ]; then
  echo "ERROR: 不在 fix/release-1.2.1 分支" >&2
  exit 1
fi

# 2. 确认工作区干净
echo ""
echo "[2/6] 工作区状态:"
if [ -n "$(git status --porcelain)" ]; then
  echo "ERROR: 工作区不干净" >&2
  git status --short
  exit 1
fi
echo "  clean"

# 3. 确认提交数量和原子性
echo ""
echo "[3/6] 提交历史 (相对于 main):"
git log --oneline main..HEAD
COMMIT_COUNT=$(git rev-list --count main..HEAD)
echo "  提交数: $COMMIT_COUNT"
if [ "$COMMIT_COUNT" -lt 3 ]; then
  echo "ERROR: 提交数少于最小要求 (ceil(8/3)=3)" >&2
  exit 1
fi

# 4. 确认未新增依赖
echo ""
echo "[4/6] 依赖检查:"
if git diff main..HEAD --name-only | grep -q "requirements.txt"; then
  echo "WARN: requirements.txt 有变更，请人工确认"
else
  echo "  requirements.txt 未变更 (无新依赖)"
fi

# 5. 运行测试
echo ""
echo "[5/6] 运行测试:"
python3 -m pytest tests/ -v

# 6. 验证缺陷修复行为
echo ""
echo "[6/6] 缺陷修复行为验证:"

echo -n "  divide(10,0) 抛出 ValueError ... "
python3 -c "
from src.calculator import divide
try:
    divide(10, 0)
    print('FAIL (未抛出异常)')
    exit(1)
except ValueError as e:
    assert 'Cannot divide by zero' in str(e)
    print('PASS')
except ZeroDivisionError:
    print('FAIL (仍抛出 ZeroDivisionError)')
    exit(1)
"

echo -n "  validate_email 支持 plus 地址 ... "
python3 -c "
from src.validator import validate_email
assert validate_email('user+tag@example.com') == True
assert validate_email('user@mail.example.com') == True
print('PASS')
"

echo -n "  DEFAULT_TIMEOUT == 30 ... "
python3 -c "
from config.settings import DEFAULT_TIMEOUT
assert DEFAULT_TIMEOUT == 30, f'期望 30, 实际 {DEFAULT_TIMEOUT}'
print('PASS')
"

echo -n "  format_date 可用 ... "
python3 -c "
from datetime import datetime
from src.formatter import format_date, truncate
assert format_date(datetime(2026,8,12)) == '2026-08-12'
assert truncate('a'*200, 10) == 'a'*7 + '...'
print('PASS')
"

echo ""
echo "========================================="
echo " 全部验证通过"
echo "========================================="
