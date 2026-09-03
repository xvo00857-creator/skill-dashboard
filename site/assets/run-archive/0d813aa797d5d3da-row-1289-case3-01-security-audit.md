# 模拟安全日志审计报告（security-audit.md）

- 审计对象：`incident_log.csv`、`edge_cases.csv`（模拟数据，授权测试范围内）
- 参考基线：Skill `google-cloud-recipe-foundation-builder`（以实际读取的 `SKILL.md` 为唯一执行依据）
- 审计性质：只读分析，未实施任何破坏性操作、未连接任何真实云环境
- 生成时间基准：2026-08-26（UTC）

---

## 1. 执行声明与范围

本次任务包含两部分：

1. **可完成部分（已完成）**：对两份模拟安全日志做离线分析，输出风险分级、证据、修复建议与复测清单。
2. **不可完成部分（已阻断，见第 8 节）**：Skill 本体是 Google Cloud 落地区（landing zone）部署配方，其 Phase 3–5 需要真实 Google Cloud Organization、计费账号、`gcloud` 授权与管理员 IAM 角色，并要求在 Phase 1 取得用户显式批准后才能继续。当前环境不具备上述条件，且任务明确禁止登录授权、外部凭据与不可逆操作，因此部署部分**不执行、不模拟、不假装成功**。

> 说明：Skill 元数据 `category` 字段为 `GettingStarted`，与题表标注的“安全与合规”不一致；按要求以 `SKILL.md` 实际内容为准，此处仅作记录。

---

## 2. 输入文件与数据完整性校验

### 2.1 incident_log.csv

- 格式：标准 CSV，UTF-8，表头 `timestamp,system,severity,event,user,source_ip`
- 数据行数：6
- 时间范围：2026-08-12T09:00:12Z ~ 2026-08-12T09:09:00Z（约 9 分钟窗口）
- 严重级别分布：`info`×1、`warning`×2、`high`×1、`critical`×1、空值×1
- 源 IP 分布：`192.0.2.10`×1、`198.51.100.23`×2、`203.0.113.8`×2、空×1
- 字段缺失：第 6 行（`malformed_record`）缺失 `severity`、`user`、`source_ip`

### 2.2 edge_cases.csv

- 格式：标准 CSV，表头 `record_id,status,value,notes`
- 数据行数：6
- 重复主键：`record_id=2` 出现 2 次（完全重复）
- 缺失：`record_id=3` 的 `status`、`value` 为空，`notes` 为占位符 `-`
- 异常值：`record_id=4`，`status=error`，`value=-999`（负异常）
- 不安全输入 + 格式畸形：`record_id=5` 的 `value` 为 `=HYPERLINK("https://example.invalid","do not execute")`
  - 以 `=` 开头，属于 CSV 公式注入载荷（在 Excel/WPS 等电子表格中打开时存在执行风险）。
  - 该行内嵌双引号未按 CSV 规则转义（应为 `""`），导致解析器将其拆成 5 列而非 4 列，`notes` 字段被污染、多出一个无表头字段。**这是一条同时具备“注入风险”和“数据畸形”双重属性的记录。**

---

## 3. 风险分级与发现（incident_log.csv）

风险级别：`critical` > `high` > `medium` > `low` > `info`。

### F-01　疑似数据外泄（critical）

- **证据**：第 5 行，`2026-08-12T09:07:30Z`，`system=db`，`severity=critical`，`event=unexpected_export`，`user=unknown`，`source_ip=203.0.113.8`。
- **关联**：同一源 IP `203.0.113.8` 在 3 分 28 秒前（09:04:02Z）触发 `token_scope_mismatch`（F-02）。两事件同源、时间相邻，构成“令牌异常 → 数据导出”的疑似攻击链。
- **判定**：`user=unknown` 表明身份未解析或被冒用，结合 `critical` 级别的非预期导出，按数据外泄事件处置。
- **修复建议**：
  1. 立即冻结 `service-a` 相关凭据并轮换令牌；对 `203.0.113.8` 做临时封禁或加风控。
  2. 核查导出目标、导出数据量与敏感字段，判断是否触发数据泄露通报流程。
  3. 在数据库层启用导出审计与异常导出告警（对应 Skill 集中日志能力，见第 5 节）。
  4. 对 `unknown` 身份溯源：检查是否存在服务账号密钥滥用或未登记主体。
- **复测方法**：在封禁与轮换后，重放同源 IP 的导出请求应被拒绝；审计日志中 `unexpected_export` 不再出现，且 `user` 字段可解析。

### F-02　令牌作用域不匹配（high）

- **证据**：第 4 行，`09:04:02Z`，`system=api`，`severity=high`，`event=token_scope_mismatch`，`user=service-a`，`source_ip=203.0.113.8`。
- **判定**：服务账号 `service-a` 出示的令牌请求了超出其授权范围的作用域，可能是配置错误，也可能是令牌被窃取后尝试越权。结合 F-01，倾向于后者。
- **修复建议**：
  1. 复核 `service-a` 的最小权限配置，移除多余作用域。
  2. 对应 Skill 的 IAM 基线：禁用服务账号密钥创建（`iam.disableServiceAccountKeyCreation`）与密钥上传（`iam.disableServiceAccountKeyUpload`），优先使用 Workload Identity / 短期令牌。
  3. 对 `token_scope_mismatch` 建立实时告警阈值。
- **复测方法**：以 `service-a` 身份请求越权作用域应返回 403；正常作用域请求成功；告警规则可被测试用例触发。

### F-03　管理员账号短时间连续登录失败（medium）

- **证据**：第 2、3 行，`09:03:45Z` 与 `09:03:49Z`（间隔 4 秒），`user=admin`，`event=login_failed`，同源 `198.51.100.23`。
- **判定**：2 次失败尚不足以确认暴力破解，但“高权限账号 + 同 IP + 极短间隔”符合暴力破解/口令喷洒前兆，需升级监控。
- **修复建议**：
  1. 对 `admin` 账号强制 MFA 与登录限流；对应 Skill 基线 `compute.requireOsLogin`（将 SSH 登录绑定到 Google 身份）。
  2. 对 `198.51.100.23` 做短期封禁或验证码挑战。
  3. 设定规则：同账号 5 分钟内 ≥5 次失败即告警并临时锁定。
- **复测方法**：模拟连续失败应触发限流/告警；正确凭据 + MFA 可登录。

### F-04　日志记录残缺/畸形（medium）

- **证据**：第 6 行，`09:09:00Z`，`event=malformed_record`，`severity`、`user`、`source_ip` 均为空。
- **判定**：可能原因包括（a）日志采集端故障或格式变更；（b）攻击者进行日志投毒/字段截断以规避检测；（c）上游系统未做字段校验。无论哪种，都意味着该条事件不可审计，存在监控盲区。
- **修复建议**：
  1. 在日志采集管道加入 schema 校验，缺关键字段的记录进入“死信队列”并告警，而非静默丢弃或入库。
  2. 对应 Skill 集中日志基线：组织级日志 sink + `global` 日志桶（30 天保留）应保证审计日志不可被单端篡改；启用日志桶写入权限最小化（`roles/logging.bucketWriter` 仅授予 sink 服务账号）。
  3. 核查 09:09 前后采集端状态与变更记录。
- **复测方法**：构造一条缺字段的日志，应被拦截并产生告警；审计日志中可查到该拦截事件。

### F-05　正常登录（info，基线）

- **证据**：第 1 行，`alice` 从 `192.0.2.10` 登录成功。
- **判定**：无异常，作为行为基线保留。
- **复测方法**：无需处置。

---

## 4. 边界与失败场景发现（edge_cases.csv）

### E-01　重复记录（low）

- **证据**：`record_id=2` 出现 2 次，`status=ok`、`value=120`、`notes=重复记录`，内容完全一致。
- **风险**：重复入库会导致统计指标（计数、求和）失真。
- **修复**：以 `record_id` 为唯一键做去重，保留首条或最新一条；对上游采集端加幂等键。
- **复测**：去重后 `record_id=2` 仅存 1 条；重复投递不再产生新行。

### E-02　缺失记录（low）

- **证据**：`record_id=3`，`status` 与 `value` 为空，`notes=-`。
- **风险**：关键字段缺失使该记录无法参与判定，若大量出现会拉低数据完整率。
- **修复**：标记为“不完整”并隔离；要求上游补传或标注缺失原因。
- **复测**：补传后字段完整；隔离区中该记录可追溯。

### E-03　异常负值（medium）

- **证据**：`record_id=4`，`status=error`，`value=-999`，`notes=异常负值`。
- **风险**：若 `value` 语义为计数/时长/字节数等非负量，`-999` 属于非法值域，可能是哨兵值误用或注入，进入统计会造成偏差。
- **修复**：定义合法值域（如 `value ≥ 0`），越界值进入异常队列；禁止用负数作为“错误哨兵”混同业务值。
- **复测**：`-999` 被拦截；合法负值（若业务允许）白名单通过。

### E-04　CSV 公式注入 + 引号转义畸形（high）

- **证据**：`record_id=5`，`value==HYPERLINK("https://example.invalid","do not execute")`，`notes=公式注入测试文本`。
- **风险**：
  1. **公式注入**：以 `=` 开头，在 Excel/WPS/Google Sheets 中打开时可能被执行（本例为 `HYPERLINK`，可诱导点击钓鱼链接；更严重载荷可执行命令或泄露数据）。
  2. **CSV 引号未转义**：内嵌双引号未写成 `""`，导致标准 CSV 解析器将该行拆为 5 列，`notes` 被污染、产生无表头字段。这意味着该记录在多数下游管道中都会解析失败或错位。
- **修复**：
  1. 输出/导出 CSV 时，对以 `= + - @` 开头的单元格前置单引号 `'` 或做转义，确保被当作纯文本。
  2. 严格按 RFC 4180 转义：含逗号、引号、换行的字段用双引号包裹，内部双引号写为 `""`。
  3. 入库前对 `value` 做类型与前缀校验，公式载荷直接拒绝或净化。
- **复测**：用 Excel/WPS 打开净化后的文件，`HYPERLINK` 应显示为纯文本不执行；用标准 CSV 解析器读取，每行均为 4 列且无 `None` 键。

---

## 5. 与 Skill 安全基线的映射

Skill `google-cloud-recipe-foundation-builder` 在组织根强制 17 条 Organization Policy（13 条 Boolean + 4 条 List），并配置集中日志与监控。本次发现与基线的对应关系如下：

| 发现 | 相关 Skill 基线 | 用途 |
|---|---|---|
| F-01 数据外泄 | `storage.publicAccessPrevention`、`storage.uniformBucketLevelAccess`、集中日志桶（30 天保留） | 防止存储公开访问、统一 IAM、保留导出审计证据 |
| F-02 令牌越权 | `iam.disableServiceAccountKeyCreation`、`iam.disableServiceAccountKeyUpload`、`iam.automaticIamGrantsForDefaultServiceAccounts` | 减少长期密钥、默认服务账号过度授权 |
| F-03 暴力破解 | `compute.requireOsLogin`、`compute.disableSerialPortAccess` | 将登录绑定企业身份、关闭串口旁路 |
| F-04 日志畸形 | 组织级 log sink + `global` 桶 + `roles/logging.bucketWriter` 最小授权 | 保证审计日志集中、不可被单端篡改 |
| F-01/F-02 身份未知 | `iam.allowedPolicyMemberDomains`（按 Directory Customer ID 限域） | 阻止外部域身份被加入 IAM |
| 横向外联/公网暴露 | `compute.vmExternalIpAccess`（denyAll）、`sql.restrictPublicIp`、`compute.disableVpcExternalIpv6` | 收缩公网攻击面 |
| E-04 公式注入 | （应用层控制，Skill 无对应组织策略） | 需在数据导出/BI 层单独治理 |

> 关键约束（来自 `SKILL.md` Phase 3 警告）：`iam.allowedPolicyMemberDomains` 若先于其他策略应用，可能把部署身份自身锁在允许域之外。因此修复/部署时必须**最后**应用该策略，或先确认部署身份属于允许的 Customer ID。该规则直接影响修复动作的执行顺序。

---

## 6. 修复建议汇总（按优先级）

1. **立即（critical）**：处置 F-01——冻结 `service-a` 凭据、轮换令牌、封禁 `203.0.113.8`、启动数据外泄影响评估。
2. **短期（high）**：处置 F-02 与 E-04——复核 `service-a` 最小权限、禁用服务账号密钥创建/上传；净化 CSV 导出管道，治理公式注入与引号转义。
3. **中期（medium）**：处置 F-03、F-04、E-03——管理员 MFA + 登录限流、日志 schema 校验与死信告警、非负值域校验。
4. **长期（low）**：处置 E-01、E-02——主键去重、缺失记录隔离与补传机制。
5. **基线建设**：按 Skill 配方落地 17 条组织策略、4 文件夹层级、集中日志桶（`global`，30 天保留）与跨环境监控指标域——但需先满足第 8 节的前置条件。

---

## 7. 复测清单

- [ ] F-01：`203.0.113.8` 导出请求被拒绝；`service-a` 新令牌生效，旧令牌失效；审计日志可查。
- [ ] F-02：`service-a` 越权作用域请求返回 403；正常作用域成功；告警可触发。
- [ ] F-03：`admin` 连续失败触发限流/锁定；MFA 强制生效。
- [ ] F-04：缺字段日志被拦截并告警，不进入主存储；采集端状态可查。
- [ ] E-01：`record_id=2` 去重后仅 1 条；重复投递幂等。
- [ ] E-02：`record_id=3` 进入隔离区，补传后字段完整。
- [ ] E-03：`value=-999` 被值域校验拦截。
- [ ] E-04：净化后 CSV 在 Excel/WPS 中 `HYPERLINK` 显示为纯文本；标准解析器每行 4 列。
- [ ] 基线：17 条组织策略可被 `gcloud org-policies list` 验证（需在具备条件的环境中执行，见第 8 节）。

---

## 8. 阻断项：GCP 落地部署未执行

### 8.1 阻断结论

Skill 的 Phase 3（安全护栏/组织策略）、Phase 4（资源层级/文件夹与项目/计费关联）、Phase 5（集中日志与监控）**均未执行**。本次仅完成离线日志分析。

### 8.2 缺失条件（依据 `SKILL.md` 的 Clarifying Questions 与 Prerequisites）

1. **Organization ID**：未提供，且无法运行 `gcloud organizations list`（无 `gcloud` 授权）。
2. **Billing Account ID**：未提供，且无法运行 `gcloud billing accounts list --filter=open=true`。
3. **Project ID Suffix** 与 **Log Bucket Region**：未提供（Skill 要求在执行前收集）。
4. **`gcloud` CLI 已安装并授权**：当前沙箱未配置可用的 Google Cloud 身份与配额项目。
5. **管理员 IAM 角色**：部署身份需具备 Organization Admin / Billing Admin / Logging-Monitoring Admin / Security Admin 等组角色；当前不具备。
6. **用户显式批准**：`SKILL.md` Phase 1 要求在呈现蓝图摘要后**暂停并等待用户明确批准**才能进入 Phase 2；本次任务同时明确禁止交互式确认与登录授权，因此该批准无法取得。
7. **不可逆/付费操作性质**：创建项目、关联计费、启用 API、创建日志桶与 sink 均属于真实云资源变更与可能产生费用的操作，任务明确禁止在未授权情况下实施。

### 8.3 降级方案

- 以 Skill 的 17 条组织策略、IAM 角色组、集中日志（`global` 桶、30 天保留、组织级 sink）作为**参考基线**写入本报告的修复建议（第 5、6 节），不实际调用 `gcloud`。
- 所有 `gcloud` 命令仅作为复测/部署手册条目列出，不在本环境执行。

### 8.4 复测方法（在具备条件的环境中）

1. 安装并授权 `gcloud`：`gcloud auth login` + `gcloud auth application-default login`，设置配额项目。
2. 收集四项输入：Organization ID、Billing Account ID、Project ID Suffix、Log Bucket Region（默认 `global`）。
3. 执行 Phase 1：`gcloud organizations describe [ORG_ID]` 提取 `displayName`（域名）与 `owner.directoryCustomerId`；呈现蓝图摘要并取得用户书面批准。
4. 按 Phase 3→4→5 顺序执行；遇 `Permission Denied` 按 Skill 的“懒式角色修复”策略授予对应管理组全部角色后重试；若授权命令失败则停机并请组织/计费管理员手动授予。
5. 执行 Skill 的 Validation Checklist：`gcloud org-policies list`、文件夹存在性、`gcloud billing projects list`、日志桶保留期=30 天、sink `writerIdentity`、监控指标域包含 dev/non-prod/prod。

---

## 9. 实际读取的 Skill 文件相对路径

解压根目录：`google-cloud-recipe-foundation-builder/`

- `google-cloud-recipe-foundation-builder/SKILL.md`
- `google-cloud-recipe-foundation-builder/references/admin-iam.md`
- `google-cloud-recipe-foundation-builder/references/logging-monitoring.md`
- `google-cloud-recipe-foundation-builder/references/org-policies.md`

共 4 个文件，全部已读取；未读取任何压缩包外文件，未编造外部凭据或平台数据。

---

## 10. 确实影响结果的 SKILL.md 规则

**规则（Phase 1 Pre-flight Confirmation）**：在呈现“Proposed Foundation Deployment Summary”后，必须**暂停执行并等待用户明确批准（Yes/No）**，否则不得进入 Phase 2 及后续部署阶段。

- **如何影响结果**：该规则直接决定了 Skill 的部署部分在本次任务中**必须被判定为阻断而非可降级执行**——因为任务同时禁止交互式确认、登录授权与不可逆操作，无法取得该显式批准。若忽略此规则而尝试执行 Phase 3–5，将违反 Skill 自身的安全闸门，并可能在无授权情况下创建真实云资源、产生费用。因此本报告将部署部分明确列为“未执行/阻断”，并仅把其安全控制作为参考基线，这一结论正是由该规则导出的。

> 次级影响规则：Phase 3 警告——`iam.allowedPolicyMemberDomains` 若先应用可能锁出部署身份，因此该策略必须**最后**应用或先确认身份属于允许域。这直接影响第 5 节修复动作的执行顺序建议。
