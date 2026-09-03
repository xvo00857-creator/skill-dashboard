# Aeroleads 自动化受约束流程方案

> 依据 `aeroleads-automation/SKILL.md` 制定。所有内容以该 Skill 的真实能力边界为准，超出边界的环节明确标注为"需外部系统"。
> 生成时间：2026-08-12（Asia/Shanghai）

---

## 一、能力边界声明（先于一切设计）

### 1.1 Skill 的真实能力

根据 SKILL.md，本 Skill 的唯一作用是：**通过 Rube MCP（Composio）调用 Aeroleads toolkit**。其工作流被严格限定为三步：

1. `RUBE_SEARCH_TOOLS`——发现可用工具及当前 schema（**必须先调用，禁止硬编码**）；
2. `RUBE_MANAGE_CONNECTIONS`——确认 Aeroleads 连接为 ACTIVE；
3. `RUBE_MULTI_EXECUTE_TOOL`——按发现的 schema 执行工具。

根据 Composio 官方 Aeroleads toolkit 文档（https://composio.dev/toolkits/aeroleads），该 toolkit 当前仅提供 **1 个工具**：

| 工具 | 能力 |
|------|------|
| Get Details From LinkedIn URL | 输入一个 LinkedIn 个人资料 URL，返回该潜在客户的详细信息（姓名、职位、公司、商务邮箱、电话等，以实际 schema 为准） |

### 1.2 Skill 不能做的事（题目假设与能力的冲突点）

以下事项**超出本 Skill 能力边界**，不得由本 Skill 静默执行，需外部系统或人工配合：

- 搜索/发现潜在客户（无 prospect search 工具）；
- 发送外联邮件、短信或任何消息（无 outreach/send 工具）；
- 管理 Aeroleads 列表、增删联系人（list 管理工具不在当前 toolkit 中）；
- 跟踪邮件打开、点击、回复等投放效果数据（无 analytics 工具）；
- 直接访问 CRM、广告平台或邮件发送平台的数据。

因此，"增长策略、投放分析与可衡量实验"中，**本 Skill 能直接自动化的只有"线索信息补全（enrichment）"这一环节**：把已有的 LinkedIn URL 批量转为结构化联系人信息。其余环节须由外部系统承担，本方案仅设计衔接接口与数据契约，不假装已实现。

### 1.3 当前环境的阻断状态

预检（见第四节及 `preflight-demo-result.txt`）证实：

- Rube MCP 端点 `https://rube.app/mcp` 在当前网络不可达；
- 本地无 `rube` CLI、无 `~/.rube` 配置、无相关环境变量；
- 当前 Agent 工具清单中不存在任何 `RUBE_*` 工具；
- 无业务输入数据（无 leads.csv 等）。

**结论：当前无法执行任何真实的 Aeroleads 调用。** 本方案中的执行流程为"就绪后可运行"的设计，演示结果仅为预检脚本的真实输出，不含任何编造的 API 返回数据。

---

## 二、总体流程：增长闭环中的 Aeroleads 定位

```
[外部] 线索收集        →  [本 Skill] 线索补全        →  [外部] 外联投放       →  [外部] 效果回收
LinkedIn Sales Nav /   →  LinkedIn URL 批量 →        →  邮件平台 / CRM       →  打开/点击/回复/转化
活动报名 / 手动整理       →  联系人详情(enrichment)    →  人工审核后发送        →  回流分析
```

本 Skill 负责中间"补全"环节，并产出可供下游使用的结构化数据文件。增长策略、投放分析、实验设计围绕这一环节展开，但数据闭环的其余部分依赖外部系统。

---

## 三、受约束的执行流程（含预检、幂等、重试、人工确认）

### 3.1 阶段 0：预检（强制门禁，已实现）

每次运行前必须通过预检，任一项 BLOCK/FAIL 即终止，不进入执行。预检项：

| # | 检查项 | 阻断条件 | 依据 |
|---|--------|----------|------|
| 1 | Rube MCP 端点可达 | 连接超时/拒绝 | SKILL.md Setup |
| 2 | 本地 rube CLI / 配置存在 | 均缺失（WARN，不阻断但提示） | 环境完整性 |
| 3 | `RUBE_SEARCH_TOOLS` 可调用 | 工具不存在或无响应 | SKILL.md "Always search first" |
| 4 | Aeroleads 连接状态 = ACTIVE | 非 ACTIVE | SKILL.md Setup 步骤 4 |
| 5 | 工具 schema 已发现 | 未获取到 schema | SKILL.md Known Pitfalls |
| 6 | 输入数据存在且格式合法 | 文件缺失或无有效 LinkedIn URL | 数据就绪 |

预检脚本：`aeroleads-preflight.sh`（只读，不修改任何外部资源）。

### 3.2 阶段 1：工具发现（禁止硬编码）

严格按 SKILL.md，每次工作流开始时调用：

```
RUBE_SEARCH_TOOLS
queries: [{use_case: "Aeroleads get prospect details from LinkedIn URL"}]
session: {generate_id: true}
```

- 从返回结果中读取**实时** tool slug 与输入 schema；
- 不使用历史记忆中的 slug 或字段名（SKILL.md："Tool schemas change"）；
- 记录返回的 `session_id`，后续步骤复用；
- 若返回工具数为 0 或与预期不符，转人工确认，不猜测。

### 3.3 阶段 2：连接确认

```
RUBE_MANAGE_CONNECTIONS
toolkits: ["aeroleads"]
session_id: "<阶段1返回>"
```

- 状态非 ACTIVE 时，输出返回的授权链接，**暂停并等待人工完成授权**（人工确认点 ①）；
- 不绕过、不使用任何硬编码 API Key。

### 3.4 阶段 3：输入准备与幂等去重

输入为一个 CSV/JSON，至少包含 `linkedin_url` 列。处理规则：

1. **URL 规范化**：去除 query 参数（保留 `/in/<slug>/` 主体）、统一小写 scheme/host、补全尾部斜杠；
2. **去重键**：对规范化后的 URL 计算 SHA-256 摘要作为 `lead_key`；
3. **幂等缓存**：维护本地 `enrichment_cache.jsonl`，已存在 `lead_key` 的记录直接复用，不重复调用 API；
4. **断点续跑**：每处理 N 条（建议 20）落盘一次进度，中断后重跑自动跳过已完成项；
5. **干跑模式（dry-run）**：首次运行默认 dry-run，只输出"将调用 N 次、去重后 M 次、预计跳过 K 次"，**不发起任何外部调用**，等待人工确认（人工确认点 ②）。

### 3.5 阶段 4：批量执行与重试

```
RUBE_MULTI_EXECUTE_TOOL
tools: [{tool_slug: "<发现的slug>", arguments: {<schema要求的字段>}}]
memory: {}
session_id: "<阶段1返回>"
```

重试策略（按 SKILL.md "schema compliance" 与通用稳健性要求）：

| 错误类型 | 策略 | 最大次数 |
|----------|------|----------|
| 网络超时 / 5xx | 指数退避 2s→4s→8s | 3 |
| 限流 429 | 尊重 `Retry-After` 头；无则退避 30s | 3 |
| 认证 401/403 | **不重试**，转人工重新授权（人工确认点 ③） | 0 |
| 无效 LinkedIn URL / 4xx 数据错误 | **不重试**，标记 `status=invalid_input` 并跳过 | 0 |
| Schema 校验失败 | **不重试**，立即暂停，说明字段不匹配（可能 schema 已变更，需重新发现） | 0 |

- 每条结果写入 `enrichment_cache.jsonl`，包含 `lead_key`、原始 URL、返回状态、原始响应（脱敏后）、时间戳；
- `memory` 参数始终传 `{}`（SKILL.md Known Pitfalls 明确要求）；
- 分页：若返回含分页 token，持续拉取直到完成（SKILL.md："Pagination"）。

### 3.6 阶段 5：人工审核点（批量外发前强制）

Aeroleads 返回的联系人数据**不得自动进入外联投放**。批量执行后：

1. 输出汇总：成功数、失败数、无效数、邮箱字段为空数；
2. 生成待审核文件 `prospects_enriched_review.csv`；
3. **人工确认点 ④**：由运营/销售人工抽检（建议至少 10% 或 20 条，取大者），确认邮箱有效性与职位匹配度后，方可导出给下游邮件平台。

### 3.7 阶段 6：导出（只写本地，不触外部）

- 导出为本地 CSV/JSON，字段以实际 schema 返回为准（不预设字段名）；
- **不直接调用邮件平台/CRM 写入接口**——那超出本 Skill 边界，由外部系统在人工确认后导入；
- 导出文件附带 `run_manifest.json`：运行时间、session_id、工具 slug、输入条数、成功/失败计数、预检结果哈希，供审计。

---

## 四、预检演示结果（真实、可核验）

以下为 `aeroleads-preflight.sh` 在当前环境的真实输出（完整文件：`preflight-demo-result.txt`，退出码 2 表示阻断）：

```
==== 1. Rube MCP 端点可达性 ====
[2026-08-12 08:29:38 CST] [FAIL] 无法连接 https://rube.app/mcp （网络不可达或超时）

==== 2. 本地 Rube / Composio 可执行文件与配置 ====
[WARN] 未找到 rube CLI
[WARN] 不存在 ~/.rube 配置目录
[WARN] 未发现 RUBE/COMPOSIO/AEROLEADS 相关环境变量

==== 3. RUBE_SEARCH_TOOLS 可用性 ====
[BLOCK] RUBE_SEARCH_TOOLS 不可用：当前 Agent 工具清单中无 RUBE_* 工具，且无 rube CLI

==== 4. Aeroleads 连接状态 ====
[BLOCK] 无法检查：RUBE_MANAGE_CONNECTIONS 依赖 Rube MCP，前置项未通过

==== 5. 工具 Schema 发现 ====
[BLOCK] 无法执行：RUBE_SEARCH_TOOLS 不可用，不能硬编码 tool slug 或参数

==== 6. 业务数据就绪情况 ====
[WARN] 未发现本地线索数据文件，无输入数据可处理

预检汇总：PASS=0  WARN=4  FAIL=1  BLOCK=3
```

**这是本次唯一可在当前环境真实执行的环节。** 任何"Aeroleads 返回了某某联系人数据"的说法都将是编造，本方案不提供。

---

## 五、增长策略（基于 Aeroleads 补全环节）

### 5.1 策略定位

Aeroleads 补全环节的增长价值在于：**提升已有线索的可触达率与信息完整度**，而非获取新线索。具体策略：

1. **线索池清洗与补全**：将各渠道收集的 LinkedIn URL 批量补全为"姓名+职位+公司+邮箱+电话"，优先补全高意向来源（活动报名、内容下载、官网申请）；
2. **路由分级**：按补全结果中的职位/公司字段做意向分层（如职位含"VP/Director/Head"且公司规模匹配目标客户画像 → 高优先级），供销售优先跟进；
3. **补全率监控**：跟踪"有效邮箱返回率"作为线索质量的反向指标——某来源补全率持续偏低，说明该来源 URL 质量差，应调整收集策略。

### 5.2 边界说明

- "各渠道收集 LinkedIn URL"需外部系统（Sales Navigator 导出、活动工具、手动整理），本 Skill 不负责采集；
- "销售跟进/邮件发送"需外部 CRM/邮件平台，本 Skill 不负责发送；
- 上述策略中的"目标客户画像""意向分层规则"需业务方提供，本方案不臆造具体标准。

---

## 六、投放分析框架（数据契约，非实时看板）

### 6.1 本 Skill 产出的数据

`prospects_enriched.csv`（字段以实际 schema 为准，预期包含）：

| 字段 | 用途 |
|------|------|
| lead_key | 幂等去重键，贯穿全链路 |
| linkedin_url | 原始输入 |
| name / title / company | 联系人属性，用于分层分析 |
| business_email | 触达凭证（需人工审核后使用） |
| enrichment_status | success / invalid_input / failed |
| enriched_at | 补全时间 |

### 6.2 需外部系统回流的数据

投放效果分析必须由邮件平台/CRM 回流以下字段，按 `lead_key`（或下游映射的联系人 ID）关联：

- 是否发送、发送时间；
- 是否打开、打开次数、首次打开时间；
- 是否点击、点击链接；
- 是否回复、回复意向分类；
- 是否转化（如预约会议、成交）。

### 6.3 可分析维度（在数据齐备后）

- 按职位层级/公司规模分组的打开率、回复率、转化率；
- 补全信息完整度（有邮箱+有电话 vs 仅邮箱）与回复率的相关性；
- 不同线索来源的补全率与后续转化率对比。

**当前状态：外部回流数据不存在，本方案不产出任何分析数字。** 上述为分析框架，待数据接入后执行。

---

## 七、可衡量实验设计（A/B 测试方案）

### 7.1 实验假设

> 对 LinkedIn 线索进行 Aeroleads 信息补全并按职位/公司分层后发送个性化外联，相比不补全、统一模板发送，可显著提升回复率。

### 7.2 实验设计

| 项目 | 设计 |
|------|------|
| 分组 | 对照组：仅邮箱+统一模板；实验组：补全字段+按职位层级个性化模板 |
| 随机化 | 同一来源、同一时间段的线索按 lead_key 哈希奇偶分组，保证两组来源构成一致 |
| 主指标 | 回复率（回复数/送达数） |
| 护栏指标 | 退订率、垃圾邮件投诉率（不超过对照组 +0.5pp） |
| 样本量 | 需根据基线回复率与最小可检测提升（MDE）计算；**基线数据当前不存在，无法给出具体数字**，需先跑 1-2 周观察期 |
| 周期 | 建议至少覆盖一个完整外联周期（含跟进邮件），通常 2-3 周 |
| 显著性 | 双比例 z 检验，α=0.05，power=0.8 |

### 7.3 本 Skill 在实验中的角色

- 仅负责实验组的线索补全与分层标签产出；
- 分组、发送、回收、统计检验均由外部系统完成；
- 实验启动前需人工确认分组规则与模板内容（人工确认点 ⑤）。

### 7.4 无法执行的声明

当前无 Rube MCP、无 Aeroleads 连接、无线索数据、无邮件平台，**实验无法实际运行**。以上为可评审、可在条件就绪后执行的实验方案，不含任何编造的实验结果。

---

## 八、人工确认点汇总

| 编号 | 时机 | 确认内容 |
|------|------|----------|
| ① | Aeroleads 连接非 ACTIVE | 人工点击授权链接完成 OAuth/API Key 配置 |
| ② | 批量执行前（dry-run 后） | 确认调用次数、去重数、输入范围 |
| ③ | 认证失败 401/403 | 人工重新授权，不自动重试 |
| ④ | 补全完成、外发前 | 人工抽检数据质量，批准导出 |
| ⑤ | 实验启动前 | 确认分组规则、模板、样本量 |

---

## 九、无法访问的资源与待确认假设

### 无法访问/不存在的资源
1. Rube MCP 服务（`https://rube.app/mcp` 当前网络不可达，且客户端未配置）；
2. Aeroleads 账户与 API 连接（未授权）；
3. 真实的 `RUBE_SEARCH_TOOLS` 返回 schema（无法获取，故不硬编码 slug/字段）；
4. 业务线索数据（未提供 leads 文件）；
5. 邮件平台/CRM 数据（无访问权限）。

### 待确认假设
1. 假设 Composio Aeroleads toolkit 仍只有"Get Details From LinkedIn URL"一个工具——以实际 `RUBE_SEARCH_TOOLS` 返回为准；
2. 假设输入数据包含 `linkedin_url` 字段——实际字段名待数据提供后确认；
3. 假设下游邮件平台支持按 lead_key 或邮箱回流效果数据——待外部系统确认；
4. 增长策略中的"目标客户画像"标准需业务方提供，本方案未臆造。

---

## 十、交付物清单

| 文件 | 说明 |
|------|------|
| `aeroleads-preflight.sh` | 预检脚本（只读，真实可运行） |
| `preflight-demo-result.txt` | 预检真实输出（退出码 2，阻断） |
| `aeroleads-constrained-plan.md` | 本流程方案文档 |

---

## 十一、实际读取的 Skill 文件

- `aeroleads-automation/aeroleads-automation/SKILL.md`（相对路径，相对于解压根目录 `aeroleads-automation/`）

### 实际影响交付结果的 SKILL.md 规则

**"Always search first: Tool schemas change. Never hardcode tool slugs or arguments without calling RUBE_SEARCH_TOOLS"**（Known Pitfalls 第一条）。

这条规则直接决定了本方案的形态：由于 `RUBE_SEARCH_TOOLS` 在当前环境不可用，我**不能**凭 Composio 文档或常识硬编码 tool slug（如 `AEROLEADS_GET_DETAILS_FROM_LINKEDIN_URL`）和参数字段名来"演示"一次调用——那将违反 Skill 规则并构成编造。因此本次唯一可核验的真实执行被限定为预检，执行流程以"就绪后可运行"的设计交付，而非伪造的 API 调用结果。
