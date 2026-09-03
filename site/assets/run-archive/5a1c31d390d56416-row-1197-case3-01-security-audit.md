# 模拟安全日志审计报告（security-audit.md）

- 审计对象：`incident_log.csv`、`edge_cases.csv`
- 审计范围：仅在授权测试范围内对模拟日志做静态分析，不实施任何破坏性操作
- 生成时间基准：2026-08-26（UTC）
- 审计人：自动化审计（基于上传 Skill 与输入文件）

---

## 1. 执行摘要与结论

本次输入为两份模拟安全日志 CSV，共 12 条数据记录（`incident_log.csv` 6 条、`edge_cases.csv` 6 条）。在不依赖外部平台、不执行破坏性操作的前提下，完成了数据质量校验、事件关联、风险分级与修复建议。

**核心结论：**

1. **存在一条高置信度的疑似横向移动 / 数据外泄链路**：同一来源 IP `203.0.113.8` 在 3 分 28 秒内先后触发 `api/high/token_scope_mismatch`（服务账号 `service-a`）与 `db/critical/unexpected_export`（用户 `unknown`），构成“令牌越权 → 数据库异常导出”的可疑事件链，风险等级 **高**。
2. **存在针对管理员账号的暴力破解信号**：`admin` 账号在 4 秒内从同一 IP `198.51.100.23` 连续登录失败 2 次，虽样本量小但目标为高权限账号，风险等级 **中**。
3. **存在 CSV 公式注入（CSV Injection，CWE-1236）不安全输入**：`edge_cases.csv` 第 6 条 `value` 字段为 `=HYPERLINK("https://example.invalid","do not execute")`，若被导出到 Excel 并执行，可导致数据外泄或命令执行，风险等级 **中**（在本模拟数据中为测试文本，未实际执行）。
4. **数据质量缺陷**：`incident_log.csv` 第 6 条为残缺记录（缺 `severity`/`user`/`source_ip`）；`edge_cases.csv` 存在 1 组完全重复记录（`record_id=2`）、1 条字段缺失记录（`record_id=3`）、1 条异常负值（`record_id=4`，`value=-999`）。这些缺陷影响事件统计的准确性，需在入库前清洗。
5. **所有来源 IP 均属于 RFC 5737 文档保留段**（`192.0.2.0/24`、`198.51.100.0/24`、`203.0.113.0/24`），确认数据为模拟/脱敏数据，不对应真实可路由主机。

---

## 2. Skill 适配性、阻断说明与降级方案

### 2.1 上传 Skill 基本信息

- Skill 名称：`ida-reverse`
- 分类：安全与合规
- Skill 定位（据 `SKILL.md` frontmatter `description`）：IDA Pro 逆向分析辅助，适用于二进制/PE/ELF/APK/DLL/SO 等文件的反编译、漏洞分析、病毒分析、固件分析等。

### 2.2 实际读取的 Skill 文件相对路径（以解压根目录 `ida-skill/` 为基准）

| 相对路径 | 说明 |
|---|---|
| `ida-reverse/SKILL.md` | 主技能文档（工作流、硬门禁、自检清单） |
| `ida-reverse/references/ida-mcp-cheatsheet.md` | 72 个 MCP 工具速查表 |
| `ida-reverse/scripts/start.ps1` | 启动 IDA MCP HTTP 服务器（Windows PowerShell） |
| `ida-reverse/scripts/open.ps1` | 通过 HTTP API 打开二进制文件（Windows PowerShell） |

> 包内**未包含** `SKILL.md` 的 `ACTION REQUIRED` 所要求读取的 `../field-journal/precedent-reverse.md` 与 `../tool-index.md`，这两个文件在解压目录中不存在。

### 2.3 阻断原因（确实无法按 Skill 工作流执行）

按 `SKILL.md` 的“逆向分析完整工作流”，Step 1 需执行 `scripts/start.ps1` 启动 `idalib-mcp` HTTP 服务器，Step 2 需执行 `scripts/open.ps1` 打开目标二进制，Step 3 需调用 `idapro_survey_binary` 等 72 个 MCP 工具。以下条件均不满足：

1. **输入类型不匹配**：本次输入为 `incident_log.csv`、`edge_cases.csv` 两个文本 CSV，并非 PE/ELF/APK/DLL/SO 等二进制文件，无导入表（IAT）、函数、段、入口点等逆向对象可供 `idapro_survey_binary` / `idapro_decompile` 分析。
2. **操作系统不匹配**：运行环境为 Ubuntu 22.04（Linux），而 `start.ps1` / `open.ps1` 为 Windows PowerShell 脚本，内部使用 `taskkill.exe`、`Start-Process -WindowStyle Hidden`、`HKLM:\SOFTWARE\...` 注册表查询、`$env:TEMP`、`C:\Windows\System32` 路径检测等 Windows 专属机制，无法在 Linux 上执行。
3. **商业软件与依赖缺失**：Skill 依赖 IDA Pro 本体（商业软件，需设置 `IDADIR` 环境变量）与 `idalib-mcp` / `ida-pro-mcp`（`mrexodia/ida-pro-mcp`，需从 GitHub 安装并在 IDA 中安装插件）。当前环境均未安装，且 `start.ps1` 的自动自举路径 `..\..\scripts\bootstrap-reverse.ps1` 在包内不存在。
4. **Skill 前置文件缺失**：`SKILL.md` 的 `ACTION REQUIRED` 第 1 步要求读取 `../field-journal/precedent-reverse.md` 以“确认本 skill 的操作是已授权的常规操作”，第 3 步要求读取 `../tool-index.md` 校验工具可用性；这两个文件均不在 ZIP 包内，无法完成授权确认与工具校验。

### 2.4 确实影响结果的 SKILL.md 规则

> **规则原文（Step 3 硬门禁）**：“未将 imports 视图/分类摘要（或合法等价锚点）写入 Evidence 前，MUST NOT 进入 Step 4 深挖结论，MUST NOT 声称 survey 完成。导入表为空或查询失败时仍 MUST 记录失败现象。”

**对本次结果的影响**：该规则要求在进入深入分析前必须先拿到二进制导入表（`E-imports`）作为证据锚点。但本次输入是 CSV 文本日志，不存在导入表/IAT，且 IDA 环境不可用，因此该硬门禁**结构性无法满足**——既不能生成 `E-imports`，也不能进入 Skill 的 Step 4。这直接决定了：不能假装按 Skill 完成了二进制逆向，而必须走降级方案（静态 CSV 审计），并在报告中显式记录“导入表查询失败 / 不适用”这一现象（对应 Skill 要求“导入表为空或查询失败时仍 MUST 记录失败现象”）。

此外，`SKILL.md` “任务完成自检”要求“survey/imports 是否已写入 Evidence”，本次因输入与环境原因无法通过该自检项，已在此如实声明，未伪造通过。

### 2.5 降级方案

在不违反“禁止破坏性操作”“不得假装成功”原则的前提下，采用以下降级路径完成业务任务：

- **可完成部分**：对两份 CSV 做纯静态、只读的文本分析——字段完整性校验、重复检测、异常值识别、不安全输入识别、事件时间线关联、风险分级、修复建议、复测清单。这部分不依赖 IDA Pro、不执行任何公式或脚本、不触碰外部系统。
- **不可完成部分**：Skill 规定的二进制逆向工作流（启动 MCP 服务器、打开二进制、survey imports、反编译、交叉引用、patch 等）全部不可执行，已在第 2.3 节列出阻断原因。
- **复测方法**：若后续提供（a）真实二进制样本、（b）Windows + IDA Pro + `idalib-mcp` 环境、（c）缺失的 `precedent-reverse.md` 与 `tool-index.md`，则可按 `SKILL.md` 工作流 Step 1→Step 7 重新执行并生成 `report.md`。

---

## 3. 输入文件与数据质量检查

### 3.1 `incident_log.csv`

- 表头：`timestamp,system,severity,event,user,source_ip`
- 数据行数：6
- 时间范围：2026-08-12T09:00:12Z ~ 2026-08-12T09:09:00Z（约 9 分钟窗口）

| 行号 | timestamp | system | severity | event | user | source_ip | 数据质量判定 |
|---|---|---|---|---|---|---|---|
| 1 | 2026-08-12T09:00:12Z | web | info | login_success | alice | 192.0.2.10 | 正常 |
| 2 | 2026-08-12T09:03:45Z | web | warning | login_failed | admin | 198.51.100.23 | 正常（事件可疑） |
| 3 | 2026-08-12T09:03:49Z | web | warning | login_failed | admin | 198.51.100.23 | 正常（事件可疑，与行 2 构成暴破信号） |
| 4 | 2026-08-12T09:04:02Z | api | high | token_scope_mismatch | service-a | 203.0.113.8 | 正常（事件高危） |
| 5 | 2026-08-12T09:07:30Z | db | critical | unexpected_export | unknown | 203.0.113.8 | 正常（事件严重；`user=unknown` 身份缺失） |
| 6 | 2026-08-12T09:09:00Z | web | （空） | malformed_record | （空） | （空） | **残缺记录**：缺 `severity`/`user`/`source_ip`，无法完整定级 |

**数据质量问题汇总：**

- **缺失**：第 6 行 `severity`、`user`、`source_ip` 三字段为空，且 `event=malformed_record` 自证为畸形记录。
- **重复**：无完全重复行；但第 2、3 行除 `timestamp` 外其余字段完全相同（4 秒间隔），属事件重复模式而非数据重复。
- **异常**：第 5 行 `user=unknown`，身份归因失败；所有 `source_ip` 均为 RFC 5737 文档保留段，非真实可路由地址（符合模拟数据预期）。
- **不安全输入**：本文件未发现公式注入或命令注入载荷。

### 3.2 `edge_cases.csv`

- 表头：`record_id,status,value,notes`
- 数据行数：6

| 行号 | record_id | status | value | notes | 数据质量判定 |
|---|---|---|---|---|---|
| 1 | 1 | ok | 120 | 正常记录 | 正常 |
| 2 | 2 | ok | 120 | 重复记录 | 正常（与行 3 完全重复） |
| 3 | 2 | ok | 120 | 重复记录 | **完全重复**：与行 2 逐字段相同 |
| 4 | 3 | （空） | （空） | - | **字段缺失**：`status`/`value` 为空，`notes` 为占位符 `-` |
| 5 | 4 | error | -999 | 异常负值 | **异常值**：`value=-999` 为负哨兵值，`status=error` |
| 6 | 5 | ok | `=HYPERLINK("https://example.invalid","do not execute")` | 公式注入测试文本 | **不安全输入**：CSV 公式注入（CWE-1236） |

**数据质量问题汇总：**

- **缺失**：第 4 行（`record_id=3`）`status`、`value` 为空。
- **重复**：第 2、3 行（`record_id=2`）完全重复，需去重保留 1 条。
- **异常**：第 5 行（`record_id=4`）`value=-999`，在以“数值指标”为语义的字段中为异常负哨兵值，且 `status=error` 自证为错误记录。
- **不安全输入**：第 6 行（`record_id=5`）`value` 以 `=` 开头并包含 `HYPERLINK` 公式，属 CSV 公式注入载荷。

---

## 4. 风险分级

采用三级风险：**高 / 中 / 低**。分级依据：事件严重性、权限影响、数据影响、可利用性、证据充分度。

| 风险编号 | 风险描述 | 等级 | 关联证据 |
|---|---|---|---|
| R-01 | 疑似令牌越权后数据库异常导出（`203.0.113.8` 事件链） | **高** | E-01、E-02 |
| R-02 | 针对 `admin` 账号的快速登录失败（暴力破解信号） | **中** | E-03 |
| R-03 | CSV 公式注入不安全输入（`=HYPERLINK(...)`） | **中** | E-04 |
| R-04 | 关键事件身份归因失败（`user=unknown`） | **中** | E-02 |
| R-05 | 日志数据质量缺陷（残缺、重复、异常值） | **低** | E-05、E-06、E-07 |
| R-06 | 来源 IP 均为文档保留段，无法溯源真实主机 | **低**（模拟数据预期内） | E-08 |

---

## 5. 证据

### E-01：API 令牌作用域不匹配（高严重度事件）

- 来源：`incident_log.csv` 第 4 行
- 原文：`2026-08-12T09:04:02Z,api,high,token_scope_mismatch,service-a,203.0.113.8`
- 解读：服务账号 `service-a` 的令牌被用于超出其授权作用域的 API 调用，`severity=high`。这通常意味着令牌被滥用、泄露或权限配置错误。
- 关联：与 E-02 共享来源 IP `203.0.113.8`，时间间隔 3 分 28 秒。

### E-02：数据库异常导出（严重事件，身份未知）

- 来源：`incident_log.csv` 第 5 行
- 原文：`2026-08-12T09:07:30Z,db,critical,unexpected_export,unknown,203.0.113.8`
- 解读：数据库发生未预期的导出操作，`severity=critical`，执行用户为 `unknown`（身份归因失败），来源 IP 与 E-01 相同。
- 推断：结合 E-01，可能为“`service-a` 令牌越权获取数据库访问能力 → 以未归因身份执行数据导出”的疑似数据外泄链路。
- 注意：`user=unknown` 意味着无法直接归责，需结合数据库审计日志、API 网关日志、令牌签发记录做二次关联。

### E-03：管理员账号快速登录失败（暴力破解信号）

- 来源：`incident_log.csv` 第 2、3 行
- 原文：
  - `2026-08-12T09:03:45Z,web,warning,login_failed,admin,198.51.100.23`
  - `2026-08-12T09:03:49Z,web,warning,login_failed,admin,198.51.100.23`
- 解读：同一 IP 在 4 秒内对 `admin` 账号连续登录失败 2 次。虽绝对次数少，但目标为高权限管理员账号，且间隔极短，符合自动化暴力破解/凭证填充的早期特征。
- 局限：仅 2 次失败，低于常见暴破阈值（如 5 次/分钟），需结合更长时间窗口的日志确认是否为持续攻击。

### E-04：CSV 公式注入载荷（不安全输入）

- 来源：`edge_cases.csv` 第 6 行
- 原文（`value` 字段）：`=HYPERLINK("https://example.invalid","do not execute")`
- 解读：字段以 `=` 开头，包含 Excel `HYPERLINK` 公式。若该 CSV 被导出到 Excel/Calc 且公式被执行，`HYPERLINK` 可诱导用户点击访问恶意 URL；更危险的载荷（如 `=CMD|' /c calc'!A1`、`=WEBSERVICE(...)`）可导致命令执行或数据外泄。本字段 `notes` 已标注“公式注入测试文本”，确认为测试用例而非真实攻击，但暴露了输入未做公式字符净化的缺陷。
- 参考：CWE-1236（CSV Injection，也称 Formula Injection）。

### E-05：残缺日志记录

- 来源：`incident_log.csv` 第 6 行
- 原文：`2026-08-12T09:09:00Z,web,,malformed_record,,`
- 解读：`severity`、`user`、`source_ip` 为空，`event=malformed_record`。该记录无法参与风险定级与事件关联，若被统计系统计入分母会稀释告警率，若被计入分子会产生空指针/解析错误。

### E-06：完全重复记录

- 来源：`edge_cases.csv` 第 2、3 行
- 原文：两行均为 `2,ok,120,重复记录`
- 解读：`record_id=2` 出现两次且逐字段相同，属数据重复。若不去重，会导致统计指标（如计数、求和）翻倍失真。

### E-07：异常负哨兵值

- 来源：`edge_cases.csv` 第 5 行
- 原文：`4,error,-999,异常负值`
- 解读：`value=-999`，`status=error`。在数值型指标字段中，负值（尤其 -999 这类约定俗成的错误哨兵）通常表示上游采集失败或无效读数。若未过滤，会拉低均值、触发异常下限告警或被误判为真实业务指标。

### E-08：来源 IP 均为 RFC 5737 文档保留段

- 涉及 IP：`192.0.2.10`（TEST-NET-1）、`198.51.100.23`（TEST-NET-2）、`203.0.113.8`（TEST-NET-3）
- 解读：这三个 /24 段由 RFC 5737 保留用于文档与示例，不可在公网路由。确认本次日志为模拟/脱敏数据，无法据此溯源真实攻击主机。在真实环境中应替换为真实源 IP 并结合威胁情报做信誉判定。

---

## 6. 修复建议

### 6.1 针对 R-01（疑似令牌越权 + 数据外泄，高）

1. **立即冻结/轮换 `service-a` 服务账号令牌**，核查该令牌在 2026-08-12 09:00–09:10 时间窗内的所有 API 调用与数据库访问记录。
2. **核查数据库导出操作**：定位 `unexpected_export` 的具体导出对象（表/库）、导出量、目标存储位置，确认是否有数据实际外泄。
3. **收紧令牌作用域**：按最小权限原则重新签发 `service-a` 令牌，移除其不应具备的数据库导出权限；启用令牌作用域校验的强制拒绝模式（fail-closed）。
4. **补强身份归因**：在数据库审计日志中关联 API 网关的 `X-Forwarded-For`、令牌 subject、会话 ID，消除 `user=unknown`。
5. **建立异常导出基线告警**：对非工作时段、非白名单 IP、超大批量导出设置实时告警。

### 6.2 针对 R-02（管理员暴破信号，中）

1. **对 `admin` 账号启用强制 MFA**，并限制管理员账号仅能从堡垒机/白名单 IP 登录。
2. **配置登录失败限流与锁定**：如 5 分钟内失败 5 次则临时锁定账号 15 分钟，并触发告警。
3. **核查 `198.51.100.23`（模拟环境中为该标识）在更长时间窗口的登录行为**，确认是否为持续暴破或凭证填充。
4. **禁用或重命名默认 `admin` 账号**，使用个体化管理员账号以提升可归因性。

### 6.3 针对 R-03（CSV 公式注入，中）

1. **输入净化**：在 CSV 导出/生成环节，对所有以 `=`、`+`、`-`、`@` 开头的单元格值前置单引号 `'`（Excel 文本前缀），或剥离公式触发字符。
2. **输出侧提示**：在 CSV 文件首行或随附说明中警示“勿在启用宏/公式的电子表格中直接打开”。
3. **采用安全导出格式**：对含用户输入的报表优先使用 `.xlsx` 并设置单元格格式为“文本”，或使用 JSON/Parquet 等不含公式执行语义的格式。
4. **WAF/输入校验**：在数据采集入口对公式特征字符做检测与告警。

### 6.4 针对 R-04（身份归因失败，中）

1. 在所有涉及数据操作的日志中强制写入 `actor_id`（令牌 subject / 用户 ID），不允许 `unknown` 落库。
2. 对无法归因的操作设置 `fail-closed`：未携带有效身份的请求直接拒绝。

### 6.5 针对 R-05（数据质量缺陷，低）

1. **入库前校验**：对 `incident_log.csv` 类日志做非空校验（`severity`/`user`/`source_ip` 必填），畸形记录写入死信队列（DLQ）而非主表。
2. **去重**：对 `edge_cases.csv` 类数据按主键（`record_id`）或全字段哈希去重。
3. **异常值过滤**：对 `value` 字段设置合理上下界，`-999` 等哨兵值映射为 `null` 并记录 `status=error`。
4. **数据质量监控**：每日统计残缺率、重复率、异常值率，超过阈值告警。

### 6.6 针对 R-06（IP 无法溯源，低，模拟数据预期内）

1. 真实环境中使用真实源 IP，并结合威胁情报（IP 信誉、地理位置、ASN）做自动判定。
2. 对模拟/脱敏数据保留 IP 段标识，避免被误接入真实风控规则。

---

## 7. 复测清单

以下为修复后需逐项验证的复测用例（均为只读/非破坏性验证）：

| 编号 | 复测项 | 预期结果 | 验证方法 |
|---|---|---|---|
| RT-01 | `service-a` 令牌作用域已收紧 | 使用旧令牌调用超出作用域的 API 返回 403 | 在测试环境用旧令牌重放 E-01 同类请求 |
| RT-02 | 异常导出告警生效 | 非白名单 IP 触发导出时产生实时告警 | 模拟一次 `unexpected_export`，确认告警通道收到 |
| RT-03 | 身份归因完整 | 数据库审计日志中 `actor_id` 非空 | 抽查修复后 100 条数据库操作日志 |
| RT-04 | 管理员登录限流 | 5 分钟内失败 5 次后账号锁定 | 用测试账号在测试环境连续失败登录 |
| RT-05 | 管理员 MFA 强制 | 未通过 MFA 无法登录管理员界面 | 尝试仅用密码登录管理员账号 |
| RT-06 | CSV 公式注入已净化 | 导出的 CSV 中 `=HYPERLINK(...)` 被前置 `'` 或剥离 | 重新导出含公式载荷的报表，用文本编辑器检查首字符 |
| RT-07 | 残缺记录进 DLQ | `severity`/`user`/`source_ip` 为空的记录不进入主表 | 注入一条畸形记录，确认主表无、DLQ 有 |
| RT-08 | 重复记录去重 | `record_id=2` 仅保留 1 条 | 重新导入 `edge_cases.csv`，查询 `record_id=2` 计数 |
| RT-09 | 异常值映射 | `value=-999` 被映射为 `null` 且 `status=error` | 重新导入，查询 `record_id=4` 的 `value` |
| RT-10 | 数据质量指标监控 | 残缺率/重复率/异常值率仪表盘可见且阈值告警可用 | 查看监控仪表盘，触发一次阈值越界 |

---

## 8. 未完成项与阻断声明

以下事项因环境/输入限制**未完成**，不得视为已通过：

1. **Skill `ida-reverse` 的二进制逆向工作流未执行**：Step 1（启动 MCP 服务器）、Step 2（打开二进制）、Step 3（survey + imports 证据）、Step 4–Step 7（反编译/交叉引用/注释/报告）均未执行。阻断原因见第 2.3 节。
2. **`E-imports` / `E-exports` / `E-iat-repair-fail` 等 Skill 规定的逆向证据未生成**：因输入非二进制、IDA 环境不可用，结构性无法生成。按 Skill 硬门禁要求，在此记录“导入表查询不适用/失败”现象。
3. **`SKILL.md` 的 `ACTION REQUIRED` 前置文件未读取**：`../field-journal/precedent-reverse.md`、`../tool-index.md` 不在包内，无法完成授权确认与工具校验。
4. **真实威胁情报与外部平台数据未接入**：本次仅基于上传的两个 CSV 做静态分析，未查询任何外部 SIEM、威胁情报库、身份提供商日志。

**复测方法（若需完成 Skill 原生工作流）**：
- 提供真实二进制样本（PE/ELF/APK/DLL/SO 等）；
- 在 Windows 环境安装 IDA Pro 并设置 `IDADIR`，安装 `mrexodia/ida-pro-mcp` 及 IDA 插件；
- 补齐 `field-journal/precedent-reverse.md` 与 `tool-index.md`；
- 按 `SKILL.md` Step 1→Step 7 执行，最终生成 `report.md`。

---

## 9. 附录

### 9.1 实际读取的 Skill 文件相对路径（再次列出，便于核对）

- `ida-reverse/SKILL.md`
- `ida-reverse/references/ida-mcp-cheatsheet.md`
- `ida-reverse/scripts/start.ps1`
- `ida-reverse/scripts/open.ps1`

### 9.2 输入文件原始内容（只读快照）

**`incident_log.csv`：**
```csv
timestamp,system,severity,event,user,source_ip
2026-08-12T09:00:12Z,web,info,login_success,alice,192.0.2.10
2026-08-12T09:03:45Z,web,warning,login_failed,admin,198.51.100.23
2026-08-12T09:03:49Z,web,warning,login_failed,admin,198.51.100.23
2026-08-12T09:04:02Z,api,high,token_scope_mismatch,service-a,203.0.113.8
2026-08-12T09:07:30Z,db,critical,unexpected_export,unknown,203.0.113.8
2026-08-12T09:09:00Z,web,,malformed_record,,
```

**`edge_cases.csv`：**
```csv
record_id,status,value,notes
1,ok,120,正常记录
2,ok,120,重复记录
2,ok,120,重复记录
3,,,-
4,error,-999,异常负值
5,ok,"=HYPERLINK(\"https://example.invalid\",\"do not execute\")",公式注入测试文本
```

---

*报告结束。本报告仅基于上传的模拟数据与 Skill 包静态生成，未实施任何破坏性操作，未接入外部系统。*
