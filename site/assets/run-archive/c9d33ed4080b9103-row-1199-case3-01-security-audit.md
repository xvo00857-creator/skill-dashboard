# 模拟安全日志审计报告

> 产物文件：`security-audit.md`
> 生成时间基准：2026-08-26（UTC）
> 审计范围：仅对随消息提供的模拟日志做静态分析，未对任何真实系统发起探测、登录或破坏性操作。

---

## 1. 审计概览

| 项目 | 内容 |
|---|---|
| 业务任务 | 在授权测试范围内分析模拟安全日志，形成风险分级、证据、修复建议和复测清单 |
| 输入文件 | `incident_log.csv`（6 条事件）、`edge_cases.csv`（6 条边界记录） |
| 指定 Skill | `js-reverse`（分类：安全与合规） |
| 实际执行方式 | 静态日志取证 + 字段级异常检测（降级路径，见第 2 节） |
| 结论摘要 | 发现 1 条严重（critical）数据外泄关联事件、1 条高危令牌越权、1 条中危暴力破解前兆、1 条 CSV 公式注入、2 类数据质量问题（畸形记录、重复记录）；无真实环境凭据或外部平台数据被使用 |

---

## 2. Skill 执行状态与范围错配声明

### 2.1 按 SKILL.md「ACTION REQUIRED」逐项核验

| 步骤 | SKILL.md 要求 | 实际结果 | 对结果的影响 |
|---|---|---|---|
| 1. NOW | 读取 `../field-journal/precedent-reverse.md` 确认授权 | **文件缺失**（ZIP 内无 `field-journal/` 目录） | 无法完成"已授权常规操作"确认；本任务改为基于用户明确授权文本执行 |
| 2. NOW | 确认当前任务是否命中适用范围 | **未命中**：Skill 适用范围为前端 JS 逆向（签名链路、页面观察、运行时采样、本地补环境），本次任务为 CSV 安全日志分析 | 五阶段工作流（Observe→Capture→Rebuild→Patch→DeepDive）不适用；按 `references/fallbacks.md` 回退到静态取证 |
| 3. NEXT | 读取 `../tool-index.md` 校验工具可用性和实际路径 | **文件缺失** | 无法校验 `js-reverse_*` 工具路径；经工具清单确认本环境无任何 `js-reverse_*` MCP 工具 |
| 4. NEXT | 缺工具时调用 bootstrap | **阻断**：ZIP 内无 `scripts/bootstrap-reverse.ps1`，且本环境为 Linux（bootstrap 为 PowerShell 脚本），`jshookmcp` 未注册 | 无法自举 MCP 工具面 |
| 5. ACT | 进入工作流第一步 | **降级执行**：以 Skill 的「Evidence-first（先取证再结论）」原则指导静态日志分析，不臆测运行时环境 | 分析深度限于日志字段本身，无法做运行时采样 |

### 2.2 确实影响结果的 SKILL.md 规则

**规则一（适用范围判定）**：SKILL.md 明确列出适用场景为"定位接口签名、加密参数、风控字段 / 观察页面请求链路 / 运行时抓取函数入参 / 追踪 XHR/Fetch/WebSocket / 本地补环境复现"，并声明"如果目标是二进制、APK、PE、ELF、DLL、SO，请改用其他 skill"。本次输入是两个 CSV 日志文件，既无目标页面也无 JS 脚本，**不命中适用范围**。该规则直接决定：不能调用 `js-reverse_new_page` / `js-reverse_break_on_xhr` 等工具，也不能按五阶段工作流执行，必须走回退路径。

**规则二（Evidence-first 核心原则）**：SKILL.md 核心原则要求"先页面观察，再最小化采样，再做本地补环境，不要跳过取证直接猜环境"。在降级场景下，该原则转化为"所有风险结论必须绑定到原始日志行号与字段值，不得基于推断补全缺失字段"。这直接影响第 4、5 节的证据呈现方式——每条风险均标注原始行号与原始字段值。

**规则三（回退策略 `references/fallbacks.md`）**：当当前路径无进展时按顺序回退（断点→请求观察→运行时证据→页面取证→最小可复现链路）。本任务在第一步即因工具缺失无进展，故回退到"最小可复现链路"的等价形态：基于原始 CSV 字节的静态字段级取证。

---

## 3. 输入文件校验（缺失 / 重复 / 异常 / 不安全输入）

### 3.1 `incident_log.csv`

- 文件格式：标准 CSV，UTF-8，LF 换行，1 行表头 + 6 行数据。
- 表头：`timestamp,system,severity,event,user,source_ip`
- 字段缺失：第 7 行（`malformed_record`）的 `severity`、`user`、`source_ip` 三列为空。
- 重复行：无完全重复行；但第 3、4 行（`login_failed`）在 `user` + `source_ip` + `event` 维度重复，属于事件重复而非记录重复。
- 异常值：
  - `user=unknown`（第 6 行）——非空但为不可解析主体，属异常标识。
  - 所有 `source_ip` 均来自 RFC 5737 文档保留段（`192.0.2.0/24`、`198.51.100.0/24`、`203.0.113.0/24`），符合模拟数据特征，不视为真实攻击源。
- 时间范围：`2026-08-12T09:00:12Z` 至 `2026-08-12T09:09:00Z`，约 9 分钟窗口。

### 3.2 `edge_cases.csv`

- 文件格式：标准 CSV，UTF-8，LF 换行，1 行表头 + 6 行数据。
- 表头：`record_id,status,value,notes`
- 重复行：第 3、4 行（`record_id=2`）为**完全重复行**（所有字段一致）。
- 字段缺失：第 5 行（`record_id=3`）的 `status`、`value` 为空，`notes=-`。
- 异常值：第 6 行（`record_id=4`）`status=error`、`value=-999`（负值，若该字段为计数/时长则异常）。
- 不安全输入：第 7 行（`record_id=5`）`value` 字段为 `=HYPERLINK("https://example.invalid","do not execute")`——**CSV 公式注入（Formula Injection）**载荷，以 `=` 开头，若用 Excel/Calc 打开且未做防护会触发公式执行与外链跳转。`notes` 字段自述为"公式注入测试文本"，确认是测试用例而非误输入。

---

## 4. `incident_log.csv` 风险分析

### 4.1 逐条事件

| 行号 | 时间 (UTC) | 系统 | 级别 | 事件 | 用户 | 源 IP | 风险判定 |
|---|---|---|---|---|---|---|---|
| 2 | 09:00:12 | web | info | login_success | alice | 192.0.2.10 | 正常基线，无风险 |
| 3 | 09:03:45 | web | warning | login_failed | admin | 198.51.100.23 | 中危（见 4.2） |
| 4 | 09:03:49 | web | warning | login_failed | admin | 198.51.100.23 | 中危（见 4.2） |
| 5 | 09:04:02 | api | high | token_scope_mismatch | service-a | 203.0.113.8 | 高危（见 4.3） |
| 6 | 09:07:30 | db | critical | unexpected_export | unknown | 203.0.113.8 | 严重（见 4.4） |
| 7 | 09:09:00 | web | *(空)* | malformed_record | *(空)* | *(空)* | 数据质量问题（见 4.5） |

### 4.2 中危：admin 账号连续登录失败（暴力破解前兆）

- **证据**：第 3、4 行，同一用户 `admin`、同一源 IP `198.51.100.23`，在 4 秒内（09:03:45 → 09:03:49）连续两次 `login_failed`。
- **分析**：2 次失败低于常见暴力破解阈值（通常 5 次/分钟），但间隔极短且针对高权限 `admin` 账号，具备枚举/撞库前兆特征。因日志窗口仅 9 分钟，无法判断后续是否继续。
- **分级**：中危（Medium）。
- **修复建议**：对 `admin` 等特权账号启用登录失败限速（如 5 次/15 分钟锁定）、强制 MFA、对 `198.51.100.23` 段做临时观察封禁。
- **复测方法**：构造同一 IP 对 `admin` 的连续失败登录，验证限速与告警是否触发；确认告警中包含源 IP、账号、时间窗口。

### 4.3 高危：service-a 令牌作用域不匹配（越权前兆）

- **证据**：第 5 行，`system=api`，`severity=high`，`event=token_scope_mismatch`，`user=service-a`，`source_ip=203.0.113.8`。
- **分析**：服务账号 `service-a` 使用的令牌请求了超出其授权范围的 API。该事件本身即表明令牌权限边界被触碰，可能是配置错误、令牌泄露被滥用，或横向移动的第一步。
- **分级**：高危（High）。
- **修复建议**：立即轮换 `service-a` 令牌；审计该令牌的 scope 配置与近期调用记录；遵循最小权限原则收敛 scope；在 API 网关对 scope mismatch 做实时拦截而非仅记录。
- **复测方法**：用收敛后的令牌尝试越权调用，确认被 403 拦截且产生告警；确认旧令牌已失效。

### 4.4 严重：数据库异常导出（疑似数据外泄）—— 与 4.3 关联

- **证据**：第 6 行，`system=db`，`severity=critical`，`event=unexpected_export`，`user=unknown`，`source_ip=203.0.113.8`。
- **关联分析**：该事件源 IP `203.0.113.8` 与第 5 行 `token_scope_mismatch` 的源 IP **完全相同**，且时间上紧随其后（09:04:02 → 09:07:30，间隔 3 分 28 秒）。这构成一条疑似攻击链：**先用越权令牌探测 API（high），再从同一 IP 发起数据库异常导出（critical）**。`user=unknown` 说明导出操作未关联到可审计身份，进一步升高风险。
- **分级**：严重（Critical）。
- **修复建议**：
  1. 立即隔离 `203.0.113.8`（如为真实 IP 则封禁，模拟环境则记录为 IOC）。
  2. 核查该时段数据库导出的目标地址、导出数据量与表范围，确认是否发生真实数据外泄。
  3. 对数据库导出操作强制身份认证与审批流，禁止 `unknown` 主体执行导出。
  4. 将 `token_scope_mismatch` 与 `unexpected_export` 按源 IP 做关联告警规则。
- **复测方法**：模拟"同一 IP 先触发 token_scope_mismatch、3 分钟内触发 unexpected_export"的序列，验证关联告警是否触发；验证 `unknown` 主体的导出请求被拒绝。

### 4.5 数据质量：畸形记录

- **证据**：第 7 行，`event=malformed_record`，但 `severity`、`user`、`source_ip` 均为空。
- **分析**：该行可能是日志采集器自身上报的解析失败事件，也可能是被篡改/截断的日志。缺失关键字段导致无法做风险归因。
- **分级**：数据质量问题（不纳入安全风险分级，但影响审计完整性）。
- **修复建议**：在日志采集端增加字段校验，对缺失必填字段的记录做死信队列留存并告警；明确 `malformed_record` 的上报规范（必须包含原始载荷摘要）。
- **复测方法**：向采集端注入一条缺字段日志，确认其进入死信队列并触发告警，而非静默进入主日志表。

---

## 5. `edge_cases.csv` 风险分析

### 5.1 逐条记录

| 行号 | record_id | status | value | notes | 风险判定 |
|---|---|---|---|---|---|
| 2 | 1 | ok | 120 | 正常记录 | 正常基线 |
| 3 | 2 | ok | 120 | 重复记录 | 重复（见 5.2） |
| 4 | 2 | ok | 120 | 重复记录 | 重复（见 5.2） |
| 5 | 3 | *(空)* | *(空)* | - | 缺失（见 5.3） |
| 6 | 4 | error | -999 | 异常负值 | 异常（见 5.4） |
| 7 | 5 | ok | `=HYPERLINK(...)` | 公式注入测试文本 | 不安全输入（见 5.5） |

### 5.2 重复记录

- **证据**：第 3、4 行完全相同（`record_id=2, status=ok, value=120, notes=重复记录`）。
- **分析**：完全重复行可能由采集端重试未去重、消息队列至少一次投递、或 ETL 重复加载导致。若该表用于计数/聚合统计，重复会导致指标虚高。
- **分级**：低危（Low，数据完整性）。
- **修复建议**：在入库层对 `record_id` 做唯一约束或 upsert；消费端启用幂等键。
- **复测方法**：重复投递同一条 `record_id=2`，确认库中仅保留一条。

### 5.3 字段缺失

- **证据**：第 5 行，`record_id=3`，`status` 与 `value` 为空，`notes=-`。
- **分析**：关键字段缺失使该记录无法参与状态统计与数值聚合，可能是上游系统异常或采集过滤所致。
- **分级**：低危（Low，数据完整性）。
- **修复建议**：对 `status`、`value` 设为 NOT NULL 或提供默认哨兵值（如 `status=unknown`、`value=NULL` 显式标记）；缺失率超阈值时告警。
- **复测方法**：注入缺字段记录，确认被标记或拦截，而非以空值静默入库。

### 5.4 异常负值

- **证据**：第 6 行，`record_id=4`，`status=error`，`value=-999`，`notes=异常负值`。
- **分析**：若 `value` 语义为计数、时长、字节数等非负量，`-999` 为非法值；`-999` 也常被用作错误哨兵值，需确认语义。`status=error` 与异常值同时出现，表明上游处理失败。
- **分级**：中危（Medium，数据可信度）——若该值流入下游报表或风控模型，可能导致误判。
- **修复建议**：明确 `value` 字段的合法值域并在采集端校验；错误场景使用独立的 `error_code` 字段而非污染 `value`；对负值做拦截。
- **复测方法**：注入 `value=-999`，确认被校验拦截或归入错误队列。

### 5.5 CSV 公式注入（不安全输入）

- **证据**：第 7 行，`record_id=5`，`value="=HYPERLINK(\"https://example.invalid\",\"do not execute\")"`，`notes=公式注入测试文本`。
- **分析**：单元格以 `=` 开头，包含 `HYPERLINK` 公式。若该 CSV 被 Excel/LibreOffice/WPS 打开且未启用公式保护，公式会被执行，可能导致：(1) 自动跳转外部域名（信息泄露 / 钓鱼）；(2) 配合 `DDE` 或 `WEBSERVICE` 等函数可执行更复杂动作。这是典型的 **CSV Injection / Formula Injection** 漏洞（CWE-1236）。
- **分级**：高危（High）——取决于下游消费方式；若仅程序读取不触发公式则风险降低，但只要存在人工用表格软件打开的可能即高危。
- **修复建议**：
  1. 输出 CSV 时对以 `=`、`+`、`-`、`@` 开头的单元格前置单引号 `'` 或制表符，使其被当作纯文本。
  2. 在数据入口对 `value` 字段做公式字符校验与转义。
  3. 安全意识：告知下游用户不要直接用 Excel 打开来源不可信的 CSV。
- **复测方法**：用包含 `=HYPERLINK(...)` 的测试记录走完整采集→导出→Excel 打开链路，确认公式未被执行（显示为纯文本或被转义）。

---

## 6. 风险分级汇总

| 级别 | 数量 | 事件 |
|---|---|---|
| 严重 Critical | 1 | unexpected_export（db，疑似数据外泄，与 token_scope_mismatch 同源 IP 关联） |
| 高危 High | 2 | token_scope_mismatch（api 越权）；CSV 公式注入（edge_cases record_id=5） |
| 中危 Medium | 2 | admin 连续登录失败（暴力破解前兆）；异常负值 -999（数据可信度） |
| 低危 Low | 2 | 完全重复记录（record_id=2）；字段缺失（record_id=3） |
| 数据质量 | 1 | malformed_record 缺字段（incident_log 第 7 行） |
| 正常 | 2 | login_success（alice）；edge_cases record_id=1 |

---

## 7. 修复建议汇总（按优先级）

1. **立即（P0）**：隔离/封禁源 IP `203.0.113.8`（模拟环境记为 IOC）；轮换 `service-a` 令牌并收敛 scope；核查 09:07:30 数据库导出的实际数据范围与目标。
2. **短期（P1）**：对 `admin` 等特权账号启用登录限速与 MFA；在 API 网关实时拦截 scope mismatch；数据库导出强制身份认证与审批；CSV 输出层加公式注入转义。
3. **中期（P2）**：建立"同源 IP 多系统高危事件关联"告警规则；日志采集端增加字段校验与死信队列；`edge_cases` 表对 `record_id` 加唯一约束、对 `value` 加值域校验。
4. **长期（P3）**：统一日志 schema 与必填字段规范；建立 CSV/导出文件的安全编码基线；定期对日志数据做完整性审计。

---

## 8. 复测清单

| 编号 | 复测项 | 方法 | 通过标准 |
|---|---|---|---|
| R1 | 越权令牌拦截 | 用旧 scope 令牌调用越权 API | 返回 403，旧令牌失效，产生告警 |
| R2 | 数据库导出身份强制 | 以 `unknown`/未认证主体发起导出 | 请求被拒绝，记录审计日志 |
| R3 | 同源 IP 关联告警 | 模拟同一 IP 先 token_scope_mismatch 后 unexpected_export | 关联告警触发，包含时间线 |
| R4 | 登录限速 | 同一 IP 对 admin 连续失败登录 | 达阈值后锁定/验证码，产生告警 |
| R5 | CSV 公式注入转义 | 导出含 `=HYPERLINK(...)` 的记录后用 Excel 打开 | 公式不执行，显示为纯文本 |
| R6 | 重复记录幂等 | 重复投递 record_id=2 | 库中仅一条 |
| R7 | 缺失字段处理 | 注入缺 status/value 的记录 | 被标记或入死信队列，不静默入库 |
| R8 | 异常值拦截 | 注入 value=-999 | 被值域校验拦截或入错误队列 |
| R9 | 畸形记录处理 | 注入缺 severity/user/source_ip 的日志 | 入死信队列并告警 |

---

## 9. 阻断与降级说明

### 9.1 未完成项及原因

| 未完成项 | 阻断原因 | 降级方案 | 复测方法 |
|---|---|---|---|
| 按 js-reverse 五阶段工作流执行 | Skill 适用范围不匹配（无前端 JS 目标）；`js-reverse_*` MCP 工具在本环境不可用；`tool-index.md`、`precedent-reverse.md`、bootstrap 脚本均缺失 | 以 Skill 的 Evidence-first 原则指导静态 CSV 取证 | 在具备 js-reverse MCP 工具且目标为前端 JS 的环境中，重新按 Observe→Capture→Rebuild→Patch→DeepDive 执行 |
| 运行时采样 / 断点取证 | 无目标页面、无浏览器环境、无 jshookmcp | 基于原始日志字节做字段级静态分析 | 提供目标页面 URL 与 MCP 工具后复测 |
| 真实攻击源 IP 溯源 | 所有 IP 均为 RFC 5737 文档保留段（模拟数据） | 仅做日志内关联分析，不做外部威胁情报查询 | 提供真实 IP 后可补充威胁情报 |
| 数据库导出实际数据范围核查 | 无数据库访问权限、无导出目标地址字段 | 标记为待核查项，给出核查方向 | 在授权环境接入数据库审计日志后复测 |

### 9.2 未实施的操作（合规声明）

- 未对任何真实系统发起网络请求、端口扫描或登录尝试。
- 未执行 `js-reverse_*` 或 `jshookmcp` 工具（不可用且无目标）。
- 未启动浏览器、未请求用户接管、未做交互式选择。
- 未使用外部凭据、平台数据或未读取的文件内容。
- 所有结论均基于本次随消息上传的两个 CSV 文件的原始字节。

---

## 10. 附录：实际读取的 Skill 文件相对路径

以下文件均已实际读取（相对于 Skill 根目录 `js-reverse/`）：

1. `SKILL.md`
2. `references/ast-deobfuscation.md`
3. `references/automation-entry.md`
4. `references/env-patching.md`
5. `references/fallbacks.md`
6. `references/instrumentation.md`
7. `references/local-rebuild.md`
8. `references/mcp-task-template.md`
9. `references/node-env-rebuild.md`
10. `references/output-contract.md`
11. `references/task-artifacts.md`
12. `references/task-input-template.md`
13. `references/tool-defaults.md`

**SKILL.md 引用但缺失的文件**（未读取，因不存在）：

- `../field-journal/precedent-reverse.md`
- `../tool-index.md`
- `../reverse-engineering/references/nonpe-format-cookbook.md`
- `../skills/SKILL.md`
- `../routing.md`
- `scripts/bootstrap-reverse.ps1`（整个 `scripts/` 目录不存在）

---

*报告结束。本报告仅基于授权范围内的模拟日志生成，不构成对任何真实系统的安全结论。*
