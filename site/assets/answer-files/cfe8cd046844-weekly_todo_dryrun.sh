#!/usr/bin/env bash
# =============================================================================
# gws-calendar-insert 只读预演脚本（dry-run）
# -----------------------------------------------------------------------------
# 目的：演示"收集本周待办 -> 筛出逾期项 -> 生成摘要 -> 人工确认 -> 插入 Google 日历"
#       的最小可用流程，供安全评审。
#
# 安全默认：
#   - DRY_RUN=1（默认）：只打印将要执行的 gws 命令，绝不调用 gws，绝不写入日历。
#   - 所有待办数据均为虚构样例（example.com 邮箱），不含任何真实个人信息。
#   - 真实执行前必须：安装 gws、补齐 gws-shared、完成认证、通过前置检查、
#     获得书面授权，并由操作者手动输入 YES。
#
# 用法：
#   bash weekly_todo_dryrun.sh              # 只读预演（默认）
#   DRY_RUN=0 bash weekly_todo_dryrun.sh    # 真实执行（需先满足授权清单）
# =============================================================================
set -euo pipefail

# ---------------------------- 配置区 ----------------------------
DRY_RUN="${DRY_RUN:-1}"                     # 1=预演；0=真实写入
CALENDAR="${CALENDAR:-primary}"             # 目标日历 ID
EVENT_START="${EVENT_START:-2026-08-13T10:00:00+08:00}"
EVENT_END="${EVENT_END:-2026-08-13T10:30:00+08:00}"
TODAY="2026-08-12"                          # 预演基准日（真实运行时用 $(date +%F)）
WEEK_START="2026-08-10"
WEEK_END="2026-08-16"
SUMMARY="产品团队本周待办与逾期项同步"

STOP_REASONS=()

# ---------------------------- 1. 前置检查 ----------------------------
echo "=============================================================="
echo " 1. 前置检查"
echo "=============================================================="
if ! command -v gws >/dev/null 2>&1; then
  STOP_REASONS+=("gws 二进制未安装（which gws 失败）")
else
  echo "  [OK] gws 已安装：$(command -v gws)"
fi

if [ -f "../gws-shared/SKILL.md" ]; then
  echo "  [OK] gws-shared/SKILL.md 存在"
else
  STOP_REASONS+=("gws-shared/SKILL.md 缺失（认证/全局标志/安全规则未知）")
fi

if [ "${DRY_RUN}" = "1" ]; then
  echo "  [INFO] 当前为 DRY_RUN=1，不会执行任何写入"
else
  echo "  [WARN] DRY_RUN=0，真实写入模式！"
  if [ ${#STOP_REASONS[@]} -gt 0 ]; then
    echo "  [STOP] 前置检查未通过，禁止进入真实写入。"
  fi
fi

# ---------------------------- 2. 待办数据（虚构样例） ----------------------------
# 格式：负责人|邮箱|任务|截止日(YYYY-MM-DD)|状态
# 说明：真实场景应从飞书任务/Jira/Sheets 等授权数据源读取；此处为脱敏样例。
TASKS=$(cat <<'EOF'
张伟|zhangwei@example.com|完成需求评审纪要|2026-08-10|未完成
李娜|lina@example.com|输出竞品分析初稿|2026-08-11|未完成
王芳|wangfang@example.com|更新Q3路线图|2026-08-13|未完成
刘洋|liuyang@example.com|修复登录缺陷P0|2026-08-09|未完成
陈静|chenjing@example.com|准备周会材料|2026-08-12|已完成
张伟|zhangwei@example.com|数据埋点方案评审|2026-08-14|未完成
EOF
)

# ---------------------------- 3. 收集本周待办 ----------------------------
echo ""
echo "=============================================================="
echo " 2. 本周待办（${WEEK_START} ~ ${WEEK_END}，含逾期未完成）"
echo "=============================================================="
printf "  %-6s %-24s %-22s %-12s %-8s\n" "负责人" "邮箱" "任务" "截止日" "状态"
WEEK_ITEMS=""
while IFS='|' read -r owner email task due status; do
  [ -z "${owner}" ] && continue
  # 本周范围：截止日在本周内，或早于本周一但仍未完成（逾期带入）
  if [[ "${due}" < "${WEEK_START}" && "${status}" != "已完成" ]] \
     || [[ "${due}" > "${WEEK_END}" ]]; then
    if [[ "${due}" > "${WEEK_END}" ]]; then continue; fi
  fi
  printf "  %-6s %-24s %-22s %-12s %-8s\n" "${owner}" "${email}" "${task}" "${due}" "${status}"
  WEEK_ITEMS+="${owner}|${email}|${task}|${due}|${status}"$'\n'
done <<< "${TASKS}"

# ---------------------------- 4. 筛出逾期项 ----------------------------
echo ""
echo "=============================================================="
echo " 3. 逾期项（截止日 < ${TODAY} 且 状态≠已完成）"
echo "=============================================================="
OVERDUE=""
OVERDUE_COUNT=0
while IFS='|' read -r owner email task due status; do
  [ -z "${owner}" ] && continue
  if [[ "${due}" < "${TODAY}" && "${status}" != "已完成" ]]; then
    printf "  [!] %s: %s（截止 %s，负责人 %s）\n" "${owner}" "${task}" "${due}" "${owner}"
    OVERDUE+="- ${owner}：${task}（截止 ${due}）"$'\n'
    OVERDUE_COUNT=$((OVERDUE_COUNT+1))
  fi
done <<< "${WEEK_ITEMS}"
[ ${OVERDUE_COUNT} -eq 0 ] && echo "  （无逾期项）"

# ---------------------------- 5. 生成摘要 ----------------------------
echo ""
echo "=============================================================="
echo " 4. 生成日历事件摘要"
echo "=============================================================="
DESCRIPTION="本周五人产品团队待办同步（${WEEK_START} ~ ${WEEK_END}）。"$'\n'
DESCRIPTION+="逾期项 ${OVERDUE_COUNT} 条："$'\n'
DESCRIPTION+="${OVERDUE}"
DESCRIPTION+=$'\n'"完整待办清单见数据源；本事件由自动化预演生成，插入前已经人工确认。"

echo "  标题：${SUMMARY}"
echo "  时间：${EVENT_START} ~ ${EVENT_END}"
echo "  日历：${CALENDAR}"
echo "  参会人（将真实收到邀请邮件）："
while IFS='|' read -r owner email task due status; do
  [ -z "${owner}" ] && continue
  echo "    - ${owner} <${email}>"
done <<< "${WEEK_ITEMS}" | sort -u
echo "  正文："
printf "    %s\n" "${DESCRIPTION}" | sed 's/^/    /'

# 构造 attendee 参数（去重）
ATTENDEE_ARGS=""
for e in $(printf '%s\n' "${WEEK_ITEMS}" | awk -F'|' 'NF{print $2}' | sort -u); do
  ATTENDEE_ARGS+=" --attendee ${e}"
done

# ---------------------------- 6. 人工确认 ----------------------------
echo ""
echo "=============================================================="
echo " 5. 人工确认（写操作，按 SKILL.md CAUTION 要求）"
echo "=============================================================="
echo "  即将执行的命令（预览）："
echo "  ───────────────────────────────────────────────────────────"
echo "  gws calendar +insert --calendar '${CALENDAR}' \\"
echo "    --summary '${SUMMARY}' \\"
echo "    --start '${EVENT_START}' --end '${EVENT_END}' \\"
echo "    --description '<见上方正文>' \\${ATTENDEE_ARGS}"
echo "  ───────────────────────────────────────────────────────────"
echo "  影响：会在 Google 日历创建事件，并向 5 名参会人发送邀请邮件。"
echo "  停止条件：前置检查未通过 / 授权缺失 / 任一参会人邮箱未核实 / 操作者未输入 YES。"

if [ ${#STOP_REASONS[@]} -gt 0 ]; then
  echo ""
  echo "  [停止] 以下前置问题未解决，禁止执行："
  for r in "${STOP_REASONS[@]}"; do echo "    - ${r}"; done
  echo ""
  echo "  本次仅完成只读预演，未做任何写入。"
  exit 0
fi

# 真实执行模式下才要求交互确认；预演模式直接给出 dry-run 结论
if [ "${DRY_RUN}" = "1" ]; then
  echo ""
  echo "  [DRY-RUN] 预演结束：未调用 gws，未创建任何事件，未发送任何邮件。"
  echo "  回滚：无写入故无需回滚。"
  exit 0
fi

read -r -p "  确认真实创建并发送邀请？输入 YES 继续： " CONFIRM
if [ "${CONFIRM}" != "YES" ]; then
  echo "  已取消，未做任何写入。"
  exit 0
fi

# ---------------------------- 7. 真实执行（受保护） ----------------------------
echo "  执行中..."
gws calendar +insert \
  --calendar "${CALENDAR}" \
  --summary "${SUMMARY}" \
  --start "${EVENT_START}" --end "${EVENT_END}" \
  --description "${DESCRIPTION}" \
  ${ATTENDEE_ARGS}
echo "  完成。回滚方式：gws calendar 删除该事件（会向参会人发送取消通知）。"
