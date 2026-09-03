#!/usr/bin/env bash
# 可重复验证脚本：不依赖 GitHub 账号、不安装第三方依赖、不修改仓库外文件。
# 用法: bash verify.sh
set -u

cd "$(dirname "$0")"
PY="${PYTHON:-python3}"
OUT="/tmp/triage-verify-$$"
PASS=0; FAIL=0

ok()   { echo "[PASS] $1"; PASS=$((PASS+1)); }
fail() { echo "[FAIL] $1"; FAIL=$((FAIL+1)); }

echo "============================================================"
echo " 0. 环境"
echo "============================================================"
$PY --version
echo "git: $(git --version)"
echo "gh:  $(command -v gh || echo '未安装（预期：本环境无 gh，验证走 mock 与预检）')"

echo
echo "============================================================"
echo " 1. 单元测试（分类 / permalink / 零写守卫 / 代码搜索 / 异常）"
echo "============================================================"
if $PY -m unittest -v test_triage.py; then
  ok "单元测试全部通过"
else
  fail "单元测试存在失败"
fi

echo
echo "============================================================"
echo " 2. mock 全流程（无需账号）"
echo "============================================================"
rm -rf "$OUT"
if $PY triage.py --mock --report-dir "$OUT"; then
  ok "mock 全流程退出码 0"
else
  fail "mock 全流程失败"
fi

echo "--- 生成文件 ---"
ls -1 "$OUT" || true

for f in SUMMARY.md issue-101.md issue-102.md issue-103.md issue-104.md issue-105.md pr-201.md pr-202.md; do
  if [ -f "$OUT/$f" ]; then ok "存在 $f"; else fail "缺少 $f"; fi
done

echo
echo "--- 关键证据检查 ---"
grep -q "MOCK MODE" "$OUT/issue-101.md" && ok "报告含 MOCK 标记" || fail "缺 MOCK 标记"
grep -q "blob/7fd1a60b01f91b314f59955a4e4d4e80d8edf11d" "$OUT/issue-101.md" && ok "permalink 使用 commit SHA（非分支）" || fail "permalink 未用 SHA"
grep -q "Verdict: CONFIRMED_BUG" "$OUT/issue-102.md" && ok "issue-102 判定 CONFIRMED_BUG" || fail "issue-102 判定错误"
grep -q "Verdict: ALREADY_FIXED" "$OUT/issue-103.md" && ok "issue-103 判定 ALREADY_FIXED" || fail "issue-103 判定错误"
grep -q "commit/a1b2c3d4" "$OUT/issue-103.md" && ok "issue-103 含修复提交 permalink" || fail "缺修复提交链接"
grep -q "Merge Readiness" "$OUT/pr-201.md" && ok "PR 报告含 Merge Readiness 表" || fail "PR 报告缺表"
grep -q "只读" "$OUT/pr-201.md" && ok "PR 报告声明只读" || fail "缺只读声明"
grep -qF "Items Processed:** 7" "$OUT/SUMMARY.md" && ok "SUMMARY 计数为 7" || fail "SUMMARY 计数错误"

echo
echo "--- SUMMARY.md 摘要 ---"
sed -n '1,40p' "$OUT/SUMMARY.md"

echo
echo "============================================================"
echo " 3. 确认前预检（--check，只读；本环境应报告 gh 缺失）"
echo "============================================================"
set +e
$PY triage.py --check
CHECK_CODE=$?
set -e
if [ "$CHECK_CODE" -eq 2 ]; then
  ok "--check 正确返回 2（未就绪）并指出 gh 缺失"
elif [ "$CHECK_CODE" -eq 0 ]; then
  ok "--check 返回 0（环境已就绪）"
else
  fail "--check 返回异常码 $CHECK_CODE"
fi

echo
echo "============================================================"
echo " 4. 零写策略直接验证（尝试构造写命令，必须被拒绝）"
echo "============================================================"
$PY - <<'PYEOF'
import triage
cases = [
    (["issue","comment","1","--body","x"], "issue comment"),
    (["issue","close","1"], "issue close"),
    (["pr","merge","1"], "pr merge"),
    (["pr","review","1","--approve"], "pr review"),
    (["api","-X","POST","repos/o/r/issues"], "api POST"),
    (["api","--method","DELETE","x"], "api DELETE"),
]
ok=True
for args, name in cases:
    try:
        triage._guard_gh(args)
        print(f"[FAIL] 未拦截: {name}"); ok=False
    except triage.ForbiddenCommandError:
        print(f"[PASS] 已拦截: {name}")
for args in (["checkout","main"],["push"],["switch","dev"]):
    try:
        triage._guard_git(args)
        print(f"[FAIL] 未拦截 git {' '.join(args)}"); ok=False
    except triage.ForbiddenCommandError:
        print(f"[PASS] 已拦截 git {' '.join(args)}")
# 白名单内只读命令应通过守卫
for args in (["issue","list"],["pr","view","1"],["api","repos/o/r/pulls/1/files"]):
    try:
        triage._guard_gh(args); print(f"[PASS] 放行只读 gh {' '.join(args)}")
    except triage.ForbiddenCommandError:
        print(f"[FAIL] 误拦截只读 gh {' '.join(args)}"); ok=False
raise SystemExit(0 if ok else 1)
PYEOF
if [ $? -eq 0 ]; then ok "零写守卫全部符合预期"; else fail "零写守卫存在问题"; fi

echo
echo "============================================================"
echo " 5. 异常处理：缺 gh 时真实模式应明确报错而非崩溃"
echo "============================================================"
set +e
$PY triage.py --repo octocat/Hello-World 2> "$OUT/real-err.txt"
REAL_CODE=$?
set -e
if [ "${REAL_CODE:-0}" -ne 0 ] && grep -q "gh" "$OUT/real-err.txt"; then
  ok "真实模式在缺 gh 时给出明确错误（退出码 ${REAL_CODE}）"
else
  fail "真实模式错误处理异常（退出码 ${REAL_CODE:-?}）"
fi
echo "错误输出: $(cat "$OUT/real-err.txt")"

echo
echo "============================================================"
echo " 结果: PASS=$PASS FAIL=$FAIL"
echo " 示例报告目录: $OUT"
echo "============================================================"
exit $FAIL
