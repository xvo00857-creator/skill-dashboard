# 云/K8s 安全审计报告 — incident_log.csv 静态分析

| 项目 | 内容 |
|------|------|
| 报告文件 | security-audit.md |
| 审计对象 | incident_log.csv（模拟安全日志，6 条记录） |
| 审计日期 | 2026-08-13（UTC+8） |
| 日志时间窗口 | 2026-08-12T09:00:12Z ~ 09:09:00Z（约 9 分钟） |
| 执行依据 | cloud-k8s Skill（SKILL.md + references/k8s-cloud-checklist.md） |
| 授权范围 | 仅对随附的模拟日志文件做离线分析；禁止任何破坏性操作 |
| 分析方式 | 静态日志分析（无实时云账号 / 无 kubeconfig / 无工具链） |

---

## 1. 授权与边界声明（对应 SKILL.md Phase 1「身份与边界」）

- **身份**：本次为离线分析，不使用任何云 AK/SK、K8s ServiceAccount 令牌或节点 SSH 凭证；不存在对真实云环境或集群的交互。
- **范围**：单文件 `incident_log.csv`，单一时段（2026-08-12 09:00–09:09 UTC）。网络档为 `authorized_target_only`，未对任何主机或 IP 发起扫描或连接。
- **破坏性操作**：全程未执行、也未建议任何删除、覆盖、导出真实数据、持久化后门等操作；修复建议均为配置加固与凭证轮换类防御措施。
- **数据性质**：日志中出现的 `192.0.2.10`、`198.51.100.23`、`203.0.113.8` 均属于 RFC 5737 文档保留网段（TEST-NET-1/2/3），确认本日志为模拟数据，不涉及真实第三方系统。

### 1.1 依赖缺口（必须说明）

SKILL.md「ACTION REQUIRED」第 1 条要求：

> `NOW`: 读取 `../field-journal/precedent-pentest.md` — **云/K8s 测试必须书面授权**

经核查，随附 ZIP 仅包含 `SKILL.md` 与 `references/k8s-cloud-checklist.md` 两个文件，`../field-journal/precedent-pentest.md` **在包内不存在**，路径 `cloud-k8s/field-journal/precedent-pentest.md` 无此文件。本报告不编造该文件内容。

**取舍**：用户在任务指令中已明确「仅在授权测试范围内分析模拟安全日志」「禁止实施破坏性操作」，该指令构成本次离线日志分析的书面范围授权，故以此替代缺失的 precedent 文件继续执行；但若后续转为对真实云/K8s 环境的主动测试，必须先补齐该书面授权文件并明确账号/集群边界，否则不得进入 Phase 2–4 的主动探测。

---

## 2. 方法与工具链状态

SKILL.md「NEXT: tool-index」要求核查 kubectl/aws/gcloud 等工具。本机实际检查结果：

| 工具 | 状态 | 用途 |
|------|------|------|
| kubectl / aws / gcloud | 未安装 | 集群与云控制面交互 |
| trivy | 未安装 | 镜像/IaC 扫描 |
| kube-bench / kubeaudit | 未安装 | CIS/配置核查 |
| pacu / scout2 / nuclei | 未安装 | 云审计 / 已知漏洞模板 |

**约束**：本任务输入仅为静态 CSV，未提供云凭证、kubeconfig 或目标端点，因此 SKILL.md Phase 2–4 中所有需要实时执行的命令（`aws sts get-caller-identity`、`kubectl auth can-i --list`、`kubectl get secrets` 等）**均无法执行**，本报告不伪造任何命令输出。所有发现均基于日志内可见字段推断，凡需实时环境验证的结论均标注为「假设」并列复测项。

---

## 3. 日志事件时间线

| # | 时间 (UTC) | 系统 | 严重级 | 事件 | 用户 | 源 IP |
|---|-----------|------|--------|------|------|-------|
| 1 | 09:00:12 | web | info | login_success | alice | 192.0.2.10 |
| 2 | 09:03:45 | web | warning | login_failed | admin | 198.51.100.23 |
| 3 | 09:03:49 | web | warning | login_failed | admin | 198.51.100.23 |
| 4 | 09:04:02 | api | high | token_scope_mismatch | service-a | 203.0.113.8 |
| 5 | 09:07:30 | db | critical | unexpected_export | unknown | 203.0.113.8 |
| 6 | 09:09:00 | web | **（空）** | malformed_record | **（空）** | **（空）** |

---

## 4. 风险分级与发现

### F-01【严重/Critical】数据库异常导出，身份不可解析

- **证据**：第 5 条，`db,critical,unexpected_export,unknown,203.0.113.8`，09:07:30Z。
- **分析**：
  - 事件标记为 `critical`，行为是「非预期导出」，直接对应数据外泄风险。
  - 用户字段为 `unknown`，说明数据库侧未能解析调用方身份——可能是匿名访问、已吊销/伪造的令牌、或日志解析器无法映射的 ServiceAccount。
  - 与 F-02 共享同一源 IP `203.0.113.8`，且时间仅相隔 3 分 28 秒，存在强关联（见第 5 节攻击链假设）。
- **影响**：若导出内容含敏感数据，可能造成数据泄露；身份不可解析意味着访问控制或审计链路存在缺口。
- **置信度**：事件本身为日志确证；其与 F-02 的因果关系为中等置信度假设（见第 6 节约束）。

### F-02【高/High】service-a 令牌作用域不匹配（IAM/SA 权限异常）

- **证据**：第 4 条，`api,high,token_scope_mismatch,service-a,203.0.113.8`，09:04:02Z。
- **分析**：
  - `token_scope_mismatch` 表明 `service-a` 持有的令牌被用于其声明作用域之外的操作，直接命中检查清单「IAM 角色权限面」与 SKILL.md Phase 4「SA token 挂载与权限」。
  - 可能成因：① ServiceAccount 被授予过宽权限（类 cluster-admin 过度绑定）；② 令牌被盗用/重放；③ 令牌以明文环境变量注入容器后泄漏（命中检查清单「secrets 明文环境变量」）；④ 通过云元数据 SSRF 窃取节点 IAM 角色凭证后冒用（检查清单 IMDS 项）。
  - 仅凭日志无法区分上述成因，需实时环境验证。
- **影响**：过宽或被盗的服务令牌可成为横向移动与数据访问的跳板，是 F-01 最可能的前置环节。

### F-03【中/Medium】畸形日志记录，疑似日志完整性事件

- **证据**：第 6 条，`web,,malformed_record,,`，09:09:00Z，severity/user/source_ip 三字段为空。
- **分析**：
  - 该记录发生在 F-01 critical 事件后约 90 秒，时间敏感。
  - 存在两种冲突解释（取舍见第 6.2 节）：
    - (a) 良性：日志采集管道故障/截断/序列化错误；
    - (b) 恶性：攻击者尝试干扰、截断或伪造审计日志以掩盖痕迹。
  - 在 critical 事件后短时间出现，不能默认按良性处理。
- **影响**：若为日志篡改，则审计链可信度下降，可能存在未被记录的后续行为。

### F-04【低/Low】admin 账户短时登录失败

- **证据**：第 2、3 条，`web,warning,login_failed,admin,198.51.100.23`，09:03:45Z 与 09:03:49Z，间隔 4 秒。
- **分析**：
  - 仅 2 次失败、持续 4 秒后停止，未达典型暴力破解阈值；可能为误输、配置错误的自动化任务，或试探性侦察。
  - 源 IP `198.51.100.23` 与后续 F-02/F-01 的 `203.0.113.8` 不同，无法直接并入同一攻击链，但可能是干扰或多源协同。
- **影响**：单独风险低；若与其他时段数据汇总出现频次升高，应升级。

### F-05【信息/Info】正常登录基线

- **证据**：第 1 条，`web,info,login_success,alice,192.0.2.10`。
- **分析**：未见异常，作为基线参考。建议核实 alice 该时段登录是否符合其正常行为画像。

---

## 5. 攻击链假设（中等置信度，需实时验证）

基于 IP 与时序关联，提出如下假设链，**非已确认事实**：

```
09:03:45–09:03:49  admin 登录失败（198.51.100.23）
        │  （可能是侦察/干扰，与后续 IP 不同，关联弱）
09:04:02           service-a 令牌作用域异常（203.0.113.8）
        │  令牌过宽/被盗/被冒用，获得超出预期的 API 权限
09:07:30           数据库非预期导出，身份 unknown（203.0.113.8）
        │  利用异常令牌访问 DB 并批量导出数据
09:09:00           畸形日志记录（字段缺失）
           可能为日志管道故障，或攻击者干扰审计
```

**关键不确定点**：
- `203.0.113.8` 在云/K8s 环境中可能是 NAT 出口 IP，背后可能对应多个 Pod/服务，同 IP 不等于同一主体。
- `unknown` 可能是真实匿名访问，也可能是日志解析器未能映射 ServiceAccount 名称。
- 无网络流日志、云审计日志（CloudTrail/Audit Log）、K8s Audit Policy 日志佐证，无法闭环。

---

## 6. 约束、冲突与关键取舍

### 6.1 约束一：Skill 主动测试工作流 vs. 仅静态日志输入

- **冲突**：SKILL.md Phase 2–4 设计为对实时云控制面、容器、K8s 集群执行命令核查（`kubectl auth can-i --list`、IMDS 可达性测试、特权容器检查等），但本次既无目标环境也无凭证，且工具链全部缺失。
- **取舍**：严格遵守 SKILL.md「MUST NOT: 未授权扫公有云其他租户」与「禁止破坏性操作」，不尝试连接任何真实端点、不安装重型扫描工具去扫公网。改为以日志字段为证据，将所有需要实时确认的检查项转化为「假设 + 复测清单」，而不是伪造 `kubectl`/`aws` 输出。
- **影响**：发现的置信度分层——日志内确证的事件为高置信；成因与攻击链为中/低置信，必须经实时复测确认。

### 6.2 约束二：畸形记录的「管道故障」vs.«日志篡改」定性冲突

- **冲突**：F-03 既可解释为采集管道 bug（降低严重级），也可解释为攻击者反取证（提升严重级）。在缺少日志代理健康指标、采集端错误率、同时间窗口其他记录的情况下，无法二选一。
- **取舍**：不强行二分。鉴于其紧邻 critical 事件（90 秒后），按「可疑、待管道侧验证」处理，定级 Medium，并在复测清单中要求同时核查日志管道健康与是否存在篡改痕迹。若管道监控显示同期无故障，则升级为 High 并启动事件响应。

### 6.3 其他依赖与风险

- **缺少 precedent-pentest.md**：见 1.1 节，主动测试前必须补齐。
- **缺少上下文数据**：无 K8s Audit Log、无云侧 CloudTrail/Activity Log、无网络流日志、无 DB 审计明细，无法确认导出的数据范围与去向（是否写入公开存储桶等）。
- **日志保留窗口短**：仅 9 分钟样本，无法判断 F-04 是否为更长时间暴力破解的一部分，也无法确认 F-03 之后是否还有后续行为。
- **IP 归属限制**：TEST-NET 网段无法用于真实威胁情报比对。

---

## 7. 与 Skill 检查清单的映射

| 检查清单（k8s-cloud-checklist.md / SKILL.md） | 本日志相关发现 | 状态 |
|------|------|------|
| IMDS：SSRF 是否可达 169.254.169.254 | 日志无直接证据；F-02 令牌异常的可能成因之一 | 待实时验证 |
| IMDS：是否强制 IMDSv2 | 无法从日志判断 | 待实时验证 |
| IMDS：返回的 IAM 角色权限面 | F-02 服务令牌作用域异常直接相关 | 待实时验证 |
| cluster-admin 绑定过多 | F-02 可能成因之一 | 待实时验证 |
| secrets 明文环境变量 | F-02 可能成因之一（令牌泄漏路径） | 待实时验证 |
| privileged + hostPID/hostPath 组合 | 日志无直接证据 | 不适用/待验证 |
| 匿名 auth / insecure apiserver 端口 | F-01 `unknown` 身份可能与匿名访问相关 | 待实时验证 |
| 容器以 root 运行 | 日志无直接证据 | 不适用/待验证 |
| 可加载内核模块 / docker.sock 挂载 | 日志无直接证据 | 不适用/待验证 |
| SA token 挂载与权限（Phase 4） | **F-02 直接命中** | 需整改+复测 |
| 网络策略默认放行（Phase 4） | F-01 DB 导出可能因网络策略过宽 | 待实时验证 |

---

## 8. 修复建议（按优先级）

### P0 — 立即
1. **轮换 service-a 令牌/密钥**：吊销当前令牌，重新签发最小权限令牌；审查 service-a 的 Role/ClusterRoleBinding，移除非必要权限（对照检查清单「cluster-admin 绑定过多」）。
2. **核查 DB 导出影响面**：确认 09:07:30Z 导出的目标、数据范围与去向；若涉及外部存储桶，检查是否为公开桶/错误 ACL（SKILL.md Phase 2「公开桶/错误 ACL」）；按数据分级评估是否需通报。
3. **封禁/审查 `unknown` 访问路径**：在 DB 与 API 网关上拒绝无法解析身份的请求；排查匿名认证配置（K8s `--anonymous-auth`、RBAC 中 system:anonymous 绑定）。

### P1 — 短期
4. **收敛 ServiceAccount 令牌**：
   - 使用 projected service account token（绑定 audience 与过期时间），禁用默认 token auto-mount（`automountServiceAccountToken: false`）。
   - 禁止将密钥/令牌以明文环境变量注入容器，改用 Secrets 挂载或外部 KMS（检查清单「secrets 明文环境变量」）。
5. **加固云元数据**：强制 IMDSv2，评估节点 IAM 角色权限是否遵循最小权限；排查应用是否存在可达 169.254.169.254 的 SSRF 路径。
6. **网络策略**：配置 default-deny NetworkPolicy，仅放行 service-a 到 DB 的必要端口与身份；限制 DB 出口。
7. **日志完整性**：将日志转发至 append-only / WORM 存储（独立账号），启用日志完整性校验；修复或告警 malformed_record。

### P2 — 中期
8. **admin 账户防护**：启用 MFA、登录失败速率限制与锁定策略；调整告警阈值（2 次失败即产生 warning 可保留，但应与其他信号关联）。
9. **镜像与运行时**：在有实时环境后用 trivy 扫描 service-a 相关镜像，kube-bench/kubeaudit 做 CIS 基线核查；检查特权容器、docker.sock 挂载、root 运行。
10. **检测规则**：新增关联规则——同一 IP 内 token_scope_mismatch 后 5 分钟内出现 DB 批量导出即触发高危告警；critical 事件后 15 分钟内出现 malformed/缺失字段日志即触发完整性告警。

---

## 9. 复测清单（需在授权的实时环境执行）

> 以下命令仅在补齐书面授权（precedent-pentest.md）、获得合法账号与 kubeconfig 后，于授权范围内执行。

- [ ] `kubectl get sa service-a -o yaml` 及对应 Role/ClusterRoleBinding，确认权限已收敛、token automount 已禁用。
- [ ] `kubectl auth can-i --list --as=system:serviceaccount:<ns>:service-a`，确认无过宽权限（尤其无 `*`/cluster-admin）。
- [ ] 确认新令牌为 projected token 且含 audience/expiration；旧令牌已吊销。
- [ ] 核查 DB 审计日志：09:07:30Z 导出的具体对象、行数、目标位置；确认 `unknown` 主体已无法访问。
- [ ] 检查对象存储 ACL，无公开桶；导出目标已被清理/隔离。
- [ ] 元数据：确认 IMDSv2 强制启用（HTTP PUT 要求），SSRF 路径已修复。
- [ ] NetworkPolicy 已应用 default-deny，service-a 到 DB 仅最小放行。
- [ ] 日志管道健康检查：09:09Z 前后无采集端故障；确认 F-03 成因；日志已落地 WORM 存储。
- [ ] 容器/镜像：trivy 扫描无高危 CVE；无 privileged、hostPath、hostPID、docker.sock 挂载；非 root 运行。
- [ ] 匿名认证：`kubectl get clusterrolebindings | grep system:anonymous` 无危险绑定；apiserver 非安全端口已关闭。
- [ ] 重放关联检测规则，确认 token_scope_mismatch → DB export 链可触发告警。

---

## 10. 任务完成自检（对应 SKILL.md「任务完成自检」）

- [x] 是否限定在授权账号/cluster？——是，仅分析授权范围内的单个模拟 CSV 文件，未触及任何真实账号/集群。
- [x] 发现是否含复现与影响？——是，每条发现附日志证据（行号/字段/时间）、影响分析与置信度。
- [x] 是否避免破坏性操作？——是，全程只读分析；修复建议均为防御性加固，无破坏性指令。
- [x] 报告 / journal？——本报告即交付物；缺失的 `field-journal/precedent-pentest.md` 已在 1.1 节如实说明。

---

## 11. 实际读取的 Skill 文件（相对路径）

以下为本次实际读取、作为执行依据的 Skill 文件（相对工作目录）：

1. `cloud-k8s/cloud-k8s/SKILL.md`
2. `cloud-k8s/cloud-k8s/references/k8s-cloud-checklist.md`

SKILL.md 引用但包内不存在、因此**未读取**的文件：`../field-journal/precedent-pentest.md`（路径 `cloud-k8s/field-journal/precedent-pentest.md`，已确认缺失，未编造其内容）。

### 影响结果的关键 SKILL.md 规则

> **SKILL.md「ACTION REQUIRED」第 1 条**：「读取 `../field-journal/precedent-pentest.md` — 云/K8s 测试必须书面授权」，以及「MUST NOT: 未授权扫公有云其他租户」。

该规则直接决定了本次执行边界：由于缺少 precedent 授权文件且无实时环境授权，我**未**执行 Phase 2–4 中任何针对云/K8s 的主动命令，也未安装扫描工具对公网发起探测，而是将工作限定为对授权日志文件的离线分析，并把所有需实时确认的检查项降级为「假设 + 复测清单」。若忽略该规则，就会在无书面授权情况下尝试主动探测，违反 Skill 的强制要求。

---

## 12. 结论摘要

在 9 分钟的模拟日志中，识别出 1 起严重事件（未知身份数据库异常导出）、1 起高危事件（service-a 令牌作用域异常）、1 起中危完整性事件（畸形日志记录）和 1 起低危事件（admin 短时登录失败）。最需关注的是 `203.0.113.8` 在 3.5 分钟内从「令牌作用域异常」演进到「数据库异常导出」的潜在攻击链，其核心成因指向 ServiceAccount/IAM 权限过宽或令牌泄漏。建议立即轮换 service-a 令牌并核查数据导出影响面，随后按复测清单在授权实时环境中闭环验证。本报告所有结论均基于日志可见证据，未伪造任何实时命令执行结果；缺失的授权先例文件与工具链已如实标注。
