# kubernetes-specialist 交付包

本交付包基于 `kubernetes-specialist` Skill（v1.1.1）生成，包含一套生产级 Kubernetes 声明式清单、
受约束的部署流程、故障排查 Runbook，以及一次可核验的本地合规校验结果。

---

## 目录结构

```
k8s-delivery/
├── manifests/                        # 声明式 YAML 清单（10 个文件，15 个资源）
│   ├── 00-namespace.yaml             # 专用命名空间 webapp-prod
│   ├── 01-rbac.yaml                  # ServiceAccount + 最小权限 Role + RoleBinding
│   ├── 02-configmap.yaml             # 非敏感配置
│   ├── 03-secret.yaml                # 敏感数据（占位符，需人工/External Secrets 替换）
│   ├── 04-deployment.yaml            # 3 副本 Deployment（资源限制/探针/安全上下文）
│   ├── 05-service.yaml               # ClusterIP Service
│   ├── 06-networkpolicy.yaml         # 默认拒绝 + 显式放行（零信任网络）
│   ├── 07-hpa.yaml                   # 水平自动伸缩（CPU 70%/内存 80%）
│   ├── 08-pdb.yaml                   # Pod 干扰预算（minAvailable=2）
│   └── 09-quota.yaml                 # ResourceQuota + LimitRange
├── scripts/
│   └── validate-manifests.py         # 本地合规校验脚本（对照 SKILL.md 12 类检查）
├── docs/
│   ├── deployment-runbook.md         # 受约束部署流程（预检/幂等/重试/人工确认/回滚）
│   ├── troubleshooting-runbook.md    # 故障排查 Runbook（7 类常见场景）
│   └── validation-result.txt         # 校验脚本真实运行输出（38 项全通过）
└── README.md                         # 本文件
```

---

## 快速开始

### 本地校验（无需集群，已验证可运行）

```bash
cd k8s-delivery
python3 scripts/validate-manifests.py
# 预期：38 通过, 0 失败, 0 警告，退出码 0
```

### 真实部署（需在有集群凭证的环境执行）

1. 阅读 `docs/deployment-runbook.md`
2. 完成预检清单（Gate 0）
3. 替换 `manifests/03-secret.yaml` 中的占位符
4. 按阶段 apply，每个 Gate 人工确认
5. 部署后执行 6 项验证

---

## 环境限制与未执行操作声明

| 项目 | 状态 |
|------|------|
| kubectl / helm / docker | 当前环境未安装，未执行任何集群命令 |
| 真实 K8s 集群访问 | 无 kubeconfig，未连接任何集群 |
| 云厂商 API | 未调用，未创建/删除/修改任何外部资源 |
| 真实凭据 | 未生成、未存储任何真实密码或密钥 |
| 本地校验脚本 | **已真实运行**，结果见 `docs/validation-result.txt` |

所有 `kubectl` 命令均为流程指导，需在具备权限的环境中由人工执行。

---

## Skill 能力边界说明

题目分类为"自动化与工具"，描述为"云端基础设施配置、运维与故障排查"。
经实际阅读 SKILL.md，该 Skill 的真实能力边界为：

- **核心输出**：声明式 Kubernetes YAML 清单（output-format: manifests）
- **能做**：生成 Deployment/Service/NetworkPolicy/RBAC/ConfigMap/Secret/HPA/PDB 等清单；
  提供 kubectl 故障排查命令和诊断流程；给出安全/成本/多集群最佳实践
- **不做**：不直接连接云厂商 API 创建真实基础设施（无 terraform/云 SDK 能力）；
  不包含集群凭证；不替用户执行部署

因此本次交付以"清单产物 + 受约束流程方案 + 本地可核验校验"形式完成，
未静默创建任何外部资源，符合"只能使用现有权限和已提供数据"的约束。

---

## 实际读取的 Skill 文件

以下为本次实际读取的 Skill 文件（相对于 `kubernetes-specialist/kubernetes-specialist/` 目录）：

1. `SKILL.md`
2. `references/workloads.md`
3. `references/networking.md`
4. `references/configuration.md`
5. `references/storage.md`
6. `references/troubleshooting.md`
7. `references/helm-charts.md`
8. `references/custom-operators.md`
9. `references/service-mesh.md`
10. `references/gitops.md`
11. `references/cost-optimization.md`
12. `references/multi-cluster.md`

---

## 实际影响交付结果的 SKILL.md 规则

以下规则直接决定了交付物的形态，均已落实在清单和校验脚本中：

1. **"Use declarative YAML manifests (avoid imperative kubectl commands)"**
   → 全部操作使用 `kubectl apply -f`，部署流程中明确禁止 `kubectl create`/`edit`/`scale`。

2. **"Set resource requests and limits on all containers"**
   → Deployment 中每个容器均设置 requests(cpu=100m, memory=128Mi) 和 limits(cpu=500m, memory=256Mi)；
   校验脚本第 2 类检查强制验证。

3. **"Use secrets for sensitive data (never hardcode credentials)"**
   → Secret 中仅使用 `PLACEHOLDER_*` 占位符，不包含任何真实凭据；
   校验脚本检查 ConfigMap 中无密码字段、env 中无明文密钥。

4. **"Implement NetworkPolicies for network segmentation"**
   → 采用零信任模型：default-deny-all 默认拒绝所有入站/出站，再显式放行必要流量。

5. **"Never use latest tag for production images"**
   → 镜像固定为 `registry.example.com/webapp:1.4.2`，校验脚本拒绝 latest 或无标签镜像。

6. **"Use namespaces for logical isolation"** + **"Don't use the default ServiceAccount for application pods"**
   → 专用命名空间 `webapp-prod` + 专用 ServiceAccount `webapp-sa`（automountServiceAccountToken: false）。

7. **"Document configuration decisions in annotations"**
   → Deployment 中记录了副本数、更新策略、资源依据、配置校验和 4 项决策 annotation。

---

## 校验结果摘要

```
已加载 15 个 YAML 文档
汇总: 38 通过, 0 失败, 0 警告, 共 38 项
退出码: 0
```

完整输出见 `docs/validation-result.txt`。
