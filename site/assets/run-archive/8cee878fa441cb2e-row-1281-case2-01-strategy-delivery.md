# 智能随行杯新品上市可执行方案

> [SYSTEM: Using Google Ads API version: v25 (Resolved from release notes)]
>
> 本文档基于 `product_brief.md` 制定，严格遵守简报中"禁止编造第三方检测结论、销量、用户评价、竞品价格"的约束。所有量化目标均为假设性目标（标注为"目标/假设"），非实际数据。结论与假设分开陈述。

---

## 1. 执行摘要

本方案为"智能随行杯"（建议零售价 199 元）制定新品上市可执行方案，覆盖受众、信息结构、渠道动作、指标与风险。核心卖点为 12 小时保温、280g 轻量化、可拆洗杯盖，目标用户为一二线城市通勤人群。

**关键结论：**
- 以"通勤场景下的轻量保温体验"为核心信息主轴，三个卖点按"保温→轻量→可拆洗"层级展开。
- 渠道采用"搜索广告（Google Ads）+ 社交种草 + 电商站内 + 私域"四线并行，其中 Google Ads 渠道因缺少 API 凭据处于**阻断状态**，需凭据就绪后执行。
- 方案识别出 **4 项约束/冲突**：输入文件错配、合规数据缺失、首发日期未定、Google Ads 凭据缺口，均已给出应对与阻断说明。
- 所有外部数据（市场规模、竞品价格、用户反馈）均列为待补项，未做任何编造。

---

## 2. 输入核验与冲突识别

### 2.1 产品简报核验（product_brief.md）

| 项目 | 内容 | 状态 |
|---|---|---|
| 产品名称 | 智能随行杯 | 已确认 |
| 目标用户 | 一二线城市通勤人群 | 已确认 |
| 核心卖点 | 12 小时保温、重量 280g、可拆洗杯盖 | 已确认 |
| 建议零售价 | 199 元 | 已确认 |
| 已确认素材 | 产品白底图、基础规格、品牌主色 #176B87 | 已确认 |
| 首发日期 | 尚未确定 | **缺失** |
| 防水等级 | 尚未提供 | **缺失** |
| 食品接触材料报告 | 尚未提供 | **缺失** |

### 2.2 冲突一：发布说明文件与产品错配

**发现：** `product_release_notes.md` 的内容为"星河笔记 2.3"（一款 Markdown 笔记软件，支持批量导入、标签筛选、快捷键面板，兼容 macOS 13 / Windows 11），与本方案的硬件产品"智能随行杯"**完全无关**。

**影响：** 该文件不能作为随行杯的产品信息来源。若误将其功能（如批量导入 Markdown）纳入随行杯卖点，将导致信息失真。

**处理：** 本方案仅以 `product_brief.md` 为产品信息唯一依据，`product_release_notes.md` 标记为"无关输入，不予采纳"。建议后续核对文件上传是否有误。

### 2.3 冲突二：合规数据缺失与营销表述的矛盾

**发现：** 防水等级与食品接触材料报告尚未提供，但随行杯作为食品接触类消费品，"食品级安全""防水/防漏"是消费者高频关注且竞品常用的卖点。

**矛盾：** 营销端希望尽早使用"食品级""防漏"等表述以提升转化，但合规端未提供检测报告，简报明确禁止编造第三方检测结论。

**处理（关键取舍）：**
- **取舍决定：** 在合规报告到位前，所有对外信息**不得**使用"食品级认证""IPX 防水""防漏"等需要检测背书的表述。
- **替代表述：** 使用"可拆洗杯盖，清洁无死角"（基于已确认的结构卖点，不涉及材料认证）和"密封杯盖设计"（描述结构，不声明防水等级）。
- **解锁条件：** 食品接触材料报告到位后，可升级为"通过 XX 食品接触材料检测"（需引用实际报告编号）；防水等级报告到位后，可声明具体 IP 等级。

### 2.4 约束三：首发日期未定

**发现：** 首发日期尚未确定，导致所有时间线（预热期、首发期、持续期）无法锚定具体日期。

**处理：** 方案以"相对时间节点"（T-14 天预热、T 日首发、T+30 天持续）描述节奏，待首发日期确定后映射为绝对日期。Google Ads 账户搭建、素材制作、着陆页开发等不依赖首发日期的工作可立即启动。

### 2.5 约束四：Google Ads API 凭据缺口

**发现：** 按 `google-ads-api-quickstart` Skill 要求，执行 Google Ads API 需要 5 项认证参数（详见第 5.2 节），当前均未提供。

**处理：** Google Ads 渠道的 API 自动化操作处于**阻断状态**。方案给出凭据就绪后的完整执行路径，并标注可通过 Google Ads UI 手动投放作为临时替代（不涉及 API）。

---

## 3. 受众策略

### 3.1 核心受众画像

基于简报"一二线城市通勤人群"，细化为以下画像（**假设性画像，非实际用户调研结果**）：

| 维度 | 描述 |
|---|---|
| 年龄 | 25–40 岁（假设） |
| 城市 | 北京、上海、广州、深圳、杭州、成都等一二线城市 |
| 职业 | 白领、互联网/金融/咨询从业者、教师、医护等规律通勤人群 |
| 场景 | 每日公共交通/自驾通勤 30 分钟以上，办公室久坐，有热饮需求 |
| 痛点 | 现有保温杯过重/过大，杯盖难清洗，保温时长不够，外观不够简约 |
| 价格敏感度 | 中等，199 元处于可接受区间（假设，需实际验证） |

### 3.2 受众分层

| 层级 | 定义 | 优先级 | 触达策略 |
|---|---|---|---|
| 核心层 | 已有保温杯使用习惯、关注品质生活的通勤者 | P0 | 搜索广告 + 精准社交种草 |
| 扩展层 | 有通勤热饮需求但尚未使用保温杯的人群 | P1 | 社交内容种草 + 场景化展示 |
| 潜在层 | 礼品购买者（送同事/家人） | P2 | 节日节点 + 电商站内推荐 |

### 3.3 受众触达优先级说明

优先覆盖核心层（P0），因为其需求明确、转化路径短，适合用搜索广告（Google Ads）捕获高意图流量。扩展层（P1）需要教育成本，通过社交种草建立认知。潜在层（P2）依赖节日节点，非首发期重点。

---

## 4. 信息结构与卖点层级

### 4.1 核心信息屋

```
                    ┌─────────────────────┐
                    │   核心主张（一句话）  │
                    │ 通勤路上，轻量保温    │
                    │ 一杯刚刚好            │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
        ┌─────┴─────┐   ┌─────┴─────┐   ┌─────┴─────┐
        │ 支柱卖点 1  │   │ 支柱卖点 2  │   │ 支柱卖点 3  │
        │ 12 小时保温 │   │ 280g 轻量   │   │ 可拆洗杯盖  │
        └─────┬─────┘   └─────┬─────┘   └─────┬─────┘
              │                │                │
        ┌─────┴─────┐   ┌─────┴─────┐   ┌─────┴─────┐
        │ 支撑事实    │   │ 支撑事实    │   │ 支撑事实    │
        │ 从早到晚    │   │ 比手机还轻  │   │ 杯盖全拆    │
        │ 水温适宜    │   │ 通勤无负担  │   │ 清洗无死角  │
        └───────────┘   └───────────┘   └───────────┘
```

### 4.2 卖点优先级与使用场景

| 优先级 | 卖点 | 核心信息 | 适用渠道 | 备注 |
|---|---|---|---|---|
| P0 | 12 小时保温 | "从早高峰到晚下班，水温始终适宜" | 全渠道 | 主卖点，所有素材首屏展示 |
| P1 | 280g 轻量 | "比大多数手机还轻，通勤包无负担" | 社交种草、详情页 | 需配合对比图（已确认白底图可用） |
| P2 | 可拆洗杯盖 | "杯盖全拆，缝隙一冲即净" | 详情页、短视频 | 差异化卖点，适合演示类内容 |

### 4.3 禁用表述与合规边界

| 禁用表述 | 原因 | 允许的替代表述 |
|---|---|---|
| "食品级认证""通过 FDA 认证" | 食品接触材料报告未提供 | "可拆洗杯盖，清洁无死角" |
| "IPX7 防水""完全防漏" | 防水等级未提供 | "密封杯盖设计"（不声明等级） |
| "销量第一""百万用户选择" | 禁止编造销量/用户评价 | 不使用 |
| "比 XX 品牌便宜""竞品价格 XX" | 禁止编造竞品价格 | 不使用 |
| "第三方检测显示保温 XX 小时" | 禁止编造第三方检测结论 | 使用简报已确认的"12 小时保温" |

---

## 5. 渠道动作

### 5.1 渠道矩阵总览

| 渠道 | 角色 | 启动条件 | 当前状态 |
|---|---|---|---|
| Google Ads 搜索广告 | 捕获高意图搜索流量 | API 凭据就绪（阻断中）/ UI 手动可立即启动 | **API 阻断，UI 可替代** |
| 社交媒体种草（小红书/抖音等） | 建立认知、场景教育 | 素材就绪 | 可立即启动内容制作 |
| 电商平台站内 | 转化承接 | 店铺就绪、首发日期确定 | 待首发日期 |
| 私域/会员 | 复购与口碑 | 用户池建立 | 首发后启动 |

### 5.2 Google Ads 搜索广告（按 google-ads-api-quickstart Skill 执行）

#### 5.2.1 API 版本（动态解析结果）

按 Skill "Crucial Requirement: Dynamic Version Resolution" 规则，已通过实时抓取 [Google Ads API Release Notes](https://developers.google.com/google-ads/api/docs/release-notes.md.txt) 解析最新稳定主版本：

- **RESOLVED_API_VERSION = v25**（主版本发布于 2026-07-22，最新小版本 v25.1 发布于 2026-08-19）
- 未使用 Skill 内置离线回退值 v24，因为实时 URL 可访问且返回了更新的版本。

#### 5.2.2 所需凭据与当前状态

按 Skill "Step 1: Obtain Google Ads API Credentials"，执行 API 调用需要以下 5 项参数：

| 序号 | 参数 | 用途 | 当前状态 |
|---|---|---|---|
| 1 | Developer Token | 标识开发者访问与 API 配额 | **未提供** |
| 2 | OAuth2 Client ID | 应用标识 | **未提供** |
| 3 | OAuth2 Client Secret | 应用密钥 | **未提供** |
| 4 | OAuth2 Refresh Token | 自动获取新访问令牌 | **未提供** |
| 5 | Client Customer ID | 目标 Google Ads 账户 10 位 ID | **未提供** |
| 6（条件必填） | Login Customer ID | 经理账户 ID（通过经理账户访问客户账户时必填） | **未提供** |

**阻断结论：** 因 5 项必填凭据均未提供，Google Ads API 的任何自动化操作（创建广告系列、检索广告、批量修改等）均无法执行。本方案不编造凭据或执行结果。

#### 5.2.3 凭据就绪后的执行路径（Python 客户端库，推荐）

按 Skill "Path A: Official Client Libraries"，选择 Python 客户端库（`google-ads` 包），原因：团队技术栈友好、脚本维护成本低、Skill 提供完整参考。

**执行步骤（凭据就绪后）：**

1. **环境准备：**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   python -m pip install google-ads
   ```
   - Python 最低运行时版本需按 Skill 要求动态解析（访问 [Supported Client Library Versions](https://developers.google.com/google-ads/api/docs/client-libs.md.txt#supported_api_versions)），当前未执行解析，列为待补项。离线回退值为 Python 3.9+。

2. **配置文件 `google-ads.yaml`（项目根目录）：**
   ```yaml
   developer_token: <实际 Developer Token>
   client_id: <实际 OAuth2 Client ID>
   client_secret: <实际 OAuth2 Client Secret>
   refresh_token: <实际 OAuth2 Refresh Token>
   # 若通过经理账户访问客户账户，取消注释并填入：
   # login_customer_id: <实际经理账户 10 位 ID>
   use_proto_plus: true
   ```

3. **检索现有广告系列（验证连通性，Skill 标准 quickstart 脚本）：**
   - 脚本路径：`get_campaigns.py`（代码见 Skill `references/python.md`）
   - 运行命令：`python get_campaigns.py -c <10位客户ID>`
   - 客户 ID 必须去除连字符（如 `123-456-7890` → `1234567890`），脚本已自动处理。

4. **创建新品搜索广告系列（凭据就绪后开发）：**
   - 广告系列类型：Search Campaign
   - 目标：最大化点击量（首发期）/ 最大化转化（稳定期）
   - 关键词方向：保温杯、通勤杯、轻量保温杯、可拆洗保温杯、12小时保温（**关键词为假设方向，需实际关键词工具验证搜索量与竞争度**）
   - 广告文案：基于第 4 节信息结构撰写，遵守禁用表述规则
   - 着陆页：电商商品页或品牌活动页（需开发，列为依赖项）

#### 5.2.4 备选路径：Direct REST（无客户端库时）

若运行环境不支持 Python 客户端库（如轻量 Serverless 函数），按 Skill "Path B: Direct HTTP REST" 执行：

- **端点 URL（v25）：** `https://googleads.googleapis.com/v25/customers/{customer_id}/googleAds:searchStream`
- **OAuth2 授权路由（Skill 要求必须说明两种）：**
  - **Option A：Service Account Flow（推荐）** — 创建服务账户、授予 Ads 账户直接访问、生成 JWT 声明集、交换 access token。Scope 为 `https://www.googleapis.com/auth/adwords`。
  - **Option B：User Authentication Flow（替代）** — 使用 refresh_token + client_id + client_secret 通过 cURL 交换短期 access token（有效期约 1 小时）。
- **必填请求头：** `Content-Type: application/json`、`developer-token`、`Authorization: Bearer <access_token>`、`login-customer-id`（经理账户场景必填）。

#### 5.2.5 Developer Token 待审批约束

按 Skill "Pending Token Restriction"：若 Developer Token 状态为"Pending"（未审批），则**只能**操作 Google Ads 测试账户，对生产账户调用将报 `DEVELOPER_TOKEN_NOT_APPROVED` 错误。生产账户投放需 Token 获批为 **Explorer Access、Basic Access 或 Standard Access** 三者之一（按 Skill 要求完整列出三个等级名称，不简化）。

**当前状态：** Developer Token 未提供，无法判断审批状态。凭据提供后需首先确认 Token 状态，若为 Pending 则需先搭建测试账户验证流程。

#### 5.2.6 常见错误预案（按 Skill Troubleshooting 章节）

| 错误 | 原因 | 处理 |
|---|---|---|
| `USER_PERMISSION_DENIED` | OAuth 用户通过经理账户间接访问客户账户，但请求头缺少 `login_customer_id` | 在配置中添加经理账户 10 位 ID 作为 `login_customer_id` |
| `DEVELOPER_TOKEN_NOT_APPROVED` | Pending Token 操作生产账户 | 使用测试账户或等待 Token 审批（Explorer/Basic/Standard Access） |
| `NOT_ADS_USER` | OAuth 用户无目标账户访问权限 | 使用有访问权限的 Google 账户重新走 OAuth 流程 |
| `INVALID_CUSTOMER_ID` | 客户 ID 含连字符或非数字 | 确保去除连字符，脚本已自动处理 |

> 按 Skill "Static Diagnostics Constraint"：排错时不执行 bash 命令或本地测试脚本复现错误，仅通过静态代码分析与配置审查定位。

#### 5.2.7 临时替代方案（不依赖 API）

在 API 凭据就绪前，可通过 **Google Ads UI 手动创建搜索广告系列**，不涉及 API 调用。此路径不受 Skill 凭据约束，但无法自动化批量操作与数据回传。建议首发期小预算通过 UI 验证投放效果，同时推进 API 凭据申请。

### 5.3 社交媒体种草

**目标：** 建立"通勤轻量保温"的品类认知，为搜索广告与电商转化蓄水。

**内容方向（基于已确认卖点，不编造）：**
- 场景化图文：通勤包内的随行杯，突出 280g 轻量（配合白底图）
- 清洁演示短视频：可拆洗杯盖的拆解与清洗过程
- 保温测试内容：仅展示"12 小时保温"已确认参数，不编造第三方检测数据

**平台优先级：** 小红书（图文种草）> 抖音（短视频演示）> 微信公众号（深度内容）

**合规要求：** 所有内容遵守第 4.3 节禁用表述规则。KOL 合作需明确标注广告。

### 5.4 电商平台站内

**目标：** 承接搜索与种草流量，完成转化。

**动作：**
- 商品详情页：按卖点优先级（保温→轻量→可拆洗）组织内容，使用已确认白底图与规格
- 标题：包含核心关键词（保温杯、通勤、轻量、12小时保温）
- 主图：品牌主色 #176B87 统一视觉
- 首发活动：待首发日期确定后制定（当前无法锚定）

### 5.5 私域与会员

**目标：** 首发后启动，提升复购与口碑传播。

**动作：**
- 包裹卡引导加企业微信/关注公众号
- 会员专属配色或刻字服务（假设性方向，需产品端确认可行性）
- 用户晒图激励（**不编造用户评价，仅激励真实用户分享**）

---

## 6. 指标体系

### 6.1 北极星指标

| 指标 | 定义 | 目标值 | 说明 |
|---|---|---|---|
| 首发期订单量 | T 日至 T+30 日累计支付订单数 | **待设定**（无历史数据，无法合理预估） | 需结合实际投放预算与品类基准设定 |

> **说明：** 因简报禁止编造销量，且无历史销售数据，北极星指标的具体目标值列为待设定项，需在首发日期与预算确定后由业务方设定。

### 6.2 渠道级指标

| 渠道 | 核心指标 | 辅助指标 | 数据来源 |
|---|---|---|---|
| Google Ads | 点击率（CTR）、平均点击成本（CPC）、转化率 | 展示量、搜索词报告、质量得分 | Google Ads API（v25）/ UI 报告 |
| 社交媒体 | 互动率、种草内容曝光量、站外点击 | 粉丝增长、收藏/评论比 | 平台后台 |
| 电商站内 | 商品页转化率、加购率、客单价 | 详情页停留时长、退货率 | 电商平台后台 |
| 私域 | 加粉率、复购率、NPS | 会员活跃度 | 私域工具后台 |

> **说明：** 以上指标为框架性定义，具体目标值因缺少历史数据与行业基准，均列为待设定项。不编造任何实际或预估数值。

### 6.3 指标基线与待补项

| 待补项 | 用途 | 来源 |
|---|---|---|
| 品类平均 CTR / CPC / CVR 基准 | 设定 Google Ads 目标 | 行业报告 / Google Ads Keyword Planner（需凭据） |
| 竞品价格带 | 定价策略验证 | 市场调研（简报禁止编造，需实际采集） |
| 历史同类产品销售数据 | 销量目标设定 | 内部数据（如有） |
| 用户调研结果 | 受众画像验证 | 定性/定量调研（当前未执行） |

---

## 7. 风险、依赖与关键取舍

### 7.1 关键取舍

| 取舍点 | 选项 A | 选项 B | 决定 | 理由 |
|---|---|---|---|---|
| 合规表述 | 提前使用"食品级""防水"等表述加速转化 | 合规报告到位前不使用，仅用结构描述 | **选 B** | 简报明确禁止编造第三方检测结论；违规表述可能引发消费者投诉与平台下架 |
| Google Ads 启动方式 | 等待 API 凭据就绪后自动化投放 | 先通过 UI 手动投放，API 后续接入 | **选 B（临时）** | UI 手动投放不依赖 API 凭据，可立即启动；API 用于后续批量管理与数据自动化 |
| 首发节奏 | 等所有信息（日期、合规报告）完备再启动 | 不依赖日期的工作（素材、账户、内容）立即启动，日期相关工作待确认 | **选 B** | 首发日期与合规报告为外部依赖，不应阻塞可并行的准备工作 |
| 受众覆盖 | 首发期全量覆盖三层受众 | 聚焦核心层（P0），扩展层/潜在层后续推进 | **选 B** | 首发期预算与精力有限，核心层需求明确、转化路径短，ROI 预期更高 |

### 7.2 依赖清单

| 依赖项 | 依赖方 | 影响 | 状态 |
|---|---|---|---|
| 首发日期确定 | 业务/产品团队 | 所有时间线锚定、电商活动排期 | **未完成** |
| 食品接触材料报告 | 合规/供应链 | 解锁"食品级"相关表述 | **未完成** |
| 防水等级报告 | 合规/供应链 | 解锁防水/防漏相关表述 | **未完成** |
| Google Ads Developer Token | 市场/技术团队 | API 自动化投放 | **未完成** |
| Google Ads OAuth2 凭据（Client ID/Secret/Refresh Token） | 技术团队 | API 认证 | **未完成** |
| Google Ads 客户账户（Client Customer ID） | 市场团队 | 广告投放目标账户 | **未完成** |
| 电商店铺与商品页 | 电商运营 | 转化承接 | 状态未知 |
| 着陆页开发 | 设计/技术 | 广告落地页 | 状态未知 |
| 产品实拍图/场景图（非白底图） | 设计/摄影 | 社交种草素材 | 状态未知 |

### 7.3 风险登记

| 风险 | 概率 | 影响 | 缓解措施 |
|---|---|---|---|
| 合规报告延迟到位，导致卖点表述受限 | 中 | 中 | 提前使用结构描述替代；报告到位后 48 小时内更新全渠道文案 |
| Google Ads 凭据申请周期长，影响自动化投放 | 中 | 中 | UI 手动投放作为临时替代；并行推进凭据申请 |
| Developer Token 处于 Pending 状态，无法投放生产账户 | 中 | 高 | 凭据到位后首先确认状态；若 Pending 则先搭建测试账户验证，同时申请审批 |
| 首发日期持续未定，影响团队节奏与渠道排期 | 低 | 中 | 以相对时间节点规划；可并行工作不等待 |
| `product_release_notes.md` 错配导致信息误用 | 低 | 高 | 已标记为无关输入；建议核对文件上传 |
| 关键词竞争度高，CPC 超出预期 | 中 | 中 | 首发期小预算测试；使用长尾关键词降低竞争 |
| 产品实际体验与卖点描述不符，引发负面评价 | 低 | 高 | 所有表述基于已确认规格；不夸大；首发期关注真实用户反馈并及时响应 |

---

## 8. 待补项与阻断说明

### 8.1 阻断项（当前无法继续执行）

| 阻断项 | 缺失条件 | 影响范围 | 复测方法 |
|---|---|---|---|
| Google Ads API 自动化操作 | 5 项必填凭据（Developer Token、OAuth2 Client ID、Client Secret、Refresh Token、Client Customer ID）均未提供 | 第 5.2 节所有 API 操作 | 凭据提供后，运行 `python get_campaigns.py -c <客户ID>` 验证连通性 |
| 首发期销量目标设定 | 无历史销售数据、无品类基准、禁止编造销量 | 第 6.1 节北极星指标目标值 | 获取历史数据或行业基准后设定 |
| 合规卖点表述 | 食品接触材料报告、防水等级报告未提供 | 第 4.3 节禁用表述中的部分条目 | 报告提供后，引用实际编号升级表述 |

### 8.2 待补项（可并行准备，不阻断当前方案制定）

| 待补项 | 说明 |
|---|---|
| 首发日期 | 确定后映射相对时间节点为绝对日期 |
| Python 最低运行时版本 | 按 Skill 要求动态解析，当前使用离线回退值 3.9+ |
| 关键词搜索量与竞争度 | 需 Google Ads Keyword Planner（需凭据）或第三方工具 |
| 电商店铺状态 | 确认店铺是否已开通、商品页是否已搭建 |
| 场景图/实拍图素材 | 白底图已确认，但社交种草需要场景化素材 |
| KOL/达人合作资源 | 社交种草渠道执行所需 |
| 投放预算 | 各渠道预算分配需业务方确定 |

---

## 9. 附录：Skill 执行记录

### 9.1 实际读取的 Skill 文件相对路径

以下为从 `google-ads-api-quickstart.zip` 解压后实际读取的全部文件（相对于 ZIP 根目录）：

| 序号 | 文件相对路径 |
|---|---|
| 1 | `google-ads-api-quickstart/SKILL.md` |
| 2 | `google-ads-api-quickstart/references/python.md` |
| 3 | `google-ads-api-quickstart/references/java.md` |
| 4 | `google-ads-api-quickstart/references/dotnet.md` |
| 5 | `google-ads-api-quickstart/references/php.md` |
| 6 | `google-ads-api-quickstart/references/ruby.md` |
| 7 | `google-ads-api-quickstart/references/perl.md` |
| 8 | `google-ads-api-quickstart/references/rest.md` |

> 共 8 个文件（1 个 SKILL.md + 7 个参考文件），全部已读取。ZIP 中无其他文件。

### 9.2 确实影响结果的 SKILL.md 规则

以下规则从 SKILL.md 中实际读取，并对本方案的内容产生了实质性影响：

#### 规则 1：动态 API 版本解析（影响最大）

- **SKILL.md 原文：** "DO NOT Hardcode: Never use hardcoded Google Ads API versions (e.g., `v24`)... You must dynamically resolve the latest stable versions at the start of execution."
- **影响：** 方案未使用 Skill 内置离线回退值 v24，而是实时抓取 Google Ads API Release Notes，解析出最新稳定主版本为 **v25**（2026-07-22 发布）。REST 端点 URL、客户端库版本均基于 v25。若忽略此规则使用 v24，将导致 API 端点指向旧版本，可能缺少 v25 的新功能（如 New Customer Acquisition Goal）。

#### 规则 2：5 项必填凭据与阻断判定

- **SKILL.md 原文：** "Before installing libraries or making API calls, you must obtain the five required authentication parameters"（Developer Token、OAuth2 Client ID、Client Secret、Refresh Token、Client Customer ID）。
- **影响：** 方案在第 5.2.2 节逐项核对 5 项凭据，确认均未提供，从而判定 Google Ads API 自动化操作为**阻断状态**，未编造任何凭据或执行结果。这直接影响了渠道动作章节的结构（区分"API 阻断"与"UI 临时替代"）。

#### 规则 3：Pending Developer Token 仅可操作测试账户

- **SKILL.md 原文：** "If your Developer Token status is 'Pending' (unapproved), you MUST ONLY target Google Ads Test Accounts."
- **影响：** 方案在第 5.2.5 节明确标注此约束，并要求凭据到位后首先确认 Token 状态。同时按 Skill 要求完整列出三个生产访问等级名称（Explorer Access、Basic Access、Standard Access），未简化为"至少 Basic Access"。

#### 规则 4：REST 路径必须说明两种 OAuth 授权路由

- **SKILL.md 原文（rest.md）：** "your response MUST explicitly explain both OAuth2 authorization routes: Option A: Service Account Flow... Option B: User Authentication Flow..."
- **影响：** 方案第 5.2.4 节在 REST 备选路径中同时说明了 Service Account Flow 与 User Authentication Flow 两种路由，未省略任何一种。

#### 规则 5：静态诊断约束（排错不执行命令）

- **SKILL.md 原文：** "When troubleshooting, you MUST NOT execute bash commands, run local test scripts, or attempt to reproduce the error in the workspace."
- **影响：** 方案第 5.2.6 节错误预案仅通过静态分析给出原因与处理，未尝试执行任何命令复现错误。

---

## 文档版本与声明

- **制定日期：** 2026-08-26
- **产品信息来源：** `product_brief.md`（唯一依据）
- **无关输入：** `product_release_notes.md`（星河笔记 2.3，与本产品无关，未采纳）
- **Skill 依据：** `google-ads-api-quickstart`（SKILL.md 及 7 个参考文件，全部已读取）
- **数据声明：** 本文档未编造任何销量、用户评价、竞品价格、第三方检测结论。所有量化目标为待设定项，所有画像为假设性画像。
- **阻断声明：** Google Ads API 自动化操作因缺少 5 项必填凭据处于阻断状态，未假装执行成功。
