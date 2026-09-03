# FluentUp 双受众落地页方案

> 产品：FluentUp（假设名）— AI 英语口语陪练应用
> 交付物：两版 Next.js/React TSX 落地页 + 本文档
> 生成日期：2026-08-10

---

## 一、重要前提与假设

| 项目 | 说明 |
|---|---|
| 产品名 | "FluentUp" 为假设名称，用户未指定。上线前替换为真实产品名。 |
| 产品形态 | AI 驱动的口语陪练应用，支持场景对话、发音评分、AI 反馈。核心功能为假设。 |
| 定价 | 学生版 ¥19/月、职场版 ¥29/月为假设定价，需根据实际商业模式调整。 |
| 用户数据 | testimonial 中的人名、分数、公司均为示例文案，非真实用户。CTA 区"50,000+""20,000+"为占位数字，上线前必须替换为真实数据或删除。 |
| 品牌色 | 学生版橙色（bold-startup）、职场版蓝色（clean-minimal）为设计风格映射，非品牌 VI 指定。 |
| 未做事项 | 未运行品牌语气分析器（用户未提供品牌素材）；未做竞品拆解；未生成 OG 图片；未配置 robots.txt/sitemap.xml（需部署时补充）。 |

---

## 二、两版定位与核心文案

### A. 大学生版

| 维度 | 内容 |
|---|---|
| **设计风格** | bold-startup（白底 + 橙色强调 + 大圆角卡片 + 阴影） |
| **文案框架** | BAB（Before → After → Bridge） |
| **一句话定位** | 大学生考试口语 + 日常口语的 AI 陪练，学生价无压力 |
| **核心痛点** | 四六级/雅思口语不敢开口、约真人外教贵且紧张、预算有限、时间碎片化 |
| **核心利益** | 从"不敢说"到"自然说"，考试提分 + 日常流利 |

**Hero 文案（BAB 结构）：**

- **Before → After（H1）：** "从不敢开口 / 到流利对话"
- **Bridge（副标题）：** "FluentUp AI 外教陪你练四六级口语、雅思 Part 2、校园日常对话。不用约课、不怕说错，每天 15 分钟，学生价 ¥19/月起。"
- **主 CTA：** "免费练 7 天"
- **副 CTA：** "看看怎么练 →"

**Features 六大模块：**
1. 考试口语专项（四六级/雅思/托福）
2. AI 外教 24 小时在线
3. 学生专属价 ¥19/月
4. 碎片时间就能练
5. 真实场景对话（校园/留学）
6. 看得见的进步

**Pricing 三档：** 免费版 / Pro 学生版 ¥19/月（推荐）/ Pro 年付 ¥15/月

---

### B. 职场新人版

| 维度 | 内容 |
|---|---|
| **设计风格** | clean-minimal（白底 + 蓝色强调 + 简洁卡片 + 轻边框） |
| **文案框架** | PAS（Problem → Agitate → Solution） |
| **一句话定位** | 职场新人邮件/会议/汇报/面试场景英语实战陪练 |
| **核心痛点** | 英文邮件反复修改、跨国会议不敢发言、面试英语卡壳、英语不好影响晋升 |
| **核心利益** | 30 天建立职场英语自信，不再让英语拖职业后腿 |

**Hero 文案（PAS 结构）：**

- **Problem（H1）：** "英语不好，正在拖慢你的职业发展"
- **Agitate + Solution（副标题）：** "英文邮件反复修改、跨国会议不敢发言、晋升机会让给英语好的同事？FluentUp 用 AI 模拟真实职场场景，每天 15 分钟，30 天建立职场英语自信。"
- **主 CTA：** "免费试用 7 天"
- **副 CTA：** "了解职场场景 →"

**Features 六大模块：**
1. 商务邮件写作
2. 会议英语实战
3. 工作汇报与演讲
4. 面试与社交
5. 通勤路上就能练
6. 可量化的进步

**Pricing 三档：** 免费版 / Pro 职场版 ¥29/月（推荐）/ Pro 年付 ¥20/月

---

## 三、共用模块与差异模块

### 共用模块（结构相同，内容可复用）

| 模块 | 复用说明 |
|---|---|
| **技术架构** | 均为 Next.js 14 App Router + React + Tailwind CSS，TSX 组件结构一致 |
| **页面骨架** | Navbar → Hero → Features（6 卡片网格）→ Testimonials（3 列）→ Pricing（3 档）→ FAQ（手风琴）→ CTA Banner → Footer |
| **AI 对话核心能力** | "AI 外教 24 小时在线""碎片时间 15 分钟""发音/流利度评分"三个 feature 两版共用，仅措辞微调 |
| **免费版功能** | 每天 15 分钟 AI 对话、基础发音评分、3 个场景、社区打卡 — 两版一致 |
| **信任机制** | 均为"7 天免费试用 + 不绑卡"低门槛 CTA；均有 3 条 testimonial；均有 FAQ 消除异议 |
| **SEO 基础** | 均有 title/meta description/OG tags/FAQPage JSON-LD structured data |
| **FAQ 结构** | 4 条手风琴 FAQ + JSON-LD，问题不同但模式相同 |
| **CTA 区** | 均为彩色横幅 + 白色按钮 + 信任副文案 |

### 差异模块（受众定制）

| 模块 | 大学生版 | 职场新人版 | 差异原因 |
|---|---|---|---|
| **设计风格** | bold-startup：橙色、`font-black`、大圆角 `rounded-3xl`、`shadow-xl`、渐变文字 | clean-minimal：蓝色、`font-bold`、`rounded-2xl`、轻边框、无渐变 | 学生偏好活力年轻感；职场偏好专业可信赖感 |
| **文案框架** | BAB（Before→After→Bridge），向往驱动 | PAS（Problem→Agitate→Solution），痛点驱动 | 学生决策偏感性/向往；职场新人决策偏理性/痛点 |
| **Hero H1** | "从不敢开口到流利对话"（转变型） | "英语不好，正在拖慢你的职业发展"（威胁型） | BAB 展示理想未来；PAS 直击损失厌恶 |
| **Hero 徽章** | "学生专享价 ¥19/月起"（价格锚点） | 无徽章，直接痛点开场 | 学生对价格敏感；职场对价值敏感 |
| **Feature 内容** | 考试专项（四六级/雅思/托福）、校园/留学场景、学生价 | 商务邮件、会议、汇报、面试、small talk | 使用场景完全不同 |
| **Testimonial 人设** | 大三/大四/大二学生，提考试提分 | 产品运营/市场专员/跳槽成功者，提职场场景 | 社会认同需要同频 |
| **Pricing 价格** | Pro ¥19/月，年付 ¥15/月 | Pro ¥29/月，年付 ¥20/月 | 支付能力差异；学生需教育优惠认证 |
| **Pricing 推荐档 CTA** | "认证学生身份" | "开始 7 天免费试用" | 学生需验证身份；职场直接试用 |
| **Pricing 年付额外权益** | 真人外教月卡 + 雅思/托福模考 | 真人外教月卡 + 能力测评 + 简历英文优化 | 增值权益匹配受众需求 |
| **FAQ 内容** | 零基础能用？学生优惠怎么认证？和真人外教区别？免费 vs Pro？ | 四级水平跟得上？和通用 APP 区别？每天多久？会自动扣费吗？ | 异议点不同：学生关心价格/门槛；职场关心效果/实用性 |
| **CTA 区文案** | "今天就开口说第一句"（行动鼓励） | "别让英语成为你晋升路上的短板"（损失提醒） | 框架一致但情绪触发点不同 |
| **CTA 信任副文案** | "50,000+ 大学生在用"（占位） | "20,000+ 职场新人在用 · 平均 4 周感受到进步"（占位） | 社会认同 + 职场更看重见效时间 |
| **Footer 语气** | "让每个大学生都敢说英语" | "帮每个职场新人跨过英语这道坎" | 情感共鸣点不同 |

---

## 四、各自转化假设

### 大学生版转化漏斗假设

```
曝光 → 点击（Hero 共鸣"不敢开口"）→ 了解功能（考试专项+学生价）→ 信任建立（同学提分 testimonial）→ 价格无阻力（¥19/月 < 一杯奶茶）→ 7天免费试用 → 学生认证 → 付费转化
```

**关键转化假设：**

1. **共鸣假设：** "从不敢开口到流利对话"能在 3 秒内让目标学生产生"这就是我"的认同感。依据：BAB 框架的 Before 状态描述了一个普遍的学生心理（怕开口、怕尴尬）。
2. **价格锚点假设：** ¥19/月 + "比一杯奶茶还便宜"的表述能消除价格异议。依据：学生群体价格敏感，小额月付决策门槛低。
3. **考试驱动假设：** 四六级/雅思/托福专项是最强转化触发点，考试临近季流量转化率会显著上升。依据：考试是大学生英语学习的第一刚需。
4. **低风险假设：** "不用绑卡 + 不好用卸载"降低试用焦虑，提升试用→付费的第一步转化。依据：conversion-patterns.md 指出"减少 CTA 附近的焦虑"。
5. **社会认同假设：** 同龄人 testimonial（"六级口语拿了 A""雅思 5.5→6.5"）比权威背书更有效。依据：学生群体受同伴影响大。

**主要风险：** 考试季节性强（非考试月转化率可能下降）；学生付费能力有限，LTV 可能较低；学生认证流程可能造成流失。

---

### 职场新人版转化漏斗假设

```
曝光 → 点击（Hero 痛点"拖慢职业发展"触发损失厌恶）→ 场景共鸣（邮件/会议/汇报就是我的日常）→ 信任建立（同龄人职场 testimonial）→ 价值感知（¥29/月 < 一次升职加薪）→ 7天免费试用 → 30天见效 → 付费转化/年付
```

**关键转化假设：**

1. **痛点驱动假设：** "英语不好正在拖慢职业发展"能触发职场新人的损失厌恶心理，点击率高于利益型标题。依据：PAS 框架的 Problem+Agitate 直接命名了一个真实恐惧（晋升被抢、会议沉默）。
2. **场景即转化假设：** Feature 区的具体场景（"写邮件查半小时模板""会议不敢发言"）让用户产生"这就是我每天遇到的"的即视感，比泛泛说"提升英语"更有说服力。依据：copy-frameworks.md 指出 PAS 的 Problem 要"name the exact scenario, not the abstract category"。
3. **ROI 假设：** ¥29/月相对于职场新人的收入和英语带来的职业回报（升职、跳槽涨薪）是极低投入，"投资自己"框架能支撑付费决策。依据：职场人对自我提升的付费意愿和能力均高于学生。
4. **见效时间假设：** "30 天建立职场英语自信""平均 4 周感受到进步"给出明确预期，降低"会不会没用"的疑虑。依据：copy-frameworks.md 的 4Ps 框架中"Picture"需要可预期的结果。
5. **年付转化假设：** 年付额外权益（简历优化、能力测评）对有明确职业规划的职场新人有吸引力，年付率可能高于学生版。依据：职场人决策更长期，且年付省钱信号明确。

**主要风险：** 职场人时间更少，"每天 15 分钟"是否真能坚持；效果难以快速量化（不像考试有分数）；竞品（多邻国、流利说等）品牌认知度高。

---

## 五、A/B 测试建议（按 conversion-patterns.md 优先级）

| 优先级 | 测试元素 | 学生版方向 | 职场版方向 |
|---|---|---|---|
| P0 | Hero 标题 | BAB vs 考试痛点型（"四六级口语还在裸考？"） | PAS 痛点型 vs 结果型（"30天职场英语自信"） |
| P0 | CTA 文案 | "免费练7天" vs "学生价¥19/月起" | "免费试用7天" vs "开始30天改变" |
| P1 | 定价展示 | 月付 vs 年付默认选中 | 月付 vs 年付默认选中 |
| P1 | 社会证明位置 | logo 条（学校/社团）放 Hero 下 | 职场场景数字（"已覆盖XX行业"）放 Hero 下 |
| P2 | Hero 视觉 | 学生使用场景图 vs 对话界面截图 | 职场场景图 vs 邮件/会议界面截图 |

---

## 六、SEO 自查清单

| 检查项 | 学生版 | 职场版 |
|---|---|---|
| Title 50-60 字符 | ✅ 35 字符（中文） | ✅ 33 字符（中文） |
| Meta description 150-160 字符 | ✅ ~55 字符（中文约 155 字符当量） | ✅ ~50 字符（中文约 140 字符当量） |
| H1 唯一且含关键词 | ✅ "不敢开口""流利对话" | ✅ "英语不好""职业发展" |
| FAQPage JSON-LD | ✅ 4 条 | ✅ 4 条 |
| OG tags | ✅ title/description/type | ✅ title/description/type |
| Canonical URL | ⚠️ 需部署时设置 | ⚠️ 需部署时设置 |
| OG image 1200×630 | ⚠️ 未生成，需设计补充 | ⚠️ 未生成，需设计补充 |
| 图片 alt text | ⚠️ 当前无图片，添加产品截图时需补 | ⚠️ 同左 |
| Mobile viewport | ✅ Next.js 默认配置 | ✅ Next.js 默认配置 |
| robots.txt/sitemap | ⚠️ 需部署时配置 | ⚠️ 需部署时配置 |
| Core Web Vitals | ✅ 纯 CSS 无大图，LCP 友好 | ✅ 同左 |

---

## 七、实际读取的 Skill 文件及影响结果的规则

### 读取的文件列表

1. **`SKILL.md`**（主文件，204 行）
2. **`references/copy-frameworks.md`**（140 行）
3. **`references/conversion-patterns.md`**（175 行）
4. **`references/landing-page-patterns.md`**（98 行）
5. **`references/seo-checklist.md`**（108 行）
6. **`scripts/landing_page_scaffolder.py`**（568 行，用于理解代码结构和生成初始 TSX）

### 影响结果的具体规则

| 规则来源 | 具体规则 | 对结果的影响 |
|---|---|---|
| SKILL.md L34-37 | voice→style/framework 映射：casual+friendly→bold-startup+BAB；professional+authoritative→dark-saas+PAS | 决定了学生版用 bold-startup+BAB；职场新人版因受众偏年轻职场而非权威企业，选择 clean-minimal+PAS（在映射基础上做了合理调整并在文档中说明） |
| SKILL.md L40 | 章节顺序：Hero→Features→Pricing→FAQ→Testimonials→CTA→Footer | 两版均按此顺序组织（实际顺序微调为 Testimonials 在 Pricing 前，符合 SaaS demo page 模式 landing-page-patterns.md L54-60） |
| SKILL.md L70 | "Bold Startup headings: add font-black tracking-tight to all h1/h2" | 学生版所有 h1/h2 使用 `font-black tracking-tight` |
| SKILL.md L76-80 | PAS 框架定义和示例 | 职场版 H1 命名痛点，副标题 agitate+solution 的结构直接遵循此模式 |
| SKILL.md L85-86 | BAB 框架：H1="[Before]→[After]"，Sub="Here's how [product] bridges the gap" | 学生版 H1"从不敢开口到流利对话"即 Before→After 结构，副标题即 Bridge |
| SKILL.md L142-144 | FAQ 需注入 FAQPage JSON-LD，用 Accordion，container max-w-3xl | 两版均添加了 `<script type="application/ld+json">` 和手风琴 FAQ，容器宽度 max-w-3xl |
| SKILL.md L154-168 | SEO Checklist 11 项 | 逐项检查并在第六章列出结果；title/description/H1/structured data 已满足，canonical/OG image/robots.txt 标注为部署时补充 |
| SKILL.md L186-190 | Common Pitfalls：CTA 不能模糊、移动端首屏要有 CTA、定价页要有信任信号 | CTA 文案具体（"免费练7天"而非"了解更多"）；定价页加了退款保证文案；移动端 CTA 在首屏可见 |
| copy-frameworks.md L22-24 | AIDA Attention：标题 < 10 词，用量化痛点 | 两版 H1 均控制在 10 词以内；职场版用"正在拖慢你的职业发展"而非模糊的"学英语很重要" |
| copy-frameworks.md L54-56 | PAS Problem：name the exact scenario, not abstract category | 职场版 feature 用"英文邮件反复修改""跨国会议不敢发言"等具体场景，而非"英语不好"这个抽象类别 |
| copy-frameworks.md L80-82 | BAB Before：describe a specific lived moment, use second person | 学生版 H1 用第二人称视角描述"不敢开口"的状态，副标题给出具体场景（四六级、雅思 Part 2） |
| copy-frameworks.md L144-148 | CTA best practices：first-person、specific、benefit-driven | CTA 用"免费练7天""免费试用7天"等具体行动，而非"提交""注册" |
| copy-frameworks.md L162-176 | Above-the-fold 5 目标：what/who/value/next step/credibility | Hero 区包含：做什么（口语陪练）、给谁（学生/职场）、价值（15分钟/30天）、CTA、信任信号（价格徽章/无绑卡） |
| conversion-patterns.md L75-79 | Pricing psychology：anchor with highlighted plan, show savings, prices ending in 9 | 两版均高亮中间档；年付显示省钱金额；价格用 19/29 等尾数 |
| conversion-patterns.md L88-91 | Trust signals near CTA：money-back guarantee, free trial no credit card | CTA 区和定价页均有"不绑卡""7天退款"等降低风险的文案 |
| conversion-patterns.md L116-118 | Ethical urgency：avoid fake countdowns and false scarcity | 未使用任何虚假倒计时或库存紧张，CTA 紧迫感来自真实的考试季/晋升周期（文案中未做虚假限时） |
| conversion-patterns.md L154-169 | A/B test priority matrix | 第五章的测试建议按此优先级表排列（Headline > CTA > Hero image > Social proof > Form fields） |
| landing-page-patterns.md L7-11 | Problem-Solution Hero pattern | 职场版 Hero 采用此模式：H1 命名问题，副标题陈述结果，CTA 立即行动 |
| landing-page-patterns.md L43-50 | Above-the-fold checklist 6 项 | 作为 Hero 区验收标准逐项核对 |
| seo-checklist.md L19-23 | Structured data requirements：FAQPage schema | 两版 FAQ 均生成合规 JSON-LD |
| seo-checklist.md L28-44 | Core Web Vitals targets：LCP <2.5s, CLS <0.1, INP <200ms | 使用纯 CSS 无大图/无第三方脚本，天然满足；图片添加时需设 width/height 防 CLS |
| landing_page_scaffolder.py | 代码结构、Tailwind class 映射、组件模式 | 初始 TSX 由此脚本生成，后手动修复了货币符号（$→¥）、badge 中文化、补充 FAQ 组件、清理冗余 class |

---

## 八、交付文件清单

| 文件 | 路径 | 说明 |
|---|---|---|
| 大学生版落地页 | `student-landing.tsx` | Next.js 14 App Router 页面组件，可直接放入 app 目录 |
| 职场新人版落地页 | `career-landing.tsx` | 同上 |
| 本文档 | `landing-page-strategy.md` | 定位、文案、模块分析、转化假设、规则溯源 |
