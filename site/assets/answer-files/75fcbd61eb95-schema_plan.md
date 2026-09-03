# 结构化数据规划 — 边界与复杂场景

## 1. 目标
为一个"仅有产品名称 + 三项已确认功能"的产品网页规划 JSON-LD 结构化数据，在不编造、不外联、不制造稀缺、不把推断当事实的前提下，给出当前信息下可安全上线的最小标记集合与停止条件。

## 2. 依据（来自 SKILL.md 的硬约束）
- **Accuracy First**：Schema 必须准确反映页面可见内容；不要标记页面上不存在的内容（SKILL.md L29-32）。
- **Use JSON-LD**：Google 推荐格式，放 `<head>` 或 `</body>` 前（L34-37）。
- **Follow Google's Guidelines**：只用 Google 支持的标记；避免 spam；检查资格要求（L39-42）。
- **Validate Everything**：上线前用 Rich Results Test / Schema.org Validator 验证（L44-47, L111-114）。
- **Product 必需字段**：name、image、offers（price + availability）（L81-82）。
- **SoftwareApplication 必需字段**：name、offers（L59）。
- **多类型用 @graph 组合**（L92-105）。

## 3. 信息分类（事实 / 推断 / 待确认）

### 事实（题目明确给出）
- 存在一个产品网页，有产品名称。
- 该产品有三项已确认功能。
- 缺少：转化率数据、竞品信息、客户评价、合规结论。
- 约束：不得制造虚假稀缺、不得自动外联、不得把推断写成事实。

### 推断（基于场景的合理判断，但非题目明说，需标注为推断）
- 该页面大概率是 SaaS / 软件产品落地页（因为有"功能"而无 SKU/物流）→ 推断，优先用 SoftwareApplication 而非实物 Product。
- 站点应有一个组织主体（公司/团队）→ 推断，Organization 标记需要主体名称与 URL 才能成立。
- 页面可能有面包屑导航 → 推断，BreadcrumbList 需真实导航结构。

### 待确认（缺失，不能编造，必须留占位或省略）
- 产品名称的具体字符串。
- 三项功能的具体文案。
- 产品/公司官网 URL。
- 公司/组织名称、Logo URL。
- 价格、币种、可获得性（offers）。
- 产品截图/图片 URL（image）。
- 真实客户评价与评分（AggregateRating / Review）。
- 合规/认证结论（不得放未确认的认证标记）。
- 社交媒体主页链接（sameAs）——"不得自动外联"直接禁止编造。
- 联系方式（contactPoint）——同上。
- 面包屑层级。

## 4. 冲突与风险识别

| 编号 | 冲突/风险 | 说明 | 处置 |
|---|---|---|---|
| R1 | Product/SoftwareApplication 的 Google 富结果资格要求 offers（价格），但价格缺失 | 若硬填价格→编造；若留空→该类型不具备富结果资格，但 schema.org 仍合法 | 保留 SoftwareApplication 但**不写 offers**，并明确标注"不申请价格富结果"；待价格确认后补 |
| R2 | image 是 Product 必需字段，但无产品图 | 编造 URL 违反 Accuracy First | 省略 Product/SoftwareApplication 的 image，或在拿到图 URL 前不声明该类型为富结果候选 |
| R3 | AggregateRating / Review 需要真实评价，而评价缺失 | 编造评分属于 spam，违反 Google 指南与题目约束 | **完全不包含** AggregateRating / Review |
| R4 | sameAs / contactPoint 涉及外联，题目禁止自动外联 | 编造社交链接/电话/邮箱即违规 | **完全省略** sameAs 与 contactPoint |
| R5 | 合规结论缺失 | 不能放"GDPR 合规""SOC2"等未确认认证 | 不包含任何认证/合规相关标记 |
| R6 | 转化率/竞品缺失 | 这些本身不属于结构化数据字段，但若在 description 里写"业界领先""比 X 更好"即把推断/营销话术写成事实 | description 只复述三项已确认功能，不做比较/第一/最/稀缺类断言 |
| R7 | 虚假稀缺 | 不得写"限时""仅剩 N 份""InStock 若不实" | 不写 availability / priceValidUntil / 倒计时类标记 |
| R8 | 把推断当事实 | 页面类型、组织主体均为推断 | JSON-LD 中所有值使用 `{{占位符}}`，并在注释/清单中标注"由页面方填入"；推断类型在本规划中明确标"推断" |

## 5. 最小可执行方案（当前信息下可安全上线）

**策略**：只标记"页面上必然存在且无需编造"的实体；对需要外部事实的字段一律留占位或省略；不追求富结果资格，先保证 schema.org 合法 + 不撒谎。

**纳入的类型**（@graph）：
1. `Organization` —— 仅 name + url（占位，由页面方填入）。**省略** logo/sameAs/contactPoint。
2. `WebSite` —— name + url（占位）。**省略** SearchAction（需要确认站内搜索 URL 模板）。
3. `SoftwareApplication` —— name + applicationCategory（推断为 BusinessApplication，需确认）+ description（仅复述三项已确认功能）。**省略** offers、image、aggregateRating、sameAs。

**明确不纳入**：Product（实物）、AggregateRating、Review、FAQPage（无 FAQ 内容）、HowTo（无教程）、BreadcrumbList（导航结构未确认）、Event、LocalBusiness、Offer/price/availability、任何认证标记。

## 6. 停止条件（Stop Conditions）
满足以下任一条即停止向 JSON-LD 加字段，转为"待确认"：
1. 字段值无法从题目事实或页面可见内容直接取得。
2. 字段需要外联 URL（社交、联系方式、第三方认证）且未被显式提供。
3. 字段涉及价格、库存、折扣、限时、评分、评价数、合规结论、竞品比较。
4. 该字段会让标记内容超出页面可见内容（Accuracy First）。
5. 任一占位符未被替换前，不得在生产环境部署该块。

## 7. 步骤
1. 页面方确认并替换所有 `{{占位符}}`（产品名、三项功能、URL、组织名）。
2. 确认 applicationCategory 是否符合实际（BusinessApplication / DeveloperApplication / 其他）。
3. 将 JSON-LD 以 `<script type="application/ld+json">` 放入页面 `<head>` 或 `</body>` 前。
4. 用 Google Rich Results Test（https://search.google.com/test/rich-results）与 Schema.org Validator（https://validator.schema.org/）验证。
5. 上线后在 Google Search Console 的 Enhancements 报告中监控。
6. 后续拿到价格/图片/评价后，按"增量"追加字段（见第 9 节）。

## 8. 关键取舍
- **选 SoftwareApplication 而非 Product**：场景是"功能"而非 SKU/物流，属推断但更贴近；若实际是实物产品，应改回 Product 并补 image+offers。
- **放弃富结果资格换取真实性**：没有 offers/image 就不申请价格/评分富结果，但 schema.org 本身合法，仍有助于搜索引擎理解实体。
- **省略 sameAs/contactPoint 而非留空数组**：空数组/空串虽不报错，但"自动外联"约束下宁可完全省略，避免被理解为已确认无外联渠道。
- **description 只写三句话**：每句对应一项已确认功能，不写营销形容词、不写比较、不写稀缺。

## 9. 下一步（增量解锁条件）
| 待确认项 | 解锁后可追加的字段/类型 |
|---|---|
| 官方产品图 URL | SoftwareApplication.image |
| 价格 + 币种 + 可获得性 | SoftwareApplication.offers（具备富结果资格） |
| 真实客户评价（≥1 条，可溯源） | Review；评价数足够后再加 AggregateRating |
| 站内搜索 URL 模板 | WebSite.potentialAction(SearchAction) |
| 真实社交主页 | Organization.sameAs |
| 客服电话/邮箱 | Organization.contactPoint |
| 面包屑导航 | BreadcrumbList |
| 合规认证（已签署/已颁发） | Organization.hasCredential 或相关认证字段（须有证据） |
| FAQ 内容上线 | FAQPage |

## 10. 衡量方式
- **结构合法**：Rich Results Test 与 Schema.org Validator 均无 error（warning 可接受，需逐条确认）。
- **内容一致**：JSON-LD 中每个字段都能在页面可见内容中找到对应；占位符 100% 被替换。
- **无编造**：检查清单第 4 节 R1–R8 全部通过。
- **上线后**：Search Console Enhancements 中该页面无 structured data 错误；富结果是否出现由 Google 决定，不作为上线门槛（SKILL.md L68 "valid schema doesn't guarantee rich results"）。
