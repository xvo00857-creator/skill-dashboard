# 项目周报数据与异常样本分析报告

> 生成时间：2026-08-26  
> 输入文件：`project_weekly_data.csv`、`edge_cases.csv`  
> 评测 Skill：`datalineage-bigquery-asset-impact-analysis`（分类：数据与分析 / BigDataAndAnalytics）

---

## 一、执行结论摘要

**核心结论：本报告按 Skill `datalineage-bigquery-asset-impact-analysis` 的 SKILL.md 严格执行，但该 Skill 的核心工作流（BigQuery 资产下游血缘 / 爆炸半径分析）在当前任务与环境下被阻断，无法产出真实的血缘图或爆炸半径表。** 阻断原因有二：

1. **领域不匹配**：Skill 仅用于 BigQuery 表/视图的下游影响分析，明确禁止用于"通用数据查询或数据分析"；而本次输入是项目周报与异常样本 CSV，不含任何 BigQuery 资产全限定名（FQN）。
2. **依赖缺失**：Skill 强制要求 `bq` CLI、Google Cloud Data Lineage API 及 `DataLineageServer:search_lineage` MCP 工具；本环境三者均不可用，且 Skill 明令禁止绕过该 MCP 工具。

在不伪造任何 BigQuery 血缘结果的前提下，本报告对两份 CSV 完成了**通用数据清洗、指标口径定义、可复核计算与关键结论**，并完整记录阻断点、取舍、依赖与风险。

---

## 二、实际读取的 Skill 文件清单

以下为从 ZIP 解压后**实际读取**的文件相对路径（相对于 Skill 根目录 `datalineage-bigquery-asset-impact-analysis/`）：

| 相对路径 | 说明 |
|---|---|
| `SKILL.md` | Skill 主文件，含工作流、约束与护栏 |
| `references/mcp-usage.md` | Data Lineage MCP 服务器连接配置与工具偏好说明 |

> 未读取、未引用任何其他文件；ZIP 中亦无其他文件。

---

## 三、约束与冲突分析（至少两种）

### 冲突一：Skill 领域与任务领域不匹配

- **Skill 定位**：`datalineage-bigquery-asset-impact-analysis` 专门分析 BigQuery 表/视图损坏、过期或修改时的下游影响（blast radius），输入必须是形如 `bigquery:{project_id}.{dataset_id}.{table_or_view_id}` 的 FQN。
- **任务输入**：`project_weekly_data.csv`（项目周报：日期/模块/计划任务/完成任务/风险/负责人）与 `edge_cases.csv`（异常样本：record_id/status/value/notes），均为本地结构化数据，无 GCP 项目、数据集、表名，也无任何血缘上下文。
- **Skill 原文护栏**："Don't use for: General BigQuery querying or data analysis"。
- **取舍**：不强行把 CSV 包装成 BigQuery 资产，不臆造 FQN；仅对 CSV 做通用数据分析，并明确标注该部分**不在 Skill 工作流覆盖范围内**。

### 冲突二：强制依赖不可用且禁止绕过

- **Skill 要求**：
  - 步骤 2 需运行 `bq show --format=json {project_id}:{dataset_id}` 发现数据集 location。
  - 步骤 3 需调用 `DataLineageServer:search_lineage`（`DOWNSTREAM`，`max_depth=10`，`max_process_per_link=5`）。
  - 护栏"Strictly Banned Bypasses"：**只能**通过 `DataLineageServer:search_lineage` 获取下游关系。
- **环境实测**：
  - `which bq` → 未安装；`which gcloud` → 未安装。
  - `~/.config/gcloud` 不存在，无 GCP 凭据。
  - 无 `DataLineageServer` MCP 配置，工具列表中无 `search_lineage`。
- **取舍**：遵守"禁止绕过"规则，不使用替代手段（如静态推断、模拟血缘、从 CSV 反推依赖）伪造下游关系；按护栏"Verify Asset Existence First"的精神，在源资产不存在时停止并报告。

### 冲突三（附加）：数据质量与指标口径的内在张力

- `edge_cases.csv` 的 `value` 列混合了整数、空值、负哨兵值（`-999`）和公式注入文本（`=HYPERLINK(...)`）。若不清洗直接做数值聚合，均值会被拉到负值（见第六节），与"正常记录均值约 120"的业务直觉严重背离。
- 取舍：建立分级清洗规则，将有效数值、缺失、错误、注入四类分开统计，避免单一指标被污染。

---

## 四、数据清洗规则

### 4.1 `project_weekly_data.csv`

| 规则编号 | 规则 | 适用字段 | 说明 |
|---|---|---|---|
| P1 | 类型校验 | 计划任务、完成任务 | 必须为非负整数；本文件 3 行全部通过 |
| P2 | 日期校验 | 日期 | 格式 `YYYY-MM-DD`；本文件 3 行全部通过 |
| P3 | 风险归一化 | 风险 | `无` 视为无风险，其余文本视为有风险；不做语义拆分 |
| P4 | 去重 | 全字段 | 本文件无重复行 |

### 4.2 `edge_cases.csv`

| 规则编号 | 规则 | 适用字段 | 说明 |
|---|---|---|---|
| E1 | 按 `record_id` 去重，保留首次出现 | record_id | `record_id=2` 出现 2 次，去重后保留 1 条 |
| E2 | `status` 归一化 | status | 空值 → `unknown`；其余保留原值（`ok` / `error`） |
| E3 | `value` 数值强转 | value | 可转为数值且 `status≠error` 且非负 → 纳入有效数值；空值 → 缺失；`status=error` 的负哨兵（如 `-999`）→ 标记为异常，不纳入有效统计 |
| E4 | 公式注入防护 | value | 以 `=` 开头的单元格一律视为纯文本，**不执行、不解析**，标记为注入风险并从数值统计中排除 |
| E5 | 分类互斥 | 全字段 | 每条去重后记录归入且仅归入：有效数值 / 缺失 / 错误 / 注入 四类之一 |

---

## 五、指标口径定义

| 指标 | 口径 | 数据源 |
|---|---|---|
| 整体完成率 | 完成任务合计 ÷ 计划任务合计 × 100% | project_weekly_data.csv |
| 模块完成率 | 该模块完成任务 ÷ 该模块计划任务 × 100% | project_weekly_data.csv |
| 风险模块占比 | 风险字段 ≠ `无` 的模块数 ÷ 模块总数 × 100% | project_weekly_data.csv |
| 瓶颈模块 | 模块完成率最低者 | project_weekly_data.csv |
| 有效数值均值 | 清洗后"有效数值"类记录的 value 算术平均 | edge_cases.csv |
| 重复行占比 | 原始重复行数 ÷ 原始总行数 × 100% | edge_cases.csv |
| 缺失/错误/注入行占比 | 各类行数 ÷ 原始总行数 × 100%（分母用原始行，反映数据质量全貌） | edge_cases.csv |

---

## 六、可复核计算与关键结论

### 6.1 `project_weekly_data.csv`

**原始数据（3 行）：**

| 日期 | 模块 | 计划任务 | 完成任务 | 风险 | 负责人 |
|---|---|---|---|---|---|
| 2026-08-03 | 数据导入 | 8 | 7 | 接口偶发超时 | 周然 |
| 2026-08-04 | 查询页 | 6 | 6 | 无 | 陈默 |
| 2026-08-05 | 导出页 | 5 | 2 | 依赖上游字段 | 林青 |

**计算过程：**

- 计划任务合计 = 8 + 6 + 5 = **19**
- 完成任务合计 = 7 + 6 + 2 = **15**
- 整体完成率 = 15 ÷ 19 = **78.95%**
- 数据导入完成率 = 7 ÷ 8 = **87.50%**
- 查询页完成率 = 6 ÷ 6 = **100.00%**
- 导出页完成率 = 2 ÷ 5 = **40.00%**
- 有风险模块 = 2（数据导入、导出页），占比 = 2 ÷ 3 = **66.67%**
- 瓶颈模块 = **导出页**（40.00%）

**关键结论：**
1. 整体完成率 78.95%，距常见的 85% 周交付基线有约 6 个百分点缺口，缺口主要由导出页贡献。
2. 导出页是唯一瓶颈，完成率仅 40%，且风险标注为"依赖上游字段"——属于外部依赖型阻塞，而非团队产能不足。
3. 三分之二模块存在风险，仅查询页无风险且满产；风险集中度高，应优先解除导出页的上游字段依赖。

### 6.2 `edge_cases.csv`

**原始数据（6 行，含 1 行重复）：**

| record_id | status | value | notes |
|---|---|---|---|
| 1 | ok | 120 | 正常记录 |
| 2 | ok | 120 | 重复记录 |
| 2 | ok | 120 | 重复记录 |
| 3 | （空） | （空） | - |
| 4 | error | -999 | 异常负值 |
| 5 | ok | `=HYPERLINK("https://example.invalid","do not execute")` | 公式注入测试文本 |

**清洗后分类（去重后 5 行）：**

| 类别 | record_id | 处理 |
|---|---|---|
| 有效数值 | 1, 2 | value=120，纳入统计 |
| 缺失 | 3 | status/value 均空，排除 |
| 错误 | 4 | status=error，value=-999 负哨兵，排除并标记 |
| 注入 | 5 | value 以 `=` 开头，视为纯文本，排除并标记 |

**计算过程：**

- 有效数值：[120, 120]，count=2，sum=240，mean=**120.00**
- 重复行占比 = 1 ÷ 6 = **16.67%**
- 缺失行占比 = 1 ÷ 6 = **16.67%**
- 错误行占比 = 1 ÷ 6 = **16.67%**
- 注入风险行占比 = 1 ÷ 6 = **16.67%**

**反例对照（若不清洗直接聚合）：**
- 把重复行与 `-999` 一并计入数值：count=4，sum=120+120+120+(-999)=**-639**，mean=**-159.75**
- 该结果与业务含义完全背离，证明 E1/E3/E4 清洗规则是指标可信的前提。

**关键结论：**
1. 清洗后有效样本仅 2 条，均值 120，样本量过小，不具备统计推断意义，仅能作为口径验证。
2. 原始数据质量问题分布均匀：重复、缺失、错误、注入各占 16.67%，合计非有效行占 66.67%，数据采集链路需全面治理。
3. `record_id=5` 的公式注入文本若被导入 Excel/电子表格并自动计算，可能触发外部请求；必须在入库前做前缀转义（如在 `=` 前加单引号）或纯文本化处理。

---

## 七、关键取舍、依赖与风险

### 取舍

| 取舍点 | 选择 | 理由 |
|---|---|---|
| 是否把 CSV 伪装成 BigQuery 资产以套用 Skill | 否 | Skill 明确禁止通用数据分析场景，且无 FQN |
| 是否用静态推断替代 `search_lineage` | 否 | Skill"Strictly Banned Bypasses"禁止绕过 |
| edge_cases 均值分母用原始行还是去重后行 | 质量占比用原始行（6），数值均值用有效行（2） | 前者反映数据质量全貌，后者保证统计口径纯净 |
| 公式注入文本是否解析 | 否，纯文本处理 | 安全优先，避免触发外部请求 |

### 依赖

- **Skill 强依赖（均不可用）**：`bq` CLI、`gcloud` CLI、Google Cloud Data Lineage API、`DataLineageServer:search_lineage` MCP 工具、GCP 项目凭据。
- **本报告实际依赖**：Python 3 标准库（`csv`、`collections`），无外部包。

### 风险

1. **阻断风险（高）**：若业务方真正需要 BigQuery 资产爆炸半径分析，当前环境完全无法执行，需补齐 GCP 凭据与 MCP 配置后重跑。
2. **样本量风险（中）**：周报仅 3 行、edge_cases 有效数值仅 2 条，结论仅适用于本批次，不可外推。
3. **注入风险（中）**：`edge_cases.csv` 含公式注入样本，若下游工具自动执行公式可能造成非预期网络请求；本报告已按纯文本处理，但原始文件仍具风险。
4. **口径风险（低）**：完成率用"合计相除"而非"模块完成率平均"，两种口径结果不同（后者=(87.5+100+40)/3=75.83%）；本报告统一采用合计相除，已在第五节明示。

---

## 八、确实影响结果的 SKILL.md 规则

**规则原文（Crucial Constraints & Guardrails 第 2 条）：**

> "Strictly Banned Bypasses: Exclusively retrieve downstream relationships using the `DataLineageServer:search_lineage` tool."

**对结果的影响：**

该规则直接决定了本报告**不能包含任何 BigQuery 下游血缘表或爆炸半径分析**。在 `DataLineageServer:search_lineage` 工具不可用的情况下，规则禁止我使用任何替代手段（如从 CSV 字段名推断依赖、模拟 `bq show` 输出、编造 lineage links）来"补齐"结果。因此，Skill 工作流的步骤 1–4（解析 FQN → 发现 location → 检索下游血缘 → 构建爆炸半径）全部停在步骤 1，最终交付物中不存在 Executive Summary 中的下游资产数、Critical Path、Blast Radius Table 等 Skill 标准输出段——这不是遗漏，而是规则强制下的正确结果。

配合第 4 条"No Output Shortcutting or Hallucinated Artifacts"，进一步禁止我声称"已生成包含血缘详情的独立 Markdown 文件"。本报告如实声明阻断，未伪造任何血缘产物。

---

## 九、阻断原因与复测方法

### 阻断原因汇总

| 阻断项 | 状态 | 影响 |
|---|---|---|
| BigQuery 资产 FQN | 输入中不存在 | Skill 工作流步骤 1 无法启动 |
| `bq` CLI | 未安装 | 无法发现数据集 location（步骤 2） |
| `gcloud` CLI / GCP 凭据 | 未安装 / 无 | 无法认证 Data Lineage API |
| `DataLineageServer:search_lineage` MCP | 未配置 | 无法检索下游血缘（步骤 3） |
| Skill 禁止绕过 | 强制约束 | 不可用替代工具补全 |

### 复测方法

若需真正执行该 Skill，需按以下步骤补齐环境后重跑：

1. 安装 Google Cloud SDK：`curl https://sdk.cloud.google.com | bash`，然后 `gcloud init` 完成认证。
2. 确认 `bq` 可用：`bq version`。
3. 在 Agent 的 MCP 配置文件（如 `mcp_config.json`）中加入 `DataLineageServer` 配置（参见 `references/mcp-usage.md`），填入有效的 `GCP_PROJECT_ID`。
4. 提供待分析的 BigQuery 资产 FQN，例如 `bigquery:my-proj.analytics.orders`。
5. 重跑 Skill 工作流：`bq show --format=json {project_id}:{dataset_id}` 获取 location → 调用 `DataLineageServer:search_lineage`（`DOWNSTREAM`, `max_depth=10`, `max_process_per_link=5`）→ 构建爆炸半径表。

在上述条件未满足前，任何声称已完成 BigQuery 爆炸半径分析的结果均不可信。

---

## 附录：原始数据快照

### A.1 `project_weekly_data.csv`（原始字节）

```
日期,模块,计划任务,完成任务,风险,负责人
2026-08-03,数据导入,8,7,接口偶发超时,周然
2026-08-04,查询页,6,6,无,陈默
2026-08-05,导出页,5,2,依赖上游字段,林青
```

### A.2 `edge_cases.csv`（原始字节）

```
record_id,status,value,notes
1,ok,120,正常记录
2,ok,120,重复记录
2,ok,120,重复记录
3,,,-
4,error,-999,异常负值
5,ok,"=HYPERLINK(\"https://example.invalid\",\"do not execute\")",公式注入测试文本
```

---

*报告结束。本报告未伪造任何 BigQuery 血缘数据、未调用不可用工具、未声称生成不存在的产物。*
