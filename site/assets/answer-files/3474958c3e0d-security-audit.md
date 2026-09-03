# 安全审计报告：incident_log.csv

## 0. 文档元信息

| 项目 | 内容 |
|---|---|
| 审计对象 | `incident_log.csv`（模拟安全日志，共 6 条记录） |
| 审计日期 | 2026-08-13 |
| 审计性质 | 授权测试范围内的只读日志分析 |
| 操作边界 | 未实施任何破坏性、侵入性或越权操作；未对任何真实系统发起请求；未修改原始日志 |
| 数据性质 | 源 IP `192.0.2.10`、`198.51.100.23`、`203.0.113.8` 均属 RFC 5737 文档保留网段（TEST-NET-1/2/3），印证为模拟数据 |

---

## 1. Skill 适用性裁定（依据实际读取的 SKILL.md）

实际读取的 Skill 文件（相对路径）：

- `competition-ios-runtime/SKILL.md`
- `competition-ios-runtime/references/ios-runtime.md`
- `competition-ios-runtime/agents/openai.yaml`

裁定结论：**该 Skill 不适用于本次任务，不予套用其执行流程。** 依据如下：

1. **前置条件不满足（直接影响结果的规则）**：`SKILL.md` 第 8 行明确规定——"Use this skill only as a downstream specialization after `$ctf-sandbox-orchestrator` is already active and has established sandbox assumptions, node ownership, and evidence priorities. If that has not happened yet, return to `$ctf-sandbox-orchestrator` first." 当前会话中 `$ctf-sandbox-orchestrator` 并未激活，沙箱假设、节点归属、证据优先级均未建立，按该规则应先返回编排器，而不是直接执行本 Skill。
2. **不得隐式调用**：`agents/openai.yaml` 中 `policy.allow_implicit_invocation: false`。
3. **领域不匹配**：该 Skill 面向 iOS 运行时信任边界分析（IPA、Frida hook、Keychain、SSL pinning 绕过、请求签名重放）；本次输入为 web/api/db 三类系统的 CSV 安全日志，不存在 IPA、bundle、selector、Keychain 等任何 iOS 运行时目标。

处理方式：遵循 SKILL.md 上述约束，不对 CSV 套用 iOS 运行时分析流程，**不编造** IPA/hook/Keychain/签名重放等不存在的执行结果；业务侧的日志风险分级改用通用只读日志分析完成，所有结论仅基于 `incident_log.csv` 实际内容。

---

## 2. 最小可验证版本（MVP）：关键步骤与验收标准

### 关键步骤

1. 下载并解压 Skill ZIP，逐字读取 `SKILL.md`、`references/ios-runtime.md`、`agents/openai.yaml`，确认前置规则。
2. 只读读取 `incident_log.csv`，按表头 `timestamp,system,severity,event,user,source_ip` 逐行解析。
3. 标注缺失/畸形字段记录，按 `system` 与 `event` 分类。
4. 以 `source_ip` 为关联键做跨系统事件关联，构建时间线。
5. 按"严重度 + 关联性 + 潜在影响"进行风险分级（Critical/High/Medium/Low/Info）。
6. 为每条风险给出：证据（原始日志行）、影响分析、修复建议、复测清单。
7. 输出本报告 `security-audit.md`。

### 验收标准

- [x] 实际读取 SKILL.md 并在报告中引用其前置规则，未违反该规则
- [x] 所有证据均可回溯到 `incident_log.csv` 的具体行，无编造数据、凭据或执行结果
- [x] 每条风险均包含：分级、证据、影响、修复建议、复测方法
- [x] 明确记录畸形/缺失字段记录及其风险
- [x] 未实施任何破坏性或越权操作
- [x] 产物保存为 `security-audit.md`

---

## 3. 日志原始记录

| # | timestamp (UTC) | system | severity | event | user | source_ip |
|---|---|---|---|---|---|---|
| 1 | 2026-08-12T09:00:12Z | web | info | login_success | alice | 192.0.2.10 |
| 2 | 2026-08-12T09:03:45Z | web | warning | login_failed | admin | 198.51.100.23 |
| 3 | 2026-08-12T09:03:49Z | web | warning | login_failed | admin | 198.51.100.23 |
| 4 | 2026-08-12T09:04:02Z | api | high | token_scope_mismatch | service-a | 203.0.113.8 |
| 5 | 2026-08-12T09:07:30Z | db | critical | unexpected_export | unknown | 203.0.113.8 |
| 6 | 2026-08-12T09:09:00Z | web | （空） | malformed_record | （空） | （空） |

---

## 4. 风险分级与发现

### 发现 1：服务令牌越权 + 数据库异常导出（同源 IP 关联）—— 严重（Critical）

**证据（原始日志行）**

- 行 4：`2026-08-12T09:04:02Z, api, high, token_scope_mismatch, service-a, 203.0.113.8`
- 行 5：`2026-08-12T09:07:30Z, db, critical, unexpected_export, unknown, 203.0.113.8`

**关联分析**

同一源 IP `203.0.113.8` 在约 3 分 28 秒内，先在 API 侧触发服务账号 `service-a` 的令牌 scope 不匹配（high），随后在数据库侧触发用户为 `unknown` 的异常导出（critical）。时间邻近性与同源性提示：`service-a` 的令牌可能被窃取、滥用或配置错误，越权调用后进一步访问数据库并导出数据。两条事件单独看分别为 high 与 critical，关联后构成完整的"越权访问→数据外泄"可疑链路。

**潜在影响**

- 敏感数据外泄；服务身份鉴权与最小权限原则失效。
- 因导出用户为 `unknown`，数据库侧可能存在匿名/弱认证导出通道。

**修复建议**

1. 立即吊销 `service-a` 当前令牌并轮换其密钥/凭据；排查该令牌近期签发与使用记录。
2. API 网关强制校验令牌 scope 与所请求资源/操作的绑定关系，越权请求一律拒绝并产生 high 级告警。
3. 数据库侧收紧导出权限：禁止 `unknown`/匿名导出，导出操作须关联工单与二次审批，并记录导出范围、行数与目标。
4. 对 `203.0.113.8` 在相关时段临时封禁，保全该 IP 的全量访问日志以备取证。
5. 核查数据库在 09:07:30 前后实际导出的对象与数据量，评估外泄范围并按事件响应流程上报。

**复测清单**

- 使用超出 scope 的 `service-a` 令牌请求 API，应被拒绝并产生 high 告警。
- 以 `unknown` 用户对数据库执行导出，应被拒绝并告警。
- 令牌轮换后，旧令牌访问应返回 401/鉴权失败。
- 同源 IP 跨 api→db 的异常事件序列应能触发关联告警。

---

### 发现 2：admin 账户短时间连续登录失败 —— 中（Medium）

**证据（原始日志行）**

- 行 2：`2026-08-12T09:03:45Z, web, warning, login_failed, admin, 198.51.100.23`
- 行 3：`2026-08-12T09:03:49Z, web, warning, login_failed, admin, 198.51.100.23`

**分析**

同一 IP `198.51.100.23` 在 4 秒内对 `admin` 账户连续两次登录失败，符合暴力破解/口令喷洒的早期行为特征。样本量较小（仅 2 次），不能排除管理员本人误输口令，但目标账户为高权限 `admin`，应按可疑攻击处理并加固。

**潜在影响**

- 管理员账户被接管，进而导致 web 侧权限失守。

**修复建议**

1. 为 `admin` 启用多因素认证（MFA）。
2. 配置登录失败阈值（如 5 次/5 分钟），触发后临时锁定账户或对来源 IP 限速，并产生告警。
3. 限制管理后台来源 IP，要求经 VPN/堡垒机访问。
4. 确认 `admin` 是否为真实在用账户；若为默认/残留账户应禁用或改名。

**复测清单**

- 连续失败登录超过阈值应触发账户锁定/IP 限速与告警。
- `admin` 未完成 MFA 不得登录。
- 非授权来源 IP 访问管理登录入口应被拦截。

---

### 发现 3：畸形日志记录（字段缺失）—— 中（Medium，数据完整性/可观测性）

**证据（原始日志行）**

- 行 6：`2026-08-12T09:09:00Z, web, , malformed_record, , `

**分析**

该记录 `severity`、`user`、`source_ip` 三个字段为空。可能原因包括：日志采集/序列化管道格式错误、web 服务在异常路径下未填字段、或日志遭篡改/注入。事件名本身为 `malformed_record`，说明上游已识别异常但未补齐关键字段，造成监控与取证盲区。

**潜在影响**

- 关键字段缺失导致无法定位来源与主体；若为篡改则存在反取证风险。

**修复建议**

1. 在日志采集端强制 schema 校验，缺字段记录隔离到死信队列并告警，不进入主分析链路。
2. 排查 09:09 前后 web 服务的异常、发布与依赖故障记录。
3. 对日志启用完整性保护（如哈希链/签名）与写入权限最小化，防止篡改。
4. 为 `malformed_record` 事件配置独立告警与处置流程。

**复测清单**

- 构造缺字段日志，应被采集端隔离并触发告警。
- 对日志的篡改应能被完整性校验检出。
- `malformed_record` 事件具备明确告警阈值与责任人。

---

### 基线记录（信息，Info）

- 行 1：`2026-08-12T09:00:12Z, web, info, login_success, alice, 192.0.2.10` —— 正常登录成功，作为正常行为基线，无风险。

---

## 5. 事件时间线

```
09:00:12  web   info      alice 登录成功            192.0.2.10    （基线）
09:03:45  web   warning   admin 登录失败 #1         198.51.100.23
09:03:49  web   warning   admin 登录失败 #2         198.51.100.23  （4 秒内）
09:04:02  api   high      service-a token scope 不匹配  203.0.113.8
09:07:30  db    critical  unknown 异常导出          203.0.113.8   （与上行同源，+3m28s）
09:09:00  web   (空)      malformed_record         (空)
```

---

## 6. 总体结论与处置优先级

| 优先级 | 发现 | 建议处置时限 |
|---|---|---|
| P0 | 发现 1：服务令牌越权 + 数据库异常导出（同源关联） | 立即：吊销令牌、封禁 IP、核查外泄范围 |
| P1 | 发现 2：admin 连续登录失败 | 短期：MFA、登录限速、来源限制 |
| P2 | 发现 3：畸形日志记录 | 持续改进：日志 schema 校验与完整性保护 |

核心结论：日志中最需立即处置的是 `203.0.113.8` 关联的"令牌 scope 越权 → 数据库异常导出"链路，存在数据外泄可能；`admin` 登录失败与畸形记录为加固项。全部结论基于现有 6 条模拟日志证据，未做超出数据的推断。

---

## 7. 限制与声明

- 本报告仅基于 6 条模拟日志，无请求体、导出数据量、账户体系、WAF/网关等更多上下文，结论为基于现有证据的合理推断，非最终司法取证结论。
- 未读取到 IPA、bundle、Frida、Keychain 等任何 iOS 运行时对象；`competition-ios-runtime` Skill 的前置编排器未激活、领域不匹配，按 SKILL.md 规则未套用其流程，未编造相关执行结果。
- 全程仅做只读分析，未实施任何破坏性操作。
