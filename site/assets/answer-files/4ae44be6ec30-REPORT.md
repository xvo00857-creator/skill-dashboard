# bids Skill 评测报告：BART fMRI 可复现分析流程

## 一、任务概述

本次评测对象为 "bids" Skill（分类：研究与学习）。任务要求：
1. 解压并完整阅读 Skill ZIP 中的 SKILL.md 及引用文件
2. 为一份公开生物医学示例数据设计可复现分析流程
3. 明确输入格式、质控、统计步骤、输出表格和可视化，并给出运行说明
4. 只能使用可追溯输入和公开证据，所有数字注明来源或计算口径
5. 将事实、假设和建议分开表达
6. 说明约束导致的方案变化，提供验证证据
7. 列出实际读取的 Skill 文件及影响执行的规则

---

## 二、实际读取的 Skill 文件

以下文件均已完整读取（非仅看名称或描述）：

| 相对路径 | 内容 | 对执行的实际影响 |
|----------|------|------------------|
| `bids/SKILL.md` | Skill 主文件，BIDS 标准概述、工作流领域、常见问题、最佳实践 | 确定了"validate early and often"原则，流程首步即做验证；确定使用 PyBIDS 和 bids-validator 工具链；确定优先使用 BIDS-Apps（fMRIPrep/MRIQC） |
| `bids/references/core_workflows.md` | 12 个工作流的完整代码示例 | PyBIDS 查询代码直接参考；bids-validator 调用方式参考；BIDS-Apps 的 docker 调用接口（input output {participant\|group}）直接采用；events 文件格式和 participants 文件规范直接遵循 |
| `bids/references/bids_specification.md` | entity 顺序表、datatypes、扩展名、必需文件、metadata 继承规则 | 文件命名遵循 entity 顺序（sub-XX_task-xxx_run-xx_*）；确认 dataset_description.json 和 participants.tsv 为必需文件；确认 BOLD 数据属于 func datatype |
| `bids/references/metadata_fields.md` | 各模态必需/推荐 JSON 字段 | QC 脚本检查 RepetitionTime、TaskName（BOLD 必需）和 SliceTiming、PhaseEncodingDirection、EchoTime（BOLD 推荐）；确认无 fmap 时的处理方式 |
| `bids/references/conversion_tools.md` | DICOM 转 BIDS 工具（HeuDiConv/dcm2bids/BIDScoin） | 本任务使用已转换好的公开数据集，未涉及 DICOM 转换，但确认了 post-conversion checklist 中的验证步骤 |
| `bids/references/beps.yml` | 24 个 BIDS Extension Proposals 列表 | 确认当前使用的模态（BOLD/anat）属于核心规范，不依赖任何 BEP |
| `bids/references/bids_schema.json` | 机器可读 schema（bids_version 1.11.1, schema_version 1.2.1） | 确认规范版本号；确认 35 个 entity 的顺序和 16 个 datatypes；作为文件命名和结构验证的权威参考 |
| `bids/scripts/update_schema.py` | schema 更新脚本 | 仅阅读，未执行（任务不需要更新 schema） |

### 影响执行的关键 SKILL.md 规则

1. **"validate early and often"**（SKILL.md 最佳实践）→ 流程第 1 步即为 BIDS 验证与 QC，使用 PyBIDS 索引 + 元数据检查 + NIfTI 头检查
2. **BIDS-Apps 标准接口**（core_workflows.md）→ fMRIPrep 和 MRIQC 均采用 `docker run <image> <input> <output> {participant|group}` 调用模式
3. **metadata inheritance**（bids_specification.md）→ 确认 task 级 JSON（task-balloonanalogrisktask_bold.json）中的 RepetitionTime 和 TaskName 可被所有 run 继承
4. **events 文件规范**（core_workflows.md）→ onset 以秒为单位，duration 以秒为单位，trial_type 为条件标签
5. **必需 vs 推荐字段**（metadata_fields.md）→ QC 区分必需字段缺失（error）和推荐字段缺失（warning）
6. **derivatives 目录规范**（core_workflows.md）→ fMRIPrep/MRIQC/一阶/组水平输出分别放在 derivatives/ 子目录，遵循 BIDS Derivatives 命名
7. **优先社区工具**（SKILL.md）→ 预处理使用 fMRIPrep 而非自行编写，质量控制使用 MRIQC，GLM 使用 nilearn

---

## 三、数据集选择

### 事实

- 选用数据集：**ds000001**（OpenNeuro 编号），任务为 Balloon Analog Risk Task（BART，气球模拟风险任务）
- 来源：OpenNeuro <https://openneuro.org/datasets/ds000001>
- 许可：CC0（公有领域贡献），允许自由使用
- 原始论文：Schonberg TS, Fox CR, Mumford JA, Congdon E, Trepel C, Poldrack RA (2012). Decreasing ventromedial prefrontal cortex activity during sequential risk-taking: An fMRI investigation of the Balloon Analogue Risk Task. *Frontiers in Decision Neuroscience*, 6:80. doi:10.3389/fnins.2012.00080
- 数据从 OpenNeuro S3 公开存储桶下载：`https://s3.amazonaws.com/openneuro.org/ds000001`
- 数据集包含 16 个被试（sub-01 至 sub-16），每被试 1 个 T1w、1 个 inplaneT2、3 个 BOLD run
- 每 run 300 个 volume，TR=2.0 秒（来源：task-balloonanalogrisktask_bold.json，经 nibabel 从头信息验证一致）
- BOLD 体素大小 3.125×3.125×4.0 mm，T1w 体素大小 1.0×1.333×1.333 mm（来源：nibabel 读取 NIfTI 头）

### 选择理由

ds000001 是 OpenNeuro 上编号最小的数据集，被广泛用作 BIDS 格式示例和教学数据，具有：
- 完整的 BIDS 结构（dataset_description.json、participants.tsv、events.tsv、JSON sidecar）
- 包含任务 fMRI 和解剖像，适合展示完整流程
- CC0 许可，无使用限制
- 事件文件包含参数调节变量（demean 列），可展示更丰富的 GLM 设计

---

## 四、分析流程设计

### 4.1 输入格式

数据遵循 BIDS v1.11.x 标准（来源：bids_schema.json 中 bids_version 字段为 1.11.1）：

```
data/ds000001/
├── dataset_description.json          # 必需：数据集描述
├── participants.tsv                  # 必需：被试表（participant_id, sex, age）
├── task-balloonanalogrisktask_bold.json  # 任务级元数据（RepetitionTime=2.0, TaskName）
└── sub-XX/
    ├── anat/
    │   ├── sub-XX_T1w.nii.gz
    │   └── sub-XX_inplaneT2.nii.gz
    └── func/
        ├── sub-XX_task-balloonanalogrisktask_run-1_bold.nii.gz
        └── sub-XX_task-balloonanalogrisktask_run-1_events.tsv
```

events.tsv 列（来源：实际读取 48 个 events.tsv 文件）：
- `onset`（必需，秒）、`duration`（必需，秒）、`trial_type`（必需，条件标签）
- `cash_demean`、`control_pumps_demean`、`explode_demean`、`pumps_demean`（参数调节变量）
- `response_time`（反应时，秒）

trial_type 四类：pumps_demean（充气）、explode_demean（爆炸）、cash_demean（兑现）、control_pumps_demean（控制充气）

### 4.2 质控步骤

| 检查项 | 方法 | 依据 |
|--------|------|------|
| BIDS 结构验证 | PyBIDS BIDSLayout 索引 | SKILL.md "validate early and often" |
| 必需元数据 | 检查 RepetitionTime、TaskName | metadata_fields.md（BOLD 必需字段） |
| 推荐元数据 | 检查 SliceTiming、PhaseEncodingDirection、EchoTime | metadata_fields.md（BOLD 推荐字段） |
| NIfTI 头一致性 | nibabel 读取维度、体素大小、TR | core_workflows.md NIfTI 检查 |
| 事件文件 | 检查 onset/duration/trial_type、事件数 | core_workflows.md events 规范 |
| 被试表 | 检查 sex 值规范性、age 范围 | bids_specification.md participants 规范 |

### 4.3 统计步骤

**行为分析（已实际运行）：**
- 每被试行为指标：爆炸率、每气球充气次数、平均反应时、气球数
- 组水平描述统计：均值、标准差、范围、中位数
- 性别差异：Welch 独立样本 t 检验（不假设等方差）
- 年龄相关：Pearson 相关

**影像分析（脚本已编写，需 Docker 环境运行）：**
- 预处理：fMRIPrep 24.0.0（BIDS-App），无 fieldmap 时使用 SyN SDC
- 一阶 GLM：nilearn FirstLevelModel，Glover HRF，6 mm 平滑，0.01 Hz 高通，6 个头动参数 + CSF + WM 混杂回归
- 组水平：nilearn SecondLevelModel，单样本 t 检验，FPR 校正 p<0.05，簇阈值 10

### 4.4 输出表格

| 文件 | 内容 | 状态 |
|------|------|------|
| `outputs/tables/qc_summary.tsv` | 每被试 QC 指标 | 已生成 |
| `outputs/tables/qc_issues.tsv` | 发现的问题清单 | 已生成 |
| `outputs/tables/participants_copy.tsv` | 被试表副本 | 已生成 |
| `outputs/tables/behavioral_summary.tsv` | 每被试行为指标 | 已生成 |
| `outputs/tables/behavioral_by_run.tsv` | 每 run 行为指标 | 已生成 |
| `outputs/tables/behavioral_group_stats.tsv` | 组水平统计 | 已生成 |
| `outputs/tables/group_clusters_*.tsv` | 组水平显著簇坐标 | 待 fMRIPrep 后生成 |

### 4.5 可视化

| 文件 | 内容 | 状态 |
|------|------|------|
| `outputs/figures/qc_events_per_run.png` | 每被试每 run 事件数 | 已生成 |
| `outputs/figures/qc_demographics.png` | 年龄/性别分布 | 已生成 |
| `outputs/figures/beh_risk_behavior.png` | 每被试爆炸率和充气次数 | 已生成 |
| `outputs/figures/beh_rt_distribution.png` | 反应时分布（含性别分组） | 已生成 |
| `outputs/figures/beh_event_counts.png` | 全组事件类型计数 | 已生成 |
| `outputs/figures/beh_age_vs_risk.png` | 年龄与风险行为散点图 | 已生成 |
| `outputs/figures/group_*_glassbrain.png` | 组水平玻璃脑图 | 待 fMRIPrep 后生成 |
| `outputs/figures/group_*_statmap.png` | 组水平统计参数图 | 待 fMRIPrep 后生成 |

---

## 五、实际运行结果（验证证据）

以下结果均来自实际运行脚本的输出，非预设值。

### 5.1 BIDS 验证与 QC（01_validate_and_qc.py）

- PyBIDS 索引成功：16 个被试，任务 balloonanalogrisktask
- 文件统计：9 个非空 BOLD 文件（3 被试×3 run）、3 个非空 T1w 文件、48 个 events 文件
- RepetitionTime 和 TaskName：全部存在，TR 一致为 2.0 秒
- 推荐字段缺失：SliceTiming、PhaseEncodingDirection、EchoTime 均缺失（9/9 文件）
- BOLD 维度：sub-01 为 64×64×33×300，sub-02/03 为 64×64×34×300（真实被试间差异）
- 事件数：每 run 121-187 个，中位数 162
- participants.tsv 发现 sub-05 的 sex 值为 "M,"（含多余逗号），已自动清理为 "M"

### 5.2 行为分析（02_behavioral_analysis.py）

总事件数 7723（来源：48 个 events.tsv 逐行计数）：
- 充气（pumps_demean）：4206
- 控制充气（control_pumps_demean）：2359
- 兑现（cash_demean）：670
- 爆炸（explode_demean）：488

组水平描述统计（n=16，来源：behavioral_group_stats.tsv）：

| 指标 | 均值 | 标准差 | 最小值 | 最大值 |
|------|------|--------|--------|--------|
| 平均反应时（秒） | 0.761 | 0.333 | 0.337 | 1.549 |
| 爆炸率 | 0.433 | 0.118 | 0.227 | 0.687 |
| 每气球充气次数 | 3.764 | 1.000 | 2.286 | 5.868 |
| 每 run 气球数 | 24.125 | 3.360 | 18.0 | 29.0 |

性别差异（Welch t 检验，6 男 10 女，来源：behavioral_group_stats.tsv）：
- 反应时：t=0.295, p=0.775（不显著）
- 爆炸率：t=-0.186, p=0.857（不显著）
- 充气次数：t=-0.111, p=0.915（不显著）

年龄相关（Pearson，n=16，来源：behavioral_group_stats.tsv）：
- 反应时：r=-0.335, p=0.204（不显著）
- 爆炸率：r=-0.087, p=0.748（不显著）
- 充气次数：r=-0.178, p=0.510（不显著）

### 5.3 一阶 GLM 设计矩阵验证

使用 sub-01 run-01 的真实 events（158 行）和 nilearn make_first_level_design_matrix 验证：
- 设计矩阵维度：300×17（4 个条件回归变量 + 余弦漂移项）
- 4 个条件列正确生成：pumps_demean、explode_demean、cash_demean、control_pumps_demean
- HRF 模型：glover，高通滤波 0.01 Hz
- 验证通过：设计矩阵可从真实 events.tsv 正确构建

---

## 六、事实、假设与建议

### 事实（有数据或公开来源支持）

1. ds000001 包含 16 个被试，CC0 许可，来源 OpenNeuro
2. TR=2.0 秒，每 run 300 个 volume（来源：JSON sidecar + NIfTI 头交叉验证）
3. sub-01 的 BOLD 为 33 层，sub-02/03 为 34 层（来源：nibabel 实际读取）
4. 全组 7723 个事件，其中充气 4206、控制充气 2359、兑现 670、爆炸 488（来源：48 个 events.tsv 实际计数）
5. 平均爆炸率 0.433（SD=0.118），性别和年龄效应均不显著（p>0.05）
6. 数据集缺少 SliceTiming、PhaseEncodingDirection、EchoTime 字段
7. 数据集无 fieldmap（fmap 目录不存在）
8. sub-05 的 sex 值在 participants.tsv 中为 "M,"（含多余逗号）
9. participants.json 在 OpenNeuro S3 上不存在（HTTP 404），该文件为可选
10. 当前环境无 Docker，fMRIPrep 和 MRIQC 无法实际运行

### 假设（基于领域知识的合理推断）

1. 假设 fMRIPrep 24.0.0 的 docker 镜像接口与 core_workflows.md 中描述的 BIDS-App 标准一致（input output {participant|group}）
2. 假设无 fieldmap 时使用 `--use-syn-sdc warn` 是合理的替代方案（依据 fMRIPrep 文档和 SKILL.md 中对 fmap 的说明）
3. 假设 demean 列的值为跨 run/被试去均值后的参数调节变量，均值接近 0（实际验证：全组均值 0.000033，符合预期）
4. 假设 6 mm FWHM 平滑和 0.01 Hz 高通滤波适用于该分辨率（3.125×3.125×4.0 mm）的 BOLD 数据
5. 假设 Glover HRF 适用于该任务（事件相关设计，TR=2s）
6. 假设每气球充气次数 = 充气事件数 /（爆炸数 + 兑现数）是合理的行为指标（每个气球以爆炸或兑现结束）

### 建议（基于分析结果的改进方向）

1. **下载全部 16 个被试的 NIfTI**：当前仅下载 3 个被试的影像数据（行为分析覆盖全部 16 个），完整影像分析需全部数据
2. **在有 Docker 的环境运行 fMRIPrep/MRIQC**：脚本已就绪，命令可直接复制执行
3. **补充缺失元数据**：SliceTiming 可用于切片时间校正，PhaseEncodingDirection 可用于畸变校正；建议从 DICOM 头或扫描协议中获取
4. **修正 participants.tsv**：将 sub-05 的 "M," 改为 "M"（已在分析中自动处理，但建议修正源文件）
5. **增加被试内 run 间稳定性分析**：当前仅计算跨 run 均值，可进一步检验学习效应
6. **考虑非参数检验**：n=16 样本量较小，t 检验的正态性假设可能不成立，可补充置换检验
7. **影像分析可增加参数调节分析**：利用 pumps_demean 列作为充气次数的参数调节变量，检验与风险行为相关的脑区

---

## 七、约束导致的方案变化

### 约束 1：只能使用可追溯输入和公开证据

**变化**：
- 未使用任何模拟数据或预设数值，所有数字均来自实际下载的数据和实际运行的脚本
- 数据来源明确标注（OpenNeuro S3 URL、DOI、论文引用）
- bids-examples 仓库中的 NIfTI 文件为 0 字节占位符，发现后改从 OpenNeuro S3 下载真实数据
- 每个统计数字均标注计算口径（如"来源：48 个 events.tsv 逐行计数"）

### 约束 2：所有数字注明来源或计算口径

**变化**：
- 报告中每个数字均标注来源（JSON sidecar、NIfTI 头、脚本输出文件名）
- 脚本输出保存为 TSV/JSON 文件，可供核查
- 行为指标的计算公式在脚本注释和 README 中明确说明

### 约束 3：事实、假设和建议分开表达

**变化**：
- 报告专设第六节，将三类内容明确区分
- 对于无法在当前环境验证的内容（如 fMRIPrep 输出），明确标注为"假设"或"待运行"

### 约束 4：环境限制（无 Docker、无 Deno）

**变化**：
- bids-validator CLI（Deno 版）无法运行，改用 PyBIDS 索引作为结构验证替代，并在报告中说明
- fMRIPrep/MRIQC 无法实际运行，提供精确的 docker 命令和完整脚本，但不伪造运行结果
- 行为分析和 QC 使用纯 Python（pandas/nibabel/matplotlib）完成，这些在当前环境可运行
- 一阶 GLM 设计矩阵使用真实 events 数据验证了代码路径，但完整 GLM 拟合需 fMRIPrep 输出

### 约束 5：不得编造工具调用、文件、数据或已完成状态

**变化**：
- 所有报告的输出文件均实际存在于磁盘
- 所有报告的统计结果均来自实际脚本运行
- 未运行的步骤明确标注"待 fMRIPrep 后生成"，不声称已完成
- participants.json 的 404 错误如实报告，未隐瞒

---

## 八、缺失项与已完成范围

### 已完成

1. 解压并完整阅读 bids Skill 全部 8 个文件
2. 从 OpenNeuro 下载 ds000001 数据（3 个被试 NIfTI + 全部 16 个被试行为数据）
3. 编写 8 个脚本（下载、QC、行为分析、MRIQC、fMRIPrep、一阶 GLM、组水平、主流程）
4. 实际运行 QC 和行为分析，生成 6 个 TSV 表格和 6 个 PNG 图
5. 验证一阶 GLM 设计矩阵构建
6. 编写 README.md 运行说明
7. 主流程脚本 run_pipeline.sh 端到端测试通过（本地步骤）

### 未完成（环境限制）

1. **bids-validator CLI 验证**：需要 Deno 运行时，当前环境未安装。替代方案：PyBIDS 索引验证已通过
2. **MRIQC 质量控制**：需要 Docker，当前环境未安装。脚本 02b_run_mriqc.sh 已就绪
3. **fMRIPrep 预处理**：需要 Docker，当前环境未安装。脚本 03_run_fmriprep.sh 已就绪
4. **一阶 GLM 拟合**：依赖 fMRIPrep 输出，脚本 04_first_level_glm.py 已就绪，设计矩阵已验证
5. **组水平统计**：依赖一阶 GLM 输出，脚本 05_group_analysis.py 已就绪
6. **全部 16 个被试的 NIfTI**：仅下载 3 个被试（sub-01/02/03），修改下载脚本中 NIFTI_SUBJECTS 即可下载全部

### 依赖版本（实际环境）

- Python 3.9.6
- pybids、nibabel、nilearn 0.12.1、pandas 2.3.3、numpy 2.0.2、scipy 1.13.1、matplotlib 3.9.4、seaborn 0.13.2
- BIDS schema 版本：1.11.1（来源：bids_schema.json）

---

## 九、运行说明

### 本地可运行步骤（无需 Docker）

```bash
cd bart_analysis

# 安装依赖
pip install pybids nibabel nilearn pandas numpy scipy matplotlib seaborn

# 一键运行（下载 + QC + 行为分析）
bash code/run_pipeline.sh
```

### 完整影像流程（需 Docker）

```bash
# 1. 编辑 code/00_download_data.py，将 NIFTI_SUBJECTS 改为全部 16 个被试
# 2. 重新下载
python3 code/00_download_data.py

# 3. 运行 MRIQC
bash code/run_pipeline.sh mriqc

# 4. 运行 fMRIPrep
bash code/run_pipeline.sh fmriprep

# 5. 一阶 GLM
bash code/run_pipeline.sh firstlevel

# 6. 组水平统计
bash code/run_pipeline.sh group
```

### 单独运行各步骤

```bash
python3 code/01_validate_and_qc.py    # 仅 QC
python3 code/02_behavioral_analysis.py # 仅行为分析
```
