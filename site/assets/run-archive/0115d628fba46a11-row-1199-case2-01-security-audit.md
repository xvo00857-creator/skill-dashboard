# 安全日志审计报告

> 输入文件：`incident_log.csv`（6 条事件，时间窗口 2026-08-12 09:00:12Z – 09:09:00Z）
> 执行依据：Skill `js-reverse` 的 SKILL.md 及其 references（实际读取路径见文末附录）
> 生成时间：2026-08-26
> 授权范围：仅对模拟安全日志做只读分析，不实施任何破坏性操作

---

## 一、执行说明与 Skill 适配

### 1.1 Skill 范围与业务任务的冲突（约束一）

`js-reverse` 的 SKILL.md「适用范围」明确限定为前端 JavaScript 逆向场景（签名链路定位、页面观察取证、运行时采样、本地补环境复现），而本次业务任务是**安全日志分析**。二者不存在直接的工具链映射。

**取舍决策**：不强行套用 JS 逆向的五阶段工作流（Observe→Capture→Rebuild→Patch→DeepDive）中的浏览器/MCP 操作步骤，而是迁移该 Skill 中与任务无关但可复用的核心原则：

| Skill 原则 | 迁移到日志分析的具体做法 |
|---|---|
| `Evidence-first`（证据优先） | 每条风险分级必须引用日志中的原始字段（timestamp / event / source_ip / user），禁止无证据推测 |
| `Observe-first`（先观察后猜测） | 先完整读取全部日志行并建立时间线，再做关联分析，不跳过原始数据直接下结论 |
| 输出契约（output-contract.md） | 报告必须包含：目标事件、证据来源、是否可稳定复现、若未完成还差什么缺口 |
| 任务产物（task-artifacts.md） | 保留目标事件样例、关联线索、first divergence（首个异常点）、每次分析决策说明 |
| 回退策略（fallbacks.md） | 当某条路径无证据支撑时，从「攻击手法猜测」回退到「日志原始证据」 |

### 1.2 工具依赖缺失（约束二）

SKILL.md「ACTION REQUIRED」要求读取 `../field-journal/precedent-reverse.md` 和 `../tool-index.md`，并默认绑定 `js-reverse_*` MCP 工具集，可选联动 `jshookmcp`。实际情况：

- ZIP 包内**不包含** `field-journal/`、`tool-index.md`、`reverse-engineering/` 等外部引用目录
- ZIP 包内**不包含** SKILL.md 提到的 `scripts/bootstrap-reverse.ps1` 自举脚本
- 当前运行环境（Ubuntu 22.04）**未注册** `js-reverse_*` MCP server，也未启用 `jshookmcp`
- 自举脚本为 PowerShell 格式，与当前 Linux 环境不兼容

**取舍决策**：依据 SKILL.md「如果无法解释为什么调用某个工具，就不要调用」的规则，**不调用任何不存在的 `js-reverse_*` 工具，不伪造工具输出**。使用环境中可用的只读文件读取能力完成日志分析，并在本报告中明确记录该依赖缺口。这一规则直接影响了报告的证据形态——所有证据均来自 CSV 原始字段，而非 MCP 工具的运行时采样结果。

### 1.3 数据量有限（约束三）

输入仅 6 条事件、跨度 9 分钟，缺少请求载荷、响应状态码、用户身份核验记录、导出内容明细等上下文。

**取舍决策**：基于已有证据做分级，对证据不足的部分标注「待确认」而非臆断攻击手法。

---

## 二、日志时间线与原始证据

| # | 时间 (UTC) | 系统 | 严重级 | 事件 | 用户 | 来源 IP |
|---|---|---|---|---|---|---|
| 1 | 09:00:12 | web | info | login_success | alice | 192.0.2.10 |
| 2 | 09:03:45 | web | warning | login_failed | admin | 198.51.100.23 |
| 3 | 09:03:49 | web | warning | login_failed | admin | 198.51.100.23 |
| 4 | 09:04:02 | api | high | token_scope_mismatch | service-a | 203.0.113.8 |
| 5 | 09:07:30 | db | critical | unexpected_export | unknown | 203.0.113.8 |
| 6 | 09:09:00 | web | *(空)* | malformed_record | *(空)* | *(空)* |

**first divergence（首个异常点）**：事件 #2（09:03:45，admin 登录失败），在此之前仅有一条正常登录成功记录。

---

## 三、风险分级与证据

### 风险 1：疑似数据外泄（Critical）

- **事件**：#5 `unexpected_export`
- **时间**：2026-08-12 09:07:30Z
- **系统**：db
- **用户**：unknown（未识别身份）
- **来源 IP**：203.0.113.8
- **证据**：日志原始行 `2026-08-12T09:07:30Z,db,critical,unexpected_export,unknown,203.0.113.8`
- **关联分析**：同一 IP `203.0.113.8` 在 3 分 28 秒前（09:04:02）触发了 `token_scope_mismatch`（事件 #4）。时间序列呈现「令牌越权 → 数据库导出」的链式特征，高度疑似利用越权令牌执行未授权数据导出。
- **定级依据**：critical 严重级 + 数据库系统 + 未授权导出 + 身份未知 + 与高危事件同源 IP，构成数据泄露的强信号。

### 风险 2：API 令牌越权（High）

- **事件**：#4 `token_scope_mismatch`
- **时间**：2026-08-12 09:04:02Z
- **系统**：api
- **用户**：service-a
- **来源 IP**：203.0.113.8
- **证据**：日志原始行 `2026-08-12T09:04:02Z,api,high,token_scope_mismatch,service-a,203.0.113.8`
- **关联分析**：`service-a` 的令牌请求了超出其授权范围的资源。该令牌可能被泄露、被提权，或 service-a 本身存在配置错误。与事件 #5 同源 IP 表明该越权访问可能是后续数据导出的前置步骤。
- **定级依据**：high 严重级 + 令牌权限边界被突破 + 与 critical 事件存在因果关联。

### 风险 3：管理员账户暴力破解（Medium）

- **事件**：#2、#3 `login_failed`（admin）
- **时间**：2026-08-12 09:03:45Z、09:03:49Z（间隔 4 秒）
- **系统**：web
- **用户**：admin
- **来源 IP**：198.51.100.23
- **证据**：两条连续日志行，同一 IP、同一目标账户、4 秒内两次失败
- **分析**：针对高权限账户 `admin` 的快速登录失败尝试。仅 2 次失败尚未达到典型暴力破解阈值，但短间隔（4 秒）和目标为 admin 表明这是自动化尝试的开始，而非用户误输。日志窗口仅 9 分钟，无法确认此前或此后是否有更多尝试。
- **定级依据**：warning 严重级 × 2 + 目标为管理员账户 + 短间隔自动化特征，但因样本量有限定为 Medium。

### 风险 4：日志完整性异常（Low / 待确认）

- **事件**：#6 `malformed_record`
- **时间**：2026-08-12 09:09:00Z
- **系统**：web
- **严重级 / 用户 / 来源 IP**：均为空
- **证据**：日志原始行 `2026-08-12T09:09:00Z,web,,malformed_record,,`
- **分析**：该记录缺少 severity、user、source_ip 三个关键字段。存在两种可能：(a) 日志采集管道故障或格式变更导致字段丢失；(b) 攻击者在数据导出后尝试篡改或淹没日志以掩盖痕迹。由于该事件紧随 critical 导出事件（09:07:30）之后 1 分 30 秒出现，时间上的接近性使 (b) 不能排除。但仅凭一条畸形记录无法区分两种原因。
- **定级依据**：无严重级标注 + 字段缺失 + 时间上紧随高危事件，定为 Low 但标记为「待确认 / 需排查」。

### 基线事件（Info，非风险）

- **事件**：#1 `login_success`（alice，192.0.2.10，09:00:12）
- 正常登录成功，作为时间线基线参考。无异常特征。

---

## 四、攻击链关联分析

```
09:00:12  alice 正常登录 (基线)
    │
09:03:45  admin 登录失败 ← 198.51.100.23 (暴力破解尝试，独立链路)
09:03:49  admin 登录失败 ← 198.51.100.23
    │
09:04:02  token_scope_mismatch ← 203.0.113.8 (service-a 令牌越权)
    │  同一 IP，3分28秒后
09:07:30  unexpected_export ← 203.0.113.8 (unknown 用户，数据库导出) ★
    │  1分30秒后
09:09:00  malformed_record (字段缺失，疑似日志异常)
```

**两条独立链路**：
1. **链路 A（暴力破解）**：198.51.100.23 → admin 登录失败。与其他事件无 IP 或用户关联，疑似独立的扫描/爆破行为。
2. **链路 B（越权导出）**：203.0.113.8 → token_scope_mismatch → unexpected_export。同一 IP 串联高危和严重事件，构成完整的「权限突破 → 数据窃取」攻击链。malformed_record 在时间上紧随其后，可能是该链路的收尾动作（日志掩盖）或无关的管道故障。

---

## 五、修复建议

### 5.1 紧急处置（针对风险 1、2，链路 B）

| 优先级 | 措施 | 依据 |
|---|---|---|
| P0 | 立即吊销或轮换 `service-a` 的 API 令牌，排查该令牌的访问范围配置 | 事件 #4 令牌越权 |
| P0 | 对 IP `203.0.113.8` 实施临时封禁，检查该 IP 在防火墙/WAF 中的历史访问 | 事件 #4、#5 同源 |
| P0 | 核查 09:04:02–09:07:30 期间数据库导出操作的具体内容、目标表、导出量和目的地 | 事件 #5 数据外泄 |
| P1 | 确认 `unknown` 用户的身份——是未认证访问、服务账户映射失败，还是日志字段丢失 | 事件 #5 user=unknown |
| P1 | 审计 service-a 令牌的签发记录和最近使用范围，判断是配置错误还是令牌泄露 | 事件 #4 |

### 5.2 短期加固（针对风险 3）

| 优先级 | 措施 | 依据 |
|---|---|---|
| P2 | 对 `admin` 账户启用登录失败锁定策略（如 5 次失败锁定 15 分钟） | 事件 #2、#3 |
| P2 | 对 IP `198.51.100.23` 加入观察名单，检查是否有更广泛的扫描行为 | 事件 #2、#3 |
| P2 | 为管理员账户强制启用多因素认证（MFA） | 针对 admin 账户的爆破风险 |

### 5.3 中期治理（针对风险 4 及系统性问题）

| 优先级 | 措施 | 依据 |
|---|---|---|
| P3 | 排查日志采集管道在 09:09:00 前后的健康状态，确认 malformed_record 是管道故障还是人为篡改 | 事件 #6 |
| P3 | 为日志管道增加字段完整性校验和告警，关键字段（severity/user/source_ip）缺失时触发通知 | 事件 #6 字段缺失 |
| P3 | 实施数据库导出操作的审批流程和异常检测，非预期导出应实时告警而非仅记录 | 事件 #5 |
| P3 | 建立 API 令牌scope 的最小权限审查机制，定期校验服务账户令牌权限与实际需求的匹配度 | 事件 #4 |
| P3 | 部署跨系统关联规则（如同源 IP 在 API 越权后短时间内触发 DB 导出时自动告警） | 链路 B 关联特征 |

---

## 六、复测清单

修复措施实施后，按以下清单逐项验证：

### 6.1 紧急处置复测

- [ ] `service-a` 旧令牌已吊销，使用旧令牌调用 API 返回 401/403
- [ ] 新签发的令牌 scope 已收敛至最小必要权限
- [ ] IP `203.0.113.8` 在防火墙/WAF 中已被封禁，从该 IP 的请求被拦截
- [ ] 数据库导出日志中 09:04–09:08 时间段的导出内容已定位并评估泄露范围
- [ ] `unknown` 用户的身份已确认（认证失败 / 服务账户 / 字段丢失）

### 6.2 短期加固复测

- [ ] admin 账户连续失败 N 次后触发锁定，锁定期间登录返回明确提示
- [ ] IP `198.51.100.23` 已加入威胁情报观察名单
- [ ] admin 账户已启用 MFA，登录流程要求第二因子

### 6.3 中期治理复测

- [ ] 日志管道字段完整性校验已上线，模拟一条缺失 severity 的记录可触发告警
- [ ] malformed_record 的根因已查明并修复（管道配置 / 采集器版本 / 人为篡改）
- [ ] 数据库非预期导出的实时告警规则已配置并经过触发测试
- [ ] API 令牌 scope 定期审查机制已建立（建议季度审查）
- [ ] 跨系统关联告警规则（API 越权 + DB 导出同源 IP）已部署并测试

### 6.4 回归验证

- [ ] alice 等正常用户的登录流程不受封禁/锁定策略影响
- [ ] service-a 的合法业务调用在新令牌下功能正常
- [ ] 日志采集管道在修复后无新增 malformed_record

---

## 七、关键取舍、依赖与风险

### 7.1 关键取舍

1. **Skill 适配而非硬套**：js-reverse 是 JS 逆向 Skill，与日志分析无直接工具映射。选择迁移其 Evidence-first、Observe-first、输出契约等通用原则，而非强行执行浏览器页面打开、XHR 断点、Node 补环境等不相关步骤。这一取舍确保了报告结构严谨但不浪费精力在无关操作上。

2. **证据不足时标注而非臆断**：malformed_record 的原因（管道故障 vs 日志篡改）无法仅凭一条记录区分。选择标注为「待确认」并给出两种假设，而非断定为攻击行为。这符合 Skill 的「从源码猜测回退到运行时证据」回退原则。

3. **暴力破解定级为 Medium 而非 High**：虽然目标是 admin 账户，但仅有 2 次失败记录，未达到典型阈值。选择 Medium 并建议扩大时间窗口排查，避免过度告警。

### 7.2 依赖

- **已满足**：CSV 文件可读、Python/Bash 环境可用、文件写入权限正常
- **未满足（已记录缺口）**：
  - `js-reverse_*` MCP 工具集（SKILL.md 默认依赖）
  - `jshookmcp` MCP server（SKILL.md 增强执行面）
  - `../field-journal/precedent-reverse.md`（ACTION REQUIRED 要求读取）
  - `../tool-index.md`（ACTION REQUIRED 要求读取）
  - `scripts/bootstrap-reverse.ps1`（自举脚本，ZIP 内不存在）
  - 更完整的日志数据（请求载荷、响应码、导出内容明细、更长时间窗口）

### 7.3 风险

- **误报风险**：链路 B 的「令牌越权 → 数据导出」关联基于同源 IP 和时间 proximity，若 service-a 是合法服务且导出是预期操作，则可能误报。需结合业务上下文确认。
- **漏报风险**：日志窗口仅 9 分钟，暴力破解可能在窗口外已有大量尝试；数据导出可能在窗口外已持续进行。
- **日志篡改风险**：若 malformed_record 是攻击者掩盖痕迹的结果，则现有日志可能已不完整，真实攻击面可能更大。
- **Skill 依赖缺失风险**：由于无法使用 `js-reverse_*` 工具，本报告未包含运行时采样、调用栈回溯等深度取证内容。若任务实际需要 JS 逆向层面的分析（例如日志中涉及前端签名参数），则需在具备 MCP 工具的环境中重新执行。

---

## 八、结论

本次审计在 6 条模拟安全日志中识别出 **1 项 Critical（疑似数据外泄）、1 项 High（API 令牌越权）、1 项 Medium（管理员暴力破解）、1 项 Low/待确认（日志完整性异常）**。其中 Critical 与 High 事件同源 IP（203.0.113.8），构成「越权访问 → 数据导出」的攻击链，需优先处置。管理员账户暴力破解为独立链路。日志畸形记录需排查根因。

所有分级均基于 CSV 原始字段证据，未做无依据推测。报告遵循了 js-reverse Skill 的 Evidence-first 原则和输出契约结构，但因 Skill 范围与任务不匹配且 MCP 工具依赖缺失，未执行 JS 逆向相关操作步骤。

---

## 附录 A：实际读取的 Skill 文件相对路径

以下文件均从 `js-reverse.zip` 解压后实际读取（相对于解压根目录 `js-reverse-skill/`）：

1. `js-reverse/SKILL.md` — 主规范文件
2. `js-reverse/references/output-contract.md` — 输出契约
3. `js-reverse/references/task-artifacts.md` — 任务产物规范
4. `js-reverse/references/fallbacks.md` — 回退策略
5. `js-reverse/references/automation-entry.md` — 自动化入口
6. `js-reverse/references/tool-defaults.md` — 工具默认值
7. `js-reverse/references/task-input-template.md` — 任务输入模板
8. `js-reverse/references/mcp-task-template.md` — MCP 任务编排模板
9. `js-reverse/references/local-rebuild.md` — 本地复现规范
10. `js-reverse/references/env-patching.md` — 补环境规则
11. `js-reverse/references/node-env-rebuild.md` — Node 环境复现
12. `js-reverse/references/instrumentation.md` — 插桩规范
13. `js-reverse/references/ast-deobfuscation.md` — AST 去混淆规范

**SKILL.md 中引用但 ZIP 内不存在、未能读取的文件**：
- `../field-journal/precedent-reverse.md`
- `../tool-index.md`
- `../reverse-engineering/references/nonpe-format-cookbook.md`
- `scripts/bootstrap-reverse.ps1`

## 附录 B：确实影响结果的 SKILL.md 规则

**规则：「如果无法解释为什么调用某个工具，就不要调用」（SKILL.md「执行要求」章节）**

该规则直接决定了本报告的证据形态和分析路径。由于当前环境未注册 `js-reverse_*` MCP 工具集，且 SKILL.md 的默认工具映射（如 `js-reverse_list_network_requests`、`js-reverse_break_on_xhr` 等）均不可用，依据此规则**不得调用或伪造这些工具的输出**。因此：

- 报告中的所有证据均来自 CSV 原始字段读取，而非 MCP 运行时采样
- 未执行浏览器页面打开、网络请求拦截、调用栈回溯等 JS 逆向步骤
- 分析深度受限于静态日志数据，无法进行运行时取证
- 报告中明确记录了工具依赖缺口，而非假装工具可用

若违反此规则（例如编造 `js-reverse_*` 工具的调用结果），将产生虚假证据，导致风险分级和修复建议失去可信度。
