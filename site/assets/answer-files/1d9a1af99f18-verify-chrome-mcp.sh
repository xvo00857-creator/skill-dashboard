#!/bin/bash
# chrome-mcp 连通性只读诊断脚本
# 依据 chrome-mcp-troubleshooting SKILL.md 的 Quick Diagnosis / Diagnostic Deep Dive
# 约束：只读，不安装依赖，不改文件，不杀进程，不重启 Chrome
# 用法：bash verify-chrome-mcp.sh

set -u
PASS=0; FAIL=0; WARN=0
ok(){   echo "[通过] $*"; PASS=$((PASS+1)); }
no(){   echo "[失败] $*"; FAIL=$((FAIL+1)); }
warn(){ echo "[警告] $*"; WARN=$((WARN+1)); }

echo "========== 1. 平台与环境 =========="
[ "$(uname)" = "Darwin" ] && ok "运行在 macOS（本 Skill 仅支持 macOS）" || no "非 macOS，本 Skill 不适用"
echo "TMPDIR=$TMPDIR"
echo "DARWIN_USER_TEMP_DIR=$(getconf DARWIN_USER_TEMP_DIR)"
[ -n "$TMPDIR" ] && ok "TMPDIR 已设置" || no "TMPDIR 未设置（Claude Code 可能找不到 socket）"

echo
echo "========== 2. Chrome 与 Claude 组件 =========="
[ -d "/Applications/Google Chrome.app" ] && ok "Chrome 已安装: $(defaults read /Applications/Google\ Chrome.app/Contents/Info.plist CFBundleShortVersionString 2>/dev/null)" || no "Chrome 未安装"
[ -d "/Applications/Claude.app" ] && { ok "Claude.app 已安装: $(defaults read /Applications/Claude.app/Contents/Info.plist CFBundleShortVersionString 2>/dev/null)"; } || warn "Claude.app 未安装"
[ -x "/Applications/Claude.app/Contents/Helpers/chrome-native-host" ] && ok "Claude.app native host helper 存在" || warn "Claude.app native host helper 不存在"
command -v claude >/dev/null 2>&1 && ok "claude CLI 存在: $(claude --version 2>&1 | head -1)" || no "claude CLI 不存在"

echo
echo "========== 3. native host 进程 =========="
NH=$(ps aux | grep chrome-native-host | grep -v grep)
if [ -n "$NH" ]; then
  echo "$NH"
  echo "$NH" | grep -q "\.local/share/claude/versions" && ok "运行的是 Claude Code native host" || warn "运行的不是 SKILL.md 描述的 Claude Code 版本目录 native host（可能是 npm 全局版或 Claude.app helper）"
else
  warn "当前没有 chrome-native-host 进程（未启动浏览器自动化，或扩展未连接）"
fi

echo
echo "========== 4. socket 文件 =========="
CC_SOCK="$(getconf DARWIN_USER_TEMP_DIR)/claude-mcp-browser-bridge-${USER}"
APP_SOCK_DIR="/tmp/claude-mcp-browser-bridge-${USER}"
if [ -e "$CC_SOCK" ]; then
  ls -la "$CC_SOCK"; ok "Claude Code 风格 socket 存在 (${CC_SOCK})"
else
  warn "Claude Code 风格 socket 不存在 (${CC_SOCK})"
fi
if [ -d "$APP_SOCK_DIR" ]; then
  ls -la "$APP_SOCK_DIR"; ok "Claude.app 风格 socket 目录存在 (${APP_SOCK_DIR})"
else
  warn "Claude.app 风格 socket 目录不存在 (${APP_SOCK_DIR})"
fi

echo
echo "========== 5. native messaging 配置 =========="
CFG_DIR="$HOME/Library/Application Support/Google/Chrome/NativeMessagingHosts"
APP_CFG="$CFG_DIR/com.anthropic.claude_browser_extension.json"
CC_CFG="$CFG_DIR/com.anthropic.claude_code_browser_extension.json"
for f in "$APP_CFG" "$CC_CFG" "$APP_CFG.disabled" "$CC_CFG.disabled"; do
  [ -e "$f" ] && { echo "存在: $f"; } || true
done
if [ -f "$APP_CFG" ] && [ -f "$CC_CFG" ]; then
  no "两个 native messaging 配置同时启用 → 冲突！必须禁用其一（SKILL.md 核心问题）"
elif [ -f "$APP_CFG" ] || [ -f "$CC_CFG" ]; then
  ok "只有一个 native messaging 配置启用"
else
  warn "没有任何 com.anthropic native messaging 配置（新版可能改用扩展自动注册/WebSocket bridge，或从未配置过）"
fi

echo
echo "========== 6. Chrome 扩展与 nativeMessaging 权限 =========="
python3 - <<'PY'
import json,os
p=os.path.expanduser("~/Library/Application Support/Google/Chrome/Default/Preferences")
try:
    d=json.load(open(p))
    exts=d.get("extensions",{}).get("settings",{})
    found=False
    for eid,v in exts.items():
        perms=v.get("permissions",[])
        m=v.get("manifest",{})
        name=m.get("name","?")
        if any("nativeMessaging" in str(x) for x in perms):
            found=True
            print(f"  [nativeMessaging] {eid} name={name} state={v.get('state')}")
    if not found:
        print("  没有任何扩展请求 nativeMessaging 权限（Claude Chrome 扩展未安装或未启用）")
except Exception as e:
    print("  读取 Preferences 失败:", e)
PY

echo
echo "========== 7. 自定义 wrapper =========="
WRAP="$HOME/.claude/chrome/chrome-native-host"
if [ -f "$WRAP" ]; then
  echo "wrapper 内容:"; cat "$WRAP"
  grep -q 'ls -t' "$WRAP" && ok "wrapper 使用动态版本查找" || warn "wrapper 可能硬编码了版本号，升级后易失效"
else
  warn "无自定义 wrapper（$WRAP 不存在）"
fi

echo
echo "========== 8. Claude Code chrome 集成开关 =========="
if grep -q '"env"' "$HOME/.claude/settings.json" 2>/dev/null; then
  python3 - <<'PY'
import json,os
for f in [os.path.expanduser("~/.claude/settings.json")]:
    try:
        d=json.load(open(f))
        env=d.get("env",{})
        if env.get("CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC")=="1":
            print("  [警告] CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1，可能阻止 chrome bridge 联网")
        for k in env:
            if "CHROME" in k.upper(): print(f"  env {k}={env[k]}")
    except Exception as e: print("  读取失败:",e)
PY
fi
claude --help 2>&1 | grep -q -- "--chrome" && echo "  claude 支持 --chrome / --no-chrome" || true

echo
echo "========== 汇总 =========="
echo "通过: $PASS  警告: $WARN  失败: $FAIL"
[ "$FAIL" -eq 0 ] && echo "未发现硬性失败项。警告项表示该组件未配置/未运行，若当前不需要 chrome 自动化可忽略。" || echo "存在失败项，请按上方 [失败] 条目处理。"
