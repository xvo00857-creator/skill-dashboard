# 模拟安全日志审计报告（security-audit）

- 审计时间基准：2026-08-26（UTC）
- 输入文件：`incident_log.csv`、`edge_cases.csv`
- 执行依据：随包 Skill `gke-service-networking/SKILL.md`（实际读取，唯一依据）
- 授权范围：仅对模拟日志做静态分析与分级，不执行任何破坏性、外联或变更类操作

---

## 0. 执行依据与覆盖边界（必读）

### 0.1 实际读取到的 Skill 文件
- `gke-service-networking/SKILL.md`（ZIP 内唯一文件，相对路径）

### 0.2 Skill 自述范围
- 覆盖：Gateway API、标准 Ingress、Cloud Armor WAF 安全策略、容器原生负载均衡（NEG）、Private Service Connect（PSC）、Google 托管 SSL 证书。
- **明确不覆盖**：核心集群 IP 规划、Dataplane V2 NetworkPolicy、节点 NAT 出口（SKILL.md 原文要求改用 `gke-networking`）。

### 0.3 分类差异说明
- 题目给定分类为“安全与合规”，但 Skill 元数据 `metadata.category` 实际为 `Networking`。
- 本报告不假装该 Skill 是日志审计 Skill；仅把其中安全相关工作流（Cloud Armor、托管 TLS、PSC、NEG）作为面向 GKE 暴露面的修复建议来源。日志解析、风险分级、CSV 注入检测均由本审计在授权范围内完成。

### 0.4 确实影响结果的 SKILL.md 规则（至少一条）
- **规则 A（影响修复路径）**：Best Practices 第 2 条“Always protect public-facing endpoints with Cloud Armor”。该规则直接决定对 `web`/`api` 暴力破解与令牌滥用事件的首选缓解措施是通过 `BackendConfig` 绑定 Cloud Armor 安全策略，而不是仅依赖应用层限流。
- **规则 B（影响范围判定）**：开头“Don't use for … Dataplane V2 network policies …”。该规则决定对 `db` 横向移动的“网络策略隔离”建议必须标注为超出本 Skill 范围，需另用 `gke-networking`，不得在本报告中伪造 NetworkPolicy 清单。
- **规则 C（影响暴露面判断）**：Workflow 6 PSC 用于跨 VPC 私有暴露服务。该规则决定对 `db` 的修复首选为内部 LB + `ServiceAttachment`，而非公网 Ingress。

---

## 1. 输入完整性与格式校验

### 1.1 incident_log.csv
- 实际格式异常：文件首行是字面量 `csv`，其后是 Markdown 表格（`|timestamp|system|...|`），**并非标准逗号分隔 CSV**。本审计按表格语义解析，未做破坏性改写。
- 共 6 条数据行，其中 1 条为畸形记录（见 §2.6）。
- 字段：`timestamp, system, severity, event, user, source_ip`。

### 1.2 edge_cases.csv
- 标准 CSV，含表头 `record_id,status,value,notes`，共 5 个逻辑记录、6 行数据。
- 发现：重复行 1 组（record_id=2 出现两次）、缺失字段 1 条（record_id=3）、异常负值 1 条（record_id=4）、公式注入测试文本 1 条（record_id=5）。

---

## 2. 事件逐条分析与风险分级

分级口径：Critical > High > Medium > Low > Info。

### 2.1 Critical — 数据库异常导出（潜在数据外泄）
- 证据：`2026-08-12T09:07:30Z | db | critical | unexpected_export | user=unknown | source_ip=203.0.113.8`
- 关联：同一源 IP `203.0.113.8` 在 09:04:02 触发 `api / high / token_scope_mismatch`（service-a），间隔约 3 分 28 秒后发生 db 导出。存在“令牌越界 → 横向访问数据库 → 导出”的合理攻击链假设。
- 风险：未知用户从可路由公网段（203.0.113.0/24 为文档保留段，模拟公网）触达 db 并导出，意味着数据库或其代理可能存在过度暴露或鉴权失效。
- 修复（基于 SKILL.md）：
  1. 数据库不得通过公网 Ingress 暴露；按 Workflow 6 改用内部 LB + `ServiceAttachment`（PSC），仅允许授权消费者 VPC 私网接入。
  2. 若 db 经由 GKE 服务暴露，确认 Service `type` 不为 `LoadBalancer`（公网），应为 `ClusterIP` 或内部 LB。
  3. 网络策略层隔离（Dataplane V2 NetworkPolicy）**超出本 Skill 范围**，需调用 `gke-networking` 补齐；本报告不生成对应清单。
- 复测：从非授权 VPC/公网尝试连接 db 端口，预期不可达；在授权 PSC 端点内验证可达；导出操作需触发强审计与审批。

### 2.2 High — API 令牌作用域不匹配
- 证据：`2026-08-12T09:04:02Z | api | high | token_scope_mismatch | user=service-a | source_ip=203.0.113.8`
- 风险：服务账号令牌被用于超出其声明 scope 的操作，是权限提升/令牌滥用的强信号，且与 §2.1 同源 IP 高度相关。
- 修复：
  1. 立即轮换 `service-a` 令牌，按最小权限重发 scope。
  2. 在 API 网关层（Gateway API，SKILL.md Workflow 1）统一做令牌校验与 scope 断言，拒绝 scope 不匹配请求。
  3. 公网 API 入口按 Best Practices 第 2 条绑定 Cloud Armor（Workflow 3），对异常令牌流量限速/拦截。
- 复测：用旧令牌应被拒；用超 scope 新令牌应被拒；用正确 scope 令牌应通过；Cloud Armor 日志可见拦截记录。

### 2.3 Medium — admin 账号疑似暴力破解
- 证据：
  - `09:03:45Z web warning login_failed admin 198.51.100.23`
  - `09:03:49Z web warning login_failed admin 198.51.100.23`
  - 4 秒内连续 2 次针对 `admin` 的失败登录，属低频但集中的探测模式。
- 风险：若不限制，可能演变为口令爆破；`admin` 为高价值账号。
- 修复（基于 SKILL.md）：
  1. web 公网入口通过 `BackendConfig` 绑定 Cloud Armor 策略，启用针对登录路径的速率限制与 WAF 规则（Workflow 3 + Best Practices 第 2 条）。
  2. 启用 Google 托管 SSL 证书（Workflow 4），确保登录仅走 HTTPS，避免明文窃听。
  3. 应用层补充账号锁定/MFA（属应用职责，非本 Skill 范围）。
- 复测：同一源 IP 超过阈值的登录请求应被 Cloud Armor 拦截；HTTP 应跳转 HTTPS；admin 登录失败应触发告警。

### 2.4 Medium — CSV 公式注入测试文本
- 证据：`edge_cases.csv` record_id=5，`value` 字段为 `=HYPERLINK("https://example.invalid","do not execute")`。
- 风险：以 `=`、`+`、`-`、`@` 开头的单元格在 Excel/表格软件中可能被解释为公式，导致 CSV 注入（Formula Injection），可触发外链、信息泄露或恶意下载。虽文本含“do not execute”，但仍是真实攻击载荷形态。
- 修复：导出 CSV 时对以 `= + - @` 开头的字段加单引号前缀 `'` 或强制文本化；下游消费方禁用自动公式执行。
- 复测：用 Excel 打开处理后的文件，该单元格应显示为纯文本，不触发公式或外链。

### 2.5 Low — 日志畸形记录
- 证据：`2026-08-12T09:09:00Z | web | severity=空 | event=malformed_record | user=空 | source_ip=空`
- 风险：可能是日志采集失败、字段截断，或攻击者尝试日志注入/清洗干扰；会降低审计可追溯性。
- 修复：校验日志 schema，对缺字段记录打标并隔离；补齐 `severity/user/source_ip` 必填约束。
- 复测：重新采集后该类记录应被标记为 `parse_error` 而非静默进入主表。

### 2.6 Low — 数据质量问题（edge_cases）
- 重复：record_id=2 完全重复两行 → 去重，以 `record_id` 为主键。
- 缺失：record_id=3 的 `status`、`value` 为空，`notes="-"` → 标记为不完整，回填或剔除。
- 异常值：record_id=4 `status=error, value=-999` → 负值在该上下文无业务含义，归为异常输入，需上游校验。
- 复测：主键唯一约束生效；空值率下降；负值被校验规则拒绝。

### 2.7 Info — 正常登录
- 证据：`09:00:12Z web info login_success alice 192.0.2.10`，单次成功登录，无异常关联。无需处置，留作基线。

---

## 3. 攻击链汇总

```
203.0.113.8 (公网段)
  └─ 09:04:02  api  token_scope_mismatch (service-a)   [High]
      └─ 09:07:30  db   unexpected_export (unknown)    [Critical]  ← 疑似令牌滥用后横向导出

198.51.100.23
  └─ 09:03:45 / 09:03:49  web  login_failed admin ×2   [Medium]  ← 独立爆破探测
```

两条源 IP 不同，暂不合并为同一行动者，但均指向公网暴露面缺乏防护。

---

## 4. 修复建议（按 SKILL.md 工作流映射）

| 风险 | SKILL.md 工作流 | 具体动作 | 本 Skill 是否覆盖 |
|---|---|---|---|
| web/api 公网入口被探测/滥用 | Workflow 3 Cloud Armor + Best Practices 2 | 创建 SecurityPolicy，通过 `BackendConfig` 绑定 Service，注解 `cloud.google.com/backend-config` | 是 |
| 明文 HTTP / 证书过期 | Workflow 4 托管证书 | `ManagedCertificate` 或 Gateway `cert-map`，监听器用 HTTPS/443 | 是 |
| 负载均衡未直达 Pod | Workflow 5 NEG | Service 注解 `cloud.google.com/neg: '{"ingress": true}'` | 是 |
| db 公网暴露 | Workflow 6 PSC | 内部 LB + `ServiceAttachment`，`connectionPreference: ACCEPT_AUTOMATIC`，专用 natSubnets | 是 |
| db 东西向网络隔离 | —（明确不覆盖） | Dataplane V2 NetworkPolicy，需 `gke-networking` | 否，已标注 |
| CSV 公式注入 | —（Skill 不涉及） | 导出层转义，本审计自行给出 | 否，已标注 |

---

## 5. 复测清单（Retest Checklist）

1. [ ] `incident_log.csv` 重新解析，畸形记录被标记为 `parse_error`，不进入主事件表。
2. [ ] `edge_cases.csv` 去重后 record_id 唯一；record_id=3 缺失字段已回填或剔除；record_id=4 负值被校验拒绝。
3. [ ] record_id=5 的 `=HYPERLINK(...)` 经转义后在 Excel 中显示为纯文本，不触发公式。
4. [ ] web/api Service 已通过 `BackendConfig` 绑定 Cloud Armor 策略；对登录路径超限请求可在 Cloud Armor 日志中看到拦截。
5. [ ] Gateway/Ingress 仅暴露 HTTPS（443），托管证书状态为 Active，HTTP 80 跳转或关闭。
6. [ ] Service 已启用 NEG（`cloud.google.com/neg` 注解），后端直达 Pod。
7. [ ] db 无公网 LB/Ingress；仅通过内部 LB + PSC `ServiceAttachment` 暴露；从公网不可达。
8. [ ] `service-a` 令牌已轮换，scope 最小化；超 scope 请求在网关层被拒。
9. [ ] admin 登录启用速率限制与告警；连续失败触发锁定或 MFA。
10. [ ] 网络策略层（Dataplane V2）已由 `gke-networking` 单独评估并落地（本 Skill 不覆盖，需另行跟踪）。

---

## 6. 未完成项与阻断说明

- 未执行任何 `gcloud`、`kubectl`、Terraform 或外联操作：题目要求仅在授权测试范围内分析模拟日志，且无集群凭据/项目 ID，故所有“修复”均为建议与清单，未实际下发。
- 未生成 NetworkPolicy：SKILL.md 明确排除 Dataplane V2 网络策略，不得编造。
- 未对 `incident_log.csv` 做格式改写：其为 Markdown 表格伪装的 CSV，改写可能破坏原始证据，保留原样并在 §1.1 标注。
- 若后续需要实际下发修复，需补充：GCP 项目 ID、集群名与区域、命名空间、服务名、Cloud Armor 策略名、PSC 专用子网名、证书域名，以及具备 `roles/compute.securityAdmin` / `roles/container.developer` 的凭据。

---

## 7. 结论

- 最高优先级事件为 `db unexpected_export`（Critical），与同源 IP 的 `token_scope_mismatch`（High）构成疑似横向移动+数据外泄链，应先断 db 公网暴露并轮换 service-a 令牌。
- `admin` 登录失败（Medium）与 CSV 公式注入（Medium）为独立但需立即修复的暴露面。
- 依据 `gke-service-networking` Skill，公网入口应统一上 Cloud Armor + 托管 HTTPS + NEG，数据库应改走 PSC 私有暴露；网络策略隔离超出本 Skill，需另用 `gke-networking`。
- 所有结论均基于实际读取的 `gke-service-networking/SKILL.md` 与两份输入文件，未编造外部凭据、平台数据或执行结果。
