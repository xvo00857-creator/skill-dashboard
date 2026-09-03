# 安全审计报告 — cloud-k8s Skill 模拟日志分析

- 报告日期：2026-08-13（Asia/Shanghai）
- 审计 Skill：`cloud-k8s`（分类：安全与合规）
- 输入文件：`incident_log.csv`、`edge_cases.csv`
- 审计方式：**离线、只读**日志分析；未连接任何云账号/K8s 集群，未执行扫描或破坏性操作
- 授权边界：依据任务方明确声明"仅在授权测试范围内分析模拟安全日志"，限定于随附两个 CSV 文件

---

## 0. 执行依据与边界声明（按 SKILL.md ACTION REQUIRED）

1. **书面授权先例文件缺失（影响流程合规）**：SKILL.md 第 10 行 `ACTION REQUIRED` 第 1 条要求"`NOW`: 读取 `../field-journal/precedent-pentest.md` — 云/K8s 测试必须书面授权"。随附 ZIP 中**不存在**该文件（`cloud-k8s-skill/field-journal/precedent-pentest.md` 缺失），因此无法读取历史书面授权先例。本次审计的授权依据降级为：任务方在需求中对范围的书面声明（仅分析随附模拟日志、禁止破坏性操作），且输入中**不含任何真实云账号、集群地址或凭据**，故无越权目标可触达。
2. **范围确认（SKILL.md 第 12 行）**：输入以 web/api/db 应用日志为主，仅 1 条 IAM 相关事件（`token_scope_mismatch`）；**不含**云元数据 IMDS、容器运行时、K8s audit/RBAC/Pod 等遥测。因此 Skill 清单中 IMDS、K8s 高危、容器逃逸等检查项**无证据可评估**（见第 4 节），不臆造结论。
3. **网络档**：`authorized_target_only`。日志中出现的 IP（192.0.2.10、198.51.100.23、203.0.113.8）均属 RFC 5737 文档保留段（TEST-NET-1/2/3），为模拟/脱敏数据，不可路由。遵守 SKILL.md"禁止默认全网扫描""MUST NOT 未授权扫公有云其他租户"，**未对任何 IP 进行探测、扫描或连接**。
4. **工具链**：`kubectl/aws/gcloud/trivy/kube-bench` 本机均未安装（SKILL.md 标注多为"手动"自举）；本次为离线分析，无需上述工具，且无授权目标可用。
5. **其他被引用但缺失的 Skill 路径**：`../supply-chain-security/`、`../pentest-tools/`、`../../CTF-Sandbox-Orchestrator/competition-agent-cloud/` 均未随包提供，不影响本次日志分析。

**实际读取的 Skill 文件（相对路径）**：
- `cloud-k8s/SKILL.md`
- `cloud-k8s/references/k8s-cloud-checklist.md`

---

## 1. 风险分级总览

| 编号 | 等级 | 来源文件 | 问题 | 关键证据 |
|------|------|----------|------|----------|
| F-01 | 严重 | incident_log.csv | 疑似令牌越权→数据库外泄链 | 同一 IP 203.0.113.8 在 208 秒内先 `token_scope_mismatch`(high) 后 `unexpected_export`(critical) |
| F-02 | 中 | incident_log.csv | admin 账户暴力破解/撞库迹象 | 198.51.100.23 在 4 秒内两次 `login_failed`（admin） |
| F-03 | 中 | incident_log.csv | 日志记录畸形/关键字段缺失，归因失效 | 第 6 行 `severity/user/source_ip` 全空，事件名 `malformed_record` |
| F-04 | 中 | edge_cases.csv | CSV/电子表格公式注入（不安全输入） | record_id=5 的 value 以 `=` 开头：`=HYPERLINK("https://example.invalid","do not execute")` |
| F-05 | 低 | edge_cases.csv | 非标准 CSV 引号转义，严格解析器字段错位 | 第 7 行用 `\"` 转义，RFC 4180 解析得 5 列（表头 4 列） |
| F-06 | 低 | edge_cases.csv | 重复记录 | record_id=2 出现 2 次，内容完全相同 |
| F-07 | 低 | edge_cases.csv | 关键字段缺失 | record_id=3 的 status、value 均为空 |
| F-08 | 低 | edge_cases.csv | 异常负值/哨兵值 | record_id=4 为 error，value=-999 |

---

## 2. incident_log.csv 发现详情

数据规模：6 条记录，字段 `timestamp,system,severity,event,user,source_ip`。

### F-01【严重】疑似令牌越权 → 数据库未授权外泄链

- **证据**：
  - `2026-08-12T09:04:02Z, api, high, token_scope_mismatch, service-a, 203.0.113.8`
  - `2026-08-12T09:07:30Z, db, critical, unexpected_export, unknown, 203.0.113.8`
  - 两事件间隔 **208 秒**，**同一源 IP 203.0.113.8**；后者用户为 `unknown`（未认证/身份丢失）。
- **影响**：`service-a` 的令牌被用于超出其声明 scope 的操作（对应 SKILL.md Phase 2 云控制面"IAM 过度权限/角色可扮演（PassRole）与横向"及参考清单"返回的 IAM 角色权限面"）；3 分多钟后同一来源触发数据库"非预期导出"且身份为 unknown，构成**越权访问→数据外传**的攻击链假设，可能导致敏感数据泄露。
- **修复建议**：
  1. 立即吊销/轮换 `service-a` 令牌，审查其 IAM/Role 权限，按最小权限收敛 scope（禁止通配资源/动作）。
  2. 数据库导出操作强制认证与授权，禁止 `unknown`/匿名身份执行导出；导出走审批与工单。
  3. 建立跨系统关联规则：同一 source_ip 在短时间内出现 `token_scope_mismatch` 后接 `unexpected_export` 即触发高危告警。
  4. 排查 09:07:30 前后 DB 导出的具体内容、目标位置与影响面。
- **复测方法**：
  - 用旧 scope 令牌请求越权接口，预期返回 403；
  - 以未认证身份请求 DB 导出，预期被拒并产生告警；
  - 重放上述两条日志的时间窗关联，验证 SIEM 规则能命中 F-01。

### F-02【中】admin 账户暴力破解/撞库迹象

- **证据**：
  - `2026-08-12T09:03:45Z, web, warning, login_failed, admin, 198.51.100.23`
  - `2026-08-12T09:03:49Z, web, warning, login_failed, admin, 198.51.100.23`
  - 同一 IP 对 `admin` 账户在 **4 秒**内连续两次登录失败，呈自动化特征。
- **影响**：针对高权限账户的口令猜测/撞库；样本中仅 2 次，未成功，但属攻击前兆。
- **修复建议**：
  1. admin 账户启用 MFA，避免使用共享/默认 admin 名。
  2. 登录失败限速与临时锁定（如 5 次/5 分钟锁定），对 198.51.100.23 类来源加验证码/封禁。
  3. 告警阈值：单 IP 对单账户 N 次失败即报警。
- **复测方法**：脚本连续触发 5 次失败登录，验证锁定/告警生效；验证 MFA 强制开启。

### F-03【中】畸形日志记录，关键字段缺失（归因与检测失效）

- **证据**：
  - `2026-08-12T09:09:00Z, web, , malformed_record, , `
  - `severity`、`user`、`source_ip` 均为空字符串。
- **影响**：缺失归因字段使该事件无法关联身份/来源；可能是日志管道/解析器故障，也可能是攻击者制造噪声或尝试日志注入以掩盖痕迹；依赖这些字段的检测规则会漏判。
- **修复建议**：
  1. 日志接入层强制 schema 校验，`severity/user/source_ip` 等必填字段缺失则拒收或隔离。
  2. 对 `malformed_record` 及字段缺失率设独立告警，排查采集/解析链路。
  3. 日志存储启用追加写/防篡改（WORM），防止事后抹除来源。
- **复测方法**：构造缺字段的日志样例发送到采集端，验证被拒收/隔离并产生告警。

---

## 3. edge_cases.csv 发现详情

数据规模：6 条记录，字段 `record_id,status,value,notes`。

### F-04【中】CSV/电子表格公式注入（不安全输入处理）

- **证据**：record_id=5，`value` 字段为 `=HYPERLINK("https://example.invalid","do not execute")`（以 `=` 开头）。
- **影响**：该文件若被 Excel/WPS/LibreOffice 直接打开，公式可能被执行或诱导点击外链，属于 CSV 公式注入（Formula Injection）。尽管 notes 自述为"公式注入测试文本"，仍须按不安全输入处理。
- **修复建议**：
  1. 导出/展示 CSV 时，对以 `= + - @` 开头的单元格前置单引号 `'` 或去除危险前缀，强制按文本处理。
  2. 打开不可信 CSV 时关闭自动计算，不启用外链/宏。
  3. 接入侧对该类载荷做输入校验与转义。
- **复测方法**：将修复后的导出文件用电子表格软件打开，确认该单元格显示为文本且不触发公式/外链提示。

### F-05【低】非标准 CSV 引号转义（数据互操作风险）

- **证据**：第 7 行（record_id=5）原文使用反斜杠转义：`"=HYPERLINK(\"https://example.invalid\",\"do not execute\")"`。RFC 4180 标准应使用双写引号 `""`。
  - 严格 RFC 4180 解析器将该行解析为 **5 个字段**（表头为 4 个），字段错位；
  - 仅当解析器显式设置 `escapechar='\\'`（宽松模式）才能还原为 4 个字段。
- **影响**：不同解析器行为不一致，可能导致下游系统静默错列、丢字段或拒绝加载，影响数据完整性。
- **修复建议**：统一按 RFC 4180 重新导出（引号双写）；在数据契约中明确 dialect/转义规则。
- **复测方法**：用严格 RFC 4180 解析器逐行校验字段数，确认每行均为 4 列。

### F-06【低】重复记录

- **证据**：record_id=2 出现 2 次，两行均为 `2,ok,120,重复记录`。
- **影响**：重复数据会使统计/计数类指标虚高，影响审计准确性。
- **修复建议**：以 `record_id` 为主键去重，入库加唯一约束。
- **复测方法**：再次导入同 ID 重复行，验证被拒绝或自动合并。

### F-07【低】关键字段缺失

- **证据**：record_id=3 的 `status`、`value` 均为空，notes 为 `-`。
- **修复建议**：必填字段加 NOT NULL/非空校验，不完整记录进入隔离区。
- **复测方法**：提交空 status/value 的记录，验证返回校验错误。

### F-08【低】异常负值/哨兵值

- **证据**：record_id=4，`status=error`，`value=-999`。
- **影响**：-999 常被用作"缺失/错误"哨兵值；若该字段语义为非负度量，负值属越界异常，可能污染统计或掩盖真实错误。
- **修复建议**：明确定义 value 合法范围；将 -999 这类哨兵值显式映射为 null/缺失并记录原因，或触发异常告警。
- **复测方法**：提交 -999，验证按既定策略处理（置空/告警）而非参与数值计算。

---

## 4. cloud-k8s 检查清单覆盖情况（基于 references/k8s-cloud-checklist.md）

| 检查项 | 结论 | 说明 |
|--------|------|------|
| IMDS SSRF 是否可达 169.254.169.254 | **无法评估** | 输入中无 VPC/Pod/元数据访问日志，无实例信息 |
| 是否强制 IMDSv2 | **无法评估** | 无实例元数据配置/云审计日志 |
| 返回的 IAM 角色权限面 | **部分评估** | 仅 F-01 的 `token_scope_mismatch` 提示 scope 过宽；无 AK/SK、无角色列表可核 |
| cluster-admin 绑定过多 | **无法评估** | 无 RBAC/ClusterRoleBinding 数据 |
| secrets 明文环境变量 | **无法评估** | 无 Pod/Deployment 清单 |
| privileged + hostPID/hostPath 组合 | **无法评估** | 无容器安全上下文/宿主机挂载信息 |
| 匿名 auth / insecure apiserver 端口 | **无法评估** | 无 apiserver 配置/审计日志 |
| 容器以 root 运行 | **无法评估** | 无运行时/镜像数据 |
| 可加载内核模块 / docker.sock 挂载 | **无法评估** | 无容器挂载信息 |

**补齐云/K8s 评估所需的输入（建议后续提供）**：K8s audit log、`kubectl auth can-i --list` 与 ClusterRoleBinding 导出、Pod/Deployment 安全上下文、云厂商 IAM 凭据清单与 CloudTrail/操作日志、IMDS 配置与 VPC 流日志、镜像扫描结果（Trivy）。在获得书面授权与目标账号/集群后，方可按 SKILL.md Phase 2–4 执行实集评估。

---

## 5. 复测清单（汇总）

- [ ] F-01：旧 scope 令牌越权请求被拒；匿名 DB 导出被拒；跨系统同 IP 关联规则可命中。
- [ ] F-02：5 次失败登录触发锁定/告警；admin 强制 MFA。
- [ ] F-03：缺字段日志被接入层拒收/隔离并告警。
- [ ] F-04：含 `=+-@` 前缀的字段在电子表格中按文本显示，不执行公式/外链。
- [ ] F-05：严格 RFC 4180 解析器逐行校验字段数一致（4 列）。
- [ ] F-06：重复 record_id 入库被拒/去重。
- [ ] F-07：空 status/value 提交返回校验错误。
- [ ] F-08：-999 按哨兵策略处理，不进入数值统计。

---

## 6. 任务完成自检（对照 SKILL.md 第 97–100 行）

- [x] 是否限定在授权账号/cluster？——本次无账号/cluster，仅离线分析随附模拟日志，未触及任何外部目标。
- [x] 发现是否含复现与影响？——每条发现均含证据行、影响分析与可操作复测步骤。
- [x] 是否避免破坏性操作？——全程只读解析，未执行删除、修改、扫描、连接等动作。
- [x] 报告/journal？——本报告 `security-audit.md`。

## 7. 阻断与降级说明（非假装成功）

- **降级项（不阻断本次日志分析，但影响 Skill 流程完整性）**：SKILL.md ACTION REQUIRED 第 1 条要求读取的 `../field-journal/precedent-pentest.md`（书面授权先例）在随附 Skill 包中缺失，已在第 0 节声明，并以任务方书面范围声明作为替代授权依据。
- **未执行项（按范围与条件，非失败）**：未连接真实云账号/K8s 集群，未运行 kubectl/aws/gcloud/trivy 等工具——原因：(1) 任务范围限定为离线日志分析；(2) 未提供任何目标地址、AK/SK、kubeconfig 等凭据；(3) 工具本机未安装且无授权目标可用。第 4 节已列出补齐评估所需材料。
- **结论**：随附两个 CSV 的分析已**实际完成**，共 8 项发现（1 严重 / 3 中 / 4 低）；云/K8s 专项检查因缺乏对应遥测数据而**无法评估**，已如实标注，未编造结果。
