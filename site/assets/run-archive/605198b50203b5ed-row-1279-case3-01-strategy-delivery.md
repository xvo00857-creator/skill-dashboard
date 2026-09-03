# 智能随行杯新品上市可执行方案（strategy-delivery）

> 生成时间：2026-08-26
> 依据文件：product_brief.md、product_release_notes.md、edge_cases.csv
> 关联 Skill：google-ads-api-account-diagnostics（分类：营销与增长）
> 声明：本文严格区分"已确认事实"与"假设/待补项"，不编造销量、用户评价、第三方检测结论或竞品价格。

---

## 一、输入校验与异常处理

### 1.1 实际读取的文件

| 文件 | 状态 | 说明 |
|---|---|---|
| product_brief.md | 已读取，有效 | 智能随行杯新品简报，含目标用户、核心卖点、零售价、素材、禁止项、不完整信息 |
| product_release_notes.md | 已读取，**不匹配** | 内容为"星河笔记 2.3"笔记应用发布说明，与智能随行杯无任何关联，判定为无关输入，不纳入本方案 |
| edge_cases.csv | 已读取，**合成测试数据** | 6 行记录，含重复、空值、异常负值、公式注入，非真实 Google Ads 账户数据 |

### 1.2 edge_cases.csv 逐条诊断

| record_id | status | value | notes | 诊断结果 | 处理方式 |
|---|---|---|---|---|---|
| 1 | ok | 120 | 正常记录 | 有效 | 保留 |
| 2 | ok | 120 | 重复记录 | **重复**（出现 2 次，record_id 相同） | 去重，仅保留 1 条 |
| 3 | （空） | （空） | - | **缺失**：status 与 value 均为空 | 标记为无效记录，排除统计 |
| 4 | error | -999 | 异常负值 | **异常**：error 状态 + 负值，非有效业务指标 | 排除，单独记录为异常样本 |
| 5 | ok | `=HYPERLINK("https://example.invalid","do not execute")` | 公式注入测试文本 | **不安全输入**：单元格内含 Excel 公式注入载荷 | 作为纯文本处理，不执行公式；下游使用时必须转义或剥离 `=` 前缀 |

**结论**：edge_cases.csv 为合成测试集，无真实业务含义，不能用于任何营销决策或 Google Ads 诊断。其价值仅在于验证输入校验逻辑。

### 1.3 product_brief.md 中明确的不完整信息

- 首发日期：尚未确定
- 防水等级：尚未提供
- 食品接触材料报告：尚未提供

以上三项列为**待补项**，方案中涉及首发节奏、防水卖点、安全合规表述时均标注为假设。

---

## 二、Skill 执行状态：google-ads-api-account-diagnostics

### 2.1 Skill 核心要求（摘自 SKILL.md）

该 Skill 用于诊断 Google Ads 账户性能问题（转化流失、线索量低、展示份额流失、离线上传管道异常），核心执行规则包括：

1. **必须使用 MCP 工具直接调用**：通过 `list_accessible_customers`（或 `customers_list_accessible_customers`）获取可访问客户 ID，再用 `search` 工具执行 GAQL 查询，用 `get_resource_metadata` 确认字段名。
2. **禁止编写自定义 Python 脚本或使用 Google Ads 客户端库**：SKILL.md 明确指出在评估沙箱内这样做会认证失败。
3. **仅查询已启用的客户账户**：必须过滤 `customer_client.status = 'ENABLED' AND customer_client.manager = FALSE`，不得查询已停用或管理员账户。
4. **change_event 查询约束**：必须带 `LIMIT ≤ 10000`、必须按 `change_event.change_date_time` 过滤近 30 天、不得选择 `metrics.*` 字段。
5. **离线上传无结果时立即停止**：若 `offline_conversion_upload_conversion_action_summary` 返回空，应直接报告"无可访问账户的离线转化上传数据"，不得重试或生成自定义脚本。

### 2.2 当前环境阻断情况

| Skill 所需条件 | 当前状态 | 影响 |
|---|---|---|
| Google Ads MCP 工具（`list_accessible_customers`、`search`、`get_resource_metadata`） | **不可用**：当前工具集中无上述 MCP 工具 | 无法执行任何 GAQL 查询 |
| Google Ads API 认证凭据（OAuth / developer token） | **未提供** | 无法调用 API |
| 客户 ID（customer_id） | **未提供** | 无法定位目标账户 |
| 可访问的客户账户列表 | **无法获取**（依赖上述工具） | 无法筛选 ENABLED 非管理员账户 |

**阻断结论**：Skill 的四项诊断工作流（转化流失、展示份额流失、低线索量、离线上传管道）均**无法实际执行**。不存在可降级为本地脚本的路径——SKILL.md 明确禁止使用自定义 Python 脚本或客户端库，且无凭据时任何脚本都会认证失败。

### 2.3 降级方案与复测方法

**降级方案**：
- 本方案的渠道策略部分将 Google Ads 列为候选渠道，但**不包含任何账户级诊断结论、实际展示份额数据、转化数据或出价建议**——这些均需 API 访问才能获得。
- 预先编写好待执行的 GAQL 查询模板（见下方），一旦环境具备 MCP 工具与凭据，可直接填入参数运行。

**复测方法**：
1. 确认 Google Ads MCP 工具已注册并可用（`list_accessible_customers`、`search`、`get_resource_metadata`）。
2. 调用 `list_accessible_customers` 获取可访问客户资源名列表。
3. 对每个客户执行：
   ```sql
   SELECT customer_client.id, customer_client.descriptive_name,
          customer_client.status, customer_client.manager
   FROM customer_client
   WHERE customer_client.status = 'ENABLED' AND customer_client.manager = FALSE
   ```
4. 拿到 ENABLED 非管理员客户 ID 后，按 Skill 工作流 1–4 依次执行诊断查询。
5. 若 `offline_conversion_upload_conversion_action_summary` 返回空，按 Skill 规则立即停止该工作流并报告无数据。

**预设 GAQL 查询模板**（待凭据就绪后执行）：

- 转化流失诊断（工作流 1）：
  ```sql
  SELECT campaign.name, metrics.conversions, metrics.conversions_value,
         metrics.cost_micros, segments.date, segments.device,
         segments.conversion_action
  FROM campaign
  WHERE segments.date >= '{start_date}' AND segments.date <= '{end_date}'
  ```
  注意：`metrics.cost_micros` 需除以 1,000,000 得到标准货币金额。

- 展示份额流失诊断（工作流 2）：
  ```sql
  SELECT campaign.name, metrics.search_impression_share,
         metrics.search_rank_lost_impression_share,
         metrics.search_budget_lost_impression_share
  FROM campaign
  WHERE segments.date >= '{start_date}' AND segments.date <= '{end_date}'
  ```
  注意：展示份额返回值为小数（0.35 = 35%）或格式化字符串（如 `"< 0.10"`）。

- 变更事件排查（工作流 3 第 5 步）：
  ```sql
  SELECT change_event.change_date_time, change_event.change_resource_name,
         change_event.resource_change_operation, change_event.changed_fields
  FROM change_event
  WHERE change_event.change_date_time >= '{start_date}'
    AND change_event.change_date_time <= '{end_date}'
  LIMIT 10000
  ```

---

## 三、新品上市可执行方案

> 以下方案基于 product_brief.md 中已确认的信息制定。所有未确认信息均标注为"假设"或"待补"。

### 3.1 受众定义

**已确认**：一二线城市通勤人群。

**人群画像细化（基于"通勤"场景的合理推演，非真实用户调研数据）**：

| 维度 | 描述 | 数据来源 |
|---|---|---|
| 年龄 | 25–40 岁（假设） | 待补：需用户调研验证 |
| 职业 | 办公室白领、互联网/金融/咨询等行业从业者（假设） | 待补 |
| 场景 | 每日通勤（地铁/公交/自驾）、办公室全天使用、短途出差 | 由"通勤人群"推演 |
| 痛点 | 通勤途中饮品温度不可控、杯重增加包内负担、杯盖清洗不便滋生异味 | 由核心卖点反向推演，非真实用户反馈 |
| 价格敏感度 | 199 元定位中高端，需价值感支撑（假设） | 待补：需价格弹性测试 |

**受众分层**：
- **核心层**：每日通勤 ≥ 30 分钟、有热饮习惯的白领（假设）
- **扩展层**：关注健康/环保、愿意为品质生活用品付费的城市青年（假设）
- **暂不触达**：下沉市场价格敏感人群（与 199 元定位不匹配，假设）

### 3.2 信息结构

**核心信息层级**：

```
主信息（一句话价值主张）
  └─ 12 小时保温 × 280g 轻量 × 可拆洗杯盖 —— 通勤杯的"轻净之选"

支撑卖点（3 个，均为已确认事实）
  ├─ 12 小时保温：通勤到办公室，午后仍温热
  ├─ 280g 轻量化：比常规保温杯轻，减轻通勤包负担
  └─ 可拆洗杯盖：彻底清洗，无卫生死角

信任背书
  ├─ 品牌主色 #176B87（已确认视觉资产）
  ├─ 产品白底图（已确认素材）
  ├─ 食品接触材料报告：【待补——未提供，不得在文案中声称"食品级安全"】
  └─ 防水等级：【待补——未提供，不得声称防水性能】

行动号召
  └─ 首发日期：【待补——尚未确定，暂用"即将上市"占位】
```

**信息使用红线**（来自 product_brief.md 禁止项）：
- 不得编造第三方检测结论
- 不得编造销量
- 不得编造用户评价
- 不得编造竞品价格
- 食品接触材料报告未提供前，不得使用"食品级""安全无毒"等表述
- 防水等级未提供前，不得使用"防水""防泼溅"等表述

### 3.3 渠道动作

> 说明：以下为渠道规划，非已执行结果。Google Ads 渠道因 Skill 诊断无法执行，仅列出规划与待诊断项。

| 渠道 | 动作 | 所需素材/条件 | 状态 |
|---|---|---|---|
| **品牌自有阵地** | 官网/小程序产品页上线，白底图+规格+核心卖点 | 产品白底图（已确认）、基础规格（已确认）、品牌主色（已确认） | 可执行 |
| **社交媒体内容** | 小红书/抖音通勤场景种草内容（图文+短视频） | 需场景实拍素材（待补）；首发日期确定后排期 | 部分可执行（素材待补） |
| **Google Ads 搜索广告** | 品牌词+品类词投放，覆盖"保温杯""通勤杯"等搜索意图 | 需 Google Ads 账户、客户 ID、API 凭据、预算、落地页 | **阻断**：无账户/凭据/客户 ID，Skill 诊断无法执行 |
| **电商平台** | 天猫/京东旗舰店首发 | 需平台店铺资质（待补）、首发日期（待补） | 待补 |
| **KOL/达人合作** | 通勤/生活方式领域达人测评 | 需达人资源与预算（待补） | 待补 |

**Google Ads 渠道专项说明**：
- 当前无法执行 Skill 中的账户诊断（转化流失、展示份额、低线索量、离线上传），原因见第二节。
- 若后续获得 Google Ads 账户访问权限，应先按 Skill 工作流完成账户健康诊断，再决定投放策略：
  - 若 `search_budget_lost_impression_share` 高 → 预算受限，需追加预算
  - 若 `search_rank_lost_impression_share` 高 → 广告排名低，需优化出价或质量得分
  - 若转化量异常下降 → 按工作流 1 排查设备/转化行动维度
  - 若离线转化上传异常 → 按工作流 4 检查上传管道健康度

### 3.4 指标体系

> 以下为规划指标，非实际数据。所有数值目标均为假设，需首发后根据实际表现校准。

| 阶段 | 指标 | 定义 | 目标值（假设） | 数据来源 |
|---|---|---|---|---|
| 预热期 | 曝光量 | 品牌内容总展示次数 | 待补 | 各渠道后台 |
| 预热期 | 互动率 | 点赞+评论+收藏 / 曝光 | 待补 | 社交媒体后台 |
| 首发期 | 点击率（CTR） | 广告点击 / 广告曝光 | 待补 | Google Ads（需 API 访问） |
| 首发期 | 转化率（CVR） | 转化次数 / 点击次数 | 待补 | Google Ads + 电商后台 |
| 首发期 | 单次转化成本（CPA） | 总花费 / 转化次数 | 待补 | Google Ads（`metrics.cost_micros` / 1,000,000） |
| 首发期 | 搜索展示份额 | `metrics.search_impression_share` | 待补 | Google Ads API（需访问） |
| 持续期 | 复购率 | 二次购买用户 / 总购买用户 | 待补 | 电商后台 |
| 持续期 | 退货率 | 退货订单 / 总订单 | 待补 | 电商后台 |

**指标获取阻断说明**：
- Google Ads 相关指标（CTR、CVR、CPA、展示份额）均需通过 Skill 规定的 `search` 工具执行 GAQL 查询获取，当前无 API 访问，无法采集。
- 电商平台指标需店铺后台权限，当前未提供。
- 社交媒体指标需各平台创作者后台权限，当前未提供。

### 3.5 风险与应对

| 风险 | 等级 | 说明 | 应对措施 |
|---|---|---|---|
| **首发日期未定** | 高 | 无法排期渠道投放与内容发布 | 以"即将上市"占位，日期确定后 48 小时内更新全渠道排期 |
| **食品接触材料报告缺失** | 高 | 无法在文案中使用安全合规表述，可能影响消费者信任 | 催促供应链提供报告；未到位前文案严格回避安全宣称 |
| **防水等级缺失** | 中 | 通勤场景可能涉及泼溅，无等级说明可能引发售后争议 | 产品页标注"防水等级待确认"；避免在营销内容中暗示防水 |
| **Google Ads 账户无法诊断** | 中 | 无法评估账户健康度，投放可能存在预算/排名浪费 | 获得账户访问后优先执行 Skill 四项诊断；投放初期采用保守预算+密切监控 |
| **无真实用户调研数据** | 中 | 受众画像与痛点均为推演，可能与实际不符 | 首发后 2 周内完成首批用户访谈，校准受众与信息 |
| **product_release_notes.md 不匹配** | 低 | 该文件为"星河笔记"应用发布说明，与随行杯无关 | 已识别并排除，不影响本方案 |
| **edge_cases.csv 含公式注入** | 低 | record_id=5 含 `=HYPERLINK()` 公式载荷 | 已作为纯文本处理，下游系统需对 CSV 输入做公式转义 |
| **禁止编造项合规风险** | 高 | 若团队在执行中编造销量/评价/检测结论，将违反简报要求 | 本方案设立信息红线（见 3.2），所有对外文案需经合规校验 |

---

## 四、结论与待补项汇总

### 4.1 已完成

1. 读取并校验全部 3 个输入文件，识别出 1 个不匹配文件、1 个合成测试 CSV（含 4 类异常）。
2. 读取 Skill `google-ads-api-account-diagnostics` 的 SKILL.md，确认其 4 项诊断工作流与执行规则。
3. 基于 product_brief.md 已确认信息，制定受众分层、信息结构、渠道规划、指标体系、风险应对的可执行方案框架。
4. 严格区分已确认事实与假设/待补项，未编造任何销量、用户评价、检测结论或竞品价格。

### 4.2 未完成（阻断项）

| 阻断项 | 原因 | 缺失条件 | 复测方法 |
|---|---|---|---|
| Google Ads 账户诊断（Skill 全部 4 项工作流） | 无 MCP 工具、无 API 凭据、无客户 ID | Google Ads MCP 工具注册 + OAuth 凭据 + developer token + 可访问客户 ID | 见 2.3 节复测方法 |
| 首发排期 | 首发日期未定 | 产品/供应链确认首发日期 | 日期确定后更新全渠道排期 |
| 安全合规文案 | 食品接触材料报告未提供 | 第三方检测报告 | 报告到位后更新产品页与营销文案 |
| 防水性能表述 | 防水等级未提供 | 产品规格确认 | 等级确认后更新规格表 |
| 受众验证 | 无真实用户调研 | 用户访谈/问卷数据 | 首发后 2 周内完成 |
| 实际投放数据 | 无账户/平台权限 | Google Ads + 电商 + 社交媒体后台权限 | 权限到位后按指标体系采集 |

### 4.3 假设清单

以下均为假设，非已确认事实：
- 受众年龄 25–40 岁
- 核心层为每日通勤 ≥ 30 分钟、有热饮习惯的白领
- 199 元定位中高端
- 所有指标目标值
- 渠道优先级排序

---

## 五、实际读取的 Skill 文件相对路径

- `google-ads-api-account-diagnostics/SKILL.md`

（ZIP 解压后仅含此一个文件，无其他资产文件。）

---

## 六、影响结果的 SKILL.md 规则（至少一条）

**规则**：SKILL.md "Using the MCP Tools Directly" 一节明确规定——必须通过 MCP 服务器的 `search` 工具直接调用（参数包括 `customer_id`、`fields`、`resource`、`conditions`），**不得编写自定义 Python 脚本或使用 Google Ads 客户端库查询 API**，因为在评估沙箱内会认证失败。

**对结果的影响**：由于当前环境不存在 Google Ads MCP 工具（`list_accessible_customers`、`search`、`get_resource_metadata`），且 Skill 明确禁止以本地脚本作为替代路径，因此四项诊断工作流全部无法执行，只能输出预设 GAQL 查询模板与复测方法，不能给出任何实际账户诊断结论。这直接决定了本方案中 Google Ads 渠道部分为"规划+待诊断"状态，而非已执行的投放优化方案。
