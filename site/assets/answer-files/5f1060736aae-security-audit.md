# 安全日志分析报告（security-audit.md）

- 分析对象：`incident_log.csv`（模拟安全日志，共 6 条记录）
- 分析范围：仅对授权提供的日志文件进行静态分析；不进行任何在线探测、漏洞利用或破坏性操作
- 执行依据：`competition-web-runtime` Skill（SKILL.md 及其 references）
- 分析时间：2026-08-13

---

## 一、最小可验证版本（关键步骤与验收标准）

### 关键步骤

1. **映射运行时**：从日志的 `system` 字段识别出三个活跃组件——`web`（前端/登录层）、`api`（接口层）、`db`（数据层），以及涉及的身份主体 `alice`、`admin`、`service-a`、`unknown` 和来源 IP `192.0.2.10`、`198.51.100.23`、`203.0.113.8`。
2. **捕获真实事件顺序**：按时间戳排列全部 6 条记录，定位"改变结论的那一条"——`db` 层 `unexpected_export`（critical）。
3. **证实一条完整路径后再扩展**：以 `203.0.113.8` 为线索，将 `api` 层 `token_scope_mismatch`（high）与 `db` 层 `unexpected_export`（critical）关联为同一攻击链；随后再扩展分析 `198.51.100.23` 的管理员登录失败与末尾畸形记录。
4. **证据打包**：保留原始日志行、时间戳、IP、用户、事件类型，不做无依据推断。
5. **输出分级、修复建议与复测清单**。

### 验收标准

- [x] 每条风险均有日志原文作为证据（精确到时间戳与字段值）
- [x] 攻击链按时间顺序闭环（同一来源 IP 跨组件串联）
- [x] 风险分级与日志 `severity` 字段及跨组件影响一致
- [x] 修复建议对应到具体事件，复测清单可逐条执行
- [x] 未实施任何破坏性操作，未伪造日志中不存在的凭据/Cookie/请求体
- [x] 无法从日志确认的内容明确标注为"待验证假设"，不作为定论

---

## 二、运行时映射（Map The Active Runtime）

| 组件 (system) | 角色推断 | 日志中出现的事件 |
|---|---|---|
| web | 前端/登录入口 | login_success、login_failed、malformed_record |
| api | 后端接口层（服务间调用） | token_scope_mismatch |
| db | 数据层 | unexpected_export |

**涉及身份与来源**：

| 主体 | 来源 IP | 说明 |
|---|---|---|
| alice | 192.0.2.10 | 正常登录用户 |
| admin | 198.51.100.23 | 被尝试登录的管理员账号（登录失败） |
| service-a | 203.0.113.8 | 服务账号，出现 token 权限范围不匹配 |
| unknown | 203.0.113.8 | 未识别身份，执行了数据导出 |

> 说明：日志中未出现 Cookie 名、路由名、存储键、队列名或具体请求/响应头，因此运行时映射仅基于 CSV 已有字段，不臆造不存在的运行时细节。

---

## 三、真实事件顺序（Capture The Real Request Order）

按时间戳排列的完整事件流：

| # | 时间 (UTC) | system | severity | event | user | source_ip |
|---|---|---|---|---|---|---|
| 1 | 09:00:12 | web | info | login_success | alice | 192.0.2.10 |
| 2 | 09:03:45 | web | warning | login_failed | admin | 198.51.100.23 |
| 3 | 09:03:49 | web | warning | login_failed | admin | 198.51.100.23 |
| 4 | 09:04:02 | api | high | token_scope_mismatch | service-a | 203.0.113.8 |
| 5 | 09:07:30 | db | critical | unexpected_export | unknown | 203.0.113.8 |
| 6 | 09:09:00 | web | （空） | malformed_record | （空） | （空） |

### 已证实的攻击链（同一来源 IP 跨组件）

```
203.0.113.8
  │
  ├─ 09:04:02  api  token_scope_mismatch (service-a)   ← 权限范围异常，疑似越权/token 滥用
  │
  └─ 09:07:30  db   unexpected_export (unknown)        ← 约 3 分 28 秒后，未识别身份导出数据
```

**结论性事件**：第 5 条 `db / critical / unexpected_export`。该事件表明数据层发生了非预期导出，且执行者身份为 `unknown`，与 3 分 28 秒前同一 IP 的 API 层权限异常直接关联。按 SKILL.md"UI 限制只是提示，不能证明后端强制执行"的原则——`web` 层的登录失败不能证明攻击者未通过其他路径进入；`api`→`db` 这条链证明后端授权边界已被绕过。

### 其他需关注事件

- **第 2、3 条**：`198.51.100.23` 在 4 秒内连续两次对 `admin` 账号登录失败，特征符合针对管理员账号的口令猜测/撞库尝试，但次数少、未成功，且与后续攻击链 IP 不同，暂定为独立事件。
- **第 6 条**：`malformed_record`，且 severity/user/source_ip 字段均为空。可能是日志注入/篡改尝试，或日志采集管道异常，需核实日志完整性。

---

## 四、风险分级

| 编号 | 风险 | 等级 | 受影响组件 | 状态 |
|---|---|---|---|---|
| R1 | 未授权数据导出（数据外泄） | **严重 (Critical)** | db | 已发生 |
| R2 | API Token 权限范围不匹配导致越权访问 | **高 (High)** | api | 已发生，与 R1 同源 |
| R3 | 管理员账号口令猜测/撞库 | **中 (Medium)** | web | 尝试中，未成功 |
| R4 | 日志记录畸形/日志完整性存疑 | **中 (Medium)** | web / 日志管道 | 待核实 |
| R5 | 正常用户登录（基线事件） | 信息 (Info) | web | 正常 |

### R1：未授权数据导出（严重）

- **证据**：`2026-08-12T09:07:30Z,db,critical,unexpected_export,unknown,203.0.113.8`
- **分析**：数据层发生非预期导出，执行者身份为 `unknown`（未认证/未识别），来源 IP 与 3 分 28 秒前的 API 权限异常事件相同。这是实际发生的数据外泄事件，影响数据机密性。
- **待验证假设（非定论）**：Skill 参考文档 `references/cookie-hmac-key-reuse-auth-bypass.md` 描述了"URL 中公开 access token 被复用为 Cookie 签名密钥→伪造管理员身份→后台绕过"的攻击模式，其最终效果（越权访问后台/数据）与 `token_scope_mismatch → unexpected_export` 链在表象上吻合。但当前 CSV 不含 Cookie、token、请求头或请求体，**无法确认是否为该具体手法**；需在授权环境下抓取完整请求/响应后才能验证。

### R2：API Token 权限范围不匹配（高）

- **证据**：`2026-08-12T09:04:02Z,api,high,token_scope_mismatch,service-a,203.0.113.8`
- **分析**：服务账号 `service-a` 使用的 token 权限范围与所请求资源不匹配，说明存在越权尝试或 token 配置/签发错误。该事件是 R1 的前置步骤，同一 IP 在短时间内从 API 越权推进到 DB 导出，构成完整攻击链。

### R3：管理员账号口令猜测（中）

- **证据**：
  - `2026-08-12T09:03:45Z,web,warning,login_failed,admin,198.51.100.23`
  - `2026-08-12T09:03:49Z,web,warning,login_failed,admin,198.51.100.23`
- **分析**：4 秒内两次失败登录，目标为 `admin`。样本量小，未达典型暴力破解规模，但具备针对性。与 R1/R2 来源 IP 不同，不作为同一攻击链，但需监控是否升级。

### R4：日志畸形/完整性存疑（中）

- **证据**：`2026-08-12T09:09:00Z,web,,malformed_record,,`
- **分析**：severity、user、source_ip 字段为空。两种可能：(a) 日志注入/篡改以掩盖痕迹（发生在数据导出后约 1 分 30 秒，时间上可疑）；(b) 日志采集/解析管道故障。需结合日志服务端原始记录核实，不能仅凭此行判定篡改。

---

## 五、修复建议

### R1 / R2：授权边界与数据导出

1. **立即处置**：吊销/轮换 `service-a` 及同 IP 相关 token；审计 2026-08-12 09:04–09:10 期间 `203.0.113.8` 的所有 API/DB 操作，确认导出数据范围并评估通报义务。
2. **服务端强制授权**：后台权限基于服务端 session/会话状态判定，不得信任客户端 Cookie payload 中的权限声明字段（如 `admin:true`）；接口层与数据层均执行独立的权限校验，不依赖单层网关。
3. **签名密钥隔离**：Cookie/Token 签名使用服务端独立密钥，不得与 URL 中公开的 access token 复用；不同角色使用不同密钥；Cookie 中加入 `iat`/`exp`/`typ` 并严格校验。（对应参考文档"修复方案"）
4. **导出操作管控**：数据导出需二次鉴权与审批，限制可导出范围，对 `unknown`/未认证主体的导出请求默认拒绝并告警。
5. **异常静默处理**：签名/Token 解析失败返回 401，不返回 500 或错误详情，避免泄露实现信息。

### R3：管理员登录防护

1. 对 `admin` 等特权账号启用多因素认证（MFA）。
2. 配置登录失败阈值与临时锁定/限速，对 `198.51.100.23` 类来源加入监控名单。
3. 特权账号禁止公网直接登录，改用堡垒机/VPN。

### R4：日志完整性

1. 核对日志服务端原始记录，确认第 6 行是写入时即畸形还是采集管道截断。
2. 日志字段增加服务端校验，缺失关键字段（severity/user/source_ip）的记录单独标记并告警。
3. 关键日志启用防篡改（追加写入/集中存储/完整性校验），防止攻击者通过日志注入掩盖痕迹。

---

## 六、复测清单

| # | 复测项 | 预期结果 | 优先级 |
|---|---|---|---|
| 1 | 使用权限不足的 token 调用越权 API（复现 token_scope_mismatch） | 请求被拒绝（403），且不产生后续 DB 操作 | P0 |
| 2 | 以未认证/unknown 身份请求数据导出接口 | 请求被拒绝（401/403），db 层无导出记录 | P0 |
| 3 | 检查 Cookie 签名密钥是否与 URL access token 独立 | 二者不同；不同角色使用不同密钥；Cookie 含 exp 且过期失效 | P0 |
| 4 | 伪造含 `admin:true` 的 Cookie/payload 访问后台 | 被拒绝，无法获得管理员权限 | P0 |
| 5 | 连续失败登录 admin 账号 | 触发限速/锁定/告警，无 MFA 不可登录 | P1 |
| 6 | 构造缺字段的畸形日志写入 | 日志管道标记异常并告警，原始记录可追溯 | P1 |
| 7 | 审计 09:04–09:10 期间 203.0.113.8 全量操作 | 完整还原攻击路径与外泄数据范围 | P0 |
| 8 | 验证 token 解析失败时的响应码 | 返回 401，不返回 500 或堆栈信息 | P2 |

---

## 七、范围与限制

1. 本报告仅基于 `incident_log.csv` 的 6 条记录做静态分析，未连接任何在线系统，未实施任何利用或破坏性操作。
2. 日志中无 Cookie、Token、请求/响应头、请求体、路由名等细节，因此无法确认具体漏洞手法；参考文档中的 HMAC 密钥复用模式仅为"与现象吻合的待验证假设"，需在授权环境抓取完整请求流后确认。
3. IP `198.51.100.23`（R3）与 `203.0.113.8`（R1/R2）不同，日志中无证据表明二者关联，不做合并归因。
4. 第 6 条畸形记录不能单独证明日志篡改，已标注为待核实。

---

## 八、实际读取的 Skill 文件

- `competition-web-runtime/SKILL.md`（主文件，63 行）
- `competition-web-runtime/references/routing-runtime.md`（路由与运行时检查清单）
- `competition-web-runtime/references/cookie-hmac-key-reuse-auth-bypass.md`（Cookie HMAC 密钥复用→认证绕过参考）
- `competition-web-runtime/agents/openai.yaml`（接口配置）

（以上路径相对于解压后的 Skill 根目录 `competition-web-runtime/competition-web-runtime/`）

---

## 九、影响结果的 SKILL.md 规则

**"Treat UI gating as a hint, not proof of backend enforcement."（UI 层限制只是提示，不能证明后端强制执行。）**

这条规则直接影响了结论：日志中 `web` 层虽有两次 `admin` 登录失败，但不能据此认定攻击者被完全阻挡。同一时间窗内，`203.0.113.8` 经 `api` 层 `token_scope_mismatch` 推进到 `db` 层 `unexpected_export`，证明后端授权边界在 API/DB 路径被绕过。若只看 web 登录失败就判定"攻击未成功"，将漏掉严重的数据外泄事件。

此外，SKILL.md 的"Capture one real request flow end-to-end before making broad claims"（先端到端证实一条完整流再下结论）要求以同一 IP 串联跨组件事件作为证据链，而非孤立解读单条日志；"What To Preserve"要求保留精确请求/响应与具体标识，本报告据此逐条引用原始日志行作为证据。
