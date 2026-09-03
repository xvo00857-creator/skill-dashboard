# Atlassian 工作区管理配置与治理落地方案（最小改动）

> 适用范围：Jira / Confluence / Bitbucket（Atlassian Cloud）
> 依据 Skill：`atlassian-admin`（SKILL.md 及其 assets / references / scripts）
> 编制日期：2026-08-12

---

## 0. 执行边界与诚实声明

- 当前环境**无法访问真实 Atlassian 组织**：无 orgId、无站点 URL、无管理员 API token、未连接 `atlassian` MCP 服务器。因此本交付是**可执行方案 + 已在本地验证的工具基线**，不是对线上实例的变更。所有线上写操作需具备权限的管理员在 `admin.atlassian.com` 或通过 REST API v3 执行。
- 已实际执行的本地验证（非模拟）：
  - `python3 scripts/permission_audit_tool.py --help`（脚本可运行，Python 3.9.6，仅标准库）；
  - 对 `assets/permission_scheme_template.json` 直接运行 → 报错 `No permission schemes found in input`（输入结构不匹配，见第 6 节）；
  - 对从模板 EXAMPLE 项目派生的 `assets/permission_audit_input_example.json` 运行 → 得到真实基线（见第 6 节）。
- 未编造任何线上用户、组、项目、权限方案或运行结果。

---

## 1. Skill 能力边界（直接决定实现方式）

依据 SKILL.md「Atlassian MCP Integration — scope limits」：

- **管理类写操作不能通过 Atlassian Remote MCP 完成**（MCP 无用户/组/权限方案/字段/工作流/SSO/应用/组织设置工具）。
- MCP 仅提供只读辅助：`lookupJiraAccountId`、`searchJiraIssuesUsingJql`、`getVisibleJiraProjects`、`getConfluenceSpaces`、`atlassianUserInfo`、`getAccessibleAtlassianResources`。
- 所有写操作必须走 `admin.atlassian.com` 控制台或 SKILL.md 内联引用的 REST API（Jira `/rest/api/3`、组织管理 `/admin/v1`、Confluence `/wiki/rest/api`）。

**对实现的影响**：方案中每个变更动作都标注执行通道（UI 路径或 REST 端点），不假设 MCP 可写；盘点阶段才用 MCP 只读工具。

---

## 2. 给定约束如何改变了实现选择

| 约束 | 对实现选择的影响 |
|---|---|
| 兼容既有接口与目录结构 | 保留 `scripts/`、`assets/`、`references/` 原有文件不动；新增文件仅放 `assets/` 且为纯数据 JSON，不改变 `permission_audit_tool.py` 的输入契约（`{"schemes":[{"name","grants":[{"group","permission"}]}]}`）。 |
| 不随意升级主版本 | 继续使用 SKILL.md 内联引用的 Jira REST `/rest/api/3`，不提议跨大版本迁移；审计脚本在系统自带 Python 3.9.6 上运行，不升级运行时。 |
| 不引入未经批准的新依赖 | 审计工具仅用 `argparse/json/sys/typing` 标准库；治理落地复用 Skill 自带的模板、加固指南、入职清单，不引入外部 IAM/CMDB/SIEM 组件（SIEM 对接列为待确认项）。 |
| 最小改动 | 以「采用既有模板 + 既有审计工具 + 既有 checklist」为主干，不新建系统；发现工具键名缺陷只记录、不擅自修改，列为待批变更（见第 6、7 节）。 |
| 不得编造 / 标注不可达资源 | 所有需要线上凭据或真实数据的步骤标注「待确认」；本地验证结果与线上推断严格分开。 |

---

## 3. 最小改动方案（分阶段）

### 阶段 A — 基线盘点（只读，零风险）
1. 用 MCP 只读工具盘点可见范围：`getVisibleJiraProjects`、`getConfluenceSpaces`、`atlassianUserInfo`、`getAccessibleAtlassianResources`。
2. 从 `admin.atlassian.com > User management > Export users` 导出用户与组；从 Jira 导出各项目权限方案的 grants（结构对齐 `assets/permission_audit_input_example.json`）。
3. 用 `scripts/permission_audit_tool.py <导出文件>` 跑基线，保存报告作为变更前对照。

### 阶段 B — 权限方案与组落地
1. 默认采用 `assets/permission_scheme_template.json` 的 **Standard Project Permission Scheme**（角色：projectAdmin / developer / user / viewer），按 `projectMappings` 逐项目映射组。
2. 按 `references/user-provisioning-checklist.md` 命名规范建组：`org-all-employees`、`dept-*`、`team-*`、`project-*`、`role-*`。
3. 一律用组授权，**不授予个人权限**（最小权限原则）；删除类/管理类权限仅给 projectAdmin。
4. 组织管理员限 2–3 人（SKILL.md Governance），并强制 2FA（`Security > Authentication policies > Require 2FA`）。

### 阶段 C — 安全加固（按 references/security-hardening-guide.md）
1. SSO/SAML：先验证域名与认领账号 → 配置 IdP → **管理员账号先测、保留密码登录** → 普通用户测 → 全组织启用 → 再强制；启用 SCIM 自动开户/销户。
2. 2FA：所有受管账号强制；管理员优先 FIDO2/WebAuthn，禁用短信 2FA。
3. 会话：空闲超时 ≤8 小时、绝对超时 ≤24 小时。
4. IP 白名单：办公网、VPN 出口、CI/CD 固定 IP；移动端走 VPN/MDM。
5. API token：台账登记、最长 90 天轮换、集成用服务账号而非个人 token、离职即吊销。
6. 审计日志：开启组织审计日志，保留 ≥1 年（SOC2/GDPR 场景 ≥7 年），导出到 SIEM（待确认是否已有）。

### 阶段 D — 用户生命周期治理
- **入职**：按 checklist 走 SCIM 自动开户优先；手工时 `POST /rest/api/3/user` → 加组 → 分配产品访问 → 发欢迎邮件 → 通知团队负责人 → 验证用户可登录。
- **离职**：先审计名下内容（Jira：`GET /rest/api/3/search?jql=assignee={accountId}`；Confluence：`GET /wiki/rest/api/user/{accountId}/property`）→ 转移项目负责人/空间/未结 issue/筛选器与看板 → 移出所有组 → 撤销产品访问 → `DELETE /rest/api/3/user?accountId={accountId}` 停用 → 验证 `"active": false` → 记入审计日志。剩余未结 issue 转交 Jira Expert 处理。

### 阶段 E — 审计闭环与节奏
- 季度：权限审计（审计工具）、用户访问复核、应用审查、IP 白名单复核。
- 月度：审计日志复核、新管理员/权限方案变更告警复核。
- 变更管理：重大变更提前 2 周公告、沙箱验证、备回滚计划、低峰执行、事后复盘；小变更提前 48 小时公告并记录。

---

## 4. 回滚办法

| 变更 | 回滚手段 |
|---|---|
| Jira 权限方案 | 变更前复制原方案保留；出问题将项目切回原方案（`Project settings > Permissions`）。 |
| Confluence 空间权限 | 变更前导出空间权限；按导出表恢复。 |
| 组成员调整 | 变更前导出成员清单；按清单加回被移除成员。 |
| SSO 强制 | 测试期保留密码登录应急通道；异常时在 `Security > Authentication policies` 关闭 SSO 强制。 |
| 2FA / 会话策略 | 在认证策略中回退到上一策略版本；应急管理员账号保留恢复码。 |
| IP 白名单 | 变更前导出现有白名单；误封时从可信网络或应急通道恢复。 |
| Marketplace 应用 | 卸载应用即回退；配置变更前按厂商文档导出配置。 |
| 审计工具键名修复（若批准） | 单文件还原 `scripts/permission_audit_tool.py`（版本控制或备份副本）。 |
| 本方案新增样例文件 | 删除 `assets/permission_audit_input_example.json` 即可，不影响任何既有文件。 |

---

## 5. 测试清单

- [ ] **权限边界**：用 projectAdmin / developer / user / viewer 四种角色账号分别验证 browse、create、edit、delete、transition、comment、attachment、worklog 的允许与拒绝。
- [ ] **个人授权清零**：审计工具 `direct_user_permission` / `too_many_direct_users` 无 high 及以上发现。
- [ ] **SSO**：管理员账号登录成功 → 普通用户登录成功 → 审计日志出现 `saml.login.success` → 强制后密码登录按预期被拒（应急账号除外）。
- [ ] **2FA**：新用户首次登录强制 enrolled；管理员账号支持硬件密钥。
- [ ] **离职流程**：停用后 `GET /rest/api/3/user?accountId=` 返回 `"active": false`；名下未结 issue 已转移；API token 已吊销。
- [ ] **审计工具**：对已知 grants 样例运行，findings 与预期一致（注意第 6 节已知键名缺陷）。
- [ ] **回归**：未纳入本次变更的项目/空间权限方案保持不变，用户访问无异常。
- [ ] **集成**：Slack/GitHub/Teams 等集成 webhook 测试投递成功，OAuth token 存入安全存储而非明文。

---

## 6. 已验证的工具基线（真实运行结果）

环境：Python 3.9.6，脚本仅依赖标准库。

**6.1 模板直跑（结构不匹配）**
```
$ python3 scripts/permission_audit_tool.py assets/permission_scheme_template.json
ERROR: No permission schemes found in input
```
原因：模板是 `permissionScheme/roles/permissions/projectMappings` 角色模型，工具期望 `schemes[].grants[]{group,permission}`。两者无适配层。

**6.2 派生样例运行结果**
`assets/permission_audit_input_example.json` 由模板 EXAMPLE 项目的 `roleAssignments` 逐角色展开派生（未改动任何既有文件）：
```
Risk Score: 24/100   Health Score: 76/100   Grade: Good   Schemes Analyzed: 1
Critical: 0   High: 1   Medium: 1   Low: 0   Info: 1
```
- HIGH `over_permissioned_group`：`project-leads` 持有 3 个敏感权限（delete_all_attachments / delete_all_comments / delete_issues）。
- MEDIUM `no_admin_defined`：未识别到显式管理权限。
- INFO `separation_of_duties`：敏感权限集中在 `project-leads` 单一组。

**6.3 发现的工具缺陷（未擅自修改）**
工具内 `SENSITIVE_PERMISSIONS` 与 `check_missing_restrictions` 使用的是 `administer_project`（单数），而 Jira 实际权限键与模板均为 `ADMINISTER_PROJECTS`（复数）。后果：
1. `project-leads` 实际持有 4 个敏感权限（含 `ADMINISTER_PROJECTS`），工具只计 3 个，风险低估；
2. `no_admin_defined` 为误报——方案中已存在 `ADMINISTER_PROJECTS`，但因键名不匹配未被识别。

按「不擅自改动既有接口」约束，此处**不直接改脚本**，将最小修复（在敏感集合与 admin 检测中补充 `administer_projects` 复数别名，保持向后兼容）列为第 7 节待批项。

---

## 7. 仍待确认项

1. 组织 orgId、站点 URL、具备管理员权限的 API token / OAuth 凭据。
2. 身份提供商选型（Okta / Azure AD / Google）与域名验证、账号认领状态。
3. 现有组清单及是否已符合 `org-/dept-/team-/project-/role-` 命名规范。
4. 当前组织管理员人数、是否已对全员强制 2FA、应急管理员账号是否已配置恢复码。
5. 数据驻留区域要求（US/EU/AU 等）与合规框架（SOC2/ISO27001/GDPR/HIPAA）。
6. 是否已启用 SCIM；审计日志 SIEM（Splunk/Datadog 等）是否就绪。
7. 从线上导出的真实权限方案 grants 数据（用以替换 `permission_audit_input_example.json` 跑真实基线）。
8. 是否批准修复审计工具键名缺陷（`administer_project` → 补 `administer_projects`）；批准后以最小补丁方式修改并回归。
9. 现有 Marketplace 应用清单与白名单策略。
10. 在职/离职数据源（HR 系统）与 SCIM/工单触发方式。

---

## 8. 实际读取的 Skill 文件（相对路径）

- `SKILL.md`
- `assets/permission_scheme_template.json`
- `assets/permission_audit_input_example.json`（本次新增，由模板派生）
- `references/security-hardening-guide.md`
- `references/user-provisioning-checklist.md`
- `scripts/permission_audit_tool.py`

---

## 9. 实际影响交付结果的 SKILL.md 规则

1. **第 217–219 行「Atlassian MCP Integration — scope limits」**：管理写操作不能经 MCP 完成，必须走 `admin.atlassian.com` 或 REST API。这直接决定了本方案把每个动作标注执行通道、把 MCP 限定在阶段 A 只读盘点，并在第 0 节明确声明未对线上实例做任何变更——而非假装已通过 MCP 执行了管理操作。
2. **第 164 行「Change Management」**（重大变更提前 2 周公告、沙箱测试、回滚计划、低峰执行、事后复盘）：决定了第 4 节回滚办法与第 5 节测试清单的结构与粒度。
3. **第 156–157 行 Access Governance**（org admin 限 2–3 人、强制 MFA）：决定了阶段 B 的管理员收敛与 2FA 要求。
