#!/usr/bin/env bash
# 可重复验证脚本：运行 api-design-reviewer 的三个工具，分别校验草稿（应失败）与最终版（应通过）。
# 用法：bash verify.sh
# 依赖：python3（标准库即可，无需 pip install）
set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
S="$HERE/../api-design-reviewer-extracted/api-design-reviewer/scripts"
OUT="$HERE/reports"
mkdir -p "$OUT"

pass=0
fail=0

run_check() {
  local name="$1"; shift
  local expect="$1"; shift
  # expect = 0 表示期望退出码 0；非 0 表示期望非 0（用于草稿演示问题被拦截）
  "$@" >/dev/null 2>&1
  local rc=$?
  if [ "$expect" = "0" ]; then
    if [ "$rc" -eq 0 ]; then echo "[PASS] $name (exit=$rc)"; pass=$((pass+1));
    else echo "[FAIL] $name (exit=$rc, 期望 0)"; fail=$((fail+1)); fi
  else
    if [ "$rc" -ne 0 ]; then echo "[PASS] $name (exit=$rc, 按预期被拦截)"; pass=$((pass+1));
    else echo "[FAIL] $name (exit=0, 期望非 0)"; fail=$((fail+1)); fi
  fi
}

echo "== 重新生成草稿与最终版规格（从 v1 + 生成脚本）=="
python3 "$HERE/gen_draft.py"
python3 "$HERE/gen_final.py"

echo
echo "== 草稿（含问题，应被拦截）=="
run_check "draft: linter 无 error"            0   python3 "$S/api_linter.py"            "$HERE/openapi-v2-draft.json" --format json --output "$OUT/lint-draft.json"
run_check "draft: breaking-change 拦截破坏性变更" 1 python3 "$S/breaking_change_detector.py" "$HERE/openapi-v1.json" "$HERE/openapi-v2-draft.json" --format json --exit-on-breaking --output "$OUT/breaking-draft.json"
run_check "draft: scorecard 未达 B"          1 python3 "$S/api_scorecard.py"          "$HERE/openapi-v2-draft.json" --format json --min-grade B --output "$OUT/scorecard-draft.json"

echo
echo "== 最终版（修复后，应全部通过）=="
run_check "final: linter 无 error"            0 python3 "$S/api_linter.py"            "$HERE/openapi-v2-final.json" --format json --output "$OUT/lint-final.json"
run_check "final: breaking-change 无破坏性变更" 0 python3 "$S/breaking_change_detector.py" "$HERE/openapi-v1.json" "$HERE/openapi-v2-final.json" --format json --exit-on-breaking --output "$OUT/breaking-final.json"
run_check "final: scorecard >= B"            0 python3 "$S/api_scorecard.py"          "$HERE/openapi-v2-final.json" --format json --min-grade B --output "$OUT/scorecard-final.json"

echo
echo "结果：PASS=$pass FAIL=$fail"
echo "工具 JSON 输出目录：$OUT"
[ "$fail" -eq 0 ]
