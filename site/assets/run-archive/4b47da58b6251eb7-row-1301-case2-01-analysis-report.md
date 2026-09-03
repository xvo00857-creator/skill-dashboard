# 项目周报数据与异常样本分析报告

> 产物文件：`analysis-report.md`
> 生成时间基准：2026-08-26（UTC+0）
> 执行依据：随消息上传的 Skill `google-cloud-storage-basics` 的 `SKILL.md`（唯一执行依据）

---

## 1. 数据来源与实际读取范围

### 1.1 业务数据文件

| 文件 | 行数（含表头） | 说明 |
|---|---|---|
| `project_weekly_data.csv` | 4 | 文件首行为字面量 `csv`，其后为 Markdown 表格语法；实际数据 3 行 |
| `edge_cases.csv` | 7 | 标准 CSV，含表头共 6 条记录 |

### 1.2 实际读取的 Skill 文件相对路径

仅读取以下文件，未读取的 reference 文件内容不被引用、不被编造：

- `google-cloud-storage-basics/SKILL.md`

`references/` 目录下的 10 个文件（`core-concepts.md`、`cli-api-usage.md`、`client-library-usage.md`、`mcp-usage.md`、`iac-usage.md`、`data-transfer.md`、`data-management.md`、`storage-intelligence.md`、`high-performance-storage.md`、`gcsfuse.md`）仅在 `SKILL.md` 的 Reference Directory 中被列出，本次未打开，故本报告不引用其中任何具体内容。

---

## 2. SKILL.md 关键规则及其对结果的实际影响

本报告识别出三条确实影响执行方式或结果口径的 `SKILL.md` 规则：

### 规则 A：不可变对象 / 整对象读写模型（影响最大）

> 原文："You read and write whole objects rather than querying or updating individual records in place. It stores immutable objects in buckets..."

**对结果的影响**：数据清洗不能对原始 CSV 做行级原地修改。本报告将原始文件视为不可变源对象，所有清洗结果写入新的派生对象/文件，原始字节保持不变。这直接决定了第 4 节"清洗规则"采用"生成清洗后副本"而非"覆盖原文件"的方案。

### 规则 B：命令归因（Attribution）必须内联，禁止 `gcloud config set`

> 原文：每条 `gcloud` 命令必须内联设置 `CLOUDSDK_METRICS_ENVIRONMENT="gcs-skills gcs-skills/1.0 (skill:google-cloud-storage-basics)"`；"Do not use `gcloud config set` for this"；HTTP 调用必须使用精确 `User-Agent: gcs-skills/1.0 (skill:google-cloud-storage-basics)`。

**对结果的影响**：第 8 节给出的所有示例 `gcloud` / `curl` 命令均按此规则内联归因，未使用 `gcloud config set`。若忽略此规则，命令虽可运行但会被错误归因，属于不合规执行。

### 规则 C：MCP 优先，无 MCP 时回退 CLI/JSON API

> 原文："If a Cloud Storage MCP server is connected, prefer its structured tools... Fall back to `gcloud storage` and the JSON API when no MCP server is available."

**对结果的影响**：当前环境未连接 Cloud Storage MCP 服务器，且无 GCP 凭据，因此既不使用 MCP 工具也不实际执行 CLI/API，仅在第 8 节给出合规的回退命令模板。

---

## 3. 数据清洗规则

### 3.1 `project_weekly_data.csv`

| 问题 | 规则 | 处理 |
|---|---|---|
| 文件首行字面量 `csv` | 非数据行，跳过 | 丢弃首行 |
| Markdown 表格分隔行 `\|---\|...\|` | 非数据行，跳过 | 丢弃分隔行 |
| 日期格式 `YYYY-MM-DD` | 校验可解析 | 3 行均合法，保留 |
| 计划任务 / 完成任务为非负整数 | 校验 `完成 ≤ 计划` | 3 行均满足，保留 |
| 风险列含中文描述 | 文本字段，不做数值化 | 原样保留 |
| 负责人列 | 文本字段 | 原样保留 |

清洗后有效记录：**3 条**，无丢弃。

### 3.2 `edge_cases.csv`

| record_id | 原始问题 | 清洗规则 | 处理结果 |
|---|---|---|---|
| 1 | 正常 | — | 保留，value=120 |
| 2 | 完全重复（出现 2 次） | 按 `record_id` 去重，保留首条 | 保留 1 条，value=120 |
| 3 | status 为空、value 为空、notes="-" | 必填字段 status/value 缺失 → 排除 | 排除 |
| 4 | status=error，value=-999 | error 状态记录不进入数值聚合；负值在 ok 口径下非法 | 排除出聚合，单独标记 |
| 5 | value 为 `=HYPERLINK(...)` 公式注入文本 | 公式前缀 `=` 属于注入风险，不作为数值；中性化处理（去除前导 `=` 或加单引号转义）后仅作文本留存 | 排除出数值聚合，标记为安全事件 |

清洗后可进入数值聚合的有效记录：**2 条**（record_id 1、2）。
被排除/标记记录：**3 条**（record_id 3 缺失、4 错误负值、5 公式注入）。

---

## 4. 指标口径

| 指标 | 口径定义 | 分母 |
|---|---|---|
| 模块完成率 | 完成任务 ÷ 计划任务 × 100% | 该模块计划任务数 |
| 整体完成率 | Σ完成任务 ÷ Σ计划任务 × 100%（按任务数加权，非模块平均） | 全部计划任务之和 |
| 异常样本有效值均值 | 清洗后 ok 且数值合法记录的 value 算术平均 | 去重且通过校验的记录数 |
| 数据合格率 | 清洗后有效记录数 ÷ 原始记录数 × 100% | 原始记录数（不含表头） |

**口径取舍说明**：整体完成率采用任务数加权而非模块简单平均。若用模块平均，结果为 (87.5%+100%+40%)/3 = 75.83%，会低估"导出页"因计划量小但拖累有限的实际影响；任务数加权更贴近真实交付进度。

---

## 5. 可复核计算

### 5.1 周报完成率

| 日期 | 模块 | 计划 | 完成 | 完成率 |
|---|---|---|---|---|
| 2026-08-03 | 数据导入 | 8 | 7 | 7 ÷ 8 = **87.50%** |
| 2026-08-04 | 查询页 | 6 | 6 | 6 ÷ 6 = **100.00%** |
| 2026-08-05 | 导出页 | 5 | 2 | 2 ÷ 5 = **40.00%** |
| **合计** | — | **19** | **15** | **15 ÷ 19 = 78.95%** |

### 5.2 异常样本数值聚合

- 原始记录数：6
- 去重后：5（record_id 2 由 2 条合并为 1 条）
- 排除缺失（record_id 3）：剩 4
- 排除 error 负值（record_id 4）：剩 3
- 排除公式注入文本（record_id 5）：剩 **2** 条有效数值记录
- 有效 value 集合：{120, 120}
- 有效值均值：(120 + 120) ÷ 2 = **120**
- 数据合格率：2 ÷ 6 = **33.33%**

**反事实校验（若不清洗）**：若将 record_id 4 的 -999 纳入，均值 = (120+120-999) ÷ 3 = **-253**，结论完全反转。这直接证明清洗规则对结果有决定性影响。

### 5.3 风险分布

- 含风险记录：2/3（数据导入"接口偶发超时"、导出页"依赖上游字段"）
- 无风险记录：1/3（查询页）
- 完成率低于 50% 的模块：1/3（导出页，40%）

---

## 6. 关键结论

1. **整体交付进度 78.95%**，未达预期，主要拖累来自导出页（40%）。
2. **导出页是唯一高风险模块**：既存在外部依赖（上游字段），完成率又最低，二者可能存在因果关系——上游字段未就绪直接导致任务无法完成。建议优先排查上游依赖。
3. **数据导入存在性能隐患**：完成率 87.5% 尚可，但"接口偶发超时"若在高峰期放大，可能演变为系统性风险。
4. **查询页是健康标杆**：100% 完成且无风险，可作为流程复用参考。
5. **异常样本数据质量差**：6 条中仅 2 条可直接用于数值聚合（合格率 33.33%），存在重复、缺失、非法负值和公式注入四类问题。其中公式注入（record_id 5）若未经清洗直接存入对象存储并被下游表格工具打开，存在代码执行风险。
6. **负值 -999 是典型哨兵值/错误码误用**：不应混入业务数值字段，建议在数据接入层增加值域校验。

---

## 7. 约束、冲突与取舍（至少两种）

### 冲突一：GCS 不可变对象模型 vs. 迭代式数据清洗

- **冲突**：`SKILL.md` 明确 GCS 以整对象、不可变方式存储，不支持行级原地更新。但数据清洗天然是逐行判断、逐行修正的迭代过程。
- **取舍**：采用"原始对象不可变 + 派生清洗对象"方案。原始 CSV 保持只读，清洗逻辑输出新文件（如 `edge_cases_cleaned.csv`），通过对象命名或元数据版本区分。代价是存储量翻倍（原始+清洗后各一份），收益是可追溯、可复算、符合 GCS 语义。
- **依赖**：需要约定对象命名规范（如 `raw/` 与 `cleaned/` 前缀）和生命周期规则。
- **风险**：若下游误读原始对象而非清洗后对象，结论会出错；需在访问控制或文档中明确唯一可信源。

### 冲突二：公式注入负载 vs. GCS 透传存储

- **冲突**：GCS 按字节透传存储，不做内容消毒。`edge_cases.csv` 中 record_id 5 的 `=HYPERLINK(...)` 若原样存入并被下载到 Excel/Sheets 打开，可能触发公式执行。
- **取舍**：在写入 GCS 前的清洗阶段中性化公式（去除前导 `=` 或加单引号前缀），并将该条记录标记为安全事件单独留存。代价是改变了原始字节（因此必须存入新对象，与冲突一的方案一致），收益是消除下游执行风险。
- **依赖**：清洗脚本必须覆盖所有公式触发字符（`=`, `+`, `-`, `@` 等），不能只处理 `=`。
- **风险**：若仅在展示层转义而存储层仍保留原始公式，风险未真正消除；必须在持久化前处理。

### 约束三：无 GCP 凭据与项目（执行阻断，非分析阻断）

- **现状**：当前环境未提供 GCP 项目 ID、服务账号密钥或 OAuth 凭据，也未连接 Cloud Storage MCP 服务器。
- **影响**：无法实际执行 `gcloud storage buckets create`、`gcloud storage cp` 或 JSON API 上传。本报告的分析与本地文件产物不受影响，但"将报告上传至 GCS bucket"这一步无法真实完成。
- **复测方法**：具备凭据后，执行第 8 节命令模板，将 `analysis-report.md` 上传至指定 bucket，并验证对象大小与 MD5 与本地一致。

---

## 8. GCS 操作命令模板（合规归因，未实际执行）

以下命令仅为模板，**未在本次执行中实际运行**（原因见第 7 节约束三）。所有命令均按 `SKILL.md` 规则 B 内联归因。

### 8.1 启用 API

```bash
CLOUDSDK_METRICS_ENVIRONMENT="gcs-skills gcs-skills/1.0 (skill:google-cloud-storage-basics)" \
gcloud services enable storage.googleapis.com --quiet
```

### 8.2 创建 Bucket（显式指定 location，避免默认 US 多区域）

```bash
CLOUDSDK_METRICS_ENVIRONMENT="gcs-skills gcs-skills/1.0 (skill:google-cloud-storage-basics)" \
gcloud storage buckets create gs://<your-bucket-name> --location=us-central1
```

> 注意：`SKILL.md` 指出 bucket 名称位于全局命名空间，常用名大概率已被占用；若省略 `--location`，默认创建在 `US` 多区域。

### 8.3 上传报告对象

```bash
CLOUDSDK_METRICS_ENVIRONMENT="gcs-skills gcs-skills/1.0 (skill:google-cloud-storage-basics)" \
gcloud storage cp ./analysis-report.md gs://<your-bucket-name>/reports/
```

### 8.4 JSON API 上传（curl，精确 User-Agent）

```bash
curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "User-Agent: gcs-skills/1.0 (skill:google-cloud-storage-basics)" \
  -H "Content-Type: text/markdown" \
  --data-binary @analysis-report.md \
  "https://storage.googleapis.com/upload/storage/v1/b/<your-bucket-name>/o?uploadType=media&name=reports/analysis-report.md"
```

---

## 9. 依赖与风险汇总

| 类别 | 项 | 说明 |
|---|---|---|
| 依赖 | 上游字段交付 | 导出页完成率直接受此影响，是当前最大外部依赖 |
| 依赖 | GCP 凭据与项目 | 上传至 GCS 的前置条件，当前缺失 |
| 依赖 | 清洗脚本公式字符覆盖度 | 需覆盖 `= + - @` 等触发字符，不能只处理 `=` |
| 风险 | 误读原始对象 | 下游若读取 raw 而非 cleaned，结论会被重复值、负值、注入文本污染 |
| 风险 | 公式注入下游执行 | 未经中性化的 CSV 被表格工具打开时可能触发恶意公式 |
| 风险 | 哨兵值 -999 混入 | 若接入层无值域校验，错误码会被当作业务值聚合 |
| 风险 | bucket 命名冲突 | 全局命名空间下短名称易被占用，需准备备选名称 |
| 风险 | 默认区域不合规 | 省略 location 时默认 US 多区域，可能违反数据驻留要求 |

---

## 10. 附录：清洗后数据

### 10.1 周报（清洗后，3 条）

| 日期 | 模块 | 计划任务 | 完成任务 | 风险 | 负责人 |
|---|---|---|---|---|---|
| 2026-08-03 | 数据导入 | 8 | 7 | 接口偶发超时 | 周然 |
| 2026-08-04 | 查询页 | 6 | 6 | 无 | 陈默 |
| 2026-08-05 | 导出页 | 5 | 2 | 依赖上游字段 | 林青 |

### 10.2 异常样本（清洗后，可聚合 2 条）

| record_id | status | value | notes |
|---|---|---|---|
| 1 | ok | 120 | 正常记录 |
| 2 | ok | 120 | 重复记录（已去重） |

被排除记录：record_id 3（缺失）、record_id 4（error/-999）、record_id 5（公式注入文本，已中性化后仅作文本留存）。

---

*报告结束。本报告所有数值均可通过第 5 节公式复算；所有 GCS 命令均符合 `google-cloud-storage-basics/SKILL.md` 的归因规则，但因缺少 GCP 凭据未实际执行。*
