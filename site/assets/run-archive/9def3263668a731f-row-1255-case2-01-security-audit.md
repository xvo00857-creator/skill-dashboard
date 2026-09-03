# 模拟安全日志审计报告（security-audit）

- 审计对象：`incident_log.csv`（授权测试范围内的模拟安全日志）
- 执行依据：随包 Skill `gke-basics` 的 `SKILL.md` 及其 `references/` 目录（以实际读取内容为准）
- 审计性质：只读分析 + 修复建议 + 复测清单；未执行任何破坏性操作
- 报告生成时间基准：2026-08-26（UTC）

---

## 1. 审计范围与方法

### 1.1 输入文件

`incident_log.csv` 实际为管道符（`|`）分隔的表格式样，首行仅含 `csv` 标记，并非标准逗号分隔 CSV。共解析出 6 条事件记录，字段为：`timestamp | system | severity | event | user | source_ip`。

### 1.2 方法

1. 逐条解析事件，按 `severity` 与 `event` 类型做初判。
2. 跨记录做关联分析（同源 IP、时间邻近、用户身份缺失）。
3. 以 `gke-basics` Skill 中实际存在的安全条款作为修复基线（见第 5 节），不引入 Skill 未声明的外部平台数据或凭据。
4. 所有结论限定在"基于现有 6 条记录"的证据范围内；对缺失字段与异常记录显式标注不确定性。

---

## 2. 数据质量发现

| 编号 | 问题 | 影响 |
|---|---|---|
| DQ-1 | 文件首行为 `csv` 字面量，主体为 Markdown 管道表，非标准 CSV | 解析需特殊处理；提示上游导出/采集格式不规范 |
| DQ-2 | 第 6 条记录 `severity`、`user`、`source_ip` 均为空，`event=malformed_record` | 日志完整性存疑，可能掩盖同期真实事件，削弱归因确定性 |

> 结论：本报告所有归因均为"基于可用记录的最强推断"，不排除被 malformed 记录或未导出事件改变结论的可能。

---

## 3. 事件明细与风险分级

### 3.1 事件总表

| # | 时间 (UTC) | 系统 | 严重级 | 事件 | 用户 | 源 IP | 风险等级 |
|---|---|---|---|---|---|---|---|
| 1 | 2026-08-12 09:00:12 | web | info | login_success | alice | 192.0.2.10 | 信息（无风险） |
| 2 | 2026-08-12 09:03:45 | web | warning | login_failed | admin | 198.51.100.23 | 中 |
| 3 | 2026-08-12 09:03:49 | web | warning | login_failed | admin | 198.51.100.23 | 中（与 #2 合并评估） |
| 4 | 2026-08-12 09:04:02 | api | high | token_scope_mismatch | service-a | 203.0.113.8 | 高 |
| 5 | 2026-08-12 09:07:30 | db | critical | unexpected_export | unknown | 203.0.113.8 | 严重 |
| 6 | 2026-08-12 09:09:00 | web | （空） | malformed_record | （空） | （空） | 低（完整性隐患） |

### 3.2 逐条证据与判定

**事件 #1 — login_success（alice，192.0.2.10）**
- 证据：info 级，单一成功登录，时间在异常序列之前，无关联异常。
- 判定：正常基线事件，保留为对照。

**事件 #2、#3 — admin 登录失败（198.51.100.23）**
- 证据：同一源 IP 在 4 秒内对 `admin` 账户连续两次登录失败（09:03:45、09:03:49）。
- 判定：暴力破解/凭证撞库的早期特征。当前仅 2 次，定为"中"；若同窗口内失败次数 ≥5 或后续出现成功登录，应立即升级为"高/严重"。
- 关联：该 IP 与后续 API/DB 异常 IP（203.0.113.8）不同，暂视为独立攻击源。

**事件 #4 — token_scope_mismatch（service-a，203.0.113.8）**
- 证据：high 级，服务账户 `service-a` 发起的令牌作用域不匹配，源 IP 203.0.113.8。
- 判定：服务凭据被滥用、越权调用或令牌配置错误的强信号。若为误配则是高风险运维缺陷；若为人为利用则是横向移动起点。
- 关键关联：与事件 #5 同源 IP，且时间上 #4 先于 #5 约 3 分 28 秒，构成"令牌异常 → 数据导出"的疑似攻击链。

**事件 #5 — unexpected_export（unknown，203.0.113.8）**
- 证据：critical 级，数据库发生非预期导出，用户字段为 `unknown`，源 IP 与 #4 相同。
- 判定：本次最严重事件，疑似数据外泄。`unknown` 用户意味着身份未被正确采集或被冒用/清洗，进一步加重风险。
- 关联：与 #4 同源 IP + 时间先后，强烈提示同一行动链；但因 #5 用户为 unknown，不能在法律/取证意义上直接等同于 `service-a`，需额外证据（见复测清单）。

**事件 #6 — malformed_record（空字段）**
- 证据：severity/user/source_ip 全部缺失，event 自描述为 malformed_record。
- 判定：低直接风险，但属于日志完整性隐患。若为采集故障，说明审计链路不可靠；若为人为篡改，则可能掩盖了 09:09 前后的真实事件。

---

## 4. 关联分析与攻击链假设

### 4.1 疑似攻击链 A（高置信度）

```
09:04:02  token_scope_mismatch (service-a, 203.0.113.8)
   │  令牌作用域异常，可能获取了超出预期的访问能力
   ▼
09:07:30  unexpected_export (unknown, 203.0.113.8)
   │  同源 IP，约 3.5 分钟后发生数据库非预期导出
   ▼
09:09:00  malformed_record (空字段)
          时间点紧邻导出之后，日志完整性异常
```

- 推断：攻击者或失控服务先利用 `service-a` 的令牌越权访问 API，随后利用获得的能力导出数据库数据，期间或之后日志出现异常记录。
- 置信度：中-高（同源 IP + 时间顺序强相关，但 #5 用户为 unknown，缺少直接身份链）。

### 4.2 独立事件 B（中置信度）

- 09:03:45–09:03:49，198.51.100.23 对 `admin` 的两次快速登录失败。
- 与攻击链 A 无 IP 关联，暂列为独立的暴力破解尝试；需检查该 IP 在更长时间窗口内是否有更多失败或最终成功。

---

## 5. 约束、冲突与关键取舍

本审计在执行中遇到以下约束与冲突，均实际影响了结论形态与修复建议的边界。

### 冲突 1：Skill 标注分类与实际内容范围错配

- 事实：任务题面将 `gke-basics` 标注为分类"安全与合规"，但实际读取的 `SKILL.md` 前端元数据为 `category: Containers`，描述为"Manages core GKE cluster provisioning, credentials, Autopilot vs Standard selection, and workload deployment"，并明确声明"Don't use for ... advanced security hardening (use gke-platform-security or gke-workload-security)"。
- 影响：该 Skill **不包含**安全日志分析流程、风险分级方法论或事件响应 playbook。因此本报告的分析框架（分级、关联、复测）是基于通用安全审计实践构建的，而非 Skill 规定的步骤；修复建议则严格回退到 Skill 中**实际存在**的安全条款（Workload Identity、禁止挂载 SA JSON 密钥、私有集群、Pod Security Standards restricted、Shielded Nodes）。
- 关键取舍：宁可缩小 Skill 可支撑的结论范围，也不编造 Skill 未声明的安全能力。若需深度硬化，应按 Skill 自身指引转用 `gke-platform-security` / `gke-workload-security`。
- 依赖：修复建议的可执行性依赖目标环境确为 GKE 集群；若非 GKE，则 Skill 条款仅作参考。
- 风险：若误把本 Skill 当作完整安全合规依据，会遗漏网络隔离、运行时威胁检测等高级硬化项。

### 冲突 2：无集群/凭据 + 禁止破坏性操作

- 事实：任务要求"禁止实施破坏性操作"，且本次未提供任何 GCP 项目 ID、区域、集群名、`kubeconfig` 或服务账号凭据。Skill 的 `cli-reference.md` 与 `mcp-usage.md` 中，`update_cluster`、`apply_k8s_manifest`、`patch_k8s_resource`、`delete_k8s_resource`、`cancel_operation` 均被标注为 `DESTRUCTIVE`，`create_cluster`/`create_node_pool` 为 `MUTATE`。
- 影响：所有修复建议均为**策略级/配置级建议**与**只读验证命令**，未实际调用任何 MUTATE/DESTRUCTIVE 工具，也未连接真实集群。复测清单以 READ 类操作（`get_cluster`、`check_k8s_auth`、`list_k8s_events`、`get_k8s_logs`、`gcloud logging read`）为主。
- 关键取舍：在"快速止血（可能需要隔离/吊销令牌，属破坏性）"与"只读审计（不改变现状）"之间，选择后者并把止血动作列为"需授权后执行"的高优先级建议，而不是擅自执行。
- 依赖：实际修复需由具备 `roles/container.admin` 或 `roles/container.clusterAdmin` 的运维人员在变更窗口执行（Skill 错误处理表中 `PERMISSION_DENIED` 条目明确了该角色要求）。
- 风险：在只读审计期间，若攻击链 A 仍在持续，数据可能继续外泄；因此报告同时给出"立即止血"的人工执行建议。

### 冲突 3：日志完整性不足限制归因确定性

- 事实：事件 #6 关键字段全空，且文件格式非标准 CSV。
- 影响：无法对 09:09 前后的事件做完整时序重建；对 #5 的 `unknown` 用户无法排除"被 malformed 记录掩盖了真实身份"的可能。
- 关键取舍：报告采用"基于可用记录的最强推断 + 显式不确定性标注"，而非给出确定性归因。
- 依赖：复测需从原始日志系统（而非此导出文件）重新拉取 09:00–09:15 全量日志。
- 风险：若 malformed 记录实为篡改，则本报告可能低估攻击范围。

---

## 6. 修复建议

以下建议均映射到 `gke-basics` Skill 中实际存在的安全条款；未引入 Skill 未声明的外部产品。

### 6.1 立即止血（需人工授权，属破坏性，本报告未执行）

| 优先级 | 动作 | 依据 |
|---|---|---|
| P0 | 吊销或轮换 `service-a` 的服务凭据，核查其令牌实际被授予的作用域 | 事件 #4 直接证据；Skill "Never mount raw GCP Service Account JSON keys in Pods" 要求改用 Workload Identity |
| P0 | 对源 IP 203.0.113.8 在控制平面与数据库入口执行临时封禁/限流 | 事件 #4、#5 同源 |
| P0 | 核查 09:04–09:09 期间数据库导出的目标位置与数据量，评估外泄范围 | 事件 #5 critical |
| P1 | 对 `admin` 账户触发强制改密并启用登录失败锁定；核查 198.51.100.23 更长时间窗口行为 | 事件 #2、#3 |

### 6.2 身份与凭据硬化（映射 Skill Workload Identity 条款）

- **禁止在 Pod 中挂载原始 GCP 服务账号 JSON 密钥**（SKILL.md Critical Gotchas #2 明确禁止）。
- 改用 Workload Identity：为 `service-a` 对应的 Kubernetes ServiceAccount 标注 `iam.gke.io/gcp-service-account: GSA_NAME@PROJECT_ID.iam.gserviceaccount.com`，通过 KSA→GSA 绑定获取短期令牌，从根上消除静态令牌泄露后被滥用的风险（对应事件 #4 的 token_scope_mismatch）。
- 遵循最小权限：为该 GSA 仅授予完成业务所需的最小 IAM 角色，避免令牌作用域超出预期。
- 启用 Secret Manager 集成并自动轮换（core-concepts.md "Identity & Security Model"）。

### 6.3 网络与控制平面硬化（映射 Skill 私有集群条款）

- 新建或迁移集群至私有 Autopilot 集群，启用：
  - `--enable-private-nodes`（节点无公网 IP）
  - `--enable-private-endpoint`（关闭控制平面公网访问）
  - `--enable-master-authorized-networks` + `--master-authorized-networks=CIDR_BLOCK`（限制控制平面来源）
- 上述配置可直接缩小 203.0.113.8 这类外部 IP 触达控制平面与服务的可能性。
- 已有集群若无法立即重建，至少先收紧 master authorized networks 与 VPC 防火墙规则。

### 6.4 工作负载安全基线（映射 core-concepts.md）

- 生产命名空间强制实施 Pod Security Standards `restricted` 配置（core-concepts.md 明确列为生产默认）。
- 依赖 Autopilot 强制的 Shielded Nodes（Secure Boot + 完整性监控），不自行关闭。
- 默认使用 Autopilot（SKILL.md "Default to Autopilot"），仅在确有自定义 sysctl、节点 taint 或 DaemonSet hostPath 需求时才使用 Standard，并需显式列出全部限制理由。

### 6.5 日志与审计链路修复

- 修复 malformed_record 对应的采集/导出链路，确保 `severity`、`user`、`source_ip` 非空校验；对空字段记录做旁路告警而非静默丢弃。
- 统一导出格式为标准 CSV 或 JSON，避免首行 `csv` 标记 + 管道表的非标格式。
- 对日志存储启用防篡改（仅追加）与完整性校验，防止类似 #6 的异常被用于掩盖攻击。

---

## 7. 复测清单

所有复测项均为只读（READ）或查询操作，不包含破坏性变更。执行前需具备有效集群凭据与项目权限。

### 7.1 身份与令牌

- [ ] 核查 `service-a` 对应 KSA 的 `iam.gke.io/gcp-service-account` 注解是否存在且指向正确 GSA。
- [ ] 用 `check_k8s_auth`（MCP，READ）或 `kubectl auth can-i` 验证该服务账户实际可执行的动词与资源，确认无越权。
- [ ] 核查 GSA 的 IAM 策略，确认遵循最小权限，无遗留 broad 角色。
- [ ] 全量搜索集群中是否存在挂载原始 SA JSON 密钥的 Pod（违反 SKILL.md 禁令）。

### 7.2 网络与控制平面

- [ ] 用 `get_cluster`（MCP，READ）或 `gcloud container clusters describe` 核查：`enablePrivateNodes`、`enablePrivateEndpoint`、`masterAuthorizedNetworksConfig` 是否符合第 6.3 节。
- [ ] 核查 VPC 防火墙规则，确认 203.0.113.8、198.51.100.23 无允许入站规则。
- [ ] 核查数据库实例的授权网络与 IAM，确认 `unknown` 导出路径已被阻断。

### 7.3 工作负载安全

- [ ] 核查生产命名空间是否打了 Pod Security Standards `restricted` 标签且无豁免。
- [ ] 核查节点是否启用 Shielded Nodes（Autopilot 默认强制；Standard 需显式确认）。
- [ ] 若为 Standard 集群，记录使用 Standard 的全部理由（自定义 sysctl / 节点 taint / DaemonSet hostPath），否则应评估迁移 Autopilot。

### 7.4 日志与事件回溯

- [ ] 从原始日志系统（非本导出文件）拉取 2026-08-12 09:00:00–09:15:00 全量日志，重点补齐 09:09 前后被 malformed 记录掩盖的部分。
- [ ] 用 `gcloud logging read`（CLI，READ）或 `list_k8s_events`（MCP，READ）查询 203.0.113.8 在该时段的全部事件，确认攻击链 A 的完整路径。
- [ ] 查询 198.51.100.23 在 24 小时窗口内的登录失败/成功次数，确认是否为持续暴力破解。
- [ ] 核查数据库审计日志，定位 `unexpected_export` 的真实执行身份与导出目标。

### 7.5 修复有效性验证

- [ ] 轮换 `service-a` 凭据后，确认旧令牌已失效（用旧令牌调用应返回 401/403）。
- [ ] 封禁 203.0.113.8 后，确认从该 IP 无法建立控制平面或数据库连接。
- [ ] 登录失败锁定策略生效后，模拟连续失败应触发锁定与告警。
- [ ] 日志采集链路修复后，连续产生测试事件，确认导出文件字段完整、格式标准。

---

## 8. 结论

1. **最严重事件**：2026-08-12 09:07:30 的 `unexpected_export`（critical，unknown 用户，203.0.113.8），疑似数据外泄，需立即评估外泄范围并止血。
2. **最强关联**：09:04:02 的 `token_scope_mismatch`（service-a，同源 IP 203.0.113.8）与该导出事件构成"令牌异常 → 数据导出"疑似攻击链，置信度中-高。
3. **独立威胁**：198.51.100.23 对 `admin` 的快速登录失败为暴力破解早期特征，当前中风险，需扩展时间窗口复核。
4. **完整性隐患**：malformed_record 与非标 CSV 格式削弱审计可信度，所有归因均带不确定性。
5. **Skill 边界**：`gke-basics` 实为 Containers 类集群管理 Skill，不含日志分析流程；本报告仅将其安全条款（Workload Identity、禁挂 SA 密钥、私有集群、restricted PSS、Shielded Nodes）作为修复基线，深度硬化需转用 Skill 自身推荐的 `gke-platform-security` / `gke-workload-security`。
6. **执行边界**：因无集群凭据且禁止破坏性操作，本报告未执行任何变更；修复与复测需由授权人员在具备权限的环境中执行。

---

## 附录 A：实际读取的 Skill 文件相对路径

以解压根目录 `gke-basics/` 为基准：

1. `gke-basics/SKILL.md`
2. `gke-basics/references/core-concepts.md`
3. `gke-basics/references/cli-reference.md`
4. `gke-basics/references/client-library-usage.md`
5. `gke-basics/references/mcp-usage.md`
6. `gke-basics/references/iac-usage.md`

## 附录 B：确实影响结果的 SKILL.md 规则（示例）

- **规则**：`SKILL.md` Critical Gotchas #2 — "Never mount raw GCP Service Account JSON keys in Pods"，并给出 KSA 注解 `iam.gke.io/gcp-service-account` 绑定 GSA 的做法。
- **如何影响结果**：该规则直接决定了事件 #4（token_scope_mismatch）的修复方向——不是简单轮换令牌，而是从静态密钥迁移到 Workload Identity 短期令牌，从根上消除令牌滥用面；同时使"全量搜索挂载原始 SA JSON 密钥的 Pod"成为复测必选项。若没有这条规则，修复建议可能停留在凭据轮换层面，无法触及架构性根因。
