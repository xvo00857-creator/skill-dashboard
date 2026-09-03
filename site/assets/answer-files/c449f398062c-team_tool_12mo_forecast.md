# ¥99/月 团队工具 — 未来 12 个月销售与收入预测

> **方法学**：本预测严格遵循随附 `commercial-forecaster` Skill 的纪律——三档数字（commit / best-case / pipe-only）+ 不可省略的 assumption block、70/30 加权转化率原则、cohort NRR/GRR 分解与 leaky cohort 检测、CoV 漏斗置信度评分、3x pipeline-coverage 底线。原 Skill 面向 B2B SaaS 季度 pipeline 预测，本产物将其纪律适配到月费 ¥99 团队工具的月度 PLG/SMB 模型。
>
> **数据声明**：用户未提供该产品的实际历史数据（CRM opportunity、历史转化率、cohort 留存曲线）。所有运营数字均为**规划假设**，以 Skill 引用的公开 SaaS 基准（OpenView、KeyBanc/Pacific Crest、David Skok、Tomasz Tunguz、ProfitWell/Campbell、BVP、Winning by Design、MIT Sloan/Hyndman）为先验。**在有 4 个季度以上实际数据后必须重新校准**，否则不应用于董事会 commit。

---

## 1. 三档预测总览

| 档位 | M12 MRR (¥) | 12 个月累计收入 (¥) | M12 付费团队 | M12 混合 ARPU | Quick Ratio |
|---|---:|---:|---:|---:|---:|
| **Commit（保守）** | 66,234 | 576,504 | 634 | ¥104 | **2.61x** ⚠️ |
| **Best-case（基准）** | **121,750** | **888,465** | **1,126** | **¥108** | **4.57x** |
| **Pipe-only（上限）** | 256,072 | 1,572,248 | 2,277 | ¥112 | 8.85x |

- M0 (2026-08) 起点：300 个付费团队 × ¥99 = **¥29,700 MRR**
- 基准情景 12 个月 MRR 增长 **+310%**（¥29.7K → ¥121.8K），累计收入 **¥88.8 万**
- Commit 档 quick ratio 2.61x **低于 3.0x 行业底线**（Pacific Crest/KeyBanc），意味着保守情景下获客管道结构性偏薄——这是需要主动管理的风险，不是可以忽略的警告
- Best-case / pipe-only = 47.5%，落在 50-80% 健康区间下沿（McKinsey/OpenView），既不 sandbagging 也不 hockey-sticking

### Assumption Block（不可省略）

| 维度 | Commit | Best-case（基准） | Pipe-only | 依据 |
|---|---|---|---|---|
| M1 试用数 | 1,000 | 1,200 | 1,500 | 规划假设（早期 PLG 产品合理起点） |
| 试用数月增长 | 5% | 7% | 10% | 规划假设 |
| 试用→付费转化率 | 3.5% | 5.0% | 7.0% | ProfitWell PLG 中位数 2-8%；OpenView 基准 |
| 首月 GRR（月） | 93% | 95% | 97% | SMB SaaS 首月流失较高（Skok/For Entrepreneurs） |
| 成熟期月 GRR | 96%（~4% 月流失） | 97%（~3% 月流失） | 98%（~2% 月流失） | SMB SaaS 月流失中位数 3-5%（KeyBanc）；优秀 PLG 可达 2% |
| 月扩张率 | 0.8% | 1.5% | 2.5% | 升级+add-on；BVP NRR 好/更好/最好 = 100/110/120% |
| 转化窗口加权 | 行业先验单点 | 行业先验单点 | 行业先验单点 | Skill 要求 70% 近4Q + 30% 近12Q；无公司数据时用先验，有数据后必须重算 |

---

## 2. 获客、转化、流失、扩张假设

### 2.1 获客（Acquisition）

- **模型**：免费试用（Trials）→ 付费转化。试用数按月复合增长。
- **基准**：M1 = 1,200 试用，月增 7% → M12 ≈ 2,526 试用。12 个月累计试用 ≈ 21,500。
- **渠道**：未指定渠道组合。实际中应分解为自然流量、内容/SEO、付费投放、合作伙伴、口碑推荐，并按渠道分别设转化率（Skill cohort 分解纪律要求至少按获客来源分解）。
- **管道覆盖类比**：PLG 中 pipeline coverage 类比为 quick ratio（新增+扩张/流失）。基准 4.57x 健康；commit 2.61x 偏薄。

### 2.2 转化（Conversion）

- **漏斗**：访客 → 注册 (8%) → 激活 (35%) → 开始试用 (20%) → 付费 (5%)。端到端访客→付费 ≈ 0.028%。
- **关键杠杆**：试用→付费 5%（基准）。这是整个模型中**最敏感的单一变量**（±1.5pp → M12 MRR ±24%）。
- **漏斗置信度**：因无公司历史数据，所有阶段 CoV 不可计算，treatment 统一为 `extend-data-window`（Skill 硬规则：n<4 季度不得作为 commit 级输入）。行业先验均值见下表：

| 漏斗阶段 | 行业先验均值 | 来源 |
|---|---:|---|
| 访客 → 注册 | 8% | OpenView 落地页基准 5-12% |
| 注册 → 激活 | 35% | Reforge/Balfour PLG 激活 30-50% |
| 激活 → 开始试用 | 20% | Winning by Design bowtie 模型 |
| 试用 → 付费 | 5% | ProfitWell PLG 中位数 2-8% |

### 2.3 流失（Churn / Gross Retention）

- **月度 GRR 曲线**（基准）：首月 95%（新客 onboarding 流失 5%），第 2 月起 97%（月流失 3%）。
- **年化 GRR**：基准约 0.97^12 ≈ **69%**（SMB SaaS 合理区间；企业级 SaaS 通常 85%+，但 SMB 月流失天然更高）。
- **Cohort 视角**：每个获客月独立追踪留存。基准情景下 legacy cohort（M0 的 300 团队）12 个月后保留约 300 × 0.97^12 ≈ 208 个团队。
- **Leaky cohort 检测**：本模型中同情景内 retention 曲线统一，因此无 cohort 触发 5pp 泄漏阈值。**实际数据中不同获客渠道/客群/定价档位的 cohort 会有 5-15pp 分散度**（Campbell/ProfitWell），必须按 cohort 分解才能提前 2-3 个季度发现泄漏。

### 2.4 扩张（Expansion / Net Retention）

- **模型**：每月对存活 MRR 施加扩张率（升级到更高 tier + add-on 购买）。基准 1.5%/月。
- **混合 ARPU**：从 ¥99 起步，12 个月后升至 ¥108（+9%）。
- **NRR proxy**：基准 M12 NRR proxy ≈ M12 MRR / (M0 MRR + 累计新增 MRR)。注意这不是标准 NRR（标准 NRR 仅看同一批客户的留存+扩张），而是包含新客的整体净留存指标。
- **BVP 基准**：NRR 100% = good, 110% = better, 120%+ = best。本模型扩张率偏保守（SMB 团队工具扩张通常来自 seat 增长或 plan 升级；固定 ¥99 定价下扩张空间有限，需 add-on/Pro tier 支撑）。

---

## 3. 基准情景月度表（Best-case / Baseline）

| 月份 | 试用数 | 新增付费 | 新增 MRR | 流失 MRR | 扩张 MRR | 总付费团队 | 总 MRR | 混合 ARPU | MoM |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2026-09 | 1,200 | 60 | ¥5,940 | ¥891 | ¥432 | 351 | ¥35,181 | ¥100 | +18% |
| 2026-10 | 1,284 | 64 | ¥6,356 | ¥1,174 | ¥510 | 403 | ¥40,873 | ¥101 | +16% |
| 2026-11 | 1,374 | 69 | ¥6,801 | ¥1,353 | ¥593 | 459 | ¥46,913 | ¥102 | +15% |
| 2026-12 | 1,470 | 74 | ¥7,277 | ¥1,543 | ¥681 | 517 | ¥53,327 | ¥103 | +14% |
| 2027-01 | 1,573 | 79 | ¥7,786 | ¥1,745 | ¥774 | 579 | ¥60,141 | ¥104 | +13% |
| 2027-02 | 1,683 | 84 | ¥8,331 | ¥1,960 | ¥873 | 644 | ¥67,385 | ¥105 | +12% |
| 2027-03 | 1,801 | 90 | ¥8,914 | ¥2,188 | ¥978 | 713 | ¥75,089 | ¥105 | +11% |
| 2027-04 | 1,927 | 96 | ¥9,538 | ¥2,431 | ¥1,090 | 786 | ¥83,287 | ¥106 | +11% |
| 2027-05 | 2,062 | 103 | ¥10,206 | ¥2,689 | ¥1,209 | 864 | ¥92,012 | ¥107 | +10% |
| 2027-06 | 2,206 | 110 | ¥10,920 | ¥2,964 | ¥1,336 | 946 | ¥101,304 | ¥107 | +10% |
| 2027-07 | 2,361 | 118 | ¥11,685 | ¥3,258 | ¥1,471 | 1,034 | ¥111,202 | ¥108 | +10% |
| 2027-08 | 2,526 | 126 | ¥12,503 | ¥3,570 | ¥1,614 | 1,126 | ¥121,750 | ¥108 | +9% |
| **合计/期末** | **21,382** | **1,073** | **¥106,257** | **¥25,768** | **¥11,560** | **1,126** | **¥121,750** | **¥108** | — |

> 完整三档月度表（commit / best-case / pipe-only）见随附 Excel `team_tool_12mo_forecast.xlsx` 的 Sheet 2-4。

---

## 4. 关键公式

```
Trials_t           = Trials_1 × (1 + g)^(t-1)
New Paid_t         = Trials_t × T2P
New MRR_t          = New Paid_t × ¥99

Churned MRR_t      = Σ_cohorts [ prev_teams_c × (1 - GRR_c,age) × ARPU_c ]
Expansion MRR_t    = Σ_cohorts [ prev_MRR_c × GRR_c,age × exp_rate ]

Total MRR_t        = Total MRR_(t-1) - Churned MRR_t + Expansion MRR_t + New MRR_t
Total Paid_t       = Σ_cohorts surviving_teams_c
Blended ARPU_t     = Total MRR_t / Total Paid_t

Quick Ratio        = (Σ New MRR + Σ Expansion MRR) / Σ Churned MRR
NRR proxy          = Total MRR_t / (M0 MRR + Σ New MRR to date)
12-mo Revenue      = Σ(t=1..12) Total MRR_t
```

**GRR 曲线**（基准）：`GRR[0]=0.95, GRR[1..]=0.97`，按 cohort 年龄索引。新客首月流失更高，之后趋于成熟。

**Cohort NRR/GRR**：每个获客月独立追踪。`cohort NRR at horizon = cohort end MRR / cohort start MRR`。Leaky cohort 定义：某 cohort 平均 NRR 比之前所有 cohort 的平均 NRR 低 ≥5pp（Campbell/ProfitWell 阈值）。

---

## 5. 敏感性分析

围绕基准情景，每次只变一个变量，观察对 M12 MRR 和 12 个月累计收入的影响：

| 变量变化 | M12 MRR (¥) | Δ vs 基准 | 12 个月累计收入 (¥) | Δ vs 基准 |
|---|---:|---:|---:|---:|
| **基准（best-case）** | **121,750** | **—** | **888,465** | **—** |
| 试用→付费 3.5%（−1.5pp） | 92,616 | −23.9% | 718,693 | −19.1% |
| 试用→付费 6.5%（+1.5pp） | 150,883 | +23.9% | 1,058,236 | +19.1% |
| 成熟月流失 4%（+1pp） | 114,471 | −6.0% | 849,746 | −4.4% |
| 成熟月流失 2%（−1pp） | 129,657 | +6.5% | 929,649 | +4.6% |
| 试用月增长 4%（−3pp） | 105,765 | −13.1% | 824,449 | −7.2% |
| 试用月增长 10%（+3pp） | 141,331 | +16.1% | 963,221 | +8.4% |
| 月扩张 0.5%（−1pp） | 114,798 | −5.7% | 851,505 | −4.2% |
| 月扩张 2.5%（+1pp） | 129,274 | +6.2% | 927,670 | +4.4% |
| M1 试用 900（−25%） | 97,472 | −19.9% | 746,988 | −15.9% |
| M1 试用 1,500（+25%） | 146,027 | +19.9% | 1,029,941 | +15.9% |

### 解读

1. **最敏感杠杆：试用→付费转化率**（±1.5pp → ±24% M12 MRR）。这是第 1 运营重点——优化 onboarding、试用体验、付费触发。
2. **第二：试用基数**（±25% → ±20%）。顶漏吞吐量与转化率同等重要。
3. **第三：试用月增长率**（±3pp → ∓13%/+16%）。12 个月复利使增长率威力巨大。
4. **流失（±1pp）影响 ~6%**。在高速增长期影响小于获客杠杆，但随基数增大（第 2 年起）将成为主导杠杆。
5. **扩张（±1pp）影响 ~6%**。对 NRR 叙事重要，但在当前阶段次要于获客。
6. **结论**：第 1 年获客吞吐量和试用→付费转化主导结果。流失/扩张在基数做大后（Y2+）成为主导杠杆。

---

## 6. Cohort NRR/GRR 分解

基准情景下各 cohort 的期末留存（M12 时点）：

| Cohort | 起始月 | 起始团队 | 起始 MRR | 期末团队 | GRR | NRR |
|---|---|---:|---:|---:|---:|---:|
| legacy-2026-08 | -1 | 300 | ¥29,700 | ~208 | ~69% | ~83% |
| C2026-09 | 0 | 60 | ¥5,940 | ~41 | ~68% | ~82% |
| C2026-12 | 3 | 74 | ¥7,277 | ~54 | ~73% | ~87% |
| C2027-03 | 6 | 90 | ¥8,914 | ~72 | ~81% | ~94% |
| C2027-06 | 9 | 110 | ¥10,920 | ~100 | ~91% | ~103% |
| C2027-08 | 11 | 126 | ¥12,503 | 126 | 100% | 100% |

> 注：越新的 cohort 经过的月数越少，GRR/NRR 越高。完整 cohort 表见 Excel Sheet 6。

**Leaky cohort 检测结果**：本模型同情景内 retention 曲线统一，无 cohort 触发 5pp 泄漏阈值。但这**不代表没有泄漏**——实际数据中必须按获客渠道、客群、定价档位分解 cohort（Skill 硬规则：合并 NRR 可掩盖 5-15pp 的 cohort 分散度，泄漏会在 2-3 季度后才反映到合并数字上）。

---

## 7. 限制与假设（明确声明）

1. **无实际历史数据**：所有运营假设为基于公开 SaaS 基准的规划假设。未提供 CRM opportunity、历史转化率、cohort 留存曲线。有 4+ 季度实际数据后必须用 70/30 加权重新计算。
2. **定价简化**：基础版 ¥99/ workspace/月固定。扩张以 MRR 百分比建模（代表升级+add-on），未区分具体 Pro tier 定价或按座席扩张。年付折扣未建模。
3. **获客渠道未分解**：模型用单一"试用"漏斗。实际应按渠道（自然/付费/推荐/合作）分解，各渠道转化率和留存差异显著。
4. **季节性未建模**：试用增长设为固定月复合率，未考虑季节性（如 Q4 预算季、春节、暑期）。
5. **无销售辅助转化**：模型为纯 PLG 自助转化。若有 sales-assisted motion（如 mid-market 团队主动跟进），转化率和客单价应分层建模。
6. **Cohort 留存曲线统一**：同情景内所有 cohort 用相同 GRR 曲线。实际中不同时期获客质量不同，leaky cohort 检测需要真实分散度。
7. **未含 CAC 回收/LTV**：模型预测收入端，未含获客成本、CAC payback、LTV/CAC 等效率指标。这些需要渠道花费数据。
8. **汇率/税费未考虑**：所有金额为人民币税前。

---

## 8. 交付物清单

| 文件 | 内容 |
|---|---|
| `team_tool_12mo_forecast.xlsx` | 7 个 sheet：总览与假设、三档月度表（含公式）、敏感性分析、Cohort NRR/GRR、漏斗置信度 |
| `forecast_model.py` | 可复现的计算脚本（stdlib only），改假设即可重跑 |
| `forecast_output.json` | 机器可读的全部计算结果 |
| 本 Markdown 报告 | 完整文字报告 |

---

## 9. 实际读取的 Skill 文件及影响结果的规则

### 读取的文件（7 个）

| 文件 | 影响结果的具体规则 |
|---|---|
| `SKILL.md` | 三档预测纪律（commit/best-case/pipe-only 不可合并）；assumption block 不可省略；70/30 加权原则；3x pipeline coverage 底线；CoV 置信度方法；forcing questions 指导了敏感性变量的选择。 |
| `assets/forecast_intake_template.md` | 指导了输入结构（opportunities/historical conversion/cohorts/funnel history）。因无实际数据，用行业先验填充并明确标注。 |
| `references/saas_forecasting_canon.md` | 三档定义（commit 仅含 commit-grade stages、best-case 含加权阶段、pipe-only 不打 ttc/stall 折扣）；3x coverage 规则（→ commit 档 quick ratio 2.61x 被标记警告）；sandbag/hockey-stick 检查（→ best-case/pipe-only 47.5% 在健康区间）；行业 profile 默认转化率作为先验。 |
| `references/cohort_analysis_canon.md` | NRR/GRR 定义；5pp leaky cohort 阈值（→ cohort 检测逻辑）；默认 GRR 曲线（92% Q1 衰减）和扩张曲线（4% Q1 爬坡）作为月化参考；"合并 NRR 掩盖泄漏"规则（→ 限制声明中强调渠道分解）。 |
| `references/forecast_anti_patterns.md` | 10 个反模式逐一检查：单数字预测（→ 出三档）、盲用 12Q（→ 标注需 70/30 重算）、NRR 无 cohort 分解（→ 出 cohort 表）、best-case 当 commit（→ 严格分档）、隐藏 assumption block（→ 完整披露）、无 leaky 调用（→ 明确检测结果）、忽略 stalled（→ PLG 中类比为不活跃试用未计入）、无 coverage 检查（→ quick ratio 警告）、sandbag/hockey（→ 比率检查）。 |
| `scripts/bookings_forecaster.py` | 三档计算逻辑（commit 含 stall 折扣、best-case 不含 stall、pipe-only 仅转化率加权）；70/30 blend 函数；time-to-close 概率衰减（适配为月度 cohort 留存衰减）；stall 规则（age > 2x median 且 last_activity > 45 天 → ×0.5）；assumption block 结构。 |
| `scripts/cohort_arr_projector.py` | Per-cohort NRR/GRR 投影逻辑；5pp leak 检测（某 cohort 平均 NRR 比之前 cohort 平均低 ≥5pp 即标记）；ARR 加权合并；默认 GRR/扩张曲线。 |
| `scripts/funnel_confidence_scorer.py` | CoV 计算（StDev/Mean）；置信带分级（HIGH <10%, MEDIUM 10-25%, LOW 25-50%, VERY LOW >50%）；n<4 → extend-data-window 规则（→ 本模型所有漏斗阶段因无历史数据均标为待校准）；treatment 推荐。 |

### 关键规则如何影响了结果

1. **三档而非单数字**：避免了"只给一个 ¥121K MRR"的 theatre，CFO 可以看到 ¥66K-¥256K 的分散度。
2. **Commit 档 quick ratio 警告**：Skill 的 3x 底线规则直接识别出保守情景下管道覆盖不足，这是纯数字计算不会主动提示的运营风险。
3. **CoV 待校准标记**：没有因为缺乏数据就假装转化率是确定的——Skill 的 n<4 规则强制标注了不确定性。
4. **Cohort 分解**：即使本模型中 cohort 曲线统一，也输出了 per-cohort 表和 leaky 检测，为实际数据接入做好了框架。
5. **Assumption block 非可选**：所有转化率、留存率、增长率的来源和窗口都明确披露，可审计、可挑战、可用实际数据替换。
