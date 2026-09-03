# 故障排查 Runbook

> 本 Runbook 基于 kubernetes-specialist Skill 的 `references/troubleshooting.md` 编写，
> 针对本套 webapp 清单的常见故障场景。
>
> **重要说明**：当前环境无 kubectl/集群，以下命令均为**流程指导**，
> 需在具备集群访问权限的环境中执行。本文件不包含任何编造的运行结果。

---

## 排查总原则

1. **先看日志，再看事件**：`kubectl logs` → `kubectl describe` → `kubectl get events`
2. **不盲目重启**：CrashLoopBackOff 重启不会修复配置错误
3. **最小化变更**：一次只改一个变量，确认效果后再继续
4. **所有排查命令为只读操作**，不会修改集群状态

---

## 场景一：Pod 处于 Pending

### 诊断步骤

```bash
# 1. 查看 Pod 状态和事件
kubectl get pods -n webapp-prod -l app.kubernetes.io/name=webapp -o wide
kubectl describe pod <pod-name> -n webapp-prod | tail -20

# 2. 查看集群事件（按时间排序）
kubectl get events -n webapp-prod --sort-by='.lastTimestamp'

# 3. 检查节点资源是否充足
kubectl top nodes
kubectl describe nodes | grep -A10 "Allocated resources"
```

### 常见原因与处理

| 事件信息 | 原因 | 处理 |
|----------|------|------|
| `Insufficient cpu/memory` | 节点资源不足 | 调整 requests 或扩容节点；不要直接删除 limits |
| `persistentvolumeclaim not bound` | PVC 未绑定 | 本套清单无 PVC，如出现检查是否误挂载 |
| `node(s) didn't match Pod's node affinity` | 反亲和导致无法调度 | 3 副本需要至少 2 个节点（preferred 非强制，可降级） |
| `0/3 nodes are available: 3 node(s) had taint` | 节点有污点 | 确认是否需要 toleration，或更换节点池 |

---

## 场景二：CrashLoopBackOff

### 诊断步骤

```bash
# 1. 查看当前和上一次崩溃日志（关键！）
kubectl logs <pod-name> -n webapp-prod
kubectl logs <pod-name> -n webapp-prod --previous

# 2. 查看 Pod 事件和状态
kubectl describe pod <pod-name> -n webapp-prod | grep -A20 "State:"
kubectl get pod <pod-name> -n webapp-prod -o jsonpath='{.status.containerStatuses[0].state}'

# 3. 检查退出码
# 0   = 正常退出（不应发生在长期运行服务中）
# 1   = 应用错误（看日志）
# 137 = SIGKILL，通常是 OOM 被 limits 杀死
# 139 = SIGSEGV，段错误
# 143 = SIGTERM，优雅终止
```

### 常见原因与处理

| 现象 | 原因 | 处理 |
|------|------|------|
| 退出码 137，日志无异常 | OOMKilled，memory limits(256Mi) 不足 | 评估后调大 limits，同时检查内存泄漏 |
| 日志显示连接数据库超时 | 数据库不可达或 NetworkPolicy 阻断 | 检查 DNS、NetworkPolicy egress 规则 |
| 日志显示认证失败 | Secret 占位符未替换或密码错误 | 确认 Secret 已通过安全渠道注入真实值 |
| livenessProbe 失败后被杀 | 探针配置过严或应用启动慢 | 检查 initialDelaySeconds、failureThreshold |
| `readinessProbe failed` | 应用未就绪但存活 | 检查依赖服务（DB/Redis）是否就绪 |

### 临时调试（只读，不修改集群）

```bash
# 在 Pod 网络命名空间中运行临时调试容器
kubectl debug -it <pod-name> -n webapp-prod \
  --image=nicolaka/netshoot --target=webapp -- /bin/bash

# 在调试容器内验证网络连通性
nslookup postgres.webapp-prod.svc.cluster.local
nc -zv postgres.webapp-prod.svc.cluster.local 5432
curl -v http://webapp/healthz
```

---

## 场景三：ImagePullBackOff / ErrImagePull

### 诊断步骤

```bash
kubectl describe pod <pod-name> -n webapp-prod | grep -A10 "Events:"
```

### 常见原因与处理

| 事件信息 | 原因 | 处理 |
|----------|------|------|
| `pull access denied` | 私有仓库认证失败 | 确认 imagePullSecret 配置 |
| `manifest unknown` | 标签 1.4.2 不存在 | 确认镜像已推送到仓库，标签拼写正确 |
| `timeout` / `no route to host` | 网络问题或仓库不可达 | 检查节点网络、DNS、代理配置 |
| `x509: certificate signed by unknown authority` | 自签名仓库证书 | 配置节点 CA 信任（不要用 insecure-registries） |

### 手动验证拉取（在节点上）

```bash
# 确认镜像和标签存在（需仓库凭证）
crictl pull registry.example.com/webapp:1.4.2
# 或
nerdctl pull registry.example.com/webapp:1.4.2
```

---

## 场景四：Service 不可达

### 诊断步骤

```bash
# 1. 确认 Service 和 Endpoints
kubectl get svc webapp -n webapp-prod
kubectl get endpoints webapp -n webapp-prod
# Endpoints 必须有后端 IP，为空说明 label 不匹配或 Pod 未就绪

# 2. 检查 label 选择器是否匹配
kubectl get pods -n webapp-prod -l app.kubernetes.io/name=webapp,app.kubernetes.io/component=backend --show-labels

# 3. 集群内连通性测试
kubectl run tmp-test --rm -it --image=nicolaka/netshoot -- /bin/bash
# 在测试 Pod 内：
nslookup webapp.webapp-prod.svc.cluster.local
curl -v http://webapp.webapp-prod.svc.cluster.local/healthz
```

### 常见原因与处理

| 现象 | 原因 | 处理 |
|------|------|------|
| Endpoints 为空 | Pod label 与 Service selector 不匹配 | 核对 label，本清单 selector 为 name+component |
| Endpoints 为空 | Pod 未通过 readinessProbe | 修复就绪探针或应用依赖 |
| DNS 解析失败 | CoreDNS 问题 | `kubectl get pods -n kube-system -l k8s-app=kube-dns` |
| 连接超时 | NetworkPolicy 阻断 | 检查 NetworkPolicy 是否允许来源命名空间 |

---

## 场景五：NetworkPolicy 误阻断

### 诊断步骤

```bash
# 1. 查看命名空间内所有 NetworkPolicy
kubectl get networkpolicy -n webapp-prod
kubectl describe networkpolicy default-deny-all -n webapp-prod

# 2. 用 netshoot 测试连通性
kubectl run tmp-test --rm -it --image=nicolaka/netshoot -- /bin/bash
# 在测试 Pod 内测试被阻断的目标
nc -zv <target-service> <port>

# 3. 确认 CNI 插件支持 NetworkPolicy
kubectl get pods -n kube-system | grep -E 'calico|cilium'
```

### 处理原则

- **不要直接删除 default-deny-all**（会破坏零信任模型）
- 应在 `webapp-allow-egress` 或 `webapp-allow-ingress` 中**添加**必要的放行规则
- 修改后 `kubectl apply -f manifests/06-networkpolicy.yaml`（幂等）
- 如需临时放行用于排查，添加临时规则并设置 TTL 提醒删除

---

## 场景六：HPA 不伸缩或异常伸缩

### 诊断步骤

```bash
kubectl get hpa webapp-hpa -n webapp-prod
kubectl describe hpa webapp-hpa -n webapp-prod
# 查看 TARGETS 列是否显示实际使用率（需要 metrics-server）

kubectl top pods -n webapp-prod -l app.kubernetes.io/name=webapp
```

### 常见原因与处理

| 现象 | 原因 | 处理 |
|------|------|------|
| TARGETS 显示 `<unknown>` | metrics-server 未安装 | 安装 metrics-server |
| 副本数卡在 minReplicas | CPU/内存未达阈值 | 正常现象，检查阈值是否合理 |
| 频繁伸缩（抖动） | stabilizationWindowSeconds 过短 | 本清单已设 300s，确认未被覆盖 |
| 无法扩容到 maxReplicas | ResourceQuota 限制 | 检查 quota 中 pods 上限 |

---

## 场景七：高资源使用

### 诊断步骤

```bash
# 按 CPU/内存排序查看 Pod
kubectl top pods -n webapp-prod --sort-by=cpu
kubectl top pods -n webapp-prod --sort-by=memory

# 查看节点分配情况
kubectl describe nodes | grep -A20 "Allocated resources"

# 查看容器级资源使用
kubectl top pods -n webapp-prod --containers
```

### 处理

- CPU 持续接近 limits：考虑调大 limits 或增加 HPA 副本数
- 内存持续接近 limits：排查内存泄漏，或调大 memory limits
- 参考 cost-optimization.md：requests 设为 P50+20%，CPU limits 2-4x，Memory limits 1.5-2x

---

## 快速参考：Pod 状态含义

| 状态 | 含义 | 首要排查方向 |
|------|------|-------------|
| Pending | 未被调度 | 资源不足、PVC、亲和性 |
| ContainerCreating | 正在创建 | 镜像拉取、ConfigMap/Secret 挂载 |
| Running | 运行中 | 如未 Ready 检查 readinessProbe |
| CrashLoopBackOff | 反复崩溃 | `logs --previous`、退出码 |
| ImagePullBackOff | 镜像拉取失败 | 标签、凭证、网络 |
| ErrImagePull | 镜像拉取错误 | 同上 |
| OOMKilled | 内存超限被杀 | 退出码 137，调大 memory limits |
| Terminating | 正在终止 | 检查 finalizer、PDB |
