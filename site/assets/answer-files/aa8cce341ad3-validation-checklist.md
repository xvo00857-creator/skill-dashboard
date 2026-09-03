# Schema 验证清单（按 SKILL.md "Validation and Testing" + "Testing Checklist" 执行）

## 一、部署前自检（本地）

- [x] JSON 语法合法（已用 `json.load()` 验证通过）
- [x] 使用 JSON-LD 格式（符合 SKILL.md "Use JSON-LD" 原则）
- [x] 多类型用 `@graph` 组合（符合 SKILL.md "Multiple Schema Types"）
- [x] 每个类型包含 SKILL.md 要求的 required properties：
  - Organization: name ✓, url ✓
  - WebSite: name ✓, url ✓
  - LocalBusiness: name ✓, address ✓
  - FAQPage: mainEntity ✓（含 Question/acceptedAnswer 嵌套）
- [x] 未编造 aggregateRating / review / offers 价格等不存在的数据（Accuracy First）
- [x] 所有占位符（【】标注）已标记，部署前必须替换为真实内容
- [x] 所有 URL 为完全限定 URL（ISO 8601 / 完全限定 URL 要求）

## 二、部署后在线验证（用免费工具，符合 8000 元预算约束）

- [ ] **Google Rich Results Test**（https://search.google.com/test/rich-results）
  - 输入页面 URL，确认 4 个 graph 节点均被识别
  - 确认无 Error；Warning 逐项确认是否可接受
  - 确认 FAQ rich result 合格
- [ ] **Schema.org Validator**（https://validator.schema.org/）
  - 确认无 schema.org 词汇错误
  - 确认 @id 引用关系正确（Organization ← WebSite.publisher / LocalBusiness.parentOrganization）
- [ ] **Google Search Console** → Enhancements 报告
  - 部署后 3-7 天检查是否有结构化数据错误
  - 确认 FAQ、LocalBusiness 类型被收录

## 三、内容一致性检查（Accuracy First）

- [ ] schema 中每个字段在页面可见内容中有对应
- [ ] FAQ 的问题和答案与页面上展示的 FAQ 完全一致
- [ ] 电话号码、地址、营业时间与实际一致
- [ ] 产品名称、logo URL 与页面实际一致
- [ ] 内容更新时同步更新 schema（SKILL.md "Keep updated when content changes"）

## 四、场景适配检查（本次变化场景特有）

- [ ] ContactPoint 包含真人电话号码（50+ 用户优先电话渠道）
- [ ] FAQ 覆盖目标用户核心疑虑（收费、安全、教学、下载、求助）
- [ ] LocalBusiness 标注线下社区服务点（主要触点之一）
- [ ] 未包含 SearchAction（目标用户不依赖站内搜索）
- [ ] 未包含 Product/SoftwareApplication offers（无真实价格/库存数据，不编造）
- [ ] 未包含 AggregateRating（无真实评价数据，不编造）
- [ ] 微信分享卡片（Open Graph / og:title, og:description, og:image）已另行配置——注意：Open Graph 非 schema.org 范畴，不在本 JSON-LD 内，但因微信是主要触点需单独检查

## 五、衡量方式

| 指标 | 工具/方法 | 通过标准 |
|------|-----------|----------|
| Schema 验证通过 | Rich Results Test | 0 Error |
| 搜索引擎识别 | Search Console Enhancements | 4 类均被收录，无严重错误 |
| 线下/微信引流用户找信息效率 | 客服电话中"网址是什么/地址在哪"类问题占比 | 上线后 2 周对比基线下降 |
| FAQ 自助解答率 | 页面 FAQ 区域点击/展开数据 | 有数据后评估 |

## 六、风险与限制（需知会）

1. **Schema ≠ 富结果保证**：Google 可选择不展示富结果（SKILL.md 明确说明 "valid schema doesn't guarantee rich results"）。
2. **目标用户搜索行为**：50+ 首次用智能手机用户可能不通过 Google 搜索到达，schema 的 SEO 引流价值有限；本方案核心价值是内容语义化和信任背书，而非搜索流量。
3. **微信内不渲染 schema 富结果**：微信内置浏览器不展示 Google 富结果，微信分享卡片依赖 Open Graph 标签，需单独实现。
4. **占位符未替换即部署会导致验证失败**：所有【】内容必须替换为真实数据后再上线。
5. **FAQ 内容必须真实**：Google 要求 FAQ 答案为事实性内容，非促销文案（SKILL.md evals 中 FAQ 用例强调 "factual answers, not promotional"）。
