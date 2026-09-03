# group-by-analysis 数据分组分析方案

## 一、重要声明（请先阅读）

1. **随附 ZIP 包中仅含 `group-by-analysis/SKILL.md`，未提供任何真实业务数据文件。**
2. 为验证脚本可运行，`make_demo_data.py` 生成了一份**合成演示数据** `demo_data.xlsx`（5000 行订单，刻意注入门店名不一致、缺失值、重复订单、合并单元格等问题）。该数据是随机生成的，**不代表任何真实业务**。
3. 下方所有"结果表/异常统计/抽样核对"数字均来自该合成演示数据，**不是真实结果**。拿到真实 Excel 后，用一行命令即可重跑得到真实结果。
4. 本方案严格以 `SKILL.md` 的四步流程为准绳；去重等 SKILL.md 正文未包含的步骤已明确标注为扩展。

## 二、文件清单

| 文件 | 说明 |
|---|---|
| `group_by_analysis.py` | 主脚本，可扩展处理方案，严格对应 SKILL.md 四步 |
| `make_demo_data.py` | 合成演示数据生成脚本（固定随机种子，可复现） |
| `demo_data.xlsx` | 合成演示数据（3 个 Sheet：订单明细/门店字典/数据说明） |
| `output/analysis_report.xlsx` | 结果报告（5 个 Sheet：分组结果/异常统计/抽样核对/Sheet行数/运行说明） |
| `output/analysis_chart.png` | Step3 柱状图 |
| `output/sampling_check.csv` | 抽样核对记录（独立 CSV） |
| `output/parquet_sheet*.parquet` | 大文件 Parquet 预处理产物 |

## 三、如何用真实数据运行

```bash
python3 group_by_analysis.py \
  --input 你的真实文件.xlsx \
  --sheet 数据所在Sheet名 \
  --group-col store_name \
  --value-col amount \
  --ffill-col category \
  --output-dir output
```

- `--group-col`：分组依据列（如门店名）
- `--value-col`：求和数值列（如订单金额）
- `--ffill-col`：存在合并单元格、需向前填充的列（如品类）；无则留空
- 门店映射表在脚本顶部 `STORE_MAPPING` 字典中维护，可扩展为从数据库/字典 Sheet 加载

## 四、数据质量处理原则（对应题目要求）

| 问题 | 处理方式 | 对应 SKILL.md |
|---|---|---|
| 合并单元格 | `ffill()` 向前填充，记录填充数量 | Step1 第1点 |
| 门店名称不一致 | 正则去标点 `clean_text` + 分类映射 `map_categories` | Step1 第2、3点 |
| 未知门店写法 | 归入 `Others`，不丢弃、不补零 | Step1 `mapping.get(value,'Others')` |
| 门店名缺失 | 单独成组「未知/缺失」，参与统计 | Step1 扩展（NaN 不转零） |
| 金额缺失 | `sum` 自动跳过 NaN；订单仍计入 `size`；不补零 | Step2（用 size 而非 count） |
| 完全重复行 | 去重并记录数量（**SKILL.md 正文未含，属扩展**） | 扩展步骤，已留痕 |
| 同 ID 冲突订单 | 保留第一条，冲突记入异常统计与抽样核对 | 扩展步骤，已留痕 |

## 五、可扩展点

- 门店映射表可外置为 CSV/数据库，脚本中替换 `STORE_MAPPING` 加载逻辑即可
- Parquet 预处理支持超大文件；`pyarrow` 缺失时自动降级跳过
- 分组维度、值列、ffill 列均通过命令行参数配置，无需改代码
- 异常统计与抽样核对自动随数据变化，无需手工维护

## 六、验证方式

脚本运行后已用独立 pandas 代码交叉验证：去重后行数、金额合计、缺失数、占比和（=1.0000）均一致。
