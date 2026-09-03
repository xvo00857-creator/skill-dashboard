# eBay 搜索列表采集 — 受约束流程方案与演示结果

> 生成时间：2026-08-12 ｜ 执行人所在地：中国/杭州
> Skill：`ebay-search-listing`（随消息上传的 ZIP）

---

## 一、Skill 能力边界（以 SKILL.md 为准）

该 Skill 的唯一能力是：**在浏览器已打开 eBay 搜索/分类页的前提下，读取页面上已展示的商品卡片信息**，返回每页商品卡片数组及分页状态。它不登录、不绕过人机验证、不创建/修改/删除任何 eBay 资源，等价于"替用户复制粘贴页面上已可见的数据"。

执行依赖：
- 一个名为 `browser-act` 的浏览器自动化工具（负责导航、等待稳定、在页面上下文执行 JS）；
- `scripts/extract-listing.py`（输出一段 JS，由 browser-act 在页面中 eval，返回 JSON）。

**本次环境实际情况：`browser-act` 未安装。** 环境中仅有 GUI 浏览器工具（打开 URL、点击、滚动、截图、键盘），且该浏览器禁用了开发者工具（F12 / Cmd+Opt+I / Cmd+Opt+J 均无效）、右键菜单、地址栏 javascript: 执行。因此 Skill 设计的 `eval "$(python scripts/extract-listing.py)"` 路径无法走通。

按题目要求"以该 Skill 的真实能力边界为准，不扩张职责"，本次演示退化为：**用浏览器打开 eBay 搜索页 → 截图 → 人工转写可见字段**，并明确标注无法获取的字段。这仍在 Skill "只读页面已展示数据"的边界内。

---

## 二、受约束流程方案

### 2.1 预检（执行前必须全部通过）

| 编号 | 检查项 | 本次结果 |
|------|--------|----------|
| P1 | `browser-act` 是否可用（SKILL.md "Pre-execution Checks" 要求） | ❌ 未安装；已在所有 skill 根目录搜索确认 |
| P2 | 经验记忆文件 `browser-act-skill-forge-memories/ebay-scraper-ebay-search-listing.memory.md` 是否存在 | ❌ 不存在（首次运行，无历史经验） |
| P3 | 浏览器能否打开 eBay 搜索页（`https://www.ebay.com/sch/i.html?_nkw=...`） | ✅ 成功打开，无需登录 |
| P4 | 页面是否展示商品卡片（`.srp-results > li.s-card`） | ✅ 截图可见商品卡片 |
| P5 | 是否出现人机验证/反爬中间页 | ✅ 未出现 |
| P6 | 地理重定向检查（SKILL.md "Known Limitations" 提及） | ⚠️ 域名仍为 www.ebay.com，但价格本地化为 CNY(元)，界面中文 |
| P7 | 能否在页面中 eval JS（DevTools / javascript: / browser-act eval） | ❌ 全部不可用 |

**预检结论：** P1/P7 失败导致标准提取路径不可用；P3/P4/P5 通过，可做截图转写降级演示。

### 2.2 幂等设计

- **每页结果落盘后再翻页**：按 SKILL.md "Error resumption" 要求，每页结果保存为 `tmp/pages/{query}-p{n}.json`；重跑时若该文件已存在且 `returnedCount >= 1`，则跳过该页，避免重复请求 eBay。
- **URL 去重**：同一 `itemNumber`（或 item URL）只保留一条；若 JS 路径不可用、用截图转写，则以 `title + seller + price` 组合键去重。
- **同一浏览器会话复用**：不每页重开浏览器（SKILL.md "Reduce redundant pre-operations"）。
- **输出文件不覆盖**：结果写入带时间戳的文件，已存在则追加而非覆盖。

### 2.3 重试策略

| 故障场景 | 重试动作 | 上限 |
|----------|----------|------|
| 页面加载后 0 张卡片（SKILL.md 列出的错误：进入详情页/反爬中间页/DOM 变更） | 截图留证 → 确认 URL 仍为 SRP → 等待 3s → 重新导航 | 2 次 |
| 网络超时/空白页 | 等待 5s → 刷新 | 2 次 |
| 出现 captcha | **不自动绕过**；截图 → 暂停 → 请求人工接管（见 2.4） | 0 次自动重试 |
| browser-act 不可用 | 不伪造结果；降级为截图转写并标注缺失字段 | — |
| 单页部分卡片字段缺失 | 保留卡片，缺失字段记 null，不臆造 | — |

### 2.4 人工确认点

1. **预检后、批量采集前**：向用户确认搜索词、筛选条件、页数上限、是否接受 CNY 本地化价格。
2. **遇到 captcha / 登录墙**：立即暂停，请用户手动完成验证后再继续。
3. **翻到第 2 页前**：先在第 1 页验证提取结果质量（SKILL.md "Test before batch execution"：先测 1-2 页再全量）。
4. **结果交付前**：用户核对样例数据，确认无异常后再写入最终文件。
5. **本次降级演示**：因 browser-act 不可用，已明确告知用户降级方案及字段缺失情况。

### 2.5 禁止事项

- 不创建、删除、覆盖任何 eBay 端资源（不加购、不收藏、不发消息、不下单）。
- 不并行翻页（SKILL.md 警告单浏览器内并行易触发反爬）。
- 不伪造 itemNumber、URL、图片链接等无法从截图获取的字段。
- 不将截图转写数据冒充为 JS 结构化提取结果。

---

## 三、一次可核验的演示结果

### 3.1 执行过程（真实操作）

1. 下载并解压 `ebay-search-listing.zip`，读取 `SKILL.md` 与 `scripts/extract-listing.py`。
2. 在全部 7 个 skill 根目录搜索 `browser-act`，确认未安装（仅有 `browser-task`、`ego-browser`）。
3. 运行 `python3 scripts/extract-listing.py --max-items 0`，成功生成 7980 字节 JS（脚本本身可正常运行，只是无 browser-act 来执行它）。
4. 用浏览器打开 `https://www.ebay.com/sch/i.html?_nkw=headphones&LH_BIN=1`，页面成功加载。
5. 截图确认：页面显示"100,000+ 个符合 headphones 的结果"，商品卡片可见，价格为 CNY。
6. 尝试 F12 / Cmd+Opt+I / Cmd+Opt+J / 右键菜单 / 地址栏 javascript: 五种方式执行 JS，均失败。
7. 滚动页面，对可见的 9 张商品卡片截图并转写。

### 3.2 数据摘要

- 搜索词：`headphones`，筛选：立即购买（Buy It Now）
- 结果总量（页面显示）：100,000+
- 本次采集卡片数：9 张（第 1 页前 9 张，含 4 个赞助位）
- 价格区间：134.52 元 ~ 1,274.99 元（CNY，本地化显示）
- 涉及卖家：cleer-audio、accessoryoutpost33、davidhe622020、ad_vision2、3dshopeu、northsideluxurious1、pudshii

| # | 商品标题 | 价格(元) | 卖家 | 好评率 | 评价数 |
|---|---------|---------|------|--------|--------|
| 1 | Cleer ARC 3 True Wireless Open Ear Headphones | 809.45 | cleer-audio | 100% | 779 |
| 2 | Cleer ARC 5 Open-Ear Wireless Earbuds | 1,261.43 | cleer-audio | 100% | 779 |
| 3 | Cleer ARC 4 Open-Ear Sport Headphones | 573.34 | cleer-audio | 100% | 779 |
| 4 | JBL Tune 310C USB-C In-Ear Wired Headphones | 134.52 | accessoryoutpost33 | 99.4% | 20K |
| 5 | Apple AirPods Pro 3 (New & Sale) | 1,274.99 | davidhe622020 | 100% | 102 |
| 6 | Apple AirPods Pro 2nd Gen ANC | 670.11 | ad_vision2 | 0% | 0 |
| 7 | Apple AirPods Pro 3 (Plz View My Other Sales) | 1,012.30 | 3dshopeu | 0% | 0 |
| 8 | Apple AirPods 3rd Gen MagSafe | 837.49 | northsideluxurious1 | 0% | 0 |
| 9 | Apple AirPods 4th Gen ANC | 508.13 | pudshii | 100% | 1 |

### 3.3 可核验性

- 以上数据全部来自浏览器实时截图，可通过重新访问同一 URL 核对。
- 完整结构化数据见同目录 `demo-result.json`（含每个字段的来源与缺失说明）。
- 表格版见 `demo-result.csv`。
- 截图由浏览器工具在执行过程中实时生成，可回溯。

### 3.4 未能获取的字段（明确标注，未臆造）

| 字段 | 原因 |
|------|------|
| `itemNumber` | 需读取 DOM `data-listingid` 属性或解析 item URL，截图不可见 |
| `url`（商品详情页） | 需读取 `a.s-card__link` 的 href，截图不可见 |
| `image`（图片 URL） | 需读取 `img.s-card__image` 的 src，截图不可见 |
| `bids` | BIN  listings 通常无此字段；需 DOM 确认 |
| `nextPageUrl` / `hasNextPage` | 需读取 `a.pagination__next`，截图不可见 |
| 原价货币（USD 等） | 页面本地化显示为 CNY，原币种需 JS eval 或切换站点确认 |
| 全页 60 张卡片 | 仅转写了滚动后可见的 9 张；完整采集需 browser-act |

---

## 四、运营观察（基于本次 9 条样本，仅供参考）

1. **赞助位集中**：前 4 条均为赞助 listing，其中 cleer-audio 独占 3 席（ARC 3/4/5），JBL 1 席。
2. **品牌分布**：非赞助位以 Apple AirPods 系列为主（Pro 3、Pro 2、3rd Gen、4th Gen）。
3. **卖家风险提示**：ad_vision2、3dshopeu、northsideluxurious1 三个卖家好评率显示 0%（评价数为 0），采购/比价时需留意。
4. **运费差异大**：运费从 28.51 元到 1,507.87 元不等，跨境运费占比高，比价时应算总价。
5. **价格本地化**：所有价格以 CNY 显示，可能含汇率换算与运费估算，与 eBay.com 原站 USD 价格存在差异。

---

## 五、实际读取的 Skill 文件

| 相对路径 | 说明 |
|----------|------|
| `ebay-search-listing/SKILL.md` | Skill 主文档，含能力边界、前置检查、分页、错误处理、效率要求 |
| `ebay-search-listing/scripts/extract-listing.py` | 提取脚本，生成在浏览器中执行的 JS（本次已运行生成 JS，但无 browser-act 执行） |

## 六、实际影响交付结果的 SKILL.md 规则（至少一条）

**规则 1（最关键）：** SKILL.md 第 27-29 行 "Pre-execution Checks / Tool Readiness" 要求先确认 `browser-act` 可用。本次预检发现 browser-act 未安装，直接导致标准 `eval "$(python scripts/extract-listing.py)"` 提取路径不可用，交付方案被迫降级为截图转写，且 `itemNumber`/`url`/`image` 等字段只能标 null——这是 Skill 规则对交付结果最直接的影响。

**规则 2：** SKILL.md 第 33 行 "This Skill's operational boundary = what the user can manually do in their browser. It only reads data already displayed to the user on the page, never bypassing authentication or access controls." 这条边界规则确认了截图转写仍在 Skill 能力范围内（只读已展示数据），同时排除了任何自动绕过 captcha 或登录的做法。

**规则 3：** SKILL.md 第 116 行 "eBay regional geo-redirection" 提示非美国 IP 可能落地本地域名/本地化显示。本次从中国杭州访问，价格确实显示为 CNY，已据此标注货币字段为"CNY (displayed)"而非假定 USD。

**规则 4：** SKILL.md 第 125 行 "Test before batch execution: first test with 1-2 pages" 要求先测 1-2 页再全量。本次仅执行第 1 页演示，未翻页批量采集，符合该规则。

**规则 5：** SKILL.md 第 127 行 "Error resumption: Save results page by page" 要求逐页落盘以便断点续传，已写入流程方案的幂等设计。
