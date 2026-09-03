# 智能随行杯 TikTok Shop 广告投放策略

> 本文件依据 `tiktok-shop-ads` Skill 的 SKILL.md 框架与输出格式编制，结合 `product_brief.md` 中的新品信息。所有结论与假设已分开标注；未提供的外部数据一律列为待补项，未编造任何销量、用户评价、第三方检测结论或竞品价格。

---

## 一、输入文件说明

| 文件 | 内容 | 是否采用 |
|------|------|----------|
| `product_brief.md` | 智能随行杯新品任务简报 | ✅ 本策略的核心输入 |
| `product_release_notes.md` | "星河笔记 2.3"软件发布说明（Markdown 导入、标签筛选等） | ❌ 与智能随行杯无关，未纳入策略 |

**说明：** `product_release_notes.md` 描述的是一款笔记软件的版本更新，与本次新品（智能随行杯）无任何关联，不作为策略依据。若该文件系误传，请确认后补充正确的发布说明。

---

## 二、结论与假设

### 2.1 已确认事实（来自 product_brief.md）

- 产品：智能随行杯
- 目标用户：一二线城市通勤人群
- 核心卖点：12 小时保温、重量 280g、可拆洗杯盖
- 建议零售价：199 元
- 已确认素材：产品白底图、基础规格、品牌主色 #176B87
- 交付语言：中文

### 2.2 策略结论（基于 SKILL.md 框架推导）

1. **广告目标**：新品期以"转化（商品销量）"为主目标，"品牌认知"为辅助目标，符合 SKILL.md Step 1 中"Define campaign objectives"的要求。
2. **广告格式组合**：采用 Product Shopping Ads（商品购物广告）+ Video Shopping Ads（视频购物广告）双格式启动；Live Shopping Ads（直播购物广告）列为第二阶段测试项，符合 SKILL.md 输出格式中的三类 Campaign Type 架构。
3. **投放节奏**：遵循 SKILL.md 最佳实践"Start conservative"——小预算测试 → 数据验证 → 逐步放量，不做首发即大规模投放。
4. **创意方向**：以已确认的白底图和基础规格为基础，围绕三大核心卖点制作素材；因新品无用户评价，SKILL.md 创意策略中要求的"reviews / customer testimonials"环节以产品实测演示替代，待真实评价积累后再补充（详见风险章节）。
5. **定向策略**：遵循 SKILL.md"audience precision"原则——先窄后宽，从核心通勤人群定向启动，再按"Audience Expansion Plan"四步扩展。

### 2.3 假设（需业务方确认，非事实）

| 编号 | 假设内容 | 依据 | 影响 |
|------|----------|------|------|
| A1 | 投放市场为 TikTok Shop 已开通站点（如东南亚/英美），售价 199 元需换算为站点当地货币 | SKILL.md 面向 TikTok Shop；简报以人民币定价 | 影响预算、定价、定向地区设置 |
| A2 | 每日测试预算约 ¥350–700/Campaign（约 $50–100） | SKILL.md Bidding & Budget 建议"conservative daily budgets ($50-100/day per campaign)" | 实际预算需业务方确认 |
| A3 | 产品毛利率足以支撑 CPA 与 ROAS 目标 | SKILL.md 要求"Target CPA based on profit margins"，但简报未提供成本 | 无法计算目标 ROAS 与 CPA，待补 |
| A4 | 首发日期在素材与账户准备完成后 2–4 周内 | 简报注明首发日期未定 | 影响排期，所有时间节点为相对值 |

---

## 三、最小可验证版本（MVP）

依据 SKILL.md 的三步流程（Step 1 策略制定 → Step 2 搭建上线 → Step 3 优化放量），MVP 覆盖 **Step 1 全部 + Step 2 的最小闭环**，目标是用最小成本验证"素材-定向-转化"链路是否跑通。

### 3.1 MVP 关键步骤

| 步骤 | 动作 | 对应 SKILL.md 环节 | 负责方 |
|------|------|---------------------|--------|
| M1 | 确认投放站点、账户、预算、产品成本与毛利（关闭假设 A1–A3） | Step 1: Define objectives | 业务方 |
| M2 | 基于已确认白底图 + 三大卖点，制作 3–4 组商品购物广告素材 + 2 条 15–30 秒视频素材 | Step 2: Create ad creatives | 创意团队 |
| M3 | 搭建 Campaign 结构：1 个 Product Shopping Campaign（转化目标）+ 1 个 Video Shopping Campaign（流量/认知目标），各含 1–2 个 Ad Group | Step 2: Configure campaign settings | 投手 |
| M4 | 配置转化追踪（TikTok Pixel / Events API）与商品目录，完成联调验证 | Step 2: Set up tracking, attribution | 技术/投手 |
| M5 | 以保守日预算（假设 A2）上线，开启自动出价用于数据收集 | Step 2: Launch with testing methodologies | 投手 |
| M6 | 连续运行 7 天，每日检查 CTR、CPC、转化数、CPA、频次 | Step 3: Monitor KPIs | 投手 |

### 3.2 MVP 验收标准

| 编号 | 验收项 | 通过标准 |
|------|--------|----------|
| V1 | 追踪验证 | TikTok Pixel / Events API 成功回传"加购"和"完成支付"事件，测试订单可在 Ads Manager 中归因 |
| V2 | 素材就绪 | 3–4 组商品卡素材 + 2 条视频素材通过审核并正常投放（符合 SKILL.md"A/B test 3-4 creative variations"要求） |
| V3 | 广告上线 | 2 个 Campaign 均通过审核、获得展示量，无定向或素材拒登 |
| V4 | 基线数据 | 7 天内每个 Ad Group 累计至少获得可统计的点击与转化数据（具体样本量以站点实际流量为准，不预设数字） |
| V5 | 合规检查 | 所有素材与落地页未使用第三方检测结论、销量、用户评价、竞品价格等简报禁止编造的内容 |
| V6 | 资质完备 | 食品接触材料报告与防水等级（如宣传涉及）已补齐或素材中未出现相关宣称 |

---

## 四、完整投放策略

### 4.1 Campaign Goal / Budget / Target ROAS

- **Campaign Goal（广告目标）：** 转化（商品销量）为主，品牌认知为辅
- **Budget（预算）：** 待业务方确认；建议按 SKILL.md 保守起步原则，初始 ¥350–700/Campaign/天（假设 A2）
- **Target ROAS（目标 ROAS）：** 待补——需产品成本与毛利率数据后设定（SKILL.md 要求基于利润率计算，当前无法得出）

### 4.2 Campaign Structure & Strategy

**Campaign Architecture（活动架构）：**

| Campaign Type | Objective | Budget | Target Audience | Bid Strategy |
|---------------|-----------|--------|-----------------|--------------|
| Product Shopping Ads（商品购物广告） | Conversions（转化） | 待确认（建议 ¥350–700/天，假设 A2） | 一二线城市 22–40 岁通勤人群，关注家居/厨具/健康生活方式 | 初期自动出价收集数据，数据充足后转手动（SKILL.md: "Start with automatic bidding for data collection"） |
| Video Shopping Ads（视频购物广告） | Traffic / Brand Awareness（流量/认知） | 待确认（建议 ¥350–700/天，假设 A2） | 通勤场景兴趣人群 + 保温杯/水杯品类兴趣人群 | CPC / CPM，按视频互动优化 |
| Live Shopping Ads（直播购物广告） | Event Promotion（活动促销） | 第二阶段启用，预算待定 | 已互动/已加购人群再营销 + 直播间互动人群 | Target CPA（待具备直播能力后开通） |

### 4.3 Ad Creative Strategy（广告创意策略）

**Product Shopping Ads（商品购物广告）：**
- **Creative format（创意格式）：** 基于已确认产品白底图的商品目录展示
- **Key elements（关键元素）：** 价格（199 元/当地货币换算）、清晰产品图、三大核心卖点图标化呈现（12h 保温 / 280g 轻量 / 可拆洗杯盖）
- **CTA strategy（行动号召）：** "立即购买"配合新品上市信息；**不使用**"热销""万人好评"等无数据支撑的紧迫感话术
- **Testing plan（测试计划）：** A/B 测试 3–4 组素材变体（SKILL.md 要求），变量包括：卖点排序、主图角度、品牌主色 #176B87 的运用比例
- **⚠️ 与 SKILL.md 的差异处理：** SKILL.md 要求 Key elements 包含"reviews"、Video Shopping Ads 包含"customer testimonials/reviews"。但本产品为新品且简报明确禁止编造用户评价，因此 MVP 阶段**不以用户评价作为创意元素**，改用产品功能实测演示；待真实用户评价产生后再补充（见风险 R3）

**Video Shopping Ads（视频购物广告）：**
- **Video length（视频时长）：** 15–30 秒（SKILL.md 建议最优时长）
- **Hook strategy（开头策略）：** 前 3 秒展示通勤场景痛点（如"通勤路上咖啡凉了""包太重"）并引出产品
- **Product demo（产品演示）：** 展示 12 小时保温实测（仅展示可验证的温度变化过程，不宣称第三方检测结论）、280g 轻量上手对比、杯盖拆洗过程
- **Social proof（社会证明）：** **MVP 阶段不使用**用户评价/证言（原因同上）；以规格参数和功能演示替代
- **视觉规范：** 使用品牌主色 #176B87 作为字幕/包装元素主色调

### 4.4 Targeting Strategy（定向策略）

**Primary Audiences（核心受众）：**
- **Demographics（人口属性）：** 22–40 岁（假设，待确认）、一二线城市、通勤上班族（基于简报"通勤人群"推导）
- **Interests（兴趣）：** 家居生活、厨具/水具、健康/养生、通勤/上班族生活方式
- **Behaviors（行为）：** 电商购物活跃用户、水杯/保温杯品类浏览或购买行为（以 TikTok Shop 可用定向维度为准）
- **Custom audiences（自定义受众）：** 新品期无存量用户，初期不设再营销列表；待积累加购/访客数据后建立再营销包

**Audience Expansion Plan（受众扩展计划，按 SKILL.md 四步走）：**
1. 从核心受众（通勤人群 + 品类兴趣）启动，验证转化
2. 基于首批购买者创建类似受众（Lookalike）
3. 扩展至更广泛的兴趣定向（如健身、户外、办公）
4. 对加购未购、浏览未购用户实施动态商品再营销

### 4.5 Bidding & Budget Strategy（出价与预算策略）

**Initial Setup（初始设置）：**
- 采用自动出价收集数据（SKILL.md: "Start with automatic bidding for data collection"）
- 保守日预算：建议 ¥350–700/Campaign/天（假设 A2，待确认）
- Target CPA：待补——需基于产品利润率设定（SKILL.md 要求基于利润率）
- 最低 ROAS 阈值：待补——同上

**Scaling Plan（放量计划）：**
- 对胜出 Ad Group 每次提预算 20–30%（SKILL.md: "Increase budgets by 20-30% for winning ad sets"）
- 数据充足后（建议单 Ad Group 累计 ≥50 次转化，具体以 TikTok 算法学习期要求为准）转手动出价
- 放量期间维持 ROAS 目标不降级

### 4.6 Performance Tracking（效果追踪）

**Key Metrics to Monitor（核心监控指标）：**

| 指标 | MVP 目标值 | 说明 |
|------|-----------|------|
| ROAS | 待基线建立后设定 | SKILL.md 要求设定目标值，但需毛利数据 |
| CTR（点击率） | 待基线建立后设定 | 不预设行业均值，避免编造 |
| Conversion Rate（转化率） | 待基线建立后设定 | 同上 |
| CPA（单次获客成本） | 待毛利数据确认后设定 | 基于利润率计算 |
| Frequency（频次） | 控制在合理范围避免素材疲劳 | SKILL.md 建议保持在阈值以下，具体数值待基线 |

**Optimization Schedule（优化节奏）：**
- **每日：** 预算调整与效果检查（SKILL.md: "Daily: Budget adjustments and performance review"）
- **每周：** 素材测试与受众优化
- **每月：** Campaign 结构与策略复盘

### 4.7 Creative Testing Plan（素材测试计划）

**第 1 个月：基础测试（MVP 阶段）**
- [ ] 测试 3–4 组商品展示素材变体
- [ ] A/B 测试不同开头 Hook 与 CTA
- [ ] 对比功能演示型 vs 场景痛点型视频
- [ ] 测试视频时长 15s vs 30s

**第 2 个月起：进阶优化**
- [ ] 测试季节/趋势创意主题
- [ ] 上线动态商品目录广告
- [ ] 测试直播购物活动推广（待直播能力就绪）
- [ ] 放量表现最佳的素材格式

### 4.8 Success Metrics & Goals（成功指标与目标）

**30 天目标：**
- Campaign ROAS：待毛利数据确认后设定
- 月广告花费：待预算确认
- CPA：待毛利数据确认后设定
- 触达人数：待基线建立后设定

> **注：** SKILL.md 模板要求填写具体数值，但产品简报未提供成本、预算、历史数据，且明确禁止编造数据。以上目标值在 MVP 基线数据建立（M6 完成）并补齐成本数据后填写，此处不虚构数字。

**扩量里程碑：**
- 第 1 个月：建立可盈利的基线 Campaign
- 第 2 个月：在 ROAS 达标前提下提升日预算
- 第 3 个月：根据数据扩展更多素材方向与受众
- 第 4 个月起：评估扩展至其他产品线或市场

### 4.9 Next Actions（下一步行动）

- [ ] 确认投放站点、TikTok Shop Ads Manager 账户与店铺状态
- [ ] 业务方确认预算、产品成本与毛利率（关闭假设 A1–A3）
- [ ] 补齐食品接触材料报告与防水等级信息（或在素材中避免相关宣称）
- [ ] 确认首发日期（关闭假设 A4）
- [ ] 基于已确认白底图制作 3–4 组商品素材 + 2 条视频素材
- [ ] 创建 Campaign 结构与 Ad Group
- [ ] 配置 TikTok Pixel / Events API 转化追踪并完成联调
- [ ] 以保守预算上线 MVP 测试
- [ ] 建立每日优化检查与每周复盘机制

---

## 五、风险与应对

| 编号 | 风险 | 影响 | 应对措施 |
|------|------|------|----------|
| R1 | 首发日期未定，排期无法锁定 | 影响素材制作与上线节奏 | 所有时间节点以 T+N 表示；首发日期确认后倒排 |
| R2 | 食品接触材料报告未提供 | 饮水器具若缺少合规报告，可能被平台拒审或引发合规风险 | 报告补齐前，素材与详情页不出现"食品级""安全材质"等宣称；优先推动报告补齐 |
| R3 | 新品无用户评价，SKILL.md 创意策略中的 reviews/testimonials 无法使用 | 社会证明缺失可能影响转化率 | MVP 以功能实测和规格参数替代；上线后通过随卡好评引导、真实用户晒单积累，严禁编造评价 |
| R4 | 防水等级未提供 | 若素材暗示防水性能但无依据，构成虚假宣传 | 不在素材中宣称防水性能；待等级确认后决定是否宣传 |
| R5 | 缺少产品成本与毛利率 | 无法设定目标 ROAS 与 CPA，出价策略缺乏依据 | MVP 阶段以自动出价收集数据；成本数据补齐后立即设定目标值 |
| R6 | 无历史投放数据 | SKILL.md 明确指出"without real-time data, campaign setup based on best practices rather than account-specific data" | 严格遵循小预算测试原则，不预设 CTR/CVR 等行业均值，以实际基线数据驱动优化 |
| R7 | 投放站点与定价货币未确认 | 199 元人民币定价需适配 TikTok Shop 站点当地货币 | 业务方确认站点后进行定价换算与合规检查 |

---

## 六、待补项清单（需外部输入）

| 编号 | 待补内容 | 用途 | 责任方 |
|------|----------|------|--------|
| P1 | 产品成本与毛利率 | 计算 Target ROAS / CPA | 业务/财务 |
| P2 | 投放站点与市场 | 确定地区定向、货币、语言 | 业务方 |
| P3 | 广告总预算与测试预算 | 填充 Campaign 预算 | 业务方 |
| P4 | 首发日期 | 锁定排期 | 业务方 |
| P5 | 食品接触材料报告 | 合规审核 | 供应链/品控 |
| P6 | 防水等级 | 决定是否可宣传防水 | 供应链/品控 |
| P7 | TikTok Shop Ads Manager 账户与店铺状态 | 账户搭建 | 运营 |
| P8 | 更多素材（场景图、视频原片等） | 丰富创意测试 | 创意团队 |

---

## 七、SKILL.md 关键规则遵循说明

本策略严格遵循 `tiktok-shop-ads/SKILL.md` 的以下规则，其中对结果影响最大的包括：

1. **"Limitations without real-time data"条款**：SKILL.md 明确指出"Campaign setup based on best practices rather than account-specific data"。这直接决定了本策略不预设 CTR、CVR、ROAS 等具体数值，所有目标值标注为"待基线建立后设定"，与简报"需要外部数据时明确列为待补项"的要求一致。
2. **"Start conservative"最佳实践**：SKILL.md 建议"$50-100/day per campaign"保守起步，本策略据此建议 ¥350–700/Campaign/天的测试预算，并采用"小预算测试→验证→20–30% 逐步放量"的节奏。
3. **创意策略中 reviews/testimonials 的要求与简报禁令的冲突处理**：SKILL.md 要求商品广告包含"reviews"、视频广告包含"customer testimonials/reviews"，但简报明确禁止编造用户评价且新品无真实评价。本策略将该元素替换为功能实测演示，并列为风险 R3，待真实评价积累后补充——这是 SKILL.md 规则与业务约束交叉后直接改变创意方案的典型案例。
4. **输出格式**：本文件第四章完整采用 SKILL.md"Output Format"的章节结构（Campaign Goal/Budget/ROAS → Campaign Architecture 表 → Ad Creative Strategy → Targeting Strategy → Bidding & Budget → Performance Tracking → Creative Testing Plan → Success Metrics → Next Actions）。
5. **Audience Expansion Plan 四步法**：严格按 SKILL.md 的"核心受众→类似受众→兴趣扩展→动态再营销"顺序规划。
