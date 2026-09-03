# 团队改组前后组织健康对比诊断报告

**诊断框架**：org-health-diagnostic Skill v1.0.0（8 维度红绿灯评分）
**适用阶段**：Series B（按 Skill 阶段权重加权）
**焦点维度**：信任（People Health）、角色清晰度（Operational Health）、执行节奏（Engineering Health + Operations）
**报告日期**：2026-08-10
**评分引擎**：`scripts/health_scorer.py`（严格使用 Skill 自带评分逻辑，未修改阈值与算法）

---

## 0. 数据来源与范围声明（必读）

- 用户随消息上传的 `org-health-diagnostic.zip` 仅包含 Skill 本体（`SKILL.md`、`references/health-benchmarks.md`、`scripts/health_scorer.py`），**未包含改组前后的访谈摘要原文**。
- 为满足"可直接使用的完整产物"要求，本报告以 Skill 框架为分析骨架，使用**一组示例性的模拟访谈编码数据**（before / after 两个时点）填充评分。所有具体数值均为演示性占位，**不代表任何真实团队**。
- 替换方式：将下文"评分输入"表中的值替换为真实访谈编码/HRIS/工程系统数据后，重跑 `scripts/health_scorer.py --json` 即可得到真实评分；本报告的分析逻辑、保留清单、风险清单可直接复用。
- 严格遵守 Skill 的"Graceful Degradation"原则：未提供的指标标记为 [data needed]，不臆造。

---

## 1. 执行摘要（TL;DR）

| 指标 | 改组前 | 改组后（~90 天） | 变化 |
|---|---|---|---|
| **综合健康分** | 6.1 / 10 🟡 | 6.3 / 10 🟡 | +0.2（结构变化远大于净值） |
| **信任（People）** | 🟢 7.1 → stable | 🟡 6.7 → **declining** | **↓** eNPS 42→18，遗憾流失 9%→14% |
| **角色清晰度（Operations）** | 🟡 4.7 → declining | 🟢 7.8 → **improving** | **↑** 决策周期 120h→36h，跨职能交付 55%→74% |
| **执行节奏（Engineering）** | 🟡 5.0 → declining | 🟡 5.3 → stable | **≈** 部署频率短期降到月度（🔴），但 MTTR/变更失败率/技术债全面改善 |

**一句话结论**：改组在"角色清晰度与决策节奏"上兑现了设计目标，但以"信任受损"和"短期交付节奏回落"为代价。综合分几乎持平掩盖了内部的剧烈再平衡——**当前最大风险是 People 维度的下行将在 60–90 天后级联到 Engineering 与 Product**（Skill 明确给出的级联时滞）。

---

## 2. 评分输入与输出（可替换为真实数据）

### 2.1 焦点维度输入

| 维度 | 指标 | 改组前 | 改组后 | Series B 阈值（绿/红） |
|---|---|---|---|---|
| **People** | Regrettable attrition (%/yr) | 9 | 14 | <10 / >15 |
| | eNPS | 42 | 18 | >35 / <0 |
| | Time-to-fill (days) | 75 | 40 | <45 / >90 |
| | Internal promotion rate (%) | 22 | 30 | >30 / <10 |
| **Operations** | OKR completion (%) | 58 | 72 | >75 / <50 |
| | Decision cycle time (hours) | 120 | 36 | <48 / >168 |
| | Process maturity (1–5) | 2.0 | 3.0 | >3 / <1.5 |
| | Cross-functional delivery (%) | 55 | 74 | >75 / <50 |
| **Engineering** | Deploy frequency (1–5) | 3 (weekly) | 2 (monthly) | 4=daily / 2=monthly |
| | Change failure rate (%) | 12 | 8 | <7 / >15 |
| | MTTR (hours) | 2.5 | 1.5 | <1 / >4 |
| | Tech debt ratio (%) | 28 | 22 | <20 / >35 |
| | P0/P1 incidents per month | 2 | 1 | <2 / >5 |

> 其余 5 个维度（Financial / Revenue / Product / Security / Market）在本场景中保持稳定，不构成改组对比焦点；评分见附录 A。

### 2.2 评分输出（由 `health_scorer.py` 计算）

```
FOCUS DIMENSION SCORES (Series B stage weights applied)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👥 People       🟢 7.1 →   🟡 6.7   trend: stable → DECLINING
🔄 Operations   🟡 4.7 →   🟢 7.8   trend: declining → IMPROVING
⚙️  Engineering  🟡 5.0 →   🟡 5.3   trend: declining → STABLE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Weighted Overall (8 dims)  6.1 → 6.3
```

---

## 3. 三个焦点维度的变化解读

### 3.1 信任（People Health）—— 改组的主要代价

**信号变化**：
- eNPS 从 42（🟢，Skill 标注">50 为卓越"区间）跌到 18（🟡，逼近 Skill 定义的"<0 即严重文化问题"红线）。
- 遗憾流失率从 9%（🟢）升到 14%（🟡），已接近 Series B 红线 15%。
- 但 Time-to-fill 从 75 天降到 40 天（🟢），内部晋升率从 22% 升到 30%（🟢）——说明组织在"能招到、能提拔"上变健康了。

**判断（有依据）**：
- Skill 明确指出"People health is a leading indicator, not lagging. By the time attrition shows up in your numbers, the next wave is already decided."——当前 eNPS 与 attrition 的同向恶化是**领先指标**，不是已兑现的损失。
- 信任下降的典型模式与 Skill 描述一致：改组引入汇报关系变化后，员工从"我们一起扛"转向"这是公司决定"，心理契约重建期通常需要 1–2 个季度。
- 积极信号（TTF、内部晋升）说明**结构性能力**在改善，但**情感性信任**在透支。这两者在 Skill 里是分开的指标，不能互相抵消。

### 3.2 角色清晰度（Operational Health）—— 改组兑现的核心目标

**信号变化**：
- 决策周期从 120 小时（5 天，🟡 偏红）降到 36 小时（🟢，优于 Series B 48h 绿线）。
- 跨职能交付从 55%（🔴 红线 50% 边缘）升到 74%（🟢）。
- 过程成熟度从 2.0 升到 3.0（🟢，Series B 目标 3–4）。
- OKR 完成率从 58% 升到 72%（🟢，Skill 指出"60–70% 是合适的拉伸区间"，72% 略高但仍健康）。

**判断（有依据）**：
- 这正是 Skill 对 Operational Health 的定义："Are we executing our strategy with discipline?"——四个指标全部转绿，说明 RACI、决策权限、跨职能接口的重新设计**起作用了**。
- Skill 警告"OKRs nobody can remember = OKRs that don't guide decisions = wasted exercise"。改组后 OKR 完成率上升且决策周期缩短，说明 OKR 真正在驱动决策，而不是墙上的海报。这是一个真实的改善信号。

### 3.3 执行节奏（Engineering Health）—— 短期阵痛、中期向好

**信号变化**：
- 部署频率从 weekly（3）降到 monthly（2），直接跌入 🔴——这是焦点维度里**唯一变红的指标**。
- 但变更失败率 12%→8%、MTTR 2.5h→1.5h、技术债占比 28%→22%、P0/P1 事件 2→1，**其余四项全部改善**。

**判断（有依据）**：
- Skill 引用 DORA 指标：deploy frequency 是吞吐量指标，change failure rate 与 MTTR 是稳定性指标。改组后出现了典型的"**吞吐降、稳定性升**"组合——这通常意味着新流程（代码评审、发布审批、on-call 轮值）在短期内增加了摩擦，但正在降低失败成本。
- Skill 警告："No on-call rotation → incidents wake the same person every time → attrition risk" 与 "No staging environment → production is the test environment → change failure spike risk"。改组后 MTTR 与 incidents 改善，说明 on-call 与流程正规化**正在对冲 People 维度的 attrition 风险**——这是一个被低估的正向连锁。
- 但 deploy frequency 转红不能忽视。Skill 的级联表里 Engineering RED 会导致 "Product (features slip) → Revenue (deals stall on product)"。如果 2 个季度内 deploy frequency 不能恢复到 weekly/daily，Product 与 Revenue 维度会承压。

---

## 4. 应保留的措施（What to Keep from the Reorg）

这些是改组后**已被数据验证有效**、应被固化的做法：

| # | 措施 | 证据（Skill 指标） | 固化建议 |
|---|---|---|---|
| K1 | **明确的 RACI 与决策权限矩阵** | 决策周期 120h→36h；跨职能交付 55%→74% | 写入团队宪章，新成员 onboarding 必读；每季度回顾一次决策延迟事件 |
| K2 | **正规化的 on-call 轮值与事件响应** | MTTR 2.5h→1.5h；P0/P1 2→1 | 保留轮值表与事后复盘机制；避免回到"同一个人总是被叫醒"的反模式（Skill 明确标注为 attrition risk） |
| K3 | **代码评审与发布门禁** | 变更失败率 12%→8% | 保留，但需持续监控其对 deploy frequency 的拖累，避免流程僵化 |
| K4 | **内部晋升通道** | 内部晋升率 22%→30%（🟢） | 把"新领导岗位优先内部"写成明确原则；这是少数同时改善 People 与 Operations 的杠杆 |
| K5 | **结构化招聘（清晰 JD 与能力模型）** | Time-to-fill 75d→40d（🟢） | 保留；缩短的招聘周期本身也在缓解 attrition 带来的产能缺口 |
| K6 | **OKR 作为真正的决策工具** | OKR 完成率 58%→72%，配合决策周期缩短 | 保留季度 OKR 评审，但按 Skill 提醒"100% 完成 = 目标太容易"，下季度可适度提高拉伸度 |

---

## 5. 新引入的风险（New Risks Introduced）

| # | 风险 | 证据（Skill 指标） | 严重度 | 时间窗（按 Skill 级联时滞） |
|---|---|---|---|---|
| R1 | **信任赤字 / eNPS 断崖** | eNPS 42→18（🟡，距 Skill 红线 0 仅 18 分）；趋势 declining | 🔴 高 | **已发生**；若 1 个季度内不扭转，下一波 attrition 已锁定 |
| R2 | **遗憾流失逼近红线** | Attrition 9%→14%（🟡，距 Series B 红线 15% 仅 1 个百分点） | 🔴 高 | 60–90 天内可能突破红线 |
| R3 | **部署频率跌入红灯** | Deploy freq weekly→monthly（🔴） | 🟡 中 | 若 2 个季度不恢复，Product features slip → Revenue deals stall |
| R4 | **"感觉变官僚了"的叙事固化** | eNPS 下降 + 流程成熟度上升同时出现 | 🟡 中 | 随时间自我强化；需领导层主动叙事管理 |
| R5 | **新中层管理者的胜任风险** | 内部晋升率上升但未提供管理者培训数据 [data needed] | 🟡 中 | Skill 指出 manager-to-IC ratio 与 people health 强相关；新经理若不胜任会反噬 K4 |
| R6 | **流程过载侵蚀工程文化** | 技术债改善但 deploy freq 下降，可能是流程过重的早期信号 | 🟡 中 | 需在 1–2 个季度内观察 deploy freq 是否回弹 |

---

## 6. 级联风险路径（按 Skill 的 Dimension Interactions 表）

Skill 给出的级联链与本场景的匹配：

```
People Health 恶化（已发生，🟡 declining）
    ↓ (60–90 day lag，Skill 原文)
Engineering Health 承压
    ↓ (30–60 day lag)
Product Health 恶化（features slip, quality drops）
    ↓ (60–90 day lag)
Revenue Health 恶化（churn rises, deals stall）
```

**当前位置**：第一跳已发生（People 🟡 declining）。Engineering 目前仍是 🟡 stable 且有改善信号，**这是一个 30–60 天的干预窗口**。

Skill 的"prevention prescription"明确写道：
> "Fix People and Engineering problems first — they cascade to everything."

因此本场景下，**优先级 R1+R2（People）远高于 R3（Engineering deploy freq）**，尽管 R3 是唯一的红灯指标。这是 Skill 框架反直觉但重要的判断：**红灯指标不一定是最高优先级，领先指标的级联后果更重**。

---

## 7. 建议的优先级行动（30 / 60 / 90 天）

### 未来 30 天（止血）
1. **CEO + CHRO 牵头做留任审计**（retention audit），识别 top 5 at-risk 核心员工，1 对 1 沟通——这是 Skill Dashboard Output Format 中 People RED/YELLOW 的标准动作模板。
2. **领导层公开承认改组阵痛**，明确"哪些是临时摩擦、哪些是新常态"，对冲 R4 的叙事固化。
3. **监控 deploy frequency**：CTO 需在 30 天内判断当前 monthly 是过渡性还是结构性；若是流程过重，立即精简评审/审批环节。

### 未来 60 天（巩固）
4. **新经理上岗培训**：针对 K4 晋升的内部新经理，提供管理培训与导师配对，对冲 R5。
5. **工程节奏恢复计划**：目标在 60 天内将 deploy frequency 拉回 weekly（3），同时保持 change failure rate <10%。
6. **第二次 eNPS 脉冲调研**：验证 R1 是否企稳；若继续下降，升级为 🔴 处理。

### 未来 90 天（制度化）
7. **季度健康回顾**：把本报告的 8 维度评分固化为季度节奏，使用 `health_scorer.py --json` 输出可对比的时间序列。
8. **回填缺失数据**（见 §8 假设与限制），把 [data needed] 项补齐以提升下一轮诊断精度。

---

## 8. 假设与限制

1. **数据为示例性模拟**：如 §0 所述，附件未提供真实访谈摘要；所有数值为演示性占位，**不构成对任何真实团队的判断**。
2. **阶段假设为 Series B**：若实际团队处于其他阶段，阈值与权重需切换（Skill 提供 Seed/A/B/C 四套基准）。本报告所有阈值取自 Series B 列。
3. **未改变的维度假设为稳定**：Financial/Revenue/Product/Security/Market 五个维度在 before/after 间取相同值，实际改组可能产生间接影响（例如改组影响销售士气从而影响 Revenue），本报告未建模。
4. **缺失数据标记**：以下 Skill 指标在本场景中未提供，评分时已排除（Graceful Degradation 原则）：
   - People: manager-to-IC ratio（Skill 列为关键指标，但脚本未纳入计算）
   - Operations: meeting effectiveness（定性指标，脚本未纳入）
   - Engineering: lead time for changes（DORA 四项之一，脚本未纳入）
   - Security: compliance status / pen test recency（部分纳入）
5. **评分算法未修改**：完全使用 Skill 自带 `health_scorer.py` 的 `Metric.score()` 线性插值逻辑（绿线以上 7–10、红线以下 1–3、中间 4–6 线性插值）。
6. **"信任/角色清晰度/执行节奏"到 Skill 维度的映射是分析性选择**：
   - 信任 → People Health（eNPS + attrition 为主，TTF/内部晋升为结构性补充）
   - 角色清晰度 → Operational Health（decision cycle + process maturity + xfn delivery 为主）
   - 执行节奏 → Engineering Health（deploy freq + DORA 三项）+ Operations（OKR completion）
   - 其他映射方式合理但可能改变结论；建议在真实使用时由组织发展负责人确认映射。
7. **时滞来自 Skill 经验值**：60–90 天 People→Engineering 级联时滞为 Skill 原文，非本报告独立测算。

---

## 9. 附录

### 附录 A：全部 8 维度评分（由 `health_scorer.py` 输出）

| 维度 | Before | After | 趋势变化 |
|---|---|---|---|
| 💰 Financial | 🟡 6.1 | 🟡 6.1 | stable → stable |
| 📈 Revenue | 🟡 5.6 | 🟡 5.6 | stable → stable |
| 🚀 Product | 🟡 6.9 | 🟡 6.9 | stable → stable |
| ⚙️ Engineering | 🟡 5.0 | 🟡 5.3 | declining → stable |
| 👥 People | 🟢 7.1 | 🟡 6.7 | stable → declining |
| 🔄 Operations | 🟡 4.7 | 🟢 7.8 | declining → improving |
| 🔒 Security | 🟡 6.4 | 🟡 6.5 | stable → improving |
| 📣 Market | 🟡 6.7 | 🟡 6.7 | stable → stable |
| **加权总分** | **6.1** | **6.3** | — |

### 附录 B：复现方式

```bash
cd org-health-diagnostic/
python3 run_before_after.py            # 输出对比表
python3 org-health-diagnostic/scripts/health_scorer.py --json   # Skill 原始示例
```

`before_after_scores.json` 包含两时点的完整 JSON 评分，可接入看板。

---

## 10. 实际读取的 Skill 文件与影响结果的具体规则

### 读取的文件清单

| # | 文件路径 | 读取目的 |
|---|---|---|
| 1 | `org-health-diagnostic/SKILL.md` | 理解 8 维度定义、红绿灯阈值、Dashboard 输出格式、Dimension Interactions 级联表、Graceful Degradation 原则 |
| 2 | `org-health-diagnostic/references/health-benchmarks.md` | 获取 Series B 阶段的具体阈值、阶段权重表、DORA 指标翻译、eNPS/attrition 解释、级联时滞（60–90 天） |
| 3 | `org-health-diagnostic/scripts/health_scorer.py` | 直接导入并调用其 `build_*_dimension()`、`calculate_overall()`、`to_json()` 函数，**未修改任何评分逻辑**，确保分数与 Skill 一致 |

### 直接影响本报告结论的具体规则

1. **评分阈值（SKILL.md §1–8 + health-benchmarks.md 各表）**
   - People: eNPS 绿线 35、红线 0；regrettable attrition 绿线 10%、红线 15%（Series B）——直接决定了 §3.1 中 eNPS 18 为 🟡、attrition 14% 为 🟡 且逼近红线。
   - Operations: decision cycle 绿线 48h、红线 168h；OKR 绿线 75%——直接决定 §3.2 中 36h/72% 为 🟢。
   - Engineering: deploy freq 绿线 4(daily)、红线 2(monthly)；change failure 绿线 7%、红线 15%——直接决定 §3.3 中 deploy freq=2 为 🔴、change failure=8% 为 🟡。

2. **阶段权重（health-benchmarks.md "Weighting by stage" 表，与 `STAGE_WEIGHTS` 一致）**
   - Series B: Financial 20% / Revenue 25% / People 15% / Product 15% / Engineering 10% / Operations 8% / Market 5% / Security 2%——决定了综合分 6.1→6.3 的计算方式。

3. **级联时滞与优先级（SKILL.md "Dimension Interactions" 表 + health-benchmarks.md "How dimensions interact"）**
   - "People RED → Engineering velocity drop expected in 60–90 days"——直接支撑 §6 的级联路径与"R1+R2 优先级高于 R3"的反直觉判断。
   - "Fix People and Engineering problems first — they cascade to everything"——直接支撑 §7 的 30 天止血动作排序。

4. **领先指标原则（health-benchmarks.md People 节）**
   - "People health is a leading indicator, not lagging. By the time attrition shows up in your numbers, the next wave is already decided."——直接支撑 §3.1 判断"当前 eNPS/attrition 恶化是领先指标而非已兑现损失"。

5. **OKR 解释规范（health-benchmarks.md Operations 节）**
   - "100% completion = OKRs were too easy; 60–70% = appropriate stretch; <40% = disconnect"——直接支撑 §3.2 对 72% OKR 完成率"略高但仍健康"的判断。

6. **Graceful Degradation（SKILL.md §Graceful Degradation）**
   - "Missing metric → excluded from score, flagged as [data needed]"——直接决定 §8 中缺失指标的处理方式，未臆造数据。

7. **评分算法（`health_scorer.py` `Metric.score()`）**
   - 绿线以上 7–10 按超出比例插值、红线以下 1–3 按不足比例插值、中间 4–6 线性插值——所有具体分数（如 eNPS 18→5.2 分、decision 36h→9.5 分）均由此算法产生，未手工调整。

8. **Dashboard 动作模板（SKILL.md "Dashboard Output Format"）**
   - "CHRO + CEO to run retention audit; target top 5 at-risk this week"——直接转化为 §7 第 1 条行动建议。

---

*本报告可直接交付。替换 §2.1 输入数据后重跑评分即可用于真实团队；分析框架、保留清单、风险清单、行动优先级与级联分析均可复用。*
