# 受约束的部署流程方案

> 本方案严格遵循 kubernetes-specialist SKILL.md 的工作流：
> 分析需求 → 设计架构 → 实现清单 → 安全加固 → 验证。
> 所有操作使用声明式 `kubectl apply -f`，避免命令式 `kubectl create`。

---

## 一、环境与权限边界声明

### 当前环境实测结果（2026-08-12）

| 检查项 | 结果 |
|--------|------|
| 操作系统 | macOS |
| `kubectl` | **未安装** |
| `helm` | **未安装** |
| `docker` / `kind` / `minikube` | **未安装** |
| 可用 kubeconfig / 集群访问 | **无** |
| `python3` | 3.9.6（可用） |
| `PyYAML` | 6.0.3（可用） |
| `jq` | 可用 |

**因此本次交付不执行任何真实集群操作**（不 apply、不 scale、不 delete）。
所有清单已通过本地静态合规校验（见 `validation-result.txt`），
真实部署需在具备集群凭证的环境中由人工按本流程执行。

### 本流程不会静默执行的操作

- 不创建、删除、覆盖任何外部云资源（VPC、节点、负载均衡器等）
- 不在未确认的情况下对真实集群执行 `apply` / `delete` / `rollout undo`
- 不硬编码或生成任何真实凭据；Secret 中仅含占位符
- 不使用 `kubectl create` / `kubectl edit` 等命令式操作

---

## 二、预检清单（Pre-flight Check）

在真实部署前，必须逐项通过以下检查。任一项失败则停止，不得继续。

### 2.1 工具链预检

```bash
# 检查 kubectl 是否安装且版本兼容（>= 1.24）
kubectl version --client --output=yaml

# 检查集群连通性
kubectl cluster-info

# 检查当前 context 和用户身份（确认操作的是目标集群）
kubectl config current-context
kubectl auth whoami 2>/dev/null || kubectl config view --minify -o jsonpath='{.contexts[0].context.user}'
```

### 2.2 权限预检

```bash
# 确认当前用户对目标命名空间有创建/更新权限
kubectl auth can-i create deployments --namespace webapp-prod
kubectl auth can-i create services --namespace webapp-prod
kubectl auth can-i create networkpolicies --namespace webapp-prod
kubectl auth can-i create secrets --namespace webapp-prod
kubectl auth can-i create resourcequotas --namespace webapp-prod
# 以上命令必须全部返回 "yes"

# 确认没有集群管理员以外的危险权限
kubectl auth can-i delete namespaces
kubectl auth can-i create clusterroles
```

### 2.3 资源容量预检

```bash
# 检查节点可分配资源是否满足请求总量
# 本套清单 requests 总量：cpu=300m, memory=384Mi（3 副本 × 100m/128Mi）
kubectl top nodes
kubectl describe nodes | grep -A5 "Allocated resources"

# 检查是否已有同名资源（防止意外覆盖）
kubectl get all -n webapp-prod 2>/dev/null
kubectl get networkpolicy -n webapp-prod 2>/dev/null
```

### 2.4 镜像可拉取预检

```bash
# 确认镜像仓库可访问、标签存在（registry.example.com/webapp:1.4.2）
# 如有 imagePullSecret，确认其存在
kubectl get secret registry-credentials -n webapp-prod 2>/dev/null
```

### 2.5 本地清单预检（已在本次交付中执行）

```bash
# 静态合规校验（无需集群）
python3 scripts/validate-manifests.py
# 必须返回退出码 0，0 失败

# 如安装了 kubectl，可额外做服务端 dry-run（需要集群）
# kubectl apply --dry-run=server -f manifests/ -n webapp-prod
```

---

## 三、部署流程（含幂等、重试、人工确认点）

### 阶段 0：人工确认（Gate 0）

在执行任何写操作前，部署人必须确认：

- [ ] 当前 kubectl context 指向**目标集群**（非生产误操作防护）
- [ ] 已获得变更审批工单号（填入 namespace annotation `change-ticket`）
- [ ] Secret 占位符已通过 External Secrets / Sealed Secrets / 人工安全渠道替换
- [ ] 已阅读本流程并理解回滚步骤

### 阶段 1：创建命名空间与基础资源（幂等）

```bash
# 幂等：kubectl apply 是声明式操作，重复执行结果一致
kubectl apply -f manifests/00-namespace.yaml
kubectl apply -f manifests/01-rbac.yaml
```

**重试策略**：如遇网络超时，直接重试同一命令（幂等保证安全）。
最多重试 3 次，间隔 5 秒、10 秒、20 秒（指数退避）。

### 阶段 2：创建配置与密钥（幂等）

```bash
kubectl apply -f manifests/02-configmap.yaml
kubectl apply -f manifests/03-secret.yaml
```

**人工确认点（Gate 1）**：
```bash
# 确认 Secret 已正确创建且非占位符（真实部署时）
kubectl get secret webapp-secret -n webapp-prod -o jsonpath='{.data}' | jq 'keys'
# 人工确认输出包含 DB_PASSWORD 等键，且值非占位符
```

### 阶段 3：创建网络策略（幂等）

```bash
# 先创建默认拒绝策略，再创建放行策略
kubectl apply -f manifests/06-networkpolicy.yaml
```

**注意**：NetworkPolicy 生效需要 CNI 插件支持（Calico/Cilium 等）。
预检时确认：
```bash
kubectl get pods -n kube-system | grep -E 'calico|cilium|weave'
```

### 阶段 4：创建工作负载（幂等，含就绪等待）

```bash
kubectl apply -f manifests/04-deployment.yaml
kubectl apply -f manifests/05-service.yaml
```

**等待就绪（含超时与重试）**：
```bash
# rollout status 会阻塞直到就绪或超时
# 超时 5 分钟；失败时自动返回非零退出码
kubectl rollout status deployment/webapp -n webapp-prod --timeout=5m
```

**重试策略**：
- 如果 rollout status 超时，**不要盲目重试 apply**，先排查（见故障排查 Runbook）
- 确认是镜像拉取问题还是资源不足，修复后重新 apply（幂等）

### 阶段 5：创建伸缩与治理资源（幂等）

```bash
kubectl apply -f manifests/07-hpa.yaml
kubectl apply -f manifests/08-pdb.yaml
kubectl apply -f manifests/09-quota.yaml
```

### 阶段 6：部署后验证（Gate 2 — 人工确认）

```bash
# 1. Pod 全部 Running 且 Ready
kubectl get pods -n webapp-prod -l app.kubernetes.io/name=webapp -o wide

# 2. Deployment 滚动更新成功
kubectl rollout status deployment/webapp -n webapp-prod

# 3. Service 有正确的 Endpoints
kubectl get endpoints webapp -n webapp-prod

# 4. RBAC 权限验证
kubectl auth can-i --list --as=system:serviceaccount:webapp-prod:webapp-sa -n webapp-prod

# 5. 网络策略已生效
kubectl get networkpolicy -n webapp-prod

# 6. 应用健康检查（通过 port-forward 临时验证）
kubectl port-forward svc/webapp -n webapp-prod 8080:80 &
curl -f http://localhost:8080/healthz
curl -f http://localhost:8080/readyz
kill %1  # 关闭 port-forward
```

**人工确认**：以上 6 项全部通过后，部署才算完成。
任一项异常，进入回滚流程。

---

## 四、回滚流程

### 4.1 工作负载回滚（最常见）

```bash
# 查看发布历史
kubectl rollout history deployment/webapp -n webapp-prod

# 回滚到上一版本
kubectl rollout undo deployment/webapp -n webapp-prod

# 或回滚到指定版本
kubectl rollout undo deployment/webapp -n webapp-prod --to-revision=<版本号>

# 等待回滚完成
kubectl rollout status deployment/webapp -n webapp-prod --timeout=5m
```

### 4.2 配置回滚

```bash
# ConfigMap/Secret 回滚需从 Git 历史恢复上一版本后重新 apply
git checkout <上一commit> -- manifests/02-configmap.yaml
kubectl apply -f manifests/02-configmap.yaml
# 配置变更后需重启 Pod 才能生效（ConfigMap volume 挂载除外）
kubectl rollout restart deployment/webapp -n webapp-prod
```

### 4.3 完整卸载（仅在确认需要时）

```bash
# 危险操作：删除整个命名空间会清除其中所有资源
# 必须经过人工确认（Gate 3）
kubectl delete -f manifests/09-quota.yaml
kubectl delete -f manifests/08-pdb.yaml
kubectl delete -f manifests/07-hpa.yaml
kubectl delete -f manifests/05-service.yaml
kubectl delete -f manifests/04-deployment.yaml
kubectl delete -f manifests/06-networkpolicy.yaml
kubectl delete -f manifests/03-secret.yaml
kubectl delete -f manifests/02-configmap.yaml
kubectl delete -f manifests/01-rbac.yaml
kubectl delete -f manifests/00-namespace.yaml
```

---

## 五、幂等性保证说明

| 操作 | 幂等机制 |
|------|----------|
| `kubectl apply -f` | 声明式，服务端 Three-Way Patch，重复执行结果一致 |
| `kubectl rollout status` | 只读操作，无副作用 |
| `kubectl rollout undo` | 回滚到指定 revision，重复执行同一版本无额外影响 |
| 本地校验脚本 | 只读分析，不修改任何文件或集群 |

**不使用**以下非幂等/命令式操作：
- `kubectl create`（已存在时报错）
- `kubectl edit`（交互式，不可审计）
- `kubectl replace --force`（会导致 Pod 重建）
- `kubectl scale`（与 HPA 冲突，且命令式不可复现）

---

## 六、重试策略汇总

| 场景 | 策略 | 上限 |
|------|------|------|
| kubectl apply 网络超时 | 指数退避重试（5s/10s/20s） | 3 次 |
| rollout status 超时 | 不自动重试 apply，先排查根因 | — |
| 镜像拉取失败 | 确认镜像/Secret 后重新 apply | 2 次后人工介入 |
| 资源不足（Pending） | 不重试，调整 requests 或扩容节点后 apply | — |
| 校验脚本失败 | 修复清单后重新运行 | 无限制 |

---

## 七、人工确认点汇总

| Gate | 时机 | 确认内容 |
|------|------|----------|
| Gate 0 | 部署前 | context 正确、审批工单、Secret 已替换 |
| Gate 1 | Secret 创建后 | 密钥非占位符、值正确 |
| Gate 2 | 部署完成后 | 6 项验证全部通过 |
| Gate 3 | 卸载前 | 确认删除范围和影响 |
