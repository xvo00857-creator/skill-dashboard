#!/usr/bin/env bash
# 重新生成全部内置模板到 generated/ 目录
# 用法: bash scripts/regenerate.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
OUT_DIR="$ROOT_DIR/generated"
mkdir -p "$OUT_DIR"

TEMPLATES=(meeting-notes decision-log runbook project-kickoff sprint-retro how-to-guide)

echo "==> 重新生成 ${#TEMPLATES[@]} 个内置模板到 $OUT_DIR"
for t in "${TEMPLATES[@]}"; do
  python3 "$SCRIPT_DIR/template_scaffolder.py" "$t" --format json > "$OUT_DIR/${t}.json"
  python3 "$SCRIPT_DIR/template_scaffolder.py" "$t"             > "$OUT_DIR/${t}.txt"
  echo "    - $t"
done

echo "==> 完成"
