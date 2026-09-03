# KubeSphere Gateway API 扩展 —— 受约束运维流程方案与演示结果

> 本方案严格依据随包 `kubesphere-gateway-api` Skill 的 `SKILL.md` 编写，不扩张其职责边界。
> 所有集群操作均为只读预检或需人工确认后执行；本次环境无 kubectl、无 kubeconfig，未对任何外部资源做创建/删除/修改。

---

## 一、Skill 能力边界（以 SKILL.md 为准）

| 维度 | 实际范围 |
|---|---|
| 管理对象 | KubeSphere **Gateway API 扩展**（底层代理 Traefik，使用 Kubernetes Gateway API + `GatewayProxy` CRD `gatewayapi.kubesphere.io/v1alpha1`） |
| 支持操作 | 安装、卸载、状态检查、GatewayProxy 状态查看、故障排查 |
| 核心资源 | `InstallPlan`（`kubesphere.io/v1alpha1`）、`GatewayProxy`、`GatewayClass`、`Gateway`、`HTTPRoute` 等标准 Gateway API 资源 |
| 三级 GatewayProxy | 集群级 `gatewayproxy-cluster`、工作空间级 `gatewayproxy-workspace-{ws}`、命名空间级 `gatewayproxy-namespace-{ns}`，均位于 `kubesphere-controls-system` 命名空间 |
| 依赖工具 | `kubectl`（必须可连接 KubeSphere 宿主/成员集群） |
| 不包含 | 不管理旧版 Ingress 网关（那是 `kubesphere-gateway` Skill 的职责）；不负责 Whizard 监控/日志组件本身的安装 |

---

## 二、环境预检结果（真实执行）

预检时间：2026-08-12 07:50 CST

| 检查项 | 结果 |
|---|---|
| kubectl 是否安装 | **未安装**（`command not found`） |
| KUBECONFIG 环境变量 | 未设置 |
| `~/.kube/config` | 不存在 |
| 集群连通性 | 无法检查（无 kubectl） |
| InstallPlan 是否已存在 | 无法检查（无 kubectl） |

**结论：当前环境不具备连接任何 KubeSphere/Kubernetes 集群的条件，所有写操作与只读集群查询均无法实际执行。** 本次仅完成脚本级本地验证与流程方案设计。

---

## 三、受约束流程方案

### 3.1 通用护栏（所有动作前置）

1. **预检**：先运行 `preflight.sh <action>`，检查 kubectl、集群连通性（重试3次×5秒）、InstallPlan 是否已存在（幂等判断）、RBAC 权限（`kubectl auth can-i`）。
2. **幂等**：安装前先查 `kubectl get installplans.kubesphere.io gateway-api --ignore-not-found`；已存在则 `kubectl apply` 走升级路径而非重复创建。
3. **重试**：集群连通性检查重试3次；状态轮询 `check-status.sh poll` 内置300秒超时、每10秒一次。
4. **人工确认点**：
   - 安装：确认目标版本（推荐最新稳定版）与目标集群清单后才 `apply`。
   - 卸载：**SKILL.md 明确要求卸载前必须与用户确认**；部分集群卸载只 patch placement，禁止删除 InstallPlan。
   - 任何 `delete`/`patch` 操作前展示将执行的命令并等待确认。
5. **dry-run**：安装时 `generate-installplan.sh` 先执行 `kubectl apply --dry-run=server`，通过后才打印 apply 命令。

### 3.2 安装流程（对应 SKILL.md Installation）

```
[预检] preflight.sh install
  ↓ 通过
[Step1] 检测可用版本，排除 alpha/beta/rc，选最新稳定版；人工确认版本
  ↓
[Step2] 检测 Ready 集群与宿主集群；单集群自动选用，多集群人工选择
  ↓
[Step3] generate-installplan.sh <version> <clusters>
        → 生成 /tmp/gateway-api-installplan.yaml
        → --dry-run=server 校验
  ↓ 人工确认
[apply] kubectl apply -f /tmp/gateway-api-installplan.yaml
  ↓
[轮询] check-status.sh poll（300秒超时，全部 Installed 为成功）
```

### 3.3 卸载流程（对应 SKILL.md Uninstallation）

- **全集群卸载**：确认 → `kubectl delete installplans.kubesphere.io gateway-api --ignore-not-found` → `verify-uninstall.sh` 验证（InstallPlan 已删除 + `extension-gateway-api` 无残留 Pod）。
- **部分集群卸载**：确认 → **不删除 InstallPlan**，仅 `kubectl patch` 修改 `/spec/clusterScheduling/placement/clusters` 为剩余集群列表 → 确认被移除集群不再出现在 `.status.clusterSchedulingStatuses`。

### 3.4 状态检查与 GatewayProxy 运维

- 快照：`check-status.sh quick`；等待完成：`check-status.sh poll`。
- 按 scope 标签列出三级 GatewayProxies（cluster/workspace/namespace）。
- 查看指定 GatewayProxy：`get -o wide` / `describe` / `get -o yaml`，并按 `status.helmRelease.name` 定位 Traefik Pod。
- 关联 GatewayClass/Gateway：按 `gatewayapi.kubesphere.io/gateway-class-name` 标签与 `status.gatewayClass.name` 查询。

### 3.5 故障排查（对应 SKILL.md Troubleshooting）

| 现象 | 关键排查命令（只读） |
|---|---|
| 卡在 Progressing | `describe gatewayproxy`；查 controller-manager 日志过滤 error/helm/install/reconcile |
| Ready=False | 查 deployment、pod、events、Pod 日志 |
| CrashLoopBackOff | `--previous` 日志、events、traefik.yaml、ConfigMap |
| Controller 不调和 | controller-manager Pod/日志、ValidatingWebhookConfiguration、deployment yaml |
| 日志/指标不可用 | 查 `extension-whizard-telemetry` 命名空间 Pod 与 Service、apiserver 日志 |

---

## 四、可核验的演示结果（均为本地真实执行）

以下演示在无 kubectl 环境下运行，输出为真实结果，未做任何篡改。

### 演示1：三个脚本语法检查
```
scripts/check-status.sh       → OK: 语法通过
scripts/generate-installplan.sh → OK: 语法通过
scripts/verify-uninstall.sh   → OK: 语法通过
```

### 演示2：generate-installplan.sh 参数预检
- 无参数：输出 Usage 并以退出码 1 退出（符合预期）。
- 带参数 `v1.0.0 host`：因 kubectl 不在 PATH，输出 `Error: kubectl not found in PATH` 并退出 1，**未生成** `/tmp/gateway-api-installplan.yaml`（脚本在写文件前即拦截）。

### 演示3：check-status.sh quick
- 输出 `Gateway API InstallPlan not found.`，退出码 1（kubectl 不可用导致查询失败，脚本正确以非零退出）。

### 演示4：verify-uninstall.sh（发现边界问题）
- 设置 `TIMEOUT=12` 运行，脚本输出 `✓ Uninstallation complete` 并退出 0。
- **但这是误报**：当前环境 kubectl 不存在，脚本未先检查 kubectl 是否存在，`kubectl get` 失败被当作"资源不存在"，`kubectl get pods` 失败经 `|| true` 后行数为 0，从而误判为卸载完成。
- **对比**：`generate-installplan.sh` 第14-17行有显式 `command -v kubectl` 检查，`verify-uninstall.sh` 缺少同等检查。建议在 `verify-uninstall.sh` 开头补充 kubectl 存在性检查，否则在工具缺失时会给出虚假成功信号。

### 演示5：preflight.sh 预检拦截
- `preflight.sh install` 与 `preflight.sh uninstall` 均因 kubectl 缺失报告 `失败=1`，结论为"预检未通过，禁止执行后续操作"，退出码 1。
- 证明预检护栏能在工具缺失时正确阻断写操作路径。

---

## 五、无法访问的资源与待确认假设

| 项 | 状态 |
|---|---|
| KubeSphere 集群 API | 无法访问（无 kubeconfig、无 kubectl） |
| 可用扩展版本列表 | 无法获取，未编造任何版本号 |
| 集群清单与 Ready 状态 | 无法获取 |
| InstallPlan / GatewayProxy 实际状态 | 无法获取 |
| 是否存在多集群、宿主集群名称 | 未知，需用户提供 |
| Whizard 监控/日志依赖是否安装 | 未知 |

**待用户确认后才能继续的事项**：
1. 提供可用的 kubeconfig 与 kubectl 环境（或告知集群接入方式）。
2. 确认本次意图：安装、卸载、状态检查还是故障排查；若为故障排查需提供目标 GatewayProxy 名称与现象。
3. 安装场景下确认目标版本与目标集群；卸载场景下确认全集群还是部分集群。

---

## 六、实际读取的 Skill 文件（相对路径）

- `kubesphere-gateway-api/SKILL.md`
- `kubesphere-gateway-api/scripts/check-status.sh`
- `kubesphere-gateway-api/scripts/generate-installplan.sh`
- `kubesphere-gateway-api/scripts/verify-uninstall.sh`

（另基于 SKILL.md 流程新增了只读预检脚本 `kubesphere-gateway-api/preflight.sh`，未修改原有三个脚本。）

---

## 七、实际影响交付结果的 SKILL.md 规则

**规则：卸载前必须与用户确认（Uninstallation 章首 "Always confirm with the user before proceeding."），且部分集群卸载禁止删除 InstallPlan、只允许 patch placement。**

这条规则直接决定了本方案的卸载设计：我没有（也不能在无确认情况下）执行任何 `kubectl delete`，并在预检脚本与流程文档中把"全集群卸载删 InstallPlan"与"部分集群卸载只 patch placement"作为两条必须人工确认的分支固化下来。同时它也约束了演示边界——在无集群、无用户明确卸载指令的情况下，本次不执行任何删除类操作。

另一条影响结果的规则是安装三步法中的 **`--dry-run=server` 前置校验**（Step 3）：本方案据此把 dry-run 设为 apply 前的强制门禁，预检脚本也对应增加了权限与连通性检查。
