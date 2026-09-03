# 安全审计报告：security-and-hardening Skill

**审计日期**：2026-08-12
**审计依据**：security-and-hardening/SKILL.md（随附 ZIP 包）
**审计模式**：只读审查，未修改任何文件，未中断任何服务，未运行任何安装或扫描命令
**审计人**：豆包安全审查助手

---

## 一、执行摘要

本次审计严格依据随附 `security-and-hardening.zip` 中的 `SKILL.md` 执行。该 Skill 是一套面向 Web 应用的**安全开发实践指南**，涵盖威胁建模、OWASP Top 10 防护模式、输入验证、依赖审计分流、速率限制、密钥管理及 LLM 安全等主题。

**关键前提**：用户未提供任何待审计的代码库、应用程序、配置文件或运行环境。压缩包内仅含 `SKILL.md` 一个文件。因此，本次审计的实际审查对象为 **SKILL.md 文档本身及其代码示例**，而非某个生产系统。所有针对实际系统的安全结论均无法做出，已在下文明确标注。

**发现汇总**：

| 分类 | 数量 | 说明 |
|---|---|---|
| 已证实问题 | 1 | 文档引用失效（`references/security-checklist.md` 缺失） |
| 疑似项 | 3 | 代码示例边界问题，需结合上下文确认 |
| 误报排除 | 2 | 经核实不构成问题 |
| 无法确认 | 4 | 缺少审计目标或不可访问资源 |

未发现 SKILL.md 中存在密钥泄露、恶意代码或危险指令。文档中的代码示例整体质量较高，BAD/GOOD 对照清晰，且主动披露了 SSRF 防护的 TOCTOU 残留风险。

---

## 二、Skill 能力边界确认

根据 SKILL.md 原文，该 Skill 的定位为：

- **是什么**：Web 应用安全开发实践指南，提供威胁建模方法、防护代码模式、审计分流决策树和检查清单。
- **不是什么**：不是自动化扫描器，不是渗透测试框架，不是运行时防护工具，不能替代人工代码审查。
- **核心约束**（直接影响本次交付）：
  - "Package-manager audits report known advisories; they do not prove a package is trustworthy or that vulnerable code is reachable."（审计报告不等于漏洞结论，必须判断可达性）
  - "If you can't name the trust boundaries for a feature, you're not ready to secure it."（无法命名信任边界则不应开始加固）
  - "Never apply forced audit remediation automatically"（禁止自动强制修复）

**与题目假设的冲突说明**：题目要求"落实安全审计、风险确认与防御性修复"，但未提供审计目标。SKILL.md 的流程要求先"Map the trust boundaries"（映射信任边界），而在没有代码的情况下无法完成此步骤。依据"以文件规则为准"的要求，本报告不虚构审计目标，不编造漏洞发现，而是对唯一可读对象（SKILL.md 本身）执行审查，并提供可复用的审计框架。

---

## 三、审计范围与资源清单

### 3.1 已读取文件

| 文件相对路径 | 状态 |
|---|---|
| `security-and-hardening/security-and-hardening/SKILL.md` | 已完整读取（467 行） |

### 3.2 不可访问资源

| 资源 | 引用位置 | 状态 |
|---|---|---|
| `../../references/security-checklist.md` | SKILL.md 第 77、303、427 行 | **不存在**——压缩包内未包含，已检查全部 Skill 根目录的 references 文件夹，均未找到 |
| OWASP Top 10 for LLM Applications (2025) 外部链接 | 第 358 行 | 公开网址，本次未联网抓取内容，仅确认其为公开安全组织链接 |

### 3.3 未提供的审计目标

- 无源代码仓库（无 `.js`/`.ts`/`.py` 等文件）
- 无 `package.json`/锁文件/依赖清单
- 无运行中的服务或配置
- 无"表格分类"所指的具体表格文件

---

## 四、威胁建模（针对 SKILL.md 作为文档资产）

按 SKILL.md 要求的 STRIDE 方法，对文档本身执行快速威胁建模：

| 威胁类别 | 对本文档的适用性 | 结论 |
|---|---|---|
| 仿冒（Spoofing） | 文档不处理身份认证 | 不适用 |
| 篡改（Tampering） | 文档为只读附件，无写入路径 | 不适用 |
| 抵赖（Repudiation） | 文档不记录操作 | 不适用 |
| 信息泄露（Information Disclosure） | 文档可能包含敏感信息 | **已检查**：无密钥、密码、令牌、PII；示例域名均为 `example.com` 保留域名 |
| 拒绝服务（DoS） | 文档不可执行 | 不适用 |
| 权限提升（Elevation of Privilege） | 文档不授予权限 | 不适用 |

**信任边界**：SKILL.md 是一份指导文档，其代码示例会被开发者复制到真实项目中。因此，代码示例的正确性本身就是安全边界——示例中的缺陷会被放大到生产系统。

---

## 五、发现详情

### 5.1 已证实问题

#### C-1：文档内部引用失效（严重度：低，文档完整性）

- **位置**：SKILL.md 第 77 行、第 303 行、第 427 行
- **现象**：三处引用 `../../references/security-checklist.md`，分别用于：
  - 第 77 行：OWASP Top 10 2021 排序速查表
  - 第 303 行：包管理器矩阵（package manager matrix）
  - 第 427 行：详细安全检查清单和提交前验证步骤
- **核实方式**：解压后检查目录结构，确认压缩包内仅含 `SKILL.md`；另检查六个 Skill 根目录下的 `references/` 文件夹，均不存在该文件。
- **影响**：读者无法获取文档承诺的补充材料，可能导致：
  - 无法确认 OWASP 2021 排序（仅影响参考，不影响防护模式本身）
  - 供应链卫生流程中"包管理器矩阵"缺失，影响多包管理器场景下的操作指引
  - 提交前验证步骤缺失，削弱 Verification 章节的可操作性
- **分类依据**：文件不存在是可直接验证的事实，故为已证实问题。但这是文档打包问题，非代码安全漏洞。

### 5.2 疑似项

#### S-1：访问控制示例未展示输入验证（严重度：信息性）

- **位置**：SKILL.md 第 134–147 行
- **现象**：`PATCH /api/tasks/:id` 示例在完成所有权检查后，直接将 `req.body` 传入 `taskService.update(req.params.id, req.body)`，未展示对 `req.body` 的 schema 验证。
- **为何疑似**：SKILL.md 自身在第 46 行要求"Validate all external input at the system boundary"，并在第 226–252 行提供了 zod 验证模式。但该访问控制示例未串联这两个实践，可能让读者误以为所有权检查即可替代输入验证。
- **为何未定为已证实**：这是一个**简化示例**，文档在独立章节已覆盖输入验证；示例代码本身也没有展示危险操作（如 SQL 拼接）。是否构成问题取决于读者是否会逐字复制。
- **建议**：在示例中补充注释 `// Validate req.body with a schema (see Input Validation Patterns)` 或直接调用 `UpdateTaskSchema.parse(req.body)`。

#### S-2：CORS 示例的环境变量空值边界（严重度：信息性）

- **位置**：SKILL.md 第 170 行
- **代码**：`origin: process.env.ALLOWED_ORIGINS?.split(',') || 'http://localhost:3000'`
- **现象**：若 `ALLOWED_ORIGINS` 设为空字符串 `""`，`?.split(',')` 返回 `[""]`（非空数组），`||` 不会触发回退，CORS 源将被设为包含空字符串的数组，可能导致跨域行为不符合预期。
- **为何疑似**：这是示例代码，生产部署中通常会正确配置环境变量。但防御性编程应处理空字符串。
- **建议**：改为 `process.env.ALLOWED_ORIGINS?.split(',').filter(Boolean) || [...]`。

#### S-3：bcrypt 示例未提示 72 字节截断（严重度：信息性）

- **位置**：SKILL.md 第 96–100 行
- **现象**：示例使用 bcrypt，`SALT_ROUNDS = 12` 符合文档自身要求（≥12），但未提及 bcrypt 对超过 72 字节的密码输入会截断处理。
- **为何疑似**：文档同时推荐了 scrypt/argon2，但未说明选型考量。长密码截断在特定场景下可能削弱安全性（尽管预哈希可缓解，但预哈希又有注意事项）。
- **为何未定为已证实**：bcrypt 的 72 字节截断是已知行为，12 轮 salt 符合行业实践；这属于文档完整性建议，非示例错误。
- **建议**：添加注释说明 bcrypt 72 字节限制，或在高安全场景推荐 argon2id。

### 5.3 误报排除

#### F-1：SSRF 防护的 `range() !== 'unicast'` 检查——非误报，实为正确实现

- **位置**：第 209 行
- **初步疑问**：单行检查是否足以覆盖所有内网地址？
- **核实结论**：`ipaddr.js` 的 `range()` 方法对 loopback、private、linkLocal（含 `169.254.169.254` 云元数据地址）、uniqueLocal（IPv6）、reserved 等均返回非 `'unicast'` 值，因此该检查能正确拒绝所有非公网地址。文档还**主动披露**了 TOCTOU 残留风险（第 220 行）并给出了高风险场景的加固方案。这不是缺陷，而是诚实且正确的示例。

#### F-2：输入验证示例返回 `result.error.flatten()`——非信息泄露

- **位置**：第 244 行
- **初步疑问**：返回验证错误详情是否违反"Never expose internal error details"？
- **核实结论**：zod 的 `flatten()` 输出的是**字段级验证错误**（如"标题不能为空"），属于用户可操作的输入反馈，不包含堆栈跟踪、SQL 语句、文件路径或内部架构信息。这与 SKILL.md 禁止的"stack traces or internal error details"（第 73 行）不是同一类别。不构成问题。

### 5.4 无法确认

| 编号 | 事项 | 原因 |
|---|---|---|
| U-1 | 任何实际应用的安全态势 | 未提供代码库、配置或运行环境 |
| U-2 | `references/security-checklist.md` 的内容 | 文件不存在于包内及所有已检查路径 |
| U-3 | 依赖漏洞审计结果 | 无 `package.json`/锁文件，无法运行包管理器审计；且 SKILL.md 要求审计结果必须经可达性分析，不能直接当作结论 |
| U-4 | 生产环境安全头/CORS/速率限制是否生效 | 无运行中的服务可验证 |

---

## 六、防御性修复建议

以下建议**仅针对 SKILL.md 文档及其示例**，不涉及任何生产系统。所有修改均需文档维护者人工确认后执行，本次审查未修改任何文件。

| 编号 | 修复项 | 最小修改方案 | 风险 |
|---|---|---|---|
| C-1 | 补充缺失的引用文件 | 在分发包中包含 `references/security-checklist.md`，或移除三处失效引用并将关键内容（OWASP 2021 排序表、包管理器矩阵、提交前步骤）内联到 SKILL.md | 无风险，文档变更 |
| S-1 | 访问控制示例补充输入验证提示 | 添加一行注释或调用 `UpdateTaskSchema.parse(req.body)` | 无风险，示例增强 |
| S-2 | CORS 环境变量空值处理 | 添加 `.filter(Boolean)` | 无风险，防御性编程 |
| S-3 | bcrypt 72 字节说明 | 添加注释或推荐 argon2id 用于高安全场景 | 无风险，文档补充 |

**关于生产系统的防御性修复**：由于无审计目标，无法提供针对性补丁。若后续提供代码库，将按 SKILL.md 的"Three-Tier Boundary System"执行：Always Do 项直接修复，Ask First 项需人工批准，Never Do 项立即移除。

---

## 七、最小风险验证计划

本计划遵循题目要求：只读权限、脱敏样本、不中断生产服务、不把扫描器提示当结论。

### 阶段一：文档级验证（零风险，可立即执行）

| 步骤 | 操作 | 权限 | 预期结果 |
|---|---|---|---|
| V-1 | 确认 `references/security-checklist.md` 是否存在于分发包 | 只读 | 当前：不存在；修复后应存在 |
| V-2 | 检查 SKILL.md 中是否包含硬编码密钥（正则匹配 `password\s*=\s*['"][^'"]+['"]`、`api_key`、`sk-` 等） | 只读 | 无匹配（已人工确认） |
| V-3 | 确认所有外部链接指向公开可信站点 | 只读 | 仅 OWASP 公开链接 |

### 阶段二：代码库审计（待提供目标后执行）

| 步骤 | 操作 | 权限 | 风险控制 |
|---|---|---|---|
| V-4 | 映射信任边界：列出所有接收外部输入的路由/处理器 | 只读 | 不修改代码 |
| V-5 | 运行包管理器原生审计（`npm audit`/`pnpm audit` 等），**仅读取报告** | 只读 | 不执行 `audit fix --force`；结果按 SKILL.md 决策树分流，判断可达性后才定级 |
| V-6 | 人工审查 SQL 查询是否参数化、输出是否转义、鉴权是否逐端点检查 | 只读 | 使用脱敏样本数据，不触碰生产数据 |
| V-7 | 检查 `.gitignore` 是否覆盖 `.env`、`*.pem`、`*.key`；用 `git log` 扫描历史中的密钥 | 只读 | 不重写历史；若发现泄露，按 SKILL.md 要求先轮换密钥再清理 |
| V-8 | 验证安全头/CORS/速率限制配置（读取配置文件或在脱敏环境发送测试请求） | 只读/脱敏环境 | 不对生产服务发起压测或中断性操作 |

### 阶段三：修复验证（修复后执行）

| 步骤 | 操作 | 风险控制 |
|---|---|---|
| V-9 | 对修复项运行现有单元/集成测试 | 在 CI 或本地开发环境执行，不影响生产 |
| V-10 | 人工复核修复 diff，确认未引入新风险 | 只读审查 |
| V-11 | 按 SKILL.md Verification 清单逐项勾选 | 不跳过任何项 |

---

## 八、实际读取的 Skill 文件清单

| 序号 | 相对路径（相对于工作目录） | 读取方式 |
|---|---|---|
| 1 | `security-and-hardening/security-and-hardening/SKILL.md` | 完整读取（两次，共 467 行） |

未读取其他文件。`../../references/security-checklist.md` 经检查不存在，无法读取。

---

## 九、影响交付结果的 SKILL.md 规则

以下规则**实际影响了本报告的结论和交付方式**：

1. **"Package-manager audits report known advisories; they do not prove a package is trustworthy or that vulnerable code is reachable."**（第 274 行）
   - 影响：本报告未将任何扫描器提示当作漏洞结论。由于无代码库可审计，未编造任何 CVE 或依赖漏洞；所有发现均基于人工阅读和逻辑验证。

2. **"If you can't name the trust boundaries for a feature, you're not ready to secure it."**（第 40 行）
   - 影响：在未提供审计目标的情况下，本报告未虚构信任边界或假设某个应用的架构，而是明确标注"无法确认"，并将审查范围限定于 SKILL.md 本身。

3. **"Never apply forced audit remediation automatically"**（第 308 行）
   - 影响：本报告未执行任何自动修复命令，所有修复建议均以提案形式列出，需人工确认。

4. **三层边界系统中的"Ask First (Requires Human Approval)"**（第 56–63 行）
   - 影响：所有防御性修复建议均标注"需文档维护者人工确认后执行"，本次审查未修改任何文件。

5. **"Never commit secrets"及密钥泄露后轮换原则**（第 67、354 行）
   - 影响：对 SKILL.md 执行了密钥扫描，确认无硬编码凭据。

---

## 十、结论与后续建议

1. **SKILL.md 本身**：是一份质量较高的安全开发指南，代码示例正确展示了主要防护模式，且诚实披露了残留风险（如 SSRF TOCTOU）。发现 1 个文档完整性问题和 3 个信息性改进建议，无安全漏洞。
2. **缺失的审计目标**：若需对实际应用执行安全审计，请提供代码库路径或仓库地址。届时将按本报告第七节的阶段二计划执行，并输出包含已证实问题、疑似项、误报排除和修复补丁的完整报告。
3. **缺失的引用文件**：建议重新打包 Skill 时包含 `references/security-checklist.md`，或将其内容内联，以保证文档自包含。

---

*本报告所有事实陈述均基于实际读取的文件内容和可验证的文件系统检查，未编造数据、运行结果或已完成的操作。无法确认的事项已明确标注。*
