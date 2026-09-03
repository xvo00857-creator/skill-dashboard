#!/usr/bin/env bash
# =============================================================================
# cloud-logging-configuration-basics — 受约束的单项目 Cloud Logging 配置流程
#
# 本脚本严格遵循 SKILL.md 的能力边界与安全分层：
#   - 仅支持单项目 Google Cloud Logging 配置（不支持跨项目/多项目）
#   - Tier R（只读）：直接执行
#   - Tier M（非计费变更）：直接执行
#   - Tier B（计费/安全敏感变更）：展示确切命令并等待用户确认后才执行
#   - Tier D（不可逆数据丢失）：要求用户输入指定确认文本后才执行
#   - 不运行网络发现命令（沙箱网络限制），所有 project_id/region 等由调用方显式传入
#   - 包含预检、幂等检查、指数退避重试
#
# 用法：
#   PROJECT_ID=my-proj REGION=us-central1 BUCKET_ID=compliance-bucket \
#   RETENTION_DAYS=365 SINK_ID=to-compliance \
#   SENSITIVE_LOG_ID=externalaudit.googleapis.com/data_access \
#   SECURITY_GROUP_EMAIL=security-team@example.com \
#   METRIC_NAME=oom_error_count \
#   bash cloud_logging_configure.sh [plan|apply]
#
#   plan  — 仅预检并打印将要执行的操作（默认），不执行任何变更
#   apply — 执行变更（Tier B/D 仍会逐个人工确认）
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# 0. 全局配置
# ---------------------------------------------------------------------------
MODE="${1:-plan}"
MAX_RETRIES="${MAX_RETRIES:-3}"
RETRY_BASE_DELAY="${RETRY_BASE_DELAY:-2}"   # 秒，指数退避基数
CONFIRM_TIMEOUT=300  # 人工确认等待秒数

# 颜色输出（仅用于提示，不影响逻辑）
RED='\033[0;31m'; YELLOW='\033[1;33m'; GREEN='\033[0;32m'; NC='\033[0m'
info()  { printf "${GREEN}[INFO]${NC} %s\n" "$*"; }
warn()  { printf "${YELLOW}[WARN]${NC} %s\n" "$*"; }
err()   { printf "${RED}[ERROR]${NC} %s\n" "$*" >&2; }

# ---------------------------------------------------------------------------
# 1. 预检（Pre-flight Checks）
# ---------------------------------------------------------------------------
preflight() {
  info "===== 预检开始 ====="
  local fail=0

  # 1.1 gcloud 可执行文件
  if ! command -v gcloud >/dev/null 2>&1; then
    err "未找到 gcloud 可执行文件。请安装 Google Cloud CLI："
    err "  https://docs.cloud.google.com/sdk/docs/install-sdk.md.txt"
    fail=1
  else
    info "gcloud 已安装：$(gcloud version 2>/dev/null | head -1)"
  fi

  # 1.2 必要变量
  local required=(PROJECT_ID)
  for v in "${required[@]}"; do
    if [[ -z "${!v:-}" ]]; then
      err "缺少必要环境变量：$v"
      fail=1
    fi
  done
  info "PROJECT_ID=${PROJECT_ID:-(未设置)}"
  info "REGION=${REGION:-(未设置，创建区域桶时必填)}"
  info "BUCKET_ID=${BUCKET_ID:-(未设置)}"
  info "SINK_ID=${SINK_ID:-(未设置)}"
  info "SENSITIVE_LOG_ID=${SENSITIVE_LOG_ID:-(未设置)}"
  info "SECURITY_GROUP_EMAIL=${SECURITY_GROUP_EMAIL:-(未设置)}"
  info "METRIC_NAME=${METRIC_NAME:-(未设置)}"

  # 1.3 沙箱网络限制提示（SKILL.md 明确禁止运行发现命令）
  warn "按 SKILL.md 沙箱限制：不运行 gcloud projects list / organizations list 等发现命令。"
  warn "假设 PROJECT_ID=${PROJECT_ID:-<placeholder>} 对应项目存在，直接使用传入值。"

  # 1.4 执行模式
  if [[ "$MODE" == "plan" ]]; then
    info "当前为 plan 模式：仅展示计划，不执行任何变更命令。"
  elif [[ "$MODE" == "apply" ]]; then
    info "当前为 apply 模式：将执行变更；Tier B/D 操作仍需逐个人工确认。"
  else
    err "未知模式：${MODE}（请使用 plan 或 apply）"
    fail=1
  fi

  if [[ $fail -ne 0 ]]; then
    err "预检未通过，请修正上述问题后重试。"
    return 1
  fi
  info "===== 预检通过 ====="
}

# ---------------------------------------------------------------------------
# 2. 重试封装（指数退避，仅对瞬时错误重试）
# ---------------------------------------------------------------------------
# 用法：retry <描述> <命令...>
retry() {
  local desc="$1"; shift
  local attempt=1 delay rc
  while true; do
    info "[$desc] 第 $attempt 次执行：$*"
    rc=0
    "$@" || rc=$?
    if (( rc == 0 )); then
      info "[$desc] 执行成功。"
      return 0
    fi
    # gcloud 瞬时错误通常表现为非零退出；这里对所有失败做有限重试，
    # 真实环境可根据 stderr 匹配 HTTP 429/500/503/unavailable 精确判断。
    if (( attempt >= MAX_RETRIES )); then
      err "[$desc] 已达最大重试次数 ${MAX_RETRIES}，放弃。最后退出码：${rc}"
      return $rc
    fi
    delay=$(( RETRY_BASE_DELAY ** attempt ))
    warn "[$desc] 执行失败（退出码 ${rc}），${delay}s 后重试..."
    sleep "$delay"
    ((attempt++))
  done
}

# ---------------------------------------------------------------------------
# 3. 人工确认点
# ---------------------------------------------------------------------------
# Tier B：展示确切命令，用户输入 yes 确认
confirm_tier_b() {
  local desc="$1"; shift
  echo "----------------------------------------------------------------"
  warn "[Tier B — 计费/安全敏感变更] $desc"
  echo "即将执行的确切命令："
  printf '  '; printf '%q ' "$@"; echo
  echo "----------------------------------------------------------------"
  if [[ "$MODE" != "apply" ]]; then
    info "[plan] 跳过执行（apply 模式下将在此等待确认）。"
    return 1
  fi
  local ans
  read -r -p "确认执行？输入 yes 继续，其他任意键取消: " -t "$CONFIRM_TIMEOUT" ans || {
    err "确认超时，已取消。"; return 1; }
  [[ "$ans" == "yes" ]] || { err "用户取消。"; return 1; }
}

# Tier D：要求用户输入指定确认文本
confirm_tier_d() {
  local required_text="$1"; shift
  local desc="$1"; shift
  echo "----------------------------------------------------------------"
  printf "${RED}[Tier D — 不可逆数据丢失]${NC} %s\n" "$desc"
  echo "即将执行的确切命令："
  printf '  '; printf '%q ' "$@"; echo
  echo "----------------------------------------------------------------"
  if [[ "$MODE" != "apply" ]]; then
    info "[plan] 跳过执行（apply 模式下将在此等待明确文本确认）。"
    return 1
  fi
  local ans
  read -r -p "请精确输入「${required_text}」以确认，其他输入取消: " -t "$CONFIRM_TIMEOUT" ans || {
    err "确认超时，已取消。"; return 1; }
  [[ "$ans" == "$required_text" ]] || { err "确认文本不匹配，已取消。"; return 1; }
}

# ---------------------------------------------------------------------------
# 4. 幂等辅助：资源是否已存在
# ---------------------------------------------------------------------------
bucket_exists() {
  gcloud logging buckets describe "$BUCKET_ID" \
    --location="$REGION" --project="$PROJECT_ID" >/dev/null 2>&1
}
view_exists() {
  local view_id="$1" bucket="${2:-_Default}" location="${3:-global}"
  gcloud logging views describe "$view_id" \
    --bucket="$bucket" --location="$location" --project="$PROJECT_ID" >/dev/null 2>&1
}
sink_exists() {
  gcloud logging sinks describe "$1" --project="$PROJECT_ID" >/dev/null 2>&1
}
metric_exists() {
  gcloud logging metrics describe "$1" --project="$PROJECT_ID" >/dev/null 2>&1
}

# ---------------------------------------------------------------------------
# 5. 配置步骤
# ---------------------------------------------------------------------------

# 5.1 创建区域日志桶（Tier M，非计费变更）
#     注意：桶本身不计费，直到有 sink 路由日志进来才产生存储费用。
step_create_bucket() {
  [[ -n "${BUCKET_ID:-}" && -n "${REGION:-}" && -n "${RETENTION_DAYS:-}" ]] || {
    warn "跳过创建日志桶：BUCKET_ID/REGION/RETENTION_DAYS 未全部提供。"; return 0; }
  info "--- 步骤 1：创建区域日志桶（Tier M）---"
  # Observability Analytics 强制降级警告（SKILL.md 要求）
  warn "升级到 Observability Analytics 后无法降级移除分析能力（不可降级）。"
  if [[ "$MODE" == "apply" ]] && bucket_exists; then
    info "桶 $BUCKET_ID 已存在，跳过创建（幂等）。"
    return 0
  fi
  local cmd=(gcloud logging buckets create "$BUCKET_ID"
    --project="$PROJECT_ID" --location="$REGION"
    --retention-days="$RETENTION_DAYS" --enable-analytics)
  if [[ "$MODE" == "plan" ]]; then
    info "[plan] 将执行：${cmd[*]}"
    return 0
  fi
  retry "create-bucket" "${cmd[@]}"
}

# 5.2 验证日志桶（Tier R）
step_verify_bucket() {
  [[ -n "${BUCKET_ID:-}" && -n "${REGION:-}" ]] || return 0
  info "--- 步骤 2：验证日志桶配置（Tier R）---"
  local cmd=(gcloud logging buckets describe "$BUCKET_ID"
    --location="$REGION" --project="$PROJECT_ID")
  if [[ "$MODE" == "plan" ]]; then
    info "[plan] 将执行：${cmd[*]}"; return 0
  fi
  retry "describe-bucket" "${cmd[@]}" || warn "桶验证未通过（可能尚未创建或传播延迟），请人工检查。"
}

# 5.3 创建日志接收器路由日志到桶（Tier B — 计费）
step_create_sink() {
  [[ -n "${SINK_ID:-}" && -n "${BUCKET_ID:-}" && -n "${REGION:-}" ]] || {
    warn "跳过创建 sink：SINK_ID/BUCKET_ID/REGION 未全部提供。"; return 0; }
  info "--- 步骤 3：创建日志接收器（Tier B — 路由日志将产生持续存储费用）---"
  local filter="${SINK_FILTER:-severity>=DEFAULT}"
  local destination="projects/${PROJECT_ID}/locations/${REGION}/buckets/${BUCKET_ID}"
  local cmd=(gcloud logging sinks create "$SINK_ID" "$destination"
    --log-filter="$filter" --project="$PROJECT_ID")
  if [[ "$MODE" == "apply" ]] && sink_exists "$SINK_ID"; then
    info "sink $SINK_ID 已存在，跳过创建（幂等）。如需修改过滤器请显式 update。"
    return 0
  fi
  confirm_tier_b "创建 sink 将使日志路由到自定义桶并产生存储费用" "${cmd[@]}" || return 0
  retry "create-sink" "${cmd[@]}"
}

# 5.4 从默认视图排除敏感日志（Tier M — 非破坏性，仅隐藏不删除）
#     SKILL.md 模糊性规则：用户说"排除/隐藏/移除"但未明确"停止存储"时，
#     必须默认走此步骤（视图过滤），而非存储排除。
step_restrict_default_view() {
  [[ -n "${SENSITIVE_LOG_ID:-}" ]] || {
    warn "跳过默认视图限制：SENSITIVE_LOG_ID 未提供。"; return 0; }
  info "--- 步骤 4：从 _Default 视图排除敏感日志（Tier M，仅隐藏不删除）---"
  local filter="NOT LOG_ID(\"cloudaudit.googleapis.com/data_access\") AND NOT LOG_ID(\"externalaudit.googleapis.com/data_access\") AND NOT LOG_ID(\"${SENSITIVE_LOG_ID}\")"
  local cmd=(gcloud logging views update _Default
    --bucket=_Default --location=global --project="$PROJECT_ID"
    --log-filter="$filter")
  if [[ "$MODE" == "plan" ]]; then
    info "[plan] 将执行：${cmd[*]}"; return 0
  fi
  retry "update-default-view" "${cmd[@]}"
}

# 5.5 创建包含敏感日志的受限视图（Tier M）
step_create_security_view() {
  [[ -n "${SENSITIVE_LOG_ID:-}" ]] || return 0
  info "--- 步骤 5：创建安全日志视图 security-logs-view（Tier M）---"
  local cmd=(gcloud logging views create security-logs-view
    --bucket=_Default --location=global --project="$PROJECT_ID"
    --log-filter="LOG_ID(\"${SENSITIVE_LOG_ID}\")"
    --description="Sensitive logs")
  if [[ "$MODE" == "apply" ]] && view_exists "security-logs-view"; then
    info "视图 security-logs-view 已存在，跳过创建（幂等）。"
    return 0
  fi
  if [[ "$MODE" == "plan" ]]; then
    info "[plan] 将执行：${cmd[*]}"; return 0
  fi
  retry "create-security-view" "${cmd[@]}"
}

# 5.6 通过 IAM 条件授予视图访问权限（Tier B — 安全敏感）
step_grant_view_access() {
  [[ -n "${SECURITY_GROUP_EMAIL:-}" ]] || {
    warn "跳过 IAM 授权：SECURITY_GROUP_EMAIL 未提供。"; return 0; }
  info "--- 步骤 6：授予 security-logs-view 访问权限（Tier B — 修改 IAM 策略）---"
  local cmd=(gcloud projects add-iam-policy-binding "$PROJECT_ID"
    --member="group:${SECURITY_GROUP_EMAIL}"
    --role="roles/logging.viewAccessor"
    --condition="expression=resource.name=='projects/${PROJECT_ID}/locations/global/buckets/_Default/views/security-logs-view',title=Restricted to Specific Log View,description=Only allows access to the specified log view")
  confirm_tier_b "授予 IAM 视图访问权限会改变访问控制策略" "${cmd[@]}" || return 0
  retry "grant-view-access" "${cmd[@]}"
}

# 5.7 创建基于日志的计数指标（Tier B — 计费）
step_create_metric() {
  [[ -n "${METRIC_NAME:-}" ]] || {
    warn "跳过指标创建：METRIC_NAME 未提供。"; return 0; }
  info "--- 步骤 7：创建基于日志的计数指标（Tier B — 按数据点计费）---"
  local filter="${METRIC_FILTER:-textPayload:\"OutOfMemory\"}"
  local desc="${METRIC_DESC:-Count of log entries about OOMs}"
  local cmd=(gcloud logging metrics create "$METRIC_NAME"
    --log-filter="$filter" --description="$desc" --project="$PROJECT_ID")
  if [[ "$MODE" == "apply" ]] && metric_exists "$METRIC_NAME"; then
    info "指标 $METRIC_NAME 已存在，跳过创建（幂等）。"
    return 0
  fi
  confirm_tier_b "创建日志指标会按数据点产生持续费用" "${cmd[@]}" || return 0
  retry "create-metric" "${cmd[@]}"
}

# 5.8 验证指标（Tier R）
step_verify_metric() {
  [[ -n "${METRIC_NAME:-}" ]] || return 0
  info "--- 步骤 8：验证日志指标（Tier R）---"
  local cmd=(gcloud logging metrics describe "$METRIC_NAME" --project="$PROJECT_ID")
  if [[ "$MODE" == "plan" ]]; then
    info "[plan] 将执行：${cmd[*]}"; return 0
  fi
  retry "describe-metric" "${cmd[@]}" || warn "指标验证未通过（可能尚未创建或被跳过），请人工检查。"
}

# 5.9 验证敏感日志限制（Tier R）
step_verify_views() {
  info "--- 步骤 9：验证视图配置（Tier R）---"
  local cmd=(gcloud logging views describe security-logs-view
    --bucket=_Default --location=global --project="$PROJECT_ID")
  if [[ "$MODE" == "plan" ]]; then
    info "[plan] 将执行：${cmd[*]}"; return 0
  fi
  retry "describe-view" "${cmd[@]}" || warn "视图验证未通过（可能尚未创建或被跳过），请人工检查。"
}

# 5.10 （可选，Tier D）从存储中丢弃敏感日志 — 默认不执行
#       仅当用户明确要求"停止存储/永久丢弃/sink exclusion"时才启用。
#       此处保留为独立函数，需显式设置 ALLOW_DESTRUCTIVE=1 才会进入确认。
step_discard_from_storage() {
  [[ -n "${SENSITIVE_LOG_ID:-}" ]] || return 0
  [[ "${ALLOW_DESTRUCTIVE:-0}" == "1" ]] || {
    info "--- 步骤 10（跳过）：存储级排除为 Tier D 破坏性操作，"
    info "    需显式设置 ALLOW_DESTRUCTIVE=1 且用户明确要求停止存储才执行。---"
    return 0; }
  info "--- 步骤 10：从存储中排除敏感日志（Tier D — 立即且不可逆删除）---"
  local cmd=(gcloud logging sinks update _Default --project="$PROJECT_ID"
    --add-exclusion="name=exclude-sensitive,filter=LOG_ID(\"${SENSITIVE_LOG_ID}\")")
  local confirm_text="I confirm I want to exclude ${SENSITIVE_LOG_ID} logs from storage"
  confirm_tier_d "$confirm_text" "永久排除敏感日志，不可恢复" "${cmd[@]}" || return 0
  retry "add-exclusion" "${cmd[@]}"
}

# ---------------------------------------------------------------------------
# 6. 故障排查辅助（Tier R，只读）
# ---------------------------------------------------------------------------
troubleshoot_readonly() {
  info "===== 只读故障排查命令（Tier R，可直接执行）====="
  cat <<EOF
  # 列出日志桶
  gcloud logging buckets list --project=$PROJECT_ID
  # 列出接收器及排除项
  gcloud logging sinks list --project=$PROJECT_ID
  gcloud logging sinks describe _Default --project=$PROJECT_ID
  # 列出视图
  gcloud logging views list --bucket=_Default --location=global --project=$PROJECT_ID
  # 列出指标
  gcloud logging metrics list --project=$PROJECT_ID
  # 读取最近日志（按过滤器）
  gcloud logging read 'severity>=ERROR' --project=$PROJECT_ID --limit=20
EOF
  info "注意：在沙箱/受限网络环境中上述命令可能无法连通 Google Cloud API。"
}

# ---------------------------------------------------------------------------
# 7. 主流程
# ---------------------------------------------------------------------------
main() {
  preflight
  echo
  step_create_bucket
  step_verify_bucket
  step_create_sink
  step_restrict_default_view
  step_create_security_view
  step_grant_view_access
  step_create_metric
  step_verify_metric
  step_verify_views
  step_discard_from_storage
  echo
  troubleshoot_readonly
  echo
  if [[ "$MODE" == "plan" ]]; then
    info "计划展示完成。确认无误后使用 apply 模式执行；Tier B/D 操作仍会逐一确认。"
  else
    info "流程执行完毕。请检查上方各步骤输出。"
  fi
}

main "$@"
