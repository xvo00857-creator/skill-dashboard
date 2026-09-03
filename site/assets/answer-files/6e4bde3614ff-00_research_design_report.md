# 术后30天死亡预测模型公开汇总数据外部验证方法学研究——研究设计总报告

**Not for patient care or live clinical use.**

| 项目 | 内容 |
|---|---|
| 版本 | 0.1.0-draft |
| 日期 | 2026-08-12 |
| 负责人 | 三人研究小组（方法学/统计、临床领域、隐私与治理各一人） |
| 数据级别 | aggregate_and_synthetic（公开汇总数据 + 合成演示数据） |
| 产物类型 | research_analysis_plan |
| 状态 | draft（待三人小组人工审查） |

---

## 一、研究问题与范围取舍

### 1.1 研究问题

在两周、三人、仅公开资料的约束下，如何基于已发表论文中的**汇总统计量**（混淆计数、校准分箱、事件数、样本量），对一个术后30天死亡预测模型进行**方法学外部验证评估**，并产出可追溯、可审计的研究治理文件？

### 1.2 做什么（In Scope）

1. 制定估计目标先行的研究方案，包括人群、终点、时间尺度、竞争事件、删失规则和敏感性分析。
2. 用 GRADE 框架搭建证据概要结构，定义关键结局和重要结局。
3. 用合成数据演示汇总模型性能评估（区分度、校准、亚组描述性差异）和披露控制的队列表生成。
4. 建立从数据输入到发布的研究治理决策逻辑溯源矩阵。
5. 记录去标识化流程边界（本研究仅用公开汇总数据，不接触原始数据）。

### 1.3 不做什么（Out of Scope，及原因）

| 排除项 | 原因 |
|---|---|
| 个体患者诊断、治疗推荐、剂量计算、分诊 | Skill 硬安全边界：仅产出研究/评估/治理产物，禁止任何患者个体输出 |
| 因果推断 | 题目明确要求不能把相关性写成因果；汇总观察性数据无法控制混杂 |
| 个体患者数据（IPD）获取或再分析 | 两周三人无法完成数据共享协议和伦理审批；Skill Data Gate 要求仅用聚合/合成数据 |
| 模型训练或阈值推导 | Skill 禁止推导阈值、分配疾病类别或输出个人预测 |
| 真正的独立外部验证 | 两周内无法获得新的独立队列数据；方案中如实记录该缺口 |
| GRADE 确定性评级 | Skill 规定确定性必须由合格人工小组做出，检查器不自动评级；本报告仅提供结构骨架 |
| 去标识化合规认定 | Skill 规定检查清单不构成去标识化或 HIPAA 合规结论；需合格隐私专业人员复核 |
| 监管合规声明 | Skill 禁止声称 FDA 授权、HIPAA 合规或监管合规 |

### 1.4 关键取舍说明

- **广度 vs 深度**：两周内不做完整系统评价，而是聚焦一个明确的方法学问题，把流程跑通、把治理文件做扎实。
- **真实数据 vs 合成演示**：真实文献检索和数据提取在两周内可以启动但无法保证完成；模型评估和队列表使用 Skill 自带合成数据演示工作流，明确标注不代表真实结果。
- **自动化 vs 人工判断**：所有脚本仅做结构检查和描述性计算；GRADE 评级、偏倚风险评估、临床相关性判断必须由人工完成，脚本不替代。

---

## 二、资料选择标准

### 2.1 纳入的资料

1. **Skill 自带文件**：SKILL.md、references/ 下全部参考文档、assets/ 下全部模板、scripts/ 下全部检查脚本。这些是本研究的方法学依据和工具。
2. **Skill references/sources.md 中引用的权威来源**（链接检查日 2026-07-23）：
   - GRADE Working Group 手册（证据评级框架）
   - TRIPOD+AI 声明（预测模型研究报告规范）
   - FDA 2026年1月 CDS 指南（监管边界参考）
   - ICH E9(R1) 附录（估计目标框架）
3. **公开已发表文献**（待检索）：术后30天死亡预测模型的外部验证研究，须报告汇总混淆计数或校准数据。检索在执行阶段进行，本报告不预设具体文献。
4. **合成数据**：仅用于演示脚本工作流，所有数值明确标注为合成，不代表任何真实模型或人群。

### 2.2 排除的资料

- 任何需要登录、付费或机构权限才能获取的文献（两周内无法保证获取）。
- 任何包含个体患者数据的文件（Skill Data Gate 禁止）。
- 预印本中未经同行评议的模型性能数据（除非作为探索性参考并明确标注）。
- 非英文和非中文文献（三人小组语言能力限制）。

### 2.3 文献纳入排除标准（待执行阶段细化）

- 研究类型：外部验证研究（回顾性或前瞻性队列）。
- 人群：接受腹部大手术的成年患者（年龄不低于18岁）。
- 模型：报告了术后30天全因死亡预测性能的模型。
- 数据要求：至少报告样本量、事件数和一个区分度指标（C统计量或 AUC）；有校准数据者优先。
- 排除：仅内部验证、样本量小于100、未报告30天结局、会议摘要无全文。

---

## 三、执行计划

### 3.1 两周排期

| 阶段 | 时间 | 任务 | 负责人 |
|---|---|---|---|
| 第1-2天 | 8/13-8/14 | 确定检索策略，在 PubMed 和 Embase 执行检索；去重；标题摘要筛选 | 方法学/统计 + 临床领域 |
| 第3-4天 | 8/15-8/16 | 全文筛选；按预先设计的提取表提取汇总数据（样本量、事件数、混淆计数、校准分箱、C统计量） | 临床领域 + 方法学/统计 |
| 第5天 | 8/17 | 提取质量检查；双人核对10%条目；用 PROBAST+AI 评估偏倚风险（人工） | 三人共同 |
| 第6-7天 | 8/18-8/19 | 汇总描述性分析：C统计量范围、校准截距近似、亚组描述性差异；不做 Meta 回归或因果推断 | 方法学/统计 |
| 第8-9天 | 8/20-8/21 | GRADE 人工小组会议：逐结局评定偏倚风险、不一致性、间接性、不精确性、发表偏倚和确定性 | 三人共同 |
| 第10天 | 8/22 | 撰写结果和局限；更新所有产物 JSON；运行全部脚本验证 | 方法学/统计 |
| 第11-12天 | 8/23-8/24 | 隐私与治理成员复核去标识化清单和决策逻辑矩阵；三人交叉审查全部产物 | 三人共同 |
| 第13天 | 8/25 | 根据审查意见修改；定稿 | 三人共同 |
| 第14天 | 8/26 | 归档；记录变更日志；制定后续工作计划（独立外部验证、IPD 获取等） | 隐私与治理 |

### 3.2 三人分工

| 角色 | 职责 |
|---|---|
| 方法学/统计成员 | 检索策略、统计分析计划、生存计划、模型评估脚本运行、GRADE 统计判断 |
| 临床领域成员 | 文献筛选、数据提取、临床相关性判断、结局重要性评定、临床术语核对 |
| 隐私与治理成员 | 去标识化清单、决策逻辑矩阵、数据边界监督、变更控制和审计归档 |

### 3.3 里程碑交付物

1. 第5天：文献提取表和偏倚风险评估表。
2. 第9天：GRADE 证据概要（人工评定完成版）。
3. 第12天：全部产物 JSON 和脚本验证报告。
4. 第14天：定稿研究报告和归档包。

---

## 四、质量检查方法

### 4.1 脚本结构验证

每个产物 JSON 均通过 Skill 自带脚本验证，验证报告随产物保存：

| 产物 | 脚本 | 本次运行结果 |
|---|---|---|
| 01_intended_use.json | validate_cds_artifact.py | **pass**（警告：人工审查未完成——符合草案状态） |
| 02_survival_plan.json | survival_plan_validator.py | **pass**（警告：人工审查未完成） |
| 03_decision_logic.json | decision_logic_traceability.py | **pass**（警告：人工审查未完成；CSV 已导出） |
| 04_model_eval_synthetic.json | model_biomarker_evaluation.py | **pass**（警告：独立外部验证未记录、人工审查未完成） |
| 05_cohort_table_synthetic.json | cohort_table_generator.py | **pass**（Markdown 已生成；演示了 SUPP 和 SUPP-C） |
| 06_evidence_profile_shell.json | evidence_profile_check.py | **fail（预期）**——所有域判断为 unassessed，需人工小组评定 |
| 07_deidentification_checklist.json | deidentification_checklist.py | **pass**（文档完整；明确不构成去标识化或合规认定） |

### 4.2 人工质量检查

1. **三人交叉审查**：每个产物由非起草人审查，重点检查数据准确性、禁止用途声明和因果语言。
2. **因果语言检查**：所有结果描述仅使用"关联""描述性差异""相关"等措辞；禁止使用"导致""降低风险""改善生存"等因果表述。
3. **数据提取核对**：双人独立提取10%条目，不一致处由第三人裁定。
4. **披露控制复核**：隐私与治理成员检查所有汇总单元格是否满足最小阈值11，确认抑制逻辑正确。
5. **来源可追溯性**：每个数值附来源文献 ID；决策逻辑矩阵每个节点附来源、负责人和验证测试。

### 4.3 技术质量检查

- 所有脚本运行前做 Python AST 编译检查（已通过）。
- 所有 JSON 文件通过 `json.load` 解析验证。
- 所有产物包含必需头部：产物类型、版本、负责人、日期、禁止用途、数据级别、局限、人工审查状态、来源引用和 "Not for patient care or live clinical use" 声明。
- 所有产物不含占位符（REPLACE_、REQUIRES_、YYYY-MM-DD）。
- 所有产物不含患者级键名（patient、mrn、ssn、dob、email、phone、raw_rows 等）。

---

## 五、本次实际产出的文件

所有文件位于 `cds-work/` 目录：

| 文件 | 说明 |
|---|---|
| 01_intended_use.json | 预期用途与治理声明（主文件） |
| 01_intended_use_report.json | 验证报告 |
| 02_survival_plan.json | 生存分析计划（仅方案） |
| 02_survival_plan_report.json | 验证报告 |
| 03_decision_logic.json | 决策逻辑溯源矩阵（9个治理节点） |
| 03_decision_logic.csv | 决策逻辑矩阵导出表 |
| 04_model_eval_synthetic.json | 合成数据模型评估输入 |
| 04_model_eval_report.json | 模型评估结果（含 Wilson 区间、校准差距、亚组差异） |
| 05_cohort_table_synthetic.json | 合成队列表输入 |
| 05_cohort_table.md | 生成的队列表（含 SUPP/SUPP-C 演示） |
| 06_evidence_profile_shell.json | GRADE 证据概要骨架（待人工评定） |
| 06_evidence_profile_report.json | 检查报告（预期失败：需人工判断） |
| 07_deidentification_checklist.json | 去标识化流程检查清单 |
| 07_deidentification_report.json | 检查报告（文档完整，非合规认定） |
| 00_research_design_report.md | 本报告 |

### 合成数据演示结果摘要（不代表真实结果）

- **择期手术组（合成，n=200）**：灵敏度 0.632，特异度 0.815，PPV 0.444，NPV 0.904，校准截距差距 0.007，加权绝对校准差距 0.052。
- **急诊手术组（合成，n=150）**：灵敏度 0.600，特异度 0.800，PPV 0.600，NPV 0.800，校准截距差距 0.010，加权绝对校准差距 0.063。
- **亚组 PPV 最大绝对差**：0.156（描述性，非公平性判断，可能反映病例组合、测量或抽样差异）。
- **队列表**：罕见合并症行择期组 count=8 低于阈值11，执行 SUPP；急诊组对应单元格执行 SUPP-C（互补抑制）。

---

## 六、无法访问的资源和待确认假设

### 6.1 无法访问的资源

1. **tests 目录不存在**：SKILL.md 提到 `python3 -m unittest discover -s tests/clinical-decision-support -p 'test_*.py'`，但解压后的 ZIP 中无 tests 目录，该命令无法运行。已通过 AST 编译检查和模板实跑替代验证。
2. **真实文献检索未执行**：本报告为研究设计阶段，文献检索和数据提取在执行阶段进行；GRADE 证据概要中的效应估计值和研究数量待填入。
3. **references/sources.md 中的外部链接**：本次未逐一访问外部 URL，仅依据 Skill 文档中的引用信息；链接检查日为 2026-07-23，执行阶段需重新验证。
4. **Python 版本**：SKILL.md 要求 Python 3.11+，实际环境为 Python 3.9.6；脚本在 3.9 下运行正常（AST 检查和全部实跑通过），但未在 3.11 下验证。

### 6.2 待确认假设

1. **假设两周内可获取足够的公开全文文献**：若核心文献需付费或权限不足，研究范围将缩小至可获取文献。
2. **假设已发表研究报告了汇总混淆计数**：若多数研究仅报告 C统计量而无混淆计数，模型评估脚本的区分度和校准部分将无法运行，仅能做描述性汇总。
3. **假设三人小组中至少一人具备 GRADE 评定经验**：若无人具备，需在第1-5天安排培训或寻求外部方法学支持。
4. **假设隐私与治理成员具备足够隐私知识完成去标识化清单**：若否，需寻求合格隐私专业人员支持。
5. **GRADE 骨架中所有 unassessed 判断**：必须在人工小组会议上逐一评定，不得由脚本或 AI 代填。

---

## 七、实际读取的 Skill 文件（相对路径）

以下为本次任务中实际读取的 Skill 文件（相对于 `clinical-decision-support/` 目录）：

**核心文档：**
- `SKILL.md`

**参考文档（references/）：**
- `references/README.md`
- `references/safety_and_scope.md`
- `references/evidence_profiles.md`
- `references/study_reporting.md`
- `references/cohort_evaluation.md`
- `references/survival_analysis.md`
- `references/model_biomarker_evaluation.md`
- `references/privacy_and_disclosure.md`
- `references/decision_logic_traceability.md`
- `references/regulatory_and_governance.md`
- `references/sources.md`
- `references/security_validation.md`

**模板（assets/）：**
- `assets/artifact_intended_use_template.json`
- `assets/evidence_profile_template.json`
- `assets/aggregate_model_evaluation_template.json`
- `assets/aggregate_cohort_table_template.json`
- `assets/survival_analysis_plan_template.json`
- `assets/decision_logic_traceability_template.json`
- `assets/deidentification_checklist_template.json`

**脚本（scripts/）：**
- `scripts/_common.py`
- `scripts/validate_cds_artifact.py`
- `scripts/evidence_profile_check.py`
- `scripts/model_biomarker_evaluation.py`
- `scripts/cohort_table_generator.py`
- `scripts/survival_plan_validator.py`
- `scripts/decision_logic_traceability.py`
- `scripts/deidentification_checklist.py`

**未找到：** `tests/` 目录（SKILL.md 提及但 ZIP 中不存在）。

---

## 八、影响交付结果的 SKILL.md 规则

**规则：Data Gate——"Only use aggregate or synthetic data. Reject patient rows, records, narratives, identifiers, free text, person-linked dates, images, waveforms, or genomic sequences."**

这条规则从根本上决定了本研究的设计：

1. **研究范围被限定为汇总层面**：无法获取 IPD 意味着无法做校准斜率估计、决策曲线分析、亚组交互检验或个体风险预测；所有分析降级为汇总描述性统计。
2. **模型评估脚本只接受混淆计数和校准分箱**：这决定了数据提取表的字段设计，也决定了两周排期中必须优先提取这些汇总指标。
3. **合成数据演示成为必要**：在真实文献提取完成前，用 Skill 自带合成数据演示工作流，确保脚本和流程可用，同时明确标注合成数据不代表真实结果。
4. **去标识化清单的定位**：因为输入本身就是公开汇总数据，清单记录的是"18类标识符均不存在"这一事实，而非对原始数据执行去标识化操作。

另一条同样关键的规则是：**"Do not present association as causation or clinical actionability."** 这决定了生存分析计划主效应量选择绝对指标（30天累积生存概率）而非风险比，所有亚组差异标注为描述性，队列表不做基线显著性检验，GRADE 证据概要不产生推荐意见。

---

*本报告由三人研究小组方法学成员起草，待三人小组人工审查。所有脚本验证结果为 2026-08-12 实际运行输出，未做任何修改或编造。*
