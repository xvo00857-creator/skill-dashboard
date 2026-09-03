#!/usr/bin/env bash
#
# cross-project-logging-setup.sh
# Google Cloud 跨项目集中日志配置 —— 受约束流程脚本
#
# 严格遵循 cloud-logging-cross-project-configuration SKILL.md：
#   - Tier R（只读）：无需确认，直接执行
#   - Tier M（非计费变更）：无需确认，但必须幂等
#   - Tier B（计费/安全敏感）：必须人工确认，且不得在询问当轮执行
#   - Tier D（不可逆数据丢失）：必须显式输入 "Yes, discard logs" 方可执行
#
# 沙箱约束：不运行网络发现命令（projects list / organizations list 等），
#           所有项目 ID 必须由调用方显式传入；不静默创建/删除/覆盖外部资源。
#
# 用法：
#   ./cross-project-logging-setup.sh --mode central --central-project P --source-project S [选项]
#   ./cross-project-logging-setup.sh --mode scope   --scoping-project P --source-projects S1,S2 [选项]
#
# 通用选项：
#   --dry-run                  只打印将要执行的命令，不实际变更（推荐先跑）
#   --bucket-id ID             中心日志桶 ID（central 模式，默认 central-logs-bucket）
#   --region REGION            区域（默认 us-central1，SKILL 建议不用 global）
#   --retention-days N         保留天数（默认 30）
#   --sink-name NAME           Sink 名称（默认 route-to-central）
#   --yes-tier-b               跳过 Tier B 确认（仅限已获书面授权时使用）
#   --max-retries N            瞬时失败重试次数（默认 3）
#   -h | --help                帮助
#
set -euo pipefail

# ---------------------------------------------------------------------------
# 默认参数
# ---------------------------------------------------------------------------
MODE=""
CENTRAL_PROJECT=""
SCIPING_PROJECT=""
SOURCE_PROJECTS=""
SOURCE_ORGANIZATION=""
BUCKET_ID="central-logs-bucket"
REGION="us-central1"
RETENTION_DAYS=30
SINK_NAME="route-to-central"
LOG_SCOPE_ID="central-query-scope"
DRY_RUN=0
SKIP_TIER_B=0
MAX_RETRIES=3
RETRY_BASE_DELAY=2

# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------
log()  { printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }
info() { log "[INFO]  $*"; }
warn() { log "[WARN]  $*" >&2; }
err()  { log "[ERROR] $*" >&2; }
die()  { err "$*"; exit 1; }

# 带指数退避的重试（仅对幂等只读/查询类命令使用）
retry() {
  local attempt=1 delay="$RETRY_BASE_DELAY" rc=0
  while (( attempt <= MAX_RETRIES + 1 )); do
    if "$@"; then return 0; fi
    rc=$?
    if (( attempt > MAX_RETRIES )); then break; fi
    warn "命令失败（退出码 $rc），${delay}s 后第 $attempt 次重试: $*"
    sleep "$delay"
    delay=$(( delay * 2 ))
    attempt=$(( attempt + 1 ))
  done
  return "$rc"
}

# 执行或干跑：dry-run 时只打印，不执行
run() {
  if (( DRY_RUN )); then
    printf '[DRY-RUN]'
    printf ' %q' "$@"
    printf '\n'
  else
    "$@"
  fi
}

# Tier B 人工确认门
confirm_tier_b() {
  local reason="$1"; shift
  if (( SKIP_TIER_B )); then
    warn "Tier B 已通过 --yes-tier-b 跳过（请确保已有书面授权）: $reason"
    return 0
  fi
  echo
  echo "========== Tier B 人工确认（计费/安全敏感）=========="
  echo "原因：$reason"
  echo "即将执行的命令（逐字）："
  printf '  '; printf '%q ' "$@"; printf '\n'
  echo "====================================================="
  echo "请在确认无误后回复 yes 执行，其余任意输入取消："
  local ans
  read -r ans
  [[ "$ans" == "yes" ]] || die "用户未确认 Tier B 操作，已中止。"
}

# Tier D 显式输入确认门（不可逆数据丢失）
confirm_tier_d() {
  local reason="$1"; shift
  echo
  echo "========== Tier D 危险操作（不可逆数据丢失）=========="
  echo "原因：$reason"
  echo "即将执行的命令（逐字）："
  printf '  '; printf '%q ' "$@"; printf '\n'
  echo "======================================================="
  echo "此操作不可恢复。如确认丢弃日志，请逐字输入：Yes, discard logs"
  local ans
  read -r ans
  [[ "$ans" == "Yes, discard logs" ]] || die "未收到显式确认，已中止。"
}

# ---------------------------------------------------------------------------
# 预检（Tier R，全部只读）
# ---------------------------------------------------------------------------
preflight() {
  info "开始预检（全部为 Tier R 只读操作）"

  # 1. gcloud 是否安装
  if ! command -v gcloud >/dev/null 2>&1; then
    if (( DRY_RUN )); then
      warn "未找到 gcloud CLI；dry-run 模式下继续，仅输出命令清单。"
    else
      die "预检失败：未找到 gcloud CLI。请先安装 Google Cloud SDK：https://cloud.google.com/sdk/docs/install"
    fi
  else
    info "gcloud 已安装：$(gcloud --version 2>/dev/null | head -1)"
  fi

  # 2. 是否已认证
  local active_account=""
  if command -v gcloud >/dev/null 2>&1; then
    active_account="$(gcloud auth list --filter=status:ACTIVE --format='value(account)' 2>/dev/null || true)"
  fi
  if [[ -z "$active_account" ]]; then
    if (( DRY_RUN )); then
      warn "未检测到 gcloud 认证账号；dry-run 模式下继续。"
    else
      die "预检失败：gcloud 未认证。请运行 gcloud auth login 或 gcloud auth application-default login"
    fi
  else
    info "当前认证账号：$active_account"
  fi

  # 3. 必要参数校验（不做网络发现，只校验显式传入值）
  [[ -n "$MODE" ]] || die "预检失败：必须指定 --mode central|scope"
  if [[ "$MODE" == "central" ]]; then
    [[ -n "$CENTRAL_PROJECT" ]] || die "预检失败：central 模式需要 --central-project"
    [[ -n "$SOURCE_PROJECTS" || -n "$SOURCE_ORGANIZATION" ]] \
      || die "预检失败：central 模式需要 --source-projects 或 --source-organization"
  elif [[ "$MODE" == "scope" ]]; then
    [[ -n "$SCIPING_PROJECT" ]] || die "预检失败：scope 模式需要 --scoping-project"
    [[ -n "$SOURCE_PROJECTS" ]] || die "预检失败：scope 模式需要 --source-projects"
  else
    die "预检失败：未知 mode=${MODE}（仅支持 central / scope）"
  fi

  # 4. 区域校验（SKILL 建议中心桶用区域桶，不用 global）
  if [[ "$MODE" == "central" && "$REGION" == "global" ]]; then
    warn "central 模式建议使用区域桶（如 us-central1），global 可能不兼容 Observability Analytics"
  fi

  # 5. 网络连通性（只做一次轻量探测，不做资源发现）
  if (( ! DRY_RUN )); then
    info "探测 GCP Logging API 连通性..."
    if ! gcloud logging logs list --page-size=1 --format="value(name)" >/dev/null 2>&1; then
      warn "无法访问 GCP Logging API（可能是沙箱网络限制或权限不足）。"
      warn "按 SKILL.md 沙箱规则，将不执行任何变更操作；可使用 --dry-run 查看完整命令清单。"
      return 1
    fi
  fi

  info "预检通过"
  return 0
}

# ---------------------------------------------------------------------------
# 幂等辅助：资源存在性检查（Tier R）
# ---------------------------------------------------------------------------
bucket_exists() {
  local project="$1" location="$2" bucket="$3"
  gcloud logging buckets describe "$bucket" \
    --project="$project" --location="$location" >/dev/null 2>&1
}

sink_exists() {
  local project="$1" sink="$2"
  gcloud logging sinks describe "$sink" --project="$project" >/dev/null 2>&1
}

view_exists() {
  local project="$1" location="$2" bucket="$3" view="$4"
  gcloud logging views describe "$view" \
    --project="$project" --location="$location" --bucket="$bucket" >/dev/null 2>&1
}

scope_exists() {
  local project="$1" scope="$2"
  gcloud logging scopes describe "$scope" --project="$project" >/dev/null 2>&1
}

# ---------------------------------------------------------------------------
# 架构一：集中式存储（Log Routing）
# ---------------------------------------------------------------------------
setup_central() {
  info "===== 架构：集中式存储（Centralized Storage）====="
  info "中心项目=$CENTRAL_PROJECT 区域=$REGION 桶=$BUCKET_ID 保留=${RETENTION_DAYS}天"

  # 步骤 1：创建中心日志桶（Tier M，幂等）
  info "[步骤 1/5] 检查/创建中心日志桶（Tier M）"
  if (( DRY_RUN )) || ! bucket_exists "$CENTRAL_PROJECT" "$REGION" "$BUCKET_ID"; then
    run gcloud logging buckets create "$BUCKET_ID" \
      --project="$CENTRAL_PROJECT" \
      --location="$REGION" \
      --retention-days="$RETENTION_DAYS" \
      --enable-analytics
    (( DRY_RUN )) || info "桶 $BUCKET_ID 已创建"
  else
    info "桶 $BUCKET_ID 已存在，跳过创建（幂等）"
  fi

  # 步骤 2：在中心项目创建 sink（Tier M，幂等）
  info "[步骤 2/5] 检查/创建中心项目 sink（Tier M）"
  if (( DRY_RUN )) || ! sink_exists "$CENTRAL_PROJECT" "$SINK_NAME"; then
    run gcloud logging sinks create "$SINK_NAME" \
      "logging.googleapis.com/projects/${CENTRAL_PROJECT}/locations/${REGION}/buckets/${BUCKET_ID}" \
      --project="$CENTRAL_PROJECT"
    (( DRY_RUN )) || info "中心 sink $SINK_NAME 已创建"
  else
    info "中心 sink $SINK_NAME 已存在，跳过创建（幂等）"
  fi

  # 步骤 3：在源项目/组织创建 sink（Tier M，幂等）
  info "[步骤 3/5] 检查/创建源端 sink（Tier M）"
  local dest="logging.googleapis.com/projects/${CENTRAL_PROJECT}"
  local exclusions=(
    --exclusion=filter='LOG_ID("cloudaudit.googleapis.com/activity")'
    --exclusion=filter='LOG_ID("externalaudit.googleapis.com/activity")'
    --exclusion=filter='LOG_ID("cloudaudit.googleapis.com/system_event")'
    --exclusion=filter='LOG_ID("externalaudit.googleapis.com/system_event")'
    --exclusion=filter='LOG_ID("cloudaudit.googleapis.com/access_transparency")'
    --exclusion=filter='LOG_ID("externalaudit.googleapis.com/access_transparency")'
  )

  if [[ -n "$SOURCE_ORGANIZATION" ]]; then
    if (( DRY_RUN )) || ! gcloud logging sinks describe "$SINK_NAME" \
         --organization="$SOURCE_ORGANIZATION" >/dev/null 2>&1; then
      run gcloud logging sinks create "$SINK_NAME" "$dest" \
        --organization="$SOURCE_ORGANIZATION" --include-children "${exclusions[@]}"
    else
      info "组织 sink 已存在，跳过"
    fi
  fi

  IFS=',' read -ra SRC_ARRAY <<< "$SOURCE_PROJECTS"
  for src in "${SRC_ARRAY[@]}"; do
    src="$(echo "$src" | xargs)"  # trim
    [[ -z "$src" ]] && continue
    if (( DRY_RUN )) || ! sink_exists "$src" "$SINK_NAME"; then
      info "  在源项目 $src 创建 sink"
      run gcloud logging sinks create "$SINK_NAME" "$dest" \
        --project="$src" "${exclusions[@]}"
    else
      info "  源项目 $src 的 sink 已存在，跳过（幂等）"
    fi
  done

  # 步骤 4：授予 IAM 权限（Tier B —— 必须人工确认）
  info "[步骤 4/5] IAM 授权（Tier B，安全敏感）"
  # 4a. 源 sink writerIdentity -> 中心项目 logWriter
  local src_writer=""
  if (( ! DRY_RUN )) && [[ -n "${SRC_ARRAY[0]:-}" ]]; then
    src_writer="$(retry gcloud logging sinks describe "$SINK_NAME" \
      --project="${SRC_ARRAY[0]}" --format="value(writerIdentity)" 2>/dev/null || true)"
  fi
  if [[ -n "$src_writer" ]]; then
    confirm_tier_b "为源 sink 服务账号授予中心项目 roles/logging.logWriter" \
      gcloud projects add-iam-policy-binding "$CENTRAL_PROJECT" \
      --member="$src_writer" --role=roles/logging.logWriter
    run gcloud projects add-iam-policy-binding "$CENTRAL_PROJECT" \
      --member="$src_writer" --role=roles/logging.logWriter
  else
    info "  （dry-run 或未取到 writerIdentity）待执行命令："
    info "    gcloud logging sinks describe $SINK_NAME --project=<source> --format=value(writerIdentity)"
    info "    gcloud projects add-iam-policy-binding $CENTRAL_PROJECT --member=<writerIdentity> --role=roles/logging.logWriter"
  fi

  # 4b. 中心 sink writerIdentity -> bucketWriter
  local central_writer=""
  if (( ! DRY_RUN )); then
    central_writer="$(retry gcloud logging sinks describe "$SINK_NAME" \
      --project="$CENTRAL_PROJECT" --format="value(writerIdentity)" 2>/dev/null || true)"
  fi
  if [[ -n "$central_writer" ]]; then
    confirm_tier_b "为中心 sink 服务账号授予中心项目 roles/logging.bucketWriter" \
      gcloud projects add-iam-policy-binding "$CENTRAL_PROJECT" \
      --member="$central_writer" --role=roles/logging.bucketWriter
    run gcloud projects add-iam-policy-binding "$CENTRAL_PROJECT" \
      --member="$central_writer" --role=roles/logging.bucketWriter
  else
    info "  （dry-run 或未取到 writerIdentity）待执行命令："
    info "    gcloud projects add-iam-policy-binding $CENTRAL_PROJECT --member=<centralWriterIdentity> --role=roles/logging.bucketWriter"
  fi

  # 步骤 5：自定义 Log View（Tier M，幂等）
  info "[步骤 5/5] 检查/创建自定义 Log View（Tier M）"
  for src in "${SRC_ARRAY[@]}"; do
    src="$(echo "$src" | xargs)"
    [[ -z "$src" ]] && continue
    local view_id="view-${src//[^a-zA-Z0-9]/-}"
    if (( DRY_RUN )) || ! view_exists "$CENTRAL_PROJECT" "$REGION" "$BUCKET_ID" "$view_id"; then
      run gcloud logging views create "$view_id" \
        --bucket="$BUCKET_ID" --location="$REGION" --project="$CENTRAL_PROJECT" \
        --log-filter="project_id=\"${src}\""
    else
      info "  View $view_id 已存在，跳过（幂等）"
    fi
  done

  # 验证指引（Tier R）
  info "集中式存储配置流程完成。验证步骤（Tier R，可直接执行）："
  info "  gcloud logging write cross-project-test 'Test log entry' --severity=WARNING --project=<source_project>"
  info "  gcloud logging read 'logName:\"projects/<source_project>/logs/cross-project-test\"' \\"
  info "    --bucket=$BUCKET_ID --location=$REGION --view=_AllLogs --project=$CENTRAL_PROJECT"
}

# ---------------------------------------------------------------------------
# 架构二：读时聚合（Log Scopes）
# ---------------------------------------------------------------------------
setup_scope() {
  info "===== 架构：读时聚合（Read-Time Aggregation）====="
  info "Scoping 项目=$SCIPING_PROJECT 源项目=$SOURCE_PROJECTS"

  IFS=',' read -ra SRC_ARRAY <<< "$SOURCE_PROJECTS"
  local resource_names=()

  # 步骤 1：为每个源项目创建自定义 Log View（Tier M，幂等）
  info "[步骤 1/3] 检查/创建源项目 Log View（Tier M）"
  for src in "${SRC_ARRAY[@]}"; do
    src="$(echo "$src" | xargs)"
    [[ -z "$src" ]] && continue
    local view_id="app-logs-view"
    if (( DRY_RUN )) || ! view_exists "$src" "global" "_Default" "$view_id"; then
      run gcloud logging views create "$view_id" \
        --bucket="_Default" --location=global --project="$src"
    else
      info "  $src 的 View $view_id 已存在，跳过（幂等）"
    fi
    resource_names+=("projects/${src}/locations/global/buckets/_Default/views/${view_id}")
  done

  # 步骤 2：创建 log scope（Tier M，幂等）
  info "[步骤 2/3] 检查/创建 Log Scope（Tier M）"
  local IFS=','
  local rn="${resource_names[*]}"
  if (( DRY_RUN )) || ! scope_exists "$SCIPING_PROJECT" "$LOG_SCOPE_ID"; then
    run gcloud logging scopes create "$LOG_SCOPE_ID" \
      --project="$SCIPING_PROJECT" --resource-names="$rn"
  else
    info "  Scope $LOG_SCOPE_ID 已存在，跳过（幂等）"
  fi

  # 步骤 3：IAM 授权（Tier B）
  info "[步骤 3/3] IAM 授权（Tier B，安全敏感）"
  info "  读时聚合要求查询者在每个源项目具备 roles/logging.viewAccessor（带 IAM 条件）"
  info "  或 roles/logging.viewer，并能访问 scoping 项目。"
  info "  待执行示例（需替换 <user> 并经 Tier B 确认）："
  info "    gcloud projects add-iam-policy-binding <source_project> --member=<user> --role=roles/logging.viewer"

  info "读时聚合配置流程完成。验证：在 Logs Explorer 中选择 scope $LOG_SCOPE_ID 即可跨项目查询。"
}

# ---------------------------------------------------------------------------
# 参数解析
# ---------------------------------------------------------------------------
usage() { sed -n '2,30p' "$0"; exit 0; }

while (( $# > 0 )); do
  case "$1" in
    --mode)               MODE="$2"; shift 2;;
    --central-project)    CENTRAL_PROJECT="$2"; shift 2;;
    --scoping-project)    SCIPING_PROJECT="$2"; shift 2;;
    --source-projects)    SOURCE_PROJECTS="$2"; shift 2;;
    --source-organization) SOURCE_ORGANIZATION="$2"; shift 2;;
    --bucket-id)          BUCKET_ID="$2"; shift 2;;
    --region)             REGION="$2"; shift 2;;
    --retention-days)     RETENTION_DAYS="$2"; shift 2;;
    --sink-name)          SINK_NAME="$2"; shift 2;;
    --log-scope-id)       LOG_SCOPE_ID="$2"; shift 2;;
    --dry-run)            DRY_RUN=1; shift;;
    --yes-tier-b)         SKIP_TIER_B=1; shift;;
    --max-retries)        MAX_RETRIES="$2"; shift 2;;
    -h|--help)            usage;;
    *) die "未知参数：$1（用 --help 查看用法）";;
  esac
done

# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
info "cloud-logging-cross-project-configuration 受约束流程启动"
(( DRY_RUN )) && warn "DRY-RUN 模式：仅打印命令，不执行任何变更"

preflight || {
  warn "预检未完全通过（常见于沙箱环境：无 gcloud / 无网络 / 无凭证）。"
  warn "将以 dry-run 模式输出完整命令清单供人工审阅与执行。"
  DRY_RUN=1
}

case "$MODE" in
  central) setup_central;;
  scope)   setup_scope;;
  *)       die "未知 mode: $MODE";;
esac

info "流程结束。"
