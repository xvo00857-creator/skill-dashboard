# GKE 工作负载安全审计报告

- **审计对象**：模拟安全日志 `incident_log.csv`
- **审计范围**：GKE 工作负载级安全控制（Workload Identity、Network Policy、Pod Security、Secret Manager CSI），严格遵循 `gke-workload-security` Skill 边界
- **审计性质**：授权测试范围内的静态日志分析，未对任何真实集群执行破坏性操作
- **报告生成时间**：2026-08-26
- **输入日志时间窗**：2026-08-12T09:00:12Z — 2026-08-12T09:09:00Z（约 9 分钟）

---

## 一、执行摘要

在 9 分钟的日志窗口内识别出 **1 起严重（Critical）数据外泄事件**、**1 起高危（High）令牌越权事件**、**1 起中危（Medium）暴力破解尝试**，以及 **1 起低危（Low）日志完整性缺陷**。

核心攻击链推断：来源 IP `203.0.113.8` 于 `09:04:02Z` 在 `api` 系统触发 `token_scope_mismatch`（服务账户 `service-a` 令牌范围不匹配），随后于 `09:07:30Z` 从同一 IP 在 `db` 系统以 `unknown` 用户身份执行 `unexpected_export`。两事件间隔约 3 分 28 秒，来源 IP 一致，高度疑似利用越权或被窃取的服务账户令牌进行数据导出。

**整体风险评级：严重（Critical）**——存在活跃的数据外泄路径，且日志完整性缺陷可能掩盖更多事件。

---

## 二、日志事件明细与时间线

| 序号 | 时间 (UTC) | 系统 | 严重级 | 事件 | 用户 | 来源 IP |
|---|---|---|---|---|---|---|
| 1 | 09:00:12 | web | info | login_success | alice | 192.0.2.10 |
| 2 | 09:03:45 | web | warning | login_failed | admin | 198.51.100.23 |
| 3 | 09:03:49 | web | warning | login_failed | admin | 198.51.100.23 |
| 4 | 09:04:02 | api | high | token_scope_mismatch | service-a | 203.0.113.8 |
| 5 | 09:07:30 | db | critical | unexpected_export | unknown | 203.0.113.8 |
| 6 | 09:09:00 | web | *(缺失)* | malformed_record | *(缺失)* | *(缺失)* |

**关键关联**：事件 4 与事件 5 共享来源 IP `203.0.113.8`，且事件 5 的用户字段为 `unknown`——符合"使用窃取/越权服务账户令牌访问数据库时，数据库层无法映射到已知用户身份"的特征。

---

## 三、风险分级与证据

### 风险 R1：数据外泄（Critical）

- **事件**：`unexpected_export`（事件 5）
- **证据**：
  - 时间 `2026-08-12T09:07:30Z`，系统 `db`，严重级 `critical`
  - 用户字段为 `unknown`，来源 IP `203.0.113.8`
  - 与 3 分 28 秒前的 `token_scope_mismatch`（事件 4）同源 IP
  - `unexpected_export` 表示非预期的数据导出操作，可能涉及批量数据下载
- **影响**：敏感数据泄露、合规违规（GDPR/个人信息保护法）、业务声誉损失
- **Skill 映射**：本风险涉及工作负载身份与网络隔离，属于 `gke-workload-security` 覆盖范围；数据库平台本身的审计不属于本 Skill

### 风险 R2：服务账户令牌越权（High）

- **事件**：`token_scope_mismatch`（事件 4）
- **证据**：
  - 时间 `2026-08-12T09:04:02Z`，系统 `api`，严重级 `high`
  - 用户 `service-a`，来源 IP `203.0.113.8`
  - `token_scope_mismatch` 表示服务账户使用的令牌请求了超出其授权范围的权限
  - 该 IP 随后触发了数据外泄事件（R1）
- **影响**：服务账户被攻破或过度授权，可作为横向移动和数据窃取的跳板
- **Skill 映射**：直接对应 SKILL.md 工作流 2（Configure Workload Identity）与最佳实践 1（Least Privilege）

### 风险 R3：管理员账户暴力破解（Medium）

- **事件**：连续 `login_failed`（事件 2、3）
- **证据**：
  - `09:03:45Z` 与 `09:03:49Z`，间隔仅 4 秒，同一账户 `admin`，同一来源 IP `198.51.100.23`
  - 短时间内针对高权限账户的连续失败登录，符合暴力破解或撞库特征
  - 日志窗口内未观察到该 IP 的后续成功登录，但窗口仅 9 分钟，不能排除窗口外成功
- **影响**：管理员账户失陷可导致集群级控制平面被接管
- **Skill 映射**：身份认证属于工作负载安全周边；本 Skill 不覆盖 RBAC 加固（SKILL.md 明确排除），但可通过 Network Policy 限制管理面访问来源

### 风险 R4：日志完整性缺陷（Low）

- **事件**：`malformed_record`（事件 6）
- **证据**：
  - `09:09:00Z`，系统 `web`，`severity`、`user`、`source_ip` 字段均为空
  - 缺失字段导致该事件无法纳入风险关联分析，可能掩盖真实攻击
  - 若为日志管道故障，则可能存在更多未记录事件；若为有意脱敏，则需评估是否影响安全审计有效性
- **影响**：审计可追溯性下降，事件响应时关键证据缺失
- **Skill 映射**：对应 SKILL.md 工作流 7（Enable Network Policy Logging）——日志完整性是网络策略可观测性的前提

---

## 四、约束与冲突分析

本审计在执行过程中识别出以下两组核心约束与冲突，均直接影响修复路径的选择。

### 冲突一：默认拒绝网络策略（Default-Deny）的安全收益 vs 业务可用性中断

**背景**：SKILL.md 工作流 3 提供了 `assets/default-deny-netpol.yaml`，通过 `podSelector: {}` 匹配命名空间内所有 Pod 并同时拒绝 Ingress 与 Egress。这是阻断 R1（数据外泄）和 R3（暴力破解横向移动）最直接的手段。

**冲突点**：
- 一旦应用 default-deny，命名空间内所有 Pod 间通信、Pod 到外部 API（包括 Google Cloud API、数据库、日志采集）都会被立即阻断。
- `service-a` 作为服务账户，其正常业务调用依赖出站网络访问；若在未梳理白名单前直接应用 default-deny，将导致服务不可用。
- SKILL.md 最佳实践 2 要求"Use Network Policies to restrict Pod-to-Pod communication"，但未提供从"全通"到"最小权限"的渐进式迁移脚本。

**关键取舍**：
- **选择**：不直接在生产命名空间应用 default-deny，而是先在隔离测试命名空间（如 SKILL.md 中的 `workload-identity-test-ns`）验证，再基于 Network Policy Logging（工作流 7）采集的实际流量画像生成白名单，最后灰度切换。
- **代价**：数据外泄通道在白名单梳理完成前仍然存在，需配合临时的身份侧缓解（吊销可疑令牌、轮换服务账户密钥）降低风险。
- **依赖**：需要集群启用 Dataplane V2 以使用 NetworkLogging CRD（SKILL.md 工作流 7）；若集群使用传统数据通路，则需先启用 NetworkPolicy 插件（`--update-addons=NetworkPolicy=ENABLED`），但 SKILL.md 注明在 Dataplane V2 集群上此步骤"may fail"。

### 冲突二：Workload Identity 最小权限收紧 vs 服务调用链依赖

**背景**：R2（`token_scope_mismatch`）表明 `service-a` 的令牌范围与实际请求不匹配。SKILL.md 最佳实践 1 明确要求"Always use Workload Identity with minimal IAM roles. Avoid using Node default service accounts."

**冲突点**：
- `token_scope_mismatch` 可能有两种成因：(a) `service-a` 被过度授权，令牌本身范围过宽，被利用后请求了不该有的权限；(b) `service-a` 权限不足，业务代码尝试访问未授权资源导致报错。
- 若为 (a)，收紧 IAM 角色可直接消除风险；若为 (b)，收紧反而会加剧业务故障。
- 日志仅记录了 `token_scope_mismatch` 事件本身，未包含请求的具体 scope 或目标资源，无法在不访问真实集群的情况下区分两种成因。
- SKILL.md 工作流 2 的 KSA-GSA 绑定操作（`gcloud iam service-accounts add-iam-policy-binding`）需要 `gcloud` 认证和项目 IAM 管理员权限，当前环境不具备。

**关键取舍**：
- **选择**：在审计报告中给出双路径修复建议——先通过 `audit_cluster.sh`（工作流 1）确认 Workload Identity 配置状态，再由集群管理员结合 IAM 审计日志判定 `service-a` 的实际授权范围，最后决定收紧还是补授权。
- **代价**：无法在本审计中直接完成修复，依赖人工介入和真实集群访问。
- **依赖**：`audit_cluster.sh` 需要 `gcloud` CLI 已认证、`jq` 已安装、以及对目标集群的 `container.clusters.get` 权限；当前环境均不满足，故脚本未实际执行，其检查项（Workload Identity、Network Policy、Shielded Nodes、Binary Authorization、Private Cluster）仅作为修复后的复测清单参考。
- **边界说明**：`audit_cluster.sh` 检查了 Shielded Nodes 和 Binary Authorization，但 SKILL.md 描述明确将这两项列为平台级控制，归 `gke-platform-security` Skill 处理。本报告仅记录其状态为"待平台侧确认"，不在工作负载级修复范围内。

---

## 五、修复建议

以下建议严格限定在 `gke-workload-security` Skill 覆盖的工作负载级控制范围内。平台级项（Shielded Nodes、Binary Authorization、RBAC、控制平面安全）标注为"需转交 gke-platform-security"。

### 5.1 紧急缓解（针对 R1 + R2，建议 24 小时内）

1. **吊销并轮换 `service-a` 的服务账户凭据**
   - 若使用 Workload Identity：删除并重建 KSA-GSA 绑定，强制令牌失效
   - 若使用静态密钥：轮换 `service-a` 的 GSA 密钥
   - 审查 `service-a` 最近 24 小时的所有 API 调用，识别异常访问

2. **临时网络隔离受影响命名空间**
   - 在确认业务可接受短暂中断的前提下，对 `db` 所在命名空间应用临时入站限制，仅允许已知合法应用 Pod 访问
   - 不建议直接应用 full default-deny（见冲突一）

3. **阻断恶意来源 IP**
   - `203.0.113.8`（数据外泄 + 令牌越权）和 `198.51.100.23`（暴力破解）应在云防火墙或 WAF 层临时封禁
   - 此操作属于平台/网络级，需协同网络安全团队

### 5.2 短期加固（1 周内）

4. **落实 Workload Identity 最小权限（对应 SKILL.md 工作流 2）**
   - 为 `service-a` 创建独立 KSA，绑定到权限最小化的 GSA
   - 移除 Pod 对 Node 默认服务账户的依赖（`automountServiceAccountToken: false`，参考 `assets/workload-identity-pod.yaml`）
   - 为 GSA 仅授予业务必需的 IAM 角色，避免 `roles/editor` 等宽权限

5. **部署 Network Policy 白名单（对应 SKILL.md 工作流 3）**
   - 先启用 Network Policy Logging（工作流 7）采集 3-7 天流量画像
   - 基于画像生成允许规则，再应用 `assets/default-deny-netpol.yaml` 作为兜底
   - 确保 DNS 出站（kube-dns）、必要的 Google API 出站、以及 Pod 间合法调用在白名单中

6. **强制 Pod Security Standards（对应 SKILL.md 工作流 5）**
   - 对所有非系统命名空间打标：
     ```
     pod-security.kubernetes.io/enforce=restricted
     pod-security.kubernetes.io/enforce-version=latest
     ```
   - 参考 `assets/workload-identity-pod.yaml` 中的 `securityContext` 配置（`runAsNonRoot`、`readOnlyRootFilesystem`、`allowPrivilegeEscalation: false`、`capabilities.drop: ALL`、`seccompProfile: RuntimeDefault`）

7. **高风险工作负载移入 GKE Sandbox（对应 SKILL.md 工作流 4）**
   - 对处理外部输入或不可信代码的工作负载（如 `web` 系统）添加 `runtimeClassName: gvisor`
   - 注意：启用 GKE Sandbox 属于集群节点池级操作（平台级），需先由 `gke-platform-security` 完成节点池配置，本 Skill 仅负责 Pod 规格侧的 `runtimeClassName` 设置

### 5.3 长期治理（1 个月内）

8. **Secret Manager CSI 集成（对应 SKILL.md 工作流 6）**
   - 将数据库凭据、API 密钥等从 Kubernetes Secret 迁移至 Secret Manager，通过 CSI Driver 挂载
   - 减少静态密钥泄露面，支持自动轮换

9. **日志完整性修复（针对 R4）**
   - 排查 `malformed_record` 的根因：是日志采集代理故障、字段映射错误，还是上游应用输出格式异常
   - 建立日志质量监控，对缺失关键字段（`severity`、`user`、`source_ip`）的记录触发告警

10. **Policy Controller 部署（对应 SKILL.md 最佳实践 6）**
    - 考虑部署 Gatekeeper/Policy Controller，在集群范围强制执行自定义安全策略（如禁止 `latest` 标签、强制资源配额、禁止主机网络）

---

## 六、复测清单

修复完成后，按以下清单逐项验证。标注 **[需真实集群]** 的项需要 `gcloud` 认证和集群访问权限，当前环境无法执行。

### 6.1 身份与访问

| 编号 | 复测项 | 方法 | 预期结果 | 状态 |
|---|---|---|---|---|
| V1 | Workload Identity 已启用 | `audit_cluster.sh <cluster> <region> <project>` 检查 `WI_CONFIG` | 非 `DISABLED` | [需真实集群] |
| V2 | `service-a` 使用独立 KSA 而非 Node 默认账户 | `kubectl get pod -l app=service-a -o jsonpath='{.spec.serviceAccountName}'` | 非 `default` | [需真实集群] |
| V3 | `automountServiceAccountToken: false` | `kubectl get pod <pod> -o jsonpath='{.spec.automountServiceAccountToken}'` | `false` | [需真实集群] |
| V4 | GSA 仅绑定最小 IAM 角色 | `gcloud projects get-iam-policy <project> --filter='serviceAccount:<gsa>'` | 无 `roles/editor`/`owner` | [需真实集群] |
| V5 | `token_scope_mismatch` 事件不再出现 | 查看 Cloud Logging / 应用日志 | 24 小时内无新事件 | [需真实集群] |

### 6.2 网络隔离

| 编号 | 复测项 | 方法 | 预期结果 | 状态 |
|---|---|---|---|---|
| V6 | Network Policy 已启用 | `audit_cluster.sh` 检查 `NETPOL_ENABLED` 或 `DATAPATH_PROVIDER=ADVANCED_DATAPATH` | `true` 或 `ADVANCED_DATAPATH` | [需真实集群] |
| V7 | default-deny 策略已应用 | `kubectl get networkpolicy default-deny-all -n <ns>` | 存在且 `policyTypes` 含 `Ingress, Egress` | [需真实集群] |
| V8 | 非白名单流量被拒绝 | 从测试 Pod 尝试访问未授权端口 | `Connection refused` / 超时 | [需真实集群] |
| V9 | Network Policy Logging 已启用 | `kubectl get networklogging default -o yaml` | `spec.cluster.deny.log: true` | [需真实集群] |
| V10 | `203.0.113.8` 无法访问 db | 从该 IP 模拟连接 | 被防火墙/NetworkPolicy 阻断 | [需真实集群] |

### 6.3 Pod 安全

| 编号 | 复测项 | 方法 | 预期结果 | 状态 |
|---|---|---|---|---|
| V11 | 命名空间 enforce=restricted | `kubectl get ns <ns> -o jsonpath='{.metadata.labels.pod-security\.kubernetes\.io/enforce}'` | `restricted` | [需真实集群] |
| V12 | Pod 以非 root 运行 | `kubectl get pod <pod> -o jsonpath='{.spec.securityContext.runAsNonRoot}'` | `true` | [需真实集群] |
| V13 | 根文件系统只读 | `kubectl get pod <pod> -o jsonpath='{.spec.containers[0].securityContext.readOnlyRootFilesystem}'` | `true` | [需真实集群] |
| V14 | 高风险工作负载使用 gVisor | `kubectl get pod <pod> -o jsonpath='{.spec.runtimeClassName}'` | `gvisor` | [需真实集群] |

### 6.4 日志与审计

| 编号 | 复测项 | 方法 | 预期结果 | 状态 |
|---|---|---|---|---|
| V15 | 无 malformed_record | 检查日志管道输出 | 24 小时内无空字段记录 | [需真实集群] |
| V16 | `unexpected_export` 不再出现 | 数据库审计日志 | 无 critical 级导出事件 | [需真实集群] |
| V17 | 暴力破解源 IP 已封禁 | 防火墙规则 / WAF 日志 | `198.51.100.23` 连接被拒 | [需真实集群] |

### 6.5 当前环境可执行的静态验证

| 编号 | 复测项 | 方法 | 预期结果 | 状态 |
|---|---|---|---|---|
| V18 | `default-deny-netpol.yaml` 语法正确 | YAML 解析 | `podSelector: {}`，`policyTypes` 含 Ingress+Egress | **通过**（已读取验证） |
| V19 | `workload-identity-pod.yaml` 安全上下文完整 | YAML 解析 | 含 `runAsNonRoot`、`readOnlyRootFilesystem`、`allowPrivilegeEscalation: false`、`capabilities.drop: ALL`、`seccompProfile` | **通过**（已读取验证） |
| V20 | `audit_cluster.sh` 参数校验逻辑 | 代码审查 | 缺少参数时 `exit 1` 并打印用法 | **通过**（已读取验证） |

---

## 七、依赖、风险与未决事项

### 7.1 关键依赖

1. **`gcloud` CLI 认证**：所有集群侧修复和复测均依赖已认证的 `gcloud`，当前环境未配置。
2. **`jq` 安装**：`audit_cluster.sh` 依赖 `jq` 解析集群 JSON，当前环境未确认安装。
3. **集群访问权限**：需要 `container.clusters.get`、`container.deployments.update` 等 IAM 权限。
4. **Dataplane V2 状态**：决定 Network Policy 启用路径（内置 vs 需手动启用插件），当前未知。
5. **Secret Manager CSI Driver**：修复建议 8 依赖该驱动已在集群启用，当前未知。

### 7.2 执行风险

1. **业务中断风险**：default-deny 策略若未先梳理白名单直接应用，将导致命名空间内所有服务通信中断。
2. **权限收紧过度风险**：`service-a` 的 IAM 角色若收紧过度，可能导致正常业务调用失败，需配合灰度和回滚预案。
3. **日志误判风险**：`token_scope_mismatch` 可能是良性的权限不足报错而非恶意利用，在未结合 IAM 审计日志确认前不应直接定性为入侵。
4. **窗口局限风险**：日志仅覆盖 9 分钟，可能存在窗口外的前期侦察或后续横向移动，本报告结论受此窗口限制。

### 7.3 未决事项（需人工/平台侧跟进）

1. **Shielded Nodes 与 Binary Authorization 状态**：`audit_cluster.sh` 可检查，但修复归 `gke-platform-security` Skill。
2. **RBAC 加固**：`admin` 账户暴力破解的彻底解决需 RBAC 层面的账户锁定和 MFA，不属于本 Skill。
3. **数据库审计**：`unexpected_export` 的具体导出内容和影响范围需数据库平台侧审计日志确认。
4. **恶意 IP 归属与封禁**：`203.0.113.8` 和 `198.51.100.23` 的封禁需网络安全团队在云防火墙/WAF 层执行。

---

## 八、实际读取的 Skill 文件清单

以下为本次审计实际读取的文件（相对于解压根目录 `gke-workload-security-extracted/`）：

| 相对路径 | 用途 |
|---|---|
| `gke-workload-security/SKILL.md` | Skill 主文档，工作流与边界定义 |
| `gke-workload-security/assets/default-deny-netpol.yaml` | 默认拒绝网络策略资产 |
| `gke-workload-security/assets/workload-identity-pod.yaml` | Workload Identity 测试 Pod 资产 |
| `gke-workload-security/scripts/audit_cluster.sh` | 集群安全审计脚本 |

未读取或不存在的文件：无（ZIP 内全部 4 个文件均已读取）。

---

## 九、影响结果的 SKILL.md 关键规则

以下规则直接影响了本报告的分析范围、修复建议和复测清单：

> **SKILL.md 描述段明确声明：**"Don't use for cluster-wide control plane security, RBAC hardening, Binary Authorization, Shielded Nodes, or enabling platform-level GKE add-ons (use gke-platform-security instead)."

**影响**：尽管 `audit_cluster.sh` 脚本会检查 Shielded Nodes 和 Binary Authorization 状态，但根据此边界规则，本报告将这两项标记为"需转交 gke-platform-security"，未在工作负载级修复建议中包含其启用操作。同样，`admin` 账户暴力破解的 RBAC 层面修复（账户锁定、MFA）也被排除在本报告范围外，仅给出网络层和身份层的工作负载级缓解建议。这一规则直接决定了修复建议 5.1-5.3 的边界划分，以及复测清单中 V1-V17 均标注"[需真实集群]"且部分项需跨 Skill 协作。

---

*报告结束。本报告基于 `incident_log.csv` 的静态分析生成，未对任何真实 GKE 集群执行操作。所有集群侧修复和复测均需在授权环境中由具备相应权限的管理员执行。*
