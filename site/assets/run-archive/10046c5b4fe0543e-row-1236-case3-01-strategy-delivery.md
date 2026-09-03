# 智能随行杯新品上市可执行方案（strategy-delivery）

> 生成时间：2026-08-26
> 依据 Skill：`data-manager-api-audience-ingestion`（metadata version 1.1, category: GoogleAds）
> 输入文件：`product_brief.md`、`product_release_notes.md`、`edge_cases.csv`
> 原则：结论与假设分开；不虚构销量、用户反馈、第三方检测结论或竞品价格；外部数据列为待补项。

---

## 一、执行摘要

本方案基于 `product_brief.md` 中已确认的产品信息，为智能随行杯制定上市受众、信息结构、渠道动作、指标与风险框架。受 Skill 执行条件与输入完整性限制，**实际可完成部分为策略规划与数据治理方案**；**Google Data Manager API 受众接入的真实调用因缺少凭据与目标账户而被阻断**，已在第八节给出证据、降级方案与复测方法。

---

## 二、输入文件核验与异常识别

### 2.1 文件清单与读取状态

| 文件 | 读取状态 | 与本任务相关性 | 说明 |
|---|---|---|---|
| `product_brief.md` | 已完整读取 | 高 | 智能随行杯新品简报，本方案主依据 |
| `product_release_notes.md` | 已完整读取 | **低/不匹配** | 内容为"星河笔记 2.3"笔记软件发布说明，与随行杯硬件无关 |
| `edge_cases.csv` | 已完整读取 | 中 | 边界测试数据，用于验证受众数据清洗规则 |

### 2.2 输入异常识别

#### 异常 1：产品错配（严重）

- **证据**：`product_release_notes.md` 标题为"星河笔记 2.3 发布说明"，功能为批量导入 Markdown、标签筛选、快捷键面板，平台兼容性为 macOS 13 / Windows 11。这与 `product_brief.md` 中的智能随行杯（12 小时保温、280g、可拆洗杯盖、199 元）属于完全不同的产品品类。
- **影响**：该文件不能作为随行杯上市方案的输入依据。
- **处理**：本方案不引用 `product_release_notes.md` 的任何功能或兼容性信息；将其列为**疑似错附文件**，待用户确认是否应替换为随行杯的发布说明。

#### 异常 2：`edge_cases.csv` 数据质量问题

逐行分析（共 6 行数据，含表头）：

| record_id | status | value | notes | 问题类型 | 处理方式 |
|---|---|---|---|---|---|
| 1 | ok | 120 | 正常记录 | 无 | 保留 |
| 2 | ok | 120 | 重复记录 | **重复行**（record_id=2 出现两次，内容完全一致） | 去重，仅保留 1 条 |
| 2 | ok | 120 | 重复记录 | 同上 | 删除 |
| 3 | （空） | （空） | - | **缺失值**（status 和 value 均为空） | 标记为无效记录，排除；若 value 为受众标识符则不可哈希 |
| 4 | error | -999 | 异常负值 | **异常值**（负值，若为数值型字段则不合理） | 排除；记录为数据质量告警 |
| 5 | ok | `=HYPERLINK("https://example.invalid","do not execute")` | 公式注入测试文本 | **CSV 公式注入**（以 `=` 开头的公式） | 视为不安全输入，必须转义或纯文本化；禁止直接传入 API 或电子表格 |

**数据清洗规则（适用于后续受众数据接入）**：
1. 按 `record_id` 去重，保留首次出现。
2. `status` 或核心标识符为空的记录直接排除。
3. 数值字段出现负值或超出合理范围时排除并告警。
4. 任何以 `=`、`+`、`-`、`@` 开头的文本字段必须前置单引号转义，防止 CSV 公式注入；本案例中 record_id=5 的 value 字段应作为纯文本处理，不可执行。
5. 清洗后有效记录数：**2 条**（record_id 1、去重后的 2）；有效率 2/5 = 40%（按去重前 5 条唯一 record_id 计）。

---

## 三、受众定义

### 3.1 核心受众（基于简报已确认信息）

- **人群**：一二线城市通勤人群。
- **场景**：日常通勤（地铁/公交/自驾）、办公室全天使用、短途外出。
- **痛点假设**（标注为假设，非用户反馈）：
  - 通勤途中饮品温度不可控（假设）。
  - 杯盖清洗不便导致卫生顾虑（假设）。
  - 包内负重敏感，偏好轻量化（假设）。
- **人口学特征**：待补项（简报未提供年龄、性别、收入分布）。

### 3.2 受众数据接入准备（对照 Skill 要求）

Skill `data-manager-api-audience-ingestion` 定义了三类可接入数据类型：
- `composite_data.user_data`（联系方式：邮箱、电话、地址）
- `mobile_data`（设备 ID）
- `user_id_data`（用户 ID）

**当前状态**：无任何实际受众标识符数据（`edge_cases.csv` 为测试数据，非真实受众名单），因此**无法执行真实的受众接入**。

**待补项**：
- 受众数据源（CRM 导出 / 一方数据平台 / 线下收集）。
- 数据类型确认（联系方式 / 设备 ID / 用户 ID）。
- 用户同意状态（Consent）——Skill 要求 `ConsentStatus` 枚举值为 `CONSENT_GRANTED` 或 `CONSENT_DENIED`，不可使用 `GRANTED`/`DENIED`。
- 数据合规依据（个人信息保护法下的合法性基础）。

---

## 四、信息结构

### 4.1 核心信息层级

| 层级 | 内容 | 依据 |
|---|---|---|
| **主信息** | 12 小时保温 × 280g 轻量 × 可拆洗杯盖 | 简报已确认卖点 |
| **支撑信息** | 199 元建议零售价；品牌主色 #176B87 | 简报已确认 |
| **信任信息** | 食品接触材料报告、防水等级 | **待补**（简报明确"尚未提供"） |
| **社交证明** | 用户评价、销量数据 | **禁止编造**（简报明确禁止） |

### 4.2 信息使用规则

- 所有素材仅使用已确认的产品白底图、基础规格、品牌主色 #176B87。
- 涉及保温时长、重量等参数时，必须标注为"厂商标称值"，不得引申为第三方检测结论。
- 食品接触材料安全性、防水等级在报告到位前，**不得作为宣传点**。

---

## 五、渠道动作

### 5.1 渠道规划（基于受众假设，非实测数据）

| 渠道 | 动作 | 前置条件 | 状态 |
|---|---|---|---|
| 社交媒体图文（小红书/微博） | 通勤场景种草图文，突出轻量与保温 | 产品白底图 + 场景图（场景图待补） | 可规划，素材待补 |
| 电商详情页 | 规格参数 + 卖点结构化展示 | 食品接触材料报告、防水等级 | **部分阻断**（信任信息缺失） |
| 付费广告（搜索/信息流） | 定向一二线城市通勤兴趣人群 | 广告账户、预算、受众包 | **阻断**（无账户/预算/凭据） |
| Google Customer Match 受众接入 | 通过 Data Manager API 上传一方受众 | 见第八节 | **阻断** |

### 5.2 Google Data Manager API 受众接入（Skill 对应动作）

按 Skill 的 Implementation Workflow，完整执行需以下步骤，当前均无法实际完成：

1. **Prerequisites**：需完成认证与客户端库安装（依赖 `data-manager-api-setup` skill，未提供）。
2. **Step 1 — 确定目标账户类型**：Skill 标注为 **[CRITICAL]**，若不明确数据发往 Google Ads 还是 DV360，**必须停止并向用户澄清，不得默认 Google Ads**。当前未提供目标账户类型，因此此步骤即触发阻断。
3. **Step 2 — 获取代码示例**：需从 GitHub 获取对应语言示例，当前无网络执行环境且无目标语言指定。
4. **Step 3 — 迁移指南**：仅在从其他 Google API 重构时需要，当前不涉及。
5. **Step 4 — 实施**：需 `product_destination_id`（数字字符串，非资源名）、`operating_account` 配置、用户数据格式化与哈希、`terms_of_service` 字段（Customer Match 上传必填）、`validate_only` 支持、异步状态轮询。

---

## 六、指标体系

### 6.1 可定义指标（无需外部数据）

| 指标类别 | 指标 | 数据来源 | 当前可测性 |
|---|---|---|---|
| 曝光 | 图文阅读量、视频播放量 | 各平台后台 | 待渠道上线后可测 |
| 互动 | 点赞、收藏、评论、分享 | 各平台后台 | 待渠道上线后可测 |
| 转化 | 详情页点击率、加购率、下单率 | 电商平台后台 | 待商品上架后可测 |
| 受众接入 | 上传记录数、匹配率区间（`upload_match_rate_range`）、成功/失败计数 | Data Manager API diagnostics | **阻断**（无法调用 API） |

### 6.2 禁止虚构的指标

- 不得预估或虚构销量、GMV、ROI。
- 不得虚构用户好评率、NPS。
- 不得虚构竞品价格对比数据。

---

## 七、风险与缓解

| 风险 | 等级 | 说明 | 缓解措施 |
|---|---|---|---|
| 首发日期未定 | 中 | 简报明确"首发日期尚未确定"，渠道排期无法锁定 | 以"首发日前 14 天"为锚点倒排，日期确定后即填充 |
| 食品接触材料报告缺失 | 高 | 涉及食品安全合规，缺失则不能宣传材质安全性 | 报告到位前不使用相关卖点；将其列为上市 Gate |
| 防水等级缺失 | 中 | 影响使用场景描述（如"可水洗"） | 等级确认前仅描述"可拆洗杯盖"，不引申整机防水 |
| 输入文件错配 | 中 | `product_release_notes.md` 为另一产品 | 不引用其内容；请用户确认是否替换 |
| 受众数据合规 | 高 | Customer Match 需用户同意与 `terms_of_service` | 数据接入前完成 Consent 收集与法务审核 |
| CSV 公式注入 | 高 | `edge_cases.csv` record_id=5 含 `=HYPERLINK()` | 所有受众数据导入前执行公式注入检测与转义 |
| API 凭据缺失 | 高 | 无法执行真实受众接入 | 见第八节降级方案 |

---

## 八、Skill 执行情况：阻断项、降级方案与复测方法

### 8.1 阻断项（有证据）

| # | 阻断项 | 证据 | 影响 |
|---|---|---|---|
| 1 | 目标账户类型未指定 | Skill Step 1 [CRITICAL]："If it's not clear where the data is being sent... STOP and CLARIFY... Do not assume Google Ads by default." | 无法进入后续任何 API 实施步骤 |
| 2 | 缺少认证与客户端库 | Skill Prerequisites 要求参考 `data-manager-api-setup` skill，未提供 | 无法初始化 `IngestionServiceClient` |
| 3 | 缺少 `product_destination_id` | Skill Step 4 要求构建 Destination 对象，且该 ID 必须为数字字符串 | 无法构建请求 payload |
| 4 | 无真实受众标识符数据 | `edge_cases.csv` 为测试数据，非邮箱/电话/设备 ID | 无数据可接入 |
| 5 | 缺少用户同意（Consent）与 ToS 确认 | Skill Critical Gotchas：Customer Match 上传 `terms_of_service` 为必填；`ConsentStatus` 需明确 | 上传请求会被 API 拒绝 |
| 6 | 执行规则限制 | 用户要求"不得发起浏览器接管、登录授权或交互式选择" | 无法完成 OAuth 等交互式认证流程 |

### 8.2 降级方案

在阻断解除前，可执行以下不依赖外部 API 的降级动作：

1. **受众数据治理方案**：已在第二节完成 `edge_cases.csv` 的清洗规则定义，可复用于真实受众数据到达后的预处理。
2. **API 接入脚本框架（伪代码级，非可执行）**：基于 Skill 文档结构，预留接入脚本的字段映射与校验逻辑，待凭据到位后填充。
3. **`validate_only` 预验证规划**：Skill 支持 `validate_only=true` 进行 schema 校验而不实际写入；凭据到位后建议先以该模式跑通，再切换为真实上传。注意 Skill 明确：**`validate_only=true` 时不可调用 `retrieve_request_status` 诊断端点**。
4. **数据格式化规范**：参照 Skill `references/formatting.md`，要求使用 utility library（如 Python `google.ads.datamanager_util.Formatter`）对邮箱、电话、地址进行归一化与哈希；哈希后必须在请求中设置 `encoding` 为 `HEX` 或 `BASE64`。地址字段仅在 `postal_code`、`family_name`、`given_name`、`region_code` 全部齐全时才可设置，否则请求会失败。

### 8.3 复测方法

阻断项解除后，按以下顺序复测：

1. **认证复测**：运行客户端库初始化代码，确认能成功实例化 `IngestionServiceClient`。
2. **目标账户确认复测**：明确 `account_type`（`GOOGLE_ADS` 或 `DISPLAY_VIDEO`），构建 Destination 对象并确认 `product_destination_id` 为数字字符串。
3. **Schema 验证复测**：发送 `validate_only=true` 的 `IngestAudienceMembersRequest`，确认无字段级错误；检查 `field_warnings`。
4. **小批量真实上传复测**：以 ≤100 条已获 Consent 的测试数据上传，记录返回的 `request_id`。
5. **异步状态复测**：上传后至少等待 30 分钟，使用指数退避轮询 `client.retrieve_request_status`；检查 `request_status_per_destination` 中各目标的状态（`SUCCESS`/`PARTIAL_SUCCESS`/`FAILED`），以及 `record_count`、`data_type_counts`、`upload_match_rate_range`。
6. **数据质量复测**：将真实受众数据通过第二节的清洗规则跑一遍，确认重复率、缺失率、异常值率在可接受阈值内。

---

## 九、待补项清单

| # | 待补项 | 用途 | 责任方（假设） |
|---|---|---|---|
| 1 | 首发日期 | 渠道排期锚点 | 产品/市场 |
| 2 | 食品接触材料报告 | 信任信息与合规 | 产品/质量 |
| 3 | 防水等级 | 场景描述边界 | 产品 |
| 4 | 目标广告账户类型（Google Ads / DV360） | API 接入 Step 1 | 增长/投放 |
| 5 | `product_destination_id` | API 请求构建 | 增长/投放 |
| 6 | Google API 认证凭据与客户端库 | API 接入 | 工程/增长 |
| 7 | 真实受众标识符数据及 Consent 记录 | 受众接入 | CRM/增长 |
| 8 | 场景图素材（非白底图） | 社媒种草 | 设计 |
| 9 | 人口学受众细分数据 | 精准定向 | 市场研究 |
| 10 | 确认 `product_release_notes.md` 是否错附 | 输入完整性 | 用户 |

---

## 十、结论

1. **策略层面可完成**：基于 `product_brief.md` 已确认信息，已输出受众定义、信息结构、渠道动作框架、指标体系与风险清单，所有未确认信息均标注为假设或待补项，未虚构任何销量或用户反馈。
2. **输入层面存在异常**：`product_release_notes.md` 与本任务产品不匹配；`edge_cases.csv` 含重复、缺失、异常负值与公式注入四类问题，已给出清洗规则。
3. **Skill 执行层面被阻断**：`data-manager-api-audience-ingestion` 的真实 API 调用因缺少目标账户类型、凭据、`product_destination_id` 和真实受众数据而无法执行，已给出降级方案与六步复测方法。
4. **确实影响结果的 Skill 规则**：Skill Step 1 的 [CRITICAL] 规则——目标账户类型不明确时必须停止并澄清，不得默认 Google Ads——直接导致 API 接入动作在第一步即被阻断，是本方案无法完成真实受众接入的首要技术原因。此外，Skill 要求 Customer Match 上传必须携带 `terms_of_service`、哈希标识符必须设置 `encoding=HEX/BASE64`、`validate_only=true` 时禁止调用诊断端点等规则，均已纳入降级方案与复测方法。
