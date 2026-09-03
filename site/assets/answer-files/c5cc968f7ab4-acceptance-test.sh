#!/usr/bin/env bash
#
# acceptance-test.sh
# 本地测试站点的可重复浏览器验收流程（基于 browser-cdp Skill）
#
# 覆盖：登录（空提交 / 错误凭据 / 正确凭据）、表单校验（必填 / 格式 / 成功提交）、
#       错误状态、每步截图证据。
#
# 安全原则：
#   - 默认 dry-run，只打印将执行的命令；必须显式 --run 才真正操作浏览器。
#   - 不自行 kill Chrome；不提取 token / cookie；不写入生产环境。
#   - 凭据只从环境变量或 .env.acceptance 读取，不硬编码、不入库。
#   - 任一断言失败立即停止（可配置 CONTINUE_ON_FAIL=1 继续）。
#
# 用法：
#   chmod +x acceptance-test.sh
#   ./acceptance-test.sh                 # dry-run 预演（默认）
#   ./acceptance-test.sh --run           # 真正执行
#   ./acceptance-test.sh --run --case login   # 只跑登录用例
#
# 配置（环境变量，或复制 .env.acceptance.example 为 .env.acceptance 后填写）：
#   TEST_BASE_URL       被测站点根地址，例如 http://127.0.0.1:8080
#   TEST_USER           登录用户名（测试账号）
#   TEST_PASS           登录密码（测试账号）
#   CDP_PORT            CDP 端口，默认 9222
#   选择器变量见 .env.acceptance.example
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "${SCRIPT_DIR}/../browser-cdp-extracted/browser-cdp" && pwd)"
SETUP_JS="${SKILL_DIR}/scripts/setup-cdp-chrome.js"
SHOT_JS="${SCRIPT_DIR}/cdp-screenshot.js"

# ---------- 参数解析 ----------
MODE="dry-run"
CASE_FILTER=""
for arg in "$@"; do
  case "$arg" in
    --run) MODE="run" ;;
    --case) shift; CASE_FILTER="${2:-}" ;;
    --case=*) CASE_FILTER="${arg#--case=}" ;;
    *) ;;
  esac
done

# ---------- 加载配置 ----------
if [[ -f "${SCRIPT_DIR}/.env.acceptance" ]]; then
  # shellcheck disable=SC1091
  set -a; source "${SCRIPT_DIR}/.env.acceptance"; set +a
fi

# 被测站点（dry-run 时用占位值，--run 时必须在 .env 中配置真实值）
: "${TEST_BASE_URL:=<TEST_BASE_URL>}"
: "${TEST_USER:=<TEST_USER>}"
: "${TEST_PASS:=<TEST_PASS>}"

: "${CDP_PORT:=9222}"
: "${CONTINUE_ON_FAIL:=0}"

# 被测页面路径（可在 .env 中覆盖）
: "${LOGIN_PATH:=/login}"
: "${FORM_PATH:=/form}"
: "${ERROR_PATH:=/this-page-does-not-exist}"

# 选择器（可在 .env 中覆盖；以下为占位默认值，必须按实际站点修改）
: "${SEL_USER_INPUT:=input[name=username]}"
: "${SEL_PASS_INPUT:=input[name=password]}"
: "${SEL_SUBMIT_BTN:=button[type=submit]}"
: "${SEL_FORM_INPUT:=input[name=email]}"
: "${SEL_ERROR_MSG:=.error-message}"
: "${SEL_SUCCESS_MSG:=.success-message}"

RUN_ID="$(date +%Y%m%d-%H%M%S)"
SHOT_DIR="${SCRIPT_DIR}/screenshots/${RUN_ID}"
LOG_FILE="${SCRIPT_DIR}/run-${RUN_ID}.log"
PASS_COUNT=0
FAIL_COUNT=0

# ---------- 工具函数 ----------
log()  { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG_FILE"; }
pass() { PASS_COUNT=$((PASS_COUNT+1)); log "  ✅ PASS: $*"; }
fail() { FAIL_COUNT=$((FAIL_COUNT+1)); log "  ❌ FAIL: $*"; screenshot "FAIL-$(echo "$*" | tr ' /' '__' | head -c 40)"; if [[ "$CONTINUE_ON_FAIL" != "1" ]]; then log "遇到失败，停止执行（CONTINUE_ON_FAIL=1 可继续）。"; summary; exit 1; fi; }

# 执行或预演一条 agent-browser 命令
ab() {
  if [[ "$MODE" == "dry-run" ]]; then
    echo "    [dry-run] agent-browser --cdp ${CDP_PORT} $*" | tee -a "$LOG_FILE"
    return 0
  fi
  timeout 30 agent-browser --cdp "${CDP_PORT}" "$@" 2>&1 | tee -a "$LOG_FILE"
}

# 在页面上执行 JS 断言（eval 返回值非空即视为断言通过）
assert_eval() {
  local desc="$1" js="$2"
  if [[ "$MODE" == "dry-run" ]]; then
    echo "    [dry-run] 断言: ${desc} | JS: ${js}" | tee -a "$LOG_FILE"
    pass "$desc (dry-run)"
    return 0
  fi
  local out
  out="$(timeout 30 agent-browser --cdp "${CDP_PORT}" eval "$js" 2>&1 | tee -a "$LOG_FILE")" || true
  if echo "$out" | grep -qiE 'true|ok|success|存在|通过'; then
    pass "$desc"
  else
    fail "$desc（eval 输出: $(echo "$out" | head -c 120)）"
  fi
}

screenshot() {
  local name="$1"
  if [[ "$MODE" == "dry-run" ]]; then
    echo "    [dry-run] 截图 -> screenshots/${RUN_ID}/${name}.png" | tee -a "$LOG_FILE"
    return 0
  fi
  mkdir -p "$SHOT_DIR"
  node "$SHOT_JS" --port "$CDP_PORT" --out "${SHOT_DIR}/${name}.png" 2>&1 | tee -a "$LOG_FILE" || \
    log "  ⚠️ 截图失败: ${name}"
}

summary() {
  log "---------- 用例汇总 ----------"
  log "通过: ${PASS_COUNT}  失败: ${FAIL_COUNT}  模式: ${MODE}"
  [[ "$MODE" == "run" ]] && log "截图目录: ${SHOT_DIR}"
  log "日志文件: ${LOG_FILE}"
}

# ---------- 前置检查（Skill 强制流程）----------
preflight() {
  log "===== 前置检查 ====="

  # 1) Skill 规定的第一步：detect-only（无副作用）
  log "执行 detect-only 探测..."
  local detect
  detect="$(node "$SETUP_JS" "$CDP_PORT" --detect-only 2>&1)" || true
  echo "$detect" | tee -a "$LOG_FILE"

  if echo "$detect" | grep -q "CDP_STATUS=ready"; then
    log "CDP 已就绪，按 Skill 规则直接复用，不运行 setup。"
  elif echo "$detect" | grep -q "CHROME_RUNNING=yes"; then
    local n; n="$(echo "$detect" | grep CHROME_PID_COUNT | cut -d= -f2)"
    log "⚠️ CDP 未就绪且检测到 ${n:-?} 个 Chrome 进程。"
    log "按 Skill 规则，启动调试 Chrome 会 kill 这些进程，可能丢失未保存工作。"
    log "本脚本不会自动执行该操作。请你手动确认后运行："
    log "    node \"$SETUP_JS\" $CDP_PORT --yes"
    log "（运行前请保存常规 Chrome 中的工作）"
    exit 1
  else
    log "CDP 未就绪且无 Chrome 运行。可安全启动："
    log "    node \"$SETUP_JS\" $CDP_PORT"
    exit 1
  fi

  # 2) 检查 agent-browser
  if ! command -v agent-browser >/dev/null 2>&1; then
    log "⚠️ 未找到 agent-browser。Skill 前置条件要求：npm install -g agent-browser"
    [[ "$MODE" == "run" ]] && { log "缺少依赖，无法 --run。"; exit 1; }
  fi

  # 3) 检查必填配置（占位值视为未配置）
  local missing=0
  case "$TEST_BASE_URL" in ""|"<TEST_BASE_URL>") log "缺少配置 TEST_BASE_URL"; missing=1 ;; esac
  case "$TEST_USER" in ""|"<TEST_USER>") log "缺少配置 TEST_USER（测试账号）"; missing=1 ;; esac
  case "$TEST_PASS" in ""|"<TEST_PASS>") log "缺少配置 TEST_PASS（测试账号）"; missing=1 ;; esac
  if [[ $missing -eq 1 ]]; then
    log "请在 .env.acceptance 或环境变量中填写上述配置后再 --run。"
    [[ "$MODE" == "run" ]] && exit 1
  fi

  log "前置检查完成（模式: ${MODE}）。"
}

# ---------- 用例 ----------
case_login() {
  log "===== 用例组：登录 ====="
  local url="${TEST_BASE_URL}${LOGIN_PATH}"

  log "[1/5] 打开登录页: $url"
  ab open "$url"; ab wait 2000; screenshot "01-login-page"
  assert_eval "登录页已加载" "document.querySelector('${SEL_SUBMIT_BTN}') ? 'ok' : 'no-submit'"

  log "[2/5] 空提交：应出现必填校验"
  ab click "$SEL_SUBMIT_BTN"; ab wait 1000; screenshot "02-login-empty-submit"
  assert_eval "空提交出现错误提示" "document.querySelector('${SEL_ERROR_MSG}') ? 'ok' : 'no-error'"

  log "[3/5] 错误凭据：应提示登录失败"
  ab type "$SEL_USER_INPUT" "__invalid_user__"
  ab type "$SEL_PASS_INPUT" "__wrong_pass__"
  ab click "$SEL_SUBMIT_BTN"; ab wait 2000; screenshot "03-login-bad-cred"
  assert_eval "错误凭据被拒绝" "document.querySelector('${SEL_ERROR_MSG}') ? 'ok' : 'no-error'"

  log "[4/5] 正确凭据：应登录成功"
  # 重新打开页面清空上一次输入
  ab open "$url"; ab wait 1500
  ab type "$SEL_USER_INPUT" "$TEST_USER"
  ab type "$SEL_PASS_INPUT" "$TEST_PASS"
  ab click "$SEL_SUBMIT_BTN"; ab wait 3000; screenshot "04-login-success"
  assert_eval "登录后离开登录页（URL 变化或出现成功标识）" \
    "(location.pathname !== '${LOGIN_PATH}' || document.querySelector('${SEL_SUCCESS_MSG}')) ? 'ok' : 'still-login'"

  log "[5/5] 登录态证据：仅确认页面可见元素，不读取 token/cookie"
  screenshot "05-after-login"
  pass "登录用例组完成"
}

case_form() {
  log "===== 用例组：表单校验 ====="
  local url="${TEST_BASE_URL}${FORM_PATH}"

  log "[1/4] 打开表单页"
  ab open "$url"; ab wait 2000; screenshot "06-form-page"

  log "[2/4] 空提交：必填校验"
  ab click "$SEL_SUBMIT_BTN"; ab wait 1000; screenshot "07-form-empty"
  assert_eval "空提交出现校验提示" "document.querySelector('${SEL_ERROR_MSG}') ? 'ok' : 'no-error'"

  log "[3/4] 非法格式（邮箱）"
  ab type "$SEL_FORM_INPUT" "not-an-email"
  ab click "$SEL_SUBMIT_BTN"; ab wait 1000; screenshot "08-form-bad-email"
  assert_eval "非法邮箱被拦截" "document.querySelector('${SEL_ERROR_MSG}') ? 'ok' : 'no-error'"

  log "[4/4] 合法提交"
  # 清空后填合法值（dry-run 下不执行，run 时用 JS 清空）
  if [[ "$MODE" == "run" ]]; then
    timeout 30 agent-browser --cdp "${CDP_PORT}" eval "document.querySelector('${SEL_FORM_INPUT}').value=''" >/dev/null 2>&1 || true
  fi
  ab type "$SEL_FORM_INPUT" "acceptance@example.com"
  ab click "$SEL_SUBMIT_BTN"; ab wait 2000; screenshot "09-form-success"
  assert_eval "合法提交成功" "document.querySelector('${SEL_SUCCESS_MSG}') ? 'ok' : 'no-success'"
  pass "表单用例组完成"
}

case_error_state() {
  log "===== 用例组：错误状态 ====="
  local url="${TEST_BASE_URL}${ERROR_PATH}"

  log "[1/2] 访问不存在页面：应出现 404 / 错误页"
  ab open "$url"; ab wait 2000; screenshot "10-error-404"
  assert_eval "错误状态页可见" "document.body.innerText.length > 0 ? 'ok' : 'blank'"

  log "[2/2] 错误状态下不暴露敏感堆栈（页面文本不含 password/token 字样）"
  if [[ "$MODE" == "dry-run" ]]; then
    echo "    [dry-run] 断言: 错误页不泄露敏感字段" | tee -a "$LOG_FILE"
    pass "错误页不泄露敏感字段 (dry-run)"
  else
    local body
    body="$(timeout 30 agent-browser --cdp "${CDP_PORT}" eval 'document.body.innerText.substring(0,4000)' 2>&1)" || true
    if echo "$body" | grep -qiE 'password|token|secret|stack trace|sqlstate'; then
      fail "错误页疑似泄露敏感信息"
    else
      pass "错误页未发现明显敏感信息"
    fi
  fi
  pass "错误状态用例组完成"
}

# ---------- 主流程 ----------
main() {
  mkdir -p "$(dirname "$LOG_FILE")"
  log "验收流程开始 run_id=${RUN_ID} 模式=${MODE}"
  preflight

  case "$CASE_FILTER" in
    ""|all)
      case_login; case_form; case_error_state ;;
    login) case_login ;;
    form)  case_form ;;
    error) case_error_state ;;
    *) log "未知用例: ${CASE_FILTER}（可选: login/form/error/all）"; exit 1 ;;
  esac

  summary
  [[ $FAIL_COUNT -eq 0 ]]
}

main "$@"
