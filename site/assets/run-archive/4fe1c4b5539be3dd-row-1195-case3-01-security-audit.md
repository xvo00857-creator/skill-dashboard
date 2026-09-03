# 安全日志审计报告（security-audit.md）

> 生成时间：2026-08-26（UTC）
> 输入文件：`incident_log.csv`、`edge_cases.csv`
> 评测 Skill：`go-rust-reverse`（分类：安全与合规）
> 授权范围：仅对模拟安全日志做静态分析，不实施任何破坏性操作。

---

## 一、Skill 执行状态与适配性说明

### 1.1 实际读取的 Skill 文件

| 相对路径 | 状态 |
|---|---|
| `go-rust-reverse/SKILL.md` | 已读取 |
| `go-rust-reverse/references/go-rust-notes.md` | 已读取 |

### 1.2 按 SKILL.md「ACTION REQUIRED」逐条核对

SKILL.md 首部要求读完后立刻执行以下四步，实际执行结果如下：

| 序号 | SKILL.md 要求 | 实际结果 | 阻断原因 |
|---|---|---|---|
| 1 | `NOW` 读取 `../field-journal/precedent-reverse.md` | **阻断** | 该文件在解压目录中不存在（`/tmp/go-rust-reverse-skill/field-journal/` 不存在） |
| 2 | `NOW` 确认样本为 Go/Rust 编译产物（`file`/字符串/运行时特征） | **阻断** | 输入为两份 CSV 文本日志，无任何二进制可执行样本可供 `file` 或字符串分析 |
| 3 | `NEXT` 确认 GoReSym / 相关插件是否可用 | **阻断** | `GoReSym`、`redress`、`radare2`/`rabin2` 均未安装（`which` 无返回） |
| 4 | `ACT` 运行时识别 → 符号/元数据恢复 → 业务逻辑 | **阻断** | 无前序二进制样本与工具链，无法执行 |

SKILL.md「参考」节还引用了 `../reverse-engineering/go-reverse.md`、`../ida-reverse/`、`../ghidra-reverse/`、`field-journal/seed-002_go-malware-stripped.md`，经核对均不存在于解压产物中。

### 1.3 适配性结论

`go-rust-reverse` 的适用场景是**剥离符号的 Go/Rust 二进制逆向**，而本次业务任务是**模拟安全日志的风险分级与修复建议**，两者领域不匹配。在不编造未读取文件、不伪造工具执行结果的前提下，Skill 的逆向工作流**整体不可执行**。

**降级方案**：业务任务（日志分析）不依赖二进制逆向能力，改用通用静态日志分析方法完成，结果见下文第二至第五节。Skill 相关阻断项列入第六节「阻断项与复测方法」。

### 1.4 确实影响结果的 SKILL.md 规则

> SKILL.md「ACTION REQUIRED」第 1 条强制要求先读取 `../field-journal/precedent-reverse.md` 作为分析前置依据，但该文件实际不存在。这一缺失直接导致无法按 Skill 规定的判例基准进行后续判断，是本次审计中**确实影响执行路径与结果**的规则。若强行假设该文件内容，将违反「不得编造未读取文件」的约束，因此必须降级为通用方法并如实记录。

---

## 二、输入文件校验与边界场景

### 2.1 incident_log.csv

**格式异常**：该文件并非标准 CSV，首行是字面量 `csv`，其后为 Markdown 表格（`| col | col |` 分隔）。解析时需先剥离首行并按 Markdown 表格处理，否则标准 CSV 解析器会把整行当作一个字段。

**记录清单（6 行数据）**：

| # | timestamp | system | severity | event | user | source_ip |
|---|---|---|---|---|---|---|
| 1 | 2026-08-12T09:00:12Z | web | info | login_success | alice | 192.0.2.10 |
| 2 | 2026-08-12T09:03:45Z | web | warning | login_failed | admin | 198.51.100.23 |
| 3 | 2026-08-12T09:03:49Z | web | warning | login_failed | admin | 198.51.100.23 |
| 4 | 2026-08-12T09:04:02Z | api | high | token_scope_mismatch | service-a | 203.0.113.8 |
| 5 | 2026-08-12T09:07:30Z | db | critical | unexpected_export | unknown | 203.0.113.8 |
| 6 | 2026-08-12T09:09:00Z | web | *(空)* | malformed_record | *(空)* | *(空)* |

**边界识别**：
- **重复/模式**：第 2、3 行均为 `admin` 登录失败，来自同一 IP `198.51.100.23`，间隔仅 4 秒 → 暴力破解特征。
- **关联**：第 4 行（api，token_scope_mismatch）与第 5 行（db，unexpected_export）来源 IP 均为 `203.0.113.8`，时间间隔约 3 分 28 秒 → 疑似同一攻击链（权限绕过 → 数据导出）。
- **缺失**：第 6 行 severity、user、source_ip 均为空，event 为 `malformed_record` → 采集管道异常或日志被截断/篡改。
- **异常用户**：第 5 行 user=`unknown`，对 db 执行 unexpected_export → 未认证/匿名导出，高危。

### 2.2 edge_cases.csv

**格式**：标准 CSV，含表头 `record_id,status,value,notes`，共 5 条数据（含 1 条重复，实际唯一 4 条）。

| record_id | status | value | notes | 边界类型 |
|---|---|---|---|---|
| 1 | ok | 120 | 正常记录 | 正常基线 |
| 2 | ok | 120 | 重复记录 | **重复**（出现两次，完全相同） |
| 2 | ok | 120 | 重复记录 | **重复**（同上） |
| 3 | *(空)* | *(空)* | - | **缺失**（status、value 为空） |
| 4 | error | -999 | 异常负值 | **异常值**（负值，与 status=error 一致） |
| 5 | ok | `=HYPERLINK("https://example.invalid","do not execute")` | 公式注入测试文本 | **不安全输入**（CSV 公式注入） |

**边界识别**：
- **重复**：record_id=2 出现两次完全相同的行 → 主键不唯一，去重逻辑缺失。
- **缺失**：record_id=3 的 status 和 value 为空 → 不完整记录。
- **异常**：record_id=4 value=-999 → 负值在多数计量场景下非法，且 status=error 已标记。
- **公式注入**：record_id=5 的 value 以 `=` 开头并包含 `HYPERLINK`，若直接用 Excel/WPS/Google Sheets 打开会触发公式执行，可能导致钓鱼链接跳转或数据外泄 → 典型 CSV 注入（Formula Injection）。

---

## 三、风险分级与证据

### 3.1 风险分级总览

| 风险编号 | 等级 | 来源 | 事件 | 关键证据 |
|---|---|---|---|---|
| R-01 | **严重（Critical）** | incident_log #5 | db 未授权数据导出 | user=unknown，source_ip=203.0.113.8，severity=critical，event=unexpected_export |
| R-02 | **高（High）** | incident_log #4→#5 | 令牌权限越界并关联数据导出 | token_scope_mismatch（service-a, 203.0.113.8）后 3 分 28 秒同 IP 触发 db critical 导出 |
| R-03 | **高（High）** | edge_cases #5 | CSV 公式注入 | value=`=HYPERLINK("https://example.invalid","do not execute")`，以 `=` 开头 |
| R-04 | **中（Medium）** | incident_log #2,#3 | admin 账户暴力破解 | 同一 IP 4 秒内两次 login_failed，目标为高权限 admin |
| R-05 | **中（Medium）** | incident_log #6 | 日志采集异常/可能被篡改 | malformed_record，severity/user/source_ip 全空 |
| R-06 | **低（Low）** | edge_cases #2 | 重复记录 | record_id=2 完全重复两行 |
| R-07 | **低（Low）** | edge_cases #3 | 字段缺失 | record_id=3 status/value 为空 |
| R-08 | **低（Low）** | edge_cases #4 | 异常负值 | record_id=4 value=-999（status=error 已自标记） |

### 3.2 攻击链还原（R-01 + R-02）

```
09:04:02  api   service-a  token_scope_mismatch   203.0.113.8   (权限越界)
   ↓ 3分28秒
09:07:30  db    unknown    unexpected_export      203.0.113.8   (数据导出)
```

同一来源 IP `203.0.113.8` 先在 API 层出现令牌作用域不匹配，随后在数据库层以 unknown 用户执行异常导出。高度疑似：利用越权令牌获取数据库访问能力后执行数据导出。需立即核查该 IP 与 service-a 令牌的关联关系，以及导出数据的范围与去向。

---

## 四、修复建议

### 4.1 严重 / 高风险

| 编号 | 修复建议 | 优先级 |
|---|---|---|
| R-01 | 立即封禁来源 IP `203.0.113.8`；审计数据库导出日志，确认导出数据范围与是否外传；核查 `unknown` 用户是未认证访问还是身份字段丢失 | P0 |
| R-02 | 吊销并轮换 `service-a` 的所有令牌；强制最小权限原则，令牌 scope 与实际 API 一一对应；增加 token_scope_mismatch 事件的实时告警与自动熔断 | P0 |
| R-03 | 在 CSV 导入/导出管道中对以 `=`、`+`、`-`、`@` 开头的单元格值前置单引号 `'` 或转义；禁止将原始用户输入直接写入可被电子表格软件解析的字段 | P1 |

### 4.2 中风险

| 编号 | 修复建议 | 优先级 |
|---|---|---|
| R-04 | 对 `admin` 等特权账户启用登录失败锁定（如 5 次/15 分钟）与速率限制；强制 MFA；对来源 IP `198.51.100.23` 临时封禁并核查 | P1 |
| R-05 | 修复日志采集管道对 malformed_record 的处理：空字段应补默认值或整条丢弃并告警；增加日志完整性校验（如连续 malformed 记录阈值告警），排查是否为日志注入/篡改 | P1 |

### 4.3 低风险 / 数据质量

| 编号 | 修复建议 | 优先级 |
|---|---|---|
| R-06 | 对 `record_id` 建立唯一约束，导入时去重（保留首条或按时间戳最新） | P2 |
| R-07 | 对必填字段（status、value）增加非空校验，不完整记录进入隔离区而非主表 | P2 |
| R-08 | 对 value 字段增加值域校验（如非负），非法值拒绝入库或标记后隔离 | P2 |

### 4.4 输入格式

- `incident_log.csv` 实际为 Markdown 表格而非标准 CSV，建议统一输出为标准 CSV（逗号分隔、RFC 4180），避免下游解析器误判。

---

## 五、复测清单

修复完成后，按以下清单逐项复测，全部通过方可关闭事件：

- [ ] **C-01**：`203.0.113.8` 在防火墙/WAF 中已封禁，从该 IP 发起的请求被拒绝。
- [ ] **C-02**：`service-a` 旧令牌已失效，新令牌 scope 严格限定，越权调用返回 403 并触发告警。
- [ ] **C-03**：数据库导出操作需认证且有审计日志；`unknown` 用户无法执行导出。
- [ ] **C-04**：构造 `=HYPERLINK(...)`、`=CMD(...)`、`+cmd`、`-1+1`、`@SUM(...)` 等 payload 写入 CSV，用 Excel/WPS 打开确认不执行公式（显示为文本或前置 `'`）。
- [ ] **C-05**：`admin` 账户连续失败登录达到阈值后被锁定，MFA 已启用；`198.51.100.23` 已封禁。
- [ ] **C-06**：向日志管道注入 malformed_record（空字段），确认管道要么补全要么丢弃并产生告警，不再出现 severity/user/source_ip 全空的记录。
- [ ] **C-07**：重复导入相同 record_id=2 的记录，确认只保留一条（唯一约束生效）。
- [ ] **C-08**：导入 status/value 为空的记录，确认进入隔离区而非主表。
- [ ] **C-09**：导入 value=-999 等负值，确认被值域校验拒绝或标记隔离。
- [ ] **C-10**：`incident_log.csv` 输出格式已统一为标准 CSV，可用 `csvkit`/Python `csv` 模块无错解析。

---

## 六、阻断项与复测方法（Skill 相关）

以下为按 `go-rust-reverse` SKILL.md 执行时遇到的**真实阻断项**，未编造任何文件内容或执行结果：

| 阻断项 | 缺失条件 | 复测方法 |
|---|---|---|
| 无法读取判例文件 | `../field-journal/precedent-reverse.md` 不存在 | 将该文件放入 Skill 同级 `field-journal/` 目录后重新执行 |
| 无 Go/Rust 二进制样本 | 输入仅为 CSV，无可执行文件 | 提供待分析的 Go/Rust 编译二进制样本（需在授权测试范围内） |
| GoReSym 不可用 | 未安装 | 安装 GoReSym（`go install github.com/mandiant/GoReSym@latest`）后复测 |
| redress / radare2 不可用 | 未安装 | 安装对应工具链后复测 |
| 参考目录缺失 | `reverse-engineering/`、`ida-reverse/`、`ghidra-reverse/` 不存在 | 补齐参考文档目录后复测 |

**结论**：在当前输入与环境下，`go-rust-reverse` Skill 的二进制逆向工作流**无法执行**；业务侧的安全日志分析已通过降级方案（通用静态分析）完整完成，产物即本文件。若后续提供二进制样本与工具链，可另行按 Skill 流程执行逆向分析。
