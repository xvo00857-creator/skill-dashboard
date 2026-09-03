# 安全审计报告：incident_log.csv

- 审计对象：`incident_log.csv`（6 条记录，时间范围 2026-08-12T09:00:12Z ~ 09:09:00Z）
- 审计日期：2026-08-13
- 审计人：罗梅梅（ByteDance / Spring产品-豆包和Dola-Dola）
- 执行模式：仅在授权测试范围内分析模拟日志，不实施任何破坏性操作
- 使用 Skill：`competition-graphql-rpc-drift`（分类：安全与合规）

---

## 一、结论概述

本次审计在 `incident_log.csv` 中识别出 **1 条严重、1 条高危、1 条中危、1 条低危** 事件，以及 1 条正常信息记录。最关键的发现是：同一来源 IP `203.0.113.8` 在 09:04:02 触发 `token_scope_mismatch`（高危）后，仅隔约 3.5 分钟于 09:07:30 以 `unknown` 用户身份执行 `unexpected_export`（严重），构成"令牌作用域异常 → 未授权数据导出"的疑似攻击链，需立即处置。

同时需说明：所加载的 Skill `competition-graphql-rpc-drift` 有明确的前置条件（须由 `$ctf-sandbox-orchestrator` 先行激活并建立沙箱假设），且其工作流要求 GraphQL schema、RPC manifest、persisted query map、生成客户端、OpenAPI 文档及 live handler 请求/响应对等契约工件。本次输入仅为通用 CSV 安全日志，**不包含上述任何契约工件或 live handler 流量**，因此该 Skill 的契约漂移（contract drift）专项分析无法执行，详见第五节阻断说明。本报告中的风险分析是基于 CSV 字段完成的通用日志审计，而非 Skill 定义的 GraphQL/RPC 漂移还原。

---

## 二、Skill 前置条件检查

| 检查项 | SKILL.md 要求 | 实际情况 | 结果 |
|---|---|---|---|
| 上游 orchestrator | 第 8 行：须在 `$ctf-sandbox-orchestrator` 已激活并建立沙箱假设、节点归属、证据优先级后使用 | 当前环境无该 orchestrator，本任务为用户直接发起 | 不满足 |
| 声明契约面 | Quick Start 第 1 步：先收集 schema / manifest / generated client / persisted query map / OpenAPI spec | 输入仅为 incident_log.csv，无任何契约工件 | 不满足 |
| 实际请求形态 | Quick Start 第 2 步：记录 operation name、variables、method、path、auth context | CSV 字段为 timestamp/system/severity/event/user/source_ip，无 GraphQL/RPC 请求字段 | 不满足 |
| Live handler 行为 | 工作流第 2 步：捕获真实请求/响应对（含 headers、cookies、status） | 无任何请求/响应数据 | 不满足 |

**结论**：Skill 的漂移还原工作流（声明契约 → 实际请求 → handler 分支 → 所得能力）因缺少必要输入而阻断，无法产出 Skill 定义的"最小契约到处理器不匹配序列"。

---

## 三、最小可验证版本（MVV）：关键步骤与验收标准

鉴于上述阻断，本次以"通用日志风险审计"作为最小可验证版本交付。

### 关键步骤

1. **数据完整性校验**：逐行解析 CSV，检查字段缺失、格式异常。
2. **事件分级**：按 severity 字段与事件语义进行风险分级。
3. **关联分析**：按 source_ip、user、时间窗口关联事件，识别攻击链。
4. **证据固定**：逐条引用原始日志行作为证据。
5. **修复建议**：针对每级风险给出可操作的处置与加固建议。
6. **复测清单**：给出修复后验证项。

### 验收标准

- [x] CSV 全部 6 行均被读取并分类，无遗漏。
- [x] 每条风险事件均附原始日志行作为证据。
- [x] 识别出跨事件关联（同 IP 的高危→严重链路）。
- [x] 每条风险均有修复建议与复测项。
- [x] 明确标注 Skill 专项分析的阻断原因，未伪造漂移分析结果。
- [x] 未实施任何破坏性操作（仅只读分析本地文件）。

---

## 四、日志风险分析

### 原始数据

| # | timestamp | system | severity | event | user | source_ip |
|---|---|---|---|---|---|---|
| 1 | 2026-08-12T09:00:12Z | web | info | login_success | alice | 192.0.2.10 |
| 2 | 2026-08-12T09:03:45Z | web | warning | login_failed | admin | 198.51.100.23 |
| 3 | 2026-08-12T09:03:49Z | web | warning | login_failed | admin | 198.51.100.23 |
| 4 | 2026-08-12T09:04:02Z | api | high | token_scope_mismatch | service-a | 203.0.113.8 |
| 5 | 2026-08-12T09:07:30Z | db | critical | unexpected_export | unknown | 203.0.113.8 |
| 6 | 2026-08-12T09:09:00Z | web | （空） | malformed_record | （空） | （空） |

### 风险分级

#### 严重（Critical）— 未授权数据导出

- **事件**：`unexpected_export`
- **证据**：第 5 行 `2026-08-12T09:07:30Z,db,critical,unexpected_export,unknown,203.0.113.8`
- **分析**：数据库层发生非预期导出，用户为 `unknown`（未认证/身份丢失），来源 IP `203.0.113.8`。该 IP 在 3 分 28 秒前刚触发 `token_scope_mismatch`（第 4 行），高度疑似服务令牌被滥用或作用域提升后执行数据外传。
- **影响**：可能导致敏感数据泄露，需立即确认导出范围与数据内容。
- **修复建议**：
  1. 立即吊销/轮换 `service-a` 相关令牌，阻断 `203.0.113.8` 的数据库访问。
  2. 核查数据库审计日志，确认导出的表、行数、时间范围及目标位置。
  3. 检查令牌签发与作用域校验逻辑，确保令牌 scope 与实际访问资源强制匹配（最小权限）。
  4. 对数据库导出操作增加强制审批与二次认证。
- **复测**：
  - 使用越权 scope 令牌请求导出，应被拒绝并记录 high 告警。
  - 未认证请求（unknown）访问导出接口，应返回 401/403。
  - 令牌轮换后，旧令牌访问应全部失效。

#### 高危（High）— 令牌作用域不匹配

- **事件**：`token_scope_mismatch`
- **证据**：第 4 行 `2026-08-12T09:04:02Z,api,high,token_scope_mismatch,service-a,203.0.113.8`
- **分析**：服务账号 `service-a` 持有的令牌声明作用域与实际请求不匹配。结合后续同 IP 的严重导出事件，此为攻击链的第一环——作用域校验可能仅告警未拦截，或存在 handler 侧 fallback 分支允许请求继续执行。
- **与 Skill 的关联（概念层面）**：此事件在语义上接近 Skill 所指的"契约漂移"——令牌声明的 scope（声明契约）与 handler 实际允许的行为不一致。但因缺少令牌原文、scope manifest、handler 代码及请求/响应头，**无法按 Skill 工作流还原最小漂移路径**。
- **修复建议**：
  1. 作用域不匹配应默认拒绝（deny-by-default），而非仅告警放行。
  2. 审计 `service-a` 的令牌签发记录，确认是否存在被篡改或异常签发。
  3. 在 API 网关与服务端双重校验 scope，避免客户端/网关单点校验被绕过。
- **复测**：
  - 构造 scope 不匹配的请求，确认返回 403 且不触达后端 handler。
  - 检查告警是否包含 operation、requested scope、actual scope 字段以便溯源。

#### 中危（Medium）— 管理员账号短时多次登录失败

- **事件**：`login_failed`（admin，连续 2 次）
- **证据**：第 2、3 行，`198.51.100.23` 于 09:03:45 与 09:03:49（间隔 4 秒）连续两次登录 admin 失败。
- **分析**：间隔极短，疑似自动化暴力破解或口令喷洒尝试。当前仅 2 次，未达锁定阈值，但需关注是否有后续未记录尝试。
- **修复建议**：
  1. 对 admin 账号启用登录失败锁定/速率限制（如 5 次/5 分钟锁定）。
  2. admin 账号强制 MFA。
  3. 对 `198.51.100.23` 加入监控观察名单。
- **复测**：
  - 连续失败超过阈值后账号应被临时锁定。
  - 锁定事件应产生 warning/critical 日志。

#### 低危（Low）— 日志记录畸形

- **事件**：`malformed_record`
- **证据**：第 6 行 `2026-08-12T09:09:00Z,web,,malformed_record,,`，severity/user/source_ip 字段均为空。
- **分析**：日志字段缺失，可能原因：(a) 日志采集/格式化 bug；(b) 日志被篡改以隐藏痕迹；(c) 异常请求导致记录不完整。无论何种原因，都会损害审计完整性。
- **修复建议**：
  1. 排查 web 系统日志采集管道，确认必填字段（severity/user/source_ip）的写入逻辑。
  2. 在日志入库前增加 schema 校验，畸形记录写入死信队列并告警。
  3. 检查 09:09:00 前后 web 访问日志，确认是否有对应原始请求。
- **复测**：
  - 构造异常请求，确认日志仍完整记录所有必填字段。
  - 畸形记录应触发采集管道告警。

#### 信息（Info）— 正常登录

- **事件**：`login_success`（alice）
- **证据**：第 1 行 `2026-08-12T09:00:12Z,web,info,login_success,alice,192.0.2.10`
- **分析**：未见异常，记录为基线正常行为。

### 攻击链时间线

```
09:03:45  198.51.100.23  admin 登录失败 #1
09:03:49  198.51.100.23  admin 登录失败 #2（间隔 4s，疑似爆破）
09:04:02  203.0.113.8    service-a 令牌 scope 不匹配（高危）
          ↓ 约 3 分 28 秒
09:07:30  203.0.113.8    unknown 用户执行 DB 未预期导出（严重）
09:09:00  web            畸形日志记录（低危，可能为干扰或痕迹掩盖）
```

**核心链路**：`203.0.113.8` 的 scope 不匹配事件与数据导出事件强关联（同 IP、短时间、前者高危后者严重），应作为本次最高优先级处置项。

---

## 五、阻断说明：Skill 专项分析无法完成

### 阻断原因

严格依据 `SKILL.md`，本 Skill 的执行存在以下不可逾越的前置条件缺失：

1. **上游 orchestrator 未激活**（SKILL.md 第 8 行）：
   > "Use this skill only as a downstream specialization after `$ctf-sandbox-orchestrator` is already active and has established sandbox assumptions, node ownership, and evidence priorities. If that has not happened yet, return to `$ctf-sandbox-orchestrator` first."

   当前任务由用户直接发起，环境中不存在 `$ctf-sandbox-orchestrator`，也无沙箱假设、节点归属与证据优先级设定。按规则应先返回该 orchestrator，但该 Skill 在当前环境不可用。

2. **缺少声明契约工件**（Quick Start 第 1 步）：无 GraphQL schema、内省输出、persisted query id、RPC manifest、生成客户端、OpenAPI 文档。

3. **缺少实际请求形态**（Quick Start 第 2 步）：无 operation name、variables、method、path、headers、cookies、auth context。

4. **缺少 live handler 行为证据**（工作流第 2 步）：无真实请求/响应对、无 handler 分支或 fallback 行为记录。

因此，Skill 参考文件 `references/graphql-rpc-drift.md` 中定义的"Chain To Reconstruct"（声明契约识别 → 实际请求捕获 → handler 归一化/隐藏分支观察 → 漂移确认 → 能力复现）五步链**无法执行**，也无法产出"one accepted and one drifted request pair"与"minimal contract-to-handler sequence"。

### 未伪造声明

- 本报告未编造任何 schema、manifest、persisted query、handler 代码或请求/响应数据。
- 第四节中的风险分析仅基于 CSV 实际存在的 6 个字段，未引入外部凭据或平台数据。
- `token_scope_mismatch` 与契约漂移的概念关联仅作语义提示，**未作为已证实的漂移结论**。

### 恢复 Skill 专项分析所需输入

若需执行完整的 GraphQL/RPC 漂移分析，需补充：
- GraphQL schema 或内省结果、persisted query 映射表
- RPC manifest / OpenAPI 规范文档
- 生成客户端代码或请求构造逻辑
- 涉及 `service-a` 令牌的真实 HTTP 请求与响应（含 headers、cookies、status）
- 后端 handler 路由与鉴权中间件代码/配置
- 已激活的 `$ctf-sandbox-orchestrator` 沙箱环境

---

## 六、实际读取的 Skill 文件清单

以下为本次实际读取的 Skill 文件（相对工作目录的路径）：

1. `competition-graphql-rpc-drift/competition-graphql-rpc-drift/SKILL.md`
2. `competition-graphql-rpc-drift/competition-graphql-rpc-drift/references/graphql-rpc-drift.md`
3. `competition-graphql-rpc-drift/competition-graphql-rpc-drift/agents/openai.yaml`

输入数据文件：`incident_log.csv`

---

## 七、影响结果的 SKILL.md 规则

最直接影响本次结果的规则是 **SKILL.md 第 8 行的前置门控规则**：

> "Use this skill only as a downstream specialization after `$ctf-sandbox-orchestrator` is already active and has established sandbox assumptions, node ownership, and evidence priorities. If that has not happened yet, return to `$ctf-sandbox-orchestrator` first."

该规则直接导致 Skill 定义的 GraphQL/RPC 契约漂移专项工作流无法启动——因为上游 orchestrator 不存在，且输入中无任何契约工件与 live handler 流量。本报告据此如实标注阻断，而非伪造漂移分析结果。

此外，**Quick Start 第 1 步**"Collect the declared contract surface first"与**第 4 步**"Preserve one accepted operation and one drifted or hidden operation"也因缺少对应输入而无法满足，进一步确认了专项分析的阻断状态。

---

## 八、处置优先级建议

| 优先级 | 事项 | 负责侧 |
|---|---|---|
| P0 | 吊销/轮换 service-a 令牌，阻断 203.0.113.8，核查 DB 导出范围 | 安全 + DBA |
| P0 | 确认 unknown 导出的数据内容，评估数据泄露影响 | 安全 + 业务 |
| P1 | scope 校验改为 deny-by-default，网关与服务端双重校验 | 后端 |
| P1 | admin 账号启用 MFA 与登录锁定策略 | 安全 + IT |
| P2 | 修复日志采集管道，增加必填字段校验与死信告警 | 平台 |
| P2 | 补充契约工件后重新执行 Skill 漂移专项分析 | 安全 |
