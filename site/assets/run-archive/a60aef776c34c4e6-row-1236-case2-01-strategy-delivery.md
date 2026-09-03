# 智能随行杯新品上市可执行方案

> 交付物：strategy-delivery.md
> 生成日期：2026-08-26
> 输入文件：product_brief.md、product_release_notes.md
> 执行依据：data-manager-api-audience-ingestion/SKILL.md（含 references/create-audience.md、references/formatting.md）

---

## 一、执行摘要

本方案基于 `product_brief.md` 中已确认的产品信息，为智能随行杯（建议零售价 199 元，核心卖点：12 小时保温 / 280g 轻量化 / 可拆洗杯盖）制定从受众定义到渠道落地的上市营销方案。方案将 Google Data Manager API 的 Customer Match 受众入库流程作为付费精准触达的核心技术动作，并严格遵循该 Skill 的执行规范。

**关键结论：**
- 目标受众聚焦一二线城市通勤人群，可细分为三个可运营子群。
- 信息结构以"轻量通勤 + 长效保温 + 易清洁"为三层递进，避免使用未经验证的防水/食品接触材料宣称。
- 渠道动作中，Google Ads Customer Match 受众上传具备完整技术路径，但因目标账户类型未确认、缺少认证凭据与用户原始数据，**实际 API 调用处于阻断状态**，本方案仅交付可执行脚本框架与前置清单。
- 至少存在两项实质性约束/冲突（见第七节），均已给出取舍与缓解措施。

---

## 二、输入文件分析与冲突识别

### 2.1 product_brief.md（主输入，有效）

| 字段 | 内容 | 状态 |
|---|---|---|
| 目标用户 | 一二线城市通勤人群 | 已确认 |
| 核心卖点 | 12 小时保温、重量 280g、可拆洗杯盖 | 已确认 |
| 建议零售价 | 199 元 | 已确认 |
| 已确认素材 | 产品白底图、基础规格、品牌主色 #176B87 | 已确认 |
| 禁止编造 | 第三方检测结论、销量、用户评价、竞品价格 | 硬约束 |
| 首发日期 | 尚未确定 | 待补 |
| 防水等级 | 尚未提供 | 待补 |
| 食品接触材料报告 | 尚未提供 | 待补 |

### 2.2 product_release_notes.md（冲突输入）

该文件为**星河笔记 2.3** 的发布说明，内容涉及 Markdown 批量导入、标签筛选、快捷键面板等软件功能，与智能随行杯无任何产品关联。

**处理决策：** 该文件不能作为随行杯的产品信息来源。本方案不引用其中任何功能描述。若业务意图是将随行杯与星河笔记进行跨界联合推广，需另行提供联合方案简报——当前无此依据，故不做假设。

---

## 三、受众策略

### 3.1 受众分层

基于简报中"一二线城市通勤人群"的定义，结合可通过 Customer Match 运营的第一方数据维度，拆分为三个子受众：

| 子受众 | 定义维度 | 数据来源类型 | Customer Match 数据类型 |
|---|---|---|---|
| A. 保温杯现有用户 | 品牌已有购买/注册用户，邮箱或手机号留存 | 品牌 CRM | `composite_data.user_data`（contact info） |
| B. 通勤场景高意向 | 近期浏览过水杯/通勤用品品类的站点访客，需有用户标识授权 | 站点第一方数据 | `user_id_data` 或 `mobile_data` |
| C. 相似扩展（Lookalike） | 基于 A/B 种子人群在 Google Ads 中生成类似受众 | 平台生成 | 无需上传，基于已入库种子 |

### 3.2 受众入库技术路径（依据 SKILL.md）

Skill 名称：`data-manager-api-audience-ingestion`，分类：营销与增长（metadata 中 category 为 GoogleAds）。

**完整执行步骤（摘自 SKILL.md Implementation Workflow）：**

1. **前置条件**：认证与客户端安装需参考 `data-manager-api-setup` skill；若需新建受众，参考 `references/create-audience.md` 获取 `product_destination_id`。
2. **Step 1 — 确定目标账户类型**：`[CRITICAL]` 若数据发往何处不明确（Google Ads / Display & Video 360），**必须停止并澄清**，不得默认 Google Ads。
3. **Step 2 — 获取代码样例**：从官方仓库获取对应语言的 `ingest_audience_members` 样例。
4. **Step 3 — 迁移指南**（如适用）：从其他 Google API 迁移时需提取字段映射指南。
5. **Step 4 — 实现**：初始化 `IngestionServiceClient` → 构建 `Destination` → 格式化用户数据 → 构造请求 → 支持 `validate_only` → 发送请求并记录 `request_id` → 检查 `field_warnings` → 异步轮询 `retrieve_request_status`。

**当前阻断点：**
- 目标账户类型（Google Ads 还是 DV360）未确认 → 触发 SKILL.md `[CRITICAL]` 规则，无法继续生成具体请求代码。
- 缺少 `data-manager-api-setup` 所需的认证凭据（OAuth / 服务账号）。
- 缺少 `product_destination_id`（需先完成受众创建）。
- 缺少实际用户标识数据（邮箱/手机号/设备 ID）。

因此，本节以下内容为**可执行框架**，待阻断项解除后可直接落地。

### 3.3 受众入库脚本框架（Python，待凭据补齐后执行）

```python
# 依据 SKILL.md Step 2 样例结构 & references/formatting.md
# 前置：pip install google-ads-data-manager google-ads-data-manager-util
# 阻断项：account_type 未确认、product_destination_id 缺失、认证未配置

from google.ads import datamanager_v1
from google.ads.datamanager_util import Formatter
from google.ads.datamanager_util.format import Encoding

# ---- 待确认参数 ----
ACCOUNT_TYPE = None          # "GOOGLE_ADS" 或 "DISPLAY_VIDEO_360" —— [CRITICAL] 必须澄清
PRODUCT_DESTINATION_ID = None  # 数字字符串，非资源名；需先创建受众获取
OPERATING_ACCOUNT_ID = None  # 接收数据的目标账户
LOGIN_ACCOUNT_ID = None      # 如使用经理账户/数据伙伴账户认证

def build_destination():
    """SKILL.md Step 4: Define Destinations"""
    destination = datamanager_v1.Destination()
    destination.product_destination_id = PRODUCT_DESTINATION_ID
    destination.operating_account.account_type = ACCOUNT_TYPE
    destination.operating_account.account_id = OPERATING_ACCOUNT_ID
    if LOGIN_ACCOUNT_ID:
        destination.login_account.account_type = ACCOUNT_TYPE
        destination.login_account.account_id = LOGIN_ACCOUNT_ID
    return destination

def format_email(email: str) -> str:
    """references/formatting.md: 使用 utility library 规范化并哈希"""
    formatter = Formatter()
    return formatter.process_email_address(email, Encoding.HEX)

def ingest_members(client, destination, user_emails):
    """SKILL.md Step 4: Construct Payload & Send Request"""
    user_identifiers = []
    for email in user_emails:
        uid = datamanager_v1.UserIdentifier()
        uid.email_address = format_email(email)  # 字段名必须是 email_address，非 hashed_email
        user_identifiers.append(uid)

    user_data = datamanager_v1.UserData()
    user_data.user_identifiers = user_identifiers

    composite = datamanager_v1.CompositeData()
    composite.user_data = user_data

    request = datamanager_v1.IngestAudienceMembersRequest()
    request.destination = destination
    request.composite_data = composite
    request.encoding = datamanager_v1.Encoding.HEX  # 发送哈希标识时必须设置
    request.terms_of_service = True  # Customer Match 上传必填：用户已接受政策
    request.consent.ad_user_data = datamanager_v1.ConsentStatus.CONSENT_GRANTED
    request.consent.ad_personalization = datamanager_v1.ConsentStatus.CONSENT_GRANTED
    # request.validate_only = True  # 首次运行建议开启，仅校验不实际写入

    response = client.ingest_audience_members(request=request)
    return response.request_id  # 记录用于后续诊断

def check_status(client, request_id):
    """SKILL.md: 异步处理，至少 30 分钟后轮询 retrieve_request_status"""
    status_request = datamanager_v1.RetrieveRequestStatusRequest(
        request_id=request_id
    )
    return client.retrieve_request_status(request=status_request)
```

> **注意**：以上脚本中 `ConsentStatus` 枚举值必须使用 `CONSENT_GRANTED` / `CONSENT_DENIED`，不可使用 `GRANTED` / `DENIED`（SKILL.md Critical Gotchas）。`validate_only=true` 时不可调用 `retrieve_request_status`。

---

## 四、信息结构

### 4.1 核心信息层级

| 层级 | 信息 | 依据 | 风险提示 |
|---|---|---|---|
| L1 主标题 | "280g 轻量随行，12 小时长效保温" | 简报已确认卖点 | 安全 |
| L2 支撑点 | 可拆洗杯盖，清洁无死角 | 简报已确认卖点 | 安全 |
| L3 价格锚点 | 建议零售价 199 元 | 简报已确认 | 安全，标注"建议零售价" |
| L4 视觉规范 | 品牌主色 #176B87，产品白底图 | 简报已确认素材 | 安全 |

### 4.2 禁止使用的信息

以下内容因简报明确禁止编造或尚未提供，**不得出现在任何对外素材中**：
- 防水等级相关宣称（待补）
- 食品接触材料安全性宣称（待补第三方报告）
- 任何销量数据、用户评价、竞品价格对比
- 第三方检测结论（如"经 XX 机构检测"）

### 4.3 结论与假设分离

- **结论（已确认）**：产品三大卖点、价格、素材、目标人群。
- **假设（需验证）**：通勤人群对"轻量化"的敏感度高于"保温时长"——此为策略假设，非用户调研结论，需通过 A/B 测试验证。
- **待补项**：首发日期、防水等级、食品接触材料报告、目标账户类型、认证凭据、第一方用户数据。

---

## 五、渠道动作

### 5.1 渠道矩阵

| 渠道 | 动作 | 依赖 | 可执行性 |
|---|---|---|---|
| Google Ads Search | 基于 Customer Match 受众做搜索再营销 + 类似受众扩展 | 受众入库完成（见 3.2） | 阻断中（凭据/账户类型） |
| Google Ads Display / DV360 | 通勤场景上下文定向 + 第一方受众叠加 | 目标账户类型确认后决定 | 阻断中 |
| 品牌自有渠道（官网/公众号/小程序） | 首发预告、产品详情页、素材投放 | 首发日期确认 | 部分可执行（素材已就绪） |
| 电商平台（如有） | 商品上架 + 详情页 | 平台入驻状态未提供 | 待确认 |

### 5.2 Google Ads Customer Match 上线检查清单

依据 SKILL.md，实际执行前必须逐项确认：

- [ ] **目标账户类型已确认**（Google Ads / DV360）—— `[CRITICAL]` 阻断项
- [ ] `data-manager-api-setup` 认证已完成，客户端库已安装
- [ ] 受众已创建，`product_destination_id` 已获取（数字字符串）
- [ ] 第一方用户数据已获取，且用户已授予数据使用同意（`ConsentStatus.CONSENT_GRANTED`）
- [ ] `terms_of_service` 已接受
- [ ] 用户标识已通过 utility library 规范化并哈希（`Encoding.HEX` 或 `BASE64`）
- [ ] 首次运行使用 `validate_only=true` 校验 schema
- [ ] 正式发送后记录 `request_id`，至少 30 分钟后轮询 `retrieve_request_status`
- [ ] 检查 `field_warnings`、`upload_match_rate_range`、`error_counts`

---

## 六、指标体系

### 6.1 营销漏斗指标

| 阶段 | 指标 | 数据来源 | 备注 |
|---|---|---|---|
| 受众入库 | 上传记录数、匹配率区间（`upload_match_rate_range`） | Data Manager API 诊断 | Skill 明确提供此字段 |
| 曝光 | 展示量、频次 | Google Ads / DV360 | 待账户确认 |
| 互动 | 点击率（CTR）、互动率 | 广告平台 | — |
| 转化 | 站点访客数、加购数、下单数 | 品牌自有助手 / GA4 | 需转化跟踪配置 |
| 效率 | 获客成本（CPA）、广告支出回报率（ROAS） | 综合计算 | 不预设目标值，待首发后基线 |

### 6.2 不预设的指标

- 不预设销量目标（简报禁止编造销量）。
- 不预设用户满意度/NPS（无用户反馈数据）。
- 所有数值目标在首发后两周内基于实际数据设定基线。

---

## 七、约束与冲突（至少两项）

### 约束/冲突一：输入文件产品不一致

**现象**：`product_brief.md` 为智能随行杯（硬件），`product_release_notes.md` 为星河笔记 2.3（软件），两者无产品关联。

**影响**：无法将 release notes 中的功能作为随行杯的卖点或补充信息。若强行关联，将构成信息编造。

**取舍**：以 `product_brief.md` 为唯一产品信息来源，`product_release_notes.md` 仅作为"已读取但不适用"的输入记录。若业务方意图为联合推广，需补充联合简报。

**缓解**：在方案中明确标注该冲突，避免下游执行方误用。

### 约束/冲突二：Skill 目标账户类型未确认触发 [CRITICAL] 阻断

**现象**：SKILL.md Step 1 明确标注 `[CRITICAL]`——若数据发往 Google Ads 还是 DV360 不明确，必须停止澄清，不得默认 Google Ads。本任务未提供目标账户类型。

**影响**：无法生成具体的 Destination 配置和完整可运行脚本，Customer Match 受众上传无法实际执行。

**取舍**：不假设账户类型，不编造 `product_destination_id`，交付脚本框架 + 前置检查清单，待账户类型确认后可直接填充参数运行。

**缓解**：在 3.3 节脚本中将 `ACCOUNT_TYPE` 设为 `None` 并标注为阻断项；在 5.2 节检查清单中将其列为第一项。

### 约束/冲突三（补充）：合规同意与数据缺失

**现象**：Customer Match 上传要求 `terms_of_service=true` 且 `ConsentStatus` 为 `CONSENT_GRANTED`，但本任务未提供任何第一方用户数据，也无法确认用户同意状态。

**影响**：即使凭据和账户类型齐备，无合法授权的用户数据也不能上传。

**取舍**：方案中明确要求数据来源必须为品牌自有且已获授权的 CRM 数据，不使用任何第三方数据或未授权数据。

---

## 八、关键取舍、依赖与风险

### 8.1 关键取舍

| 取舍点 | 选择 | 理由 |
|---|---|---|
| 信息深度 vs 合规安全 | 优先合规安全，缺失信息标注为待补而非推测 | 简报明确禁止编造第三方检测/销量/评价 |
| 渠道广度 vs 执行确定性 | 聚焦 Google Customer Match + 自有渠道，不铺未确认平台 | 电商平台入驻状态未提供 |
| 脚本完整度 vs 不编造凭据 | 交付框架而非可运行脚本 | 账户类型/凭据/数据均缺失，强行生成将含虚假参数 |
| 首发节奏 | 不设定具体日期，以"首发日期确认后 T-14 启动预热"为相对时间线 | 首发日期尚未确定 |

### 8.2 依赖项

1. **产品侧**：防水等级、食品接触材料报告（影响信息结构和合规宣称）。
2. **技术侧**：`data-manager-api-setup` 认证配置、`product_destination_id`、目标账户类型确认。
3. **数据侧**：品牌第一方用户数据（邮箱/手机号）及用户授权同意。
4. **业务侧**：首发日期确认、电商平台入驻状态。

### 8.3 风险

| 风险 | 概率 | 影响 | 缓解 |
|---|---|---|---|
| 食品接触材料报告延迟导致上市合规风险 | 中 | 高 | 上市前必须取得报告，否则不得使用相关宣称；以已确认卖点先行 |
| Customer Match 匹配率过低（种子人群质量差） | 中 | 中 | 上传后检查 `upload_match_rate_range`，低于预期时扩充种子数据源 |
| 异步处理状态未及时检查导致问题滞后 | 中 | 中 | 严格执行 SKILL.md 要求：发送后至少 30 分钟轮询 `retrieve_request_status` |
| `address` 字段不完整导致请求失败 | 低 | 中 | 仅在 `postal_code`/`family_name`/`given_name`/`region_code` 全部齐全时设置 `address`（SKILL.md Critical Gotchas） |
| 首发日期不确定导致渠道排期空转 | 高 | 低 | 采用相对时间线（T-14 / T-7 / T-Day），日期确认后自动映射 |

---

## 九、待补项与阻断说明

### 9.1 阻断项（不解决则无法完成实际执行）

| 编号 | 阻断项 | 来源 | 复测方法 |
|---|---|---|---|
| B1 | 目标账户类型未确认（Google Ads / DV360） | SKILL.md `[CRITICAL]` 规则 | 确认后填入 `ACCOUNT_TYPE`，运行 `validate_only=true` 校验 |
| B2 | 缺少 Data Manager API 认证凭据 | SKILL.md Prerequisites | 完成 `data-manager-api-setup` 后，运行客户端初始化测试 |
| B3 | 缺少 `product_destination_id` | SKILL.md Step 1 / create-audience.md | 完成受众创建后获取数字字符串 ID |
| B4 | 缺少第一方用户数据及授权 | SKILL.md terms_of_service / ConsentStatus | 获取 CRM 导出并确认用户同意后，运行格式化 + 校验 |

### 9.2 待补项（不阻断方案交付，但影响执行质量）

- 首发日期
- 防水等级
- 食品接触材料报告
- 电商平台入驻状态
- 星河笔记 2.3 是否为联合推广对象（需业务确认）

---

## 十、附录：Skill 执行依据

### 10.1 实际读取的 Skill 文件相对路径

| 相对路径 | 用途 |
|---|---|
| `data-manager-api-audience-ingestion/SKILL.md` | 主执行流程、Critical Gotchas、错误处理 |
| `data-manager-api-audience-ingestion/references/create-audience.md` | 受众创建、`product_destination_id` 获取、headers 配置 |
| `data-manager-api-audience-ingestion/references/formatting.md` | 用户数据规范化与哈希、utility library 使用 |

### 10.2 确实影响结果的 SKILL.md 规则

**规则：Step 1 — Determine Destination Account Type `[CRITICAL]`**

> "If it's not clear where the data is being sent (e.g., Google Ads, Display & Video 360, etc.), STOP and CLARIFY with the user BEFORE generating any code. Do not assume Google Ads by default."

**影响**：本任务未提供目标账户类型。若忽略此规则默认 Google Ads，将生成可能指向错误平台的 Destination 配置和请求代码，导致实际调用失败或数据发往错误账户。因此本方案将实际 API 执行判定为阻断状态，仅交付参数化的脚本框架和前置检查清单，而非编造账户 ID 和 destination ID 的"可运行"脚本。这一规则直接决定了交付物的形态（框架 + 清单 vs 完整可执行脚本）。

**其他被遵循的关键规则：**
- `terms_of_service` 为 Customer Match 上传必填字段（已在脚本中体现）。
- `product_destination_id` 必须为数字字符串，非资源名（已在注释中标注）。
- `ConsentStatus` 枚举值为 `CONSENT_GRANTED` / `CONSENT_DENIED`，非 `GRANTED` / `DENIED`（已在脚本中体现）。
- `UserIdentifier` 字段名为 `email_address` / `phone_number`，非 `hashed_email` / `hashed_phone_number`（已在脚本中体现）。
- 发送哈希标识时必须设置 `encoding` 为 `HEX` 或 `BASE64`（已在脚本中体现）。
- 异步处理：发送后至少 30 分钟轮询 `retrieve_request_status`（已在检查清单和指标中体现）。
- `validate_only=true` 时不可调用 `retrieve_request_status`（已在脚本注释中标注）。
- `address` 字段仅在全部子字段齐全时设置（已在风险表中体现）。

---

*本方案中所有未标注"已确认"的数据均为策略假设或待补项，不构成对产品性能、市场表现或用户反馈的事实陈述。*
