#!/usr/bin/env bash
# verify-project.sh —— 在 NanoClaw 项目根目录执行，验证 Linear 渠道集成是否就位
#
# 用法：
#   bash verify-project.sh              # 在 NanoClaw 项目根目录运行
#   bash verify-project.sh /path/to/nanoclaw
#
# 对应 SKILL.md Apply 步骤 1-4 的可重复验证：
#   1. 适配器文件存在（src/channels/linear.ts、linear-registration.test.ts）
#   2. barrel 注册（src/channels/index.ts 含 import './linear.js'）
#   3. 依赖锁定（@chat-adapter/linear@4.29.0）
#   4. 构建与注册测试通过
set -euo pipefail

ROOT="${1:-.}"
cd "$ROOT"

pass=0; fail=0
ok()   { echo "  ✓ $1"; pass=$((pass+1)); }
no()   { echo "  ✗ $1"; fail=$((fail+1)); }

echo "=== Linear 渠道项目集成验证: $(pwd) ==="
echo

# 1. 适配器文件
if [ -f src/channels/linear.ts ]; then
  ok "src/channels/linear.ts 存在"
else
  no "src/channels/linear.ts 缺失（应从 channels 分支复制）"
fi
if [ -f src/channels/linear-registration.test.ts ]; then
  ok "src/channels/linear-registration.test.ts 存在"
else
  no "src/channels/linear-registration.test.ts 缺失"
fi

# 2. barrel 注册
if [ -f src/channels/index.ts ] && grep -q "import './linear.js'" src/channels/index.ts; then
  ok "src/channels/index.ts 已注册 import './linear.js'"
else
  no "src/channels/index.ts 缺少 import './linear.js' 注册行"
fi

# 3. 依赖版本
if [ -f package.json ]; then
  if grep -q '"@chat-adapter/linear"' package.json; then
    VER=$(node -e "const p=require('./package.json');console.log((p.dependencies||{})['@chat-adapter/linear']||(p.devDependencies||{})['@chat-adapter/linear']||'')")
    if [ "$VER" = "4.29.0" ]; then
      ok "@chat-adapter/linear 锁定为 4.29.0"
    else
      no "@chat-adapter/linear 版本为 $VER，Skill 要求精确锁定 4.29.0"
    fi
  else
    no "package.json 未声明 @chat-adapter/linear 依赖"
  fi
else
  no "package.json 不存在（当前目录不是 NanoClaw 项目根目录）"
fi

# 4. 构建与测试（仅在项目存在时执行）
if [ -f package.json ] && [ -d node_modules ]; then
  echo
  echo "--- pnpm run build ---"
  if pnpm run build; then
    ok "构建通过"
  else
    no "构建失败"
  fi
  echo
  echo "--- vitest linear-registration ---"
  if pnpm exec vitest run src/channels/linear-registration.test.ts; then
    ok "注册测试通过"
  else
    no "注册测试失败"
  fi
else
  echo
  echo "  ⊙ 跳过构建/测试（无 node_modules，请先 pnpm install）"
fi

echo
echo "结果: $pass 通过, $fail 失败"
exit $fail
