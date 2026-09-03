#!/usr/bin/env bash
# accint-frames 受约束排空脚本（预检 + 干跑）
# 严格依据 accint-frames/SKILL.md：
#   1. acc frames            —— 只读列出队列
#   2. acc_act(runtime="continue", input={frame_id, submit_token, proposal_text})
#   3. proposal_text 以 PREDICT: <0.00-1.00> <why> 结尾
#   4. 重复 submit 重放缓存结果（幂等）
#   5. 排空队列后再接新工作
# 本脚本默认只做预检（--preflight），不执行任何 submit；
# 真正 submit 前必须通过 --i-have-human-approval 并经人工确认点。
set -euo pipefail

LOG_FILE="accint_frames_drain.log"
STATE_FILE="drained_frames.tsv"
MAX_RETRY=3
RETRY_BACKOFF=(1 2 4)

log() { printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" | tee -a "$LOG_FILE"; }

# ---------- 幂等：状态文件 ----------
init_state() {
  if [[ ! -f "$STATE_FILE" ]]; then
    printf 'frame_id\tsubmit_token\tcommitment_id\tstatus\ttimestamp\n' > "$STATE_FILE"
    log "初始化幂等状态文件 $STATE_FILE"
  fi
}

already_drained() {
  # 返回 0 表示该 frame 已有成功 commitment（幂等跳过）
  local fid="$1"
  awk -F'\t' -v f="$fid" '$1==f && $4=="success"{found=1} END{exit !found}' "$STATE_FILE"
}

record_drain() {
  local fid="$1" token="$2" commit="$3" status="$4"
  printf '%s\t%s\t%s\t%s\t%s\n' "$fid" "$token" "$commit" "$status" "$(date '+%Y-%m-%dT%H:%M:%S')" >> "$STATE_FILE"
}

# ---------- 重试：仅用于只读命令 ----------
retry_readonly() {
  local desc="$1"; shift
  local attempt=1 rc=0
  while (( attempt <= MAX_RETRY )); do
    log "[$desc] 第 $attempt 次尝试（只读）"
    if "$@"; then
      log "[$desc] 成功"
      return 0
    fi
    rc=$?
    log "[$desc] 失败 rc=$rc"
    if (( attempt == MAX_RETRY )); then break; fi
    log "[$desc] ${RETRY_BACKOFF[$((attempt-1))]}s 后重试"
    sleep "${RETRY_BACKOFF[$((attempt-1))]}"
    ((attempt++))
  done
  return $rc
}

# ---------- 预检 ----------
preflight() {
  log "===== 预检开始 ====="
  local fail=0

  # P1: acc CLI
  if command -v acc >/dev/null 2>&1; then
    log "P1 通过：acc CLI 位于 $(command -v acc)"
  else
    log "P1 失败：acc CLI 未在 PATH 中找到"
    fail=1
  fi

  # P2: acc_act MCP 动词（本脚本无法直接探测 MCP 注册，检查是否有 acc_act 可执行包装）
  if command -v acc_act >/dev/null 2>&1; then
    log "P2 通过：acc_act 可执行包装存在"
  else
    log "P2 失败：acc_act MCP 动词未注册/不可用（需在 MCP 配置中启用）"
    fail=1
  fi

  # P3: 配置/认证目录
  local cfg_found=0
  for d in "$HOME/.acc" "$HOME/.config/acc" "$HOME/.local/share/acc"; do
    if [[ -d "$d" ]]; then log "P3 发现配置目录：$d"; cfg_found=1; fi
  done
  if (( cfg_found == 0 )); then
    log "P3 失败：未发现 acc 配置/认证目录（~/.acc、~/.config/acc、~/.local/share/acc 均不存在）"
    fail=1
  fi

  # P4: acc frames 只读列表（仅当 P1 通过时尝试）
  if command -v acc >/dev/null 2>&1; then
    if retry_readonly "acc frames" acc frames; then
      log "P4 通过：队列可访问"
    else
      log "P4 失败：acc frames 无法列出队列"
      fail=1
    fi
  else
    log "P4 跳过：P1 未通过，无法执行 acc frames"
  fi

  log "===== 预检结束：$([[ $fail -eq 0 ]] && echo 全部通过 || echo 存在阻断项) ====="
  return $fail
}

# ---------- 人工确认点 ----------
human_confirm() {
  local msg="$1"
  if [[ "${HUMAN_APPROVAL:-0}" != "1" ]]; then
    log "人工确认点[$msg]：未传入 --i-have-human-approval，停止。"
    return 1
  fi
  printf '人工确认 -> %s [y/N]: ' "$msg"
  local ans; read -r ans
  [[ "$ans" == "y" || "$ans" == "Y" ]]
}

# ---------- 主流程 ----------
main() {
  local mode="${1:---preflight}"
  log "accint-frames 排空脚本启动，模式=$mode"
  init_state

  case "$mode" in
    --preflight)
      if preflight; then
        log "预检通过。下一步：经 H1 人工确认后，以 --i-have-human-approval --drain 运行。"
      else
        log "预检未通过：流程安全停止，未执行任何 submit，未产生外部副作用。"
        log "需人工确认(H3)：安装 acc CLI / 配置认证 / 启用 acc_act MCP 动词。"
        exit 2
      fi
      ;;
    --drain)
      HUMAN_APPROVAL="${HUMAN_APPROVAL:-0}"
      preflight || { log "预检未通过，不能排空。"; exit 2; }
      human_confirm "H1：是否开始排空队列？" || exit 3
      # 真实环境此处应解析 acc frames 的 JSON 输出，逐 frame 处理。
      # 本干跑脚本不构造任何 frame 数据（不得编造 frame_id/submit_token）。
      log "干跑模式：未提供真实队列解析逻辑，且本环境无队列数据；不执行 submit。"
      log "真实流程中每个 frame 须经 H2 确认 proposal_text（含 PREDICT 行）后提交。"
      ;;
    *)
      echo "用法: $0 [--preflight|--drain]  (--drain 需配合 --i-have-human-approval)"
      exit 64
      ;;
  esac
}

# 允许 --i-have-human-approval 出现在任意位置
for arg in "$@"; do
  [[ "$arg" == "--i-have-human-approval" ]] && HUMAN_APPROVAL=1
done
main "${1:---preflight}"
