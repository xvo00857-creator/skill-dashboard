#!/usr/bin/env bash
# =============================================================================
# check_creative.sh — 广告素材文件规格校验工具
# 零依赖：macOS 使用自带 sips 读取图片尺寸；file 命令识别格式
# 用法：bash check_creative.sh <素材目录或文件>
# 示例：bash check_creative.sh ./assets/
# =============================================================================
set -euo pipefail

TARGET="${1:?用法: bash check_creative.sh <素材目录或文件>}"

# 规格表：平台|宽x高|最大字节|允许格式
SPECS=(
  "微信朋友圈单图|800x800|314572|JPEG|PNG"
  "微信朋友圈卡片|800x450|314572|JPEG|PNG"
  "抖音竖版|1080x1920|524288|JPEG|PNG"
  "抖音横版|1280x720|524288|JPEG|PNG"
  "小红书竖版|1080x1440|524288|JPEG|PNG"
  "B站信息流|1146x717|314572|JPEG|PNG"
  "通用横幅728x90|728x90|157286|JPEG|PNG|GIF"
  "通用矩形300x250|300x250|157286|JPEG|PNG"
)

PASS=0; FAIL=0

check_image() {
  local f="$1"
  local fname
  fname="$(basename "$f")"
  local fsize
  fsize=$(stat -f%z "$f" 2>/dev/null || stat -c%s "$f" 2>/dev/null)
  local ftype
  ftype=$(file -b "$f")

  # 获取尺寸（macOS sips）
  local dims wh w h
  if dims=$(sips -g pixelWidth -g pixelHeight "$f" 2>/dev/null); then
    w=$(echo "$dims" | awk '/pixelWidth/{print $2}')
    h=$(echo "$dims" | awk '/pixelHeight/{print $2}')
    wh="${w}x${h}"
  else
    wh="未知"
  fi

  local matched=false
  for spec in "${SPECS[@]}"; do
    IFS='|' read -r sname sdim smax sfmt <<< "$spec"
    if [ "$wh" = "$sdim" ]; then
      matched=true
      if [ "$fsize" -le "$smax" ]; then
        echo "[PASS] ${fname} — 尺寸 ${wh} 匹配「${sname}」，大小 $((fsize/1024))KB ≤ $((smax/1024))KB"
        PASS=$((PASS+1))
      else
        echo "[FAIL] ${fname} — 尺寸 ${wh} 匹配「${sname}」，但大小 $((fsize/1024))KB > $((smax/1024))KB"
        FAIL=$((FAIL+1))
      fi
      break
    fi
  done

  if ! $matched; then
    echo "[WARN] ${fname} — 尺寸 ${wh} 不匹配任何已知规格（大小 $((fsize/1024))KB，类型: ${ftype}）"
    FAIL=$((FAIL+1))
  fi
}

echo "========================================"
echo " 广告素材文件规格校验"
echo "========================================"
echo "目标: $TARGET"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "----------------------------------------"

if [ -d "$TARGET" ]; then
  while read -r f; do
    check_image "$f"
  done < <(find "$TARGET" -type f \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' -o -iname '*.gif' \))
elif [ -f "$TARGET" ]; then
  check_image "$TARGET"
else
  echo "[FAIL] 路径不存在: $TARGET"
  exit 2
fi

echo "----------------------------------------"
echo "结果: 通过 ${PASS}，失败/警告 ${FAIL}"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
