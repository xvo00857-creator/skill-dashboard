# 安全审计报告：incident_log.csv 模拟日志分析

> 分类：安全与合规
> 审计日期：2026-08-13
> 输入文件：incident_log.csv（6 条记录，时间范围 2026-08-12T09:00:12Z ~ 09:09:00Z）
> 审计范围：仅对授权提供的模拟日志文件进行只读分析，未执行任何破坏性操作、未访问任何外部系统

---

## 0. Skill 适用性声明（必读）

本报告依据随附 Skill `competition-browser-persistence` 的 SKILL.md 执行。经实际阅读，存在以下前提差异，须如实声明：

1. **前置编排器未激活**：SKILL.md 第 8 行规定"Use this skill only as a downstream specialization after `$ctf-sandbox-orchestrator` is already active and has established sandbox assumptions, node ownership, and evidence priorities. If that has not happened yet, return to `$ctf-sandbox-orchestrator` first."当前环境中 `$ctf-sandbox-orchestrator` 并未激活，也无沙箱假设、节点归属或证据优先级的上游输出。
2. **领域不完全匹配**：该 Skill 的工作域是浏览器持久化状态（cookie、localStorage、sessionStorage、IndexedDB、Cache Storage、Service Worker），而本次输入为服务端安全事件 CSV 日志，不含任何浏览器端状态数据。
3. **处理方式**：未编造任何浏览器状态、存储项或外部凭据；仅借用 SKILL.md 中与本次任务兼容的方法论原则（证据-效果关联、最小决定性链、分块举证、干净态对比异常态），对日志进行分析。

**实际读取的 Skill 文件（相对路径）：**
- `competition-browser-persistence/SKILL.md`
- `competition-browser-persistence/references/browser-persistence.md`
- `competition-browser-persistence/agents/openai.yaml`

---

## 1. 最小可验证版本（MVP）：关键步骤与验收标准

### 1.1 关键步骤

| 步骤 | 内容 | 产出 |
|------|------|------|
| S1 | 读取并校验 incident_log.csv 完整性（字段数、空值、格式） | 数据质量备注 |
| S2 | 逐条记录事件，按 severity 初步分级 | 事件清单 |
| S3 | 按 source_ip 关联事件，识别同源事件链 | 关联分析 |
| S4 | 按时间线重建攻击路径，提取最小决定性链 | 决定性链 |
| S5 | 形成风险分级、证据、修复建议、复测清单 | 本报告 |

### 1.2 验收标准

- [x] 日志中全部 6 条记录均被覆盖，无遗漏
- [x] 每条风险结论均引用具体日志行作为证据，不做无证据推断
- [x] 风险分级有明确依据（severity 字段 + 关联分析）
- [x] 修复建议可操作、复测清单可验证
- [x] 未执行任何写入、删除、导出真实数据等破坏性操作
- [x] 未编造日志中不存在的 IP、用户、令牌或浏览器状态

---

## 2. 日志数据概览

| # | 时间 (UTC) | 系统 | 严重级 | 事件 | 用户 | 源 IP |
|---|-----------|------|--------|------|------|-------|
| 1 | 09:00:12 | web | info | login_success | alice | 192.0.2.10 |
| 2 | 09:03:45 | web | warning | login_failed | admin | 198.51.100.23 |
| 3 | 09:03:49 | web | warning | login_failed | admin | 198.51.100.23 |
| 4 | 09:04:02 | api | high | token_scope_mismatch | service-a | 203.0.113.8 |
| 5 | 09:07:30 | db | critical | unexpected_export | unknown | 203.0.113.8 |
| 6 | 09:09:00 | web | *(空)* | malformed_record | *(空)* | *(空)* |

**数据质量备注：**
- 第 6 条记录 severity、user、source_ip 三字段为空，事件类型为 `malformed_record`，表明日志管道本身存在完整性问题，可能是日志注入尝试、采集异常或格式错误。
- 所有 IP 均属于 RFC 5737 文档保留段（192.0.2.0/24、198.51.100.0/24、203.0.113.0/24），确认本日志为模拟数据。

---

## 3. 风险分级与证据

### 风险 1（严重/Critical）：数据库异常导出——疑似数据外泄

- **分级依据**：severity=critical；事件类型 `unexpected_export`；用户字段为 `unknown`（未认证/身份不明）；发生在 db 系统。
- **证据**：
  - 日志第 5 行：`2026-08-12T09:07:30Z,db,critical,unexpected_export,unknown,203.0.113.8`
- **关联分析**：该事件源 IP 203.0.113.8 与 3 分 28 秒前的高危事件（风险 2）相同，构成同源事件链。
- **可能影响**：敏感数据被未授权导出，违反数据保密性；可能涉及合规违规（如个人信息保护法、数据安全法）。
- **置信度**：高（日志直接记录为 critical 且用户为 unknown）。

### 风险 2（高/High）：API 令牌权限范围不匹配——疑似越权利用

- **分级依据**：severity=high；事件类型 `token_scope_mismatch`；涉及服务账号 service-a。
- **证据**：
  - 日志第 4 行：`2026-08-12T09:04:02Z,api,high,token_scope_mismatch,service-a,203.0.113.8`
- **关联分析**：同一 IP 203.0.113.8 在 09:04 触发令牌范围异常后，于 09:07 对 db 发起异常导出。时间线高度衔接，令牌范围不匹配可能是导出操作的前置越权手段。
- **可能影响**：服务账号令牌被滥用或权限配置错误，导致越权访问数据库。
- **置信度**：中高（单条日志 + 同源关联，无法确认令牌是否被窃取，需进一步取证）。

### 风险 3（中/Medium）：admin 账户短时间连续登录失败——疑似暴力破解

- **分级依据**：severity=warning；同一 IP 198.51.100.23 在 4 秒内对 admin 账户连续两次登录失败。
- **证据**：
  - 日志第 2 行：`2026-08-12T09:03:45Z,web,warning,login_failed,admin,198.51.100.23`
  - 日志第 3 行：`2026-08-12T09:03:49Z,web,warning,login_failed,admin,198.51.100.23`
- **关联分析**：两次失败间隔仅 4 秒，符合自动化暴力破解特征；但样本仅 2 次，未达到典型暴力破解的量级，可能是手动输错或早期探测。
- **可能影响**：若口令较弱，admin 账户可能被攻破。
- **置信度**：中（频率可疑但样本量小）。

### 风险 4（中/Medium）：日志记录畸形——日志完整性受损

- **分级依据**：存在 `malformed_record` 事件，且 severity/user/source_ip 字段缺失。
- **证据**：
  - 日志第 6 行：`2026-08-12T09:09:00Z,web,,malformed_record,,`
- **可能影响**：日志采集管道存在缺陷，或攻击者尝试注入/破坏日志以掩盖痕迹；影响审计可追溯性。
- **置信度**：中（无法区分采集故障与恶意注入）。

### 信息项（Info）：alice 正常登录

- 日志第 1 行：`2026-08-12T09:00:12Z,web,info,login_success,alice,192.0.2.10`
- 作为基线正常事件，未发现异常。

---

## 4. 最小决定性链（依据 SKILL.md "Reduce To The Decisive Persistence Chain" 方法论）

参照 SKILL.md 第 38 行"Compress the result to the smallest chain: initial page or login -> state persisted -> subsequent request or render branch -> resulting capability"，将本次事件压缩为最小因果链：

```
09:03:45–09:03:49  admin 连续登录失败（198.51.100.23）
        ↓ （可能的口令喷洒/探测，与后续 IP 不同，暂无法直接关联）
09:04:02  service-a 令牌范围不匹配（203.0.113.8）  ← 越权前置
        ↓ （3 分 28 秒）
09:07:30  unknown 用户从同一 IP 异常导出数据库（203.0.113.8）  ← 关键危害
        ↓
09:09:00  出现畸形日志记录（字段缺失）  ← 可能的痕迹掩盖或采集故障
```

**核心结论**：203.0.113.8 从令牌越权到数据导出构成完整攻击链，是本次审计最需处置的事件。admin 登录失败与畸形日志目前无法与主链直接关联，需补充日志进一步判断。

---

## 5. 修复建议

### 5.1 针对风险 1（数据库异常导出）

1. 立即核查 2026-08-12 09:07:30Z 前后 db 系统的导出操作记录，确认被导出的数据集范围与体量。
2. 吊销并轮换 service-a 及同期可能泄露的所有凭据/令牌。
3. 对数据库导出操作实施强制审批与最小权限控制，禁止 unknown/匿名身份执行导出。
4. 检查 203.0.113.8 的访问是否还触及其他系统，扩大排查窗口至事件前后 24 小时。

### 5.2 针对风险 2（令牌范围不匹配）

1. 审计 service-a 令牌的 scope 配置，确认其实际权限与业务所需权限是否一致（最小权限原则）。
2. 在 API 网关层对 scope 不匹配请求实施实时拦截与告警，而非仅记录日志。
3. 建立服务账号令牌的定期轮换与异常使用检测机制。

### 5.3 针对风险 3（admin 登录失败）

1. 对 admin 账户启用多因素认证（MFA）。
2. 配置登录失败锁定策略（如 5 次失败后临时锁定）与速率限制。
3. 核查 198.51.100.23 在更大时间窗口内的登录尝试，确认是否为持续攻击。

### 5.4 针对风险 4（畸形日志）

1. 校验日志采集管道（agent/parser）的格式处理逻辑，排除采集端 bug。
2. 在日志入口增加格式校验与丢弃/告警策略，防止日志注入。
3. 确保日志字段完整性约束（severity/user/source_ip 不应为空）。

---

## 6. 复测清单

| # | 复测项 | 验证方法 | 通过标准 |
|---|--------|----------|----------|
| 1 | 数据库导出权限已收紧 | 使用 service-a 令牌尝试导出 db 数据 | 请求被拒绝并产生 high 级告警 |
| 2 | service-a 令牌已轮换 | 使用旧令牌调用 API | 返回 401/403，旧令牌失效 |
| 3 | 令牌 scope 校验生效 | 使用超出 scope 的令牌调用 API | 实时拦截，不产生实际后端操作 |
| 4 | admin 账户 MFA 已启用 | 从新设备登录 admin | 要求第二因素验证 |
| 5 | 登录失败锁定生效 | 连续输错 admin 口令超过阈值 | 账户临时锁定并通知管理员 |
| 6 | 日志完整性校验生效 | 发送缺字段的日志条目 | 被入口校验拒绝并产生告警 |
| 7 | 203.0.113.8 已被处置 | 检查防火墙/ACL | 该 IP 后续无成功访问记录 |
| 8 | 数据外泄影响评估完成 | 核查导出数据范围与合规义务 | 形成影响评估报告并完成必要通报 |

---

## 7. 局限性说明

1. 本日志仅 6 条记录、时间跨度约 9 分钟，样本量极小，无法还原完整攻击路径，也无法确认 admin 登录失败与主链是否同源。
2. 日志中无请求体、响应码、User-Agent、会话 ID 等上下文字段，无法进行更深层的取证。
3. 依据 SKILL.md 引用文件 `references/browser-persistence.md` 第 28 行的告诫——"Treating cached UI data as backend authorization without proving a server-side effect"（不得在未证明服务端效果的情况下将缓存 UI 数据当作后端授权），本报告对所有因果关联均标注了置信度，未将时间相邻等同于因果确认。
4. 本报告未执行任何主动探测、漏洞利用或破坏性操作，仅基于提供的日志文件进行只读分析。

---

## 8. 影响结果的 SKILL.md 规则

以下 SKILL.md 规则实际影响了本报告的分析方式与结论表述：

- **SKILL.md 第 8 行**（前置编排器要求）：直接导致本报告第 0 节如实声明 `$ctf-sandbox-orchestrator` 未激活的前提差异，未假装处于完整 CTF 沙箱流程中。
- **SKILL.md 第 18 行**（"Tie stored state to one concrete effect"，将状态关联到一个具体效果）：指导本报告将 token_scope_mismatch 与 unexpected_export 通过同源 IP 和时间线关联为具体因果链，而非孤立罗列事件。
- **references/browser-persistence.md 第 28 行**（Common Pitfalls：不得在未证明服务端效果时将缓存 UI 数据当作后端授权）：指导本报告对所有因果推断标注置信度，避免将时间相邻事件过度断言为已证实因果。
