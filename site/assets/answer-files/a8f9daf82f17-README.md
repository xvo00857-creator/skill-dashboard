# bioservices 公开蛋白列表可复现分析流程

## 概述

本流程以一份公开的人类蛋白 UniProt accession 列表为输入，通过 [bioservices](https://pypi.org/project/bioservices/) 1.16.0 调用公开生物信息学数据库，完成：

1. 输入质控（格式校验、去重、物种校验）
2. UniProt → KEGG 基因 ID 映射
3. KEGG 通路注释
4. KEGG 通路富集分析（Fisher 精确检验 + BH FDR 校正）
5. GO（Gene Ontology）功能注释
6. 结果表格与可视化输出

所有数据均来自公开数据库（UniProt、KEGG、QuickGO/EBI），无任何私有数据。

## 环境要求

- Python 3.9–3.12（实测 3.9.6）
- 依赖包：

```bash
python3 -m pip install --user "bioservices==1.16.0" pandas scipy matplotlib requests
```

- 需联网访问：
  - `https://rest.uniprot.org/`
  - `https://rest.kegg.jp/`
  - `https://www.ebi.ac.uk/QuickGO/`
- NCBI BLAST 相关步骤需要 `NCBI_EMAIL` 环境变量；本流程不包含 BLAST，故无需设置。

## 目录结构

```
analysis/
├── input/
│   └── uniprot_ids.txt      # 输入文件，每行一个 UniProt accession
├── output/                  # 运行后生成
│   ├── qc_report.csv
│   ├── id_mapping.csv
│   ├── pathway_annotation.csv
│   ├── pathway_enrichment.csv
│   ├── go_annotation.csv
│   ├── go_summary.csv
│   ├── run_metadata.json
│   ├── pathway_enrichment.png
│   ├── go_aspect_summary.png
│   └── qc_mapping_yield.png
└── run_analysis.py          # 主脚本
```

## 运行方法

```bash
cd analysis
python3 -W ignore run_analysis.py
```

可选参数：

```bash
python3 -W ignore run_analysis.py --input input/uniprot_ids.txt --outdir output
```

`-W ignore` 用于屏蔽 macOS 系统 LibreSSL 的 `NotOpenSSLWarning`，不影响结果。

实测完整运行约 4 分钟（14 个蛋白，网络正常时）。

## 输入格式

`input/uniprot_ids.txt` 为纯文本：

- 以 `#` 开头的行为注释，会被忽略
- 其余每行一个 6 位人类 UniProt accession（首字母 O/P/Q）

示例：

```
# 注释行
P43403
P06239
```

## 输出说明

| 文件 | 内容 |
|---|---|
| `qc_report.csv` | 每个 accession 的格式校验、基因名、物种、是否通过 |
| `id_mapping.csv` | UniProt accession 与 KEGG 基因 ID 的对应关系 |
| `pathway_annotation.csv` | 每个蛋白所属的 KEGG 通路 |
| `pathway_enrichment.csv` | 通路富集结果：命中数、通路大小、富集倍数、OR、p 值、BH FDR、命中蛋白 |
| `go_annotation.csv` | 每条 GO 注释的明细（GO ID、名称、方面、证据码、参考文献） |
| `go_summary.csv` | 按 P/F/C 三个方面统计注释数、唯一 GO 术语数、覆盖蛋白数 |
| `run_metadata.json` | 运行时间、版本、参数、数据来源、统计方法、已知限制 |
| `pathway_enrichment.png` | 富集气泡图（前 15 条最显著通路） |
| `go_aspect_summary.png` | GO 三方面注释数柱状图 |
| `qc_mapping_yield.png` | 质控与 ID 映射得率柱状图 |

## 统计方法

- **富集检验**：对每条通路构建 2×2 列联表（输入基因是否在通路中 × 背景基因是否在通路中），使用 `scipy.stats.fisher_exact` 单侧（greater）精确检验。
- **背景基因集**：KEGG 人类全部通路-基因注释，实时从 `https://rest.kegg.jp/link/pathway/hsa` 获取（实测 372 条通路、9422 个基因、39574 条注释）。
- **多重检验校正**：Benjamini-Hochberg FDR，显著性阈值 FDR < 0.05。
- **富集倍数**：(通路中输入基因数 / 输入基因总数) / (通路基因数 / 背景基因总数)。

## 可复现性说明

- 脚本固定使用 `bioservices==1.16.0`，版本号写入 `run_metadata.json`。
- 背景注释为运行时实时获取，KEGG 注释更新会导致结果轻微变化；`run_metadata.json` 记录了运行时间（UTC）。
- 所有随机过程：本流程无随机数，结果完全由输入和数据库当时状态决定。

## 已知版本兼容问题（1.16.0 实测）

1. `UniProt.search` 的 `frmt` 参数必须用 `"tsv"`，Skill 文档中的 `"tab"` 已失效。
2. `UniProt.mapping` 返回 `{"results":[{"from","to"}], "failedIds":[]}`，非旧版 `{id: [targets]}`。
3. `KEGG.get_pathway_by_gene` 返回 `dict`（pathway_id → name），非 list。
4. `QuickGO.Annotation` 使用 `geneProductId=` 参数且返回 JSON dict，非旧版 `protein=` + TSV 字符串；每页上限 99 条。
5. `PSICQUIC` 在 1.16.0 中无法导入，故本流程不含蛋白互作步骤。
6. `KEGG.link()` 因 bioservices 内部请求 `/list/organism` 返回 HTTP 400 而不可用，背景注释改用 `requests` 直连 KEGG REST。
7. `UniChem.get_compound_id_from_kegg` 等 per-source 方法已移除；且 `get_compounds` 的 `source_type` 不支持 `"kegg"`。
