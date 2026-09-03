# 安全审计报告：模拟安全日志分析

- 报告日期：2026-08-13（UTC+8）
- 分析范围：授权测试范围内的模拟日志 `incident_log.csv`、`edge_cases.csv`
- 适用 Skill：`competition-ad-certificate-abuse`（AD CS 证书滥用分析）
- 分析原则：仅基于实际读取的文件内容下结论；无证据不推断、不编造；不实施任何破坏性操作

---

## 1. 执行摘要

本次对两份模拟日志共 12 条记录完成了离线分析，识别出 **1 条严重风险链、3 条中危、3 条低危、1 条信息**，并发现 4 类数据质量问题（缺失、重复、异常值、非标准转义）。

最关键发现：同一来源地址 `203.0.113.8` 在 3 分 28 秒内先后触发 **high 级令牌范围不匹配（service-a）** 与 **critical 级未知身份数据导出（unknown）**，构成"令牌异常 → 未识别身份导出数据"的疑似攻击链，需优先核查。

需要特别说明：本次输入数据**不包含任何 AD CS / 证书相关字段**，且 Skill 要求的前置编排器 `$ctf-sandbox-orchestrator` 未激活，因此 Skill 的 AD CS 证书滥用专项工作流**无法执行**（详见第 5 节）。本报告为通用安全日志审计结果，未断言任何证书滥用结论。

---

## 2. Skill 适用性与前置条件检查

依据实际读取的 `SKILL.md`：

- SKILL.md 第 8 行明确规定："Use this skill only as a downstream specialization after `$ctf-sandbox-orchestrator` is already active and has established sandbox assumptions, node ownership, and evidence priorities. If that has not happened yet, return to `$ctf-sandbox-orchestrator` first."
- 当前会话中不存在 `$ctf-sandbox-orchestrator` 上下文，未建立沙箱假设、节点归属与证据优先级。
- 输入文件 `incident_log.csv`、`edge_cases.csv` 中**不存在** CA 名称、证书模板、EKU、SAN、注册权限（enrollment rights）、PKINIT、证书序列号/指纹、Schannel/LDAPS/WinRM 证书映射等任何 AD CS 字段。

**结论**：Skill 的 AD CS 专项分析工作流因前置条件不满足且必要输入缺失而**阻断**。按 Skill 证据纪律（`references/ad-certificate-abuse.md` "Common Pitfalls"：不得在未证明证书签发与接受路径的情况下断言证书滥用），本报告不虚构任何证书模板、签发记录或权限提升链。可完成的通用日志审计在第 3、4 节给出。

---

## 3. 数据质量与输入安全问题

### 3.1 incident_log.csv

| 行 | 问题类型 | 字段 | 说明 |
|---|---|---|---|
| 第 7 行 | 缺失字段 | severity、user、source_ip | 事件 `malformed_record`（09:09:00）三个关键字段为空，无法定位来源与主体 |

- 全表 6 行，无完全重复行；时间戳均唯一。
- 来源 IP 均属 RFC 5737 文档保留段（`192.0.2.x`/`198.51.100.x`/`203.0.113.x`），与"模拟日志"性质一致。

### 3.2 edge_cases.csv

| record_id | 问题类型 | 说明 |
|---|---|---|
| 2 | 重复记录 | 整行重复 1 次（共 2 条完全相同），主键 record_id 重复 |
| 3 | 缺失字段 | status、value 为空，notes 为 `-` |
| 4 | 异常值 | status=error，value=-999（负数哨兵值混入数值列） |
| 5 | 不安全输入（公式注入） | value 以 `=` 开头：`=HYPERLINK("https://example.invalid","do not execute")`，属 CWE-1236 CSV 公式注入模式；`example.invalid` 为 RFC 2606 保留测试域名，当前为测试载荷 |
| 5 | 非标准 CSV 转义 | 该字段使用反斜杠转义引号（`\"`），不符合 RFC 4180 标准（标准为双写引号 `""`），导致标准 CSV 解析器将其拆为多列（实测 Python csv 模块把"公式注入测试文本"挤入额外字段） |

---

## 4. 安全事件分析与风险分级

### F-01【严重】疑似令牌滥用导致数据外传链

- **证据**：
  - `2026-08-12T09:04:02Z`，api 系统，high，`token_scope_mismatch`，主体 `service-a`，来源 `203.0.113.8`
  - `2026-08-12T09:07:30Z`，db 系统，critical，`unexpected_export`，主体 `unknown`，来源 `203.0.113.8`
- **分析**：同一来源地址、间隔 3 分 28 秒、严重度由 high 升至 critical，主体从服务账号变为未识别身份，事件类型从"令牌范围异常"递进为"非预期数据导出"，构成可疑攻击链。
- **证据边界**：当前仅为日志相关性推断，**非直接取证**。缺少令牌内容/作用域变更记录、数据库会话与导出目标、网络流量、数据量等，无法确认外传是否成功及影响范围。
- **影响主体**：`service-a` 服务账号、db 系统数据。

### F-02【中】admin 账户短时登录失败

- **证据**：`198.51.100.23` 在 `09:03:45Z` 与 `09:03:49Z`（间隔 4 秒）对 `admin` 两次 `login_failed`。
- **分析**：次数少（2 次），未达典型暴力破解阈值，但针对管理员账户，可能是口令喷洒/撞库前兆，需结合后续日志判断。

### F-03【中】日志记录畸形，完整性存疑

- **证据**：`09:09:00Z` web 系统 `malformed_record`，severity/user/source_ip 全部为空。
- **分析**：可能是日志采集管道解析失败，也可能是日志被截断/篡改。仅凭该文件无法区分，需比对原始日志与采集链路。

### F-04【中】CSV 公式注入不安全输入

- **证据**：edge_cases record_id=5 的 value 字段以 `=` 开头，含 `HYPERLINK` 公式。
- **分析**：若该文件被 Excel/WPS 等电子表格直接打开，公式可能被解释执行，诱导点击外链（CWE-1236）。当前域名为保留测试域名，属测试载荷，但输入处理模式不安全；且非标准转义会导致下游解析错位。

### F-05【低】重复记录

- **证据**：edge_cases record_id=2 整行重复 1 次。
- **影响**：计数、求和、均值等聚合指标失真。

### F-06【低】关键字段缺失

- **证据**：edge_cases record_id=3 status/value 为空；incident_log 第 7 行 severity/user/source_ip 为空。
- **影响**：缺失行无法参与分级与关联分析，可能漏报。

### F-07【低】异常负值

- **证据**：edge_cases record_id=4 value=-999，status=error。
- **分析**：-999 常作错误哨兵值，但混入数值列会污染统计；错误状态应由 status 字段独立表达。

### F-08【信息】基线正常事件

- `2026-08-12T09:00:12Z` web 系统 info 级 `login_success`，用户 `alice`，来源 `192.0.2.10`，作为正常基线记录。

---

## 5. AD CS 证书滥用专项分析（阻断说明）

按 Skill 工作流（Map CA And Template Trust → Prove Cert-To-Privilege Acceptance → Reduce To The Decisive Abuse Chain）逐项核对：

| Skill 要求的证据要素 | 输入中是否存在 |
|---|---|
| CA 配置、颁发策略、注册权限、管理器批准、授权签名 | 否 |
| 模板名称、标志、EKU、主题/SAN 控制、注册代理 | 否 |
| 已签发证书（序列号、主题、SAN、有效期、颁发者、指纹） | 否 |
| PKINIT/智能卡登录/Schannel/LDAPS/WinRM 证书映射接受路径 | 否 |
| 注册权/配置错误 → 签发证书 → 接受映射 → 获得权限的最小链 | 无法重建 |

**阻断原因**：
1. 前置编排器 `$ctf-sandbox-orchestrator` 未激活（SKILL.md 第 8 行硬性前置条件）；
2. 必要输入缺失：两份 CSV 无任何 AD CS 相关字段；
3. 无 AD 环境、无凭据、无网络访问权限，无法主动采集。

**依据的 Skill 证据纪律**：`references/ad-certificate-abuse.md` "Common Pitfalls" 指出"仅停留在模板配置错误而不证明证书签发"和"证明签发却不证明证书在何处被接受"均属错误做法。因此在无证书签发与接受证据时，不得断言证书滥用结论。

**降级方案**：已完成通用日志审计（第 3、4 节）。若需 AD CS 专项分析，需在 `$ctf-sandbox-orchestrator` 建立沙箱假设后，补充 CA 配置导出、模板 ACL、已签发证书记录、PKINIT/映射日志等输入。

---

## 6. 修复建议

| 编号 | 级别 | 建议 |
|---|---|---|
| F-01 | 严重 | 立即轮换 `service-a` 凭据/令牌；核查 `203.0.113.8` 在 09:04–09:10 的完整会话与 db 导出记录（对象、数据量、目标地址）；审查 service-a 令牌实际作用域与最小权限；对 unknown 身份的导出操作建立强制阻断与告警 |
| F-02 | 中 | 核查 `198.51.100.23` 后续是否有成功登录或更多失败；为 admin 启用 MFA；配置管理员账户失败登录阈值与锁定/告警策略 |
| F-03 | 中 | 排查 09:09 前后日志采集管道解析错误；对日志加序号/哈希做完整性校验；补采该时段原始日志并比对 |
| F-04 | 中 | 导出/展示 CSV 时对以 `=`、`+`、`-`、`@` 开头的单元格加 `'` 前缀或文本化；修复生成端采用 RFC 4180 标准双写引号转义；对外部输入做公式注入过滤 |
| F-05 | 低 | 对重复数据去重；写入端对 record_id 加唯一约束或幂等键 |
| F-06 | 低 | 对 severity/user/source_ip、status/value 等关键字段设非空校验或显式 `unknown` 枚举；缺失行隔离待补，不直接入分析库 |
| F-07 | 低 | value 列加数值范围校验；错误状态用 status 字段表达，禁止用负数哨兵混入数值列 |

---

## 7. 复测清单

| 编号 | 复测步骤 | 通过标准 |
|---|---|---|
| F-01 | 复查 service-a 令牌轮换后的作用域；重新检索 `203.0.113.8` 全量事件；核对 db 导出审计日志 | 令牌作用域最小化；同 IP 无新异常；导出操作可追溯到认证主体且无 unknown 导出 |
| F-02 | 用同一来源对 admin 发起 2 次以上失败登录后观察告警 | 触发阈值告警并记录来源；admin 已启用 MFA |
| F-03 | 重新采集 09:09 时段日志并校验序号/哈希 | 无缺失/断号；malformed 行可被正确解析或有明确错误原因 |
| F-04 | 将含 `=HYPERLINK(...)` 的记录导出为 CSV 并用 Excel 打开；用标准 csv 解析器读取 | 公式不被执行（显示为文本）；解析器不产生额外列 |
| F-05 | 重复写入 record_id=2 | 写入端拒绝或幂等处理，查询仅返回 1 条 |
| F-06 | 提交缺字段记录 | 校验拦截或自动标记 unknown，不进入分析主库 |
| F-07 | 写入 value=-999 且 status=error | 校验拦截或隔离，不污染数值聚合 |

---

## 8. 实际读取的 Skill 文件（相对路径）

- `competition-ad-certificate-abuse/competition-ad-certificate-abuse/SKILL.md`
- `competition-ad-certificate-abuse/competition-ad-certificate-abuse/references/ad-certificate-abuse.md`
- `competition-ad-certificate-abuse/competition-ad-certificate-abuse/agents/openai.yaml`

## 9. 影响结果的 SKILL.md 规则

SKILL.md 第 8 行的前置条件规则——"仅在 `$ctf-sandbox-orchestrator` 已激活并建立沙箱假设后才能作为下游专项使用，否则应先返回该编排器"——直接决定了本报告的结构：由于该编排器未激活且输入无 AD CS 数据，AD CS 证书滥用专项被判定为**阻断**而非强行执行，避免了在无 CA/模板/证书/映射证据时编造证书滥用结论。这与 `references/ad-certificate-abuse.md` "Common Pitfalls" 的证据链要求（必须同时证明证书签发与接受路径）共同约束了本次分析不得越界下结论。

---

## 10. 输入文件与处理方式

- 输入：`incident_log.csv`（6 行）、`edge_cases.csv`（6 行），均完整读取。
- 处理：本地 Python 标准库 `csv` 离线校验（缺失、重复、异常值、公式注入特征、同 IP 关联），未连接任何外部系统、未使用任何外部凭据、未执行任何破坏性操作。
- 数据性质：来源 IP 均为 RFC 5737 文档保留地址，域名为 RFC 2606 保留域名，确属授权测试范围内的模拟数据。
