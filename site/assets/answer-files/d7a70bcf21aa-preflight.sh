#!/usr/bin/env bash
# kubeSphere Gateway API 扩展 —— 受约束操作预检脚本
# 基于 kubesphere-gateway-api SKILL.md 编写，仅做只读检查，不创建/删除/修改任何集群资源。
# 用法: ./preflight.sh [install|uninstall|status|gatewayproxy]
set -euo pipefail

ACTION="${1:-status}"
PASS=0; FAIL=0; WARN=0
log_pass(){ echo "  [通过] $1"; PASS=$((PASS+1)); }
log_fail(){ echo "  [失败] $1"; FAIL=$((FAIL+1)); }
log_warn(){ echo "  [警告] $1"; WARN=$((WARN+1)); }

echo "=========================================="
echo " KubeSphere Gateway API 预检 (动作: $ACTION)"
echo " 时间: $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "=========================================="

# ---------- 1. 本地依赖检查 ----------
echo ""
echo "== 1. 本地依赖 =="
if command -v kubectl >/dev/null 2>&1; then
  log_pass "kubectl 已安装: $(kubectl version --client --short 2>/dev/null || kubectl version --client 2>/dev/null | head -1)"
  KUBECTL_OK=1
else
  log_fail "kubectl 未安装或不在 PATH 中"
  KUBECTL_OK=0
fi

# ---------- 2. 集群连通性检查（只读）----------
echo ""
echo "== 2. 集群连通性 =="
if [ "$KUBECTL_OK" = "1" ]; then
  # 重试3次，每次间隔5秒
  CONN_OK=0
  for i in 1 2 3; do
    if kubectl cluster-info >/dev/null 2>&1; then
      CONN_OK=1; break
    fi
    echo "  第 $i 次连接失败，5秒后重试..."
    sleep 5
  done
  if [ "$CONN_OK" = "1" ]; then
    CTX=$(kubectl config current-context 2>/dev/null || echo "<未知>")
    log_pass "集群可达，当前上下文: $CTX"
  else
    log_fail "集群不可达（已重试3次），请检查 kubeconfig 与网络"
  fi
else
  log_warn "跳过集群连通性检查（kubectl 不可用）"
fi

# ---------- 3. 幂等性检查：是否已安装 ----------
echo ""
echo "== 3. 安装状态（幂等判断）=="
if [ "$KUBECTL_OK" = "1" ] && kubectl cluster-info >/dev/null 2>&1; then
  if kubectl get installplans.kubesphere.io gateway-api >/dev/null 2>&1; then
    STATE=$(kubectl get installplans.kubesphere.io gateway-api -o jsonpath='{.status.state}' 2>/dev/null || echo "<未知>")
    log_warn "gateway-api InstallPlan 已存在，状态: $STATE"
    echo "         -> 安装动作将走升级/幂等 apply 路径，不会重复创建"
    INSTALLED=1
  else
    log_pass "gateway-api InstallPlan 不存在，可执行全新安装"
    INSTALLED=0
  fi

  # CRD 可用性
  if kubectl get crd gatewayproxies.gatewayapi.kubesphere.io >/dev/null 2>&1; then
    log_pass "GatewayProxy CRD 已就绪"
  else
    log_warn "GatewayProxy CRD 不存在（安装后才会出现）"
  fi
else
  log_warn "跳过安装状态检查（集群不可达）"
fi

# ---------- 4. 权限检查（只读 SelfSubjectAccessReview）----------
echo ""
echo "== 4. 权限检查 =="
if [ "$KUBECTL_OK" = "1" ] && kubectl cluster-info >/dev/null 2>&1; then
  case "$ACTION" in
    install)
      if kubectl auth can-i create installplans.kubesphere.io >/dev/null 2>&1; then
        log_pass "有创建 InstallPlan 权限"
      else
        log_fail "无创建 InstallPlan 权限"
      fi
      ;;
    uninstall)
      if kubectl auth can-i delete installplans.kubesphere.io >/dev/null 2>&1; then
        log_pass "有删除 InstallPlan 权限"
      else
        log_fail "无删除 InstallPlan 权限"
      fi
      ;;
    *)
      if kubectl auth can-i get installplans.kubesphere.io >/dev/null 2>&1; then
        log_pass "有读取 InstallPlan 权限"
      else
        log_fail "无读取 InstallPlan 权限"
      fi
      ;;
  esac
else
  log_warn "跳过权限检查（集群不可达）"
fi

# ---------- 5. 人工确认点提示 ----------
echo ""
echo "== 5. 人工确认点 =="
case "$ACTION" in
  install)
    if [ "${INSTALLED:-0}" = "1" ]; then
      echo "  [需确认] 检测到已存在 InstallPlan，apply 将触发升级/变更，是否继续？"
    else
      echo "  [需确认] 全新安装将创建 InstallPlan 并在目标集群部署 Traefik，是否继续？"
    fi
    echo "  [需确认] 目标版本与目标集群清单需人工确认（见 SKILL.md Step1/Step2）"
    ;;
  uninstall)
    echo "  [需确认] 卸载将删除 InstallPlan（全集群卸载）或修改 placement（部分集群卸载）"
    echo "  [需确认] SKILL.md 明确要求：卸载前必须与用户确认"
    echo "  [需确认] 部分集群卸载时禁止删除 InstallPlan，只 patch placement"
    ;;
  *)
    echo "  只读状态检查，无需人工确认"
    ;;
esac

# ---------- 汇总 ----------
echo ""
echo "=========================================="
echo " 预检汇总: 通过=$PASS  失败=$FAIL  警告=$WARN"
echo "=========================================="
if [ "$FAIL" -gt 0 ]; then
  echo "结论: 预检未通过，禁止执行后续操作。请修复上述失败项后重试。"
  exit 1
fi
echo "结论: 预检通过。后续操作仍需按 SKILL.md 流程执行，并在写操作前完成人工确认。"
