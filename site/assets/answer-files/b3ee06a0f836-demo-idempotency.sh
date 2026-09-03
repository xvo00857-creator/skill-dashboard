#!/usr/bin/env bash
# demo-idempotency.sh
# 在隔离临时目录中演示 SKILL.md 步骤2(append) 与步骤4(ESM patch) 的幂等性。
# 不访问网络、不触碰任何外部资源；所有输入文件均为本脚本构造的最小样例，
# 仅用于验证幂等逻辑，不是 NanoClaw 真实源码。
set -euo pipefail

WORK="$(mktemp -d)/add-matrix-demo"
mkdir -p "$WORK/src/channels"
PNPM_DIR="$WORK/node_modules/.pnpm/@beeper+chat-adapter-matrix@0.2.0/node_modules/@beeper/chat-adapter-matrix/dist"
mkdir -p "$PNPM_DIR"

echo "沙箱目录: $WORK"
echo

# ---- 样例1: channel barrel（最小占位内容）----
cat > "$WORK/src/channels/index.ts" <<'EOF'
// channel barrel - 最小样例
export const registry = new Map<string, unknown>();
EOF

# ---- 样例2: 模拟 adapter dist，含缺少 .js 的 matrix-js-sdk 导入 ----
cat > "$PNPM_DIR/index.js" <<'EOF'
import { MatrixClient } from "matrix-js-sdk/lib/client";
import { createClient } from "matrix-js-sdk/lib/matrix";
export function register() { return { MatrixClient, createClient }; }
EOF

echo "============================================================"
echo "演示 A: 步骤2 nc:append —— import './matrix.js';"
echo "============================================================"
barrel="$WORK/src/channels/index.ts"
append_once() {
  if grep -qxF "import './matrix.js';" "$barrel"; then
    echo "  -> barrel 已包含 import 行，跳过（幂等）"
  else
    printf "\nimport './matrix.js';\n" >> "$barrel"
    echo "  -> 已追加 import './matrix.js';"
  fi
}
echo "--- 初始 barrel ---"; cat "$barrel"
echo "--- 第1次执行 ---"; append_once
echo "--- 第2次执行（应跳过）---"; append_once
echo "--- 最终 barrel ---"; cat "$barrel"
echo

echo "============================================================"
echo "演示 B: 步骤4 nc:run —— 为 matrix-js-sdk/lib 导入补 .js"
echo "============================================================"
dist="$PNPM_DIR/index.js"
patch_once() {
  node -e '
    const fs=require("fs"),path=require("path");
    const root=process.argv[1];
    const dir=fs.readdirSync(root).find(d=>d.startsWith("@beeper+chat-adapter-matrix@"));
    const f=path.join(root,dir,"node_modules/@beeper/chat-adapter-matrix/dist/index.js");
    const before=fs.readFileSync(f,"utf8");
    const after=before.replace(/from "(matrix-js-sdk\/lib\/[^"]+?)(?<!\.js)"/g,"from \"$1.js\"");
    if(before===after){console.log("  -> 已修补过，无需改动（幂等）");process.exit(0);}
    fs.writeFileSync(f,after);console.log("  -> Patched（已补 .js）");
  ' "$WORK/node_modules/.pnpm"
}
echo "--- 初始 dist ---"; cat "$dist"
echo "--- 第1次执行 ---"; patch_once
echo "--- 第2次执行（应跳过）---"; patch_once
echo "--- 最终 dist ---"; cat "$dist"
echo
echo "============================================================"
echo "演示 C: 预检对'有 git 但无 channels 分支'目录的反应"
echo "============================================================"
git init -q "$WORK/repo-no-branch"
( cd "$WORK/repo-no-branch" && git config user.email t@t && git config user.name t && git commit --allow-empty -q -m init )
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$SCRIPT_DIR/apply-matrix-channel.sh" --repo "$WORK/repo-no-branch" || true
echo
echo "沙箱保留在: ${WORK}（可自行核验；删除不影响任何外部资源）"
