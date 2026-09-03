#!/usr/bin/env bash
# agiled_preflight.sh — Agiled 自动化预检与编排脚本
# 依据 agiled-automation/SKILL.md：Rube MCP 必须可用且 agiled 连接 ACTIVE 才可执行。
# 本脚本只做预检、幂等状态管理与重试编排；真正的 MCP 工具调用由具备 Rube MCP 能力的 Agent 执行。
# 不创建/删除/覆盖任何外部资源。

set -euo pipefail

RUN_DIR="$(cd "$(dirname "$0")" && pwd)"
INPUT_DIR="$RUN_DIR/input"
STATE_DIR="$RUN_DIR/state"
LOG_DIR="$RUN_DIR/logs"
WORKFLOW_ID="${WORKFLOW_ID:-wf-$(date +%Y%m%d-%H%M%S)}"
STATE_FILE="$STATE_DIR/${WORKFLOW_ID}.jsonl"
LOG_FILE="$LOG_DIR/${WORKFLOW_ID}.log"
MAX_RETRIES=3
RETRY_DELAYS=(2 4 8)

mkdir -p "$INPUT_DIR" "$STATE_DIR" "$LOG_DIR"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"; }
pass() { log "[PASS] $*"; }
fail() { log "[FAIL] $*"; }

OVERALL_OK=1

# ---------- P0: Rube MCP 工具可用性 ----------
check_p0_mcp_tools() {
    log "=== P0: 检查 Rube MCP 工具可用性 ==="
    # Rube MCP 工具（RUBE_SEARCH_TOOLS 等）由 MCP 客户端注入，不在 shell PATH 中。
    # 检查常见 MCP 配置与环境变量作为间接证据。
    local mcp_configured=0
    if [ -n "${RUBE_MCP_URL:-}" ] || [ -n "${RUBE_SEARCH_TOOLS:-}" ]; then
        mcp_configured=1
    fi
    for cfg in "$HOME/.cursor/mcp.json" "$HOME/.claude/mcp.json" \
               "$HOME/.config/claude/mcp.json" "$HOME/.codex/mcp.json"; do
        if [ -f "$cfg" ] && grep -qi "rube" "$cfg" 2>/dev/null; then
            mcp_configured=1
            log "  发现含 rube 的 MCP 配置: $cfg"
        fi
    done
    if [ "$mcp_configured" -eq 1 ]; then
        pass "检测到 Rube MCP 配置迹象（仍需在 Agent 中确认 RUBE_SEARCH_TOOLS 可调用）"
    else
        fail "未检测到 Rube MCP 配置。SKILL.md 要求：添加 https://rube.app/mcp 为 MCP server"
        OVERALL_OK=0
    fi
}

# ---------- P3: 网络连通性 ----------
check_p3_network() {
    log "=== P3: 检查 rube.app 网络连通性 ==="
    # 只看 curl 退出码：DNS 失败/超时/连接拒绝均视为不可达
    if curl -sS -o /dev/null --max-time 10 "https://rube.app/mcp" 2>/dev/null; then
        pass "rube.app 可建立连接"
    else
        fail "rube.app 不可达（DNS/网络问题），无法建立 MCP 连接"
        OVERALL_OK=0
    fi
}

# ---------- P4: 输入数据校验 ----------
check_p4_input() {
    log "=== P4: 检查批处理输入数据 ==="
    local input_file="$INPUT_DIR/batch.jsonl"
    if [ ! -f "$input_file" ]; then
        log "  [INFO] 未找到 $input_file —— 无批处理数据，跳过数据校验（演示模式）"
        return 0
    fi
    local line_no=0
    local dup=0
    declare -A seen_keys
    while IFS= read -r line || [ -n "$line" ]; do
        line_no=$((line_no + 1))
        [ -z "$line" ] && continue
        if ! echo "$line" | python3 -c "import sys,json; json.loads(sys.stdin.read())" 2>/dev/null; then
            fail "输入第 $line_no 行不是合法 JSON"
            OVERALL_OK=0
            return
        fi
        local key
        key=$(echo "$line" | python3 -c "import sys,json; print(json.loads(sys.stdin.read()).get('idempotency_key',''))" 2>/dev/null || echo "")
        if [ -z "$key" ]; then
            fail "输入第 $line_no 行缺少 idempotency_key"
            OVERALL_OK=0
            return
        fi
        if [ -n "${seen_keys[$key]:-}" ]; then
            fail "幂等键重复: $key（第 $line_no 行）"
            dup=1
        fi
        seen_keys[$key]=1
    done < "$input_file"
    if [ "$dup" -eq 1 ]; then OVERALL_OK=0; return; fi
    pass "输入数据校验通过，共 $line_no 条记录"
}

# ---------- 幂等状态管理 ----------
is_already_success() {
    local key="$1"
    [ -f "$STATE_FILE" ] || return 1
    grep -q "\"idempotency_key\":\"$key\"" "$STATE_FILE" 2>/dev/null && \
    tail -n 20 "$STATE_FILE" | grep "\"idempotency_key\":\"$key\"" | grep -q '"status":"success"'
}

record_status() {
    local key="$1" status="$2" detail="${3:-}"
    python3 -c "
import json, sys
rec = {'ts': '$(date -u +%Y-%m-%dT%H:%M:%SZ)', 'workflow_id': '$WORKFLOW_ID',
       'idempotency_key': '$key', 'status': '$status', 'detail': '''$detail'''}
print(json.dumps(rec, ensure_ascii=False))
" >> "$STATE_FILE"
}

# ---------- 重试框架（仅函数定义，预检未通过时不执行） ----------
run_with_retry() {
    local key="$1"
    shift
    local attempt=0
    while [ "$attempt" -le "$MAX_RETRIES" ]; do
        if "$@"; then
            record_status "$key" "success"
            return 0
        fi
        local rc=$?
        if [ "$attempt" -lt "$MAX_RETRIES" ]; then
            local delay="${RETRY_DELAYS[$attempt]}"
            log "  重试 $((attempt+1))/$MAX_RETRIES，${delay}s 后重试 (key=$key)"
            sleep "$delay"
        fi
        attempt=$((attempt + 1))
    done
    record_status "$key" "failed" "exhausted retries"
    return 1
}

# ---------- 人工确认点 ----------
human_confirm() {
    local prompt="$1"
    log "[人工确认] $prompt"
    log "[人工确认] 请在 Agent 对话中确认后继续；脚本非交互模式下默认拒绝继续。"
    return 1
}

# ---------- 主流程 ----------
main() {
    log "Agiled 自动化预检开始 (workflow=$WORKFLOW_ID)"
    log "依据 SKILL.md: Rube MCP 必须可用 + agiled 连接 ACTIVE"
    log ""

    check_p0_mcp_tools
    check_p3_network
    check_p4_input

    log ""
    if [ "$OVERALL_OK" -ne 1 ]; then
        log "=============================="
        fail "预检未通过，安全中止。不执行任何 Agiled/MCP 调用。"
        log "待满足条件："
        log "  1) 在客户端添加 MCP server: https://rube.app/mcp"
        log "  2) 确认网络可访问 rube.app"
        log "  3) 在 Agent 中确认 RUBE_SEARCH_TOOLS 可调用"
        log "  4) 通过 RUBE_MANAGE_CONNECTIONS 完成 agiled 授权（状态 ACTIVE）"
        log "=============================="
        exit 1
    fi

    log "=============================="
    pass "预检通过。"
    log "后续应由具备 Rube MCP 能力的 Agent 按 SKILL.md 执行："
    log "  阶段1 RUBE_SEARCH_TOOLS（发现工具，新 session）"
    log "  阶段2 RUBE_MANAGE_CONNECTIONS（确认 agiled ACTIVE）"
    log "  阶段3 RUBE_MULTI_EXECUTE_TOOL（含 memory:{}，逐条+幂等+重试）"
    log "=============================="
}

main "$@"
