# BART fMRI 可复现分析流程

基于 OpenNeuro ds000001（Balloon Analog Risk Task，气球模拟风险任务）的可复现 fMRI 分析流程。

## 数据集

| 项目 | 内容 |
|------|------|
| 数据集编号 | ds000001 |
| 来源 | OpenNeuro <https://openneuro.org/datasets/ds000001> |
| 许可 | CC0（公有领域贡献） |
| 被试数 | 16 |
| 任务 | Balloon Analog Risk Task（BART） |
| 每被试扫描 | 1 个 T1w + 1 个 inplaneT2 + 3 个 BOLD run（每 run 300 个 volume，TR=2.0s） |
| 事件类型 | pumps_demean（充气）、explode_demean（爆炸）、cash_demean（兑现）、control_pumps_demean（控制充气） |
| 原始论文 | Schonberg et al. (2012), Frontiers in Decision Neuroscience, 6:80, doi:10.3389/fnins.2012.00080 |

## 目录结构

```
bart_analysis/
├── code/
│   ├── 00_download_data.py        # 从 OpenNeuro S3 下载数据
│   ├── 01_validate_and_qc.py      # BIDS 验证与质量控制
│   ├── 02_behavioral_analysis.py  # 行为数据分析
│   ├── 02b_run_mriqc.sh           # MRIQC（需 Docker）
│   ├── 03_run_fmriprep.sh         # fMRIPrep 预处理（需 Docker）
│   ├── 04_first_level_glm.py      # 一阶 GLM
│   ├── 05_group_analysis.py       # 组水平统计
│   └── run_pipeline.sh            # 主运行脚本
├── data/ds000001/                 # BIDS 格式原始数据
├── derivatives/                   # 预处理与统计输出
│   ├── fmriprep/                  # fMRIPrep 输出
│   ├── mriqc/                     # MRIQC 输出
│   ├── first_level/               # 一阶 GLM 对比图
│   └── group_level/               # 组水平统计图
└── outputs/
    ├── tables/                    # 统计表格（TSV）
    ├── figures/                   # 可视化图（PNG）
    ├── qc_info.json
    └── behavioral_info.json
```

## 环境要求

### 必需
- Python 3.9+
- Python 包：`pybids`, `nibabel`, `nilearn`, `pandas`, `numpy`, `scipy`, `matplotlib`, `seaborn`
  ```bash
  pip install pybids nibabel nilearn pandas numpy scipy matplotlib seaborn
  ```

### 可选（完整影像流程需要）
- Docker（运行 fMRIPrep 和 MRIQC BIDS-Apps）
- 磁盘空间：完整 16 被试约 5 GB 原始数据 + 15 GB derivatives

## 快速开始

```bash
# 1. 下载数据（默认下载 3 个被试的 NIfTI + 全部被试的行为数据）
python3 code/00_download_data.py

# 2. 运行可在本地完成的步骤（验证 + QC + 行为分析）
bash code/run_pipeline.sh

# 3. 如有 Docker，运行完整影像流程
bash code/run_pipeline.sh mriqc      # MRIQC 质量控制
bash code/run_pipeline.sh fmriprep   # fMRIPrep 预处理
bash code/run_pipeline.sh firstlevel # 一阶 GLM
bash code/run_pipeline.sh group      # 组水平统计
```

### 下载全部被试

编辑 `code/00_download_data.py`，将 `NIFTI_SUBJECTS` 改为全部 16 个被试：
```python
NIFTI_SUBJECTS = {f"{i:02d}" for i in range(1, 17)}
```

## 分析步骤说明

### 步骤 00：数据下载
- 从 OpenNeuro S3（`s3.amazonaws.com/openneuro.org/ds000001`）下载
- 输入：无（脚本自动下载）
- 输出：`data/ds000001/`（BIDS 格式）

### 步骤 01：BIDS 验证与质量控制
- 使用 PyBIDS（`bids.BIDSLayout`）索引数据集，验证 BIDS 结构
- 检查元数据完整性（RepetitionTime、TaskName 等必需/推荐字段）
- 检查 NIfTI 头信息（维度、体素大小、TR 一致性）
- 检查 events.tsv 格式（onset、duration、trial_type）
- 检查 participants.tsv（人口学数据规范性）
- 输出：
  - `outputs/tables/qc_summary.tsv`：每被试 QC 指标
  - `outputs/tables/qc_issues.tsv`：发现的问题
  - `outputs/figures/qc_events_per_run.png`：每 run 事件数
  - `outputs/figures/qc_demographics.png`：人口学分布

### 步骤 02：行为数据分析
- 从全部 16 被试的 events.tsv 计算行为指标：
  - 爆炸率（explosion rate）
  - 每气球平均充气次数
  - 平均反应时（RT）
  - 每 run 气球数
- 组水平统计：描述统计、性别差异（Welch t 检验）、年龄相关（Pearson）
- 输出：
  - `outputs/tables/behavioral_summary.tsv`：每被试指标
  - `outputs/tables/behavioral_by_run.tsv`：每 run 指标
  - `outputs/tables/behavioral_group_stats.tsv`：组水平统计
  - `outputs/figures/beh_risk_behavior.png`：风险行为柱状图
  - `outputs/figures/beh_rt_distribution.png`：RT 分布
  - `outputs/figures/beh_event_counts.png`：事件类型计数
  - `outputs/figures/beh_age_vs_risk.png`：年龄与风险行为关系

### 步骤 02b：MRIQC（需 Docker）
- 使用 MRIQC BIDS-App 提取影像质量指标（IQMs）
- 命令：`docker run nipreps/mriqc:24.0.0 /data /out participant` + `group`
- 输出：`derivatives/mriqc/`（含 group_bold.html 报告）

### 步骤 03：fMRIPrep 预处理（需 Docker）
- 使用 fMRIPrep BIDS-App 进行标准化预处理
- 因数据集无 fieldmap，使用 `--use-syn-sdc warn` 进行畸变校正
- 输出空间：MNI152NLin2009cAsym:res-2 + anat + fsaverage5
- 命令：`docker run nipreps/fmriprep:24.0.0 /data /out participant ...`
- 输出：`derivatives/fmriprep/`

### 步骤 04：一阶 GLM
- 使用 nilearn `FirstLevelModel`
- 4 个条件回归变量（pumps、explode、cash、control_pumps）
- Glover HRF 模型，6 mm 平滑，0.01 Hz 高通滤波
- 混杂回归变量：6 个头动参数 + CSF + WhiteMatter 信号
- 对比：各条件 baseline、explode vs cash、cash vs explode
- 输出：`derivatives/first_level/sub-XX/contrast-*_zmap.nii.gz`

### 步骤 05：组水平统计
- 使用 nilearn `SecondLevelModel` 进行随机效应分析
- 单样本 t 检验，FPR 校正（p < 0.05），簇阈值 10 个体素
- 输出：
  - `derivatives/group_level/contrast-*_group-zmap.nii.gz`
  - `outputs/tables/group_clusters_*.tsv`：显著簇坐标
  - `outputs/figures/group_*_glassbrain.png`：玻璃脑图
  - `outputs/figures/group_*_statmap.png`：统计参数图

## 输入格式

数据遵循 BIDS v1.11.x 标准：

```
data/ds000001/
├── dataset_description.json   # 必需：数据集描述
├── participants.tsv           # 必需：被试表（participant_id, sex, age）
├── task-balloonanalogrisktask_bold.json  # 任务元数据（RepetitionTime, TaskName）
└── sub-XX/
    ├── anat/
    │   ├── sub-XX_T1w.nii.gz
    │   └── sub-XX_inplaneT2.nii.gz
    └── func/
        ├── sub-XX_task-balloonanalogrisktask_run-1_bold.nii.gz
        └── sub-XX_task-balloonanalogrisktask_run-1_events.tsv
```

events.tsv 必需列：`onset`（秒）、`duration`（秒）、`trial_type`。
本数据集额外列：`cash_demean`、`control_pumps_demean`、`explode_demean`、`pumps_demean`、`response_time`。

## 统计方法

| 分析 | 方法 | 软件 |
|------|------|------|
| 行为描述统计 | 均值、标准差、范围 | pandas |
| 性别差异 | Welch 独立样本 t 检验 | scipy.stats.ttest_ind |
| 年龄相关 | Pearson 相关 | scipy.stats.pearsonr |
| 一阶 GLM | 广义线性模型 + Glover HRF | nilearn FirstLevelModel |
| 组水平 | 单样本 t 检验（随机效应） | nilearn SecondLevelModel |
| 多重比较 | FPR voxel-level p<0.05 + 簇阈值 10 | nilearn threshold_stats_img |

## 已知数据问题（QC 发现）

1. **sub-05 sex 值为 "M,"**（含多余逗号），已在分析中自动清理为 "M"
2. **BOLD 层数不一致**：sub-01 为 33 层，sub-02/03 为 34 层（真实被试间差异）
3. **缺少推荐元数据**：SliceTiming、PhaseEncodingDirection、EchoTime 均缺失
4. **无 fieldmap**：无法进行基于场图的畸变校正，fMRIPrep 使用 SyN 替代
5. **participants.json 不存在**（OpenNeuro S3 返回 404），该文件为可选

## 可复现性说明

- 所有数字均来自实际运行的脚本输出或公开数据源，无预设值
- 数据下载地址、软件版本、参数均在脚本中明确标注
- 随机效应分析使用 nilearn 默认设置，无随机种子依赖
- 行为分析结果可通过 `bash code/run_pipeline.sh behavior` 完全复现
