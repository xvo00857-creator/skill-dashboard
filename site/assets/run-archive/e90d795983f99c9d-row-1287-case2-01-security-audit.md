# 模拟安全日志审计报告（security-audit.md）

- 审计对象：`incident_log.csv`（本地模拟安全日志，6 条记录，时间窗 2026-08-12 09:00:12Z–09:09:00Z，约 9 分钟）
- 执行依据：Skill `google-cloud-networking-observability` 的 `SKILL.md`（以实际读取内容为准）
- 执行性质：授权测试范围内的离线静态分析，未连接任何真实 Google Cloud 项目，未执行破坏性操作
- 报告语言：除 Skill 名、文件名、命令、必要技术标识外，均为中文

---

## 1. 实际读取的 Skill 文件（相对路径）

以下文件均已在本次任务中实际读取，未读取的文件不引用其内容：

1. `google-cloud-networking-observability/SKILL.md`
2. `google-cloud-networking-observability/references/threat-analysis.md`

未读取（本任务不需要，故不引用）：
`references/cloud-nat-analysis.md`、`references/connectivity-tests.md`、`references/firewall-analysis.md`、`references/mcp-usage.md`、`references/metrics-analysis.md`、`references/vpc-flow-analysis.md`、`references/vpc-flow-logs-cost-estimation.md`。

> 说明：`SKILL.md` 元数据中 `category: Compute`，与题目给定分类“安全与合规”不一致；本报告以 `SKILL.md` 正文规则为唯一执行依据，安全部分参照已读取的 `threat-analysis.md`。

---

## 2. 约束、冲突与关键取舍

本任务至少存在以下两组会直接影响结果的约束/冲突：

### 冲突一：Skill 预设的在线 GCP 工具链 vs 授权范围仅提供本地模拟 CSV

- `SKILL.md` 要求优先使用 Cloud Monitoring MCP / BigQuery MCP / Cloud Logging MCP，回退到 `gcloud` / `bq` / `curl`，并要求先检查 BigQuery 关联数据集（如 `_AllLogs`）。
- 本次授权范围仅提供本地 `incident_log.csv`，**没有** `project_id`、服务账号凭据、MCP 服务、BigQuery 数据集或 Cloud Logging sink。
- **取舍**：不伪造任何在线查询结果，不编造 `project_id`/数据集/返回行数；改为对 CSV 做离线静态分析，并把 Skill 规定的在线查询改写为“复测清单中的可执行模板”，明确标注“未执行”。这同时遵守了 `SKILL.md` 的“Ban on Auxiliary Scripting”——CSV 仅 6 行，已通过文件读取完整载入，未编写任何 `.sh`/`.py` 脚本。

### 冲突二：“Results First / 禁止二次验证 / 不查第二数据源” vs 安全审计需要关联与复测

- `SKILL.md` 明确：找到结论后立即终止；**不得**在未获用户明确许可时做二次验证（如找到防火墙拦截后再去查 VPC Flow）；**不得**查询第二数据源；**不得**陷入“差异循环”；对“0 / 无数据”必须作为结论性结果接受。
- 安全审计天然要求跨事件关联、修复后复测。
- **取舍**：
  - 关联分析**仅在 CSV 这一个数据源内部**进行（如同一源 IP 的先后事件），不引入威胁情报、VPC Flow、Metrics 等第二数据源，因此不违反“不查第二数据源”。
  - 修复后的在线复测（查 VPC Flow、跑 Connectivity Test、查 IP 信誉）**全部列入复测清单，不在本次执行**，并标注“需用户明确授权后执行”，以此兼容“禁止二次验证”规则。
  - 对 CSV 中“未出现成功登录”“未出现更多失败次数”等缺失，按“Conclusive Acceptance of Inactivity”视为本时间窗内的结论性状态，不臆测更多活动。

### 确实影响结果的一条 SKILL.md 规则

> **“NEVER perform secondary verification … without explicit user permission.”**

该规则直接决定了本报告的深度边界：识别出 `critical` 级 `unexpected_export` 后，**没有**也**不能**声称已通过 VPC Flow Logs 或 Metrics 验证其流量规模与外发目的地；相关验证被降级为“需授权的复测项”。若忽略该规则，报告将出现未经执行的虚假验证结论。

---

## 3. 事件清单与风险分级

分级参照 `threat-analysis.md` 的严重级定义（CRITICAL / HIGH / MEDIUM / LOW / INFORMATIONAL）。

| # | 时间 (UTC) | 系统 | 原始严重级 | 事件 | 用户 | 源 IP | 审计分级 | 判定理由 |
|---|---|---|---|---|---|---|---|---|
| 1 | 09:00:12 | web | info | login_success | alice | 192.0.2.10 | INFORMATIONAL | 正常登录基线，无异常 |
| 2 | 09:03:45 | web | warning | login_failed | admin | 198.51.100.23 | MEDIUM | 针对高权限 admin 账户的登录失败 |
| 3 | 09:03:49 | web | warning | login_failed | admin | 198.51.100.23 | MEDIUM | 与上一条间隔仅 4 秒、同 IP 同账户，呈现暴力破解/撞库节奏；本窗内仅 2 次，故未升至 HIGH |
| 4 | 09:04:02 | api | high | token_scope_mismatch | service-a | 203.0.113.8 | HIGH | 服务令牌作用域不匹配，可能为令牌泄露/越权使用的前兆 |
| 5 | 09:07:30 | db | critical | unexpected_export | unknown | 203.0.113.8 | CRITICAL | 未知用户发起非预期数据库导出，且与事件 4 同源 IP，疑似数据外泄 |
| 6 | 09:09:00 | web | （空） | malformed_record | （空） | （空） | 数据质量问题 | 严重级/用户/源 IP 全空，破坏审计完整性，可能掩盖真实事件 |

**总体风险结论：CRITICAL。** 依据是存在一条 `critical` 事件且与一条 `high` 事件构成同源 IP 的时间序列关联。

---

## 4. 关键证据与关联分析

### 4.1 主攻击链（同源 IP 203.0.113.8）

- 09:04:02 `api` / `token_scope_mismatch` / 用户 `service-a` / 源 IP `203.0.113.8`
- 09:07:30 `db` / `unexpected_export` / 用户 `unknown` / 源 IP `203.0.113.8`
- 两事件间隔约 3 分 28 秒，源 IP 完全一致。
- **推断（仅基于 CSV，未做第二源验证）**：`service-a` 令牌可能被窃取或被滥用，以超出授权的作用域访问 API，随后在约 3.5 分钟内发起数据库导出；导出时用户字段为 `unknown`，说明导出动作未被正确鉴权或鉴权日志缺失。
- **证据强度**：中。同源 IP + 时间邻近 + 权限前置事件，构成合理杀伤链；但缺少导出目标、数据量、令牌 ID 等字段，无法定量确认外泄规模。

### 4.2 admin 账户暴力破解尝试（198.51.100.23）

- 09:03:45 与 09:03:49 两次 `login_failed`，间隔 4 秒，均针对 `admin`，均来自 `198.51.100.23`。
- 本时间窗内**未出现**来自该 IP 的 `login_success`（按“Conclusive Acceptance of Inactivity”，在本窗内视为未成功）。
- 仅 2 次失败不足以判定为已成型攻击，但 admin 为高价值账户，需按潜在暴力破解处置。

### 4.3 数据质量缺陷

- 09:09:00 一条 `malformed_record` 缺失 `severity`、`user`、`source_ip` 三个关键字段。
- 风险：若采集端普遍存在该问题，真实攻击可能被静默丢弃；审计结论的完整性依赖日志质量。

### 4.4 关于源 IP 的说明

- 三个源 IP 段 `192.0.2.0/24`、`198.51.100.0/24`、`203.0.113.0/24` 均为 RFC 5737 规定的文档/测试地址段，不对应真实互联网主机。
- 因此本次**不执行**也**不建议**对这些 IP 做威胁情报查询（既无意义，也会构成“第二数据源”查询）；复测时应替换为真实环境中的实际源 IP。

---

## 5. 修复建议

按优先级从高到低：

### P0（针对 CRITICAL，立即）
1. **冻结并轮换 `service-a` 凭据/令牌**：吊销当前令牌，重新签发最小作用域令牌；核查该服务账户近期所有令牌签发与作用域变更记录。
2. **阻断源 IP `203.0.113.8`**：在 VPC 防火墙 / Cloud Armor 层加入临时拒绝规则（真实环境中替换为实际 IP），并设置过期复核。
3. **核查数据库导出目标**：定位 09:07:30 前后的导出任务、目标存储桶/外部地址、导出数据量与字段范围；评估是否已发生数据外泄并启动相应通报流程。
4. **补齐导出鉴权**：`unexpected_export` 的用户为 `unknown`，说明导出路径存在未鉴权或鉴权日志缺失，须强制身份校验并记录操作者。

### P1（针对 HIGH）
5. **令牌作用域治理**：为 `service-a` 实施最小权限，禁用宽作用域令牌；开启 `token_scope_mismatch` 实时告警。
6. **服务间调用强制 mTLS + 身份透传**：确保 API 调用可追溯到具体服务实例，避免 `unknown` 用户出现。

### P2（针对 MEDIUM）
7. **admin 账户保护**：启用 MFA、登录失败速率限制与账户临时锁定；将 admin 登录纳入高优先级告警。
8. **异常登录检测**：对同一账户短时间多次失败建立阈值告警（如 5 分钟内 ≥5 次）。

### P3（数据质量）
9. **日志采集校验**：在采集端对 `severity`、`user`、`source_ip` 做非空校验，不合格记录进入死信队列而非静默丢弃。
10. **定期审计日志完整率**：将 `malformed_record` 占比纳入可观测性 SLI。

---

## 6. 复测清单

以下为修复后应执行的验证项。**所有在线查询均未在本次执行**，仅提供模板；执行前需具备 GCP 项目、凭据与用户明确授权，并遵守 `SKILL.md`“先打印 SQL 再执行”“不超过 2 次探索性查询”等规则。

### 6.1 验证外泄是否被遏制（对应 P0）
- 在 BigQuery `_AllLogs` 中复核阻断后是否仍有来自该 IP 的 `unexpected_export`：
  ```sql
  -- 执行前需替换 {project_id}.{dataset_id} 与目标 IP；先 --dry_run
  SELECT timestamp, JSON_VALUE(json_payload.connection.clientIp) AS src_ip,
         JSON_VALUE(json_payload.action) AS action
  FROM `{project_id}.{dataset_id}._AllLogs`
  WHERE log_id = '...db_audit_log...'
    AND JSON_VALUE(json_payload.connection.clientIp) = '203.0.113.8'
    AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
  ORDER BY timestamp DESC LIMIT 20;
  ```
  复测通过标准：阻断规则生效后无新增 `unexpected_export`。

### 6.2 验证令牌治理（对应 P1）
- 检索 `service-a` 最近 24 小时是否仍有 `token_scope_mismatch`：
  ```sql
  SELECT timestamp, JSON_VALUE(json_payload.principal) AS principal,
         JSON_VALUE(json_payload.requestedScope) AS requested_scope
  FROM `{project_id}.{dataset_id}._AllLogs`
  WHERE log_id = '...api_audit_log...'
    AND JSON_VALUE(json_payload.event) = 'token_scope_mismatch'
    AND JSON_VALUE(json_payload.principal) = 'service-a'
    AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
  ORDER BY timestamp DESC LIMIT 20;
  ```
  复测通过标准：0 条新增（按“Conclusive Acceptance of Inactivity”视为通过）。

### 6.3 验证 admin 登录保护（对应 P2）
- 模拟或核查失败登录阈值：确认 5 分钟内 ≥N 次失败后触发锁定/告警；本窗内 2 次失败不应再静默。
- 核查是否存在来自 `198.51.100.23` 的成功登录（真实环境替换 IP）：
  ```sql
  SELECT timestamp, JSON_VALUE(json_payload.user) AS user,
         JSON_VALUE(json_payload.connection.clientIp) AS src_ip
  FROM `{project_id}.{dataset_id}._AllLogs`
  WHERE log_id = '...web_login...'
    AND JSON_VALUE(json_payload.event) = 'login_success'
    AND JSON_VALUE(json_payload.user) = 'admin'
    AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
  LIMIT 20;
  ```

### 6.4 验证防火墙阻断（Connectivity Test，需授权）
- 使用 Connectivity Test 从 `203.0.113.8` 到 db 端点做静态路径诊断，预期结果为 `DENY`。该项属于 `SKILL.md` 中的二次验证，**必须在用户明确许可后执行**。

### 6.5 验证日志质量（对应 P3）
- 统计最近 1 小时 `malformed_record` 或关键字段为空的记录数，复测通过标准：0 条。

### 6.6 Flow Analyzer 入口
- 按 `SKILL.md` 要求提供 Flow Analyzer 控制台入口：<https://console.cloud.google.com/net-intelligence/flow-analyzer>
- 注意：该链接需真实 GCP 项目上下文才可使用；本次离线分析中不可操作。

---

## 7. 依赖、风险与未完成项

### 依赖（本次缺失，故未执行在线部分）
- 有效的 GCP `project_id` 与具备 `logging.viewer` / `bigquery.dataViewer` 权限的服务账号。
- 已配置的 BigQuery 关联日志数据集（`_AllLogs`）或 Cloud Logging sink。
- MCP 服务（Cloud Monitoring / BigQuery / Cloud Logging）或可用的 `gcloud` / `bq` 认证环境。
- 用户对“二次验证 / 第二数据源查询”的明确授权。

### 风险
- **样本极小**：仅 6 条、9 分钟窗口，无法代表整体安全态势；admin 暴力破解可能在窗外继续，外泄规模无法定量。
- **字段缺失**：无目标 IP/端口、无导出目标、无令牌 ID、无数据量，关联分析停留在“合理推断”层面。
- **模拟 IP**：源 IP 均为文档测试段，无法做真实 IP 信誉与地理位置研判。
- **日志质量**：`malformed_record` 的存在意味着可能有未被捕获的真实事件。

### 未完成项（明确阻断，不假装成功）
- 未执行任何 `bq` / `gcloud` / `curl` / MCP 查询——原因：无 GCP 项目与凭据。
- 未做 VPC Flow Logs、Metrics、Connectivity Test 交叉验证——原因：`SKILL.md` 禁止未经授权的二次验证，且无在线环境。
- 未做威胁情报 IP 查询——原因：IP 为文档测试段，且会构成第二数据源查询。

---

## 8. 结论

1. 本次模拟日志的**总体风险为 CRITICAL**：`203.0.113.8` 在 09:04:02 触发 `token_scope_mismatch`（HIGH）后，于 09:07:30 以 `unknown` 用户触发 `unexpected_export`（CRITICAL），构成“令牌滥用 → 数据导出”的疑似杀伤链，应按 P0 立即处置（轮换 `service-a` 令牌、阻断该 IP、核查导出目标与数据量）。
2. `198.51.100.23` 对 `admin` 的两次快速登录失败为 MEDIUM 风险，需启用 MFA 与失败阈值告警。
3. 存在一条字段全空的 `malformed_record`，属数据质量缺陷，可能掩盖真实事件，需修复采集校验。
4. 受 `SKILL.md`“禁止未经授权二次验证”与“不查第二数据源”规则约束，以及缺少 GCP 在线环境，所有跨源验证与在线复测均以模板形式列入第 6 节，未实际执行；需在具备项目、凭据与用户授权后按清单复测。
