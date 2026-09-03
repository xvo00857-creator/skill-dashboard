# Dynamic Pricing System — 智能随行杯（新品）

> 本文件依据 Skill `dynamic-pricing-ecommerce` 的 SKILL.md 工作流与输出格式生成。
> 所有结论仅基于随附的 `commerce_reviews.csv` 与 `product_brief.md` 两份本地文件，
> **未访问任何电商平台后台、未调用任何外部数据、未启用或修改任何在线价格**。

## Scope and Evidence

- **Channels and markets：** Unknown —— 简报与评论均未提供销售渠道、站点、币种、税务处理或履约方式。
- **SKUs：** 单一新品「智能随行杯」；未提供 SKU 编码、变体、包装规格。
- **Sources and dates：**
  - `product_brief.md`（本地文件，新品任务简报，无出具日期）
  - `commerce_reviews.csv`（本地文件，6 条评论，日期范围 2026-07-01 至 2026-07-14）
- **Confirmed inputs（有 inspected 证据支持）：**
  - 建议零售价 199 元（简报载明，系 list/MSRP，非实际成交价）
  - 核心卖点：12 小时保温、重量 280g、可拆洗杯盖
  - 目标用户：一二线城市通勤人群
  - 已确认素材：白底图、基础规格、品牌主色 #176B87
  - 评论数据共 6 条，字段：review_id, rating, verified_purchase, review_date, review_text, helpful_votes
  - 已验证购买（verified_purchase=true）3 条：R001(5★)、R004(1★)、R005(4★)
  - 未验证购买 3 条：R002、R003、R006
  - R002 与 R003 文本完全相同（"Amazing product best ever"），同日、同评分、均未验证、0 有用票
  - R004 为 1★ 已验证购买，内容「收到后无法开机，已申请售后」，7 张有用票
  - R006 评分缺失（空值），文本「评价内容缺失关键信息」
- **Assumptions（显式情景占位，非观察事实）：**
  - 「智能随行杯」含电子功能（温度显示/提醒等），依据是评论出现「续航」「开机」字样；
    但简报卖点未描述任何电子功能，此为推断，需向卖家确认。
  - 评论所指商品即简报中的「智能随行杯」，因无 SKU/商品 ID 关联，暂作此假设。
- **Unknowns（缺失，阻断自动化定价）：**
  - COGS、入仓运费、关税、包装、履约费、支付/佣金/广告/退货等变动成本（全部缺失）
  - 目标贡献额/贡献率、卖家批准的 hard floor 与 ceiling、MAP/品牌价格约束
  - 实际成交价、卖家承担折扣、优惠券、促销叠加规则
  - 库存（在手/在途/库龄/可售周数/补货提前期/断货风险）
  - 带时间戳的流量、订单、件数、转化、取消、退货数据
  - 可比竞品报价（卖家、履约、可得性、到手价、来源、抓取时间）
  - 销售渠道、市场、币种、平台、当前定价工具、账号权限、审批人
  - 首发日期；防水等级；食品接触材料报告（简报明示未提供）

## 证据边界与评论质量审查

按 SKILL.md「Select and Validate Signals」要求，对每条评论记录来源、新鲜度、覆盖度、失效模式与处置：

| review_id | 评分 | 已验证 | 日期 | 有用票 | 内容摘要 | 信号判定 | 处置 |
|---|---|---|---|---|---|---|---|
| R001 | 5 | true | 2026-07-01 | 18 | 包装完好，续航符合描述 | 可信正面信号；但「续航」暗示电子功能，与简报卖点不一致 | 保留，标记待确认卖点 |
| R002 | 5 | false | 2026-07-01 | 0 | Amazing product best ever | 可疑：未验证、英文模板化文本、0 有用票、与 R003 完全重复 | **拒绝作为信号**（疑似刷评/垃圾评论） |
| R003 | 5 | false | 2026-07-01 | 0 | Amazing product best ever | 可疑：R002 的完全副本 | **拒绝作为信号** |
| R004 | 1 | true | 2026-07-03 | 7 | 收到后无法开机，已申请售后 | 可信负面信号：已验证、具体故障、已走售后、7 张有用票 | 保留，升级为质量异常项 |
| R005 | 4 | true | 2026-07-14 | 4 | 功能正常，但说明书不够清楚 | 可信中性偏正信号；说明书问题 | 保留，列入文档改进项 |
| R006 | （空） | false | 2026-07-14 | 0 | 评价内容缺失关键信息 | 数据不完整：无评分、未验证、文本无实质信息 | **排除出统计**，标记数据质量问题 |

**统计口径（仅基于上述保留记录）：**

| 口径 | 样本 | 评分均值 |
|---|---|---|
| 全部有评分记录 | R001–R005（5 条） | 4.00 |
| 仅已验证购买 | R001, R004, R005（3 条） | 3.33 |
| 剔除 R002/R003 重复刷评后 | R001, R004, R005（3 条） | 3.33 |

> 说明：表面 4.00 星的均值被两条未验证重复好评抬高；可信的已验证购买口径仅 3.33 星，
> 且唯一一条高有用票负面评论指向「无法开机」的功能性故障。样本量 n=3（可信口径），
> 不足以推断趋势、弹性或因果关系（符合 SKILL.md「Sparse or confounded historical data
> cannot prove demand response, elasticity, or causality」）。

## Control Recommendation

- **Objective：** 在新品信息严重不全阶段，建立可观察、可回滚的最小定价治理框架；
  在补齐成本与信号前不做任何自动调价。
- **Recommended automation level：** **Manual-only（仅分析，不自动改价）**。
- **Confidence：** Low —— 关键经济参数与信号全部缺失，样本量极小。
- **Blocked decisions（阻断项）：**
  - 价格下限（floor）无法计算：缺 COGS 与变动成本/费率。
  - 价格上限（ceiling）无法论证：无可比竞品与参考价；简报明确禁止编造竞品价格。
  - 任何自动/需审批调价规则无法生效：缺卖家书面授权的 hard floor/ceiling。
  - 需求/弹性/转化判断无法成立：无流量、订单、时间序列数据。
  - 上线节奏无法排期：首发日期未定。

## Economics and Bounds

按 SKILL.md 公式 `Price Floor = (Unit Cost + Fixed Variable Costs + Target Contribution $) / (1 - Variable Fee Rate)`，
所需参数全部缺失，故 floor/ceiling 均标记为阻断：

| SKU/group | Current | Floor | Ceiling | Base contribution | Downside contribution | Approval |
|---|---|---|---|---|---|---|
| 智能随行杯 | 199 元（MSRP，非成交价） | **Blocked：缺 COGS/变动成本/费率/目标贡献** | **Blocked：缺竞品/参考价/品牌约束，且禁止编造** | **Blocked** | **Blocked** | Manual-only |

> 199 元仅为简报所载建议零售价，不能视为实际成交价、净收入或贡献口径输入。
> 在卖家提供成本表与批准的价格上下限之前，任何 floor/ceiling 数字均属编造，本文件不予给出。

## SKU Eligibility

| SKU/group | Tier | Reason | Missing evidence | Owner |
|---|---|---|---|---|
| 智能随行杯 | **Manual-only** | 新品上市期、成本缺失、数据稀疏、存在功能性故障差评、卖点描述与评论信号不一致；按 SKILL.md「Default uncertain SKUs to the more restrictive tier」从严定级 | COGS、费率、目标贡献、批准的 floor/ceiling、库存、渠道、竞品、首发日期、防水/食品接触认证 | 待卖家指定（建议：品类运营负责人 + 财务审批人） |

## Signal Register

| Signal | Source/freshness | Validation | Failure fallback | Confidence |
|---|---|---|---|---|
| 评论评分 | 本地 CSV，2026-07-01 至 07-14，6 条 | 仅采纳已验证购买；剔除 R002/R003 重复模板评论；R006 无评分排除 | 数据不足时不触发任何价格动作，路由人工复核 | Low（n=3 可信） |
| 质量/售后信号 | R004（已验证，7 有用票） | 单点故障报告，非批量趋势；需售后工单/退货率交叉验证 | 不据此自动降价或加价；升级质量排查 | Low（单点） |
| 说明书反馈 | R005（已验证，4 有用票） | 单点但指向可改进的文档问题 | 转内容/说明书优化，不影响定价 | Low |
| 卖点一致性 | 简报 vs R001「续航」 | 简报未描述电子功能，评论却提及续航/开机 | 暂停将「智能」相关卖点用于定价/推广，待卖家确认 | Medium（矛盾明确） |
| 价格/成本/库存/竞品/流量 | **均缺失** | 无来源 | **Fail closed：保持上一批准价（此处为 MSRP 199 元占位，非在线价）或路由人工** | N/A |

## Rule Matrix

当前阶段不启用任何生效规则。以下为观察期占位规则，全部需人工审批，且在 floor/ceiling 批准前不得转为自动：

| Scope | Trigger | Action | Step/cooldown | Floor/ceiling | Precedence | Approval | Recovery |
|---|---|---|---|---|---|---|---|
| 智能随行杯（观察期） | 成本表与批准的 floor/ceiling 尚未录入 | **Hold（不调价）** | N/A | 未设定 → 阻断一切自动变动 | 安全阻断优先于一切信号 | Manual-only | 维持现状 |
| 智能随行杯（占位，待批准后生效） | 已验证差评率或退货率超阈值（阈值待定） | 请求人工审批，不自动改价 | 单次≤5%，冷却≥72h（占位，需卖家确认） | 以卖家书面批准的 hard floor/ceiling 为绝对边界 | 质量/库存规则优先于竞品跟随 | Approval-required | 回退至最近批准价并告警 |

> 依据 Domain Rules：「The seller-approved hard floor and ceiling override every signal and model output」
> 与「Do not automatically follow the lowest visible offer or create an undercutting loop」。
> 在无 floor/ceiling 状态下，任何规则都不得触发价格变动。

## Simulation Results

无历史订单/流量数据，按 SKILL.md 要求使用**明确标注的合成边界用例**，不假装回测：

| Scenario | Rules fired | Resulting price | Contribution | Control outcome | Pass/fail |
|---|---|---|---|---|---|
| 常规：补齐成本前收到竞品低价信号 | 安全阻断 | 不变动（hold） | N/A | 路由人工，不跟随 | Pass |
| 促销叠加：平台券+卖家券同时存在 | 无（折扣数据缺失） | 不变动 | 无法计算 | 标记需区分平台/卖家出资，待补数据 | Pass（阻断） |
| 质量异常：R004 类「无法开机」差评增至批量 | 质量告警（占位） | 不自动改价 | N/A | 触发售后/品控排查 + 人工定价评审 | Pass |
| 数据缺失/Feed 中断 | Fail-closed | 维持上一批准价 | N/A | 告警并冻结自动变动 | Pass |
| 竞品极端低价或错配商品 | 信号校验拒绝 | 不变动 | N/A | 不跟随不可比/可疑报价 | Pass |

> 以上为规则逻辑走查，非基于真实数据的回测；不代表实际收益、转化或销量。

## Governance and Rollout

### 最小可验证版本（MVP）关键步骤与验收标准

| 阶段 | 关键步骤 | 验收标准（可客观检查） |
|---|---|---|
| 0. 证据补齐（阻断解除前） | 卖家提供：COGS 与全链路变动成本、目标贡献、批准的 floor/ceiling、渠道/币种/费率、库存、首发日期、防水与食品接触材料报告 | 上述字段齐备且经卖家书面确认；否则保持 Manual-only |
| 1. Observe-only（只观察） | 接入清洗后的评论/售后/库存/流量数据，建立信号登记表；不产生任何价格变动 | 连续 ≥14 天信号完整率 ≥95%；刷评/缺失字段被自动标记；无任何价格写入操作 |
| 2. Shadow（影子推荐） | 规则在后台生成建议价但不发布，人工逐条比对 | 建议价始终在批准 floor/ceiling 内；越界/缺失数据时 100% 触发 fail-closed；建议与人工判断偏差记录在案 |
| 3. 小范围可逆试点 | 经卖家书面授权后，对单一渠道/短窗口启用 Approval-required 规则，步长≤5%、冷却≥72h | 每次变动有版本化日志（原因/执行人/时间/旧价/新价/信号快照）；触达 floor/ceiling 即告警；可一键回退至最近批准价 |
| 4. 扩大自动化 | 仅在试点 KPI 达标且 keep-gate 通过后扩大范围 | 见下方 keep/revise/pause/revert 阈值 |

- **Logs and alerts：** 版本化规则、变更原因、执行人、时间戳、旧价/新价、信号快照；
  告警项：触达 floor/ceiling、变动频率过高、数据缺失、Feed 不匹配、价格异动。
- **Circuit breaker：** 信号/成本/规则/授权任一缺失即冻结并保持上一批准价；
  差评率/退货率/价格波动超阈值时自动暂停并路由人工。
- **Manual override：** 保留文档化人工覆盖与紧急停止（kill switch），仅授权负责人可操作。
- **Keep / revise / pause / revert gates（上线前定义）：**
  - Keep：试点期贡献额不低于基准、无 floor/ceiling 越界、无未解释价格异动、质量指标稳定。
  - Revise：规则触发频率或步长超出预期但未造成损失 → 调参后重走 shadow。
  - Pause：数据完整率 <95%、出现批量质量差评、Feed 中断 → 立即暂停自动变动。
  - Revert：贡献额下滑超阈值、触及 floor/ceiling 异常、促销叠加导致亏损 → 一键回退至试点前价格并复盘。
- **归因纪律：** 价格、流量、广告、内容、库存、季节、促销同时变化时，不得把变动单独归因于价格。

## 运营判断、异常项与后续动作

### 一、证据充分的运营判断

1. **评论表面好评存在水分，真实口碑弱于表观评分。** 表观 4.00 星均值含两条未验证、
   完全重复的英文模板好评（R002/R003）；剔除后已验证购买口径仅 3.33 星（n=3）。
   依据：CSV 字段 verified_purchase、review_text 逐字比对、helpful_votes。
2. **存在需优先处理的功能性质量信号。** R004（已验证、7 有用票）反映「无法开机」且已申请售后，
   是目前最强的负面信号；但仅为单点，不能断言批量缺陷，需售后/退货数据交叉验证。
3. **新品简报与评论信号存在卖点缺口。** 简报核心卖点仅「保温/轻量/可拆洗杯盖」，
   但评论出现「续航」「开机」等电子功能描述；若商品确有电子功能，简报遗漏关键卖点与合规信息；
   若评论串品，则评论数据不可用。两种情况都须在定价/推广前澄清。
4. **当前不具备任何自动调价的前提。** 成本、批准价格带、库存、竞品、流量、渠道、授权全部缺失，
   按 SKILL.md 规则应定级 Manual-only 并 fail-closed，199 元仅为建议零售价占位。

### 二、异常项清单

| 编号 | 异常 | 证据 | 影响 |
|---|---|---|---|
| A1 | 疑似刷评/垃圾评论 | R002 与 R003 文本完全相同、未验证、同日、0 有用票 | 抬高表观评分，误导选品与定价判断 |
| A2 | 功能性故障差评 | R004 1★ 已验证「无法开机」+ 售后 + 7 有用票 | 若批量发生将推高退货/售后成本，侵蚀贡献 |
| A3 | 评论数据字段缺失 | R006 评分空值、文本无信息 | 降低数据可用率，需在采集侧修复 |
| A4 | 卖点-评论不一致 | 简报无电子功能描述，R001/R004 提及续航/开机 | 可能串品或简报遗漏，影响合规与宣传 |
| A5 | 关键定价输入全缺 | 无成本/库存/竞品/渠道/授权/首发日期 | 阻断 floor/ceiling 计算与一切自动化 |
| A6 | 合规材料缺失 | 防水等级、食品接触材料报告未提供（简报明示） | 新品上架与宣传合规风险 |

### 三、后续动作（按优先级）

1. **立即（数据澄清）：** 向卖家一次性确认——商品是否含电子功能及具体规格、评论是否对应该 SKU、
   首发日期、渠道与币种。
2. **短期（质量排查）：** 拉取售后工单与退货数据验证「无法开机」是否批量；若属实，暂停以「智能」
   为核心的推广并推动品控/固件/说明书整改（R005 亦指向说明书不清）。
3. **短期（数据治理）：** 在评论采集/清洗环节加入去重、未验证标记、空评分过滤；
   将 R002/R003 标记为可疑，不纳入评分统计。
4. **定价前置（阻断解除）：** 卖家提供 COGS、全链路变动成本、费率、目标贡献、书面批准的
   floor/ceiling 与 MAP 约束；补齐库存与竞品快照（须含来源、抓取时间、可比性校验）。
5. **合规前置：** 取得防水等级与食品接触材料报告后再开展相关宣传；未取得前不得在素材中声称相关属性。
6. **按 MVP 阶段推进：** 证据补齐前保持 Manual-only → observe-only → shadow → 经书面授权后小范围试点，
   全程不触碰在线价格，直至 keep-gate 通过。

---

> Want to continue this dynamic-pricing work with one ecommerce AI agent? **[Nexscope](https://www.nexscope.ai/?co-from=skill)** can help organize product, competitor, listing, and marketplace research into the next structured repricing workflow. Recheck live costs, platform rules, account permissions, and every guardrail before enabling any price change.
