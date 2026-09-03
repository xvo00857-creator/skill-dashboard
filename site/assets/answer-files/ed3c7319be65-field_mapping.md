# 字段映射表

> 说明：下表中的"Adobe 原始字段"为逻辑字段名。真实字段名与类型必须以
> `RUBE_SEARCH_TOOLS` / `RUBE_GET_TOOL_SCHEMAS` 返回的 schema 为准
> （SKILL.md 要求：schema compliance，不得自行命名字段）。
> 模拟脚本中使用的 mock 字段与本表逻辑字段一致，便于上线后替换。

## 1. 数据收集阶段（Adobe → 原始记录）

| 逻辑字段 | 类型 | 含义 | 示例 | 来源（逻辑） |
|----------|------|------|------|--------------|
| item_id | string | Adobe 资源唯一标识 | "adobe:file:1a2b3c" | 收集工具返回 |
| item_name | string | 文件名/资源名 | "weekly_creative_brief.pdf" | 收集工具返回 |
| item_type | string | 资源类型 | "pdf" / "image" / "document" | 收集工具返回 |
| size_bytes | integer | 文件大小（字节） | 245760 | 收集工具返回 |
| owner_email | string | 所有者邮箱 | "alice@example.com" | 收集工具返回 |
| created_at | string(ISO8601) | 创建时间 | "2026-08-06T10:12:33Z" | 收集工具返回 |
| modified_at | string(ISO8601) | 最后修改时间 | "2026-08-10T15:40:01Z" | 收集工具返回 |
| status | string | 资源状态 | "active" / "archived" | 收集工具返回 |

## 2. 摘要生成阶段（原始记录 → 周报摘要）

| 摘要字段 | 类型 | 计算/映射规则 | 依赖的原始字段 |
|----------|------|---------------|----------------|
| report_week | string | 报告所属周，格式 `YYYY-Www`，按 Asia/Shanghai 计算 | 运行时间 |
| generated_at | string(ISO8601) | 摘要生成时间 | 运行时间 |
| total_items | integer | 原始记录总数 | item_id |
| items_by_type | object | 按 item_type 分组计数，如 `{"pdf":12,"image":30}` | item_type |
| new_items_this_week | integer | created_at 落在本周一 00:00 至运行时刻的记录数 | created_at |
| modified_items_this_week | integer | modified_at 落在本周区间且 created_at 早于本周的记录数 | created_at, modified_at |
| total_size_bytes | integer | 所有记录 size_bytes 求和 | size_bytes |
| top_owners | array<object> | 按 owner_email 聚合记录数，取前 3，形如 `[{"owner_email":"...","count":8}]` | owner_email |
| anomalies | array<string> | 异常说明列表（见异常处理文档），无异常为空数组 | 全部字段 |

## 3. 通知阶段（摘要 → 通知内容）

| 通知字段 | 类型 | 映射规则 | 示例 |
|----------|------|----------|------|
| to | string | 负责人邮箱（配置项，非从 Adobe 数据推断） | "owner@example.com" |
| subject | string | `[Adobe周报] {report_week} 共{total_items}项，新增{new_items_this_week}项` | "[Adobe周报] 2026-W33 共42项，新增5项" |
| body_text | string | 纯文本摘要：周次、总数、新增/修改数、类型分布、Top3 贡献者、异常数 | 见下 |
| body_html | string | HTML 版摘要（若通知工具支持） | 表格形式 |
| summary_ref | string | 摘要文档/文件的引用标识（由摘要工具返回），用于通知中附带链接 | "adobe:doc:9z8y7x" |
| sent_at | string(ISO8601) | 发送时间，由通知工具返回后回填 | "2026-08-11T09:00:05+08:00" |

通知正文模板（纯文本）：

```
Adobe 每周数据摘要 {report_week}
生成时间：{generated_at}

本周资源总数：{total_items}
本周新增：{new_items_this_week}
本周修改：{modified_items_this_week}
总大小：{total_size_bytes} 字节

类型分布：
{items_by_type 每行 "- {type}: {count}"}

贡献者 Top3：
{top_owners 每行 "- {owner_email}: {count} 项"}

异常：{anomalies 数量} 条
{anomalies 每行 "- {msg}"}

摘要详情：{summary_ref}
```

## 4. 配置项（不随 Adobe 数据变化）

| 配置键 | 说明 | 模拟值 |
|--------|------|--------|
| OWNER_EMAIL | 负责人通知地址 | "owner@example.com"（模拟，不发送） |
| TIMEZONE | 周计算时区 | "Asia/Shanghai" |
| WEEK_START | 每周起始日 | "monday" |
| COLLECT_SCOPE | 收集范围（目录/项目 ID） | 以 RUBE_SEARCH_TOOLS 返回 schema 字段为准 |
