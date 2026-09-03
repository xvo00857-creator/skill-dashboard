# 某竞品 — 有限画像（受限版 / Limited Profile）

**URL**: 未提供（用户描述为"某竞品"，官网无法访问）
**Generated**: 2026-08-10
**Depth**: quick scan（受限于源不可达，实际退化为"源不可达下的框架画像"）
**状态**: ⛔ 阻塞 — 竞品身份未具名，一手源（官网）不可达，二手源互相冲突。本文件不补造任何事实，仅给出证据矩阵、信息缺口与待核验问题。

---

## 0. 执行前置说明（为什么是"有限画像"）

按 `SKILL.md` 的 Initial Assessment，画像前必须确认：(1) 竞品 URL；(2) 己方产品；(3) 深度；(4) 聚焦维度。本轮输入只给出了"某竞品官网无法访问且二手资料互相冲突"这一约束，**未提供可识别的竞品 URL / 公司名 / 产品名**，项目目录下也不存在 `.agents/product-marketing.md`、`.claude/product-marketing.md` 或 `product-marketing-context.md` 等上下文文件。

同时，本环境未挂载 Skill 中引用的 Firecrawl / DataForSEO MCP 工具（`firecrawl_map`、`firecrawl_scrape`、`backlinks_summary`、`dataforseo_labs_*` 等），即便给出 URL，Phase 1 / Phase 2 也只能退化为 `general_search` + `web.fetch` 的公开网页抓取，且用户已声明官网不可达。

依据 Skill 核心原则 **#1 Facts Over Opinions**（每条主张可溯源）、**#4 Honest Assessment**（不夸大不贬低），以及用户明确要求"不得补造"，本画像**不填充任何无法溯源的字段值**；所有维度以证据矩阵形式列出，未获取项一律标注置信度 D / X，并给出后续核验问题。

---

## 1. 证据矩阵（Evidence Matrix）

**置信度分级**（本画像自定义，对齐 Skill "Facts Over Opinions" 与"交叉验证"要求）：

| 等级 | 含义 | 可作为结论引用？ |
|------|------|------------------|
| **A 已核实** | 一手源直接观察 / 多源一致且无冲突 | 可 |
| **B 较可信** | ≥2 个独立二手源一致，无反向证据 | 可，需注明来源 |
| **C 存疑** | 单一二手源，或多源冲突未裁决 | 不可，仅作线索 |
| **D 不可验证** | 无可达源 / 源被屏蔽 / 目标未识别 | 不可，仅列缺口 |
| **X 禁止补造** | 无任何来源，禁止写入画像正文 | 不可，仅出现在缺口表 |

| # | 维度（对应 Skill 模板章节） | 主张 / 取值 | 来源 | 置信度 | 是否存在冲突 | 备注 |
|---|----------------------------|-------------|------|--------|--------------|------|
| 1 | 竞品身份（URL / 公司名 / 产品名） | — | 用户输入仅"某竞品" | **D** | 无法判断 | 最上游阻塞项，未识别则所有下游字段不可溯源 |
| 2 | At a Glance — Tagline | — | 官网不可达 | **D** | 二手源若有 slogan 可能互相不一致 | 需官网首页或权威媒体直引 |
| 3 | At a Glance — Founded（成立年份） | — | 未检索（无目标） | **D** | 常见冲突点：工商注册年 vs 产品上线年 vs 品牌启用年 | 需明确口径 |
| 4 | At a Glance — Headquarters | — | 未检索 | **D** | 常见冲突点：注册地 vs 实际办公地 vs 母公司所在地 | 需工商/官网 About 页 |
| 5 | At a Glance — Team size | — | 未检索 | **D** | LinkedIn 抓取数与官方口径常差 2–5 倍 | 需以官方或最新融资公告为准 |
| 6 | At a Glance — Funding | — | 未检索 | **D** | 融资金额/轮次在 Crunchbase、IT 桔子、新闻稿间常不一致 | 需以领投方公告或监管文件为准 |
| 7 | At a Glance — Domain rank | — | DataForSEO 不可用；无域名无法跑 | **D** | — | 需域名 + DataForSEO 或同类工具 |
| 8 | At a Glance — Est. organic traffic | — | 同上 | **D** | SimilarWeb / Semrush / Ahrefs 三家估算常差 30%–200% | 若用二手估算需并列三家数值 |
| 9 | At a Glance — Referring domains | — | 同上 | **D** | Majestic / Ahrefs / Moz 口径不同 | 需注明工具与抓取日期 |
| 10 | At a Glance — Organic keywords | — | 同上 | **D** | 同上 | 同上 |
| 11 | Positioning — Primary value prop | — | 官网不可达 | **D** | 二手解读类文章会带作者立场，非官方原文 | 需首页 H1 + 副标题原文 |
| 12 | Positioning — Target audience | — | 未检索 | **C/D** | 二手资料可能将"实际客户"与"宣称受众"混为一谈 | 需结合定价页、客户页、案例三方判断 |
| 13 | Positioning — Positioning angle | — | 未检索 | **D** | 媒体定性（如"企业级"/"SMB 自助"）可能互相矛盾 | 需以官网导航结构 + 定价分层佐证 |
| 14 | Product — Core capabilities | — | 官网 / Features 页不可达 | **D** | 二手功能清单可能滞后于当前版本 | 需 Features 页或 Changelog 原文 |
| 15 | Product — Notable differentiators | — | 未检索 | **D** | 竞品自评 vs 评测媒体观点常冲突 | 需标注"自述"还是"第三方观察" |
| 16 | Product — Integrations | — | Integrations 页不可达 | **D** | 集成目录页数量 vs 实际可用集成常不一致 | 需目录页抓取日期 |
| 17 | Product — Product direction signals | — | Changelog 不可达 | **D** | 二手"路线图解读"属推测 | 需官方 Changelog / 发布博客 |
| 18 | Pricing — Tiers / Prices | — | Pricing 页不可达 | **D** | **高冲突区**：第三方汇总站（如 G2、Capterra 附带的价格）常滞后；货币、年付折扣、是否含席位费口径不一 | 需定价页原文 + 抓取日期 + 年付/月付分列 |
| 19 | Pricing — Billing / Free trial | — | 同上 | **D** | 免费试用时长、是否需信用卡在不同落地页可能不同 | 需注册流程实测 |
| 20 | Customers — Named customers / logos | — | Customers 页不可达 | **D** | 依 Skill evals #6：logo 墙是定位主张，非客户结构证明；需案例/新闻稿/评测交叉验证 | 区分"具名可核实客户"与"行业覆盖宣称" |
| 21 | Customers — Industries | — | 未检索 | **D** | 同上 | 需案例页统计 |
| 22 | Customers — G2 / Capterra 评分 | — | 未检索 | **C/D** | **高冲突区**：评分随样本量变化；不同平台评分口径不同；刷分风险 | 需并列 G2、Capterra、TrustRadius、Product Hunt 各自评分+评论数+抓取日期 |
| 23 | SEO — Top organic pages | — | DataForSEO 不可用 | **D** | SimilarWeb / Semrush 给出的 Top 页可能不同 | 需注明工具与时间窗 |
| 24 | SEO — Content strategy signals | — | Blog 顶层页不可达 | **D** | 二手"内容策略分析"属推断 | 需博客首页 + 近 90 天发布频率统计 |
| 25 | SEO — Backlink profile | — | DataForSEO / Majestic 不可用 | **D** | 各工具 referring domains 数值差异大 | 需并列工具名 + 抓取日期 |
| 26 | Strengths & Weaknesses | — | 无一手源不可下结论 | **X** | 任何"强项/弱项"在无溯源情况下属补造 | 本画像**不输出** SWOT，仅在核验问题中列出待证项 |
| 27 | Competitive Implications（对己方） | — | 己方产品上下文缺失 | **X** | 无己方产品信息无法对比 | 需先提供己方产品定位/定价/客群 |

---

## 2. 信息缺口（Information Gaps）

按"阻塞强度"排序，前 3 项不解决则整份画像无法升级到 B 级以上。

### 🔴 一级阻塞（不解决无法继续）
1. **竞品身份未具名**：无 URL、无公司名、无产品名。所有检索、抓取、SEO 查询均无锚点。
2. **一手源（官网）不可达**：无法验证 tagline、定价、功能、客户、集成、Changelog 等所有"自述类"字段。需确认是域名失效、区域屏蔽、JS 渲染拦截还是临时宕机。
3. **己方产品上下文缺失**：无 `.agents/product-marketing.md` 等文件，无法完成 Skill 模板中的 "Competitive Implications for [Your Product]" 章节。

### 🟡 二级缺口（影响置信度但可部分推进）
4. 二手源具体清单未知：用户称"二手资料互相冲突"，但未给出具体来源（媒体名、报告名、URL）。无法执行"冲突并列"。
5. SEO / 域名权威类工具在本环境不可用（Firecrawl、DataForSEO MCP 未挂载）。即便有域名，也只能用 `general_search` / `web.fetch` 抓公开页面，拿不到 domain_rank、estimated traffic、referring domains 等结构化指标。
6. 时间窗未定义：未说明画像用于什么时间点的决策（当前 vs 历史回溯）。Skill 强调"Profiles are snapshots"，需明确"as of"日期。
7. 深度未确认：Skill 默认 quick scan（≤3 家竞品时可 deep）；当前只有 1 家，理论上可 deep，但受限于源不可达，deep 也无法执行。

### 🟢 三级缺口（可在拿到目标后补齐）
8. 评测评台（G2 / Capterra / TrustRadius / Product Hunt）上的对应条目 URL。
9. 工商 / 融资数据库（Crunchbase、IT 桔子、PitchBook）的对应条目。
10. 应用商店 / 插件市场条目（若为 SaaS 或开发者工具）。
11. 招聘信息（用于反推团队规模、技术栈、扩张方向）。
12. 创始人 / 高管公开访谈（用于定位与路线图口径）。

---

## 3. 冲突并列框架（Conflict Ledger）

用户声明"二手资料互相冲突"，但未给出具体冲突来源。此处先给出**冲突登记模板**，待提供来源后填入；同时列出 Skill 与 evals 中明确预警过的高频冲突点，作为检索时的重点核对项。

| 维度 | 来源 A 主张 | 来源 B 主张 | 裁决依据（优先级） | 当前状态 |
|------|-------------|-------------|--------------------|----------|
| 成立年份 | — | — | 工商注册 > 官方 About > 媒体报道 | 待填入 |
| 总部地点 | — | — | 官网 Contact > 工商 > LinkedIn | 待填入 |
| 团队规模 | — | — | 最新融资公告 > 官方 > LinkedIn 自报 | 待填入 |
| 融资金额/轮次 | — | — | 领投方公告 > 监管文件 > Crunchbase > 媒体 | 待填入 |
| 定价（起步价） | — | — | 官网 Pricing 页（带抓取日期）> 注册实测 > G2/Capterra 价格栏 | 待填入 |
| 客户数量 / Logo 墙 | — | — | 具名可核实案例 > 新闻稿 > 官网 logo 墙（仅定位主张） | 待填入 |
| G2 / Capterra 评分 | — | — | 并列两平台数值+评论数+抓取日期，不做平均 | 待填入 |
| 月独立访客 / 流量 | — | — | 并列 SimilarWeb / Semrush / Ahrefs 三家估算，不取单一值 | 待填入 |
| 反向链接数 | — | — | 并列 Majestic / Ahrefs / Moz，注明工具与日期 | 待填入 |
| 功能清单 | — | — | 官网 Features + Changelog > 第三方评测（可能滞后） | 待填入 |

**Skill 明确预警的冲突处理规则**（来自 evals #6 与 Core Principles）：
- Logo 墙是**定位主张**，不是客户结构证明；不得当作"客户列表"直接引用。
- "10,000 customers" 这类规模主张需用流量 / 反链档案做量级交叉验证，不吻合则在画像中**标旗**而非采信。
- 区分"具名可核实客户（named customers）"与"服务行业（industries served）"——后者是定位陈述。

---

## 4. 后续核验问题（Verification Questions — 替代确定结论）

按 Skill 章节组织。这些问题**不是结论**，而是把画像从 D/X 级提升到 A/B 级所必须回答的问题。

### 4.1 身份与可达性（必须先回答）
- Q1. 该竞品的**准确公司名 + 产品名 + 主域名**是什么？是否有别名 / 曾用名 / 子品牌？
- Q2. 官网"无法访问"的具体表现是什么？（DNS 失败 / HTTP 4xx-5xx / 区域屏蔽 / Cloudflare 拦截 / JS 白屏 / 付费墙）是否已尝试不同网络环境、UA、`curl -I`、Google Cache、Wayback Machine（web.archive.org）？
- Q3. 是否存在可替代的一手源？（官方博客子域、文档站 docs.*、状态页 status.*、应用商店页、GitHub 组织页、官方社交媒体置顶）
- Q4. 该画像的"as of"日期是哪一天？用于判断二手资料是否过期。

### 4.2 己方上下文（用于 Competitive Implications 章节）
- Q5. 己方产品名称、定位句、目标客群、起步价分别是什么？是否有 `.agents/product-marketing.md` 可提供？
- Q6. 本次画像用于什么决策？（销售 battlecard / 定价调整 / 内容 gap / 投资判断）——决定聚焦维度。

### 4.3 At a Glance
- Q7. 成立年份以哪个口径为准（工商注册 / 产品上线 / 品牌启用）？
- Q8. 总部是注册地、实际办公地还是母公司所在地？三者是否一致？
- Q9. 团队规模取官方口径还是 LinkedIn 自报？取数日期？
- Q10. 融资信息以哪一轮公告为准？是否包含未披露金额的轮次？

### 4.4 Positioning & Messaging
- Q11. 首页 H1 与副标题原文是什么？（需 Wayback 或官方社媒截图佐证）
- Q12. 官网导航结构与定价分层指向哪类客群（SMB 自助 / Mid-market / Enterprise）？
- Q13. 媒体定性（如"XX 领域的 Notion / Figma"）是否与官网自述一致？不一致时以哪个为准？

### 4.5 Product & Features
- Q14. 当前功能清单的最新来源是 Features 页还是 Changelog？日期？
- Q15. "差异化"项是官网自述还是第三方评测？需逐条标注。
- Q16. 集成目录中"已上线"vs"即将上线"vs"社区维护"如何区分？
- Q17. 近 90 天 Changelog 条目数与主题分布是什么？（用于产品方向信号）

### 4.6 Pricing（高冲突区，需最严核验）
- Q18. 定价页抓取日期与时间？月付 vs 年付分别列价？
- Q19. 是否有按席位、按用量、按模块的复合计费？最低承诺期？
- Q20. 免费试用是否需信用卡？试用时长？是否有永久免费层？
- Q21. G2 / Capterra 等第三方显示的价格与官网是否一致？差异多大？

### 4.7 Customers & Social Proof
- Q22. Logo 墙上的客户，有多少能在其官网 Case Study / 新闻稿 / 客户官网上找到反向佐证？
- Q23. "10,000+ customers" 等规模主张，与 SimilarWeb 月访客量级、反链量级是否同量级？不匹配时如何标旗？
- Q24. G2、Capterra、TrustRadius、Product Hunt 各自的评分、评论数、最近评论日期？是否存在刷分迹象（评论集中在短窗口、文案雷同）？

### 4.8 SEO & Content
- Q25. 若 DataForSEO 不可用，是否接受 SimilarWeb / Semrush / Ahrefs 中任一家作为替代？接受哪几家并列？
- Q26. 博客近 90 天发布频率、主要内容类型（指南 / 对比 / 模板 / 客户故事）？
- Q27. 反链 Top 5 来源是否包含高权重媒体？是否存在大量垃圾外链（影响 spam score 判断）？

### 4.9 综合裁决
- Q28. 当两个二手源冲突时，裁决优先级是否采用本文件第 3 节所列？是否有内部更权威的来源（如销售一线反馈、客户访谈、商务渠道情报）可作为裁决依据？
- Q29. 本画像的"可引用线"定在置信度 B 还是 A？低于该线的内容是否仅作内部线索、不进入对外材料？

---

## 5. 按 Skill 模板应有的章节 — 当前完成度

| Skill 模板章节 | 状态 | 原因 |
|----------------|------|------|
| At a Glance | ⛔ 空 | 无目标 + 一手源不可达 |
| Positioning & Messaging | ⛔ 空 | 同上 |
| Product & Features | ⛔ 空 | 同上 |
| Pricing | ⛔ 空 | 同上 |
| Customers & Social Proof | ⛔ 空 | 同上 |
| SEO & Content Strategy | ⛔ 空 | DataForSEO 不可用 + 无域名 |
| Strengths & Weaknesses | ⛔ 故意空 | 无溯源下写 SWOT 即补造，违反用户"不得补造"与 Skill #1/#4 |
| Competitive Implications | ⛔ 空 | 己方产品上下文缺失 |
| Raw Data Sources | 📁 目录已建 | `competitor-profiles/raw/unknown-competitor/2026-08-10/{scrapes,seo,reviews}/` 均为空，符合"无原始数据不伪造" |

---

## 6. 实际读取的 Skill 文件

| 文件路径（相对 ZIP 根） | 是否读取 | 对本结果的影响 |
|--------------------------|----------|----------------|
| `SKILL.md` | ✅ 完整读取 | 定义了三阶段流程、核心四原则、目录约定、输出模板、quick vs deep 规则；本画像的"不补造 / 可溯源 / 快照日期 / 不覆盖历史日期目录"全部源于此 |
| `references/templates.md` | ✅ 完整读取 | 提供了 quick scan 模板、对比表、定位图、SWOT、changelog 结构；本画像第 1 节维度列与第 5 节完成度表对齐其字段 |
| `references/tool-reference.md` | ✅ 完整读取 | 列出 Firecrawl + DataForSEO MCP 工具集与推荐执行顺序、错误处理表；本画像第 0 节"工具不可用退化"与第 2 节二级缺口 #5 直接源于此 |
| `evals/evals.json` | ✅ 完整读取 | eval #6（logo 墙 ≠ 客户证明）与 eval #5（用户要求跳过 SEO 时应标"未采集"而非留空）直接决定了本画像把 logo 墙列为"定位主张"、把 SEO 章节标为"未获取"而非留空或编造 |

---

## 7. 影响结果的关键规则（从 Skill 中提炼并实际生效）

1. **Facts Over Opinions（SKILL.md §Core Principles #1）**：每条主张必须可溯源到抓取页、评测数据或 SEO 指标；推断必须显式标注。→ 本画像所有无来源字段一律留空并标 D/X，不写"大概是…"。
2. **Honest Assessment（#4）**：不夸大对手弱项、不淡化其强项。→ 在无数据时不输出任何 SWOT，避免凭空制造"对手弱"的错觉。
3. **Snapshot 原则（#3 + Updating Profiles）**：画像必须带生成日期，过期内容需标旗。→ 本文件日期 2026-08-10，并要求二手源也带抓取日期。
4. **Raw data 先落盘再综合（§Saving Raw Data）**：先存 `raw/<slug>/<YYYY-MM-DD>/` 再写画像；新跑不覆盖旧日期目录。→ 已建目录结构；无数据时空目录本身就是"未采集"的证据。
5. **Initial Assessment 前置确认（§Initial Assessment）**：URL、己方产品、深度、聚焦维度四项未确认前不画像。→ 本画像把"竞品未具名"和"己方上下文缺失"列为一级阻塞。
6. **Logo 墙 = 定位主张（evals #6）**：客户 logo 不等于客户结构；规模主张需用流量/反链交叉验证。→ 证据矩阵第 20 行与冲突框架对应行直接采用此规则。
7. **跳过的章节要显式标注（evals #5）**：用户要求跳过某类数据时，标"未采集"而非留空或编造。→ 本画像 SEO 章节标为"DataForSEO 不可用 + 无域名"，而非留空。
8. **Error handling（tool-reference.md §Error Handling）**：scrape 被挡时尝试浏览器模式 / 缓存；DataForSEO 无数据时注"insufficient data"。→ 本画像在 Q2 列出 Wayback / Google Cache / 子域等替代路径，而不是直接放弃。
9. **Inference 与 fact 分离（#1）**：推断需显式标注。→ 本画像第 4 节全部以"问题"形式给出，不把推断写成结论。

---

## 8. 下一步（解锁画像所需的最小输入）

请补充以下任意一项即可推进到下一版：

- **最小集**：竞品主域名（或公司名+产品名）。拿到后可立即尝试 `web.fetch` + Wayback + 公开搜索，把证据矩阵中 D 级项尽量抬到 C/B 级。
- **推荐集**：最小集 + 你方产品一句话定位 + 本次画像用途（销售/定价/内容/投资）。
- **完整集**：推荐集 + 你已收集到的互相冲突的二手资料链接（哪怕只有 2–3 条），可直接填入第 3 节冲突并列框架并裁决。

> 在收到上述输入前，本文件保持"有限画像"状态：结构完整、证据可审计、零补造。
