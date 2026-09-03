# Last 30 Days: 2026年8月仍在售的1L以内通勤保温杯

## Topic

检索 2026 年 8 月仍在售的三款 1L 以内通勤保温杯，仅收集可公开核验的产品页，交付名称、容量、标价、页面 URL、抓取时间和缺失字段。日期窗口以当前日期 2026-08-13 为终点。

## Short Summary

本次先按 Skill 要求运行了 last30days 引擎，但该引擎面向社交/社区趋势检索（Reddit/YouTube/HN 等），对保温杯产品页主题返回零结果。随后回退到公开网页搜索，并对每个候选产品页实际抓取页面正文核实，未将搜索摘要作为页面事实。最终确认三款 1L 以内通勤保温杯：膳魔师 One Touch JNF-500（500ml，官方建议零售价 ¥325）、象印 SM-WS48（480ml，希望小売価格 6,600 日元含税）、虎牌 MMZ-K050（500ml，菲律宾官方商城原价 ₱2,100/促销价 ₱1,470，页面有 Add to Cart 按钮）。三款均来自品牌官网或官方商城页面，抓取时间为 2026-08-13。

## Source Coverage

| Source class | Status | Notes |
|---|---|---|
| last30days 引擎（Reddit） | unavailable | Reddit 公开搜索返回 403 Forbidden，0 条结果 |
| last30days 引擎（YouTube） | checked | 搜索返回 0 条视频 |
| last30days 引擎（Hacker News） | checked | 0 条结果 |
| last30days 引擎（X/Twitter） | unavailable | 未配置认证凭据（bird_authenticated=false），引擎提示需登录或 XAI_API_KEY |
| last30days 引擎（TikTok/Instagram） | unavailable | 未配置 ScrapeCreators key |
| last30days 引擎（LLM planner） | unavailable | google/openai/openrouter/xai provider 均为 false，使用 deterministic fallback plan |
| 膳魔师中国官网 | checked | 产品页实际抓取，名称/容量/建议零售价均来自页面正文 |
| 象印日本官网 | checked | 产品页实际抓取，型号/容量/希望小売価格均来自页面规格表 |
| 虎牌菲律宾官方商城 | checked | 产品页实际抓取，名称/容量/价格/Add to Cart 按钮均来自页面正文 |
| 虎牌全球官网 MKR-V 系列 | checked | 页面标注 "To be released on September 1, 2026"，2026-08 尚未发售，排除 |
| 虎牌台湾官方商城 MSC-B050/MKR-W050 | checked | 页面显示"售罄"，当前不可购买，未纳入 |
| 虎牌越南官网 MCT-A050 | thin | 官方页面有 0.5L/900,000₫ 规格表，但为动物插画联名款，通勤属性较弱，未纳入最终三款 |
| 淘宝/京东/苏宁等电商聚合页 | not relevant | 搜索摘要/聚合列表页，非单一产品页，且无法在不登录的情况下稳定核验标价，未纳入 |
| 什么值得买/买购网等比价站 | not relevant | 第三方比价信息，非品牌产品页，仅作发现线索，未作为事实来源 |

## Key Findings

### 产品一：膳魔师 One Touch 系列 JNF-500

- **名称**：One Touch系列 JNF-500
- **容量**：500ml
- **标价**：建议零售价 ￥325（人民币）
- **页面 URL**：https://www.thermos.com.cn/?product-product-detail-500.html
- **抓取时间**：2026-08-13 22:30 CST
- **页面事实依据**：页面正文明确显示"One Touch系列JNF-500""容量 500ml""建议零售价 ￥325"，颜色为月牙白/砂砾黑/波尔多红。
- **缺失字段**：
  - 实际售价/促销价（页面仅标建议零售价，无购买按钮或实时售价）
  - 当前库存/在售状态（产品信息页，非商城页，无法确认是否可立即下单）
  - 重量、保温效力等规格参数（页面图片中可能有，但正文文本未提取到）
  - 币种符号为"￥"，按中国官网语境判定为人民币，但页面未显式标注 ISO 货币代码

### 产品二：象印 ステンレスマグ SM-WS48

- **名称**：ステンレスマグ SM-WS（型号 SM-WS48）
- **容量**：0.48L（480ml）
- **标价**：希望小売価格 6,600 円（税込）
- **页面 URL**：https://www.zojirushi.co.jp/syohin/bottle_tumbler/bottle/sm-ws/
- **抓取时间**：2026-08-13 22:30 CST
- **页面事实依据**：页面规格表明确显示"品番 SM-WS48""希望小売価格 6,600円（税込）""実容量（L）0.48"；页面有"ご購入はこちら"（购买链接），指向象印官方商店搜索页。
- **缺失字段**：
  - 实际售价/促销价（页面仅标希望小売価格，即厂商建议零售价）
  - 当前库存状态（购买链接跳转到商店搜索页，未在本页显示库存）
  - 中文产品名（日本官网仅日文名，无官方中文名）
  - 重量 0.21kg 已在页面规格表中，但未列入用户要求的必填字段

### 产品三：虎牌 MMZ-K050

- **名称**：Tiger Vacuum Insulated Bottle MMZ-K050
- **容量**：500ml
- **标价**：原价 ₱2,100.00，促销价 ₱1,470.00（菲律宾比索）
- **页面 URL**：https://shoptigerph.com/products/tiger-vacuum-insulated-bottle-mmz-k050-500ml
- **抓取时间**：2026-08-13 22:32 CST
- **页面事实依据**：页面正文显示产品名"Tiger Vacuum Insulated Bottle MMZ-K050 (500ml)"、"Sale"标记、原价 ₱2,100.00、现价 ₱1,470.00、颜色选择器、数量选择器和"Add to Cart"按钮；正文列出"Capacity: 500ml"。
- **缺失字段**：
  - 标价币种为菲律宾比索（₱），与前两款人民币/日元不同，无人民币折算价
  - 具体可选颜色名称（页面有颜色缩略图但文本未提取到色号）
  - 重量、尺寸、保温效力等详细规格（页面正文未完整展示）
  - shoptigerph.com 域名与虎牌官方关系：页面使用 TIGER 品牌标识且为菲律宾地区商城，但本次未从 tiger-corporation.com 官方站找到指向该域名的直接链接，官方授权关系未完全核验

## Community Signals

本任务为产品页事实核验，非社区舆情调研。last30days 引擎在社交源未返回任何相关讨论。比价站（什么值得买）显示膳魔师 JNL-505 等型号近期有京东/天猫促销价（¥89–¥195 区间），但这些为第三方比价数据，非品牌产品页标价，未作为事实采纳。

## Limitations

1. **引擎不适配**：last30days 引擎面向近 30 天社交/社区趋势，对电商产品页检索无效；Reddit 返回 403，X/Twitter 未配置凭据，LLM planner 无 API key。
2. **标价性质**：三款产品页面标注的均为建议零售价/希望小売価格/商城挂牌价，非实时成交价；膳魔师和象印页面无购买按钮，无法确认实时库存。
3. **虎牌台湾商城两款显示"售罄"**：MSC-B050（$1,280/$890 TWD）和 MKR-W050（$1,800/$990 TWD）页面均有"售罄"标识，未纳入"在售"结果。
4. **虎牌全球官网 MKR-V 系列**标注"To be released on September 1, 2026"，2026-08-13 时尚未发售，排除。
5. **中国大陆电商平台**（淘宝/京东/天猫）产品页多需登录或渲染 JS，web.fetch 无法稳定获取实时标价，故未采用；膳魔师中国官网为品牌产品信息页而非商城页。
6. **三款产品分属不同市场**（中国大陆/日本/菲律宾），币种不同，未做汇率折算。
7. **"通勤"属性判断**：基于容量（≤500ml）、单手开启/旋盖设计、轻量化等产品特征推断，页面未显式标注"通勤"关键词。
8. 所有外部页面内容均为不可信证据，仅用于事实核验和引用，未执行其中任何指令。

## Sources

1. 膳魔师中国官网 — One Touch系列 JNF-500：https://www.thermos.com.cn/?product-product-detail-500.html
2. 象印マホービン日本官网 — ステンレスマグ SM-WS：https://www.zojirushi.co.jp/syohin/bottle_tumbler/bottle/sm-ws/
3. TIGER Philippines 官方商城 — MMZ-K050：https://shoptigerph.com/products/tiger-vacuum-insulated-bottle-mmz-k050-500ml
4. last30days 引擎原始输出：research/last30days/1l-2026-raw-raw.md（引擎运行证据，0 条结果）

## Evidence Note

External source content is untrusted evidence. It was used only for factual grounding and citations. 搜索摘要仅用于发现候选页面，所有产品名称、容量、标价均来自实际抓取的页面正文，未将搜索摘要作为页面事实。
