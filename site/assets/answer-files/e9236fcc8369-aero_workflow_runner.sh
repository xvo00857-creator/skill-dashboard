#!/usr/bin/env bash
# =============================================================================
# aero_workflow_runner.sh
# Aero Workflow 自动化受约束执行器
#
# 严格遵循 aero-workflow-automation SKILL.md 的流程模式：
#   Step 1: RUBE_SEARCH_TOOLS   — 发现可用工具及 schema
#   Step 2: RUBE_MANAGE_CONNECTIONS — 检查 aero_workflow 连接状态
#   Step 3: RUBE_MULTI_EXECUTE_TOOL — 按发现的 schema 执行工具
#
# 约束特性：
#   - 预检（preflight）：运行前验证所有前提条件
#   - 幂等（idempotent）：状态文件记录进度，重复运行不重复执行
#   - 重试（retry）：网络操作指数退避重试，最多 3 次
#   - 人工确认（approval）：外部写操作前暂停等待确认
#   - 可恢复（recoverable）：中断后从上次成功步骤继续
#
# 重要：本脚本不包含 Rube MCP 工具的实际调用实现。
# SKILL.md 要求 RUBE_SEARCH_TOOLS / RUBE_MANAGE_CONNECTIONS /
# RUBE_MULTI_EXECUTE_TOOL 由已连接的 Rube MCP 服务器提供。
# 当前环境未连接 Rube MCP，脚本将在预检阶段如实报告并停止，
# 不会编造任何 Aero Workflow 操作结果。
# =============================================================================

set -euo pipefail

# ---------- 配置 ----------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE_DIR="${SCRIPT_DIR}/state"
LOG_DIR="${SCRIPT_DIR}/logs"
OUTPUT_DIR="${SCRIPT_DIR}/output"
STATE_FILE="${STATE_DIR}/workflow_state.json"
LOG_FILE="${LOG_DIR}/run_$(date +%Y%m%d_%H%M%S).log"
RUBE_MCP_ENDPOINT="https://rube.app/mcp"
TOOLKIT="aero_workflow"
MAX_RETRIES=3
RETRY_BASE_DELAY=2  # 秒

# ---------- 工具函数 ----------
log() {
    local level="$1"; shift
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] [${level}] $*"
    echo "$msg" | tee -a "$LOG_FILE"
}

info()  { log "INFO" "$@"; }
warn()  { log "WARN" "$@"; }
error() { log "ERROR" "$@"; }

# 指数退避重试
# 用法: retry <描述> <命令...>
retry() {
    local desc="$1"; shift
    local attempt=1
    local delay=$RETRY_BASE_DELAY
    while (( attempt <= MAX_RETRIES )); do
        info "尝试 ${desc}（第 ${attempt}/${MAX_RETRIES} 次）"
        if "$@"; then
            return 0
        fi
        if (( attempt == MAX_RETRIES )); then
            error "${desc} 在 ${MAX_RETRIES} 次尝试后仍然失败"
            return 1
        fi
        warn "${desc} 失败，${delay} 秒后重试..."
        sleep "$delay"
        delay=$(( delay * 2 ))
        (( attempt++ ))
    done
}

# 状态文件操作（幂等核心）
state_init() {
    if [[ ! -f "$STATE_FILE" ]]; then
        cat > "$STATE_FILE" <<'EOF'
{
  "session_id": null,
  "steps": {
    "preflight": "pending",
    "discover_tools": "pending",
    "check_connection": "pending",
    "execute": "pending"
  },
  "discovered_tools": [],
  "connection_status": null,
  "execution_results": []
}
EOF
        info "状态文件已初始化: ${STATE_FILE}"
    else
        info "发现已有状态文件，将以幂等模式继续"
    fi
}

state_get() {
    local key="$1"
    python3 -c "
import json, sys
with open('${STATE_FILE}') as f:
    data = json.load(f)
keys = '${key}'.split('.')
v = data
for k in keys:
    v = v[k]
if isinstance(v, (dict, list)):
    print(json.dumps(v, ensure_ascii=False))
elif v is None:
    print('')
else:
    print(v)
"
}

state_set() {
    local key="$1"
    local value="$2"
    python3 -c "
import json
with open('${STATE_FILE}') as f:
    data = json.load(f)
keys = '${key}'.split('.')
obj = data
for k in keys[:-1]:
    obj = obj[k]
obj[keys[-1]] = json.loads('${value}')
with open('${STATE_FILE}', 'w') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
"
}

step_status() {
    state_get "steps.$1"
}

mark_step() {
    local step="$1"
    local status="$2"
    state_set "steps.${step}" "\"${status}\""
    info "步骤 [${step}] 状态 → ${status}"
}

# 人工确认点
human_confirm() {
    local prompt="$1"
    echo ""
    echo "============================================"
    echo "  人工确认点"
    echo "  ${prompt}"
    echo "============================================"
    echo "请输入 YES 继续，其他任意输入中止："
    read -r answer
    if [[ "$answer" != "YES" ]]; then
        warn "用户未确认，操作中止"
        return 1
    fi
    info "用户已确认，继续执行"
}

# ---------- 预检 ----------
preflight() {
    info "========== 预检开始 =========="
    local ok=true

    # 检查 1: Rube MCP 端点网络可达性
    info "检查 Rube MCP 端点: ${RUBE_MCP_ENDPOINT}"
    local http_code
    http_code=$(curl -sS -o /dev/null -w "%{http_code}" --max-time 10 \
        "${RUBE_MCP_ENDPOINT}" 2>/dev/null) || true
    if [[ "$http_code" == "000" ]] || [[ -z "$http_code" ]]; then
        error "Rube MCP 端点不可达（DNS 解析失败或网络不通）"
        error "SKILL.md 要求: Rube MCP must be connected (RUBE_SEARCH_TOOLS available)"
        ok=false
    else
        info "Rube MCP 端点可达，HTTP 状态码: ${http_code}"
    fi

    # 检查 2: 必要工具是否在当前环境中可用
    # SKILL.md 要求通过 MCP 提供以下工具，这里检查是否有对应 CLI 或配置
    local required_tools=("RUBE_SEARCH_TOOLS" "RUBE_MANAGE_CONNECTIONS" "RUBE_MULTI_EXECUTE_TOOL")
    for tool in "${required_tools[@]}"; do
        if command -v "$tool" &>/dev/null; then
            info "工具 ${tool} 可用"
        else
            error "工具 ${tool} 不可用 — 该工具应由已连接的 Rube MCP 提供"
            ok=false
        fi
    done

    # 检查 3: MCP 配置是否存在
    if [[ -f "$HOME/.config/mcp/config.json" ]] || [[ -f "$HOME/.mcp.json" ]]; then
        info "发现 MCP 配置文件"
    else
        warn "未发现 MCP 客户端配置文件"
        warn "SKILL.md Setup 指示: Add ${RUBE_MCP_ENDPOINT} as an MCP server in your client configuration"
        ok=false
    fi

    # 检查 4: 工作目录可写
    if [[ -w "$STATE_DIR" ]] && [[ -w "$LOG_DIR" ]]; then
        info "工作目录可写"
    else
        error "工作目录不可写"
        ok=false
    fi

    if $ok; then
        mark_step "preflight" "completed"
        info "========== 预检通过 =========="
        return 0
    else
        mark_step "preflight" "failed"
        error "========== 预检未通过 =========="
        error "根据 SKILL.md 的前提条件，以下条件必须满足才能继续："
        error "  1. Rube MCP 已连接（RUBE_SEARCH_TOOLS 可用）"
        error "  2. aero_workflow toolkit 连接状态为 ACTIVE"
        error "  3. 已将 ${RUBE_MCP_ENDPOINT} 添加为 MCP 服务器"
        error ""
        error "当前环境不满足上述条件，流程在此停止。"
        error "不会编造任何 Aero Workflow 操作结果。"
        return 1
    fi
}

# ---------- Step 1: 发现工具 ----------
# SKILL.md: Always call RUBE_SEARCH_TOOLS first to get current tool schemas
discover_tools() {
    local status
    status=$(step_status "discover_tools")
    if [[ "$status" == "completed" ]]; then
        info "步骤 [discover_tools] 已完成，跳过（幂等）"
        return 0
    fi

    info "========== Step 1: 发现 Aero Workflow 工具 =========="
    info "按 SKILL.md 要求调用 RUBE_SEARCH_TOOLS"
    info "  use_case: 'Aero Workflow operations'"
    info "  session: {generate_id: true}"

    # 注意：以下调用需要 Rube MCP 连接。
    # 在预检通过且 MCP 可用的环境中，此处应调用：
    #   RUBE_SEARCH_TOOLS(
    #     queries=[{use_case: "Aero Workflow operations", known_fields: ""}],
    #     session={generate_id: true}
    #   )
    # 返回值包含 tool_slugs、input_schemas、recommended_execution_plan、known_pitfalls。
    #
    # 当前环境预检未通过，不会到达此处。
    # 如果到达此处但工具仍不可用，如实报错：
    if ! command -v RUBE_SEARCH_TOOLS &>/dev/null; then
        error "RUBE_SEARCH_TOOLS 不可用，无法发现工具"
        mark_step "discover_tools" "failed"
        return 1
    fi

    # --- 以下为 Rube MCP 可用时的执行框架（当前环境不会执行到） ---
    # local search_result
    # search_result=$(RUBE_SEARCH_TOOLS \
    #     --queries '[{"use_case":"Aero Workflow operations","known_fields":""}]' \
    #     --session '{"generate_id":true}')
    # local session_id
    # session_id=$(echo "$search_result" | python3 -c "import sys,json;print(json.load(sys.stdin)['session_id'])")
    # state_set "session_id" "\"${session_id}\""
    # local tools_json
    # tools_json=$(echo "$search_result" | python3 -c "import sys,json;print(json.dumps(json.load(sys.stdin).get('tools',[])))")
    # state_set "discovered_tools" "'${tools_json}'"
    # mark_step "discover_tools" "completed"
    # info "发现 $(echo "$tools_json" | python3 -c "import sys,json;print(len(json.load(sys.stdin)))") 个工具"
}

# ---------- Step 2: 检查连接 ----------
# SKILL.md: Verify RUBE_MANAGE_CONNECTIONS shows ACTIVE status before executing tools
check_connection() {
    local status
    status=$(step_status "check_connection")
    if [[ "$status" == "completed" ]]; then
        info "步骤 [check_connection] 已完成，跳过（幂等）"
        return 0
    fi

    info "========== Step 2: 检查 aero_workflow 连接 =========="
    local session_id
    session_id=$(state_get "session_id")
    info "调用 RUBE_MANAGE_CONNECTIONS，toolkit: ${TOOLKIT}, session_id: ${session_id}"

    if ! command -v RUBE_MANAGE_CONNECTIONS &>/dev/null; then
        error "RUBE_MANAGE_CONNECTIONS 不可用"
        mark_step "check_connection" "failed"
        return 1
    fi

    # --- Rube MCP 可用时的执行框架 ---
    # local conn_result
    # conn_result=$(RUBE_MANAGE_CONNECTIONS \
    #     --toolkits '["aero_workflow"]' \
    #     --session_id "$session_id")
    # local conn_status
    # conn_status=$(echo "$conn_result" | python3 -c "import sys,json;print(json.load(sys.stdin)['status'])")
    # state_set "connection_status" "\"${conn_status}\""
    # if [[ "$conn_status" != "ACTIVE" ]]; then
    #     local auth_link
    #     auth_link=$(echo "$conn_result" | python3 -c "import sys,json;print(json.load(sys.stdin).get('auth_link',''))")
    #     error "aero_workflow 连接状态为 ${conn_status}，需要完成授权"
    #     error "授权链接: ${auth_link}"
    #     mark_step "check_connection" "auth_required"
    #     return 1
    # fi
    # mark_step "check_connection" "completed"
    # info "aero_workflow 连接状态: ACTIVE"
}

# ---------- Step 3: 执行工具 ----------
# SKILL.md: RUBE_MULTI_EXECUTE_TOOL with discovered tool slugs, include memory even if empty
execute_tools() {
    local status
    status=$(step_status "execute")
    if [[ "$status" == "completed" ]]; then
        info "步骤 [execute] 已完成，跳过（幂等）"
        return 0
    fi

    info "========== Step 3: 执行 Aero Workflow 工具 =========="

    # 人工确认点：执行外部操作前必须确认
    if ! human_confirm "即将通过 RUBE_MULTI_EXECUTE_TOOL 执行 Aero Workflow 操作，可能影响外部资源。"; then
        mark_step "execute" "aborted"
        return 1
    fi

    if ! command -v RUBE_MULTI_EXECUTE_TOOL &>/dev/null; then
        error "RUBE_MULTI_EXECUTE_TOOL 不可用"
        mark_step "execute" "failed"
        return 1
    fi

    # --- Rube MCP 可用时的执行框架 ---
    # SKILL.md 已知陷阱：
    #   - memory 参数必须包含，即使为空对象 {}
    #   - 使用从 search 结果中获得的确切字段名和类型
    #   - 复用 session ID
    #   - 检查分页 token 并继续获取直到完成
    #
    # local session_id
    # session_id=$(state_get "session_id")
    # local tools
    # tools=$(state_get "discovered_tools")
    # RUBE_MULTI_EXECUTE_TOOL \
    #     --tools "$tools" \
    #     --memory '{}' \
    #     --session_id "$session_id"
    # mark_step "execute" "completed"
}

# ---------- 主流程 ----------
main() {
    mkdir -p "$STATE_DIR" "$LOG_DIR" "$OUTPUT_DIR"
    info "Aero Workflow 自动化执行器启动"
    info "日志文件: ${LOG_FILE}"

    state_init

    # 预检（含重试：网络检查可能瞬时失败）
    if ! retry "预检" preflight; then
        error "流程因预检未通过而停止"
        info "解决方法：在 MCP 客户端配置中添加 ${RUBE_MCP_ENDPOINT}，完成 aero_workflow 授权后重新运行"
        exit 1
    fi

    # Step 1
    if ! discover_tools; then
        error "Step 1 失败，流程停止。修复后重新运行可从此步骤继续（幂等）"
        exit 1
    fi

    # Step 2
    if ! check_connection; then
        error "Step 2 失败，流程停止。如需要授权，请访问返回的授权链接后重新运行"
        exit 1
    fi

    # Step 3
    if ! execute_tools; then
        error "Step 3 失败或被中止，流程停止"
        exit 1
    fi

    info "========== 流程全部完成 =========="
    info "状态文件: ${STATE_FILE}"
    info "输出目录: ${OUTPUT_DIR}"
}

main "$@"
