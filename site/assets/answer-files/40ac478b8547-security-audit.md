# 安全审计报告：incident_log.csv

- 审计日期：2026-08-13
- 审计范围：仅对随附模拟日志文件 `incident_log.csv` 进行只读分析
- 授权边界：授权测试范围内的日志分析；未执行任何破坏性操作、未访问外部系统、未使用任何凭据
- 分析依据：Skill `competition-queue-worker-drift` 的 SKILL.md（见"Skill 适用性说明"）

---

## 一、Skill 适用性说明（重要前提）

实际读取的 Skill 文件（相对路径）：

1. `competition-queue-worker-drift/SKILL.md`
2. `competition-queue-worker-drift/references/queue-worker-drift.md`
3. `competition-queue-worker-drift/agents/openai.yaml`

**SKILL.md 前置条件未满足，直接影响执行方式：**

- SKILL.md 第 8 行规定："Use this skill only as a downstream specialization after `$ctf-sandbox-orchestrator` is already active and has established sandbox assumptions, node ownership, and evidence priorities. If that has not happened yet, return to `$ctf-sandbox-orchestrator` first."
- 当前环境中 `$ctf-sandbox-orchestrator` 未激活、也不存在该 Skill，无法按 SKILL.md 要求"先返回 orchestrator"。
- 此外，本 Skill 的领域是队列/异步 worker/重试/死信/payload-to-side-effect 链；而 `incident_log.csv` 中不包含任何队列名、worker 进程、重试、延迟任务或异步 payload 事件，字段为 `timestamp,system,severity,event,user,source_ip`，属于通用认证/授权/数据导出类安全日志。
- `agents/openai.yaml` 中 `allow_implicit_invocation: false`，亦表明本 Skill 不应被隐式调用。

**处理方式**：鉴于业务任务明确要求对模拟日志做只读安全分析（无破坏性操作），我在不违反授权边界的前提下完成日志本身的风险分级、证据链、修复建议与复测清单；但上述前置条件缺口属于真实阻断项，已在此明确记录，未假装 Skill 前提已满足。

---

## 二、日志数据概览

文件共 6 条记录（含表头），时间范围 2026-08-12T09:00:12Z 至 09:09:00Z，涉及系统：web、api、db。

| # | 时间 (UTC) | 系统 | 严重级 | 事件 | 用户 | 来源 IP |
|---|------------|------|--------|------|------|---------|
| 1 | 09:00:12 | web | info | login_success | alice | 192.0.2.10 |
| 2 | 09:03:45 | web | warning | login_failed | admin | 198.51.100.23 |
| 3 | 09:03:49 | web | warning | login_failed | admin | 198.51.100.23 |
| 4 | 09:04:02 | api | high | token_scope_mismatch | service-a | 203.0.113.8 |
| 5 | 09:07:30 | db | critical | unexpected_export | unknown | 203.0.113.8 |
| 6 | 09:09:00 | web | （空） | malformed_record | （空） | （空） |

注：来源 IP 均属 RFC 5737 文档保留段（192.0.2.0/24、198.51.100.0/24、203.0.113.0/24），与"模拟日志"性质一致。

---

## 三、风险分级

| 编号 | 风险项 | 等级 | 涉及记录 | 说明 |
|------|--------|------|----------|------|
| R1 | 未授权数据库导出（疑似数据外泄） | **严重 / Critical** | #5 | db 系统出现 `unexpected_export`，用户为 `unknown`，来源 IP 203.0.113.8 |
| R2 | 服务令牌权限范围不匹配（疑似令牌滥用/越权） | **高 / High** | #4 | service-a 令牌发生 `token_scope_mismatch`，来源 IP 同为 203.0.113.8 |
| R3 | admin 账户连续登录失败（疑似暴力破解） | **中 / Medium** | #2、#3 | 4 秒内同一 IP 对 admin 连续两次登录失败 |
| R4 | 日志记录畸形/字段缺失（日志完整性风险） | **低 / Low** | #6 | severity、user、source_ip 均为空，可能为日志管道异常或篡改/注入痕迹 |
| R5 | 正常登录基线 | **信息 / Info** | #1 | alice 正常登录，作为基线对照 |

### 决定性证据链（R1 + R2 关联）

同一来源 IP `203.0.113.8` 在约 3.5 分钟内先后触发：

1. **09:04:02** — api 层 `token_scope_mismatch`（service-a 令牌权限范围不符）；
2. **09:07:30** — db 层 `unexpected_export`（用户标识为 unknown）。

该链表明：一个权限范围异常的服务令牌调用之后，同一来源对数据库发起了未预期的导出操作，且数据库侧无法识别有效用户。这是本次日志中最需要处置的事件链，符合"授权异常 → 数据外泄副作用"的攻击路径特征。

> 方法学参照：SKILL.md 要求将结果压缩为"最小可复现链"（enqueue → worker runtime → retry/branch → side effect）。本日志虽无队列/worker 组件，但我借用同一证据打包原则，将决定性序列还原为：**token_scope_mismatch（203.0.113.8）→ unexpected_export（203.0.113.8）**，并将入端证据（IP、服务身份、时间戳）与副作用端证据（db 导出、unknown 用户、时间戳）保持在同一条链中。

---

## 四、证据清单

| 证据 ID | 来源记录 | 证据内容 | 支撑风险 |
|---------|----------|----------|----------|
| E1 | #4 | `2026-08-12T09:04:02Z,api,high,token_scope_mismatch,service-a,203.0.113.8` | R2 |
| E2 | #5 | `2026-08-12T09:07:30Z,db,critical,unexpected_export,unknown,203.0.113.8` | R1 |
| E3 | #2、#3 | 同一 IP 198.51.100.23 于 09:03:45、09:03:49 连续两次 admin 登录失败 | R3 |
| E4 | #6 | `2026-08-12T09:09:00Z,web,,malformed_record,,` 三字段为空 | R4 |
| E5 | #1 | alice 正常登录基线 | 对照 |
| E6 | E1+E2 | 同 IP 203.0.113.8 跨 api/db 两个系统，时间间隔约 208 秒 | R1+R2 关联链 |

---

## 五、修复建议

### R1 未授权数据库导出（严重）
1. 立即在数据库侧核查 09:07:30 前后导出任务的实际内容、目标位置与数据量级，确认是否构成数据外泄。
2. 临时封禁或限流来源 IP 203.0.113.8，吊销/轮换 service-a 相关令牌。
3. 对数据库导出操作强制二次授权与审批，禁止 `unknown`/匿名身份执行导出。
4. 导出行为增加实时告警（critical 级事件应触发即时通知，而非仅落日志）。

### R2 令牌权限范围不匹配（高）
1. 核查 service-a 令牌的签发范围与实际调用范围，确认是配置漂移还是令牌被盗用。
2. 实施最小权限：为 service-a 收窄 scope，拒绝跨 scope 请求。
3. 令牌绑定来源 IP/服务身份，异常 scope 使用直接拒绝并告警。

### R3 admin 连续登录失败（中）
1. 对 admin 账户启用登录失败锁定/速率限制与 MFA。
2. 对 198.51.100.23 启用临时封禁或验证码挑战。
3. 禁止 admin 账户直接对外暴露登录入口，改用堡垒机/SSO。

### R4 畸形日志记录（低）
1. 校验日志管道：确认 #6 是采集/序列化异常还是伪造/注入。
2. 对日志字段强制 schema 校验，severity/user/source_ip 缺失时拒收并告警。
3. 保证日志写入完整性与防篡改（追加写、访问控制）。

### 通用建议
- 将 api 与 db 日志按 source_ip + 时间窗做自动关联分析，提升同类链式攻击检出率。
- 所有来源 IP 在真实环境中应替换为实际公网 IP 后再做威胁情报比对。

---

## 六、复测清单

| 序号 | 复测项 | 预期结果 | 验证方法 |
|------|--------|----------|----------|
| V1 | 使用超出 scope 的 service-a 令牌请求 api | 请求被拒绝，产生 high 告警，令牌被标记/吊销 | 构造越权令牌调用，观察响应与告警 |
| V2 | 以 unknown/匿名身份触发 db 导出 | 导出被拒绝并产生 critical 告警 | 在测试环境模拟匿名导出 |
| V3 | 同一 IP 连续 admin 登录失败 ≥2 次 | 账户锁定/限速/MFA 挑战生效 | 自动化登录失败尝试 |
| V4 | 提交缺字段的日志记录 | 被 schema 校验拒收并产生管道告警 | 发送畸形日志事件 |
| V5 | 跨 api/db 同 IP 链式事件 | 关联规则在时间窗内自动聚合为一条告警 | 回放 E1→E2 序列验证检测规则 |
| V6 | 正常 alice 登录 | 无告警，记录 info 基线 | 正常登录验证无误报 |

---

## 七、最小可验证版本（MVV）

**目标**：在不访问任何外部系统、不使用凭据的前提下，证明日志中最关键的风险链可被检出。

### 关键步骤
1. 读取并解析 `incident_log.csv`（6 条记录，含表头）。
2. 按 severity 与 event 类型对每条记录分级。
3. 以 `source_ip` 为关联键，跨 `system` 字段在时间窗内关联事件。
4. 输出决定性链：203.0.113.8 的 `token_scope_mismatch` → `unexpected_export`。
5. 形成风险分级表、证据表、修复建议、复测清单（即本报告）。

### 验收标准
- [x] 6 条记录全部被读取并标注，无遗漏、无编造。
- [x] 至少识别出 1 条跨系统关联证据链（R1+R2，同 IP 203.0.113.8）。
- [x] 风险分级覆盖 critical/high/medium/low/info 五级。
- [x] 每条风险均有对应证据记录 ID。
- [x] 修复建议与复测项一一对应。
- [x] 未执行任何破坏性操作，未访问外部系统或使用凭据。
- [x] 如实记录 Skill 前置条件未满足的阻断情况。

---

## 八、阻断与局限

1. **Skill 前置条件阻断**：SKILL.md 要求 `$ctf-sandbox-orchestrator` 先激活，当前不可用；本报告以通用只读日志分析完成业务任务，但未、也无法按该 Skill 的完整队列/worker 工作流执行。
2. **数据局限**：仅 6 条模拟记录，无法确认导出数据内容、量级与去向；来源 IP 为 RFC 5737 文档保留段，不代表真实攻击源。
3. **无队列/worker 事件**：日志不含队列名、payload、worker 进程、重试或死信信息，无法开展 Skill 所定义的异步链追踪。
