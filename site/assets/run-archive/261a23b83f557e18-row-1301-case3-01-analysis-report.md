# 项目周报数据与异常样本分析报告

> 生成时间：2026-08-26
> 依据 Skill：google-cloud-storage-basics（v1，publisher: google，metadata.category: Storage）
> 输入文件：project_weekly_data.csv、edge_cases.csv

---

## 一、执行环境与 Skill 适配性判定

### 1.1 实际读取的 Skill 文件清单（相对路径，基于解压根目录）

| 序号 | 相对路径 |
|------|----------|
| 1 | google-cloud-storage-basics/SKILL.md |
| 2 | google-cloud-storage-basics/references/core-concepts.md |
| 3 | google-cloud-storage-basics/references/cli-api-usage.md |
| 4 | google-cloud-storage-basics/references/client-library-usage.md |
| 5 | google-cloud-storage-basics/references/data-management.md |
| 6 | google-cloud-storage-basics/references/data-transfer.md |
| 7 | google-cloud-storage-basics/references/gcsfuse.md |
| 8 | google-cloud-storage-basics/references/high-performance-storage.md |
| 9 | google-cloud-storage-basics/references/iac-usage.md |
| 10 | google-cloud-storage-basics/references/mcp-usage.md |
| 11 | google-cloud-storage-basics/references/storage-intelligence.md |

共 11 个文件，全部已读取。

### 1.2 环境探测结果（证据）

| 探测项 | 命令/方式 | 结果 |
|--------|-----------|------|
| gcloud CLI | `which gcloud` | 未安装 |
| gsutil CLI | `which gsutil` | 未安装 |
| Google 凭据目录 | `ls ~/.config/gcloud/` | 不存在 |
| 环境变量凭据 | `env \| grep -i google` | 无 GOOGLE_APPLICATION_CREDENTIALS 等 |
| MCP 服务器 | 运行环境检查 | 未连接任何 Cloud Storage MCP 服务器 |

### 1.3 阻断结论与降级方案

**阻断项**：本 Skill（google-cloud-storage-basics）的核心能力是对 Google Cloud Storage 桶和对象执行创建、上传、下载、列表、权限配置等操作。上述操作全部依赖 gcloud CLI 或 MCP 服务器或客户端库 + ADC 凭据，当前环境三者皆无，因此**无法执行任何真实的 GCS 操作**（无法创建桶、无法上传报告到 GCS、无法读取 GCS 中的数据、无法配置 IAM/生命周期等）。

**降级方案**：
1. 数据分析部分完全在本地完成，不依赖 GCS。
2. 最终产物以本地文件 `analysis-report.md` 交付，而非上传至 `gs://` 桶。
3. 若后续需要将报告存入 GCS，需先满足前置条件（见第七节复测方法）。

**这是 SKILL.md 规则直接影响结果的第一条**：SKILL.md "Quick Start" 明确要求"优先使用 MCP 结构化工具，无 MCP 时回退到 gcloud storage 和 JSON API"；当前既无 MCP 也无 gcloud 凭据，故所有 GCS 路径均不可达，只能本地交付。

---

## 二、数据文件原始内容与格式问题

### 2.1 project_weekly_data.csv

**原始内容**（文件首行是字面量 `csv`，随后是空行，再后是 Markdown 表格，并非标准逗号分隔值）：

```
csv

|日期|模块|计划任务|完成任务|风险|负责人|
|---|---|---|---|---|---|
|2026-08-03|数据导入|8|7|接口偶发超时|周然|
|2026-08-04|查询页|6|6|无|陈默|
|2026-08-05|导出页|5|2|依赖上游字段|林青|
```

**格式问题识别**：
- 文件扩展名为 `.csv`，但内容不是 CSV 格式，而是 Markdown 表格 + 首行冗余字面量 `csv`。
- 首行 `csv` 无字段含义，属于噪声行。
- 分隔符为 `|` 而非逗号，且首尾各有一个 `|`，解析时需去除。
- 第二行（`|---|---|...`）是 Markdown 分隔行，非数据。

### 2.2 edge_cases.csv

**原始内容**（标准 CSV，含引号转义）：

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

## 三、数据清洗规则

### 3.1 project_weekly_data.csv 清洗规则

| 规则编号 | 规则描述 | 处理方式 |
|----------|----------|----------|
| P1 | 首行字面量 `csv` 为噪声 | 删除该行 |
| P2 | 空行 | 删除 |
| P3 | Markdown 表头行（`\|日期\|...\|`） | 提取为字段名，去除首尾 `\|` 后按 `\|` 分割 |
| P4 | Markdown 分隔行（`\|---\|...\|`） | 删除 |
| P5 | 数据行首尾 `\|` | 去除后按 `\|` 分割为字段 |
| P6 | `计划任务`、`完成任务` 字段 | 转为整数 |
| P7 | `日期` 字段 | 校验为 `YYYY-MM-DD` 格式，三条记录均合法 |
| P8 | 重复行检测 | 按 (日期, 模块) 联合主键检测，无重复 |

**清洗后有效数据**（3 条）：

| 日期 | 模块 | 计划任务 | 完成任务 | 风险 | 负责人 |
|------|------|----------|----------|------|--------|
| 2026-08-03 | 数据导入 | 8 | 7 | 接口偶发超时 | 周然 |
| 2026-08-04 | 查询页 | 6 | 6 | 无 | 陈默 |
| 2026-08-05 | 导出页 | 5 | 2 | 依赖上游字段 | 林青 |

### 3.2 edge_cases.csv 清洗规则

| 规则编号 | 规则描述 | 处理方式 | 影响记录 |
|----------|----------|----------|----------|
| E1 | 重复记录（record_id 完全相同且所有字段一致） | 去重，保留 1 条 | record_id=2（2 条→1 条） |
| E2 | 缺失值（status 和 value 均为空） | 标记为无效，不纳入数值聚合 | record_id=3 |
| E3 | 错误状态记录（status=error） | 标记为异常，不纳入数值聚合 | record_id=4 |
| E4 | 异常负值（value=-999，且 status=error） | 与 E3 联动排除；若单独出现负值需结合业务阈值判断 | record_id=4 |
| E5 | 公式注入（value 以 `=` 开头，含 HYPERLINK） | **视为不安全输入，不执行、不解析公式，仅作为纯文本标记并隔离**；数值聚合时排除 | record_id=5 |
| E6 | 有效记录判定 | status=ok 且 value 可解析为非负数值 | record_id=1, 2（去重后） |

**清洗后有效记录**（2 条，去重后）：

| record_id | status | value | notes |
|-----------|--------|-------|-------|
| 1 | ok | 120 | 正常记录 |
| 2 | ok | 120 | 重复记录（去重保留 1 条） |

**被排除/隔离记录**（4 条原始行，去重后 3 个唯一 record_id）：

| record_id | 原因 | 处置 |
|-----------|------|------|
| 2（重复行） | 与另一条 record_id=2 完全重复 | 去重删除 |
| 3 | status 和 value 均缺失 | 标记无效，不纳入聚合 |
| 4 | status=error，value=-999 异常负值 | 标记异常，不纳入聚合 |
| 5 | value 为 `=HYPERLINK(...)` 公式注入文本 | 隔离为不安全输入，纯文本保留，不执行不聚合 |

---

## 四、指标口径

### 4.1 项目周报指标

| 指标 | 口径定义 | 计算公式 |
|------|----------|----------|
| 计划任务总数 | 清洗后所有行的 `计划任务` 之和 | Σ(计划任务) |
| 完成任务总数 | 清洗后所有行的 `完成任务` 之和 | Σ(完成任务) |
| 整体完成率 | 完成任务总数 / 计划任务总数 × 100% | Σ(完成) / Σ(计划) × 100% |
| 模块完成率 | 单模块完成任务 / 该模块计划任务 × 100% | 按模块分组计算 |
| 风险模块占比 | 风险字段不为"无"的模块数 / 总模块数 × 100% | count(风险≠无) / count(模块) × 100% |

### 4.2 异常样本指标

| 指标 | 口径定义 |
|------|----------|
| 原始记录数 | CSV 数据行总数（不含表头） |
| 唯一 record_id 数 | 去重后的 record_id 个数 |
| 重复行数 | 原始行数 - 唯一 record_id 数（当重复行完全一致时） |
| 有效数值记录数 | status=ok 且 value 为合法非负数值的记录数（去重后） |
| 有效 value 之和 | 有效记录的 value 求和 |
| 有效 value 均值 | 有效 value 之和 / 有效数值记录数 |
| 缺失记录数 | status 或 value 为空的记录数 |
| 异常记录数 | status=error 或 value 超出业务合理范围的记录数 |
| 不安全输入数 | value 以 `=`、`+`、`-`、`@` 开头等可能触发公式注入的记录数 |

---

## 五、关键结论与可复核计算

### 5.1 项目周报结论

**计算过程（已通过计算器验证）**：

- 计划任务总数 = 8 + 6 + 5 = **19**
- 完成任务总数 = 7 + 6 + 2 = **15**
- 整体完成率 = 15 / 19 × 100% = **78.95%**（精确值 78.9474%）

**分模块完成率**：

| 模块 | 计划 | 完成 | 完成率 | 风险 |
|------|------|------|--------|------|
| 数据导入 | 8 | 7 | 87.50% | 接口偶发超时 |
| 查询页 | 6 | 6 | 100.00% | 无 |
| 导出页 | 5 | 2 | 40.00% | 依赖上游字段 |

- 风险模块占比 = 2 / 3 × 100% = **66.67%**

**结论**：
1. 整体完成率约 78.95%，未达 100%，主要拖累来自"导出页"模块（仅 40%）。
2. "导出页"风险明确标注为"依赖上游字段"，完成率低与该风险直接相关，建议优先排查上游字段依赖问题。
3. "数据导入"存在"接口偶发超时"风险，但完成率仍达 87.5%，风险影响可控。
4. "查询页"无风险且 100% 完成，是本周表现最佳模块。
5. 数据样本仅 3 条（3 天），统计意义有限，建议积累更长周期数据后再做趋势判断。

### 5.2 异常样本结论

**计算过程（已通过计算器验证）**：

- 原始记录数 = **6 行**（不含表头）
- 唯一 record_id = {1, 2, 3, 4, 5} = **5 个**
- 重复行数 = 6 - 5 = **1 行**（record_id=2 出现 2 次，完全重复）
- 有效数值记录数（去重 + status=ok + 合法数值）= **2 条**（record_id=1, 2）
- 有效 value 之和 = 120 + 120 = **240**
- 有效 value 均值 = 240 / 2 = **120**

**错误聚合对比（说明清洗必要性）**：
- 若不去重、不排除 error 记录，直接对全部 6 行 value 求和：120 + 120 + 120 + (空) + (-999) + (非数值公式) → 数值部分 = 120+120+120+(-999) = **-639**，结果严重失真。
- 若去重但仍包含 error 记录：120 + 120 + (-999) = **-759**，同样失真。
- 正确清洗后结果为 **240**，差异显著，证明清洗规则直接影响结论。

**各类异常统计**：

| 异常类型 | 数量 | record_id |
|----------|------|-----------|
| 完全重复 | 1 行 | 2 |
| 缺失值 | 1 | 3 |
| 错误状态+异常负值 | 1 | 4 |
| 公式注入（不安全输入） | 1 | 5 |
| 正常有效 | 2（去重后） | 1, 2 |

**结论**：
1. 6 行原始数据中仅 2 行（去重后）可安全纳入数值聚合，有效率仅 33.3%。
2. record_id=5 的 `=HYPERLINK(...)` 是典型的 CSV 公式注入攻击向量，若直接导入 Excel 并自动执行可能触发恶意链接跳转；本报告按纯文本处理，不执行不解析。
3. record_id=4 的 value=-999 与 status=error 联动，属于哨兵值/错误码，不应混入业务数值统计。
4. record_id=3 完全缺失 status 和 value，无法补全，只能排除。
5. 重复记录（record_id=2）两行完全一致，去重不丢失信息。

---

## 六、SKILL.md 规则对结果的影响

本节列出**确实影响本次分析结果**的 SKILL.md 规则，而非泛泛罗列。

### 规则 1：执行路径优先级与环境依赖（确实影响交付形态）

- **出处**：SKILL.md "Quick Start" — "If a Cloud Storage MCP server is connected, prefer its structured tools... Fall back to gcloud storage and the JSON API when no MCP server is available."
- **影响**：当前环境无 MCP 服务器、无 gcloud、无凭据，因此 Skill 规定的两条执行路径均不可达。本报告**无法上传至 GCS 桶**，只能以本地文件交付。若忽略此规则而伪造"已上传 gs://xxx"的结果，则违反"不得编造执行结果"的约束。

### 规则 2：命令归因前缀（确实影响可复现性）

- **出处**：SKILL.md "Attribution" — "Prefix every gcloud invocation... with the metrics environment variables. Set them inline on each command; shell state may not persist between commands."
- **影响**：若后续环境具备 gcloud 后重跑，任何 `gcloud storage` 命令必须以内联方式携带 `CLOUDSDK_METRICS_ENVIRONMENT="gcs-skills gcs-skills/1.0 (skill:google-cloud-storage-basics)"`，且**不得**使用 `gcloud config set`（会持久化并错误标记无关用量）。此规则直接决定了复测命令的正确写法。

### 规则 3：禁止使用 gsutil（确实影响工具选择）

- **出处**：references/cli-api-usage.md — "Do not use the legacy gsutil CLI: it is minimally maintained and does not support newer features such as soft delete and managed folders."
- **影响**：即使环境中安装了 gsutil，也不得使用；必须使用 `gcloud storage`。本次环境两者皆无，但复测时必须遵守此约束。

### 规则 4：对象不可变性原则（影响数据清洗方法论）

- **出处**：references/core-concepts.md — "Objects cannot be edited in place; an 'edit' is an overwrite that creates a new object."
- **影响**：本报告遵循此原则——**不修改原始 CSV 文件**，所有清洗结果在报告中以新表呈现，原始文件保持不变。这与 GCS 对象不可变的设计哲学一致，也保证了数据可追溯、可复算。

### 规则 5：安全评估不得手动 improvising（影响安全分析边界）

- **出处**：references/data-management.md — "For an automated security analysis of GCS resources... an agent should use the gcs-security-assessment skill instead of improvising a manual assessment. If not installed: Do not attempt the assessment manually, and do not substitute other security products."
- **影响**：`gcs-security-assessment` Skill 未安装，因此本报告**不对任何 GCS 资源做安全态势评估**。对 edge_cases.csv 中公式注入的识别属于通用 CSV 数据安全检查，不涉及 GCS 资源安全评估，故不在此限。

### 规则 6：删除操作需显式授权（影响操作边界）

- **出处**：references/cli-api-usage.md 和 references/mcp-usage.md 均有 "CRITICAL: You MUST stop and ask the user for explicit permission before deleting a bucket or recursively deleting all of its contents."
- **影响**：本次不涉及任何 GCS 删除操作，故无需请求授权。但若复测时需要清理测试桶，必须先获得用户显式同意。

---

## 七、不能完成的事项、证据与复测方法

### 7.1 不能完成的事项清单

| 序号 | 事项 | 阻断原因 | 证据 |
|------|------|----------|------|
| 1 | 创建 GCS 桶 | 无 gcloud CLI、无 Google 项目、无凭据 | `which gcloud` 返回未安装；`~/.config/gcloud/` 不存在 |
| 2 | 上传报告至 GCS | 同上，且无目标桶 | 同上行 |
| 3 | 从 GCS 读取数据 | 无桶、无凭据、无 MCP | 同上行 |
| 4 | 配置 IAM / 生命周期 / 存储类别 | 无桶可配置 | 同上行 |
| 5 | GCS 资源安全态势评估 | `gcs-security-assessment` Skill 未安装，按规则不得手动替代 | 已安装 Skill 列表中无此 Skill |
| 6 | 使用 MCP 服务器操作 | 未连接任何 Cloud Storage MCP 服务器 | 运行环境无 MCP 配置 |
| 7 | 挂载 GCSFuse | 无桶、无凭据、且 gcsfuse 未安装 | 无 gcsfuse 二进制 |

### 7.2 复测方法（满足前置条件后可执行）

**前置条件**：
1. 安装 Google Cloud CLI：`curl https://sdk.cloud.google.com \| bash` 或参照官方文档。
2. 认证：`gcloud auth login`（用户账号）或配置服务账号 ADC。
3. 设定项目：`gcloud config set project <PROJECT_ID>`。
4. （可选）连接 Cloud Storage MCP 远程服务器：端点 `https://storage.googleapis.com/storage/mcp`，需 OAuth 2.0 凭据 + `roles/mcp.toolUser` + 对应 `roles/storage.*`。

**复测命令模板（必须遵守归因规则）**：

```bash
# 启用 API
CLOUDSDK_METRICS_ENVIRONMENT="gcs-skills gcs-skills/1.0 (skill:google-cloud-storage-basics)" \
gcloud services enable storage.googleapis.com --quiet

# 创建桶（示例，桶名全局唯一需替换）
CLOUDSDK_METRICS_ENVIRONMENT="gcs-skills gcs-skills/1.0 (skill:google-cloud-storage-basics)" \
gcloud storage buckets create gs://<UNIQUE_BUCKET_NAME> --location=us-central1

# 上传本报告
CLOUDSDK_METRICS_ENVIRONMENT="gcs-skills gcs-skills/1.0 (skill:google-cloud-storage-basics)" \
gcloud storage cp ./analysis-report.md gs://<UNIQUE_BUCKET_NAME>/

# 验证上传
CLOUDSDK_METRICS_ENVIRONMENT="gcs-skills gcs-skills/1.0 (skill:google-cloud-storage-basics)" \
gcloud storage ls gs://<UNIQUE_BUCKET_NAME>/
```

**注意**：
- 不得使用 `gsutil`（按 cli-api-usage.md 规则）。
- 不得使用 `gcloud config set` 设置归因环境变量（按 SKILL.md Attribution 规则）。
- 删除桶或递归删除内容前必须获得用户显式授权。
- 若使用 MCP 远程服务器，HTTP 请求须设 `User-Agent: gcs-skills/1.0 (skill:google-cloud-storage-basics)`。

---

## 八、数据安全与不安全输入处置

### 8.1 公式注入识别

edge_cases.csv 第 6 行（record_id=5）的 value 字段为：

```
=HYPERLINK("https://example.invalid","do not execute")
```

此值以 `=` 开头，是典型的 CSV/Excel 公式注入载荷。若该 CSV 被直接用 Excel 打开且启用了动态数据交换，可能触发自动跳转或代码执行。

**处置方式**：
- 本报告中以纯文本代码块展示，**不渲染为可点击链接、不执行公式**。
- 在清洗规则 E5 中将其标记为不安全输入，排除出数值聚合。
- 建议下游使用方在导入此类 CSV 前，对所有以 `=`、`+`、`-`、`@` 开头的单元格值前置单引号 `'` 进行转义，或使用数据导入时禁用公式自动执行。

### 8.2 原始文件保护

遵循 GCS 对象不可变原则（core-concepts.md），本次分析**未修改、未覆盖、未删除**任何原始输入文件。project_weekly_data.csv 和 edge_cases.csv 保持上传时的原始状态，所有清洗结果仅在本报告中以派生表形式呈现。

---

## 九、总结

1. **数据分析已完成**：项目周报整体完成率 78.95%，导出页模块（40%）是主要短板；异常样本 6 行中仅 2 行可安全聚合，有效 value 之和为 240、均值为 120。
2. **GCS 操作全部阻断**：因环境无 gcloud/gsutil/凭据/MCP，无法执行 Skill 定义的任何云存储操作，报告以本地文件交付。
3. **清洗规则可复核**：所有排除、去重、隔离决策均有明确规则和原始行对应，计算结果经计算器验证。
4. **不安全输入已处置**：公式注入文本按纯文本隔离，未执行未解析。
5. **复测路径清晰**：满足 gcloud + 凭据 + 项目前置条件后，可按第七节命令模板完成 GCS 上传等操作，且必须遵守归因前缀和禁用 gsutil 等规则。
