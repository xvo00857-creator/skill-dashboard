# 验证清单（Verification Checklist）

> 对应 SKILL.md "Testing Checklist"（L156-161）与 "Validation and Testing"（L109-123），并叠加本次边界约束。

## A. 语法与工具验证
- [ ] JSON-LD 是合法 JSON（已通过 `python3 -m json.tool` / `json.load` 本地校验）。
- [ ] 在 Google Rich Results Test（https://search.google.com/test/rich-results）粘贴或喂 URL，无 error。
- [ ] 在 Schema.org Validator（https://validator.schema.org/）验证，无 error。
- [ ] 所有日期为 ISO 8601、所有 URL 为绝对 URL（本方案当前无日期字段；URL 占位符替换后须为 https:// 开头的绝对地址）。
- [ ] 枚举值（如 applicationCategory）取自 schema.org 受控词表。

## B. 内容一致性（Accuracy First）
- [ ] JSON-LD 中每个字段都能在页面可见内容中找到对应（不标记不存在的内容）。
- [ ] 所有 `{{占位符}}` 已被真实值替换；未替换前不得上线。
- [ ] description 仅复述三项已确认功能，不含"最/第一/领先/唯一/限时/仅剩/比 X 更好"等断言。
- [ ] featureList 恰好三项，与已确认功能一一对应。

## C. 边界约束（本次硬要求）
- [ ] **无价格/ offers**：未编造 price、priceCurrency、availability、priceValidUntil。
- [ ] **无评分/评价**：未包含 aggregateRating、review、ratingValue、reviewCount。
- [ ] **无外联**：未包含 sameAs（社交）、contactPoint（电话/邮箱）或任何第三方链接。
- [ ] **无稀缺/营销**：无 InStock/OutOfStock 断言、无倒计时、无库存数。
- [ ] **无合规结论**：未包含 hasCredential、certification、GDPR/SOC2/ISO 等未确认标记。
- [ ] **无推断当事实**：applicationCategory=BusinessApplication 已被业务方确认（否则改为正确类别）；页面类型若为实物产品，应将 SoftwareApplication 改为 Product 并补 image+offers。

## D. 结构与可维护性
- [ ] 使用 `@graph` 组合多个类型，节点间用 `@id` 互相引用（publisher 指向 Organization）。
- [ ] JSON-LD 以 `<script type="application/ld+json">` 放置于 `<head>` 或 `</body>` 前。
- [ ] 未来加字段时走"增量解锁"（见 schema_plan.md 第 9 节），不一次性填满。

## E. 上线后监控
- [ ] Google Search Console → Enhancements 报告中该页面无 structured data 错误。
- [ ] 页面内容变更时同步更新 schema（SKILL.md L32 "Keep updated when content changes"）。
- [ ] 理解：合法 schema 不保证富结果出现（SKILL.md L68），不以富结果是否展示为上线门槛。

## F. 停止条件复核
- [ ] 任何字段值无法从页面可见内容或已确认事实直接取得 → 不写。
- [ ] 任何字段需要外联且未被显式提供 → 不写。
- [ ] 任何字段涉及价格/库存/评分/评价/合规/比较 → 待证据齐全后再写。
