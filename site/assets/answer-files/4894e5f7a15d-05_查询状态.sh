#!/usr/bin/env bash
# ============================================================
# 查询 HeyGen 视频生成状态并下载
# 依据 create-video Skill: references/video-status.md
#
# 用法：
#   bash 05_查询状态.sh <video_id>          # 查询一次
#   bash 05_查询状态.sh <video_id> --wait   # 轮询直到完成并下载
# ============================================================
set -euo pipefail

if [ -z "${HEYGEN_API_KEY:-}" ]; then
  echo "错误：未设置 HEYGEN_API_KEY 环境变量。"
  echo "请先执行：export HEYGEN_API_KEY=\"你的Key\""
  exit 1
fi

if [ $# -lt 1 ]; then
  echo "用法：bash $0 <video_id> [--wait]"
  exit 1
fi

VIDEO_ID="$1"
WAIT_MODE="${2:-}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OUTPUT_DIR="$SCRIPT_DIR/output"
mkdir -p "$OUTPUT_DIR"

STATUS_URL="https://api.heygen.com/v2/videos/$VIDEO_ID"

check_status() {
  curl -s -X GET "$STATUS_URL" -H "X-Api-Key: $HEYGEN_API_KEY"
}

download_video() {
  local url="$1"
  local outfile="$2"
  echo "正在下载视频到：$outfile"
  curl -L -o "$outfile" "$url"
  echo "下载完成：$outfile"
  ls -lh "$outfile"
}

# 低性能兼容版本：用 ffmpeg 将 1080p 转 720p
transcode_720p() {
  local src="$1"
  local dst="${src%.mp4}_720p.mp4"
  if command -v ffmpeg &>/dev/null; then
    echo "正在生成 720p 低性能兼容版本..."
    ffmpeg -y -i "$src" -vf "scale=720:1280" -c:v libx264 -crf 26 -preset medium -c:a aac -b:a 96k "$dst" 2>/dev/null
    echo "720p 版本已生成：$dst"
    ls -lh "$dst"
  else
    echo "提示：未安装 ffmpeg，跳过 720p 转码。安装 ffmpeg 后可手动执行："
    echo "  ffmpeg -i \"$src\" -vf scale=720:1280 -c:v libx264 -crf 26 -c:a aac \"$dst\""
  fi
}

if [ "$WAIT_MODE" != "--wait" ]; then
  # 单次查询
  RESPONSE=$(check_status)
  echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"

  STATUS=$(echo "$RESPONSE" | python3 -c "import json,sys; print(json.load(sys.stdin).get('data',{}).get('status','unknown'))")
  if [ "$STATUS" = "completed" ]; then
    VIDEO_URL=$(echo "$RESPONSE" | python3 -c "import json,sys; print(json.load(sys.stdin)['data']['video_url'])")
    OUTFILE="$OUTPUT_DIR/portable-coffee-video.mp4"
    download_video "$VIDEO_URL" "$OUTFILE"
    transcode_720p "$OUTFILE"
  fi
  exit 0
fi

# 轮询模式
echo "开始轮询视频状态（每 10 秒一次，最多 20 分钟）..."
ELAPSED=0
MAX_WAIT=1200
INTERVAL=10

while [ $ELAPSED -lt $MAX_WAIT ]; do
  RESPONSE=$(check_status)
  STATUS=$(echo "$RESPONSE" | python3 -c "import json,sys; print(json.load(sys.stdin).get('data',{}).get('status','unknown'))")
  echo "[$(date +%H:%M:%S)] 已等待 ${ELAPSED}s — 状态：$STATUS"

  case "$STATUS" in
    completed)
      VIDEO_URL=$(echo "$RESPONSE" | python3 -c "import json,sys; print(json.load(sys.stdin)['data']['video_url'])")
      DURATION=$(echo "$RESPONSE" | python3 -c "import json,sys; print(json.load(sys.stdin)['data'].get('duration','?'))")
      echo "视频已完成！时长：${DURATION}s"
      OUTFILE="$OUTPUT_DIR/portable-coffee-video.mp4"
      download_video "$VIDEO_URL" "$OUTFILE"
      transcode_720p "$OUTFILE"
      echo ""
      echo "全部完成！"
      echo "  主版本（1080p）：$OUTFILE"
      echo "  字幕文件：$SCRIPT_DIR/02_字幕.srt"
      exit 0
      ;;
    failed)
      FAIL_MSG=$(echo "$RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin)['data']; print(d.get('failure_code',''), d.get('failure_message',''))")
      echo "视频生成失败：$FAIL_MSG"
      exit 1
      ;;
    pending|processing)
      sleep $INTERVAL
      ELAPSED=$((ELAPSED + INTERVAL))
      ;;
    *)
      echo "未知状态，5 秒后重试..."
      sleep 5
      ELAPSED=$((ELAPSED + 5))
      ;;
  esac
done

echo "超时：等待超过 ${MAX_WAIT}s，视频仍未完成。"
echo "video_id 已保存，可稍后再次运行本脚本查询：bash $0 $VIDEO_ID --wait"
exit 1
