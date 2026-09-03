# 用户反馈主题分析工作流

基于 `product_brief.md`（智能随行杯新品任务简报）设计的最小可用工作流。
输入用户反馈，输出**去重后的主题、优先级和下一步行动**。

纯 Python 标准库实现，无第三方依赖，不调用外部 API，不生成或编造任何数据。

---

## 一、接口 / 命令定义

### 命令行

```bash
# 从文件读取，结果写入文件
python3 feedback_workflow.py --input feedback.json --output result.json

# 从文件读取，结果输出到终端
python3 feedback_workflow.py -i feedback.json

# 从标准输入读取（管道）
cat feedback.json | python3 feedback_workflow.py

# 调试日志
python3 feedback_workflow.py -i feedback.json -v
```

| 参数 | 缩写 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| `--input` | `-i` | 否 | stdin | 输入 JSON 文件路径；省略则从标准输入读取 |
| `--output` | `-o` | 否 | stdout | 输出 JSON 文件路径；省略则输出到标准输出 |
| `--verbose` | `-v` | 否 | 关闭 | 输出 DEBUG 级别日志 |

### 退出码

| 退出码 | 含义 |
|---|---|
| 0 | 成功 |
| 1 | 输入错误（文件不存在、JSON 非法、格式不符、空输入、ID 重复等） |
| 2 | 未预期的内部错误（会打印完整堆栈到 stderr） |

### Python 函数接口

也可作为模块导入使用：

```python
from feedback_workflow import load_feedback, analyze, FeedbackItem

# raw 为 json.loads() 后的对象
feedback = load_feedback(raw)       # -> list[FeedbackItem]
result = analyze(feedback)          # -> dict（与 CLI 输出结构一致）
```

---

## 二、输入格式

JSON，支持两种顶层结构：

```json
{
  "feedback": [
    {"id": "fb-001", "text": "保温效果很好", "source": "京东", "timestamp": "2026-08-10"}
  ]
}
```

或直接传数组：

```json
[
  {"id": "fb-001", "text": "保温效果很好"}
]
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | string | 否 | 反馈唯一标识；省略时自动生成 `auto-N`；重复则报错 |
| `text` | string | **是** | 反馈正文；空白字符串视为无效 |
| `source` | string | 否 | 来源渠道（仅记录，不参与分析） |
| `timestamp` | string | 否 | 时间戳（仅记录，不参与分析） |

---

## 三、输出格式

```json
{
  "summary": {
    "total_feedback": 14,
    "unique_feedback": 13,
    "duplicates_removed": 1,
    "theme_count": 10
  },
  "themes": [
    {
      "theme": "安全健康",
      "priority": "P0",
      "count": 3,
      "feedback_ids": ["fb-004", "fb-008", "fb-009"],
      "sample_texts": ["..."],
      "next_actions": ["..."],
      "结论_假设": "结论",
      "note": "食品接触材料报告尚未提供，相关结论需以检测报告为准"
    }
  ],
  "pending_items": [
    "首发日期尚未确定",
    "防水等级尚未提供",
    "食品接触材料报告尚未提供"
  ]
}
```

| 字段 | 说明 |
|---|---|
| `summary.total_feedback` | 输入反馈总数 |
| `summary.unique_feedback` | 去重后反馈数（按归一化文本精确去重） |
| `summary.duplicates_removed` | 被合并的重复条数 |
| `themes[].theme` | 主题名（见下方主题表） |
| `themes[].priority` | 优先级 P0–P3 |
| `themes[].count` | 该主题下反馈条数（去重后计数，重复文本只计一次） |
| `themes[].feedback_ids` | 该主题包含的全部反馈 ID |
| `themes[].sample_texts` | 最多 3 条代表性原文 |
| `themes[].next_actions` | 下一步行动列表 |
| `themes[].结论_假设` | `"结论"` = 关键词直接命中；`"待人工确认"` = 未命中预定义主题 |
| `themes[].note` | 备注（如涉及未提供的检测报告/规格时提示） |
| `pending_items` | 来自 product_brief.md 的全局待补项 |

---

## 四、主题与优先级规则

### 主题（基于 product_brief.md 已知产品属性定义）

| 主题 | 匹配关键词示例 |
|---|---|
| 保温性能 | 保温、保冷、温度、凉了、不保温、热水、冰水 |
| 重量便携 | 重、轻、便携、携带、通勤、重量、轻便 |
| 杯盖清洗 | 杯盖、盖子、拆洗、清洗、清洁、缝隙、密封圈 |
| 价格价值 | 价格、贵、便宜、199、性价比、值、定价 |
| 外观颜色 | 颜色、外观、好看、丑、配色、青色、蓝绿、颜值 |
| 质量耐用 | 坏了、断裂、掉漆、变形、破损、质量、耐用、划痕 |
| 安全健康 | 安全、异味、有毒、烫伤、漏水、食品接触、材质、304、316、不锈钢、发霉 |
| 防水性能 | 防水、进水、泡水、淋水 |
| 物流包装 | 快递、包装、物流、发货、到货、配送 |
| 其他 | 以上均未命中（回退，标记"待人工确认"） |

一条反馈可同时命中多个主题（如"杯盖有异味"同时归入杯盖清洗和安全健康）。

### 优先级

| 级别 | 触发条件 |
|---|---|
| **P0** | 任一条反馈命中高严重度关键词：安全、有毒、烫伤、漏水、异味、断裂、爆炸、着火、漏电、割手、受伤、发霉 |
| **P1** | 去重后该主题反馈数 ≥ 3 |
| **P2** | 去重后该主题反馈数 ≥ 2 |
| **P3** | 去重后该主题反馈数 = 1 |

P0 不受频次限制，单条即可触发。同优先级按反馈数降序排列。

### 去重逻辑

对反馈文本做归一化（去首尾空白、压缩连续空白、转小写）后，**完全相同**的文本视为重复，合并为一条但保留全部原始 ID。
注意：这是精确去重，不做语义相似度判断（避免误合并）。

---

## 五、失败处理

| 场景 | 处理方式 | 退出码 |
|---|---|---|
| 输入文件不存在 | stderr 打印 `输入文件不存在：<path>` | 1 |
| 输入不是合法 JSON | stderr 打印 JSON 解析错误位置 | 1 |
| 顶层不是对象/数组 | stderr 打印格式要求 | 1 |
| `feedback` 不是数组 | stderr 打印类型错误 | 1 |
| 反馈列表为空 | stderr 打印"至少需要一条有效反馈" | 1 |
| 某条缺少 `text` 或为空白 | stderr 打印第几条出错 | 1 |
| 反馈 ID 重复 | stderr 打印重复的 ID | 1 |
| 文件编码/读取异常 | stderr 打印具体 OS 错误 | 1 |
| 未预期的运行时异常 | stderr 打印完整堆栈（`logger.exception`） | 2 |

错误信息输出到 stderr，stdout 不会产生半截 JSON，便于脚本管道安全使用。

---

## 六、结论与假设的区分

遵循 product_brief.md「结论与假设分开」的要求：

- **结论**（`"结论_假设": "结论"`）：主题由反馈文本中的关键词直接命中，有原文可查。
- **待人工确认**（`"结论_假设": "待人工确认"`）：归入"其他"的反馈，未命中任何预定义关键词，需人工复核分类。
- **优先级阈值**（P1 ≥ 3 条、P2 ≥ 2 条）是规则设定的启发式判断，可在代码常量 `P1_MIN_COUNT` / `P2_MIN_COUNT` 中调整，不作为客观结论。
- **下一步行动**是基于主题+优先级的规则映射，不代表已执行。
- **待补项**（防水等级、食品接触材料报告、首发日期）来自 product_brief.md 明确标注的不完整信息，输出中始终附带，相关主题会额外提示。

---

## 七、文件清单

| 文件 | 说明 |
|---|---|
| `feedback_workflow.py` | 主程序（CLI + 可导入函数） |
| `sample_feedback.json` | 样例输入（14 条测试反馈，含 1 条重复、1 条未命中主题） |
| `sample_output.json` | 运行样例输入产生的实际输出 |
| `README.md` | 本文档 |

运行样例：

```bash
python3 feedback_workflow.py -i sample_feedback.json -o sample_output.json
```

---

## 八、限制与不做的事

- **不调用任何外部 API 或 LLM**：主题匹配完全基于关键词，结果可复现、可审计。
- **不编造数据**：不生成用户评价、销量、检测结论、竞品价格。
- **不做情感分析**：正面和负面反馈都会归入同一主题，优先级由严重度关键词和频次决定，不由情感倾向决定。
- **不做语义去重**：仅精确文本去重；"保温不行"和"不保温"不会被合并，需后续迭代引入语义模型。
- **不做时序分析**：`timestamp` 字段仅透传记录，不参与趋势判断。
