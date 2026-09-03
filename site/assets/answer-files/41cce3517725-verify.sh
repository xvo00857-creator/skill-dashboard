#!/usr/bin/env bash
# baoyu-skill 最小可用组合验证脚本
# 用途：针对"整理研究资料并生成汇报"需求，验证最小技能组合的 CLI 可加载性与端到端功能
# 用法：bash verify.sh
# 约束：不调用外部账号/付费 API；不实际抓取网页；端到端测试仅用本地临时文件
set -u

ROOT="$(cd "$(dirname "$0")" && pwd)"
PASS=0; FAIL=0
ok()   { echo "  [PASS] $1"; PASS=$((PASS+1)); }
bad()  { echo "  [FAIL] $1"; FAIL=$((FAIL+1)); }
section() { echo; echo "========== $1 =========="; }

# 0. 运行时检查
section "0. 运行时环境"
if command -v bun >/dev/null 2>&1; then
  ok "bun $(bun --version)"
else
  bad "bun 未安装（必需运行时）"
fi
if [ -d "/Applications/Google Chrome.app" ]; then
  ok "Google Chrome 已安装（url-to-markdown 的 CDP 后端需要）"
else
  bad "Google Chrome 未在默认路径找到（url-to-markdown 需要）"
fi

# 1. 依赖安装检查
section "1. skill 自带依赖检查"
check_deps() {
  local dir="$1" name="$2"
  if [ -d "$dir/node_modules" ]; then
    ok "$name 依赖已安装（$dir/node_modules）"
  else
    bad "$name 依赖未安装，请在 $dir 执行 bun install"
  fi
}
check_deps "$ROOT/skills/baoyu-url-to-markdown/scripts" "baoyu-url-to-markdown"
check_deps "$ROOT/skills/baoyu-format-markdown/scripts"  "baoyu-format-markdown"
check_deps "$ROOT/skills/baoyu-translate/scripts"        "baoyu-translate（可选）"
if [ -d "$ROOT/node_modules/pptxgenjs" ] && [ -d "$ROOT/node_modules/pdf-lib" ] && [ -d "$ROOT/node_modules/sharp" ]; then
  ok "根目录依赖已安装（pptxgenjs/pdf-lib/sharp，供 slide-deck 合并与 diagram 转 PNG）"
else
  bad "根目录依赖未安装，请在 $ROOT 执行 bun install"
fi

# 2. CLI 可加载性检查（--help / 无参用法，不触发网络或账号）
section "2. CLI 可加载性"
TMP="$ROOT/verify-tmp"; mkdir -p "$TMP/slides"

if "$ROOT/skills/baoyu-url-to-markdown/scripts/baoyu-fetch" 2>&1 | grep -q "baoyu-fetch"; then
  ok "baoyu-fetch（url-to-markdown）CLI 可加载"
else
  bad "baoyu-fetch CLI 加载失败"
fi

if bun "$ROOT/skills/baoyu-format-markdown/scripts/main.ts" 2>&1 | grep -q "Usage"; then
  ok "format-markdown CLI 可加载"
else
  bad "format-markdown CLI 加载失败"
fi

if bun "$ROOT/skills/baoyu-slide-deck/scripts/merge-to-pptx.ts" 2>&1 | grep -q "Usage"; then
  ok "slide-deck merge-to-pptx CLI 可加载"
else
  bad "slide-deck merge-to-pptx CLI 加载失败"
fi

if bun "$ROOT/skills/baoyu-slide-deck/scripts/merge-to-pdf.ts" 2>&1 | grep -q "Usage"; then
  ok "slide-deck merge-to-pdf CLI 可加载"
else
  bad "slide-deck merge-to-pdf CLI 加载失败"
fi

if bun "$ROOT/skills/baoyu-diagram/scripts/main.ts" --help 2>&1 | grep -q "Usage"; then
  ok "diagram CLI 可加载"
else
  bad "diagram CLI 加载失败"
fi

if bun "$ROOT/skills/baoyu-image-gen/scripts/main.ts" --help 2>&1 | grep -q "Usage"; then
  ok "image-gen CLI 可加载（图片生成后端，需 API key 才能实际出图）"
else
  bad "image-gen CLI 加载失败"
fi

if bun "$ROOT/skills/baoyu-translate/scripts/main.ts" --help 2>&1 | grep -q "Usage"; then
  ok "translate CLI 可加载（可选）"
else
  bad "translate CLI 加载失败"
fi

# 3. 端到端功能测试（纯本地，无网络无账号）
section "3. 端到端功能测试"

# 3a. format-markdown（--no-spacing 避免 npx 自动拉取 autocorrect-node）
cat > "$TMP/note.md" <<'EOF'
---
title: 测试笔记
---
# 测试笔记
中文English混排。

- 第一项
**强调**
EOF
if bun "$ROOT/skills/baoyu-format-markdown/scripts/main.ts" "$TMP/note.md" --no-spacing 2>&1 | grep -q "Formatted"; then
  ok "format-markdown 格式化成功（--no-spacing）"
else
  bad "format-markdown 格式化失败"
fi

# 3b. diagram SVG -> PNG
cat > "$TMP/test.svg" <<'EOF'
<svg xmlns="http://www.w3.org/2000/svg" width="400" height="200" viewBox="0 0 400 200">
  <rect width="400" height="200" fill="#0f172a"/>
  <text x="200" y="110" font-family="sans-serif" font-size="28" fill="#e2e8f0" text-anchor="middle">test</text>
</svg>
EOF
if bun "$ROOT/skills/baoyu-diagram/scripts/main.ts" "$TMP/test.svg" -s 2 2>&1 | grep -q "800×400"; then
  ok "diagram SVG→@2x PNG 成功（800×400）"
else
  bad "diagram SVG→PNG 失败"
fi

# 3c. slide-deck 合并：用 sharp 生成两张符合 NN-slide-*.png 命名的幻灯片
bun -e '
import sharp from "sharp";
await sharp({create:{width:1280,height:720,channels:3,background:{r:30,g:58,b:138}}}).png().toFile("'$TMP'/slides/01-slide-cover.png");
await sharp({create:{width:1280,height:720,channels:3,background:{r:15,g:23,b:42}}}).png().toFile("'$TMP'/slides/02-slide-content.png");
' 2>/dev/null
rm -f "$TMP/slides/slides.pptx" "$TMP/slides/slides.pdf"
if bun "$ROOT/skills/baoyu-slide-deck/scripts/merge-to-pptx.ts" "$TMP/slides" 2>&1 | grep -q "Created"; then
  ok "slide-deck 合并 PPTX 成功"
else
  bad "slide-deck 合并 PPTX 失败"
fi
if bun "$ROOT/skills/baoyu-slide-deck/scripts/merge-to-pdf.ts" "$TMP/slides" 2>&1 | grep -q "Created"; then
  ok "slide-deck 合并 PDF 成功"
else
  bad "slide-deck 合并 PDF 失败"
fi

# 4. 汇总
section "验证结果"
echo "通过: $PASS  失败: $FAIL"
if [ "$FAIL" -eq 0 ]; then
  echo "结论：最小可用组合（url-to-markdown + format-markdown + slide-deck）CLI 与本地功能验证全部通过。"
  echo "注意：url-to-markdown 实际抓取需 Chrome（已装）；slide-deck 出图需图片生成后端（见报告说明）。"
  exit 0
else
  echo "结论：存在失败项，请按上述提示处理。"
  exit 1
fi
