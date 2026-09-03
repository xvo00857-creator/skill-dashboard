#!/usr/bin/env bash
# 验证脚本：查询本人本周飞书考勤打卡记录
# 依赖：lark-cli（已安装）、bash、jq（可选，仅用于美化输出）
# 用法：bash verify_attendance.sh
# 不新增任何非必要依赖，不修改无关文件。

set -euo pipefail

# 抑制 lark-cli 更新通知，保证 JSON 输出稳定
export LARKSUITE_CLI_NO_UPDATE_NOTIFIER=1
export LARKSUITE_CLI_NO_SKILLS_NOTIFIER=1

# 本周日期范围（周一至周日），格式 yyyyMMdd
# 当前日期：2026-08-12（周三），本周一 2026-08-10，本周日 2026-08-16
DATE_FROM=20260810
DATE_TO=20260816

echo "=== 步骤 1：检查 lark-cli ==="
if ! command -v lark-cli >/dev/null 2>&1; then
  echo "错误：未找到 lark-cli，请先安装。"
  exit 1
fi
lark-cli --version
echo ""

echo "=== 步骤 2：查看 API 参数结构（Skill 要求调用前必须先看 schema）==="
lark-cli schema attendance.user_tasks.query 2>&1 | head -5
echo "  ...（schema 已确认：params 需要 employee_type；data 需要 check_date_from/check_date_to/user_ids）"
echo ""

echo "=== 步骤 3：dry-run 预览请求（不实际调用）==="
lark-cli attendance user_tasks query \
  --employee-type employee_no \
  --data "{\"user_ids\":[],\"check_date_from\":${DATE_FROM},\"check_date_to\":${DATE_TO}}" \
  --dry-run 2>&1
echo ""

echo "=== 步骤 4：实际查询本周考勤（${DATE_FROM} ~ ${DATE_TO}）==="
# Skill 规定：employee_type 固定为 employee_no，user_ids 固定为空数组 []
lark-cli attendance user_tasks query \
  --employee-type employee_no \
  --data "{\"user_ids\":[],\"check_date_from\":${DATE_FROM},\"check_date_to\":${DATE_TO}}" \
  2>&1

echo ""
echo "=== 步骤 5：原始响应 ==="
if [ -f download.txt ]; then
  cat download.txt
  echo ""
  # 简单判断（不依赖 jq）
  if grep -q '"user_task_results":\[\]' download.txt; then
    echo ""
    echo "结论：API 调用成功（code=0），但本周考勤记录为空。"
  fi
else
  echo "警告：未找到响应文件 download.txt"
fi
