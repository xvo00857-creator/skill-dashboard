# 安全审计报告：模拟安全日志分析

- 审计日期：2026-08-13
- 审计人：Doubao（MainAgent）
- 输入文件：`incident_log.csv`、`edge_cases.csv`
- 执行依据：`competition-browser-persistence` Skill（以实际读取的 `SKILL.md` 为唯一执行依据）
- 授权范围：仅对随附的模拟日志做静态分析与风险分级；不接触任何真实系统，不执行任何破坏性、写入性或利用性操作

---

## 1. Skill 适用性与前置条件声明（影响结果的关键规则）

本节直接决定本次审计的执行方式与结论边界，请先阅读。

### 1.1 实际读取的 Skill 文件（相对路径）

- `competition-browser-persistence/SKILL.md`
- `competition-browser-persistence/references/browser-persistence.md`
- `competition-browser-persistence/agents/openai.yaml`

### 1.2 前置条件未满足（阻断项）

`SKILL.md` 第 8 行明确规定：

> "Use this skill only as a downstream specialization after `$ctf-sandbox-orchestrator` is already active and has established sandbox assumptions, node ownership, and evidence priorities. **If that has not happened yet, return to `$ctf-sandbox-orchestrator` first.**"

`agents/openai.yaml` 亦声明 `allow_implicit_invocation: false`。

实际情况：

- 本会话中 `$ctf-sandbox-orchestrator` **未激活、未安装**（已在全部 Skill 根目录检索，无 `ctf-sandbox-orchestrator`）。
- 该 Skill 的 Quick Start 第 1 步要求"识别活动持久化面：cookie jar、localStorage、sessionStorage、IndexedDB、Cache Storage 或 service worker"，但本次输入仅为两份 CSV 文本日志，**不存在任何浏览器状态面**可供映射、变更或重放。

因此，该 Skill 的原生工作流（Map Browser State Surfaces → Tie State To Runtime Behavior → Reduce To The Decisive Persistence Chain）**无法按原样执行**。按 `SKILL.md` 指示应"先返回 `$ctf-sandbox-orchestrator`"，但该前置 Skill 不在环境中，无法跳转。

### 1.3 降级方案

在前置条件不满足的前提下，本次审计**不冒充**完成浏览器持久化分析，而是：

1. 严格沿用 `SKILL.md` 与 `references/browser-persistence.md` 的**证据纪律**作为分析框架：
   - 证据分块保存（"Keep auth tokens, refresh material, CSRF state, cached responses, and feature toggles in separate evidence blocks"）；
   - 相关性五步法（状态项 → 来源/范围确认 → 行为关联 → 干净态 vs 变更态对比 → 决定性分支复现）；
   - 证据三要素（状态标识、运行时影响、重放前置条件）。
2. 将上述方法迁移到日志审计：以"正常基线 vs 异常态"对比替代"干净态 vs 变更态"；对每条发现给出证据、影响、修复与复测方法。
3. 遵守 `references/browser-persistence.md` 的陷阱条款，尤其是：
   - "Treating cached UI data as backend authorization without proving a server-side effect"——迁移为：**不得仅凭日志时间相邻就断言攻击链因果关系**，必须标注"已证实"与"可疑待证"。
   - "Listing storage contents without showing which item changes behavior"——迁移为：**不罗列日志条目，每条发现必须关联到具体风险影响**。

### 1.4 影响结果的一条 SKILL.md 规则

**第 8 行的前置编排器门禁规则**直接影响了结果：它使本次交付定性为"前置条件缺失下的降级静态审计"，而非 Skill 原生的浏览器持久化取证；报告中所有结论均不包含浏览器状态重放、cookie/存储变更或 service worker 分析，因为输入中不存在这些对象。

---

## 2. 输入概览

### 2.1 `incident_log.csv`

- 表头：`timestamp, system, severity, event, user, source_ip`
- 数据行：6 行
- 时间范围：2026-08-12T09:00:12Z ～ 09:09:00Z（约 9 分钟窗口）

| # | timestamp (UTC) | system | severity | event | user | source_ip |
|---|---|---|---|---|---|---|
| 1 | 09:00:12 | web | info | login_success | alice | 192.0.2.10 |
| 2 | 09:03:45 | web | warning | login_failed | admin | 198.51.100.23 |
| 3 | 09:03:49 | web | warning | login_failed | admin | 198.51.100.23 |
| 4 | 09:04:02 | api | high | token_scope_mismatch | service-a | 203.0.113.8 |
| 5 | 09:07:30 | db | critical | unexpected_export | unknown | 203.0.113.8 |
| 6 | 09:09:00 | web | （空） | malformed_record | （空） | （空） |

### 2.2 `edge_cases.csv`

- 表头：`record_id, status, value, notes`
- 数据行：6 行

| # | record_id | status | value | notes |
|---|---|---|---|---|
| 1 | 1 | ok | 120 | 正常记录 |
| 2 | 2 | ok | 120 | 重复记录 |
| 3 | 2 | ok | 120 | 重复记录 |
| 4 | 3 | （空） | （空） | - |
| 5 | 4 | error | -999 | 异常负值 |
| 6 | 5 | ok | `=HYPERLINK("https://example.invalid","do not execute")` | 公式注入测试文本 |

### 2.3 数据来源性质判定

三个源 IP `192.0.2.10`、`198.51.100.23`、`203.0.113.8` 均属于 RFC 5737 保留的 TEST-NET 段；公式注入中的域名 `example.invalid` 属于 RFC 2606 保留的 `.invalid` TLD。这与"模拟安全日志"的题设一致，**不涉及真实主机或真实回调**，本次分析全程在授权测试范围内。

---

## 3. 数据质量与完整性检查

按 Skill 证据纪律，先固定输入本身的完整性问题，再进入风险分级。

### 3.1 `incident_log.csv`

- **空字段**：第 6 行 `severity`、`user`、`source_ip` 三列为空，`event` 自身值为 `malformed_record`。
- **重复**：无完全重复行；第 2、3 行为同用户同 IP 的两次不同失败事件（间隔 4 秒），属行为模式而非数据重复。
- **时间格式**：均为 ISO 8601 UTC（`Z` 结尾），格式一致。

### 3.2 `edge_cases.csv`

- **重复主键**：`record_id=2` 出现两次（第 2、3 行），整行内容完全相同。
- **缺失字段**：`record_id=3` 的 `status`、`value` 为空。
- **异常取值**：`record_id=4` 的 `value=-999`，且 `status=error`；-999 常见于哨兵/错误码，需与正常值域区分。
- **公式注入载荷**：`record_id=5` 的 `value` 以 `=` 开头，为电子表格公式注入（CSV Injection）测试文本。
- **CSV 转义不规范（解析器兼容性问题）**：该公式行在文件中写作 `"=HYPERLINK(\"https://example.invalid\",\"do not execute\")"`，使用反斜杠 `\"` 转义内嵌引号，而非 RFC 4180 标准的双引号转义 `""`。实测 Python 标准库 `csv.DictReader`（默认 RFC 4180 方言）会将其错误切分为 5 列，导致 `notes` 列内容溢出到 `None` 键；需指定 `escapechar="\\" 才能正确还原。**这意味着依赖标准 CSV 解析器的下游管道可能静默错列或丢字段。**

---

## 4. 风险分级发现

分级标准：Critical（已发生/可能导致数据外泄或越权）、High（活跃攻击迹象）、Medium（需修复的弱点/完整性缺陷）、Low（数据质量或加固项）。

### F-1【Critical】未授权数据导出，且与同 IP 令牌越权事件时间相关

- **证据块（服务端已记录事件）**：
  - 09:04:02Z `api/high/token_scope_mismatch`，主体 `service-a`，源 IP `203.0.113.8`；
  - 09:07:30Z `db/critical/unexpected_export`，主体 `unknown`（未认证/未知主体），源 IP `203.0.113.8`；
  - 两事件间隔约 3 分 28 秒，**同一源 IP**。
- **影响**：数据库发生"非预期导出"且主体为 `unknown`，存在数据外泄的现实可能；前序 `token_scope_mismatch` 提示服务账号令牌可能被滥用或权限范围配置错误。
- **因果性判定（依据 Skill 陷阱条款）**：同一 IP 将两事件**关联为可疑**，但仅凭这两行日志**不能证实**"令牌越权直接导致导出"的因果链——缺少令牌 ID、请求路径、导出对象/行数、认证结果等字段。结论标注为"高度可疑、因果待证"，不夸大为已证实攻击链。
- **修复建议**：
  1. 立即轮换/吊销 `service-a` 的相关令牌/凭据，审查其 scope 配置与最小权限；
  2. 在数据库侧审计 09:07:30Z 前后的导出任务：导出者、导出表、行数、目标位置；
  3. 对 `203.0.113.8` 在该时间窗的所有 api/db 行为做回溯；
  4. 对 DB 导出增加强制审批、二次认证与行数/敏感表白名单控制。
- **复测方法**：修复后，用 `service-a` 令牌请求超出其 scope 的导出接口，应被服务端拒绝并产生 `token_scope_mismatch` 但**不产生**任何 `unexpected_export`；以未认证主体请求导出应返回 401/403 且无数据落盘。

### F-2【High】admin 账户短时连续登录失败（爆破迹象）

- **证据块**：09:03:45Z 与 09:03:49Z，`web/warning/login_failed`，用户 `admin`，同一 IP `198.51.100.23`，间隔 4 秒。
- **影响**：对管理账户的自动化口令猜测迹象；虽仅 2 次未达锁定阈值，但与 13 秒后发生的 F-1 首事件时间接近（不同 IP，未证实关联）。
- **修复建议**：
  1. 对 admin 登录启用速率限制与指数退避，N 次失败后临时锁定并告警；
  2. 为管理后台强制 MFA；
  3. 禁止/重命名默认 `admin` 账户，使用具名管理员账户；
  4. 将"同 IP 同用户短时多次失败"纳入实时告警规则。
- **复测方法**：在测试环境对 admin 连续提交错误口令，验证第 N 次后账户锁定/要求验证码并触发告警；使用正确口令+MFA 可正常登录。

### F-3【Medium】日志完整性缺陷：畸形记录致关键字段缺失

- **证据块**：第 6 行 `09:09:00Z,web,,malformed_record,,`，`severity/user/source_ip` 均为空。
- **影响**：关键归因字段缺失会直接削弱检测与溯源；若为管道写入失败说明可观测性管道有丢字段风险，若为被篡改则可能是掩盖痕迹。无法从现有数据区分成因。
- **修复建议**：
  1. 日志接入侧增加 schema 校验，`severity/user/source_ip` 等关键字段缺失时拒收并进入隔离队列；
  2. 对 `malformed_record` 类事件建立计数与告警；
  3. 日志管道启用端到端完整性校验（如序号/哈希链）以区分写入故障与篡改。
- **复测方法**：向日志入口提交缺字段样本，验证其被拒绝/隔离而非落库；人为制造管道故障，验证畸形率监控告警。

### F-4【Medium】CSV 公式注入（CSV Injection）

- **证据块**：`edge_cases.csv` 第 6 行 `value` 为 `=HYPERLINK("https://example.invalid","do not execute")`，以 `=` 起始。
- **影响**：该文件若被 Excel/WPS/LibreOffice/在线表格直接打开，`=HYPERLINK` 可能被解释为公式并渲染可点击链接，诱导用户访问恶意站点；同类载荷还可使用 `cmd|'/c ...'!A1` 等形式触发外部命令（取决于客户端与版本）。当前域名为 `.invalid` 保留域，无真实危害，但载荷模式不安全。
- **修复建议**：
  1. 导出 CSV 时，对以 `= + - @` 或 Tab/回车开头的单元格，前置单引号 `'` 或强制按文本写入；
  2. 接收侧将该类输入视为不可信文本，禁止直接以表格公式解析；
  3. 对用户可控字段做输出编码。
- **复测方法**：在修复后的导出中重新放入 `=HYPERLINK(...)` 载荷，用 Excel 打开应显示为纯文本而非可点击公式/链接。

### F-5【Medium】CSV 转义不规范导致标准解析器错列

- **证据块**：第 6 行使用 `\"` 转义内嵌引号；实测 Python `csv.DictReader` 默认方言将该行解析为 5 列，`notes` 内容溢出，`value` 被截断为 `=HYPERLINK(\https://example.invalid\"`。
- **影响**：下游使用标准 RFC 4180 解析器的系统会静默错列、丢字段或误类型，可能导致风控/统计基于错误数据；也可能被利用来绕过依赖列位置的校验。
- **修复建议**：统一使用 RFC 4180 双引号转义（`""`），或改用 JSON/TSV 等明确编码；在数据交换契约中固定方言并增加解析后列数校验。
- **复测方法**：用标准 `csv.DictReader` 解析修复后的文件，断言每行列数等于表头列数且 `value` 完整还原。

### F-6【Low】重复主键记录

- **证据块**：`record_id=2` 整行重复出现两次。
- **影响**：可能导致计数/统计翻倍、去重逻辑误判；反映写入端缺乏幂等性。
- **修复建议**：以 `record_id` 建唯一约束；写入端采用幂等键；分析侧按主键去重。
- **复测方法**：重复提交同一 `record_id`，验证第二次被拒绝或覆盖而非新增。

### F-7【Low】必填字段缺失

- **证据块**：`record_id=3` 的 `status`、`value` 为空，`notes` 为 `-`。
- **影响**：记录不可用，可能代表采集失败或未完成事务。
- **修复建议**：`status`、`value` 设为 NOT NULL 并定义取值约束；缺失记录进入隔离区并告警。
- **复测方法**：提交缺字段记录，验证被校验拒绝。

### F-8【Low】异常负值

- **证据块**：`record_id=4`，`status=error`，`value=-999`。
- **影响**：-999 常被用作错误哨兵值；若直接混入数值统计会拉低指标。当前 `status=error` 已自带标记，风险较低，但需与正常值域显式区分。
- **修复建议**：错误码与测量值分字段/分表存储；定义 `value` 合法值域并校验。
- **复测方法**：提交越界负值，验证被标记/拒绝而非进入统计。

---

## 5. 风险汇总矩阵

| 编号 | 等级 | 发现 | 关键证据 | 状态 |
|---|---|---|---|---|
| F-1 | Critical | 未授权 DB 导出 + 同 IP 令牌越权（因果待证） | 09:04:02 token_scope_mismatch；09:07:30 unexpected_export；同 IP 203.0.113.8 | 待处置/待取证 |
| F-2 | High | admin 短时连续登录失败 | 09:03:45、09:03:49 两次 login_failed，同 IP | 待处置 |
| F-3 | Medium | 日志畸形记录、关键字段缺失 | incident_log 第 6 行 severity/user/source_ip 为空 | 待处置 |
| F-4 | Medium | CSV 公式注入载荷 | edge_cases record_id=5 value 以 `=` 开头 | 待处置 |
| F-5 | Medium | 非标准 CSV 转义致解析错列 | `\"` 转义；标准解析器得 5 列 | 待处置 |
| F-6 | Low | 重复主键 | record_id=2 出现两次 | 待处置 |
| F-7 | Low | 必填字段缺失 | record_id=3 status/value 为空 | 待处置 |
| F-8 | Low | 异常负值 | record_id=4 value=-999 | 待处置 |

---

## 6. 复测清单（修复后逐项验证）

- [ ] **F-1**：越权 scope 令牌无法触发任何导出；未认证导出返回 401/403 且无数据落盘；`service-a` 旧令牌已失效。
- [ ] **F-1**：补全 09:07:30Z 导出的溯源（主体、表、行数、去向）并形成事件结论。
- [ ] **F-2**：admin 连续失败 N 次后锁定/告警；MFA 生效；默认 admin 账户已更名或禁用。
- [ ] **F-3**：缺字段日志被接入侧拒绝/隔离；畸形率监控与告警可用。
- [ ] **F-4**：`=+-@` 开头字段在导出 CSV 中被强制为文本，Excel 打开不执行公式。
- [ ] **F-5**：文件改用 RFC 4180 转义；标准解析器逐行列数断言通过。
- [ ] **F-6**：`record_id` 唯一约束生效，重复写入被幂等处理。
- [ ] **F-7**：status/value 缺失记录被 NOT NULL 校验拒绝。
- [ ] **F-8**：value 值域校验生效，-999 类哨兵值不进入统计。
- [ ] **全局**：在前置 Skill `$ctf-sandbox-orchestrator` 可用且提供真实浏览器状态工件（cookie/存储/service worker 导出）后，重新执行 `competition-browser-persistence` 原生工作流，补齐浏览器持久化取证（本次因输入不含浏览器状态面而无法完成）。

---

## 7. 阻断与未完成项说明

1. **未完成：浏览器持久化原生取证。** 阻断原因：`SKILL.md` 第 8 行要求前置 `$ctf-sandbox-orchestrator` 已激活，该 Skill 在本环境未安装；且输入 CSV 不含任何 cookie/localStorage/sessionStorage/IndexedDB/Cache Storage/service worker 工件，Quick Start 第 1 步无对象可识别。已按第 1.3 节降级为静态日志审计，并在第 6 节给出复测条件。
2. **未完成：F-1 因果链确证。** 阻断原因：日志缺少令牌 ID、请求路径、认证结果、导出对象/行数等字段，无法证实"令牌越权→数据导出"的因果关系；已标注为"高度可疑、因果待证"，需补充日志或数据库审计记录。
3. **未完成：F-3 畸形记录成因判定。** 阻断原因：无管道侧错误与完整性校验数据，无法区分写入故障与篡改；已给出两种可能与对应修复/复测。

本次审计未执行任何破坏性操作，未访问除随附文件以外的任何系统或凭据。
