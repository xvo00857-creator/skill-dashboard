#!/usr/bin/env bash
# aeroleads-preflight.sh
# Aeroleads Automation via Rube MCP —— 预检脚本
# 依据 SKILL.md 的 Prerequisites / Setup / Known Pitfalls 设计
# 只读检查，不创建、删除或修改任何外部资源
set -u

TS="$(date '+%Y-%m-%d %H:%M:%S %Z')"
PASS=0; WARN=0; FAIL=0; BLOCK=0

log() { printf '[%s] [%s] %s\n' "$TS" "$1" "$2"; }
section() { printf '\n==== %s ====\n' "$1"; }

section "1. Rube MCP 端点可达性 (SKILL.md: Get Rube MCP -> https://rube.app/mcp)"
HTTP_CODE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 8 https://rube.app/mcp 2>/dev/null)
if [ -z "$HTTP_CODE" ] || [ "$HTTP_CODE" = "000" ]; then
  log FAIL "无法连接 https://rube.app/mcp （网络不可达或超时）"
  FAIL=$((FAIL+1))
else
  log INFO "端点返回 HTTP $HTTP_CODE （MCP 端点通常需 POST 协商，HTTP 码仅供参考）"
  PASS=$((PASS+1))
fi

section "2. 本地 Rube / Composio 可执行文件与配置"
if command -v rube >/dev/null 2>&1; then
  log PASS "rube CLI 存在: $(command -v rube)"; PASS=$((PASS+1))
else
  log WARN "未找到 rube CLI"; WARN=$((WARN+1))
fi
if [ -d "$HOME/.rube" ]; then
  log PASS "存在 ~/.rube 配置目录"; PASS=$((PASS+1))
else
  log WARN "不存在 ~/.rube 配置目录"; WARN=$((WARN+1))
fi
if env | grep -qiE 'rube|composio|aeroleads'; then
  log PASS "发现相关环境变量"; PASS=$((PASS+1))
else
  log WARN "未发现 RUBE/COMPOSIO/AEROLEADS 相关环境变量"; WARN=$((WARN+1))
fi

section "3. RUBE_SEARCH_TOOLS 可用性 (SKILL.md: Always call RUBE_SEARCH_TOOLS first)"
# 当前会话的工具清单中不存在 RUBE_* 工具；以下通过环境探测侧面确认
if command -v rube >/dev/null 2>&1; then
  log INFO "rube CLI 存在，可尝试 'rube search-tools' （本次不执行写操作）"
else
  log BLOCK "RUBE_SEARCH_TOOLS 不可用：当前 Agent 工具清单中无 RUBE_* 工具，且无 rube CLI"
  BLOCK=$((BLOCK+1))
fi

section "4. Aeroleads 连接状态 (SKILL.md: RUBE_MANAGE_CONNECTIONS with toolkit aeroleads)"
log BLOCK "无法检查：RUBE_MANAGE_CONNECTIONS 依赖 Rube MCP，前置项未通过，按 SKILL.md 不得执行后续工作流"
BLOCK=$((BLOCK+1))

section "5. 工具 Schema 发现 (SKILL.md: Never hardcode tool slugs without RUBE_SEARCH_TOOLS)"
log BLOCK "无法执行：RUBE_SEARCH_TOOLS 不可用，不能硬编码 tool slug 或参数"
BLOCK=$((BLOCK+1))

section "6. 业务数据就绪情况"
if [ -f "./leads.csv" ] || [ -f "./prospects.csv" ] || [ -f "./leads.json" ]; then
  log PASS "发现本地线索数据文件"; PASS=$((PASS+1))
else
  log WARN "未发现本地线索数据文件（leads.csv/prospects.csv/leads.json），无输入数据可处理"
  WARN=$((WARN+1))
fi

section "预检汇总"
printf 'PASS=%d  WARN=%d  FAIL=%d  BLOCK=%d\n' "$PASS" "$WARN" "$FAIL" "$BLOCK"
if [ "$BLOCK" -gt 0 ] || [ "$FAIL" -gt 0 ]; then
  echo "结论：预检未通过。按 SKILL.md 要求，Rube MCP 不可用时不得执行任何 Aeroleads 工作流。"
  echo "待人工处理：(1) 在客户端配置 MCP server https://rube.app/mcp；(2) 通过 RUBE_MANAGE_CONNECTIONS 完成 Aeroleads 授权；(3) 提供线索输入数据。"
  exit 2
else
  echo "结论：预检通过，可进入工具发现与执行阶段。"
  exit 0
fi
