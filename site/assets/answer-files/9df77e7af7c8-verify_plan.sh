#!/usr/bin/env bash
# =============================================================================
# verify_plan.sh — 在线课程付费广告素材与落地页检查方案 本地验证脚本
# 零依赖：仅使用 bash/grep/awk/sed/curl/file 等系统自带工具
# 用法：bash verify_plan.sh [方案文档路径]
# 退出码：0=全部通过  1=存在失败项  2=参数/环境错误
# =============================================================================
set -euo pipefail

# ---------- 配置 ----------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLAN_FILE="${1:-$SCRIPT_DIR/广告素材与落地页检查方案.md}"
RUBE_MCP_URL="https://rube.app/mcp"
PASS=0; FAIL=0; WARN=0
RESULTS=""

# ---------- 工具函数 ----------
green() { printf '\033[32m%s\033[0m' "$1"; }
red()   { printf '\033[31m%s\033[0m' "$1"; }
yellow(){ printf '\033[33m%s\033[0m' "$1"; }

record() {
  local status="$1" check="$2" detail="$3"
  case "$status" in
    PASS) PASS=$((PASS+1)); RESULTS+="$(green "[PASS]") $check — $detail"$'\n' ;;
    FAIL) FAIL=$((FAIL+1)); RESULTS+="$(red   "[FAIL]") $check — $detail"$'\n' ;;
    WARN) WARN=$((WARN+1)); RESULTS+="$(yellow "[WARN]") $check — $detail"$'\n' ;;
  esac
}

check_cmd() {
  if command -v "$1" >/dev/null 2>&1; then
    record PASS "依赖检查: $1" "命令可用"
  else
    record FAIL "依赖检查: $1" "命令不存在"
  fi
}

# ---------- 前置检查 ----------
echo "========================================"
echo " 广告素材与落地页检查方案 — 本地验证"
echo "========================================"
echo "方案文件: $PLAN_FILE"
echo "验证时间: $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "主机信息: $(uname -srm)"
echo "----------------------------------------"

if [ ! -f "$PLAN_FILE" ]; then
  echo "$(red "[FAIL]") 方案文件不存在: $PLAN_FILE"
  exit 2
fi

# 1. 系统依赖检查（均为 macOS/Linux 自带工具）
echo ""
echo ">>> 1. 系统依赖检查（零新增依赖）"
for cmd in bash grep awk sed curl file date; do
  check_cmd "$cmd"
done

# ---------- 文档结构检查 ----------
echo ""
echo ">>> 2. 方案文档结构完整性"

# 2.1 五大必交付章节
SECTIONS=("目标受众" "信息主张" "素材规格" "转化路径" "可验证清单")
for sec in "${SECTIONS[@]}"; do
  if grep -q "$sec" "$PLAN_FILE"; then
    record PASS "章节存在: $sec" "已找到"
  else
    record FAIL "章节缺失: $sec" "文档中未找到「$sec」"
  fi
done

# 2.2 素材规格表关键字段
echo ""
echo ">>> 3. 素材规格表字段完整性"
SPEC_FIELDS=("尺寸" "格式" "大小" "文案占比")
for field in "${SPEC_FIELDS[@]}"; do
  if grep -q "$field" "$PLAN_FILE"; then
    record PASS "规格字段: $field" "已包含"
  else
    record FAIL "规格字段缺失: $field" "素材规格表应包含「$field」"
  fi
done

# 检查图片规格行数（至少覆盖 5 个平台/版位）
IMG_ROWS=$(awk '/3\.1 图片素材规格/,/3\.2 视频素材规格/' "$PLAN_FILE" | grep -c '^|' || true)
if [ "$IMG_ROWS" -ge 7 ]; then  # 表头+分隔+至少5行
  record PASS "图片规格覆盖" "表格行数=${IMG_ROWS}（含表头），覆盖≥5个版位"
else
  record FAIL "图片规格覆盖不足" "表格行数=${IMG_ROWS}，应≥7（表头+5版位）"
fi

# 检查视频规格行数
VID_ROWS=$(awk '/3\.2 视频素材规格/,/3\.3 文案规格/' "$PLAN_FILE" | grep -c '^|' || true)
if [ "$VID_ROWS" -ge 6 ]; then
  record PASS "视频规格覆盖" "表格行数=${VID_ROWS}（含表头），覆盖≥4个平台"
else
  record FAIL "视频规格覆盖不足" "表格行数=${VID_ROWS}，应≥6（表头+4平台）"
fi

# ---------- 合规词库检查 ----------
echo ""
echo ">>> 4. 合规词库覆盖检查"
COMPLIANCE_TERMS=("最" "第一" "国家级" "包过" "包就业" "保证薪资" "保过")
for term in "${COMPLIANCE_TERMS[@]}"; do
  if grep -q "$term" "$PLAN_FILE"; then
    record PASS "合规词收录: $term" "已在方案中列为禁用词"
  else
    record WARN "合规词未收录: $term" "建议在合规章节补充「$term」"
  fi
done

# ---------- 转化路径完整性 ----------
echo ""
echo ">>> 5. 转化路径节点完整性"
PATH_NODES=("广告曝光" "点击" "落地页" "CTA" "表单" "提交成功" "再营销")
for node in "${PATH_NODES[@]}"; do
  if grep -q "$node" "$PLAN_FILE"; then
    record PASS "路径节点: $node" "已包含"
  else
    record FAIL "路径节点缺失: $node" "转化路径应包含「$node」"
  fi
done

# UTM 参数检查
UTM_PARAMS=("utm_source" "utm_medium" "utm_campaign" "utm_content" "utm_term")
UTM_ALL_OK=true
for p in "${UTM_PARAMS[@]}"; do
  if ! grep -q "$p" "$PLAN_FILE"; then
    record FAIL "UTM 参数缺失: $p" "追踪配置应包含 $p"
    UTM_ALL_OK=false
  fi
done
if $UTM_ALL_OK; then
  record PASS "UTM 参数完整" "5 个 UTM 参数均已列出"
fi

# ---------- 检查项编号唯一性与连续性 ----------
echo ""
echo ">>> 6. 检查项编号唯一性与连续性"

check_series() {
  local prefix="$1" max="$2" label="$3"
  local missing="" dup=""
  # 仅提取清单表格行中的编号（以 | C- 等开头），排除其他章节的引用
  local ids
  ids=$(grep -E "^\| *${prefix}-[0-9]+" "$PLAN_FILE" | grep -oE "${prefix}-[0-9]+" | sort -u)
  local count
  count=$(echo "$ids" | grep -c . || true)

  # 检查连续性（零填充两位）
  for i in $(seq 1 "$max"); do
    local num
    num=$(printf "%s-%02d" "$prefix" "$i")
    if ! echo "$ids" | grep -q "^${num}$"; then
      missing="$missing $num"
    fi
  done

  # 检查重复（表格行中原始出现次数 vs 去重后）
  local raw_count
  raw_count=$(grep -E "^\| *${prefix}-[0-9]+" "$PLAN_FILE" | grep -oE "${prefix}-[0-9]+" | sort | wc -l | tr -d ' ')
  if [ "$raw_count" -gt "$count" ]; then
    dup="（存在重复编号）"
  fi

  if [ -z "$missing" ] && [ -z "$dup" ]; then
    record PASS "$label 编号" "共 ${count} 项，编号连续无重复"
  else
    [ -n "$missing" ] && record FAIL "$label 编号缺号" "缺失:$missing"
    [ -n "$dup" ] && record FAIL "$label 编号重复" "$dup"
  fi
}

check_series "C" 12 "素材检查(C系列)"
check_series "L" 12 "落地页检查(L系列)"
check_series "A" 6  "连通性检查(A系列)"

# ---------- Rube MCP 端点连通性（安全只读探测） ----------
echo ""
echo ">>> 7. Rube MCP 端点连通性（安全探测，不发送凭证）"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 8 "$RUBE_MCP_URL" 2>/dev/null || true)
HTTP_CODE="${HTTP_CODE:-000}"
if [ "$HTTP_CODE" = "000" ]; then
  record WARN "Rube MCP 可达性" "端点 ${RUBE_MCP_URL} 不可达（HTTP ${HTTP_CODE}），Skill 工具暂无法执行"
elif [ "$HTTP_CODE" -ge 200 ] && [ "$HTTP_CODE" -lt 400 ]; then
  record PASS "Rube MCP 可达性" "端点返回 HTTP $HTTP_CODE"
else
  record WARN "Rube MCP 可达性" "端点返回 HTTP $HTTP_CODE"
fi

# 检查环境中是否有 RUBE_ 工具（通过 MCP 配置或环境变量间接判断）
if env | grep -qi "rube\|composio" 2>/dev/null; then
  record PASS "Rube/Composio 环境变量" "检测到相关环境变量"
else
  record WARN "Rube/Composio 环境变量" "未检测到 RUBE_/COMPOSIO_ 环境变量，MCP 可能未配置"
fi

# ---------- Skill 映射检查 ----------
echo ""
echo ">>> 8. Skill 自动化映射一致性"
SKILL_ITEMS=("C-11" "C-12" "A-02" "A-03" "A-04" "A-05" "A-06")
for item in "${SKILL_ITEMS[@]}"; do
  if grep -q "$item" "$PLAN_FILE"; then
    record PASS "Skill 映射项: $item" "已在清单中标注"
  else
    record FAIL "Skill 映射项缺失: $item" "应在清单中包含 $item"
  fi
done

# 检查 SKILL.md 规定的关键流程是否在方案中体现
SKILL_RULES=("RUBE_SEARCH_TOOLS" "RUBE_MANAGE_CONNECTIONS" "RUBE_MULTI_EXECUTE_TOOL" "memory" "session" "pagination")
for rule in "${SKILL_RULES[@]}"; do
  if grep -qi "$rule" "$PLAN_FILE"; then
    record PASS "SKILL.md 规则体现: $rule" "已在方案中引用"
  else
    record FAIL "SKILL.md 规则未体现: $rule" "方案应遵循 SKILL.md 中的 $rule 要求"
  fi
done

# ---------- 幂等性检查 ----------
echo ""
echo ">>> 9. 脚本幂等性检查"
if [ "${VERIFY_IDEMPOTENCY_SKIP:-0}" = "1" ]; then
  record PASS "幂等性" "递归调用中跳过（防止无限递归）"
else
  RUN1=$(VERIFY_IDEMPOTENCY_SKIP=1 bash "$0" "$PLAN_FILE" 2>&1 | sed 's/\x1b\[[0-9;]*m//g' | grep -cE '\[(PASS|FAIL|WARN)\]' || true)
  RUN2=$(VERIFY_IDEMPOTENCY_SKIP=1 bash "$0" "$PLAN_FILE" 2>&1 | sed 's/\x1b\[[0-9;]*m//g' | grep -cE '\[(PASS|FAIL|WARN)\]' || true)
  if [ "$RUN1" -eq "$RUN2" ] && [ "$RUN1" -gt 0 ]; then
    record PASS "幂等性" "两次运行检查项数一致（${RUN1} 项）"
  else
    record FAIL "幂等性" "两次运行结果不一致（${RUN1} vs ${RUN2}）"
  fi
fi

# ---------- 输出结果 ----------
echo ""
echo "========================================"
echo " 验证结果汇总"
echo "========================================"
echo "$RESULTS"
echo "----------------------------------------"
TOTAL=$((PASS+FAIL+WARN))
echo "总计: $TOTAL 项 | $(green "通过: $PASS") | $(red "失败: $FAIL") | $(yellow "警告: $WARN")"
echo "========================================"

if [ "$FAIL" -gt 0 ]; then
  exit 1
else
  exit 0
fi
