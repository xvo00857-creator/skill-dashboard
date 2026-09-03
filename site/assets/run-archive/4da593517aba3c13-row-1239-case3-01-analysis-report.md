# 项目周报数据与异常样本分析报告

> 生成时间：2026-08-26
> 输入文件：`project_weekly_data.csv`、`edge_cases.csv`
> 执行依据：Skill `datalineage-bigquery-asset-impact-analysis` 的 `SKILL.md`（实际读取版）

---

## 一、执行概述

本次任务要求基于上传的 Skill 执行项目周报数据与异常样本分析。经实际读取与环境核验，结论如下：

- **Skill 原始定位**：BigQuery 表/视图的下游影响分析（blast radius），依赖 Google Cloud Data Lineage MCP Server。
- **实际输入**：两个本地 CSV 文件（项目周报 + 异常样本），**非 BigQuery 资产**，未提供任何 BigQuery 表/视图的 FQN。
- **环境阻断**：`bq` CLI、`gcloud` CLI 均未安装；无 GCP 凭据目录（`~/.config/gcloud/` 不存在）；工具列表中无 `DataLineageServer:search_lineage` MCP 工具。
- **完成范围**：Skill 核心工作流（BigQuery 血缘检索）**无法执行**；已完成本地 CSV 数据的清洗、异常识别、指标计算与可复核验证，并给出降级方案与复测方法。

---

## 二、实际读取的 Skill 文件清单

| 相对路径 | 说明 |
|---|---|
| `datalineage-bigquery-asset-impact-analysis/SKILL.md` | 主技能文件，含工作流、约束与输出格式 |
| `datalineage-bigquery-asset-impact-analysis/references/mcp-usage.md` | MCP 服务器连接配置与工具偏好说明 |

> 以上为解压后实际存在并读取的全部文件，未编造任何未读取的文件内容。

---

## 三、确实影响结果的 SKILL.md 规则

### 规则 1（核心阻断）：Strictly Banned Bypasses

> "Exclusively retrieve downstream relationships using the `DataLineageServer:search_lineage` tool."

该规则**禁止**使用 `bq` CLI、`gcloud` CLI 或任何其他方式替代 MCP 工具进行血缘检索。当前环境中 `DataLineageServer:search_lineage` 工具不可用，因此 Skill 的核心工作流（步骤 3「Retrieve the Downstream Lineage Graph」）完全无法执行，且**不允许**用其他工具绕过。这直接导致 BigQuery 资产影响分析部分被阻断。

### 规则 2（输出约束）：No Output Shortcutting or Hallucinated Artifacts

> "Avoid telling the user you have created a separate Markdown file or artifact containing the details unless you have explicitly executed file-writing tools to create it."

该规则要求不得声称创建了未实际生成的文件。本报告通过 `Write` 工具实际生成，符合该规则；同时不得编造任何 BigQuery 血缘查询结果。

### 规则 3（空响应解释）：Interpret Empty Responses Correctly

> "If the lineage response is empty, immediately assume that no dependencies exist in the queried locations."

该规则仅在成功调用 MCP 工具并返回空结果时适用。当前因工具不可用未能发起调用，**不适用**该规则——不能将"未调用"等同于"无依赖"。

---

## 四、环境阻断详情

| 依赖项 | SKILL.md 要求 | 实际状态 | 影响 |
|---|---|---|---|
| `DataLineageServer:search_lineage` MCP 工具 | 步骤 3 必须调用，且为唯一允许的血缘检索方式 | 工具列表中不存在 | 核心工作流阻断 |
| `bq` CLI | 步骤 2 用于 `bq show --format=json` 发现数据集 location | `command not found` | 无法验证资产存在性、无法发现 location |
| `gcloud` CLI | 参考文档中提及（但 mcp-usage.md 明确 gcloud 不支持血缘检索） | 未安装 | 辅助能力缺失 |
| GCP 凭据 | MCP 配置需 `authProviderType: google_credentials` | `~/.config/gcloud/` 不存在，环境变量无 GCP 相关项 | 无法认证 |
| BigQuery 资产 FQN | 步骤 1 需 `bigquery:{project_id}.{dataset_id}.{table_or_view_id}` | 用户提供的是 CSV 文件，无 FQN | 无分析对象 |
| MCP 服务器配置 | 需在 `mcp_config.json` 中配置 `DataLineageServer` | 无配置文件 | 无法连接 |

**阻断结论**：因缺少 MCP 工具、CLI、凭据与分析对象，Skill 原始工作流（BigQuery 资产下游影响分析）无法执行。以下分析为基于本地 CSV 的降级完成部分。

---

## 五、数据清洗规则

### 5.1 `project_weekly_data.csv`

- **格式**：标准 CSV，UTF-8 编码，6 列（日期、模块、计划任务、完成任务、风险、负责人），3 条数据行。
- **清洗规则**：
  1. 日期格式校验：均为 `YYYY-MM-DD`，无异常。
  2. 数值字段（计划任务、完成任务）转为整数，均为正整数，无缺失。
  3. 风险字段：`无` 视为无风险，其余文本保留。
  4. 无重复行、无空值。

### 5.2 `edge_cases.csv`

- **格式**：CSV，UTF-8 编码，4 列（record_id、status、value、notes），6 条数据行。
- **格式异常**：第 6 行（record_id=5）使用**反斜杠转义引号**（`\"`），不符合 RFC 4180 标准（标准应为双引号转义 `""`）。需以 `escapechar='\\'` 解析，否则字段错位。
- **清洗规则**：

| 规则 | 检测条件 | 处理方式 |
|---|---|---|
| 完全重复去重 | 所有字段值完全相同的行 | 保留 1 条，去除冗余 |
| 缺失值 | status 或 value 为空字符串或 `-` | 标记为缺失，不纳入数值统计 |
| 异常状态 | status = `error` | 剔除，不纳入有效记录 |
| 异常负值 | value 可解析为数值且 < 0 | 剔除（与 status=error 通常伴生） |
| 公式注入 | value 以 `=`、`+`、`-`、`@` 开头且非合法数值 | 转义处理（前置单引号 `'`），不直接执行 |
| 误判防护 | 以 `-` 开头但可解析为合法负数值 | 归为异常负值而非公式注入（如 -999） |

---

## 六、指标口径

| 指标 | 口径定义 | 计算公式 |
|---|---|---|
| 总计划任务 | 所有模块计划任务数之和 | `Σ 计划任务` |
| 总完成任务 | 所有模块完成任务数之和 | `Σ 完成任务` |
| 整体完成率 | 总完成 / 总计划 | `Σ完成 / Σ计划 × 100%` |
| 模块完成率 | 单模块完成 / 单模块计划 | `完成任务 / 计划任务 × 100%` |
| 有效记录数 | 去重后，剔除 error/负值/缺失/公式注入后的记录数 | 见清洗规则 |
| 有效 value 均值 | 有效记录中可解析为数值的 value 的算术平均 | `Σ value / N` |

---

## 七、关键结论

### 7.1 项目周报（`project_weekly_data.csv`）

- **整体完成率 78.95%**（15/19），未达 100%，主要拖累来自导出页模块。
- **模块分化明显**：
  - 查询页：100%（6/6），无风险，健康。
  - 数据导入：87.50%（7/8），风险为"接口偶发超时"，影响可控但需关注稳定性。
  - 导出页：40.00%（2/5），风险为"依赖上游字段"，是本周最大瓶颈，完成率不足一半。
- **风险关联**：导出页的低完成率与其"依赖上游字段"的风险描述一致，属上游依赖导致的阻塞，需优先协调上游字段交付。

### 7.2 异常样本（`edge_cases.csv`）

- **6 条原始记录中，仅 2 条为完全有效记录**（record_id=1、2，去重后），有效率 33.3%。
- **完全重复**：record_id=2 出现 2 次，字段完全一致，去重后保留 1 条。
- **缺失值**：record_id=3 的 status、value、notes 均为空（notes 为 `-`），属整行无效。
- **异常负值 + error 状态**：record_id=4，value=-999，status=error，应剔除。
- **公式注入 + CSV 格式异常**：record_id=5，value 为 `=HYPERLINK("https://example.invalid","do not execute")`，且该行使用非标准反斜杠转义。若直接导入 Excel 可能触发公式执行，**必须转义**（前置单引号）。
- **有效 value 统计**：2 条有效记录 value 均为 120，总和 240，均值 120.00。

---

## 八、可复核计算

### 8.1 项目周报指标

```
总计划任务 = 8 + 6 + 5 = 19
总完成任务 = 7 + 6 + 2 = 15
整体完成率 = 15 / 19 × 100% = 78.95%

数据导入完成率 = 7 / 8 × 100% = 87.50%
查询页完成率   = 6 / 6 × 100% = 100.00%
导出页完成率   = 2 / 5 × 100% = 40.00%
```

### 8.2 异常样本清洗链路

```
原始记录数: 6
  ├─ record_id=1: ok, value=120 → 有效
  ├─ record_id=2: ok, value=120 → 有效 (与下一条完全重复)
  ├─ record_id=2: ok, value=120 → 完全重复, 去重移除
  ├─ record_id=3: status=空, value=空, notes=- → 缺失, 剔除
  ├─ record_id=4: status=error, value=-999 → 异常负值+error, 剔除
  └─ record_id=5: value==HYPERLINK(...) → 公式注入+CSV格式异常, 需转义

去重后: 5 条
清洗后有效: 2 条 (record_id=1, 2)
被剔除/需特殊处理: 3 条 (record_id=3 缺失, 4 error/负值, 5 公式注入)

有效 value: [120, 120], 总和=240, 均值=120.00
```

### 8.3 验证命令

以上计算可通过以下 Python 片段复现（`escapechar='\\'` 用于正确解析非标准 CSV 行）：

```python
import csv, re
from collections import Counter

# project_weekly_data.csv
with open('project_weekly_data.csv', encoding='utf-8') as f:
    proj = list(csv.DictReader(f))
total_plan = sum(int(r['计划任务']) for r in proj)
total_done = sum(int(r['完成任务']) for r in proj)
print(f'完成率: {total_done}/{total_plan} = {total_done/total_plan*100:.2f}%')

# edge_cases.csv (注意 escapechar)
with open('edge_cases.csv', encoding='utf-8') as f:
    edge = list(csv.DictReader(f, escapechar='\\'))
print(f'原始记录: {len(edge)}')
# 去重
unique = [dict(k) for k, v in Counter(tuple(sorted(r.items())) for r in edge).items()]
print(f'去重后: {len(unique)}')
```

---

## 九、降级方案与复测方法

### 9.1 Skill 原始工作流的降级方案

由于 `DataLineageServer:search_lineage` 不可用且 SKILL.md 禁止绕过，BigQuery 资产影响分析无法在本环境完成。降级方案如下：

| 层级 | 方案 | 前提条件 |
|---|---|---|
| L1（推荐） | 配置 MCP 服务器后重跑 | 在 `mcp_config.json` 中配置 `DataLineageServer`，提供 GCP 凭据与 project_id，确保 `search_lineage` 工具可用 |
| L2（替代，需用户明确授权） | 使用 `bq` CLI + `INFORMATION_SCHEMA` 手动查询视图依赖 | 安装 Google Cloud SDK，执行 `gcloud auth`，但**注意**：SKILL.md 明确禁止此绕过，仅在用户书面同意偏离 Skill 约束时可用 |
| L3（纯本地） | 仅对本地 CSV 做数据质量分析（即本报告第五至八节） | 无需外部依赖，已完成 |

### 9.2 复测方法（具备条件后）

1. **安装依赖**：安装 Google Cloud SDK（含 `bq`、`gcloud`）。
2. **认证**：执行 `gcloud auth application-default login` 或设置 `GOOGLE_APPLICATION_CREDENTIALS` 环境变量。
3. **配置 MCP**：在 agent 的 `mcp_config.json` 中添加：
   ```json
   {
     "mcpServers": {
       "DataLineageServer": {
         "serverUrl": "https://datalineage.googleapis.com/mcp",
         "authProviderType": "google_credentials",
         "headers": { "x-goog-user-project": "<GCP_PROJECT_ID>" }
       }
     }
   }
   ```
4. **提供分析对象**：给出 BigQuery 表/视图的 FQN，格式 `bigquery:{project_id}.{dataset_id}.{table_or_view_id}`。
5. **按 SKILL.md 工作流执行**：
   - 步骤 1：确认 FQN 格式。
   - 步骤 2：`bq show --format=json {project_id}:{dataset_id}` 获取 location，构造 parent path。
   - 步骤 3：调用 `DataLineageServer:search_lineage`，direction=`DOWNSTREAM`，max_depth=10，max_process_per_link=5。
   - 步骤 4：遍历 lineage links 构建影响图，区分 Direct/Indirect，标记 `EXACT_COPY`。
   - 步骤 5：按 SKILL.md 规定的 4 段结构输出（Executive Summary / Critical Path / Blast Radius Table / Analysis Metadata）。
6. **验证**：若返回空，按 SKILL.md 规则 1 报告"查询范围内无依赖"；若 `bq show` 报资产不存在，按规则 3 停止并报告。

---

## 十、总结

1. **Skill 核心工作流阻断**：因缺少 `DataLineageServer:search_lineage` MCP 工具、`bq`/`gcloud` CLI、GCP 凭据及 BigQuery 资产 FQN，BigQuery 下游影响分析无法执行。SKILL.md 的"Strictly Banned Bypasses"规则进一步禁止用其他工具替代，故不存在合规的本地绕过路径。
2. **本地 CSV 分析已完成**：项目周报整体完成率 78.95%，导出页（40%）为主要瓶颈；异常样本 6 条中仅 2 条有效，存在完全重复、缺失、异常负值、公式注入及 CSV 格式不规范五类问题。
3. **可复核**：所有指标均给出计算公式与验证脚本，清洗规则明确可追溯。
4. **复测路径清晰**：具备 GCP 环境与 MCP 配置后，可按第九节步骤完整执行 Skill 原始工作流。
