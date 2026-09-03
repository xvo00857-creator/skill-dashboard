# 模拟安全日志审计报告

> 生成时间：2026-08-26  
> 输入文件：`incident_log.csv`、`edge_cases.csv`  
> 执行依据：`gke-basics` Skill（SKILL.md 及 references/ 目录）  
> 授权范围：仅在授权测试范围内分析模拟安全日志，不实施破坏性操作

---

## 一、执行范围与 Skill 边界声明

### 1.1 Skill 实际元数据与任务标注的差异

| 项目 | Skill 实际值（SKILL.md frontmatter） | 任务标注值 |
|---|---|---|
| name | `gke-basics` | `gke-basics` |
| category | `Containers` | `安全与合规` |

**结论**：Skill 自身元数据分类为 `Containers`，与任务标注的"安全与合规"不一致。本报告以实际读取到的 SKILL.md 为唯一执行依据。

### 1.2 SKILL.md 明确的适用边界（直接影响本报告深度）

SKILL.md 在 description 中明确声明：

> "Don't use for specialized GKE networking (use gke-networking), **advanced security hardening (use gke-platform-security or gke-workload-security)**, or cluster upgrades (use gke-upgrades)."

**影响**：本 Skill 不适用于高级安全加固。因此本审计仅执行**基础日志分诊、风险分级、证据固定和通用修复建议**；涉及深度安全加固（如零信任架构、高级威胁狩猎、容器运行时防护等）需移交 `gke-platform-security` 或 `gke-workload-security` Skill 处理。此为降级方案，非完整安全评估。

### 1.3 SKILL.md 中可适用于本审计的安全相关规则

以下规则来自 SKILL.md 及 `references/core-concepts.md`，在本次日志分析中作为判断依据：

1. **禁止在 Pod 中挂载原始 GCP 服务账号 JSON 密钥**（SKILL.md "Critical Gotchas" 第 2 条）。
2. **使用 Workload Identity（KSA 注解绑定 GSA）替代静态密钥**（SKILL.md 第 2 条 + core-concepts.md "Identity & Security Model"）。
3. **私有集群最佳实践**：`--enable-private-nodes`、`--enable-private-endpoint`、`--enable-master-authorized-networks`（SKILL.md 第 1 条）。
4. **Pod Security Standards `restricted` 策略应在生产命名空间强制执行**（core-concepts.md "Identity & Security Model"）。
5. **Secret Manager 集成与自动轮换**（core-concepts.md）。
6. **工具偏好层级**：MCP > gcloud > kubectl；破坏性操作需谨慎（cli-reference.md）。

---

## 二、输入文件校验

### 2.1 incident_log.csv

- **格式**：标准逗号分隔 CSV，UTF-8 编码。
- **字段**：`timestamp`, `system`, `severity`, `event`, `user`, `source_ip`（共 6 列）。
- **数据行数**：6 行。
- **完全重复记录**：无。
- **缺失字段**：

| 行号 | event | 缺失字段 |
|---|---|---|
| 6 | `malformed_record` | `severity`、`user`、`source_ip` |

- **异常/不安全输入**：第 6 行为畸形记录（`malformed_record`），三个关键字段为空，无法定位用户和来源，属于日志完整性缺陷。

### 2.2 edge_cases.csv

- **格式**：标准逗号分隔 CSV，UTF-8 编码。
- **字段**：`record_id`, `status`, `value`, `notes`（共 4 列）。
- **数据行数**：6 行（含 1 组重复）。
- **重复记录**：

| record_id | 出现次数 | 行号 | 说明 |
|---|---|---|---|
| 2 | 2 | 第 2、3 行 | 两行列值完全一致，为重复记录 |

- **缺失字段**：

| 行号 | record_id | 缺失字段 |
|---|---|---|
| 4 | 3 | `status`、`value`（`notes` 为占位符 `-`） |

- **异常值**：

| 行号 | record_id | 字段 | 值 | 异常类型 |
|---|---|---|---|---|
| 5 | 4 | `value` | `-999` | 异常负值（在正向指标场景下不合理） |

- **不安全输入（公式注入）**：

| 行号 | record_id | 字段 | 原始值 | 风险 |
|---|---|---|---|---|
| 6 | 5 | `value` | `=HYPERLINK("https://example.invalid","do not execute")` | CSV 公式注入：当文件在 Excel / WPS / Google Sheets 中打开时，`=` 开头的单元格会被当作公式执行，可能触发外部请求或执行恶意代码 |

  补充说明：该公式内含逗号，导致标准 CSV 解析器将其拆分为多列（`value` 列截断、`notes` 列错位、产生额外 `None` 列），这本身也证明了未转义的不安全输入会破坏数据结构。`notes` 字段明确标注"公式注入测试文本"。

---

## 三、风险分级与证据

### 3.1 风险总览

| 编号 | 风险等级 | 事件 | 来源 IP | 用户 | 时间 |
|---|---|---|---|---|---|
| R-01 | **严重 (Critical)** | `unexpected_export`（意外数据导出） | 203.0.113.8 | `unknown` | 2026-08-12T09:07:30Z |
| R-02 | **高 (High)** | `token_scope_mismatch`（令牌作用域不匹配） | 203.0.113.8 | `service-a` | 2026-08-12T09:04:02Z |
| R-03 | **中 (Medium)** | `login_failed` × 2（管理员登录失败，疑似暴力破解） | 198.51.100.23 | `admin` | 2026-08-12T09:03:45Z / 09:03:49Z |
| R-04 | **低 (Low)** | `malformed_record`（畸形日志记录） | —（缺失） | —（缺失） | 2026-08-12T09:09:00Z |
| R-05 | **信息 (Info)** | `login_success`（正常登录，基线） | 192.0.2.10 | `alice` | 2026-08-12T09:00:12Z |

### 3.2 详细证据

#### R-01 严重：意外数据导出（潜在数据泄露）

- **证据**：`incident_log.csv` 第 5 行 — `db` 系统，`critical` 级别，`unexpected_export` 事件，用户为 `unknown`，来源 IP `203.0.113.8`。
- **分析**：
  - 导出操作用户为 `unknown`，表明可能存在未认证访问、被盗凭据或服务账号被滥用。
  - 来源 IP `203.0.113.8` 与 R-02（token_scope_mismatch）为同一 IP，时间间隔仅 3 分 28 秒，存在强关联（见第四节攻击链分析）。
  - 涉及 `db` 系统，数据导出可能导致敏感信息外泄。
- **SKILL.md 关联规则**：私有集群应使用 `--enable-private-nodes` 和 `--enable-master-authorized-networks` 限制控制平面访问；若数据库部署在 GKE 中，外部 IP 直接访问数据库表明网络隔离不足。

#### R-02 高：令牌作用域不匹配（潜在权限提升/令牌滥用）

- **证据**：`incident_log.csv` 第 4 行 — `api` 系统，`high` 级别，`token_scope_mismatch` 事件，用户 `service-a`，来源 IP `203.0.113.8`。
- **分析**：
  - `service-a` 的令牌请求了超出其授权范围的权限，可能表明令牌被窃取、重放或配置错误。
  - 与 R-01 同源 IP，时间上先于数据导出，可能是攻击链的前置步骤。
- **SKILL.md 关联规则**：
  - "Never mount raw GCP Service Account JSON keys in Pods" — 若 service-a 使用静态 JSON 密钥，密钥泄露后可被任意位置使用，无法绑定到特定 Pod/节点。
  - 应使用 Workload Identity（KSA 注解绑定 GSA），使服务身份与运行环境绑定，降低密钥泄露风险。
  - core-concepts.md 推荐 Secret Manager 集成与自动轮换。

#### R-03 中：管理员连续登录失败（疑似暴力破解）

- **证据**：`incident_log.csv` 第 2、3 行 — `web` 系统，`warning` 级别，`login_failed` 事件，用户 `admin`，来源 IP `198.51.100.23`。
- **分析**：
  - 两次失败间隔仅 4 秒（09:03:45 → 09:03:49），针对高权限 `admin` 账户，符合自动化登录尝试特征。
  - 仅 2 次尝试，置信度为中；若后续日志中出现更多失败则升级为高。
  - 来源 IP `198.51.100.23` 与 R-01/R-02 的 `203.0.113.8` 不同，暂未发现直接关联。
- **修复方向**：实施登录速率限制、账户锁定策略、管理员账户强制 MFA。

#### R-04 低：畸形日志记录（日志完整性缺陷）

- **证据**：`incident_log.csv` 第 6 行 — event 为 `malformed_record`，`severity`、`user`、`source_ip` 三字段为空。
- **分析**：
  - 日志采集或传输过程中存在数据丢失，可能掩盖真实安全事件。
  - 无法判断该记录是否为攻击行为的一部分（因缺少用户和 IP）。
- **修复方向**：修复日志采集管道，在入库前进行 schema 校验，对不完整记录进行告警和隔离。

#### R-05 信息：正常登录（基线）

- **证据**：`incident_log.csv` 第 1 行 — `alice` 从 `192.0.2.10` 正常登录，`info` 级别。
- **分析**：作为正常行为基线，无风险。

---

## 四、攻击链分析

### 4.1 IP 203.0.113.8 关联事件链

```
09:04:02  token_scope_mismatch (high)   service-a   203.0.113.8
    │
    │  间隔 3分28秒
    ▼
09:07:30  unexpected_export (critical)   unknown      203.0.113.8
```

**推断**：攻击者可能从 `203.0.113.8` 首先利用 `service-a` 的令牌进行越权访问（token_scope_mismatch），随后在同一 IP 以 `unknown` 用户身份执行了数据库意外导出。两步操作同源、时间紧密衔接，构成完整的"令牌滥用 → 数据泄露"攻击链。

**置信度**：中高（同源 IP + 时间序列吻合，但缺少中间步骤日志和网络流量证据）。

### 4.2 IP 198.51.100.23 事件

```
09:03:45  login_failed (warning)   admin   198.51.100.23
09:03:49  login_failed (warning)   admin   198.51.100.23
```

**推断**：独立事件，针对 `admin` 账户的快速登录尝试，疑似暴力破解的早期阶段。与 `203.0.113.8` 攻击链暂未发现关联。

---

## 五、修复建议

> 注意：根据 SKILL.md 边界声明，以下为通用基础修复建议。高级安全加固需移交 `gke-platform-security` / `gke-workload-security`。

### 5.1 针对 R-01（严重）

1. **立即响应**：
   - 对来源 IP `203.0.113.8` 进行封禁或加入监控列表。
   - 审计该 IP 在事件时间窗口内的所有操作记录。
   - 核查数据库导出内容，评估数据泄露范围。
2. **身份与访问**：
   - 排查 `unknown` 用户产生原因：是否存在匿名访问、共享账户或日志中用户字段丢失。
   - 对所有数据库访问强制认证和审计。
3. **网络隔离（SKILL.md 规则适用）**：
   - 若数据库部署于 GKE，确保集群启用 `--enable-private-nodes`，节点无公网 IP。
   - 使用 `--enable-master-authorized-networks` 限制控制平面访问来源。
   - 数据库服务不应暴露公网入口。

### 5.2 针对 R-02（高）

1. **令牌治理**：
   - 立即轮换 `service-a` 的所有凭据/令牌。
   - 审计 `service-a` 的令牌权限范围，实施最小权限原则。
2. **Workload Identity 改造（SKILL.md 规则适用）**：
   - 禁止在 Pod 中挂载原始 GCP 服务账号 JSON 密钥。
   - 通过 KSA 注解绑定 GSA：
     ```yaml
     metadata:
       annotations:
         iam.gke.io/gcp-service-account: GSA_NAME@PROJECT_ID.iam.gserviceaccount.com
     ```
   - 使用 Workload Identity Federation 使 Pod 无需静态密钥即可获取 IAM 身份。
3. **密钥管理（core-concepts.md 规则适用）**：
   - 集成 Secret Manager，启用自动轮换。

### 5.3 针对 R-03（中）

1. 对 `admin` 账户启用多因素认证（MFA）。
2. 实施登录速率限制（如同一 IP 5 分钟内最多 5 次失败）。
3. 配置账户锁定策略（连续失败后临时锁定）。
4. 对 `198.51.100.23` 进行威胁情报查询和监控。

### 5.4 针对 R-04（低）

1. 修复日志采集管道，确保所有字段完整传输。
2. 在日志入库前添加 schema 校验，对缺失关键字段的记录进行隔离和告警。
3. 建立日志完整性监控指标（如记录数异常波动、字段缺失率）。

### 5.5 针对 edge_cases.csv 数据质量问题

| 问题类型 | 涉及记录 | 修复建议 |
|---|---|---|
| 重复记录 | record_id=2 | 在数据管道中添加基于主键的去重逻辑 |
| 缺失字段 | record_id=3 | 对 `status`、`value` 等必填字段添加非空校验 |
| 异常负值 | record_id=4 (value=-999) | 添加数值范围校验，拒绝超出合理范围的值 |
| 公式注入 | record_id=5 (=HYPERLINK...) | 在写入 CSV/电子表格前，对以 `=`、`+`、`-`、`@` 开头的单元格值添加前导单引号 `'` 进行转义；或在数据入口层过滤公式表达式 |

---

## 六、复测清单

以下为修复后需验证的项目，按优先级排序：

### 6.1 高优先级（安全事件相关）

- [ ] **R-01 复测**：在测试环境中模拟来自非授权 IP 的数据库导出请求，验证请求被拒绝或触发告警。
- [ ] **R-01 复测**：确认 `203.0.113.8` 已被封禁或处于监控状态。
- [ ] **R-02 复测**：轮换 `service-a` 凭据后，确认旧令牌已失效（使用旧令牌调用 API 应返回 401/403）。
- [ ] **R-02 复测**：验证 `service-a` 令牌权限范围已缩小至最小必要权限。
- [ ] **R-02 复测**：若已实施 Workload Identity，验证 Pod 内不再存在静态 JSON 密钥文件，且通过 KSA 注解可正常获取 GSA 身份。

### 6.2 中优先级

- [ ] **R-03 复测**：模拟同一 IP 连续快速登录失败，验证速率限制和账户锁定策略生效。
- [ ] **R-03 复测**：确认 `admin` 账户已启用 MFA。
- [ ] **攻击链复测**：验证 token_scope_mismatch 事件触发后，系统能自动关联同源 IP 的后续操作并产生告警。

### 6.3 低优先级（数据质量相关）

- [ ] **R-04 复测**：向日志管道发送一条缺失 `severity`/`user`/`source_ip` 的测试记录，验证被正确隔离并触发告警。
- [ ] **去重复测**：发送两条完全相同的记录，验证仅保留一条。
- [ ] **非空校验复测**：发送 `status`/`value` 为空的记录，验证被拒绝。
- [ ] **数值范围复测**：发送 `value=-999` 的记录，验证被拒绝或标记为异常。
- [ ] **公式注入复测**：发送 `=HYPERLINK(...)` 作为单元格值，验证被转义（添加前导 `'`）或过滤，在 Excel 中打开时不执行公式。

---

## 七、降级方案与未完成项

### 7.1 因 Skill 边界导致的降级

| 项目 | 状态 | 说明 |
|---|---|---|
| 高级安全加固方案 | **未完成（降级）** | SKILL.md 明确声明不适用高级安全加固，需使用 `gke-platform-security` 或 `gke-workload-security` Skill。本报告仅提供基础修复建议。 |
| 容器运行时安全分析 | **未完成（降级）** | 超出 gke-basics 范围。 |
| 网络策略深度审计 | **未完成（降级）** | SKILL.md 指向 `gke-networking` Skill。 |

### 7.2 因输入限制导致的未完成项

| 项目 | 状态 | 阻断原因 | 复测方法 |
|---|---|---|---|
| 实际 GKE 集群配置核查 | **未完成** | 无可用 GCP 项目、集群凭据或 MCP/gcloud 访问权限；输入仅为模拟日志文件 | 在具备授权的 GCP 环境中，使用 `gcloud container clusters describe` 或 MCP `get_cluster` 核查私有节点、授权网络、Workload Identity 等配置 |
| 实时日志查询与关联分析 | **未完成** | 输入为静态 CSV 快照，无 Cloud Logging 访问权限 | 使用 `gcloud logging read` 或 MCP 诊断工具查询完整时间窗口内的日志 |
| 威胁情报查询 | **未完成** | 无外部威胁情报 API 访问权限 | 对 `203.0.113.8`、`198.51.100.23` 进行威胁情报查询 |
| 数据库导出内容核查 | **未完成** | 无数据库访问权限，日志仅记录事件不记录导出内容 | 在授权环境中核查数据库审计日志和导出文件 |

### 7.3 已完成项

- [x] 解压并读取 gke-basics Skill 全部文件（SKILL.md + 5 个 references）
- [x] 解析并校验 incident_log.csv（6 行，识别 1 条畸形记录）
- [x] 解析并校验 edge_cases.csv（6 行，识别重复、缺失、异常负值、公式注入）
- [x] 风险分级（严重 1、高 1、中 1、低 1、信息 1）
- [x] 攻击链关联分析（IP 203.0.113.8 两步攻击链）
- [x] 通用修复建议（含 SKILL.md 安全规则适用）
- [x] 复测清单（高/中/低优先级共 14 项）
- [x] 降级方案与未完成项说明

---

## 八、实际读取的 Skill 文件列表

以下为从 `gke-basics.zip` 解压后实际读取的文件（相对于 `gke-basics/` 目录）：

| 序号 | 相对路径 | 读取状态 |
|---|---|---|
| 1 | `SKILL.md` | 已完整读取 |
| 2 | `references/core-concepts.md` | 已完整读取 |
| 3 | `references/cli-reference.md` | 已完整读取 |
| 4 | `references/client-library-usage.md` | 已完整读取 |
| 5 | `references/mcp-usage.md` | 已完整读取 |
| 6 | `references/iac-usage.md` | 已完整读取 |

共 6 个文件，全部读取完毕，未编造任何未读取文件的内容。

---

## 九、确实影响结果的 SKILL.md 规则

以下规则从 SKILL.md 中实际读取，并对本审计的范围、深度和结论产生了实质性影响：

### 规则 1（影响最大）：Skill 适用边界声明

> **原文**（SKILL.md description 字段）："Don't use for specialized GKE networking (use gke-networking), **advanced security hardening (use gke-platform-security or gke-workload-security)**, or cluster upgrades (use gke-upgrades)."

**影响**：此规则直接决定了本审计不能提供高级安全加固方案，只能执行基础日志分诊和通用修复建议。报告中所有"高级安全加固"相关内容均被标记为降级项，并指向 `gke-platform-security` / `gke-workload-security`。如果忽略此规则，将超出 Skill 授权范围给出不恰当的深度安全建议。

### 规则 2：禁止在 Pod 中挂载原始服务账号 JSON 密钥

> **原文**（SKILL.md "Critical Gotchas & Best Practices" 第 2 条）："Never mount raw GCP Service Account JSON keys in Pods."

**影响**：此规则直接应用于 R-02（token_scope_mismatch）的修复建议。`service-a` 的令牌滥用问题，根因可能与静态密钥管理有关，修复建议明确要求使用 Workload Identity 替代静态 JSON 密钥，并给出了 KSA 注解的 YAML 示例。

### 规则 3：私有集群网络隔离最佳实践

> **原文**（SKILL.md 第 1 条）：使用 `--enable-private-nodes`、`--enable-private-endpoint`、`--enable-master-authorized-networks` 限制访问。

**影响**：此规则应用于 R-01（unexpected_export）的修复建议。数据导出来自外部 IP `203.0.113.8`，若相关服务部署在 GKE 中，未启用私有节点和授权网络则是导致外部可达的根本原因之一。

---

*报告结束。本报告基于模拟日志数据和 gke-basics Skill 规则生成，所有结论均有输入文件中的证据支撑，未编造外部凭据、平台数据或执行结果。*
