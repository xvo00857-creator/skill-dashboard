#!/usr/bin/env bash
# ============================================================
# 便携咖啡机 30 秒竖屏产品短片 — HeyGen Video Agent 生成脚本
# 依据 create-video Skill: references/video-agent.md
#
# 使用前：
#   export HEYGEN_API_KEY="你的HeyGen API Key"
# 然后：
#   bash 04_生成视频.sh
#
# 成功后会打印 video_id，用 05_查询状态.sh <video_id> 查询并下载
# ============================================================
set -euo pipefail

# ---- 检查 API Key ----
if [ -z "${HEYGEN_API_KEY:-}" ]; then
  echo "错误：未设置 HEYGEN_API_KEY 环境变量。"
  echo "请先执行：export HEYGEN_API_KEY=\"你的Key\""
  exit 1
fi

# ---- 读取 prompt 文件 ----
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROMPT_FILE="$SCRIPT_DIR/01_优化prompt.txt"

if [ ! -f "$PROMPT_FILE" ]; then
  echo "错误：找不到 prompt 文件：$PROMPT_FILE"
  exit 1
fi

# 将 prompt 读入变量并转为 JSON 字符串（用 python3 安全转义）
PROMPT_JSON=$(python3 -c "
import json, sys
with open(sys.argv[1], 'r', encoding='utf-8') as f:
    print(json.dumps(f.read()))
" "$PROMPT_FILE")

# ---- 构造请求体 ----
# config 依据 video-agent.md：
#   duration_sec: 30（5-300 范围内）
#   orientation: "portrait"（竖屏 9:16，手机端优先）
# 不指定 avatar_id，让 Video Agent 自动选择匹配的中文女性形象
REQUEST_BODY=$(cat <<EOF
{
  "prompt": $PROMPT_JSON,
  "config": {
    "duration_sec": 30,
    "orientation": "portrait"
  }
}
EOF
)

echo "正在调用 HeyGen Video Agent API..."
echo "  接口：POST https://api.heygen.com/v1/video_agent/generate"
echo "  时长：30 秒"
echo "  画幅：portrait（竖屏 9:16）"
echo ""

# ---- 调用 API ----
RESPONSE=$(curl -s -X POST "https://api.heygen.com/v1/video_agent/generate" \
  -H "X-Api-Key: $HEYGEN_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$REQUEST_BODY")

echo "API 响应："
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo ""

# ---- 提取 video_id ----
VIDEO_ID=$(echo "$RESPONSE" | python3 -c "
import json, sys
data = json.load(sys.stdin)
if data.get('error'):
    print('ERROR:' + str(data['error']), file=sys.stderr)
    sys.exit(1)
vid = data.get('data', {}).get('video_id', '')
if not vid:
    print('ERROR: 响应中未找到 video_id', file=sys.stderr)
    sys.exit(1)
print(vid)
")

if [[ "$VIDEO_ID" == ERROR:* ]]; then
  echo "生成失败：${VIDEO_ID#ERROR:}"
  exit 1
fi

echo "============================================"
echo "视频生成已启动！"
echo "video_id: $VIDEO_ID"
echo ""
echo "视频通常需要 5-15 分钟生成。"
echo "查询状态并下载："
echo "  bash 05_查询状态.sh $VIDEO_ID"
echo "============================================"
