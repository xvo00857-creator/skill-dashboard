#!/usr/bin/env bash
# agent-mail-automation 预检演示脚本（只读，不修改任何外部资源）
# 依据 SKILL.md：必须先确认 Rube MCP 可用、agent_mail 连接 ACTIVE，才能执行邮件操作。
# 用法：bash precheck-demo.sh
# 退出码：0=全部通过；1=预检未通过（不得进入执行阶段）

PASS=0
FAIL=0
ok(){ echo "[通过] $1"; PASS=$((PASS+1)); }
no(){ echo "[未通过] $1"; FAIL=$((FAIL+1)); }

echo "========================================================"
echo " Agent Mail Automation 预检（agent-mail-automation skill）"
echo " 时间: $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "========================================================"

# P0-1: Rube MCP 端点可达性（SKILL.md: Rube MCP must be connected）
echo ""
echo "--- P0-1: Rube MCP 端点可达性 ---"
CURL_OUT=$(LC_ALL=C curl -sS -m 10 -o /dev/null -w "%{http_code}" https://rube.app/mcp 2>&1)
CURL_RC=$?
if [ "$CURL_RC" -ne 0 ]; then
  no "https://rube.app/mcp 不可达"
  echo "       curl退出码: $CURL_RC"
  echo "       curl输出: $CURL_OUT"
else
  ok "https://rube.app/mcp 可达（HTTP $CURL_OUT）"
fi

# P0-1b: Rube 命令行 / 工具可用性
echo ""
echo "--- P0-1b: Rube 工具可用性 ---"
if command -v rube >/dev/null 2>&1; then
  ok "检测到 rube 命令行: $(command -v rube)"
else
  no "未检测到 rube 命令行；当前 Agent 工具集中亦未发现 RUBE_* 工具（需在客户端配置 MCP server https://rube.app/mcp）"
fi

# P0-2: 本地 MCP 配置
echo ""
echo "--- P0-2: 本地 MCP 配置检查 ---"
FOUND_CFG=0
for f in "$HOME/.cursor/mcp.json" "$HOME/.config/claude/mcp.json" "$HOME/.config/claude-desktop/mcp.json"; do
  if [ -f "$f" ]; then
    if grep -qi "rube" "$f" 2>/dev/null; then
      ok "在 $f 中发现 rube 配置"
    else
      echo "[信息] $f 存在但未包含 rube"
    fi
    FOUND_CFG=1
  fi
done
if [ "$FOUND_CFG" -eq 0 ]; then
  no "未在常见位置（~/.cursor/、~/.config/claude*/）发现 MCP 配置文件"
fi

# P0-3: 相关环境变量
echo ""
echo "--- P0-3: Rube/Composio 环境变量 ---"
ENV_OUT=$(env | grep -iE "rube|composio" 2>/dev/null)
if [ -n "$ENV_OUT" ]; then
  ok "发现相关环境变量（值已隐藏）"
  echo "$ENV_OUT" | sed 's/=.*/=<已隐藏>/'
else
  no "未发现 RUBE/COMPOSIO 相关环境变量"
fi

echo ""
echo "========================================================"
echo " 预检结果: 通过 $PASS 项, 未通过 $FAIL 项"
if [ "$FAIL" -gt 0 ]; then
  echo " 结论: 前置条件不满足，按 SKILL.md 不得执行任何 Agent Mail 操作。"
  echo " 后续: 需在客户端添加 MCP server https://rube.app/mcp 并完成 agent_mail 授权(ACTIVE)。"
  echo "========================================================"
  exit 1
else
  echo " 结论: 预检通过，可进入工具发现(RUBE_SEARCH_TOOLS)与连接确认(RUBE_MANAGE_CONNECTIONS)阶段。"
  echo "========================================================"
  exit 0
fi
