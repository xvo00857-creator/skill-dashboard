# 智能随行杯上市可执行方案（最小可验证版本）

> 生成日期：2026-08-26
> 依据文件：`product_brief.md`、`product_release_notes.md`（后者经判定与本产品无关，详见第 1 节）
> 执行技能：`data-manager-api-audience-ingestion`（分类：营销与增长 / Google Ads 受众入库）
> 文档性质：结论与假设分开；所有外部数据均标注为待补项，不虚构销量、用户反馈、第三方检测结论或竞品价格。

---

## 1. 输入依据与适用性判定

### 1.1 已确认输入（来自 product_brief.md）

| 项目 | 内容 |
|---|---|
| 产品 | 智能随行杯 |
| 目标用户 | 一二线城市通勤人群 |
| 核心卖点 | 12 小时保温、重量 280g、可拆洗杯盖 |
| 建议零售价 | 199 元 |
| 已确认素材 | 产品白底图、基础规格、品牌主色 #176B87 |
| 禁止编造 | 第三方检测结论、销量、用户评价、竞品价格 |
| 交付要求 | 中文；结论与假设分开；外部数据列为待补项 |

### 1.2 不完整信息（来自 product_brief.md）

- 首发日期尚未确定。
- 防水等级与食品接触材料报告尚未提供。

### 1.3 product_release_notes.md 适用性判定

该文件内容为「星河笔记 2.3」发布说明（批量导入 Markdown、标签筛选、快捷键面板、macOS 13 / Windows 11 兼容性等），与智能随行杯无任何产品、功能或受众关联。**判定为不适用输入，不纳入本方案。** 若后续确认该文件为误传或需关联，请补充说明。

---

## 2. 受众定义

### 2.1 核心受众（简报已确认）

- **人群**：一二线城市通勤人群。
- **场景推断（假设，非数据）**：工作日通勤途中携带热饮，对保温时长、轻便性和清洁便利性有需求。
- **价格敏感度（假设）**：199 元处于中端价位，需通过材质与功能感知支撑溢价。

> 以上场景推断均为假设，未经用户调研验证，标注为「假设」。

### 2.2 受众分层（用于 Customer Match 上传，按 Skill 数据类型规范）

依据 `data-manager-api-audience-ingestion` SKILL.md，Customer Match 受众支持三种数据类型：

| 数据类型 | 字段 | 本方案用途 | 当前状态 |
|---|---|---|---|
| `composite_data.user_data` | 邮箱、电话、地址等联系方式 | 已有会员/留资用户再营销 | **阻断：无实际用户数据** |
| `mobile_data` | 移动设备 ID | App 端或 SDK 采集的设备用户 | **阻断：无设备 ID 数据** |
| `user_id_data` | 用户 ID | 自有平台登录用户 | **阻断：无用户 ID 体系说明** |

### 2.3 受众数据合规前提（Skill 强制规则）

- 上传 Customer Match 受众时，`IngestAudienceMembersRequest` 必须携带 `terms_of_service` 字段，表明用户已接受相关政策。
- `ConsentStatus` 枚举值只能使用 `CONSENT_GRANTED` 或 `CONSENT_DENIED`，**不得**使用 `GRANTED` / `DENIED`。
- 哈希标识符（邮箱、电话）必须在请求中设置 `encoding` 字段为 `HEX` 或 `BASE64`。
- `UserIdentifier` 字段名为 `email_address` 和 `phone_number`，**不得**使用旧 Google Ads API 的 `hashed_email` / `hashed_phone_number`。
- 仅当 `address` 的全部必填字段（`postal_code`、`family_name`、`given_name`、`region_code`）齐全时才可设置，否则请求将失败。

---

## 3. 信息结构

### 3.1 核心信息层级（基于已确认卖点）

| 层级 | 信息 | 依据 |
|---|---|---|
| 主信息 | 12 小时保温，通勤一路温热 | 简报已确认卖点 |
| 辅助信息 1 | 仅 280g，轻量随行无负担 | 简报已确认卖点 |
| 辅助信息 2 | 可拆洗杯盖，清洁无死角 | 简报已确认卖点 |
| 价格锚点 | 建议零售价 199 元 | 简报已确认 |
| 视觉规范 | 品牌主色 #176B87，产品白底图可用 | 简报已确认素材 |

### 3.2 待补信息（不得编造）

| 待补项 | 影响 | 阻断程度 |
|---|---|---|
| 首发日期 | 无法制定精确排期 | 中（可先做前置准备） |
| 防水等级 | 影响使用场景描述（如雨天、户外） | 中 |
| 食品接触材料报告 | 影响安全类卖点表述 | 高（无报告不得宣称食品级） |
| 第三方检测结论 | 禁止编造，需真实报告 | 高 |
| 销量 / 用户评价 | 禁止编造 | 高（上市后才可获取） |
| 竞品价格 | 禁止编造 | 中（可做公开信息检索，但需标注来源） |

---

## 4. 渠道动作

### 4.1 渠道矩阵（最小可验证版本）

| 渠道 | 动作 | 依赖 | 当前可执行性 |
|---|---|---|---|
| 品牌自有内容（社媒图文） | 基于白底图 + #176B87 主色发布 3 条卖点图文 | 素材已确认 | **可执行** |
| 私域 / 会员触达 | 向已有会员发送新品预告 | 需会员数据 | 部分可执行（取决于是否有会员列表） |
| Google Ads Customer Match | 上传受众列表进行再营销 / 相似受众拓展 | 见 4.2 节 | **阻断** |
| 电商平台上架 | 商品详情页搭建 | 需首发日期、防水等级、材料报告 | 部分可执行（先搭建框架） |
| KOL / 测评 | 寄送样品获取真实反馈 | 需样品 + 首发日期 | 待补 |

### 4.2 Google Ads Customer Match 受众入库（按 Skill 工作流）

以下严格遵循 `data-manager-api-audience-ingestion` SKILL.md 的 Implementation Workflow。

#### 步骤 1：确定目标账户类型 [CRITICAL 阻断]

> **SKILL.md 原文规则**：「If it's not clear where the data is being sent (e.g., Google Ads, Display & Video 360, etc.), STOP and CLARIFY with the user BEFORE generating any code. Do not assume Google Ads by default.」

当前输入未指定数据发往 **Google Ads** 还是 **Display & Video 360 (DV360)**。按 Skill 强制规则，**不得默认 Google Ads**，因此无法生成具体入库代码。需补充以下信息：

- [ ] `account_type`：`GOOGLE_ADS` 或 `DISPLAY_VIDEO`
- [ ] 目标账户 ID（`operating_account`）
- [ ] 若使用经理账户 / 数据合作伙伴账户认证，需提供 `login_account`
- [ ] 若通过合作伙伴链接访问，需提供 `linked_account`

#### 步骤 2：创建受众（获取 product_destination_id）[阻断]

- 需使用 `UserListServiceClient`（**不是** `UserListsClient`）创建 Customer Match 受众。
- 创建后获得 `product_destination_id`，该值**必须是数字字符串**，不是资源名称。
- 当前无账户访问权限，无法执行此步骤。

#### 步骤 3：检索代码示例 [待账户类型确认后执行]

Skill 提供五种语言示例：Python / Java / PHP / Node / .NET。待账户类型确认后，按所选语言检索对应示例。

#### 步骤 4：数据格式化与哈希 [待用户数据就绪后执行]

- 使用 `google.ads.datamanager_util.Formatter` 对邮箱、电话、地址进行标准化与哈希。
- Python 示例（来自 Skill 参考文件 formatting.md）：
  ```python
  from google.ads.datamanager_util import Formatter
  from google.ads.datamanager_util.format import Encoding
  formatter = Formatter()
  processed_email = formatter.process_email_address(email, Encoding.HEX)
  ```
- 当前无任何用户标识符数据，此步骤无法执行。

#### 步骤 5：构造并发送请求 [阻断]

- 新增受众：`IngestAudienceMembersRequest` → `ingest_audience_members`
- 移除指定成员：`RemoveAudienceMembersRequest` → `remove_audience_members`
- 清空全部：`RemoveAllAudienceMembersRequest` → `remove_all_audience_members`
- 支持 `validate_only=true` 进行模式校验（不实际写入），**但设置 `validate_only=true` 时不得调用诊断端点 `retrieve_request_status`**。

#### 步骤 6：异步状态轮询 [阻断]

- 请求返回 HTTP 200 + `request_id` 仅表示 payload 已接收，**不代表处理成功**。
- 需在发送后**至少 30 分钟**，使用指数退避策略调用 `client.retrieve_request_status` 轮询。
- 检查 `request_status_per_destination` 中的状态（`SUCCESS` / `PARTIAL_SUCCESS` / `FAILED`）。
- 检查 `field_warnings`、`error_info.error_counts`、`warning_info.warning_counts`。
- 检查 `upload_match_rate_range`（匹配率区间）。

---

## 5. 指标

### 5.1 可设定指标（不虚构数值）

| 指标类别 | 具体指标 | 数据来源 | 当前状态 |
|---|---|---|---|
| 品牌曝光 | 社媒图文曝光量、互动率 | 各平台后台 | 待上线后采集 |
| 受众入库 | 上传记录数、成功匹配数、匹配率区间 | Data Manager API 诊断端点 | **阻断：无 API 访问** |
| 转化 | 电商详情页访问量、加购率、下单转化率 | 电商平台后台 | 待上架后采集 |
| 私域 | 会员打开率、点击率 | 私域工具后台 | 取决于会员体系 |

### 5.2 禁止项

- 不得预设销量目标（简报明确禁止编造销量）。
- 不得引用用户评价（无真实用户反馈）。
- 不得声称第三方检测通过（无报告）。

---

## 6. 风险

### 6.1 信息缺失风险

| 风险 | 影响 | 缓解措施 |
|---|---|---|
| 首发日期未定 | 无法制定精确排期和渠道协调 | 先完成素材准备和框架搭建，日期确定后 48 小时内排出精确时间表 |
| 防水等级缺失 | 场景描述受限，不能宣称防水 | 文案中避免防水相关表述，待报告到位后补充 |
| 食品接触材料报告缺失 | 不能宣称「食品级安全」 | 文案中仅描述「可拆洗杯盖」等已确认功能，不涉及材质安全声明 |

### 6.2 API 执行风险（来自 Skill Critical Gotchas）

| 风险 | 说明 | 规避 |
|---|---|---|
| 账户类型未确认 | Skill 强制要求先澄清，不得默认 | 必须先获取 `account_type` |
| `terms_of_service` 遗漏 | Customer Match 上传必填字段 | 请求构造时检查该字段非空 |
| `encoding` 未设置 | 哈希标识符必须指定 HEX 或 BASE64 | 使用 utility library 自动处理 |
| `address` 字段不完整 | 缺少任一必填子字段将导致请求失败 | 仅在四字段齐全时设置 address |
| 误判请求成功 | HTTP 200 仅表示接收，非处理成功 | 必须 30 分钟后轮询状态 |
| `validate_only` 后调用诊断 | Skill 明确禁止 | 校验模式下跳过状态查询 |
| `product_destination_id` 格式错误 | 必须为数字字符串，非资源名称 | 创建受众后校验格式 |

### 6.3 合规风险

- Customer Match 上传需用户已同意数据使用条款（`terms_of_service`）。
- 需确保受众数据来源合法，符合个人信息保护要求。
- 不得上传未授权的第三方数据。

---

## 7. 最小可验证版本：关键步骤与验收标准

### 7.1 关键步骤（按优先级）

| 序号 | 步骤 | 产出 | 依赖 |
|---|---|---|---|
| 1 | 确认首发日期、防水等级、食品接触材料报告 | 完整产品规格表 | 业务方提供 |
| 2 | 基于已确认素材制作 3 条社媒卖点图文 | 图文内容稿 | 白底图 + #176B87（已具备） |
| 3 | 确认 Google Ads / DV360 账户类型及账户 ID | `account_type` + 账户 ID | 业务方提供 |
| 4 | 获取 Data Manager API 认证凭据（参考 `data-manager-api-setup` skill） | 可用 service account / OAuth | 管理员授权 |
| 5 | 创建 Customer Match 受众，获取 `product_destination_id` | 数字字符串 ID | 步骤 3、4 完成 |
| 6 | 准备并格式化受众数据（邮箱/电话哈希） | 合规的受众列表文件 | 会员数据 + 合规授权 |
| 7 | 使用 `validate_only=true` 发送入库请求做模式校验 | 校验通过 / 报错信息 | 步骤 5、6 完成 |
| 8 | 正式发送入库请求，记录 `request_id` | `request_id` | 步骤 7 通过 |
| 9 | 30 分钟后轮询请求状态，检查匹配率与警告 | 状态报告 | 步骤 8 完成 |
| 10 | 基于受众投放再营销广告 | 广告活动 | 步骤 9 状态为 SUCCESS / PARTIAL_SUCCESS |

### 7.2 验收标准

| 阶段 | 验收标准 |
|---|---|
| 内容准备 | 3 条图文均使用 #176B87 主色和白底图，仅包含已确认卖点，无禁止编造内容 |
| API 前置 | `account_type`、账户 ID、凭据、`product_destination_id` 全部就绪且格式正确 |
| 数据校验 | `validate_only=true` 请求返回无错误，`field_warnings` 为空或仅含非关键字段警告 |
| 入库执行 | 正式请求返回 `request_id`，30 分钟后状态为 `SUCCESS` 或 `PARTIAL_SUCCESS` |
| 匹配质量 | `upload_match_rate_range` 处于可接受区间（具体阈值待业务方确认，不预设） |
| 整体方案 | 文档中所有数据均有来源或标注为待补，无虚构销量、用户反馈、检测结论 |

---

## 8. 阻断项汇总与复测方法

### 8.1 当前无法完成的事项

1. **Google Ads / DV360 受众入库实际执行** — 缺少 `account_type`、账户 ID、API 凭据、`product_destination_id` 和实际受众数据。
2. **精确上市排期** — 首发日期未定。
3. **安全类卖点文案** — 防水等级和食品接触材料报告缺失。
4. **销量与效果预测** — 简报禁止编造，需上市后真实数据。

### 8.2 复测方法

当以下条件补齐后，可重新执行完整方案：

- [ ] 提供 `account_type`（`GOOGLE_ADS` 或 `DISPLAY_VIDEO`）及目标账户 ID。
- [ ] 提供 Data Manager API 认证凭据（service account JSON 或 OAuth token）。
- [ ] 提供受众数据文件（邮箱 / 电话 / 设备 ID，含用户授权证明）。
- [ ] 确认首发日期、防水等级、食品接触材料报告。
- [ ] 复测时先以 `validate_only=true` 运行，确认无错误后再正式发送。

---

## 附录 A：实际读取的 Skill 文件相对路径

| 文件 | 相对路径 |
|---|---|
| 技能主文件 | `data-manager-api-audience-ingestion/SKILL.md` |
| 受众创建参考 | `data-manager-api-audience-ingestion/references/create-audience.md` |
| 数据格式化参考 | `data-manager-api-audience-ingestion/references/formatting.md` |

## 附录 B：确实影响结果的 SKILL.md 规则

> **规则原文**：「Determine Destination Account Type: [CRITICAL] If it's not clear where the data is being sent (e.g., Google Ads, Display & Video 360, etc.), STOP and CLARIFY with the user BEFORE generating any code. Do not assume Google Ads by default.」

**影响**：由于输入未指定目标账户类型，按此强制规则不得生成任何 API 入库代码，也不得默认使用 Google Ads。因此本方案中 Customer Match 受众入库部分全部标注为阻断，仅提供工作流规范和待补条件，未伪造代码执行结果。这是本方案与"直接写一段 Google Ads 入库脚本"的根本区别。

此外，以下规则也实质性影响了方案结构：
- `terms_of_service` 为 Customer Match 上传必填项 → 纳入合规前提。
- 请求为异步处理，HTTP 200 不等于成功 → 纳入指标与验收标准（必须 30 分钟后轮询）。
- `validate_only=true` 时不得调用诊断端点 → 纳入风险与验收标准。
- `product_destination_id` 必须为数字字符串 → 纳入格式校验标准。
