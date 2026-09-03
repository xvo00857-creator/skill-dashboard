#!/usr/bin/env bash
# =============================================================================
# add-matrix-channel.sh
# 受约束的 add-matrix Skill 执行器 —— 严格实现 add-matrix/SKILL.md 的
# Apply(5 步) + Credentials 步骤。
#
# 设计约束（对应题目要求）：
#   - 预检(preflight)：执行前校验目标仓库/分支/工具链，缺则安全退出
#   - 幂等(idempotent)：每步可重复执行，不产生重复副作用
#   - 重试(retry)：仅对网络类操作(pnpm add)做有限次指数退避重试
#   - 人工确认(human gate)：覆盖文件、写入 .env 等破坏性/外部副作用前确认
#   - 干跑(dry-run)：只打印将执行的动作，不落盘
#   - 不静默创建/删除/覆盖外部资源；不访问未提供的远端
#
# 用法:
#   ./apply-matrix-channel.sh --repo <path> [--dry-run] [--yes]
#                             [--non-interactive --fixtures <json>]
#                             [--auth-method A|B|all]
# =============================================================================
set -euo pipefail

REPO_DIR="."
DRY_RUN=0
ASSUME_YES=0
NON_INTERACTIVE=0
FIXTURES_FILE=""
AUTH_METHOD="ask"          # ask | A | B | all
MAX_RETRIES=3
RETRY_BACKOFF=2            # 秒，指数退避基数

# ---- 日志 -------------------------------------------------------------------
if [ -t 1 ]; then C_CYAN=$'\033[36m'; C_YEL=$'\033[33m'; C_RED=$'\033[31m'; C_GRN=$'\033[32m'; C_RST=$'\033[0m'; else C_CYAN=""; C_YEL=""; C_RED=""; C_GRN=""; C_RST=""; fi
log()  { printf '%s[add-matrix]%s %s\n' "$C_CYAN" "$C_RST" "$*"; }
ok()   { printf '%s[add-matrix][OK]%s %s\n' "$C_GRN" "$C_RST" "$*"; }
warn() { printf '%s[add-matrix][WARN]%s %s\n' "$C_YEL" "$C_RST" "$*" >&2; }
err()  { printf '%s[add-matrix][ERROR]%s %s\n' "$C_RED" "$C_RST" "$*" >&2; }
die()  { err "$*"; exit 1; }
step() { printf '\n%s== 步骤 %s ==%s\n' "$C_CYAN" "$*" "$C_RST"; }

usage() { sed -n '2,20p' "$0"; exit "${1:-0}"; }

# ---- 参数解析 ---------------------------------------------------------------
while [ $# -gt 0 ]; do
  case "$1" in
    --repo)            REPO_DIR="$2"; shift 2;;
    --dry-run)         DRY_RUN=1; shift;;
    --yes)             ASSUME_YES=1; shift;;
    --non-interactive) NON_INTERACTIVE=1; shift;;
    --fixtures)        FIXTURES_FILE="$2"; shift 2;;
    --auth-method)     AUTH_METHOD="$2"; shift 2;;
    -h|--help)         usage 0;;
    *) die "未知参数: $1 (用 --help 查看用法)";;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ---- 人工确认点 -------------------------------------------------------------
confirm() {
  local msg="$1"
  if [ "$ASSUME_YES" = 1 ]; then return 0; fi
  if [ "$NON_INTERACTIVE" = 1 ]; then
    die "需要人工确认但处于非交互模式: $msg (加 --yes 显式授权，或交互运行)"
  fi
  printf '%s[add-matrix][确认]%s %s [y/N] ' "$C_YEL" "$C_RST" "$msg"
  local ans; read -r ans
  case "$ans" in y|Y|yes|YES) return 0;; *) die "用户拒绝: $msg";; esac
}

# ---- 仅对网络操作重试 -------------------------------------------------------
retry_net() {
  local desc="$1"; shift
  local n=1 rc=0
  while true; do
    if "$@"; then return 0; fi
    rc=$?
    if [ "$n" -ge "$MAX_RETRIES" ]; then
      err "「$desc」重试 $n 次后仍失败 (exit=$rc)"; return $rc
    fi
    local wait=$((n*RETRY_BACKOFF))
    warn "「$desc」第 $n 次失败，${wait}s 后重试…"; sleep "$wait"
    n=$((n+1))
  done
}

# =============================================================================
# 预检：SKILL.md 步骤1 依赖 channels 分支；步骤3/5 依赖 pnpm 与 package.json
# =============================================================================
preflight() {
  step "0 预检"
  [ -d "$REPO_DIR" ] || die "目标目录不存在: $REPO_DIR"
  REPO_DIR="$(cd "$REPO_DIR" && pwd)"
  log "目标仓库: $REPO_DIR"

  (cd "$REPO_DIR" && git rev-parse --is-inside-work-tree) >/dev/null 2>&1 \
    || die "不是 git 仓库。SKILL.md 步骤1 需要从 channels 分支复制 adapter，无法继续。"

  if ! (cd "$REPO_DIR" && git rev-parse --verify channels >/dev/null 2>&1); then
    die "缺少 channels 分支。SKILL.md 步骤1 (nc:copy from-branch:channels) 要求该分支存在。"
  fi
  ok "存在 channels 分支"

  [ -f "$REPO_DIR/package.json" ] || die "缺少 package.json — 目标不是 NanoClaw/Chat SDK 项目。"
  [ -d "$REPO_DIR/src/channels" ] || die "缺少 src/channels/ 目录 — 目标结构不符。"
  ok "存在 package.json 与 src/channels/"

  for tool in node pnpm git; do
    command -v "$tool" >/dev/null 2>&1 || die "未找到命令: $tool"
  done
  ok "node $(node --version) / pnpm $(pnpm --version) / git $(git --version | awk '{print $3}')"

  for f in src/channels/matrix.ts src/channels/matrix-registration.test.ts; do
    (cd "$REPO_DIR" && git cat-file -e "channels:$f") >/dev/null 2>&1 \
      || die "channels 分支上缺少 $f"
  done
  ok "channels 分支包含 matrix adapter 与注册测试"

  if [ "$DRY_RUN" = 1 ]; then warn "干跑模式：不会写入或修改任何文件。"; fi
}

# =============================================================================
# 步骤1：从 channels 分支复制 adapter（分支为 canonical，允许覆盖）
# nc:copy from-branch:channels
# =============================================================================
do_copy() {
  step "1 复制 Matrix adapter"
  local base="$REPO_DIR/src/channels"
  for f in matrix.ts matrix-registration.test.ts; do
    if [ -f "$base/$f" ]; then
      warn "$base/$f 已存在，将以 channels 分支版本覆盖（SKILL.md: 分支为 canonical）"
      confirm "覆盖 $base/$f ?"
    fi
    if [ "$DRY_RUN" = 1 ]; then
      log "[dry-run] git show channels:$f > $base/$f"
    else
      (cd "$REPO_DIR" && git show "channels:$f" > "$base/$f") \
        || die "从 channels 分支读取 $f 失败"
      ok "已写入 $base/$f"
    fi
  done
}

# =============================================================================
# 步骤2：在 barrel 追加自注册 import（幂等：已存在则跳过）
# nc:append to:src/channels/index.ts
# =============================================================================
do_register() {
  step "2 注册 adapter 到 channel barrel"
  local barrel="$REPO_DIR/src/channels/index.ts"
  [ -f "$barrel" ] || die "barrel 文件不存在: $barrel"
  if grep -qxF "import './matrix.js';" "$barrel"; then
    ok "barrel 已包含 import './matrix.js'; — 跳过（幂等）"
    return 0
  fi
  if [ "$DRY_RUN" = 1 ]; then
    log "[dry-run] 追加 \"import './matrix.js';\" 到 $barrel"
  else
    printf "\nimport './matrix.js';\n" >> "$barrel"
    ok "已追加 import './matrix.js';"
  fi
}

# =============================================================================
# 步骤3：安装固定版本依赖（供应链策略：拒绝范围与 latest）
# nc:dep @beeper/chat-adapter-matrix@0.2.0
# =============================================================================
do_install_dep() {
  step "3 安装 adapter 包（精确固定版本）"
  local pkg="@beeper/chat-adapter-matrix@0.2.0"
  local installed
  installed="$(cd "$REPO_DIR" && node -e '
    try { const p=require("./node_modules/@beeper/chat-adapter-matrix/package.json");
          process.stdout.write(p.version); } catch(e) { process.stdout.write(""); }
  ' 2>/dev/null || true)"
  if [ "$installed" = "0.2.0" ]; then
    ok "$pkg 已安装 (版本匹配) — 跳过（幂等）"
    return 0
  fi
  if [ -n "$installed" ]; then
    warn "已安装版本为 $installed，将被固定为 0.2.0"
  fi
  confirm "执行 pnpm add $pkg (会修改 node_modules 与 lockfile) ?"
  if [ "$DRY_RUN" = 1 ]; then
    log "[dry-run] pnpm add $pkg"
  else
    retry_net "pnpm add $pkg" bash -c "cd '$REPO_DIR' && pnpm add '$pkg'" \
      || die "依赖安装失败"
    ok "已安装 $pkg"
  fi
}

# =============================================================================
# 步骤4：修补 matrix-js-sdk ESM 导入（幂等：正则只补缺失的 .js）
# nc:run effect:external
# =============================================================================
do_patch_esm() {
  step "4 修补 matrix-js-sdk ESM 导入扩展名"
  if [ "$DRY_RUN" = 1 ]; then
    log "[dry-run] 运行 SKILL.md 中的 node patch 脚本"
    return 0
  fi
  (cd "$REPO_DIR" && node -e '
    const fs = require("fs"), path = require("path");
    const root = "node_modules/.pnpm";
    if (!fs.existsSync(root)) { console.log("node_modules/.pnpm 不存在，跳过（依赖未安装？）"); process.exit(0); }
    const dir = fs.readdirSync(root).find(d => d.startsWith("@beeper+chat-adapter-matrix@"));
    if (!dir) { console.log("Matrix adapter not installed"); process.exit(0); }
    const f = path.join(root, dir, "node_modules/@beeper/chat-adapter-matrix/dist/index.js");
    if (!fs.existsSync(f)) { console.log("dist/index.js 不存在，跳过:", f); process.exit(0); }
    const before = fs.readFileSync(f, "utf8");
    const after = before.replace(
      /from "(matrix-js-sdk\/lib\/[^"]+?)(?<!\.js)"/g, "from \"$1.js\""
    );
    if (before === after) { console.log("已修补过，无需改动（幂等）:", f); process.exit(0); }
    fs.writeFileSync(f, after);
    console.log("Patched", f);
  ') || die "ESM patch 执行失败"
  ok "ESM patch 完成"
}

# =============================================================================
# 步骤5：构建 + 注册测试
# nc:run effect:build / effect:test
# =============================================================================
do_build_test() {
  step "5 构建与注册测试"
  if [ "$DRY_RUN" = 1 ]; then
    log "[dry-run] pnpm run build"
    log "[dry-run] pnpm exec vitest run src/channels/matrix-registration.test.ts"
    return 0
  fi
  (cd "$REPO_DIR" && pnpm run build) || die "build 失败（检查 import 行/依赖/ESM patch）"
  ok "build 通过"
  (cd "$REPO_DIR" && pnpm exec vitest run src/channels/matrix-registration.test.ts) \
    || die "注册测试失败"
  ok "matrix-registration 测试通过"
}

# =============================================================================
# 凭证：bot 必须为独立账号（Matrix 不能给自己发 DM）
# nc:prompt / nc:env-set —— 幂等 upsert 到 .env
# =============================================================================
prompt_val() {
  local varname="$1" label="$2" secret="${3:-0}"
  local v=""
  if [ "$NON_INTERACTIVE" = 1 ]; then
    [ -n "$FIXTURES_FILE" ] || die "非交互模式需要 --fixtures <json>"
    v="$(node -e '
      const fs=require("fs");
      const fx=JSON.parse(fs.readFileSync(process.argv[1],"utf8"));
      const s=fx.scenarios[0].inputs[process.argv[2]];
      if (s===undefined) process.exit(2);
      process.stdout.write(String(s));
    ' "$FIXTURES_FILE" "$varname")" || die "fixtures 中缺少输入: $varname"
    log "  $varname = <来自 fixtures${secret:+, secret}>"
  else
    if [ "$secret" = "secret" ]; then
      printf '  %s: ' "$label"; read -rs v; echo
    else
      printf '  %s: ' "$label"; read -r v
    fi
  fi
  printf '%s' "$v"
}

env_upsert() {
  local key="$1" val="$2"
  if [ "$DRY_RUN" = 1 ]; then
    log "[dry-run] .env <= $key=***"
    return 0
  fi
  node "$SCRIPT_DIR/lib/env-upsert.mjs" "$REPO_DIR/.env" "$key" "$val"
}

do_credentials() {
  step "6 配置 bot 凭证（人工步骤）"
  warn "SKILL.md 要求：bot 必须是独立于用户本人的 Matrix 账号（Matrix 不能给自己发 DM）。"
  warn "注册账号/获取 token 需在 Element 中人工完成，本脚本不代劳。"

  if [ "$AUTH_METHOD" = "ask" ] && [ "$NON_INTERACTIVE" != 1 ]; then
    printf '  选择认证方式 [A=用户名密码 / B=access token / all=两者都写(仅fixtures一致性测试)]: '
    read -r AUTH_METHOD
  fi
  case "$AUTH_METHOD" in
    A|B|all) ;;
    *) die "无效认证方式: $AUTH_METHOD (应为 A / B / all)";;
  esac

  local base_url user_id bot_username username password access_token
  base_url="$(prompt_val base_url "homeserver base URL，如 https://matrix.org")"
  user_id="$(prompt_val user_id "bot 完整 user ID，如 @andybot:matrix.org")"
  bot_username="$(prompt_val bot_username "bot 显示名，如 Andy")"

  confirm "将写入 $REPO_DIR/.env (幂等 upsert，会更新已存在的 MATRIX_* 键) ?"

  env_upsert MATRIX_BASE_URL    "$base_url"
  env_upsert MATRIX_USER_ID     "$user_id"
  env_upsert MATRIX_BOT_USERNAME "$bot_username"

  if [ "$AUTH_METHOD" = "A" ] || [ "$AUTH_METHOD" = "all" ]; then
    username="$(prompt_val username "Option A: bot 登录名(localpart)")"
    password="$(prompt_val password "Option A: bot 密码" secret)"
    env_upsert MATRIX_USERNAME "$username"
    env_upsert MATRIX_PASSWORD "$password"
  fi
  if [ "$AUTH_METHOD" = "B" ] || [ "$AUTH_METHOD" = "all" ]; then
    access_token="$(prompt_val access_token "Option B: access token" secret)"
    env_upsert MATRIX_ACCESS_TOKEN "$access_token"
  fi
  ok "凭证已写入 .env（请确认 .env 不被提交到版本库）"
  if [ "$AUTH_METHOD" = "all" ]; then
    warn "同时写入了密码与 access_token —— 仅用于 fixtures 一致性测试；"
    warn "SKILL.md 中 Option A/B 为二选一，生产环境请只保留一种。"
  fi
}

# =============================================================================
# 主流程
# =============================================================================
main() {
  log "add-matrix Skill 受约束执行器（严格按 SKILL.md）"
  preflight
  do_copy
  do_register
  do_install_dep
  do_patch_esm
  do_build_test
  do_credentials
  echo
  ok "全部完成。后续：运行 /manage-channels 将该渠道接到 agent group（SKILL.md Next Steps）。"
  warn "端到端消息投递需在服务启动后人工对真实 homeserver 验证（SKILL.md 明确说明）。"
}
main "$@"
