# 模拟安全日志审计报告（security-audit.md）

> 输入文件：`incident_log.csv`（6 条记录，时间跨度 2026-08-12 09:00:12Z – 09:09:00Z，共 528 秒）
> 评测 Skill：`macos-reverse`（分类：安全与合规）
> 执行原则：仅在授权测试范围内做静态日志分析，不实施任何破坏性操作。

---

## 一、执行摘要与结论

本次输入为一份 **Web/API/DB 混合安全日志（CSV）**，并非 macOS/Mach-O 二进制或 .app bundle。依据 `macos-reverse/SKILL.md` 的「ACTION REQUIRED」第 2 条「确认目标为 macOS/Mach-O/App bundle」，该 Skill 的逆向工作流（`codesign` / `otool` / `class-dump` / `lldb` / `Frida` 等）**不适用于本输入**，故未执行任何 Mach-O 静态或动态分析，也未编造签名、Hardened Runtime、地址级或符号级结论。

在 Skill 适用范围之外，按业务任务对日志本身完成了最小可验证版本的风险分析。核心结论：

- **存在一条疑似横向移动 + 数据外传的攻击链**：`203.0.113.8` 先在 API 层触发 `token_scope_mismatch`（high），3 分 28 秒后在 DB 层以 `unknown` 用户触发 `unexpected_export`（critical），同源 IP 高度关联，判定为 **P0 级数据外泄风险**。
- **存在针对 `admin` 账户的暴力破解尝试**：`198.51.100.23` 在 4 秒内连续两次 `login_failed`，判定为 **P2 级**（量级低但目标为高权限账户）。
- **存在日志完整性问题**：第 6 条 `malformed_record` 的 `severity` / `user` / `source_ip` 均为空，可能为采集异常或日志篡改，需单独排查。
- 正常基线：`alice` 从 `192.0.2.10` 登录成功，暂未发现异常。

总体风险评级：**高（P0 事件未闭环前不可降级）**。

---

## 二、Skill 执行记录（严格按 SKILL.md）

### 2.1 实际读取的 Skill 文件（相对解压根目录）

| 相对路径 | 状态 |
|---|---|
| `macos-reverse/SKILL.md` | 已完整读取 |
| `macos-reverse/references/macho-triage.md` | 已完整读取 |

### 2.2 ACTION REQUIRED 逐条执行情况

| 步骤 | SKILL.md 要求 | 执行结果 |
|---|---|---|
| 1. `NOW` | 读取 `../field-journal/precedent-reverse.md` | **文件不存在**。解压包内无 `field-journal/` 目录，无法读取；按规则不编造其内容。 |
| 2. `NOW` | 确认目标为 macOS/Mach-O/App bundle（iOS IPA → `mobile-reverse/`） | **目标不匹配**。`incident_log.csv` 经 `file` 判定为 `CSV text`，内容为 Web/API/DB 事件日志，非 Mach-O / .app / dylib / framework。 |
| 3. `NEXT` | tool-index；jtool2/lldb 等 | 因步骤 2 不通过，**不进入**工具索引与逆向流程。 |
| 4. `ACT` | 签名与装载信息 → 静态 → 动态（lldb/Frida） | 因目标非 Mach-O，**不执行**。 |

### 2.3 确实影响结果的 SKILL.md 规则

> **「ACTION REQUIRED 第 2 条：确认目标为 macOS/Mach-O/App bundle」**
>
> 该规则直接决定了本报告的方法论边界：因为输入是 CSV 日志而非 Mach-O 二进制，整个逆向工作流（签名校验、`otool -L`、`class-dump`、`lldb`/`Frida` 动态调试）被判定为不适用，报告中**不会**出现任何关于代码签名、Hardened Runtime、entitlements、符号恢复或地址级结论的内容——若强行产出则属于编造。此外，「任务完成自检」中的「是否记录签名/Hardened Runtime 状态」「是否有地址级/符号级结论」两项对本输入天然不适用，已在第八节局限性中如实标注。

第二条影响结果的规则：**ACTION REQUIRED 第 1 条要求读取的 `../field-journal/precedent-reverse.md` 在包内缺失**，导致无法引用该 Skill 预设的先例/判例口径，本报告的风险分级仅基于日志数据本身与通用安全实践，不声称引用了该缺失文件。

---

## 三、数据概览

- 总记录数：6
- 字段：`timestamp, system, severity, event, user, source_ip`
- `severity` 分布：info ×1、warning ×2、high ×1、critical ×1、空 ×1
- `system` 分布：web ×4、api ×1、db ×1
- `source_ip` 分布：`198.51.100.23` ×2、`203.0.113.8` ×2、`192.0.2.10` ×1、空 ×1
- 时间跨度：528 秒（约 8 分 48 秒）

### 原始记录（按时间排序）

| 行 | 时间 (UTC) | system | severity | event | user | source_ip |
|---|---|---|---|---|---|---|
| 1 | 09:00:12 | web | info | login_success | alice | 192.0.2.10 |
| 2 | 09:03:45 | web | warning | login_failed | admin | 198.51.100.23 |
| 3 | 09:03:49 | web | warning | login_failed | admin | 198.51.100.23 |
| 4 | 09:04:02 | api | high | token_scope_mismatch | service-a | 203.0.113.8 |
| 5 | 09:07:30 | db | critical | unexpected_export | unknown | 203.0.113.8 |
| 6 | 09:09:00 | web | (空) | malformed_record | (空) | (空) |

---

## 四、风险分级与证据

### P0 — 严重（Critical）：疑似未授权数据外传

- **事件**：行 5，`2026-08-12T09:07:30Z`，`db` / `critical` / `unexpected_export`，`user=unknown`，`source_ip=203.0.113.8`。
- **证据**：
  - 导出动作发生在数据库层，且用户字段为 `unknown`，表明身份未被正确识别或鉴权被绕过。
  - 同源 IP `203.0.113.8` 在 3 分 28 秒前（行 4）刚触发 API 层 `token_scope_mismatch`，时间与来源高度串联，符合「令牌滥用 → 数据导出」的攻击链特征。
- **影响**：可能导致敏感数据外泄；若涉及个人信息或业务核心数据，触发数据泄露应急流程。
- **处置优先级**：立即遏制。

### P1 — 高（High）：服务令牌越权使用

- **事件**：行 4，`2026-08-12T09:04:02Z`，`api` / `high` / `token_scope_mismatch`，`user=service-a`，`source_ip=203.0.113.8`。
- **证据**：`service-a` 的令牌被用于超出其授权 scope 的操作；来源 IP 与后续 P0 导出事件一致。
- **影响**：令牌可能已泄露或被横向滥用，是 P0 事件的直接前置条件。
- **处置优先级**：与 P0 联动处置，先吊销再排查。

### P2 — 中（Medium）：针对 admin 的暴力破解尝试

- **事件**：行 2、行 3，`09:03:45` 与 `09:03:49`，`web` / `warning` / `login_failed`，`user=admin`，`source_ip=198.51.100.23`。
- **证据**：4 秒内连续两次失败，目标为高权限 `admin` 账户；当前量级尚低，但属于典型爆破起步特征。
- **影响**：若未限速/MFA，存在账户被接管风险。
- **处置优先级**：当日内加固。

### P3 — 低（Low）/ 信息：日志完整性异常

- **事件**：行 6，`09:09:00`，`web` / `malformed_record`，`severity`、`user`、`source_ip` 均为空。
- **证据**：关键字段缺失，无法判定事件真实严重度与来源。
- **影响**：可能是采集/解析故障，也可能是攻击者干扰日志；在攻击时间窗内出现需警惕。
- **处置优先级**：纳入排查，不单独定级但影响取证完整性。

### 基线（无风险）

- 行 1：`alice` 从 `192.0.2.10` 登录成功，时间与行为正常，作为对照基线。建议后续核对该会话是否被劫持（当前无证据）。

---

## 五、攻击链分析

```
09:03:45  198.51.100.23  admin login_failed  ──┐  (独立/疑似声东击西)
09:03:49  198.51.100.23  admin login_failed  ──┘
09:04:02  203.0.113.8    service-a token_scope_mismatch  ← 令牌越权 (P1)
                  │
                  │  3分28秒
                  ▼
09:07:30  203.0.113.8    unknown unexpected_export (db)  ← 数据外传 (P0)
09:09:00  (空)           malformed_record                ← 日志异常 (P3)
```

- **核心链**：`203.0.113.8` 从 API 令牌越权到 DB 未授权导出，是本次最需关注的链路。
- **旁支**：`198.51.100.23` 的 admin 爆破与主链无 IP 关联，可能是独立扫描，也可能是分散注意力的协同动作，需结合更宽时间窗日志确认。
- **日志异常**：`malformed_record` 出现在攻击链末端，需排除是否为攻击者清理或干扰日志所致。

---

## 六、修复建议

### 针对 P0（数据外传）
1. **立即遏制**：在边界防火墙 / WAF / 安全组封禁 `203.0.113.8`。
2. **令牌处置**：吊销 `service-a` 当前所有令牌并强制轮换；审计该服务近期令牌签发与使用记录。
3. **数据影响评估**：拉取 DB 层完整导出日志，确认导出对象、行数、是否含个人信息或核心业务数据；必要时启动数据泄露响应与通知流程。
4. **鉴权加固**：DB 导出接口必须要求强身份认证，禁止 `unknown` / 匿名调用；导出动作强制二次审批或 MFA。

### 针对 P1（令牌越权）
1. 落实最小权限原则，复核 `service-a` 的 token scope，移除非必要权限。
2. 在 API 网关增加 `token_scope_mismatch` 实时告警与自动熔断。
3. 为服务令牌绑定来源 IP / mTLS 身份，降低被盗用后的横向影响。

### 针对 P2（admin 爆破）
1. 对 `admin` 等高权限账户强制 MFA。
2. 配置登录失败限速与账户临时锁定（如 5 次/15 分钟）。
3. 封禁或挑战 `198.51.100.23`；将该 IP 加入威胁情报观察名单。

### 针对 P3（日志完整性）
1. 修复日志采集 / 解析管道，对 `malformed_record` 做结构化落盘而非丢弃关键字段。
2. 校验攻击时间窗内日志是否有缺失或篡改痕迹（日志序号、哈希链、转发延迟）。
3. 日志写入账户与业务账户隔离，防止攻击者反向清理日志。

---

## 七、复测清单（修复后验证）

| 编号 | 复测项 | 预期结果 | 对应风险 |
|---|---|---|---|
| R1 | 从 `203.0.113.8` 发起任意 API/DB 请求 | 被边界拒绝，无响应 | P0 |
| R2 | 使用已吊销的 `service-a` 旧令牌调用 API | 返回 401/403，且触发告警 | P0/P1 |
| R3 | 用 `service-a` 令牌尝试超出 scope 的操作 | 被网关拒绝并记录 `token_scope_mismatch` | P1 |
| R4 | 匿名 / `unknown` 身份调用 DB 导出接口 | 被拒绝，要求强认证 | P0 |
| R5 | 对 `admin` 连续输入错误密码 | 达到阈值后账户锁定或要求 MFA | P2 |
| R6 | 从 `198.51.100.23` 登录 | 被限速 / 挑战 / 封禁 | P2 |
| R7 | 构造一条字段缺失的日志事件 | 采集端完整落盘并标记异常，不丢字段 | P3 |
| R8 | 核对攻击时间窗日志完整性 | 序号连续、无篡改痕迹 | P3 |
| R9 | 复核 `alice` 会话（192.0.2.10） | 无异常操作、无令牌借用痕迹 | 基线 |

---

## 八、最小可验证版本（MVP）说明

### 关键步骤
1. 解压 Skill 包，读取 `SKILL.md` 与 `references/macho-triage.md`。
2. 执行 ACTION REQUIRED：尝试读取 `../field-journal/precedent-reverse.md`（缺失）→ 确认目标类型（CSV，非 Mach-O）→ 判定逆向流程不适用。
3. 用 `file` 与 Python `csv` 模块校验日志结构、字段、空值、时间跨度、IP 分布。
4. 按 severity + 事件语义 + IP 串联做风险分级，输出 P0–P3 与攻击链。
5. 给出修复建议与可执行复测清单。

### 验收标准
- [x] 报告中所有结论均可追溯到 `incident_log.csv` 的具体行与字段。
- [x] 未编造任何 Mach-O / 签名 / 符号级结论；明确标注 Skill 范围不匹配。
- [x] 明确指出缺失文件 `../field-journal/precedent-reverse.md`，未引用其内容。
- [x] 风险分级至少覆盖 critical / high / warning / 异常记录四类。
- [x] 修复建议与复测清单一一对应可验证。
- [x] 产物保存为 `security-audit.md`。

### 局限性与阻断说明
- **Skill 范围阻断**：`macos-reverse` 面向 macOS/Mach-O 逆向，本输入为 CSV 日志，Skill 的核心工作流无法执行；这是输入与 Skill 不匹配导致的方法论阻断，非环境依赖问题。
- **缺失依赖文件**：`../field-journal/precedent-reverse.md` 不在解压包内，无法按 ACTION REQUIRED 第 1 条读取；已如实标注，未编造。
- **数据量限制**：仅 6 条记录、约 9 分钟时间窗，无法做长期行为基线或攻击源归因；结论限于该时间窗内的关联分析。
- **无外部凭据/平台调用**：本报告未访问任何外部系统、未执行动态调试或破坏性操作，符合「仅授权测试范围内分析」的约束。

---

*报告生成时间基准：2026-08-26（UTC）。本报告基于模拟日志，仅用于授权安全分析练习。*
