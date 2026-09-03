# 模拟安全日志审计报告（security-audit.md）

> 执行 Skill：`google-cloud-networking-observability`（ZIP 内 `SKILL.md` 元数据 category 为 `Compute`，任务标注分类为「安全与合规」，存在元数据不一致，已记录）
> 输入文件：`incident_log.csv`、`edge_cases.csv`
> 分析范围：仅授权测试范围内的模拟日志，离线静态分析，未执行任何破坏性操作或真实云平台查询。
> 生成时间基准：2026-08-26（UTC）

---

## 0. 执行环境与 Skill 适配性声明（阻断与降级）

### 0.1 Skill 原生能力依赖（均不可用 → 确证阻断）

`SKILL.md` 规定的主数据源与工具链如下，经核查当前环境**全部不具备**：

| 依赖项 | Skill 要求 | 当前状态 | 证据 |
|---|---|---|---|
| GCP Project ID | 所有 `gcloud`/`bq`/MCP 调用必填 | 未提供 | 输入仅为两个本地 CSV，无项目上下文 |
| GCP 凭据 / Access Token | `curl` 模板与 `gcloud auth print-access-token` | 未配置 | 无 `gcloud` 登录态，无服务账号密钥 |
| MCP 服务器（Cloud Monitoring / BigQuery / Cloud Logging / NetworkManagement） | `SKILL.md` §1「MCP Servers First」 | 未接入 | 当前工具集无对应 MCP 工具 |
| BigQuery 链接数据集（`_AllLogs`） | `SKILL.md` §0「ALWAYS check for BigQuery linked datasets」 | 不可达 | 无项目、无凭据 |
| GCP 原生日志格式（`jsonPayload`、`logName`、`resource.type`） | 所有参考文档的 SQL/过滤条件均基于此字段 | 输入不匹配 | CSV 列为 `timestamp,system,severity,event,user,source_ip`，无 GCP 字段 |

### 0.2 适用的 SKILL.md 规则（直接影响本次结果）

1. **「Conclusive Acceptance of Inactivity」**（`SKILL.md` Boundaries）：将「0 / No data found / 无记录」视为请求时间范围与资源下的**确证性结论**并立即终止。本次 GCP 主数据源全部返回「不可达 / 无凭据」，等同于无数据，据此**不再发起第二轮探索性查询**，直接降级。
2. **「NO DISCREPANCY LOOPS」+「NEVER query a second data source if primary has already provided a conclusive answer」**：主数据源（BigQuery/Cloud Logging/MCP）已确证不可用后，不循环尝试 `gcloud`/`curl` 等备用路径去「验证」差异，避免无限循环。
3. **「Ban on Auxiliary Scripting」**（`SKILL.md` Boundaries）：禁止编写或执行本地 `.sh`/`.py` 脚本文件。本次分析全部基于已读取的文件内容直接推理，未生成任何辅助脚本；最终仅产出本 `.md` 报告（非脚本）。
4. **「Results First / Definitive Termination」**：识别到直接答案后立即呈现并终止，不做过度探索。本报告在完成 CSV 全量读取后即给出结论，未追加无关查询。
5. **「ALWAYS print the generated SQL for review before execution」**：因无 BigQuery 执行环境，SQL 仅作为**不可执行的参考模板**列于附录 A，不实际运行，符合「先打印再执行」的程序要求（执行步骤因凭据缺失被阻断）。

### 0.3 降级方案

- **降级路径**：由「GCP 原生日志/指标在线查询」降级为「本地 CSV 离线静态安全分析」。
- **保留能力**：威胁分级、证据提取、IP 关联、数据质量/注入检测、修复建议、复测清单。
- **丧失能力**：实时日志检索、BigQuery 聚合趋势、VPC Flow 流量分析、Cloud NAT 端口耗尽排查、Connectivity Tests 路径诊断、Metrics 时序查询——以上均需 GCP 凭据，**无法在本次完成**，复测方法见第 6 节。

---

## 1. 输入文件概览

### 1.1 incident_log.csv

- 表头：`timestamp | system | severity | event | user | source_ip`
- 数据行：6 行（其中 1 行为畸形记录）
- 时间范围：2026-08-12T09:00:12Z ~ 2026-08-12T09:09:00Z（约 9 分钟窗口）

| # | timestamp | system | severity | event | user | source_ip |
|---|---|---|---|---|---|---|
| 1 | 2026-08-12T09:00:12Z | web | info | login_success | alice | 192.0.2.10 |
| 2 | 2026-08-12T09:03:45Z | web | warning | login_failed | admin | 198.51.100.23 |
| 3 | 2026-08-12T09:03:49Z | web | warning | login_failed | admin | 198.51.100.23 |
| 4 | 2026-08-12T09:04:02Z | api | high | token_scope_mismatch | service-a | 203.0.113.8 |
| 5 | 2026-08-12T09:07:30Z | db | critical | unexpected_export | unknown | 203.0.113.8 |
| 6 | 2026-08-12T09:09:00Z | web | *(空)* | malformed_record | *(空)* | *(空)* |

### 1.2 edge_cases.csv

- 表头：`record_id,status,value,notes`
- 数据行：6 行（含 1 组重复、1 行缺失、1 行异常负值、1 行公式注入）

| record_id | status | value | notes |
|---|---|---|---|
| 1 | ok | 120 | 正常记录 |
| 2 | ok | 120 | 重复记录 |
| 2 | ok | 120 | 重复记录 |
| 3 | *(空)* | *(空)* | - |
| 4 | error | -999 | 异常负值 |
| 5 | ok | `=HYPERLINK("https://example.invalid","do not execute")` | 公式注入测试文本 |

---

## 2. 风险分级总览

| 风险编号 | 来源文件 | 风险等级 | 简述 | 涉及实体 |
|---|---|---|---|---|
| R-01 | incident_log.csv | **严重（Critical）** | 疑似数据外泄：`unknown` 用户执行 `unexpected_export` | source_ip=203.0.113.8, system=db |
| R-02 | incident_log.csv | **高（High）** | 服务账号令牌作用域不匹配，与 R-01 同源 IP | user=service-a, source_ip=203.0.113.8 |
| R-03 | incident_log.csv | **中（Medium）** | 管理员账号短时间内连续登录失败（疑似暴力破解前兆） | user=admin, source_ip=198.51.100.23 |
| R-04 | edge_cases.csv | **高（High）** | CSV 公式注入：`=HYPERLINK(...)` 可在电子表格中触发 | record_id=5 |
| R-05 | edge_cases.csv | **中（Medium）** | 重复记录（record_id=2 出现两次），可致聚合统计偏差 | record_id=2 |
| R-06 | edge_cases.csv | **中（Medium）** | 异常哨兵负值 `-999`，若参与计算可致结果失真 | record_id=4 |
| R-07 | incident_log.csv | **低（Low）** | 畸形日志记录（severity/user/source_ip 全空），可能为采集失败或日志篡改 | 行 #6 |
| R-08 | edge_cases.csv | **低（Low）** | 缺失记录（record_id=3 的 status/value 为空） | record_id=3 |

> 说明：严重等级参照 `references/threat-analysis.md` 中定义的 `CRITICAL / HIGH / MEDIUM / LOW / INFORMATIONAL` 五级体系映射。

---

## 3. 详细风险分析与证据

### R-01【严重】疑似数据外泄 — unexpected_export

- **证据**：`incident_log.csv` 第 5 行
  - `timestamp=2026-08-12T09:07:30Z`
  - `system=db`, `severity=critical`, `event=unexpected_export`
  - `user=unknown`, `source_ip=203.0.113.8`
- **分析**：
  - `user=unknown` 表明操作未关联到有效身份，可能为未认证访问、服务账号冒用或日志身份字段丢失。
  - `unexpected_export` 在数据库系统上下文中属于高敏感操作，可能导致批量数据外泄。
  - **关键关联**：同一源 IP `203.0.113.8` 在 3 分 28 秒前（09:04:02Z）触发了 `token_scope_mismatch`（R-02）。时间序列呈现「令牌异常 → 数据导出」的递进模式，高度疑似令牌被窃取或滥用后进行数据窃取。
- **影响**：数据库数据机密性受损，可能涉及合规违规（数据泄露通知义务）。

### R-02【高】服务账号令牌作用域不匹配 — token_scope_mismatch

- **证据**：`incident_log.csv` 第 4 行
  - `timestamp=2026-08-12T09:04:02Z`
  - `system=api`, `severity=high`, `event=token_scope_mismatch`
  - `user=service-a`, `source_ip=203.0.113.8`
- **分析**：
  - `service-a` 的令牌请求了超出其授权范围的权限，可能为配置错误或令牌被泄露后尝试提权。
  - 与 R-01 同源 IP，且时间在前，构成攻击链的第一阶段。
- **影响**：API 访问控制失效，服务账号可能被用于横向移动或数据访问。

### R-03【中】管理员登录失败聚集 — login_failed ×2

- **证据**：`incident_log.csv` 第 2、3 行
  - 09:03:45Z 与 09:03:49Z，间隔仅 4 秒
  - `system=web`, `severity=warning`, `event=login_failed`
  - `user=admin`, `source_ip=198.51.100.23`
- **分析**：
  - 4 秒内 2 次失败，针对高权限 `admin` 账号，符合暴力破解或密码喷洒的早期特征。
  - 当前仅 2 次，未达到典型阈值（通常 ≥5 次/分钟），但需监控该 IP 后续行为。
  - 该 IP（198.51.100.23）与 R-01/R-02 的 IP（203.0.113.8）不同，暂不关联为同一攻击源。
- **影响**：管理员账号存在被接管风险。

### R-04【高】CSV 公式注入 — =HYPERLINK

- **证据**：`edge_cases.csv` 第 6 行（record_id=5）
  - `value==HYPERLINK("https://example.invalid","do not execute")`
  - `notes=公式注入测试文本`
- **分析**：
  - 单元格值以 `=` 开头，包含 `HYPERLINK` 公式。若该 CSV 被 Microsoft Excel、Google Sheets、LibreOffice 等电子表格软件直接打开，公式可能被解析执行，导致：
    - 诱导用户访问恶意 URL（钓鱼）。
    - 结合其他公式（如 `=CMD|...`）可触发本地命令执行（取决于软件版本与安全设置）。
  - 这是典型的 **CSV Injection（Formula Injection）** 漏洞，属于 OWASP 相关安全风险。
  - 虽然 `notes` 字段标注为「测试文本」，但在真实场景中若该字段来自用户输入且未做转义，即为可利用漏洞。
- **影响**：任何消费此 CSV 的下游系统（报表、BI、人工审核）均可能受影响。

### R-05【中】重复记录 — record_id=2

- **证据**：`edge_cases.csv` 中 record_id=2 出现两次，内容完全一致（status=ok, value=120, notes=重复记录）。
- **分析**：
  - 可能为数据采集重复写入、ETL 去重逻辑缺失或上游重试导致。
  - 若直接用于聚合统计（如求和、计数、平均值），会导致结果偏差（例如 value 总和被多计 120）。
- **影响**：统计准确性受损，可能误导基于该数据的决策。

### R-06【中】异常哨兵负值 — -999

- **证据**：`edge_cases.csv` record_id=4，`status=error`, `value=-999`, `notes=异常负值`。
- **分析**：
  - `-999` 是常见的哨兵值/错误码约定，用于表示采集失败或无效读数。
  - 若下游计算未过滤 `status=error` 或未排除负值，直接参与求和/平均会导致结果严重失真（例如拉低平均值）。
  - `status=error` 本身已标记该记录不可用，但 value 字段仍保留数值，存在被误用的风险。
- **影响**：数据分析准确性受损。

### R-07【低】畸形日志记录 — malformed_record

- **证据**：`incident_log.csv` 第 6 行
  - `timestamp=2026-08-12T09:09:00Z`, `system=web`, `event=malformed_record`
  - `severity`、`user`、`source_ip` 均为空
- **分析**：
  - 关键字段缺失，无法进行安全关联分析。
  - 可能原因：日志采集管道解析失败、上游系统输出格式变更、或**日志篡改/注入攻击**（攻击者构造畸形记录以污染日志或掩盖痕迹）。
  - 在安全事件上下文中，畸形记录本身需要被标记，不能静默忽略。
- **影响**：该时间点的安全可见性存在盲区。

### R-08【低】缺失记录 — record_id=3

- **证据**：`edge_cases.csv` record_id=3，`status` 与 `value` 均为空，`notes="-"`。
- **分析**：
  - 不完整记录，无法判断其状态或数值。
  - 可能为采集中断或上游未返回数据。
- **影响**：数据完整性轻微受损。

---

## 4. 攻击链关联分析

基于时间戳与源 IP 的关联，识别出一条疑似攻击链：

```
09:03:45Z  198.51.100.23  admin 登录失败 #1  (R-03, 独立源)
09:03:49Z  198.51.100.23  admin 登录失败 #2  (R-03, 独立源)
09:04:02Z  203.0.113.8    service-a token_scope_mismatch  (R-02, 攻击链阶段1)
09:07:30Z  203.0.113.8    unknown unexpected_export        (R-01, 攻击链阶段2)
09:09:00Z  (空)            malformed_record                  (R-07, 可能的掩盖痕迹)
```

**攻击链假设**（需进一步验证，当前仅为基于日志的推断）：
1. 攻击者从 `203.0.113.8` 使用 `service-a` 的令牌尝试访问超出授权范围的 API（令牌可能已泄露或被滥用）。
2. 约 3.5 分钟后，同一 IP 以 `unknown` 身份对数据库执行了 `unexpected_export`，可能利用了前一步获取的令牌或漏洞。
3. 随后出现的 `malformed_record`（R-07）时间点紧随其后，不能排除是攻击者尝试干扰日志采集或掩盖操作痕迹。

**注意**：`198.51.100.23` 的管理员登录失败与上述攻击链**无直接 IP 关联**，应作为独立事件跟踪，但需排查是否为协同攻击的一部分。

---

## 5. 修复建议

### 5.1 紧急处置（针对 R-01 / R-02，严重与高）

| 优先级 | 措施 | 对应风险 |
|---|---|---|
| P0 | 立即封禁源 IP `203.0.113.8` 的所有入站访问（防火墙/WAF/安全组） | R-01, R-02 |
| P0 | 吊销 `service-a` 的当前令牌并轮换密钥/证书，审计该服务账号近期所有操作 | R-02 |
| P0 | 锁定 `unknown` 关联的数据库会话，检查 09:07:30Z 前后的数据库导出记录与访问日志，确认外泄数据范围 | R-01 |
| P1 | 对 `admin` 账号启用临时登录锁定（如 5 次失败锁定 15 分钟），并告警 `198.51.100.23` | R-03 |
| P1 | 评估是否需触发数据泄露响应流程（合规通知、影响评估） | R-01 |

### 5.2 中期加固

| 措施 | 对应风险 | 说明 |
|---|---|---|
| 对所有服务账号实施最小权限原则，定期审计令牌作用域 | R-02 | 禁止令牌请求超出其所需范围的权限 |
| 数据库导出操作强制要求 MFA 或审批工作流，禁止 `unknown`/未认证身份执行 | R-01 | 所有高敏感操作必须关联有效身份 |
| 部署 CSV 输出安全转义：对以 `=`、`+`、`-`、`@` 开头的单元格值前置单引号 `'` 或进行文本化处理 | R-04 | 防止公式注入，参考 OWASP CSV Injection 防护指南 |
| ETL 管道增加去重逻辑（按 record_id 或内容哈希） | R-05 | 防止重复记录影响统计 |
| 数据校验规则：过滤 `status=error` 的记录，排除负值哨兵（如 -999），或在 schema 层标记为无效 | R-06 | 防止异常值参与计算 |
| 日志采集管道增加格式校验与告警，畸形记录应单独存储并触发告警而非静默丢弃 | R-07 | 防止日志篡改或采集失败被忽视 |
| 缺失字段的记录应标记为 `incomplete` 并进入异常队列 | R-08 | 提升数据完整性 |

### 5.3 长期建设

- 建立 SIEM（安全信息与事件管理）平台，实现跨日志源的实时关联分析（IP 关联、时间序列分析、攻击链检测）。
- 部署 UEBA（用户与实体行为分析），对 `unknown` 用户操作、服务账号异常行为进行基线检测。
- 所有 CSV/数据导出文件在交付前自动经过安全扫描（公式注入检测、PII 检测、敏感数据识别）。
- 定期进行日志完整性审计，确保日志不可篡改（如使用 WORM 存储或哈希链）。

---

## 6. 复测清单（Retest Checklist）

### 6.1 可在当前离线环境完成的复测

| 编号 | 复测项 | 方法 | 通过标准 |
|---|---|---|---|
| RT-01 | 重复记录检测 | 对 `edge_cases.csv` 按 `record_id` 分组计数 | record_id=2 计数=1（去重后） |
| RT-02 | 异常负值过滤 | 过滤 `status=error` 或 `value<0` 的记录 | record_id=4 被排除，不参与聚合 |
| RT-03 | 公式注入检测 | 扫描所有单元格值是否以 `=`/`+`/`-`/`@` 开头 | record_id=5 的 value 被标记并转义 |
| RT-04 | 缺失字段检测 | 检查 `severity`/`user`/`source_ip`/`status`/`value` 是否为空 | R-07、R-08 对应行被标记为异常 |
| RT-05 | IP 关联复测 | 按 `source_ip` 分组，统计每个 IP 的事件数与严重等级 | 203.0.113.8 关联 high+critical 共 2 条 |
| RT-06 | 时间序列复测 | 按时间排序验证攻击链时间顺序 | 09:04:02 → 09:07:30 递进关系成立 |

### 6.2 需 GCP 环境/凭据的复测（当前无法完成，给出方法）

> 以下复测项依赖 `google-cloud-networking-observability` Skill 的原生能力，因缺少 GCP Project ID 与凭据**当前无法执行**。具备条件后按以下方法复测：

| 编号 | 复测项 | Skill 参考路径 | 执行方法 | 通过标准 |
|---|---|---|---|---|
| RT-GCP-01 | Threat Logs 威胁检索 | `references/threat-analysis.md` §1 | Cloud Logging MCP `list_log_entries`，过滤 `logName:(firewall_threat OR ids.googleapis.com/threat)` + `severity=HIGH/CRITICAL` + `action=DENY` | 返回与 203.0.113.8 相关的威胁告警 |
| RT-GCP-02 | 威胁趋势聚合 | `references/threat-analysis.md` §2 | BigQuery MCP `execute_sql_readonly`，对 `_AllLogs` 按 `clientIp` 聚合攻击次数 | 203.0.113.8 在 Top attackers 列表中 |
| RT-GCP-03 | VPC Flow 流量溯源 | `references/vpc-flow-analysis.md` §2 | BigQuery 查询 `src_ip=203.0.113.8` 的流记录，确认其与 db 系统的通信量与目标端口 | 存在指向数据库端口的异常流量 |
| RT-GCP-04 | Firewall DENY 核查 | `references/firewall-analysis.md` §2 | BigQuery 聚合 `rule_details.action=DENY`，确认 203.0.113.8 是否已被拦截规则命中 | 修复后该 IP 命中 DENY 规则 |
| RT-GCP-05 | Cloud NAT 出口审计 | `references/cloud-nat-analysis.md` §2 | 查询 `allocation_status=DROPPED` 及 `internal_ip` 关联，确认外泄流量是否经过 NAT | 异常出口流量可追溯到源 VM |
| RT-GCP-06 | Connectivity Test 路径验证 | `references/connectivity-tests.md` | NetworkManagement MCP `create_connectivity_test` 模拟 203.0.113.8 → db 的路径，验证防火墙/路由是否阻断；**测试后必须 `delete_connectivity_test`** | 修复后路径结果为 UNREACHABLE（被防火墙阻断） |
| RT-GCP-07 | Metrics 异常检测 | `references/metrics-analysis.md` | Cloud Monitoring MCP 查询 `vm_flow/rtt`、`received_bytes_count` 等指标，确认 09:04-09:09 窗口是否有流量突增 | 异常时间窗口存在可观测的指标偏离 |

### 6.3 复测前置条件（阻断项解除清单）

要执行 RT-GCP-01 ~ RT-GCP-07，需具备：

1. **GCP Project ID**：明确目标项目。
2. **有效凭据**：具备以下任一——
   - 已配置 `gcloud auth login` 的用户账号（具有 Logs Viewer、Monitoring Viewer、BigQuery Data Viewer 等角色）。
   - 服务账号 JSON 密钥文件（已设置 `GOOGLE_APPLICATION_CREDENTIALS` 环境变量）。
3. **MCP 服务器接入**：Cloud Monitoring MCP、BigQuery MCP、Cloud Logging MCP、NetworkManagement MCP 至少接入所需子集。
4. **BigQuery 链接数据集**：确认 `_AllLogs` 或对应日志链接数据集已存在（`SKILL.md` §0 要求优先检查）。
5. **日志已启用**：VPC Flow Logs、Firewall Logs、Cloud NAT Logs 在目标子网/网关上已开启，否则查询结果为 0（按 Skill 规则视为确证性「无流量」，但需区分「未启用日志」与「确实无流量」）。

---

## 7. 数据质量统计汇总

### 7.1 incident_log.csv

| 指标 | 值 |
|---|---|
| 总数据行 | 6 |
| 有效记录（关键字段完整） | 5 |
| 畸形/不完整记录 | 1（R-07） |
| 严重事件数 | 1 |
| 高事件数 | 1 |
| 警告事件数 | 2 |
| 信息事件数 | 1 |
| 涉及唯一源 IP | 3（192.0.2.10, 198.51.100.23, 203.0.113.8） |
| 涉及唯一用户 | 4（alice, admin, service-a, unknown） |

### 7.2 edge_cases.csv

| 指标 | 值 |
|---|---|
| 总数据行 | 6 |
| 唯一 record_id | 5（record_id=2 重复） |
| 正常记录 | 1（record_id=1） |
| 重复记录 | 2 行（record_id=2，R-05） |
| 缺失记录 | 1（record_id=3，R-08） |
| 异常值记录 | 1（record_id=4，R-06） |
| 公式注入记录 | 1（record_id=5，R-04） |

---

## 附录 A：若具备 GCP 环境时的参考 SQL 模板（不可执行，仅展示）

> 按 `SKILL.md`「ALWAYS print the generated SQL for review before execution」要求，以下为对应风险的 BigQuery 查询模板。因当前无 Project ID / 凭据 / `_AllLogs` 数据集，**未实际执行**。

### A.1 威胁日志检索（对应 R-01 / R-02，参考 threat-analysis.md）

```sql
SELECT
  timestamp,
  JSON_VALUE(json_payload.threatDetails.threat) AS threat_name,
  JSON_VALUE(json_payload.threatDetails.severity) AS severity,
  JSON_VALUE(json_payload.action) AS action,
  JSON_VALUE(json_payload.connection.clientIp) AS src_ip,
  JSON_VALUE(json_payload.connection.serverIp) AS dest_ip
FROM `{project_id}.{dataset_id}._AllLogs`
WHERE
  log_id IN ('networksecurity.googleapis.com/firewall_threat',
             'ids.googleapis.com/threat')
  AND JSON_VALUE(json_payload.connection.clientIp) = '203.0.113.8'
  AND timestamp >= '2026-08-12T09:00:00Z'
  AND timestamp <= '2026-08-12T09:10:00Z'
ORDER BY timestamp DESC
```

### A.2 防火墙 DENY 聚合（对应修复后验证，参考 firewall-analysis.md）

```sql
SELECT
  JSON_VALUE(json_payload.rule_details.reference) AS rule_name,
  COUNT(*) AS block_count
FROM `{project_id}.{dataset_id}._AllLogs`
WHERE
  log_name LIKE '%firewall%'
  AND JSON_VALUE(json_payload.rule_details.action) = 'DENY'
  AND JSON_VALUE(json_payload.connection.src_ip) = '203.0.113.8'
GROUP BY 1
ORDER BY block_count DESC
LIMIT 10
```

---

## 附录 B：实际读取的 Skill 文件清单（相对路径）

以下为本次从 ZIP 中实际读取并用于执行的文件（相对于 Skill 根目录 `google-cloud-networking-observability/`）：

1. `SKILL.md` — 主指令文件（核心规则、边界、流程）
2. `references/threat-analysis.md` — 威胁日志分析参考（严重等级体系、SQL 模式）
3. `references/firewall-analysis.md` — 防火墙日志分析参考
4. `references/vpc-flow-analysis.md` — VPC Flow 日志分析参考
5. `references/vpc-flow-logs-cost-estimation.md` — VPC Flow 成本估算参考（含严格脚本禁令规则）
6. `references/cloud-nat-analysis.md` — Cloud NAT 分析参考
7. `references/connectivity-tests.md` — 连通性测试参考（含测试后必须删除的规则）
8. `references/metrics-analysis.md` — 网络指标分析参考
9. `references/mcp-usage.md` — MCP 服务器使用参考

> 共读取 9 个文件，覆盖 SKILL.md 引用的全部参考文档。未读取 ZIP 外的任何文件，未编造未读取的内容。

---

## 附录 C：阻断声明

**本次未完成且无法完成的事项**（因缺少必要条件，不假装成功）：

1. **GCP 原生日志查询**：无 Project ID、无凭据、无 MCP 接入，无法执行 BigQuery / Cloud Logging / Monitoring 查询。
2. **Connectivity Tests 路径诊断**：无 NetworkManagement MCP 或 `gcloud` 凭据，无法创建/查询/删除连通性测试。
3. **VPC Flow Logs 成本估算**：无项目子网列表与 Monitoring API 访问，无法执行 `references/vpc-flow-logs-cost-estimation.md` 中的 Step 3-5。
4. **实时威胁狩猎**：无法查询 Cloud Firewall Plus / Cloud IDS 的实时威胁日志。

以上事项的复测方法已在第 6.2 节给出，待具备 GCP 环境与凭据后可执行。

---

*报告结束。本报告基于离线静态分析生成，所有结论均有对应 CSV 行作为证据；未执行任何破坏性操作、未访问任何真实云平台、未生成任何辅助脚本文件。*
