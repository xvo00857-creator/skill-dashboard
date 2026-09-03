#!/usr/bin/env bash
# notify_team.sh — 团队工作流通知示例
#
# 场景：某个重复的团队工作流（如 CI 构建失败、部署审批、数据任务卡住）
# 需要在 Telegram 上通知负责人，并轮询其回复以决定是否继续。
# 本脚本演示如何调用 sentinel_setup.sh 完成完整流程：
#   store_token → detect_chat → configure → notify → 轮询回复
#
# 用法：
#   ./notify_team.sh --mock "构建 #1234 失败，请回复 continue 重试或 abort 终止"
#   SENTINEL_CONFIG_DIR=~/.sentinel ./notify_team.sh "部署审批：是否发布 v1.2.3？"
#
# 依赖：与 sentinel_setup.sh 相同（bash/curl/python3），不新增任何依赖。

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SENTINEL="$SCRIPT_DIR/../sentinel_setup.sh"

MOCK_FLAG=()
MOCK_CFG_DIR=""
WAIT_TIMEOUT=120  # 等待回复的秒数
POLL_INTERVAL=5

usage() {
  cat <<EOF
用法: $(basename "$0") [--mock] [--timeout 秒] <通知内容>
  --mock        使用本地模拟 Telegram API（自动完成配置，无需真实账号）
  --timeout N   等待回复超时秒数（默认 120）
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    --mock) MOCK_FLAG=(--mock); shift;;
    --timeout) WAIT_TIMEOUT="$2"; shift 2;;
    -h|--help) usage; exit 0;;
    *) break;;
  esac
done

MESSAGE="${1:-}"
[ -n "$MESSAGE" ] || { usage; exit 2; }

# 模拟模式下使用固定配置目录，让多次调用间状态（token、chat_id、模拟服务器状态）持久化
if [ ${#MOCK_FLAG[@]} -gt 0 ]; then
  MOCK_CFG_DIR="$(mktemp -d -t sentinel_example.XXXXXX)"
  trap 'rm -rf "$MOCK_CFG_DIR"' EXIT
  MOCK_FLAG=(--mock --config-dir "$MOCK_CFG_DIR")
fi

echo "=== 团队工作流通知 ==="
echo "通知内容: $MESSAGE"

# 1. 检查配置状态
echo "--- 检查 Sentinel 配置 ---"
"$SENTINEL" "${MOCK_FLAG[@]}" status

# 2. 模拟模式下自动完成一次性配置（真实模式需人工按 SKILL.md 步骤操作）
if [ ${#MOCK_FLAG[@]} -gt 0 ]; then
  echo "--- 模拟模式：自动完成 store_token / detect_chat / configure ---"
  # store_token：--mock 下自动注入模拟 token
  "$SENTINEL" "${MOCK_FLAG[@]}" store_token
  # detect_chat：模拟服务器返回一条 /start 消息
  detect_out=$("$SENTINEL" "${MOCK_FLAG[@]}" detect_chat)
  echo "$detect_out"
  chat_id=$(printf '%s\n' "$detect_out" | sed -n 's/^CHAT_ID=//p')
  sender_id=$(printf '%s\n' "$detect_out" | sed -n 's/^SENDER_ID=//p')
  # configure：将检测到的用户加入白名单
  "$SENTINEL" "${MOCK_FLAG[@]}" configure --chat-id "$chat_id" --allowlist "$sender_id"
fi

# 3. 发送通知
echo "--- 发送通知 ---"
"$SENTINEL" "${MOCK_FLAG[@]}" notify --text "🔔 工作流通知: $MESSAGE

请回复指令：
• continue — 继续执行
• abort — 终止流程
• status — 查看当前状态"

# 4. 轮询回复（模拟 Sentinel 的长轮询行为）
#    注意：真实场景中可由 sentinel_setup.sh listen 长驻进程处理，
#    这里用短轮询演示"等待人工回复"这一重复工作流。
echo "--- 等待回复（超时 ${WAIT_TIMEOUT}s）---"
elapsed=0
while [ "$elapsed" -lt "$WAIT_TIMEOUT" ]; do
  # detect_chat 返回最近一条消息；模拟模式下首次 /start 已消费，后续返回 PENDING
  if reply=$("$SENTINEL" "${MOCK_FLAG[@]}" detect_chat 2>/dev/null); then
    text=$(printf '%s\n' "$reply" | sed -n 's/^TEXT=//p')
    sender=$(printf '%s\n' "$reply" | sed -n 's/^SENDER_ID=//p')
    case "$text" in
      continue)
        echo "✅ 收到 $sender 的回复: continue，继续执行工作流"
        exit 0;;
      abort)
        echo "🛑 收到 $sender 的回复: abort，终止工作流"
        exit 1;;
      status)
        echo "ℹ️  收到 $sender 的状态查询，当前状态：等待中"
        "$SENTINEL" "${MOCK_FLAG[@]}" notify --text "当前状态：工作流等待你的指令中（已等待 ${elapsed}s）"
        ;;
      /start|"")
        : ;;  # 忽略初始 /start
      *)
        echo "❓ 收到未知指令: ${text}（期望 continue/abort/status）"
        ;;
    esac
  fi
  sleep "$POLL_INTERVAL"
  elapsed=$((elapsed + POLL_INTERVAL))
done

echo "⏰ 等待回复超时（${WAIT_TIMEOUT}s），按默认策略继续"
exit 0
