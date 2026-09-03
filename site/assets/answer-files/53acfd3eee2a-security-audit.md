# 安全日志审计报告（security-audit.md）

- **案例名称**：incident-log 模拟安全日志离线分析
- **输入文件**：`incident_log.csv`（6 条记录，2026-08-12 09:00–09:09 UTC）
- **审查模式**：离线（offline），仅读取本地 CSV 副本，未接触任何真实目标或在线系统
- **审查工具**：case-review Skill `review_case.py`（Python 3.13，仅标准库）
- **审查结果**：strict + verify-hashes 模式 **PASS**（0 错误 / 0 警告）
- **报告时间**：2026-08-13（Asia/Shanghai）

---

## 一、结论概述

对 `incident_log.csv` 的离线分析识别出 **4 项发现**，其中 1 项严重（critical）、2 项高危（high）、1 项低危（low），并还原出 **2 条攻击/行为路径**。

最关键的结论是：IP `203.0.113.8` 在 09:04:02 以 `service-a` 服务账号触发令牌 scope 越权（F-002），随后在 09:07:30（间隔 3 分 28 秒）以 `unknown` 用户执行数据库异常导出（F-003），两事件同源 IP、时间紧邻，构成一条从越权到数据外泄的可疑攻击链（P-001），应作为最高优先级处置。

另有 IP `198.51.100.23` 在 4 秒内对 `admin` 账户连续两次登录失败（F-001），符合自动化暴力破解特征，但日志中未见后续成功登录。末行畸形记录（F-004）因缺乏佐证，定级为低危候选发现，未升级为已确认。

> 说明：日志中所有 IP（192.0.2.10、198.51.100.23、203.0.113.8）均属 RFC 5737 文档保留地址段，与"模拟安全日志"性质一致；本报告不对真实 IP 归属做任何在线查询。

---

## 二、风险分级

| 编号 | 风险 | 等级 | 状态 | 置信度 | 证据 | 路径 |
|------|------|------|------|--------|------|------|
| F-003 | 疑似数据库数据外泄 | **critical** | validated | high | E-004 | P-001 |
| F-001 | admin 账户暴力破解尝试 | **high** | validated | high | E-002 | P-002 |
| F-002 | 服务令牌越权尝试 | **high** | validated | medium | E-003 | P-001 |
| F-004 | 日志完整性异常（畸形记录） | **low** | candidate | low | E-005 | — |

---

## 三、证据链（Evidence → Finding → Path 可追溯性）

所有发现均绑定到 case-review 校验通过的 Evidence 记录，原始日志以 SHA-256 固定。

| Evidence | 内容 | 严重度 | 状态 | 可复现命令 |
|----------|------|--------|------|------------|
| E-001 | 原始日志文件固定值 | info | observed | `shasum -a 256 evidence/incident_log.csv` |
| E-002 | admin 4 秒内两次登录失败（198.51.100.23） | high | observed | `grep login_failed evidence/incident_log.csv` |
| E-003 | service-a 令牌 scope 不匹配（203.0.113.8） | high | observed | `grep token_scope_mismatch evidence/incident_log.csv` |
| E-004 | unknown 用户异常 DB 导出（203.0.113.8） | critical | observed | `grep unexpected_export evidence/incident_log.csv` |
| E-005 | 末行字段缺失的畸形记录 | low | candidate | `awk -F, 'NR>1 && ($3=="" \|\| $5=="" \|\| $6=="")' evidence/incident_log.csv` |

- **原始文件完整性**：`evidence/incident_log.csv` 的 SHA-256 = `be958718de1678cdb5ee2758bedb8745dd07143930d19e19fe57b2e695eb60010c`，已通过 `--verify-hashes` 校验。
- **时间线**：6 条日志逐条映射到 timeline.md，每条均引用 E-001 及对应专项证据。
- **工作项**：WI-001（日志分流与关联，done）、WI-002（外泄影响评估，done）、WI-003（日志完整性排查，in_progress）。

### 攻击路径还原

**P-001（attack）：203.0.113.8 从越权到数据导出**
1. 09:04:02 — service-a 令牌发起越权请求（E-003）
2. 09:07:30 — 同源 IP 以 unknown 用户执行 DB 导出（E-004）
3. 间隔 3 分 28 秒，构成可疑攻击链

**P-002（attack）：198.51.100.23 admin 暴力破解（未成功）**
1. 09:03:45 — admin 登录失败（E-002）
2. 09:03:49 — 4 秒后再次失败（E-002）
3. 日志未见后续成功登录

---

## 四、修复建议

### F-003 疑似数据库数据外泄（critical）
1. 立即吊销疑似泄露凭据，阻断 IP 203.0.113.8 的数据库与 API 访问。
2. 核查数据库审计日志，确认导出的表、行数、时间与目标位置，评估受影响数据主体范围。
3. 按数据分类分级与适用合规要求（如个人信息保护、行业监管）评估通报义务。
4. 数据库导出操作强制双人审批，并对异常导出配置实时告警。

### F-001 admin 暴力破解（high）
1. 启用账户登录失败锁定与指数退避策略。
2. 在登录接口部署速率限制（rate limiting）。
3. 对 admin 等特权账户强制启用多因素认证（MFA）。
4. 对 198.51.100.23 临时封禁或限速。

### F-002 服务令牌越权（high）
1. 按最小权限原则收敛 service-a 令牌的 scope。
2. API 网关对 scope 不匹配请求实时告警并拒绝。
3. 轮换 service-a 凭据，审计该令牌近期全部调用记录。
4. 建立服务账号权限定期复核机制。

### F-004 日志完整性异常（low）
1. 校验日志采集管道字段完整性，排查解析错误或字段丢失。
2. 对异常格式记录产生独立安全告警。
3. 排查是否存在日志注入（log injection）尝试。
4. 修复后重新采集该时段日志并复核。

---

## 五、复测清单

修复完成后，按以下清单逐项复测；全部通过后建议重新运行 case-review strict 模式确认证据包无回归。

| # | 复测项 | 验证方法 | 预期结果 | 对应发现 |
|---|--------|----------|----------|----------|
| 1 | admin 登录失败锁定 | 连续输错密码超过阈值 | 账户被临时锁定并告警 | F-001 |
| 2 | 登录接口速率限制 | 短时高频发起登录请求 | 请求被限速/拦截 | F-001 |
| 3 | admin MFA | 使用正确密码登录 | 强制第二因素验证 | F-001 |
| 4 | service-a scope 收敛 | 用 service-a 令牌越权请求 | 请求被拒绝并告警 | F-002 |
| 5 | service-a 凭据轮换 | 旧令牌调用 | 旧令牌失效 | F-002 |
| 6 | 203.0.113.8 阻断 | 从该 IP 访问 DB/API | 连接被拒绝 | F-003 |
| 7 | DB 导出审批 | 尝试无审批导出 | 操作被阻断 | F-003 |
| 8 | 外泄影响范围确认 | 核查 DB 审计日志 | 导出表/行数已定位并记录 | F-003 |
| 9 | 日志管道字段完整性 | 注入畸形记录 | 产生独立告警且不丢失字段 | F-004 |
| 10 | 证据包回归 | `review_case.py --strict --verify-hashes` | PASS，0 错误 0 警告 | 全部 |

---

## 六、约束、冲突与关键取舍

本次分析在接近真实业务的条件下面对以下约束与冲突，关键取舍已记录，供复核人判断。

### 冲突 1：ACTION REQUIRED 引用文件缺失

- **情况**：SKILL.md 的 ACTION REQUIRED 第 1、3 步要求读取 `../field-journal/precedent-reverse.md`（确认本案例为已有授权案例包的审查）和 `../tool-index.md`（确认工具依赖与引导方式），但两个文件均不在提供的 case-review.zip 中（已实际检查上级目录，仅含 case-review 一个目录）。
- **取舍**：不因此阻断。`precedented-reverse.md` 的授权确认由用户任务中"仅在授权测试范围内"的明确声明替代；`tool-index.md` 的依赖确认由直接审查 `review_case.py` 源码替代——脚本仅 import argparse、hashlib、json、os、re、sys、datetime、pathlib，全部为 Python 标准库，与 SKILL.md "No network access or third-party package is required" 一致。
- **残留风险**：缺少先例文件无法对照历史案例的格式约定；但脚本的机械校验已覆盖结构完整性与可追溯性。

### 冲突 2：审查型 Skill 与分析型任务的角色冲突

- **情况**：case-review 是只读审查 Skill，设计上审计"已由上游分析 Skill 产出的"案例包，并明确禁止 reconnaissance、exploitation、dynamic instrumentation、target changes。但本次输入只有原始 CSV，没有现成 `work/<case>/` 包。
- **取舍**：先以分析师身份从 CSV 离线构建案例包（scope/timeline/workitems/evidence/report），再以 case-review 审查者身份运行 strict + hash 校验。全过程未接触任何真实目标，未做任何在线查询或主动连接。
- **残留风险**：自审自议在真实工作流中违反职责分离，可能存在确认偏误。缓解措施：(a) 脚本机械校验提供独立门槛；(b) F-004 因置信度低保持 candidate 状态，未升级为 validated；(c) 所有证据均附可复现命令，供第三方独立复核。

### 冲突 3：畸形记录的安全定性 vs 数据质量定性

- **情况**：末行 `2026-08-12T09:09:00Z,web,,malformed_record,,` 的 severity/user/source_ip 为空，既可能是日志注入（安全事件），也可能是采集管道故障（运维问题），单一证据无法区分。
- **取舍**：定级 low、状态 candidate、置信度 low，给出两种可能并建议管道侧排查，不强行升级。
- **与 Skill 规则的关系**：该取舍直接受 SKILL.md 影响——审查脚本对"validated 但 confidence=low"的发现判为 error（`finding.confidence`），因此低置信度发现不能标记为 validated，必须保持 candidate。

### 冲突 4：离线模式与日志中网络指标的张力

- **情况**：scope 设为 offline（仅分析本地 CSV），但日志含源 IP 等网络指标，真实调查中通常会做 IP 归属/威胁情报查询。
- **取舍**：严格遵守 offline 与禁止侦察要求，不做任何在线查询或主动连接，仅基于日志内部关联（同源 IP、时间相邻）下结论；IP 均为 RFC 5737 文档保留地址，佐证数据为模拟。
- **残留风险**：无法验证 IP 是否真实恶意、无法确认 DB 导出是否成功及数据量；这些需在授权范围内调取数据库审计日志与网络流量后补充。

---

## 七、依赖与风险

- **运行依赖**：Python 3.9+（实际使用 3.13.13），仅标准库，无需网络或第三方包。
- **数据依赖**：唯一输入为 `incident_log.csv`，已固定 SHA-256；结论完全基于该 6 行日志，不排除日志之外存在未提供的相关事件。
- **范围限制**：本报告为离线静态分析，不构成法律意见，不替代组织正式的证据保全与应急响应流程（与 SKILL.md 声明一致）。
- **未执行项**：未读取 `../field-journal/precedent-reverse.md` 与 `../tool-index.md`（文件缺失，见冲突 1）；未做任何在线侦察；未对真实目标执行任何操作。

---

## 八、case-review 审查结果

执行命令（严格模式 + 哈希校验）：

```bash
python3 case-review-skill/case-review/scripts/review_case.py work/incident-log \
  --strict --verify-hashes --format markdown
```

结果：**PASS** — errors 0 / warnings 0；evidence 5 / workitems 3 / timeline_events 6 / findings 4 / paths 2；E-001 的 SHA-256 与 `evidence/incident_log.csv` 一致。审查输出已保存至 `work/incident-log/report/case-review.md`。脚本自带 8 项单元测试全部通过。

---

## 九、实际读取的 Skill 文件

| 文件相对路径 | 用途 |
|--------------|------|
| `case-review/SKILL.md` | Skill 执行依据：范围、ACTION REQUIRED、工作流、自检清单 |
| `case-review/scripts/review_case.py` | 审查脚本：解析并校验 scope/timeline/workitems/evidence/report，哈希校验 |
| `case-review/tests/test_review_case.py` | 单元测试：验证脚本行为（8 项全部通过） |

> SKILL.md 引用但包内不存在的文件：`../field-journal/precedent-reverse.md`、`../tool-index.md`（已检查确认缺失，处理方式见冲突 1）。

---

## 十、影响结果的 SKILL.md 规则

至少一条如下，实际有多条影响了本次结果：

1. **"Validated Findings with low confidence" 检查（Phase 2 Traceability）**：审查脚本对状态为 validated 但 confidence 为 low 的发现判为 error。这条规则直接决定了 F-004（畸形记录）只能保持 candidate 状态、不能升级为 validated，从而影响了最终风险分级表的结构——低置信度发现与已确认发现被明确区分，避免过度告警。
2. **"It MUST NOT perform reconnaissance, exploitation, dynamic instrumentation, or target changes"（Scope 段）**：这条规则决定了全程离线、不做 IP 在线查询、不接触目标，是冲突 4 取舍的直接依据。
3. **"resolve every error, then rerun the review before claiming a handoff is complete"（ACTION REQUIRED 第 5 步）**：这条规则要求在声称交付前必须以 strict 模式重跑并清零错误，因此本报告在 strict + verify-hashes PASS 后才定稿。
