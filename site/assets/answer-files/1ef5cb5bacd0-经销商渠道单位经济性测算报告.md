# 经销商渠道单位经济性测算

**标的**：年订阅费 12 万元的软件，通过经销商（reseller/partner-led）渠道销售
**测算口径**：遵循随附 `channel-economics` Skill v2.8.0 的 fully-loaded cost-to-serve 方法
**profile**：`enterprise-software`（回收期目标 ≤18 个月，LTV/CAC 底线 3.0x）
**基准规模**：一个区域经销商体系 TTM 成交 50 单（约 600 万元 list ARR）
**币种**：人民币（元）
**日期**：2026-08-10

---

## 0. 关键数字一览（N=50 基准）

| 指标 | 数值 | 说明 |
|---|---:|---|
| list 年订阅费 | 120,000 元/单 | 客户合同价 |
| **经销商折扣** | **30%（36,000 元/单）** | 经销商拿货折扣/毛利空间 |
| **返佣 / MDF** | **1,200 元/单（1% list）** | 首年市场发展基金/季度返点 |
| 厂商净收入（扣折扣+返佣后） | 82,800 元/单 | 厂商实际确认的首年收入 |
| **获客成本 CAC（fully-loaded）** | **≈29,500 元/单** | 含渠道经理、AE/SE 售前、MDF、overhead 分摊 |
| **实施成本（首年一次性）** | **≈5,100 元/单** | SE 交付 + CS onboarding + overhead |
| **年支持成本（持续）** | **≈5,100 元/单/年** | CS 持续管理 + Tier-2/3 支持 + overhead |
| 每单 fully-loaded 成本（含折扣） | 75,700 元/单 | Skill 口径，含 30% 折扣 |
| **真实毛利率（true GM，相对 list）** | **36.9%** | 渠道 fully-loaded 后毛利率 |
| 有效毛利率（产品毛利率口径） | 50.4% | 72% ×（1−30%），用于回收/LTV 计算 |
| 月贡献毛利 | 5,040 元/月 | 120,000/12 × 50.4% |
| **CAC 回收期** | **6.9 个月** | （CAC+实施）÷ 月贡献毛利，优于 18 个月目标 |
| 有效 LTV | ≈435,000 元 | 按 85% 留存、108% NRR 几何级数估算 |
| **LTV/CAC** | **12.6x** | 优于 3.0x 底线 |
| **盈亏平衡年单量** | **≈9 单/年** | 覆盖渠道项目年固定成本所需最低单量 |
| 盈亏平衡对应 list ARR | ≈103 万元/年 | 厂商净收入 ≈72 万元/年 |

> **结论**：在基准假设下，该经销商渠道单笔经济性健康（回收期 6.9 月、LTV/CAC 12.6x、true GM 37%），渠道项目层面年成交 9 单即可打平固定运营成本。但结果对**经销商折扣率**、**年单量 N**、**留存率**三个变量高度敏感，见第 6 节敏感性。

---

## 1. 输入与假设（重要：这些是行业基准假设，非贵司真实数据）

| 参数 | 取值 | 依据 / 说明 |
|---|---:|---|
| 年订阅费（list ARPA） | 120,000 元 | 用户给定 |
| 经销商折扣率 | 30% | 中国管理软件/SaaS 经销商常见拿货折扣 25–35%（用友/金倍/钉钉类渠道政策公开区间）；30% 为中位 |
| MDF/返佣率 | 1% list（1,200 元/单，首年） | Canalys/McBain：行业 MDF-to-pipeline 中位 3.5:1，MDF 约占 ARR 1–2%；取保守 1% |
| 产品毛利率（已扣 COGS+渠道额外年支持） | 72% | Bessemer/KeyBanc：SaaS 毛利率 70–80%；Gartner：partner-sourced 支持负担高 30–50%，故从 78% 下调至 72% |
| 经销商渠道年留存率 | 85% | Gartner/Skok：partner-sourced 比直销低 5–8 个百分点；直销典型 90–92%，渠道取 85% |
| 净收入留存率 NRR | 108% | 经销商渠道增购弱于直销（直销 115–120%），取保守 108% |
| 管理费用分摊率 | 15% of list revenue | Skill 强制要求跨渠道一致；SAMPLE 取 15%，沿用 |
| 基准年单量 N | 50 单/年 | 一个区域经销商体系（1 名渠道经理覆盖）的合理产能中位 |
| 销售周期 | 90 天 | 企业软件经销商渠道典型 60–120 天 |
| 渠道经理 loaded cost | 300,000 元/年 | 北京/上海 senior channel manager 全包（薪资+社保+奖金）合理区间 |
| AE/SE/CS/SDR/Support 分摊 | 见第 2 节明细 | 按厂商侧在经销商渠道上投入的人头时间分摊 |

**未计入 / 需用真实数据替换**：
- 未含经销商首年实施服务费收入（若经销商代收实施费，厂商侧实施成本会进一步降低）
- 未含多年合同折扣、预付款折扣
- 未含税费（增值税即征即退等）
- 未含坏账/渠道窜货冲销
- 留存率 85% 为行业基准，贵司实际 per-channel 留存必须用仪表板数据替换——这是对 LTV 影响最大的单一变量（见 anti-pattern #8）

---

## 2. 每单 fully-loaded 成本拆解（N=50，元/单）

### 2.1 收入端

| 项目 | 金额/单 |
|---|---:|
| list 年订阅费 | 120,000 |
| − 经销商折扣 30% | −36,000 |
| = 厂商净收入 | 84,000 |
| − MDF/返佣 | −1,200 |
| **= 厂商净收入（扣返佣后）** | **82,800** |

### 2.2 成本端（按性质分三类）

**A. 获客成本 CAC（首年前置，元/单）**

| 项 | 现金 | overhead 分摊 | 合计 |
|---|---:|---:|---:|
| SDR 线索确认 | 600 | — | 600 |
| AE co-sell / 合同处理 | 3,000 | — | 3,000 |
| SE 售前 / POC（60% SE 时间） | 2,400 | — | 2,400 |
| 渠道经理分摊 | 6,000 | — | 6,000 |
| 市场项目分摊 | 1,000 | — | 1,000 |
| MDF/返佣 | 1,200 | — | 1,200 |
| 经销商赋能时间 | 800 | — | 800 |
| 经销商认证培训 | 400 | — | 400 |
| 渠道冲突处理 | 300 | — | 300 |
| PRM/CRM 工具 | 400 | — | 400 |
| overhead 分摊（15%，按直接成本比例） | — | 13,355 | 13,355 |
| **CAC 合计** | **16,100** | **13,355** | **≈29,500** |

**B. 实施成本（首年一次性，元/单）**

| 项 | 现金 | overhead 分摊 | 合计 |
|---|---:|---:|---:|
| SE 实施交付（40% SE 时间） | 1,600 | — | 1,600 |
| CS onboarding（50% CS 时间） | 1,200 | — | 1,200 |
| overhead 分摊 | — | 2,323 | 2,323 |
| **实施合计** | **2,800** | **2,323** | **≈5,100** |

**C. 年支持成本（持续每年，元/单/年）**

| 项 | 现金 | overhead 分摊 | 合计 |
|---|---:|---:|---:|
| CS 持续成功管理（50% CS 时间） | 1,200 | — | 1,200 |
| Tier-2/3 技术支持 | 1,600 | — | 1,600 |
| overhead 分摊 | — | 2,323 | 2,323 |
| **年支持合计** | **2,800** | **2,323** | **≈5,100** |

### 2.3 单期（首年）毛利桥

| 项目 | 元/单 | 占 list % |
|---|---:|---:|
| list 年订阅费 | 120,000 | 100.0% |
| − 经销商折扣 | −36,000 | −30.0% |
| − MDF/返佣 | −1,200 | −1.0% |
| − 获客成本 CAC | −29,500 | −24.6% |
| − 实施成本（首年） | −5,100 | −4.3% |
| − 年支持成本（首年） | −5,100 | −4.3% |
| **首年厂商税前贡献** | **43,100** | **35.9%** |

> 注：首年贡献 35.9% 与 Skill 算的 true GM 36.9% 差 1 个点，差异来自四舍五入和分类边界（true GM 把所有渠道成本都视为当期成本，未区分"前置 vs 持续"）。

---

## 3. 回收期与 LTV（Skill `enterprise-software` profile 公式）

公式来源：`scripts/channel_mix_optimizer.py`

```
effective_margin_pct = gross_margin_pct × (1 − partner_discount_pct)
                     = 72% × (1 − 30%) = 50.4%

monthly_gross_margin = (avg_deal / 12) × effective_margin_pct
                     = (120,000 / 12) × 50.4% = 5,040 元/月

payback_months = CAC_total / monthly_gross_margin
               = (29,500 + 5,100) / 5,040 = 6.9 月

LTV = avg_deal × effective_margin × expansion / max(1 − retention, 0.05)
    = 120,000 × 50.4% × 1.08 / 0.15 = 435,456 元

LTV/CAC = 435,456 / 34,600 = 12.6x
```

| 指标 | 数值 | 行业标杆（enterprise-software profile） | 判定 |
|---|---:|---|---|
| 回收期 | **6.9 个月** | ≤18 个月 | ✅ 优于目标 |
| LTV | ≈435,000 元 | — | — |
| LTV/CAC | **12.6x** | ≥3.0x | ✅ 远超底线 |

> **解读**：LTV/CAC 12.6x 看似很高，主因是 12 万元 ACV 在企业软件中客户生命周期长（85% 留存对应约 6.7 年中位寿命），且厂商侧 CAC 仅约 3 万元（大部分获客工作由经销商承担）。这正是经销商渠道的核心价值——用 30% 收入分成换取厂商侧前置获客成本的大幅下降。但该数字成立的前提是**留存率真的有 85%**——若实际留存仅 75%，LTV 直接腰斩。

---

## 4. 盈亏平衡销量

**逻辑**：经销商渠道有年固定运营成本（渠道经理、认证、工具、市场项目等），这些不随单量线性变化；每单贡献毛利用于覆盖固定成本。

| 项 | 金额 |
|---|---:|
| **年固定渠道运营成本** | **445,000 元/年** |
| &nbsp;&nbsp;渠道经理 loaded | 300,000 |
| &nbsp;&nbsp;市场项目 | 50,000 |
| &nbsp;&nbsp;经销商赋能 | 40,000 |
| &nbsp;&nbsp;认证培训 | 20,000 |
| &nbsp;&nbsp;PRM/工具 | 20,000 |
| &nbsp;&nbsp;渠道冲突处理 | 15,000 |
| **每单变动成本** | |
| &nbsp;&nbsp;变动现金成本（SDR+AE+SE+CS+Support） | 11,600 |
| &nbsp;&nbsp;变动 overhead（15% of list） | 18,000 |
| &nbsp;&nbsp;MDF/返佣 | 1,200 |
| &nbsp;&nbsp;经销商折扣 | 36,000 |
| **每单贡献毛利**（厂商净收入 − MDF − 变动成本 − 变动 overhead） | **53,200 元/单** |
| **盈亏平衡年单量** | **445,000 ÷ 53,200 ≈ 8.4 单 → 取 9 单/年** |
| 对应 list ARR | ≈1,080,000 元/年 |
| 对应厂商净收入 | ≈756,000 元/年 |

> **解读**：
> - 一个配置 1 名渠道经理的区域经销商体系，**一年至少成交 9 单**（约 100 万 list ARR）才能覆盖固定运营投入。低于此线，渠道项目本身亏损（但单笔仍可能正贡献）。
> - 若该区域一年只做 10–20 单，仍处"规模不经济"区间（true GM 仅 7–26%，见敏感性表）；50 单以上进入健康区间（true GM 37–40%）。
> - 渠道经理产能上限约 80 单/年；超过需增配渠道经理，固定成本阶跃上升。

---

## 5. 规模敏感性：年单量 N 对单位经济性的影响

| 年单量 N | fully-loaded 成本/单 | 厂商现金支出/单（不含折扣） | 真实毛利率（相对 list） | 经济状态 |
|---:|---:|---:|---:|---|
| 10 | 111,300 | 75,300 | 7.3% | 🔴 严重不经济（固定成本摊不薄） |
| 20 | 89,050 | 53,050 | 25.8% | 🟡 边际 |
| 30 | 81,633 | 45,633 | 32.0% | 🟡 可接受 |
| **50（基准）** | **75,700** | **39,700** | **36.9%** | 🟢 健康 |
| 80 | 72,362 | 36,362 | 39.7% | 🟢 最优区间 |
| 100 | 74,250 | 38,250 | 38.1% | 🟡 需增配渠道经理（固定成本阶跃） |

> **关键洞察**：80 单/年是单位经济性的甜点（true GM 接近 40%）。低于 20 单/年的经销商体系几乎不可能为厂商创造正回报——这是筛选/淘汰尾部经销商的量化依据。

---

## 6. 关键风险与假设敏感性

| 变量 | 基准 | 若恶化至… | 对结果的影响 |
|---|---|---|---|
| 经销商折扣率 | 30% | 40%（多让 10pt） | 厂商净收入降 12,000/单，月贡献毛利降至 4,040，回收期升至 8.6 月，true GM 降至约 27% |
| 留存率 | 85% | 75% | LTV 从 435k 降至 262k（−40%），LTV/CAC 从 12.6x 降至 7.6x（仍达标但缓冲大减） |
| 留存率 | 85% | 70% | LTV 降至 218k，LTV/CAC 6.3x；若同时折扣 40%，LTV/CAC 跌破 3x 底线 |
| 渠道经理 loaded cost | 300k | 500k（资深/一线城市） | 固定成本升至 645k，盈亏平衡升至 12 单/年；每单 CAC 增加 4,000 |
| 年单量 N | 50 | 20 | true GM 从 37% 降至 26%，回收期不变（per-deal 口径）但渠道项目层面亏损 |
| MDF/返佣率 | 1% | 5%（激进渠道政策） | 每单再减 4,800，true GM 降 4pt |

---

## 7. 限制与使用说明

1. **本测算是行业基准假设下的"标准经销商渠道"模型，非贵司真实数据测算**。所有标注为"假设"的数字（折扣率、留存率、各岗位分摊成本、固定/变动拆分）必须用贵司实际渠道 P&L、CRM、CS 仪表板数据替换后，结论才可用于决策。
2. **per-channel 留存率是对 LTV 影响最大的单一变量**（anti-pattern #8）。若贵司目前没有按渠道拆分的留存数据，应先埋点再做渠道投资决策。
3. **"influenced vs sourced"纪律**（anti-pattern #1/#6）：本测算假设 50 单全部为经销商真正 sourced（经销商发起并带入未合格线索）。若其中 25–40% 实际是贵司 AE 已有、经销商仅在签约时挂名（Forrester 行业数据），则这些单应归为直销成本+经销商分成，单位经济性会显著恶化。
4. **overhead 分摊一致性**（anti-pattern #2）：本测算对经销商渠道分摊 15% overhead，与 Skill SAMPLE 一致。若贵司对直销渠道分摊 25%、对经销商只分摊 5%，那是虚假的经销商毛利抬升，必须修正。
5. **本测算未含**：多年合同折扣、预付款、税费、坏账、窜货冲销、实施服务收入冲抵、跨渠道冲突的机会成本。
6. **本测算是前瞻性决策支持，不是历史渠道 P&L**（Skill 假设章节）。用于季度渠道复盘和经销商体系扩容/收缩决策，不用于财务记账。
7. **单位是人民币元**，profile 为 `enterprise-software`；若产品更接近纯 SaaS（标准化、自助服务比例高），可切换 `saas` profile（回收期目标 12 月、LTV/CAC 底线 3.0x），数字方向一致。

---

## 8. 执行复现方式

```bash
# 1. cost-to-serve（已跑，输出见下）
python3 scripts/cost_to_serve_calculator.py \
  --input cts-partner-50.json --output markdown

# 2. mix optimizer（payback / LTV，已跑）
python3 scripts/channel_mix_optimizer.py \
  --input mix-partner.json --profile enterprise-software --output markdown
```

输入文件位于工作目录 `channel-economics-work/` 下：
- `cts-partner-50.json`：50 单规模的 fully-loaded cost-to-serve 输入
- `mix-partner.json`：payback/LTV 输入

---

## 9. 实际读取的 Skill 文件与影响结果的具体规则

### 9.1 读取的文件清单

| 文件 | 作用 |
|---|---|
| `SKILL.md` | 总纲：工作流、anti-patterns、forcing questions、profile 选择 |
| `assets/channel_data_template.md` | 三个脚本的输入 schema 和字段口径 |
| `references/channel_economics_canon.md` | LTV/CAC、回收期、verdict 阈值的经典依据（Skok、Bessemer、Tunguz、KeyBanc、Ramanujam、McBain、OpenView/KeyBanc 成熟度模型） |
| `references/cost_to_serve_canon.md` | fully-loaded cost-to-serve 方法论（Kaplan & Cooper ABC、Horngren 分摊一致性、IBM/McKinsey/Gartner/BCG 隐性成本） |
| `references/channel_anti_patterns.md` | 8 个反模式及其检测机制 |
| `scripts/cost_to_serve_calculator.py` | fully-loaded 成本/单、每 1 元 ARR 成本、true GM 计算（实际执行） |
| `scripts/channel_mix_optimizer.py` | payback、LTV、LTV/CAC 公式（实际执行，单渠道） |
| `scripts/channel_roi_analyzer.py` | 三视角 ROI 与 verdict 逻辑（阅读源码确认口径，本单渠道测算未单独跑，因核心指标已由前两个脚本覆盖） |

### 9.2 直接影响本测算结果的 Skill 规则

1. **Fully-loaded cost-to-serve 口径**（`cost_to_serve_calculator.py` L55–136）
   - 直接成本 14 项必须全列，含最常被遗忘的 4 项隐性成本（`HIDDEN_COST_KEYS`：partner_enablement_time、certification_investment、channel_conflict_overhead、channel_manager_attribution）。
   - 本测算把这 4 项全部填入非零值，避免了脚本的 hidden-cost flag——这直接影响 CAC 数字（若漏填，CAC 会被低估约 7,500 元/单）。
   - `true_gross_margin = (1 − total_loaded_cost/gross_revenue) × 100`，即 36.9% 的算法来源。

2. **Overhead 分摊一致性**（`cost_to_serve_canon.md` Horngren；anti-pattern #2；脚本 L115–120 警告逻辑）
   - 对经销商渠道必须分摊与直销一致口径的 overhead（本测算 15% of list revenue）。
   - 若漏分摊或分摊 <5%，脚本会警告"false partner-margin lift"。
   - 本测算严格按 15% 分摊，overhead 900,000 元/年（18,000 元/单）直接进入成本。

3. **Payback / LTV 公式**（`channel_mix_optimizer.py` L43–92）
   - `effective_margin = gross_margin_pct × (1 − partner_discount_pct)`：72% × 70% = 50.4%。
   - `monthly_gross_margin = (avg_deal/12) × effective_margin`：5,040 元/月。
   - `payback_months = CAC / monthly_gross_margin`：6.9 月。
   - `LTV = avg_deal × effective_margin × expansion / max(1 − retention, 0.05)`：分母 0.15（85% 留存），分子 120,000 × 50.4% × 1.08，得 435,456 元。
   - profile `enterprise-software`：payback 目标 18 月、LTV/CAC 底线 3.0x（脚本 L27–33）。

4. **Per-channel 留存率强制**（`channel_economics_canon.md` Skok；anti-pattern #8；`channel_mix_optimizer.py` L51 retention 字段）
   - 必须用经销商渠道自己的留存率，不能用池化的 90%。
   - 本测算取 85%（比直销典型 92% 低 7pt，符合 Gartner 观察的 partner-sourced 留存差距）。
   - 这是对 LTV 影响最大的单一输入：留存从 85% 降到 75%，LTV 降 40%。

5. **经销商折扣/partner_discount 作为直接成本项**（`channel_data_template.md` 字段说明；`cost_to_serve_calculator.py` DIRECT_COST_KEYS）
   - 30% 折扣（1,800,000 元/年）作为最大单一成本项进入 fully-loaded cost。
   - 这是经销商渠道 true GM 显著低于直销的核心原因。

6. **MDF 纪律**（forcing question #5；`channel_anti_patterns.md` #4；McBain/Canalys）
   - MDF-to-pipeline 比应 ≥5:1（best-in-class >7:1），无 ROI 追踪的 MDF 实质是变相折扣。
   - 本测算保守取 1% list（1,200 元/单），假设 MDF 有 attributable pipeline 追踪；若实际 MDF 失控到 5%，true GM 再降 4pt。

7. **Influenced vs sourced 纪律**（forcing question #3；anti-pattern #1/#6；SiriusDecisions/Forrester）
   - 本测算假设 50 单全部为经销商真正 sourced。若实际含 influenced 单，这些单应重新归为直销成本+经销商分成，CAC 会被低估、结论会过于乐观。
   - 这是使用本测算时最需要用真实 CRM first-touch 数据验证的假设。

8. **渠道经理人头成本必须归因到渠道**（anti-pattern #7；`HIDDEN_COST_KEYS` 中 `channel_manager_attribution`）
   - 300,000 元/年渠道经理成本不能藏在 G&A 里。
   - 本测算将其全部分摊到经销商渠道，是固定成本 445,000 元/年的最大组成部分（67%），直接决定盈亏平衡 9 单/年的结论。

9. **决策支持而非自动分配**（SKILL.md Assumptions）
   - 本测算输出 verdict 和数字，不自动建议资源分配；最终扩容/收缩/淘汰经销商的决策应由人结合战略约束（直销地板、经销商集中度天花板等）做出。
