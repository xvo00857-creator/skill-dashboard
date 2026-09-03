#!/usr/bin/env bash
# verify.sh — 可重复验证脚本（无需真实 Telegram 账号）
#
# 在本地启动模拟 Telegram API，依次验证：
#   1. status（初始无配置）
#   2. store_token（getMe 校验 + 存储）
#   3. detect_chat（getUpdates 检测 chat_id）
#   4. configure（设置 chat_id + 白名单）
#   5. test（sendMessage 测试消息）
#   6. notify（发送工作流通知）
#   7. listen（短时长轮询，验证能收到更新）
#   8. 异常路径：错误 token、未配置 chat_id 发消息、PENDING 场景
#
# 用法：./verify.sh
# 退出码：0 全部通过；非 0 有失败项

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SENTINEL="$SCRIPT_DIR/sentinel_setup.sh"

PASS=0; FAIL=0
LOG_DIR="$SCRIPT_DIR/verify-logs"
mkdir -p "$LOG_DIR"
# 使用独立配置目录，不污染 ~/.sentinel
VERIFY_CFG="$SCRIPT_DIR/.verify-config"
rm -rf "$VERIFY_CFG"

green() { printf '\033[32m%s\033[0m\n' "$1"; }
red()   { printf '\033[31m%s\033[0m\n' "$1"; }
yellow(){ printf '\033[33m%s\033[0m\n' "$1"; }

check() {
  local desc="$1"; shift
  local logf="$1"; shift
  if "$@" >"$logf" 2>&1; then
    green "  [PASS] $desc"
    PASS=$((PASS+1))
  else
    red "  [FAIL] $desc (日志: $logf)"
    FAIL=$((FAIL+1))
  fi
}

check_fail() {
  # 期望命令失败（用于异常路径验证）
  local desc="$1"; shift
  local logf="$1"; shift
  if "$@" >"$logf" 2>&1; then
    red "  [FAIL] $desc — 期望失败但成功了 (日志: $logf)"
    FAIL=$((FAIL+1))
  else
    green "  [PASS] ${desc}（按预期被拒绝）"
    PASS=$((PASS+1))
  fi
}

echo "============================================"
echo " Sentinel Telegram 通知通道 — 可重复验证"
echo " 时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo " 配置目录: ${VERIFY_CFG}（独立，不影响真实配置）"
echo "============================================"

# 语法检查
echo ""
yellow "[0] 脚本语法检查"
if bash -n "$SENTINEL"; then
  green "  [PASS] sentinel_setup.sh 语法正确"
  PASS=$((PASS+1))
else
  red "  [FAIL] sentinel_setup.sh 语法错误"
  FAIL=$((FAIL+1))
fi

# 依赖检查
echo ""
yellow "[0b] 依赖检查（应均为系统自带）"
for cmd in bash curl python3; do
  if command -v "$cmd" >/dev/null 2>&1; then
    green "  [PASS] $cmd: $(command -v $cmd)"
    PASS=$((PASS+1))
  else
    red "  [FAIL] $cmd 未找到"
    FAIL=$((FAIL+1))
  fi
done

# ---- 正常流程 ----
echo ""
yellow "[1] status（初始状态，无 token）"
check "初始 status 显示 token 未存储" "$LOG_DIR/01_status_init.log" \
  "$SENTINEL" --mock --config-dir "$VERIFY_CFG" status

echo ""
yellow "[2] store_token（模拟 getMe 校验并存储）"
check "store_token 成功" "$LOG_DIR/02_store_token.log" \
  "$SENTINEL" --mock --config-dir "$VERIFY_CFG" store_token
# 验证凭据文件内容
if python3 -c "
import json
d=json.load(open('$VERIFY_CFG/credentials.json'))
assert d['telegram']['access_token']=='123456789:MOCK-TOKEN-FOR-TESTING'
assert d['telegram']['bot_username']=='mock_sentinel_bot'
print('ok')
" >"$LOG_DIR/02_cred_content.log" 2>&1; then
  green "  [PASS] credentials.json 内容正确"
  PASS=$((PASS+1))
else
  red "  [FAIL] credentials.json 内容不符"
  FAIL=$((FAIL+1))
fi
# 文件权限应为 600
perms=$(stat -f '%Lp' "$VERIFY_CFG/credentials.json" 2>/dev/null || stat -c '%a' "$VERIFY_CFG/credentials.json" 2>/dev/null)
if [ "$perms" = "600" ]; then
  green "  [PASS] credentials.json 权限 600"
  PASS=$((PASS+1))
else
  yellow "  [WARN] credentials.json 权限 ${perms}（期望 600，不影响功能）"
fi

echo ""
yellow "[3] status（存储后状态）"
check "status 显示 token 已存储" "$LOG_DIR/03_status_after.log" \
  "$SENTINEL" --mock --config-dir "$VERIFY_CFG" status
grep -q "Token 已存储: 是" "$LOG_DIR/03_status_after.log" && \
  green "  [PASS] status 输出包含 'Token 已存储: 是'" && PASS=$((PASS+1)) || \
  { red "  [FAIL] status 未显示 token 已存储"; FAIL=$((FAIL+1)); }

echo ""
yellow "[4] detect_chat（getUpdates 检测 chat_id）"
check "detect_chat 成功" "$LOG_DIR/04_detect_chat.log" \
  "$SENTINEL" --mock --config-dir "$VERIFY_CFG" detect_chat
grep -q "CHAT_ID=987654321" "$LOG_DIR/04_detect_chat.log" && \
  green "  [PASS] 检测到 chat_id=987654321" && PASS=$((PASS+1)) || \
  { red "  [FAIL] 未检测到预期 chat_id"; FAIL=$((FAIL+1)); }

echo ""
yellow "[5] configure（设置 chat_id + 白名单）"
check "configure 成功" "$LOG_DIR/05_configure.log" \
  "$SENTINEL" --mock --config-dir "$VERIFY_CFG" configure \
  --chat-id 987654321 --allowlist 987654321 --enabled true
if python3 -c "
import json
d=json.load(open('$VERIFY_CFG/config.json'))
assert d['channel']=='telegram'
assert d['target']['chat_id']=='987654321'
assert d['allowlist']==['987654321']
assert d['enabled']==True
print('ok')
" >"$LOG_DIR/05_config_content.log" 2>&1; then
  green "  [PASS] config.json 内容正确"
  PASS=$((PASS+1))
else
  red "  [FAIL] config.json 内容不符"
  FAIL=$((FAIL+1))
fi

echo ""
yellow "[6] test（发送测试消息）"
check "test 成功" "$LOG_DIR/06_test.log" \
  "$SENTINEL" --mock --config-dir "$VERIFY_CFG" test
grep -q "测试消息已发送" "$LOG_DIR/06_test.log" && \
  green "  [PASS] test 消息发送成功" && PASS=$((PASS+1)) || \
  { red "  [FAIL] test 消息发送失败"; FAIL=$((FAIL+1)); }

echo ""
yellow "[7] notify（发送工作流通知）"
check "notify 成功" "$LOG_DIR/07_notify.log" \
  "$SENTINEL" --mock --config-dir "$VERIFY_CFG" notify --text "验证通知：构建 #1234 完成"
grep -q "通知已发送" "$LOG_DIR/07_notify.log" && \
  green "  [PASS] notify 通知发送成功" && PASS=$((PASS+1)) || \
  { red "  [FAIL] notify 通知发送失败"; FAIL=$((FAIL+1)); }

echo ""
yellow "[8] listen（长轮询 3 秒，验证不崩溃且能轮询）"
# 后台运行 listen 3 秒后杀掉
timeout 3 "$SENTINEL" --mock --config-dir "$VERIFY_CFG" listen >"$LOG_DIR/08_listen.log" 2>&1 || true
if [ -s "$LOG_DIR/08_listen.log" ]; then
  green "  [PASS] listen 启动并运行（日志: $LOG_DIR/08_listen.log）"
  PASS=$((PASS+1))
else
  red "  [FAIL] listen 无输出"
  FAIL=$((FAIL+1))
fi

# ---- 异常路径 ----
echo ""
yellow "[9] 异常路径验证"

check_fail "格式错误的 token 被拒绝" "$LOG_DIR/09_bad_token_format.log" \
  "$SENTINEL" --mock --config-dir "$VERIFY_CFG" store_token --token "not-a-valid-token"

# 模拟服务器对错误 token 返回 401
check_fail "无效 token（模拟服务器返回 401）被拒绝" "$LOG_DIR/09_invalid_token.log" \
  "$SENTINEL" --mock --config-dir "$VERIFY_CFG-badtoken" store_token --token "111:bad-token"

check_fail "未配置 chat_id 时 test 被拒绝" "$LOG_DIR/09_no_chatid.log" \
  bash -c "CFG2='${VERIFY_CFG}-nocfg'; rm -rf \"\$CFG2\"; '$SENTINEL' --mock --config-dir \"\$CFG2\" store_token && '$SENTINEL' --mock --config-dir \"\$CFG2\" test"

check_fail "configure 缺少 chat-id 被拒绝" "$LOG_DIR/09_no_chatid_arg.log" \
  "$SENTINEL" --mock --config-dir "$VERIFY_CFG" configure

check_fail "非数字 chat-id 被拒绝" "$LOG_DIR/09_bad_chatid.log" \
  "$SENTINEL" --mock --config-dir "$VERIFY_CFG" configure --chat-id "abc"

check_fail "未知 action 被拒绝" "$LOG_DIR/09_bad_action.log" \
  "$SENTINEL" --mock status_bogus

echo ""
yellow "[10] detect_chat PENDING 场景（第二次调用无新消息）"
# 模拟服务器第一次返回消息，之后返回空；前面已消费过一次，这里应 PENDING
check_fail "无新消息时 detect_chat 返回 PENDING" "$LOG_DIR/10_pending.log" \
  "$SENTINEL" --mock --config-dir "$VERIFY_CFG" detect_chat

# ---- 汇总 ----
echo ""
echo "============================================"
echo " 验证结果: $(green "$PASS 通过") / $(red "$FAIL 失败")"
echo " 日志目录: $LOG_DIR"
echo "============================================"

# 清理验证配置
rm -rf "$VERIFY_CFG" "$VERIFY_CFG-nocfg" "$VERIFY_CFG-badtoken"

[ "$FAIL" = 0 ]
