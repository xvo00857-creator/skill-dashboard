# 门店订单数据处理方案（chroma Skill 落地）

## 一、Skill 能力边界与职责划分（重要）

本题随附的 `chroma` Skill（见 `SKILL.md`）是一个**开源向量/嵌入数据库**，核心能力为：
存储 embedding 与元数据、向量相似度检索、全文/元数据过滤、RAG 与语义检索。

因此本方案严格按其真实能力边界使用：

| 环节 | 承担者 | 说明 |
|------|--------|------|
| 门店名变体语义匹配 | **chroma** | `collection.add` 建主数据索引，`collection.query` 做相似度匹配，元数据携带规范门店信息 |
| 分块读取大文件 | pandas | `read_csv(chunksize=...)` |
| 重复订单检测 | pandas | 按 `order_id` 去重标记 |
| 缺失值统计 | pandas | 按列计数，**不补 0** |
| 金额聚合 | pandas | 仅累加非空金额，缺失单独计数 |
| 抽样核对 | pandas | 固定 `random_state`，可复现 |

chroma **不**承担去重、缺失值填充、数值聚合等关系型数据处理工作——这些超出其能力边界，
若强行让 chroma 完成属于扩张职责。

## 二、关键设计决策

1. **缺失金额不补 0**：聚合时缺失金额行不计入 `total_amount`，单独计入
   `missing_amount_orders`；结果表中同时展示"有效金额订单数"与"缺失金额订单数"，
   避免把未知误读为 0。
2. **重复订单不静默合并**：按 `order_id` 检测，重复行写入 `duplicate_orders.csv`，
   默认不参与聚合（首条参与），并在异常统计中报告重复行数与涉及的 order_id 数。
3. **门店名两级匹配**：
   - 先做**规范化精确匹配**（去空格/括号/大小写），确定性优先；
   - 再用 chroma 做**语义相似度匹配**，距离 ≤ 阈值才采纳；
   - 低于阈值的一律标记 `UNRESOLVED`，写入 `unresolved_stores.csv` 进入人工复核，
     **绝不强行归并**。
4. **负金额标记但不丢弃**：计入 `negative_amount_rows` 异常，金额仍参与求和
   （可能是退款），由复核人判断，避免静默篡改数据。
5. **可扩展**：分块读取（默认 10 万行/块）、chroma 批量写入（500 条/批）、
   `PersistentClient` 持久化索引，可重复运行增量数据。

## 三、实测发现的模型限制（影响交付结果）

chroma 默认嵌入模型为 `all-MiniLM-L6-v2`（SKILL.md 明确记载），该模型以英文为主。
冒烟测试实测：

- "星巴克咖啡(国贸店)" 与主数据 "星巴克咖啡（国贸店）" → 规范化精确匹配成功 ✓
- "Starbucks 国贸店" 与 "星巴克咖啡（国贸店）" → 语义距离 **0.9133** > 阈值 0.75，未匹配 ✗
- "luckin coffee 望京店" 与 "瑞幸咖啡（望京店）" → 语义距离 **0.8161** > 阈值，未匹配 ✗

即默认模型**无法**将英文品牌名（Starbucks/luckin）与中文品牌名（星巴克/瑞幸）对齐。
这些记录按设计进入 UNRESOLVED 人工复核，而不是被错误归并。生产环境建议按 SKILL.md
"Custom embedding function" 一节接入多语言模型（如
`paraphrase-multilingual-MiniLM-L12-v2`），或维护"英文品牌→中文主数据"别名表做前置映射。

## 四、文件结构

```
solution/
├── store_name_resolver.py   # chroma 门店名解析器（唯一使用 chroma 的模块）
├── etl_pipeline.py          # 分块 ETL、异常统计、聚合、抽样核对
├── run_smoke.py             # 合成数据冒烟测试（非真实业务数据）
├── smoke_data/              # 冒烟测试输入（合成）
│   ├── store_master.csv
│   └── orders.csv
├── chroma_smoke_db/         # chroma 持久化索引（运行后生成）
└── output/                  # 运行产物
    ├── result_by_store.csv      # 结果表（按规范门店聚合）
    ├── anomalies.json           # 异常统计
    ├── duplicate_orders.csv     # 重复订单明细
    ├── unresolved_stores.csv    # 未解析门店（人工复核）
    ├── sample_verification.csv  # 抽样核对记录
    └── pipeline_summary.txt     # 运行摘要
```

## 五、如何对真实数据运行

```bash
pip install chromadb pandas
cd solution
python3 -c "
from etl_pipeline import run_pipeline
run_pipeline(
    input_path='/path/to/真实订单.csv',
    store_master_path='/path/to/门店主数据.csv',
    output_dir='./output',
    chunksize=100000,
    distance_threshold=0.75,   # 需在真实主数据上抽样校准
    sample_size=50,
    sample_seed=42,
)
"
```

真实订单 CSV 需包含列：`order_id, store_name, amount`（`order_time` 可选）；
门店主数据 CSV 需包含：`canonical_id, canonical_name`（`brand, city, area` 可选）。

## 六、待确认事项

1. **未提供真实数据文件**：本次消息仅随附 `chroma.zip`（Skill 本身），未包含任何
   门店/订单数据。当前结果表与异常统计均来自**合成冒烟数据**，用于验证流程可运行，
   不代表真实业务指标。提供真实 CSV 后可直接按第五节运行。
2. **距离阈值 0.75** 为保守默认值，需在真实主数据上抽样校准（建议取
   "正确匹配距离分布"与"错误匹配距离分布"的分界点）。
3. **负金额处理策略**：当前标记异常但仍计入金额（按退款假设）。若业务规定负金额
   应剔除，需确认后调整。
4. **重复订单处理策略**：当前保留首条、排除后续重复行。若重复行代表状态更新
   （如改单），需确认取最新还是取首条。
