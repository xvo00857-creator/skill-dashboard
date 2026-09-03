# 用户反馈主题去重与优先级工作流（最小可用版）

## 1. 概述

基于 `product_brief.md`（智能随行杯新品任务简报），实现一个最小可用工作流：

> 输入用户反馈 → 输出去重后的主题、优先级和下一步行动

本工作流分为两层：

| 层 | 职责 | 状态 |
|----|------|------|
| **数据获取层** | 通过 Rube MCP（Composio `_2chat` 工具包）从 2chat 拉取用户反馈 | **阻塞**——当前环境未连接 Rube MCP，详见第 6 节 |
| **本地处理层** | 对反馈 JSON 做主题归类、去重、优先级评分、下一步行动生成 | **已实现并验证** |

本仓库交付的是本地处理层。数据获取层需在 Rube MCP 连接后按 SKILL.md 流程补齐。

## 2. 文件清单

| 文件 | 说明 |
|------|------|
| `feedback_pipeline.py` | 主程序，仅依赖 Python 3.8+ 标准库 |
| `sample_feedback.json` | 样例输入（**合成测试数据，非真实用户评价**） |
| `sample_output.json` | 样例输出（由程序实际运行生成） |
| `README.md` | 本文档 |

## 3. 运行环境

- Python 3.8+（实测 Python 3.13.13）
- 无第三方依赖，无需 `pip install`

## 4. 接口与命令定义

### 4.1 命令行接口

```bash
# 从文件读取，结果写 stdout
python3 feedback_pipeline.py -i <输入.json>

# 从 stdin 读取
cat feedback.json | python3 feedback_pipeline.py

# 从文件读取，结果写入文件
python3 feedback_pipeline.py -i <输入.json> -o <输出.json>
```

| 参数 | 说明 |
|------|------|
| `-i, --input` | 输入 JSON 文件路径；缺省时从 stdin 读取 |
| `-o, --output` | 输出 JSON 文件路径；缺省时写 stdout |
| `--help` | 显示帮助 |

### 4.2 退出码

| 退出码 | 含义 |
|--------|------|
| 0 | 成功 |
| 1 | 输入错误（文件不存在、JSON 非法、格式不符、内容为空、ID 重复等） |
| 2 | 处理错误（程序内部异常） |

### 4.3 输入格式

JSON 数组，或含 `feedback` / `items` / `data` 数组字段的对象。每条反馈：

```json
{
  "id": "fb-001",           // 必填（可空，自动生成 auto-N）；不可重复
  "content": "反馈文本",     // 必填，也接受 text 或 message 字段名
  "source": "2chat",        // 可选
  "timestamp": "2026-08-10T09:12:00+08:00"  // 可选
}
```

### 4.4 输出格式

```json
{
  "meta": {
    "total_feedback": 12,
    "total_themes": 8,
    "dedup_jaccard_threshold": 0.5,
    "dedup_overlap_threshold": 0.65,
    "pipeline_version": "0.1.0",
    "note": "本地处理层结果；2chat真实反馈拉取需Rube MCP，当前环境未连接"
  },
  "themes": [
    {
      "theme_key": "leak_seal",
      "theme_label": "漏水与密封",
      "is_core_selling_point": false,
      "raw_feedback_count": 2,
      "deduped_group_count": 2,
      "priority": "P0",
      "priority_score": 12,
      "priority_reasons": ["..."],
      "severity_hits": ["漏水", "退货"],
      "next_actions": ["..."],
      "deduped_groups": [
        {
          "representative_id": "fb-007",
          "representative_content": "...",
          "member_ids": ["fb-007"],
          "member_contents_preview": ["..."]
        }
      ],
      "source_feedback_ids": ["fb-007", "fb-008"]
    }
  ]
}
```

主题按优先级排序（P0 → P1 → P2），同级按分数降序。

## 5. 处理逻辑

### 5.1 主题归类

基于 `product_brief.md` 的产品维度定义 9 个主题，关键词命中即归类（一条反馈可命中多个主题）：

| 主题 | 是否核心卖点 | 关键词依据 |
|------|-------------|-----------|
| 保温性能 | 是 | 12小时保温（核心卖点） |
| 重量与便携 | 是 | 280g（核心卖点） |
| 杯盖与拆洗 | 是 | 可拆洗杯盖（核心卖点） |
| 漏水与密封 | 否 | 安全相关 |
| 材质与安全 | 否 | 食品接触材料报告未提供 |
| 防水等级 | 否 | 防水等级未提供 |
| 价格与性价比 | 否 | 建议零售价 199 元 |
| 外观与颜色 | 否 | 品牌主色 #176B87 |
| 容量 | 否 | 用户需求维度 |
| 其他 | 否 | 未命中任何关键词的兜底 |

### 5.2 去重

对同一主题下的反馈，使用**字符二元组（char bigram）**计算文本相似度：

- **Jaccard 系数 ≥ 0.5**，或
- **重叠系数 ≥ 0.65**（较短文本至少 8 个二元组时启用，用于捕获"一条是另一条的复述"）

满足任一条件即视为重复，合并为一组，保留首条为代表。

### 5.3 优先级评分

| 因子 | 分值 |
|------|------|
| 每个去重后反馈组 | +2 |
| 原始反馈量 ≥ 5 | +3 |
| 命中严重度关键词（漏水/退货/异味/安全/投诉等） | +8 |
| 涉及核心卖点且含负面表述 | +4 |

| 优先级 | 条件 |
|--------|------|
| **P0** | 总分 ≥ 10，或命中任何严重度关键词 |
| **P1** | 总分 ≥ 5 |
| **P2** | 其他 |

### 5.4 下一步行动

每个主题有默认行动模板；命中特定条件时追加：

- 材质与安全 → 标注"食品接触材料报告"为待补项（简报明确未提供）
- 防水等级 → 标注"防水等级"为待补项（简报明确未提供）
- 价格与性价比 → 提醒禁止编造竞品价格（简报明确禁止）
- 命中"漏水" → 48 小时内密封复测并同步客服话术
- 命中"异味" → 留样送检并暂停相关批次发货建议

## 6. 阻塞项：Rube MCP 未连接（影响 2chat 数据获取）

### 6.1 SKILL.md 的要求

随消息上传的 Skill（`-2chat-automation/SKILL.md`）明确要求：

1. **前置条件**：Rube MCP 必须已连接，`RUBE_SEARCH_TOOLS` 可用
2. **必须先调用** `RUBE_SEARCH_TOOLS` 获取当前工具 schema（"Always search first"，"Never hardcode tool slugs"）
3. 通过 `RUBE_MANAGE_CONNECTIONS` 确认 `_2chat` 连接状态为 ACTIVE
4. 通过 `RUBE_MULTI_EXECUTE_TOOL` 执行 2chat 工具

### 6.2 实际检查结果

- 在当前环境中搜索 `RUBE_SEARCH_TOOLS` 等工具，**未找到任何 Rube MCP 工具**
- SKILL.md 说明 Rube MCP 需在客户端配置中添加 `https://rube.app/mcp` 作为 MCP server；当前会话不具备该配置，也无法自行添加
- 因此**无法执行** SKILL.md 规定的工具发现、连接检查和 2chat 数据拉取步骤

### 6.3 影响范围

- **已完成**：本地反馈处理（主题归类、去重、优先级、下一步行动），可对任意符合格式的反馈 JSON 运行
- **未执行**：从 2chat 拉取真实用户反馈——**未将任何计划或模拟结果写成已执行**
- `sample_feedback.json` 为**合成测试数据**，文件内已标注，不代表真实用户评价（简报禁止编造用户评价）

### 6.4 恢复步骤

当 Rube MCP 可用后，按 SKILL.md 执行：

1. 确认 `RUBE_SEARCH_TOOLS` 可响应
2. 调用 `RUBE_MANAGE_CONNECTIONS`（toolkits: `["_2chat"]`），确认状态 ACTIVE
3. 调用 `RUBE_SEARCH_TOOLS`（use_case: "2chat operations"）发现可用工具及 schema
4. 用 `RUBE_MULTI_EXECUTE_TOOL` 拉取反馈，转换为本程序输入格式后管道执行：
   ```bash
   <2chat拉取结果转换为JSON> | python3 feedback_pipeline.py
   ```

## 7. 失败处理

| 场景 | 处理方式 |
|------|---------|
| 输入文件不存在 | stderr 输出错误，退出码 1 |
| stdin 无数据且未指定 -i | stderr 提示，退出码 1 |
| JSON 解析失败 | 指出解析错误位置，退出码 1 |
| 非数组/对象格式 | 说明期望格式，退出码 1 |
| 缺少 content/text/message | 指出第几条，退出码 1 |
| 内容为空字符串 | 指出第几条，退出码 1 |
| id 重复 | 指出重复 id，退出码 1 |
| 反馈数组为空 | 提示数组为空，退出码 1 |
| 输出文件无法写入 | stderr 输出错误，退出码 1 |
| 处理中未预期异常 | 输出异常类型和消息，退出码 2 |

## 8. 合规说明（依据 product_brief.md）

- 未编造第三方检测结论、销量、用户评价、竞品价格
- 样例输入为合成测试数据并已标注
- 食品接触材料报告、防水等级在输出中明确列为"待补项"
- 结论（程序实际输出）与假设（2chat 数据获取层待实现）已分开
- 所有输出均为中文
