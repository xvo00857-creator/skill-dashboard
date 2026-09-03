# 安全审计报告：incident_log.csv

- 审计对象：`incident_log.csv`（模拟安全日志，共 6 条记录）
- 审计时间窗口：2026-08-12T09:00:12Z ～ 2026-08-12T09:09:00Z（约 8 分 48 秒）
- 执行依据：Skill `competition-lsass-ticket-material` 的 SKILL.md 及其 `references/lsass-ticket-material.md` 清单
- 范围声明：本报告仅在授权测试范围内对提供的模拟日志做离线分析，未对任何真实系统执行访问、导出、爆破或其他破坏性操作。

---

## 一、最小可验证版本（关键步骤与验收标准）

### 关键步骤
1. **解析与规范化**：读取 CSV 全部 6 行，校验字段完整性，识别空字段与畸形记录。
2. **凭据/会话状态映射**（按 Skill First Pass 清单）：登记登录会话、账户名、源 IP、系统、事件类型、严重级别。
3. **重建决定性凭据链**（按 Skill "Chain To Reconstruct"）：主机制品 → 凭据材料 → 重放/接受路径 → 服务接受 → 最终能力。
4. **风险分级**：按严重/高/中/低/信息五级，每条风险绑定证据行。
5. **修复建议与复测清单**：针对每条风险给出可验证的修复项与复测方法。

### 验收标准
- [x] CSV 全部 6 条记录均被读取并引用，无遗漏、无编造。
- [x] 至少重建一条"制品→材料→接受→能力"的完整证据链。
- [x] 每条风险均有原始日志行作为证据（含时间戳、系统、事件、用户、源 IP）。
- [x] 明确区分"材料存在"与"材料被接受/可重放"，不把仅有迹象夸大为已证实入侵。
- [x] 修复建议与复测清单一一对应，复测项可判定通过/失败。
- [x] 指出日志自身的数据质量缺口及其对结论置信度的影响。

---

## 二、日志原始记录（证据底账）

| # | 时间戳 (UTC) | 系统 | 严重级别 | 事件 | 用户 | 源 IP |
|---|---|---|---|---|---|---|
| 1 | 2026-08-12T09:00:12Z | web | info | login_success | alice | 192.0.2.10 |
| 2 | 2026-08-12T09:03:45Z | web | warning | login_failed | admin | 198.51.100.23 |
| 3 | 2026-08-12T09:03:49Z | web | warning | login_failed | admin | 198.51.100.23 |
| 4 | 2026-08-12T09:04:02Z | api | high | token_scope_mismatch | service-a | 203.0.113.8 |
| 5 | 2026-08-12T09:07:30Z | db | critical | unexpected_export | unknown | 203.0.113.8 |
| 6 | 2026-08-12T09:09:00Z | web | （空） | malformed_record | （空） | （空） |

---

## 三、凭据/会话状态映射（Skill First Pass）

| 清单要素 | 日志中可观测内容 | 不可观测/缺失 |
|---|---|---|
| 登录会话 | alice 成功登录（#1）；admin 两次失败（#2、#3） | 无 LUID、会话 ID |
| 账户名 | alice、admin、service-a、unknown | 无域/机器账户上下文 |
| 凭据材料类型 | API token（#4，service-a 作用域不匹配）；DB 访问身份 unknown（#5） | 无明文/NTLM 哈希/TGT/服务票据/DPAPI 秘密/SSP 残留 |
| 接受候选 | API（#4 拒绝/告警）、DB（#5 接受并执行导出） | 无 SMB/WinRM/Schannel/DPAPI unwrap 等边缘证据 |
| 票据/包信息 | 不适用（应用层日志，非 LSASS/kerberos 层） | 无 SPN、票据标志、加密类型、缓存位置、package 名 |

> 说明：本 Skill 原生面向 LSASS 驻留凭据、Kerberos 票据缓存、DPAPI/SSP 材料；本次输入为 web/api/db 应用层日志，故 LUID、票据缓存、SPN、加密类型等字段在数据源中不存在。下文仅复用 Skill 的"凭据链重建"与"证据打包"方法论，不臆造不存在的 LSASS 字段。

---

## 四、决定性凭据链重建（Skill Chain To Reconstruct）

### 链条 A：203.0.113.8 可疑凭据使用 → DB 未授权导出（主链）

| 链节 | 证据 | 说明 |
|---|---|---|
| 1. 制品/凭据材料被提交 | #4：api，token_scope_mismatch，service-a，203.0.113.8，09:04:02Z | service-a 的 token 被提交，但作用域不匹配（材料存在，但在 API 侧未获预期授权） |
| 2. 重放/使用路径 | 同源 IP 203.0.113.8，间隔 208 秒（3 分 28 秒） | 由 API 侧向 DB 侧横向移动/凭据复用的时间与来源关联 |
| 3. 服务接受 | #5：db，unexpected_export，user=unknown，203.0.113.8，09:07:30Z | DB 接受了来自该源的访问，且身份为 unknown（认证/授权异常） |
| 4. 最终能力 | unexpected_export（critical） | 结果为非预期数据导出，即数据外泄能力被实际行使 |

**置信度与边界（依据 Skill "Common Pitfalls"）**：
- 日志可证明：同一源 IP 在 3 分 28 秒内先后触发 API token 作用域异常与 DB 关键导出事件，且 DB 侧身份为 unknown。
- 日志**不能**直接证明：#4 与 #5 使用的是同一个 token/凭据（同源 IP 是关联证据，非同一凭据的铁证）；也不能证明 token 系从 LSASS 或票据缓存中窃取。
- 因此本链定性为"高度可疑的凭据滥用/横向移动导致数据外泄"，而非"已证实 token 被盗并重放"。需补充 API 网关 token 审计日志、DB 会话认证日志与网络连接日志以闭环。

### 链条 B：198.51.100.23 对 admin 的快速失败登录

| 链节 | 证据 |
|---|---|
| 材料提交 | #2、#3：web，login_failed，admin，198.51.100.23，09:03:45Z 与 09:03:49Z |
| 接受结果 | 两次均失败，未建立会话 |
| 最终能力 | 无（未获授权） |

两次失败间隔 4 秒，呈自动化尝试特征，但样本量仅 2 次，未达持续爆破阈值；无成功接受方，不构成可重放凭据链。

---

## 五、风险分级

### 风险 1 — 严重（Critical）：DB 非预期导出，身份 unknown
- **证据**：#5，2026-08-12T09:07:30Z，db，critical，unexpected_export，user=unknown，src=203.0.113.8。
- **影响**：数据库数据被非预期导出，存在数据泄露/外泄；访问身份为 unknown，表明认证或审计存在缺口。
- **置信度**：高（事件本身被日志直接记录）；归属到链条 A 的凭据复用为中高置信度。

### 风险 2 — 高危（High）：service-a token 作用域不匹配
- **证据**：#4，2026-08-12T09:04:02Z，api，high，token_scope_mismatch，user=service-a，src=203.0.113.8。
- **影响**：token 权限边界异常，可能为越权令牌、被盗服务账号令牌或配置错误；是风险 1 的潜在前置事件。
- **置信度**：高（事件直接记录）；与风险 1 的因果关联为中高置信度（同源 IP、时间相邻）。

### 风险 3 — 中危（Medium）：admin 账户快速失败登录
- **证据**：#2、#3，09:03:45Z 与 09:03:49Z（间隔 4 秒），web，warning，login_failed，admin，src=198.51.100.23。
- **影响**：疑似口令猜测/喷洒早期阶段；当前未成功，但 admin 为高价值账户。
- **置信度**：中（样本仅 2 次，不能排除误操作）。

### 风险 4 — 低危（Low）：日志记录畸形/字段缺失
- **证据**：#6，2026-08-12T09:09:00Z，web，malformed_record，severity/user/source_ip 均为空。
- **影响**：日志完整性受损，既可能是采集管道缺陷，也可能是攻击者干扰审计；发生在风险 1 之后 90 秒，时序可疑。
- **置信度**：中（无法区分管道故障与人为干扰）。

### 信息（Info）：正常基线
- #1：alice 于 09:00:12Z 从 192.0.2.10 成功登录 web，未见异常，作为正常基线。

---

## 六、修复建议

| 风险 | 修复建议 |
|---|---|
| 风险 1（DB 导出） | 1) 立即吊销/轮换 203.0.113.8 相关服务账号与令牌；2) DB 侧禁用匿名/unknown 身份访问，强制强认证；3) 限制 DB 导出权限（最小权限、导出审批、行级/列级脱敏）；4) 核查 09:07:30Z 前后导出的数据范围与去向，必要时启动数据泄露响应。 |
| 风险 2（token 作用域） | 1) 收紧 service-a token 的 scope，遵循最小权限；2) API 网关强制校验 audience/scope，拒绝越权令牌并告警；3) 建立服务账号令牌生命周期管理（轮换、过期、绑定来源网络）。 |
| 风险 3（admin 登录） | 1) admin 账户启用强口令+MFA；2) 登录失败阈值锁定与速率限制；3) 对 198.51.100.23 做临时封禁/观察，结合更长时间窗日志判断是否持续爆破。 |
| 风险 4（日志畸形） | 1) 修复 web 日志采集管道，保证 severity/user/source_ip 必填；2) 日志传输启用防篡改（追加写、集中存储、完整性校验）；3) 对 malformed_record 比例建立监控告警。 |

---

## 七、复测清单

| 编号 | 复测项 | 通过标准 |
|---|---|---|
| RT-1 | DB 不再接受 unknown 身份访问 | 用未认证/越权凭据连接 DB 被拒绝，审计日志中无 user=unknown 的访问记录 |
| RT-2 | 非授权导出被阻断 | 普通服务账号尝试导出被拒；导出操作产生审批记录与告警 |
| RT-3 | service-a token 越权使用被拦截 | 用超出 scope 的 token 调 API 返回 403，并产生 high 级告警；轮换后的旧 token 失效 |
| RT-4 | admin 爆破防护生效 | 连续失败（如 ≥5 次/分钟）触发账户锁定或 MFA 二次校验，源 IP 被速率限制 |
| RT-5 | 日志完整性 | 连续 24 小时无 malformed_record；关键字段（severity/user/source_ip）非空率 100% |
| RT-6 | 证据链闭环（补充取证） | 调取 API 网关 token 审计、DB 会话认证、网络连接日志，确认 #4 与 #5 是否为同一凭据/同一会话；若确认，更新本报告置信度为"已证实" |

---

## 八、结论

在约 9 分钟的日志窗口内，发现一条以 203.0.113.8 为核心的高度可疑凭据滥用链：服务账号 service-a 的 token 在 API 侧触发作用域不匹配（高危），3 分 28 秒后同一源 IP 以 unknown 身份在 DB 侧触发非预期数据导出（严重）。该链条已满足"凭据材料提交→服务接受→最终能力行使"的证据要件，但受限于应用层日志，无法证实两次事件使用同一凭据，需补充网关与 DB 认证日志闭环。同时存在 admin 快速失败登录（中危）和日志畸形（低危）。建议按修复建议处置并按复测清单验收。

---

## 九、实际读取的 Skill 文件（相对路径）

- `competition-lsass-ticket-material/competition-lsass-ticket-material/SKILL.md`
- `competition-lsass-ticket-material/competition-lsass-ticket-material/references/lsass-ticket-material.md`
- `competition-lsass-ticket-material/competition-lsass-ticket-material/agents/openai.yaml`

## 十、影响结果的 SKILL.md 规则

SKILL.md "Common Pitfalls"（见 references/lsass-ticket-material.md）明确要求：**"Treating every extracted secret as replayable without proving an accepting service"**（不得在未证明接受方的情况下把每条提取到的秘密都当作可重放）。该规则直接影响本报告结论：日志中 #4 仅证明 token 材料存在且作用域异常，不能据此断言"token 被盗且可重放"；只有结合 #5 中 DB 确实接受了同源访问并产生导出能力，才将链条定性为"高度可疑的凭据滥用"，并在置信度部分明确标注证据边界，未夸大为"已证实 token 重放"。
