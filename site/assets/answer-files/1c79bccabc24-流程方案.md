# eBay 已售出商品数据采集 — 受约束流程方案

> 基于 Skill `ebay-sold-listings-search`（版本以随附 SKILL.md 为准），在当前权限与环境约束下制定。
> 生成时间：2026-08-12（Asia/Shanghai）

---

## 一、能力边界声明（以 SKILL.md 为准）

本 Skill 的操作边界等同于用户在浏览器中手动可做的事：

- 仅读取 eBay 搜索结果页上**已经展示给用户**的已售出（completed/sold）商品数据；
- 不绕过登录、验证码或任何访问控制；
- 不创建、删除、修改 eBay 上的任何资源；
- 三个原子能力均由 `scripts/` 下的 Python 脚本提供，通过浏览器执行其输出的 JavaScript：
  1. `build-url.py` — 拼装 8 个站点的已售出搜索 URL（本地可独立运行）；
  2. `extract-page.py` — 在已渲染的搜索结果页上提取结构化商品记录（需浏览器执行 JS）；
  3. `enum-categories.py` — 枚举当前搜索页的顶级分类（需浏览器执行 JS）。

**SKILL.md 明确要求的前置依赖**：`browser-act` 命令行工具（负责 navigate / wait / eval）。

---

## 二、当前环境预检结果（2026-08-12 实测）

| 检查项 | 结果 | 说明 |
|---|---|---|
| Python 3 | ✅ 可用 | Python 3.9.6 |
| Node.js（JS 语法校验用） | ✅ 可用 | 用于校验提取器 JS 语法 |
| `build-url.py` | ✅ 正常 | 正确生成含全部筛选参数的 URL |
| `extract-page.py` 输出 JS 语法 | ✅ 通过 | `node --check` 无错误 |
| `enum-categories.py` 输出 JS 语法 | ✅ 通过 | `node --check` 无错误 |
| `browser-act` 命令 | ❌ 未安装 | `command not found`，系统中无此工具及对应 Skill |
| eBay 首页（浏览器 GUI） | ✅ 可访问 | 中文界面正常加载 |
| eBay 普通搜索结果页 | ✅ 可访问 | 通过搜索框交互可正常加载在售商品 |
| eBay 已售出搜索页（LH_Sold=1） | ❌ 被阻止 | 直接访问触发 hCaptcha 或重定向登录页；curl 返回 HTTP 403 |
| 经验记忆文件 | 不存在 | `browser-act-skill-forge-memories/ebay-sold-listings-search.memory.md` 未找到 |

**结论**：工具链中 URL 构建和 JS 提取代码均已验证可用，但缺少 `browser-act` 执行环境，且当前出口 IP 访问 eBay 已售出搜索页被反爬机制（hCaptcha / 登录墙 / 403）阻止。因此本次**无法完成真实商品数据采集**，仅交付工具链可核验演示与受约束流程方案。

---

## 三、受约束采集流程（含预检 / 幂等 / 重试 / 人工确认点）

### 阶段 0：预检（Pre-flight）

执行任何采集前必须逐项通过：

1. **工具就绪检查**
   - `python3 --version` ≥ 3.8
   - `browser-act --help` 可执行（SKILL.md 要求；当前环境缺失，标记为阻塞项）
   - `node --version`（用于 JS 语法自检，可选但推荐）
2. **网络可达性检查**
   - 用浏览器打开 `https://www.ebay.com`，确认首页加载且无验证码；
   - 用 `build-url.py` 生成一个测试 URL，浏览器导航后确认出现 `li.s-card` 元素；
   - 若出现 `splashui/challenge` 或登录墙，进入人工确认点 A。
3. **经验记忆检查**
   - 若 `browser-act-skill-forge-memories/ebay-sold-listings-search.memory.md` 存在，先读取并调整策略。
4. **输出目录检查（幂等准备）**
   - 确认输出目录可写；若已有同名 JSONL 结果文件，进入人工确认点 B（避免覆盖）。

### 阶段 1：URL 构建（本地，无网络副作用）

```bash
URL=$(python3 scripts/build-url.py '<关键词>' \
  --ebaySite ebay.com \
  --sortOrder endedRecently \
  --itemCondition used \
  --minPrice 50 --maxPrice 300 \
  --includeCompletedListings true \
  --ipg 60 --page 1)
```

- 支持的 8 个站点：ebay.com / .co.uk / .de / .fr / .it / .es / .ca / .com.au
- 支持的排序：endedRecently / timeNewlyListed / pricePlusPostageLowest / pricePlusPostageHighest / distanceNearest
- 支持的成色：new(1000) / used(3000) 或任意数字成色 ID

### 阶段 2：页面导航与等待（browser-act）

```bash
browser-act navigate "$URL"
browser-act wait --selector "li.s-card" --state visible --timeout 30000
```

- 若 30 秒内未出现 `li.s-card`，检查 `window.location.href` 和 `document.title`：
  - `splashui/challenge` → 等待 10 秒后重试（最多 2 次）；仍被阻止则进入人工确认点 A；
  - `SORRY / Something went wrong` → 等待 30 秒后重试 1 次；仍失败则暂停并报告。

### 阶段 3：数据提取（browser-act eval）

```bash
RESULT=$(browser-act eval "$(python3 scripts/extract-page.py --keyword '<关键词>')")
```

- 解析返回 JSON，检查 `error === false` 且 `itemCount >= 1`；
- 每条记录必须有 `itemId`、`url`、`title`、`soldPrice`（SKILL.md 成功标准）；
- 按 `itemId` 去重（跨页幂等）。

### 阶段 4：分页循环（含退避与重试）

对每个关键词：
1. `page=1`，`collected=[]`，`seenIds=set()`；
2. 循环直到 `len(collected) >= count` 或 `hasNextPage === false`；
3. 每页之间 **sleep 2–4 秒**（SKILL.md 要求，避免触发限流）；
4. 单页失败重试 1 次（等待 10 秒）；仍失败则标记该关键词不完整并跳出；
5. 每页结果**立即追加写入 JSONL**（断点续传，幂等恢复）。

### 阶段 5：持久化与合并

- 每个关键词一个 JSONL 文件：`output/<keyword>_<timestamp>.jsonl`；
- 合并时按 `itemId` 全局去重；
- 可选后过滤：按 `daysToScrape` 丢弃超出时间窗口的记录（eBay URL 不支持直接按成交日期筛选）。

---

## 四、人工确认点

| 编号 | 触发条件 | 处理方式 |
|---|---|---|
| **A** | 出现 hCaptcha / 登录墙 / 持续 splash challenge | 暂停自动化，提示用户在浏览器中手动完成验证或登录；完成后通知继续。**不自动绕过验证码。** |
| **B** | 输出目录已存在同名结果文件 | 提示用户选择：覆盖 / 追加 / 中止；默认不覆盖。 |
| **C** | 非美国站点（如 ebay.co.uk / ebay.de）从非匹配地区 IP 访问被拒 | 提示用户需要匹配地区代理或 stealth browser；不擅自切换代理。 |
| **D** | 批量采集前（>2 个关键词或 >5 页） | 先跑 1–2 关键词 × 2 页的小批量验证（SKILL.md "Test before batch execution"），人工确认解析质量后再全量运行。 |

---

## 五、幂等与重试设计

- **幂等键**：`itemId`。同一关键词跨页、跨次运行均以 itemId 去重；
- **断点续传**：每页写入 JSONL 后才继续下一页；中断后从最后完成页的下一页恢复；
- **重试上限**：单页最多重试 1 次（等待 10 秒）；splash challenge 最多等待重试 2 次（各 10 秒）；
- **退避策略**：页间 2–4 秒固定退避；错误后 10–30 秒指数退避；
- **不重复请求**：同一 URL 在同一次运行中不重复导航（除非显式重试）。

---

## 六、已知限制（SKILL.md 原文要点）

1. Best Offer Accepted 成交的实际成交价 eBay 不公开，`soldPrice` 为标价，`isBestOfferAccepted=true` 标记差异；
2. BOA 检测需要 `includeCompletedListings=true`（默认）；
3. eBay URL 不支持直接按成交日期范围筛选，需按 `endedRecently` 排序后在客户端截断；
4. `sellerType`（private/business）仅在欧盟站点标注；
5. `fullResThumbnailUrl` 由 s-l500 改写为 s-l1600，部分商品可能 404；
6. 单 IP 激进分页会触发限流/验证码；页间须间隔 2–4 秒；
7. 非匹配地区 IP 访问部分站点可能直接被拒。

---

## 七、本次可核验演示结果

由于上述阻塞项，本次演示范围为**工具链本地验证**（不涉及 eBay 实时数据）：

1. `build-url.py` 生成的真实 URL 示例见 `工具链验证报告.md`；
2. `extract-page.py` / `enum-categories.py` 输出的 JS 通过 `node --check` 语法校验；
3. 可执行编排脚本 `collect.sh` 已就绪，在 `browser-act` 可用且 eBay 可达时可直接运行。

**未编造任何 eBay 商品数据。** 所有商品记录字段均需在浏览器成功访问已售出搜索页后由 `extract-page.py` 真实提取。
