# 安全审计报告 / Security Audit Report

- 案件名称：模拟安全日志事件审查（incident_log.csv）
- 审查日期：2026-08-13
- 审查模式：offline 只读静态分析（授权测试范围内）
- 证据文件 SHA-256：`be958718de1678cdb5ee2758bedb8745dd07143930d19efe57b2e695eb60010c`
- Case review 状态：**PASS**（strict 模式，0 errors / 0 warnings，哈希验证通过）

---

## 一、结论概述

对 `incident_log.csv`（共 6 条记录，时间跨度 2026-08-12T09:00:12Z ~ 09:09:00Z）的离线审查发现 **1 条严重、2 条高危、1 条中危** 安全问题，并识别出一条完整攻击链：

> 来源 IP `203.0.113.8` 先以服务账号 `service-a` 触发 Token 权限范围不匹配（疑似权限提升试探），约 3.5 分钟后以 `unknown` 用户从同一 IP 成功执行数据库异常导出，构成 **"权限试探 → 数据外泄"** 攻击链。

另有 `198.51.100.23` 对 `admin` 账号在 4 秒内连续 2 次登录失败，符合暴力破解特征；以及一条关键字段为空的畸形日志，影响审计可追溯性。

**本审查仅对本地模拟日志做只读分析，未执行任何侦察、利用、动态注入或目标变更操作。**

---

## 二、审查范围与授权

| 项目 | 内容 |
|------|------|
| 授权状态 | granted（授权测试范围内的模拟数据） |
| 网络模式 | offline（纯静态文件分析，无网络活动） |
| 范围内资产 | evidence/incident_log.csv |
| 禁止事项 | 不接触真实目标、不执行破坏性操作 |

---

## 三、风险分级

| 编号 | 风险 | 等级 | 置信度 | 来源证据 |
|------|------|------|--------|----------|
| F-003 | 未知用户执行数据库异常导出（疑似数据外泄） | **严重 / critical** | high | E-004, E-003 |
| F-001 | admin 账号遭暴力破解/密码喷洒 | **高 / high** | high | E-002 |
| F-002 | 服务账号 Token 权限范围不匹配（疑似权限提升） | **高 / high** | high | E-003 |
| F-004 | 日志记录关键字段为空（完整性/可追溯性缺陷） | **中 / medium** | medium | E-005 |

---

## 四、证据与时间线

| 时间 (UTC) | 系统 | 级别 | 事件 | 用户 | 来源 IP | 证据 ID |
|------------|------|------|------|------|---------|---------|
| 09:00:12 | web | info | login_success | alice | 192.0.2.10 | E-001 |
| 09:03:45 | web | warning | login_failed | admin | 198.51.100.23 | E-002 |
| 09:03:49 | web | warning | login_failed | admin | 198.51.100.23 | E-002 |
| 09:04:02 | api | high | token_scope_mismatch | service-a | 203.0.113.8 | E-003 |
| 09:07:30 | db | critical | unexpected_export | unknown | 203.0.113.8 | E-004 |
| 09:09:00 | web | — | malformed_record | （空） | （空） | E-005 |

### 证据可复现命令

| 证据 | 复现命令 |
|------|----------|
| E-001 | `grep 'login_success,alice' evidence/incident_log.csv` |
| E-002 | `grep 'login_failed,admin' evidence/incident_log.csv` |
| E-003 | `grep 'token_scope_mismatch' evidence/incident_log.csv` |
| E-004 | `grep 'unexpected_export' evidence/incident_log.csv` |
| E-005 | `awk -F',' 'NF<6 \|\| $3=="" \|\| $5=="" \|\| $6==""' evidence/incident_log.csv` |

---

## 五、攻击路径分析（P-001）

**路径类型：attack**

1. **E-003（09:04:02）**：`service-a` 的 Token 从 `203.0.113.8` 触发 `token_scope_mismatch`，疑似在试探/提升权限。
2. **E-004（09:07:30）**：同一 IP `203.0.113.8` 以 `unknown` 用户成功执行 `unexpected_export`，距上一事件约 3.5 分钟。
3. 两事件同源 IP、时间紧邻，构成 **"权限试探 → 数据外泄"** 攻击链。

**残余风险：**
- 单条日志无法确认导出数据的具体范围与量级；
- 无法确认攻击者是否通过其他通道持久化访问；
- 需结合数据库审计日志与网络流量进一步确认。

---

## 六、修复建议

### F-003 严重 — 数据库异常导出
1. 立即阻断 `203.0.113.8` 并隔离受影响数据库账号；
2. 核查导出操作的数据集、时间范围与数据量，评估泄露面；
3. 轮换数据库凭据与相关 API Token；
4. 启动数据泄露应急响应流程，按法规要求评估通报义务；
5. 对数据库导出操作增加审批与二次认证。

### F-001 高危 — admin 暴力破解
1. 对 admin 账号启用账户锁定或指数退避策略；
2. 部署多因素认证（MFA）；
3. 对 `198.51.100.23` 实施临时封禁并加入监控黑名单；
4. 审查 admin 账号是否存在弱口令并强制重置。

### F-002 高危 — Token 权限不匹配
1. 立即吊销并轮换 `service-a` 的 Token；
2. 审计 `service-a` 近期所有 API 调用，确认是否有越权访问成功记录；
3. 强化 Token scope 最小权限校验，拒绝不匹配请求并告警；
4. 排查 `203.0.113.8` 的访问历史与归属。

### F-004 中危 — 日志完整性缺陷
1. 在日志采集端增加字段非空校验与格式校验，拒绝或隔离畸形记录；
2. 调查该记录产生原因（采集 bug 还是注入尝试）；
3. 建立日志完整性监控与告警。

---

## 七、复测清单

| 序号 | 复测项 | 验证方法 | 通过标准 |
|------|--------|----------|----------|
| 1 | `203.0.113.8` 是否已阻断 | 检查防火墙/WAF 黑名单 | 该 IP 无法访问 api 与 db |
| 2 | `service-a` Token 是否已轮换 | 检查旧 Token 是否失效 | 旧 Token 请求返回 401 |
| 3 | 数据库导出是否已加审批 | 尝试无审批导出 | 被拒绝并产生告警 |
| 4 | admin 账号是否启用 MFA/锁定 | 连续失败登录测试 | 触发锁定或要求 MFA |
| 5 | `198.51.100.23` 是否被封禁 | 从该 IP 发起连接 | 连接被拒绝 |
| 6 | 日志采集是否拒绝空字段 | 注入一条缺字段记录 | 记录被拒绝或隔离并告警 |
| 7 | 数据泄露面是否已评估 | 核查数据库审计日志 | 出具导出数据范围报告 |
| 8 | 所有凭据是否已轮换 | 检查凭据轮换记录 | db 密码、API Token 均已更新 |

---

## 八、Case Review 结果（strict 模式）

审查工具：`scripts/review_case.py`（Python 3 标准库，只读）

```
status: PASS
errors: 0
warnings: 0
evidence: 5
workitems: 4
timeline_events: 6
findings: 4
paths: 1
hash verification: 通过（SHA-256 一致）
```

证据可追溯性矩阵：

| Evidence | Work items | Timeline | Reports |
|----------|-----------:|---------:|--------:|
| E-001 | 1 | 1 | 0 |
| E-002 | 1 | 2 | 1 |
| E-003 | 1 | 1 | 3 |
| E-004 | 1 | 1 | 2 |
| E-005 | 1 | 1 | 1 |

---

## 九、关键步骤与验收标准（最小可验证版本）

| 步骤 | 内容 | 验收标准 |
|------|------|----------|
| 1 | 读取 SKILL.md，确认只读审查模式与 offline 范围 | 已确认 scope.md：auth=granted, mode=offline |
| 2 | 从 incident_log.csv 提取 5 条证据并计算 SHA-256 | 5 个 E-*.md，哈希与文件一致 |
| 3 | 建立时间线与工作项，绑定证据 ID | timeline 6 事件、workitems 4 项，无悬空引用 |
| 4 | 形成 4 条 Finding 与 1 条攻击 Path | 每条 Finding 均引用现存 Evidence，Path 含合法 path_type |
| 5 | 运行 review_case.py --strict --verify-hashes | status=PASS，0 errors，0 warnings |
| 6 | 输出风险分级、修复建议、复测清单 | 本报告第三、六、七节完整 |

---

## 十、限制声明

- 本报告基于单份模拟日志文件的静态分析，不构成法律意见，不替代组织证据管理流程；
- SKILL.md 引用的 `../field-journal/precedent-reverse.md` 与 `../tool-index.md` 未包含在随附 ZIP 中；SKILL.md 已明确本 Skill 仅依赖 Python 3 标准库、无需 bootstrap，且本次为 offline 只读审查，上述文件缺失不影响审查结论；
- 所有 IP（192.0.2.10、198.51.100.23、203.0.113.8）均属文档保留地址段（RFC 5737/5735），为模拟数据。
