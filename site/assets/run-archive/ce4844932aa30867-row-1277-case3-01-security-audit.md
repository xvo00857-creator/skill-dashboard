# GKE 工作负载安全审计报告（模拟日志静态分析）

- 报告生成时间：2026-08-26（UTC）
- 依据 Skill：`gke-workload-security`（分类：安全与合规）
- 输入文件：`incident_log.csv`、`edge_cases.csv`
- 分析模式：仅在授权测试范围内对模拟安全日志做静态分析；未对任何真实集群执行 `kubectl` / `gcloud` 变更操作。

---

## 1. 执行范围与 Skill 边界

本报告严格以实际读取到的 `SKILL.md` 为唯一执行依据。该 Skill 覆盖：集群安全审计脚本（只读检查）、Workload Identity、Network Policy、GKE Sandbox（gVisor）、Pod Security Standards、Secret Manager CSI、Dataplane V2 Network Logging。

**明确不在本 Skill 范围内（需转交 `gke-platform-security`）**：集群控制平面安全、RBAC 加固、Binary Authorization 启用、Shielded Nodes 启用、平台级 GKE 插件启用。`audit_cluster.sh` 虽对后两项做只读检查，但其"启用"类修复不属于本 Skill。

**输入与 Skill 原生对象的差异**：两份输入为通用应用层日志（web / api / db）与边界测试数据，并非 GKE 集群审计日志。因此本报告将日志事件映射到 GKE 工作负载层控制面（身份、网络、密钥、Pod 安全）给出修复建议；无法直接套用 `audit_cluster.sh` 的集群级检查结论。

---

## 2. 输入完整性校验（缺失 / 重复 / 异常 / 不安全输入）

### 2.1 `incident_log.csv`

- **格式异常**：文件首行是字面量 `csv`，其后为 Markdown 表格（`|...|`），并非标准逗号分隔 CSV。已按表格语义解析，不影响事件识别，但属于采集/导出格式缺陷，应在入仓前规范化。
- **字段缺失（malformed_record）**：`2026-08-12T09:09:00Z` 的 `web` 记录，`severity`、`user`、`source_ip` 三列均为空。判定为**不完整记录**，无法独立定级，需回溯原始采集端补全或丢弃。
- **重复/聚集模式**：`admin` 账户在 4 秒内（09:03:45、09:03:49）从同一 IP `198.51.100.23` 连续两次 `login_failed`。非完全重复行，但构成**暴力破解/撞库尝试模式**。
- **可疑用户字段**：`critical` 级 `unexpected_export` 事件的 `user=unknown`，身份不可归因。

### 2.2 `edge_cases.csv`

| record_id | 问题类型 | 证据 | 处置 |
|---|---|---|---|
| 2 | **完全重复行** | 两行 `2,ok,120,重复记录` 完全一致 | 去重，保留一条 |
| 3 | **字段缺失** | `status`、`value` 为空，`notes=-` | 标记为无效记录，不入统计 |
| 4 | **异常负值** | `status=error`，`value=-999` | 值域校验拦截，负值不应进入正常指标 |
| 5 | **公式注入测试文本** | `value` 为 `=HYPERLINK(...)` 形式字符串 | **按纯文本处理，绝不执行/求值**；导出到 Excel/表格时前置单引号 `'` 或强制文本格式 |

> 关于 record_id=5：该字段内容为 CSV 公式注入（CSV Injection）测试载荷。本报告全程将其作为**字面字符串**展示与分析，未在任何电子表格或脚本中执行。原始载荷见第 6 节复测清单，已用代码块包裹并加中性化说明。

---

## 3. 风险分级与证据

### 严重（Critical）

**C-1 数据外泄链：token 越界 → 异常导出（同一源 IP）**

- 证据：
  - `2026-08-12T09:04:02Z` `api` `high` `token_scope_mismatch`，`user=service-a`，`source_ip=203.0.113.8`
  - `2026-08-12T09:07:30Z` `db` `critical` `unexpected_export`，`user=unknown`，`source_ip=203.0.113.8`
- 关联分析：两事件源 IP 相同，间隔约 3 分 28 秒，呈现"先获取越权令牌 → 再以不可归因身份导出数据"的典型横向移动/数据外泄链。
- 影响面：数据库敏感数据可能已被外传；`service-a` 的令牌权限边界失效。

### 高（High）

**H-1 服务令牌权限范围不匹配（token_scope_mismatch）**

- 证据：同 C-1 中 `service-a` 事件。
- 分析：服务账户令牌被用于超出其声明 scope 的操作，违反最小权限原则；可能是令牌配置错误、令牌泄露后被滥用，或身份混淆（Workload Identity 绑定错误）。

### 中（Medium）

**M-1 管理员账户暴力破解尝试**

- 证据：`admin` 在 4 秒内从 `198.51.100.23` 连续两次 `login_failed`。
- 分析：样本量仅 2 次，未达常见阈值，但时间高度集中且目标为高权限 `admin` 账户，应按撞库/爆破前兆处置。

**M-2 日志完整性缺陷（malformed_record）**

- 证据：`2026-08-12T09:09:00Z` 记录缺失 `severity`/`user`/`source_ip`。
- 分析：可能是采集端 bug，也可能是日志被篡改或注入的掩护行；在安全事件时间窗内出现不完整记录需重点排查。

### 低（Low）

**L-1 边界数据质量问题（edge_cases 全量）**

- 重复行、空字段、异常负值、公式注入文本。本身不构成入侵事件，但反映数据管道缺乏校验与清洗，会降低审计可信度。

---

## 4. 修复建议（映射到 `gke-workload-security` 工作流）

### 4.1 针对 C-1 / H-1（身份与最小权限）

- **启用并规范 Workload Identity**（Skill 工作流 2）：将 `service-a` 从节点默认服务账户迁移到独立 KSA，并绑定最小权限 GSA；核验 `iam.gke.io/gcp-service-account` 注解与 IAM `roles/iam.workloadIdentityUser` 成员是否一一对应，排除身份混淆。
- **令牌 scope 收敛**：审查 `service-a` 的 OAuth / GSA 角色，移除未使用权限；令牌应按服务粒度签发，避免共享。
- **参考资产**：`assets/workload-identity-pod.yaml`（已含 `automountServiceAccountToken: false`、`runAsNonRoot`、`readOnlyRootFilesystem`、`drop ALL capabilities`、`seccompProfile: RuntimeDefault`），可作为 `service-a` Pod 规范基线。

### 4.2 针对 C-1（网络隔离与外泄阻断）

- **应用默认拒绝 NetworkPolicy**（Skill 工作流 3）：对承载 `service-a` 与数据库的命名空间分别应用 `assets/default-deny-netpol.yaml`，再按需放行最小化 ingress/egress；数据库命名空间应仅允许来自授权应用的 egress，禁止直接对外。
- **启用 Dataplane V2 Network Logging**（Skill 工作流 7）：部署 `NetworkLogging` CR，将 allow/deny 连接日志接入 Cloud Logging，用于回溯 `203.0.113.8` 的实际连接路径。
- 若集群未启用 Dataplane V2，按 Skill 说明通过 `--update-addons=NetworkPolicy=ENABLED` 开启；已启用 DPv2 时该步骤可跳过且可能失败。

### 4.3 针对 M-1（入口防护）

- 在应用层前增加登录速率限制与账户锁定；对 `admin` 类高权限账户强制 MFA 与来源 IP 白名单。
- 若 `admin` 为共享通用账户，应拆分为个人身份账户，避免不可归因。

### 4.4 针对 M-2 / L-1（日志与数据质量）

- 日志入仓前增加 schema 校验：`severity`、`user`、`source_ip` 为必填，缺失则进入死信队列并告警。
- 对 `edge_cases` 类数据管道：去重（按 `record_id`）、非空校验、值域校验（`value >= 0`）、公式注入中性化（导出时强制文本或前置 `'`）。
- 公式注入载荷**不得**被任何表格软件自动求值；建议在采集端即检测 `=`/`+`/`-`/`@` 开头的单元格并转义。

### 4.5 Pod 安全基线（预防性）

- 对所有非系统命名空间强制 Pod Security Standards `restricted`（Skill 工作流 5）：
  `kubectl label --overwrite ns <namespace> pod-security.kubernetes.io/enforce=restricted pod-security.kubernetes.io/enforce-version=latest`
- 不可信或高风险工作负载放入 GKE Sandbox（`runtimeClassName: gvisor`，Skill 工作流 4）。
- 敏感凭据改用 Secret Manager CSI 驱动挂载（Skill 工作流 6），避免使用默认 Kubernetes Secret。

---

## 5. 不可执行项、证据与降级方案

### 5.1 `scripts/audit_cluster.sh` 无法执行

- **预期命令**：`scripts/audit_cluster.sh <cluster-name> <region> <project-id>`
- **前置依赖**（SKILL.md 明确要求）：`gcloud` CLI 已认证、`jq` 已安装、需提供集群名/区域/项目 ID。
- **实际环境证据**：
  - `gcloud`：未安装（`command -v gcloud` → NOT_FOUND）
  - `kubectl`：未安装
  - `jq`：已安装（`/usr/bin/jq`）
  - 未提供 `<cluster-name>` / `<region>` / `<project-id>`，也无 GCP 认证凭据
- **结论**：脚本无法运行，**未产生任何集群级审计结果**；本报告不编造 PASS/FAIL。
- **降级方案**：以应用层日志静态分析 + Skill 最佳实践清单替代集群实时审计；所有修复建议均为声明式，需在具备权限的环境中人工执行。
- **复测方法**：在安装并认证 `gcloud`、安装 `jq` 的环境中，执行
  `bash scripts/audit_cluster.sh <cluster-name> <region> <project-id>`，
  核对 Workload Identity、Network Policy（含 DPv2）、Shielded Nodes、Binary Authorization、Private Nodes 六项输出；其中 Shielded Nodes / Binary Authorization 的"启用"修复需转交 `gke-platform-security`。

### 5.2 所有 `kubectl apply` / `gcloud` 变更均未执行

- 原因：无集群访问凭据，且任务要求禁止破坏性操作；NetworkPolicy、PSS 标签、Workload Identity 绑定、SecretProviderClass 均仅给出建议，未实际下发。
- 复测方法：在测试命名空间先以 `kubectl apply --dry-run=server -f ...` 校验，再灰度应用，并用 `kubectl get networkpolicy,pod -n <ns>` 与 Network Logging 验证。

---

## 6. 复测清单

| 编号 | 复测项 | 方法 | 通过标准 |
|---|---|---|---|
| R-1 | 集群安全审计脚本 | `audit_cluster.sh <cluster> <region> <project>` | 六项检查均有明确 PASS/WARN/FAIL，无脚本错误 |
| R-2 | Workload Identity 绑定 | `gcloud iam service-accounts get-iam-policy <gsa>` + `kubectl get sa <ksa> -o yaml` | KSA 注解与 IAM 成员一致，`service-a` 仅持最小权限 |
| R-3 | 默认拒绝 NetworkPolicy | `kubectl apply -f assets/default-deny-netpol.yaml -n <ns>` 后测试非白名单流量 | 非授权 ingress/egress 被拒绝，授权流量正常 |
| R-4 | Network Logging | 部署 `NetworkLogging` CR 后查看 Cloud Logging | allow/deny 日志可查，含 `203.0.113.8` 回溯记录 |
| R-5 | PSS restricted | `kubectl label ns <ns> pod-security.kubernetes.io/enforce=restricted` | 违规 Pod 被拒绝，现有工作负载无异常重启 |
| R-6 | 暴力破解防护 | 模拟短时间多次失败登录 | 触发速率限制/锁定，告警可达 |
| R-7 | 日志 schema 校验 | 重放含空字段的 malformed_record | 进入死信队列并触发告警，不混入主索引 |
| R-8 | 公式注入中性化 | 将 record_id=5 行导出到 Excel/Sheets | 单元格显示为字面文本，无链接/执行，公式不被求值 |
| R-9 | 数据管道清洗 | 输入含重复/空值/负值的 edge_cases | 重复去重、空值剔除、负值拦截，统计结果可复现 |

> record_id=5 原始载荷（仅作证据，按纯文本展示，禁止执行）：
> ```text
> =HYPERLINK("https://example.invalid","do not execute")
> ```

---

## 7. 附录：实际读取的 Skill 文件（相对路径）

解压根目录：`gke-workload-security/`

- `SKILL.md`
- `scripts/audit_cluster.sh`
- `assets/default-deny-netpol.yaml`
- `assets/workload-identity-pod.yaml`

未读取、未引用任何上述清单之外的文件；未访问外部网络或 GCP 平台。

---

## 8. 影响结果的关键 SKILL.md 规则（至少一条）

1. **范围边界规则**：`SKILL.md` 明确"Don't use for cluster-wide control plane security, RBAC hardening, Binary Authorization, Shielded Nodes, or enabling platform-level GKE add-ons (use gke-platform-security instead)"。该规则直接决定：本报告对 Shielded Nodes、Binary Authorization 仅做只读提及，其"启用"修复必须转交平台级 Skill，不得在本报告中给出启用命令。
2. **审计脚本前置依赖规则**：`SKILL.md` 要求 `gcloud` CLI 已认证且 `jq` 已安装，并需传入 `<cluster-name> <region> <project-id>`。因实际环境无 `gcloud`/`kubectl`、无凭据、无集群参数，该规则直接导致 `audit_cluster.sh` 不可执行，报告采用静态分析降级方案而非伪造集群审计结果。
3. **Dataplane V2 例外规则**：`SKILL.md` 注明若集群已启用 Dataplane V2，Network Policy 强制执行内置，`--update-addons=NetworkPolicy=ENABLED` 步骤可跳过且可能失败。该规则影响网络策略修复路径的选择，避免在 DPv2 集群上执行无效/报错命令。
