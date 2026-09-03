# 供应商筛选 / 评估 / 续约 / 风险管理清单（边界与复杂场景版）

> 本方案严格按 `vendor-management` Skill v2.8.0 的工作流与反模式清单产出。
> **重要前提**：本次没有提供任何真实供应商台账（vendor catalog JSON）、SLA 记录或合规证据；背景已明确"资料缺页、价格不可直接比较、关键合规结论未知"。因此本方案**不输出任何具体供应商的评分、KEEP/REVIEW/REPLACE 结论、认证状态或节省金额**——这些在数据齐备前由脚本确定性产出，不得由 LLM 推断或编造（见 SKILL.md "Assumptions" 与 "Anti-patterns: Score by gut feel"）。

---

## 0. 适用范围与边界声明（先于一切动作）

| 维度 | 在本 Skill 范围内 | **不在本 Skill 范围内**（需转其他流程） |
|---|---|---|
| 供应商绩效评估（已有合同、已有供应商） | ✅ 评分卡 + SLA 追踪 + 风险分类 | ❌ |
| 续约 KEEP/REVIEW/REPLACE 建议 | ✅ 基于脚本输出 | ❌ |
| 第三方风险（TPRM）4 向量分类 | ✅ 数据/财务/运营/监管 | ❌ |
| **新供应商筛选 / RFP / 选型打分** | ❌ | ⚠️ 用户需求中"筛选"一项超出本 Skill，应走采购/RFP 流程（SKILL.md "When NOT to use"） |
| 合同条款谈判、赔偿、法律文本 | ❌ | ⚠️ 法务 / `general-counsel-advisor` |
| 价格对标、议价、SaaS 支出优化 | ❌ | ⚠️ `procurement-optimizer`（SKILL.md "Distinct from"） |
| 内部 SLO / 错误预算设计 | ❌ | ⚠️ `slo-architect` |

**关键取舍**：用户要求"建立筛选、评估、续约和风险管理清单"。其中"评估、续约、风险管理"由本 Skill 覆盖；"筛选"（新供应商引入）本 Skill 不覆盖，但本方案在第 5 节给出**最小衔接清单**（intake 字段与门槛），不替代正式 RFP。

---

## 1. 事实 / 推断 / 待确认（三分法）

### 1.1 事实（来自 Skill 文件本身，可直接引用）

- 评分由 `vendor_scorer.py` 按 5 维度加权产出，权重随 `--profile {saas,fintech,healthcare,enterprise}` 变化；阈值 KEEP ≥75 / REVIEW 50–74 / REPLACE <50。
- SLA 信用赔付触发条件（脚本内置）：`breach_count_12m ≥ 2` **或** 季度实际值偏离目标 > 0.5pp（uptime 类）/ 超目标 0.5 单位（响应时长类）。
- 风险分类 4 向量：数据敏感度、财务敞口（年支出 × tier 系数）、运营依赖（tier-1 + 无 break-glass = Critical）、监管敞口（healthcare 下 PHI 无 HIPAA = Critical；fintech 下 cardholder 无 PCI-DSS = Critical）。
- 总风险 = 4 向量取最差；若有 ≥2 个 High 则升为 Critical。
- 三个脚本均为 stdlib only、确定性、无 LLM 调用；已用 `--sample` 自检通过（仅工具链验证，非用户数据）。

### 1.2 推断（基于 Skill 反模式可合理推导，但需业务侧确认）

- "资料缺页" + "关键合规结论未知" 意味着：在拿到 SOC2 Type II 报告原件（而非问卷自报）之前，任何 tier-1 / 接触 PII 或 PHI 的供应商都应被**临时按 High 风险处理**（依据：`vendor_risk_anti_patterns.md` 第 3 条 "Trust the questionnaire without verification"）。
- "价格不可直接比较" 意味着 commercial 维度（renewal flexibility）可评，但**价格对标/节省金额不可评**——本方案不给出任何节省数字。
- 若存在 auto-renew 且年支出 > $50k 的合同，脚本会自动加注 "renegotiate to manual-renew"；但具体合同是否属于此类需台账确认。

### 1.3 待确认（阻塞项，未确认前不得进入评分阶段）

| # | 待确认项 | 阻塞哪个阶段 | 来源/责任人 |
|---|---|---|---|
| Q1 | tier-1 关键度阈值——按运营依赖（revenue-blocking）还是按年支出？ | 全部 | SKILL.md 强制问题 1；推荐"运营依赖" |
| Q2 | 每个 tier-1 供应商是否有**12 个月内**签发的 SOC2 Type II 报告原件？ | 评分+风险 | 强制问题 2；仅有问卷不算 |
| Q3 | 每个 tier-1 供应商是否有**书面、年度演练过**的 72 小时 break-glass 预案？ | 风险分类 | 强制问题 3 |
| Q4 | 过去 12 个月是否**实际发起过** SLA 信用赔付申请？ | SLA 阶段 | 强制问题 4；若从未发起需审计条款是否过弱 |
| Q5 | 离职/替换供应商的 offboarding 清单（数据删除、权限回收、密钥轮换）是否最新？ | 续约/替换 | 强制问题 5 |
| Q6 | 监管爆炸半径——是否涉及 HIPAA / GDPR / SOX / PCI？决定 `--profile` 取值 | 全部 | 强制问题 6；推荐由合规/法务确认 |
| D1 | 完整 vendor catalog（schema 见 `assets/vendor_catalog_template.md`） | 评分+风险 | 采购/IT/VMO |
| D2 | SLA 记录（vendor, metric, target, actual_last_month, actual_last_quarter, breach_count_12m） | SLA 阶段 | 监控/状态页/工单系统 |
| D3 | 每个供应商的 `data_access` 实际标签（不要猜，需供应商书面确认） | 风险分类 | 供应商 + 安全团队 |
| D4 | `break_glass_plan` 布尔值——true 必须意味着"有书面预案"，不是"觉得能搞定" | 风险分类 | IT/运维 |

> **SKILL.md 强制顺序**："Walk depth-first. Lock 1-3 before opening 4-6." 即 Q1–Q3 未锁定前，不应启动 Q4–Q6，更不应跑脚本。

---

## 2. 冲突识别（本次场景的核心矛盾）

| 冲突 | 说明 | 处置 |
|---|---|---|
| **C1：用户要"筛选" vs Skill 只做"已有供应商绩效"** | SKILL.md 明确 "ongoing vendor performance review, **not** initial selection" | 评估/续约/风险走本 Skill；新供应商引入走采购流程，本方案第 5 节只给衔接门槛 |
| **C2：要评分 vs 无台账数据** | 脚本对缺失字段会用默认值（uptime=0、certs=[]、p90=999h），这会把"未知"误判为"0 分"，构成隐性编造 | **不得**用默认值跑真实供应商；必须先补全 D1–D4 |
| **C3：要"节省金额" vs 价格不可比 + Skill 不做议价** | Skill 不输出节省金额；价格不可比时任何节省数字都是编造 | 本方案不输出任何节省金额；价格对标转 procurement-optimizer |
| **C4：合规结论未知 vs 风险分类要求确定结论** | 风险分类器对缺失 `data_access` 默认返回 Medium（`classify_data_sensitivity` 中 `if not tags: return Medium`），这是"未知即 Medium"，可能低估 | 对 tier-1 / 接触客户数据的供应商，在 D3 确认前**人工上调为 High 并加缓解项**，不直接采信脚本默认 |
| **C5：auto-renew 合同可能已过续约窗口** | 背景未给合同到期日；若有 auto-renew 已在 60–90 天窗口内，延迟决策 = 自动续约 | 第 6 节设停止条件：距到期 <60 天的 auto-renew 立即升级 |

---

## 3. 最小可执行方案（在现有信息下可安全推进的部分）

> 原则：**只做"准备动作"和"框架搭建"，不做"结论产出"**。所有结论性产出（评分卡、SLA 报告、风险矩阵）在第 1.3 节阻塞项清除后由脚本确定性生成。

### 阶段 A — Intake 与台账搭建（可立即开始，不依赖任何外部确认）

1. 复制 `assets/vendor_catalog_template.md` 中的 JSON schema，建立 `vendor_catalog.json` 空模板，字段**一个都不能少**：
   `name, category, annual_spend, contract_end_date, criticality, uptime_pct, support_response_hours_p90, incident_count_last_12m, security_certs, renewal_terms, data_access, break_glass_plan`
2. 数据来源优先级（按模板 "Tips"）：
   - SaaS 管理工具（Vendr/Tropic/Zylo/BetterCloud）→ name/category/spend/contract_end_date/renewal_terms
   - 供应商状态页归档或内部监控（StatusGator/Datadog）→ uptime/incidents
   - 工单系统 → support P90
   - **向供应商书面询问** `data_access`（不要猜）
   - 内部文档 → `break_glass_plan`
3. 同步建立 `sla_records.json`（schema 同模板 SLA 段）。

### 阶段 B — 强制问题锁定（深度优先，Q1→Q3 先于 Q4→Q6）

按 SKILL.md "Forcing-question library" 逐条与业务/法务/安全确认，答案落表。**未锁定 Q1–Q3 前不得进入阶段 C。**

### 阶段 C — 脚本运行（数据齐备后）

```bash
# 三个脚本按 SKILL.md Step 5 指定顺序运行
python3 scripts/vendor_scorer.py        --input vendor_catalog.json --profile <saas|fintech|healthcare|enterprise> --output scorecard.md
python3 scripts/sla_compliance_tracker.py --input sla_records.json --output sla_report.md
python3 scripts/vendor_risk_classifier.py --input vendor_catalog.json --profile <同上> --output risk_matrix.md
```

- `--profile` 由 Q6 答案决定（涉及 PHI → healthcare；涉及 cardholder → fintech；普通 B2B SaaS → saas；大型企业内控 → enterprise）。
- 三个输出都是**人工决策的输入，不是决策本身**（SKILL.md Assumption 4）。

### 阶段 D — 人工综合（Step 5 Synthesize）

基于三份脚本产出，人工汇总：
- Top 3 KEEP（可加深合作）
- Top 3 REVIEW（安排 QBR）
- Top 3 REPLACE（启动备选搜索，**不要**等 auto-renew）
- 所有可申请 SLA 信用赔付的记录（**金额需按合同条款人工核算**，脚本只标资格不算钱）
- 所有 Critical 风险且无现行缓解措施的供应商

---

## 4. 续约清单（Renewal Checklist）

| 项 | 触发条件 | 动作 | 升级路径 |
|---|---|---|---|
| R1 | 合同到期 ≤ 90 天 | 拉入本季度评分 | VMO 负责人 |
| R2 | 评分 < 50（REPLACE） | 立即启动备选搜索；关闭 auto-renew | IT 总监 + 采购 |
| R3 | 评分 50–74（REVIEW） | 续约前安排 QBR，要求 RCA/改进计划 | VMO + 供应商 CSM |
| R4 | auto-renew 且年支出 > $50k | 脚本自动标记；改为 manual-renew | 采购 + 法务 |
| R5 | SLA `credit_claim_eligible = YES` | 在合同窗口内（通常 30–90 天）提交信用赔付申请，附证据 | 财务 + 供应商 CSM；**金额由合同条款核算，本方案不估算** |
| R6 | tier-1 无 SOC2 Type II 报告 | 续约前必须取得报告原件，读 exceptions 段 | CISO |
| R7 | 过去 12 个月从未发起过 SLA 赔付（Q4 = 否） | 审计 SLA 条款是否过弱或违约未上报 | 法务 + IT |
| R8 | 供应商被收购/合并 | 触发 offboarding 预案评估 + 数据删除/权限回收清单 | 法务 + 安全 |

---

## 5. 新供应商引入衔接清单（"筛选"最小门槛，不替代 RFP）

> 本 Skill 不做新供应商选型打分。以下为引入前必须满足的**门槛项**（gating），任一项不满足则不进入现有供应商台账：

- [ ] 已签署 DPA（数据处理协议），且监管要求匹配（HIPAA → BAA；PCI → AOC；GDPR → SCC）
- [ ] 已提供 SOC2 Type II 报告原件（12 个月内），tier-1 必须；tier-2 至少 SOC2 Type I 或等效
- [ ] `data_access` 字段已由供应商书面确认（不是口头）
- [ ] 合同为 manual-renew 或 fixed-term（拒绝 auto-renew 作为默认）
- [ ] SLA 条款可度量、有信用赔付机制、有测量方法说明（拒绝 "best effort"）
- [ ] tier-1 供应商已要求 SBOM（软件物料清单）——依据 `vendor_risk_anti_patterns.md` log4j 教训
- [ ] 已识别前 5 大分包商（fourth-party），并确认其是否接触我方数据
- [ ] 合同包含 24–72 小时事件通报条款（依据 Okta 2022 教训）

> 正式选型打分、价格权重、能力对比走 RFP 流程，不在本方案范围。

---

## 6. 停止条件（Stop Conditions）与升级路径

满足以下**任一**条件，停止当前推进并升级：

| 停止条件 | 升级到 | 原因 |
|---|---|---|
| S1 | Q1–Q3 任一无法在 5 个工作日内锁定 | VMO 负责人 / IT 总监 | 强制问题未锁，跑脚本无意义 |
| S2 | 任一 tier-1 供应商拒绝提供 SOC2 Type II 报告 | CISO + 法务 | 反模式 3；可能直接进入 REPLACE |
| S3 | 任一供应商涉及 PHI 但无 HIPAA BAA，或涉及 cardholder 但无 PCI-DSS AOC | CISO + 合规 | 脚本会标 Regulatory = Critical；应**阻断数据访问**直到达规 |
| S4 | 距合同到期 < 60 天且为 auto-renew | 采购 + 法务 + 业务负责人 | 延迟 = 自动续约，丧失议价权 |
| S5 | tier-1 + 无 break-glass 预案 | IT 总监 + 业务负责人 | 脚本标 Operational = Critical |
| S6 | 发现供应商事件未在 72 小时内通报我方 | 法务（合同违约）+ 安全 | Okta 教训；可能触发解约条款 |
| S7 | 数据缺失导致脚本大量使用默认值（任何关键字段空值率 > 20%） | VMO 暂停评分，回阶段 A 补数 | 默认值 = 隐性编造，违反"不得 LLM 推断"原则 |
| S8 | 出现 fourth-party / 供应链事件（类似 SolarWinds/log4j） | CISO 紧急响应 | 启动 SBOM 排查 + 受影响供应商清单 |

---

## 7. 衡量方式（怎么知道这套流程在工作）

| 指标 | 目标 | 测量频率 |
|---|---|---|
| 台账字段完整度（按 schema 必填字段） | 100%（无默认值） | 每次评分前 |
| tier-1 供应商 SOC2 Type II 报告持有率 | 100% | 季度 |
| tier-1 供应商 break-glass 预案书面化+年度演练率 | 100% | 半年 |
| SLA 违约在合同窗口内提交赔付申请的比例 | 100%（违约即申请） | 月度 |
| auto-renew 合同占比（按支出加权） | 逐年下降 | 季度 |
| Critical 风险供应商从识别到缓解闭环的平均时长 | ≤ 30 天 | 季度 |
| 续约决策在到期前 60 天完成的比例 | ≥ 90% | 月度 |
| MTTD（第三方事件发现时长，Forrester 基准 < 60 天） | 持续下降 | 季度 |

> 不设"节省金额"作为衡量指标——本 Skill 不产出节省数字；价格优化由 procurement-optimizer 独立衡量。

---

## 8. 下一步（Next Actions，按优先级）

1. **立即**：在工作目录建立空 `vendor_catalog.json` 与 `sla_records.json`（schema 见模板），启动数据采集。
2. **本周**：与业务/法务/安全召开 30 分钟会议，锁定 Q1–Q3（tier 阈值、SOC2 报告、break-glass）。
3. **Q1–Q3 锁定后**：推进 Q4–Q6，确定 `--profile`。
4. **数据齐备后**：按阶段 C 顺序跑三个脚本，产出 scorecard.md / sla_report.md / risk_matrix.md。
5. **脚本产出后**：人工综合（阶段 D），形成 VMO digest 交决策层。
6. **建立节奏**：tier-1 季度评审、tier-2 半年、tier-3 续约时（SKILL.md Anti-pattern 2）。

---

## 9. 自检（对照 SKILL.md 要求逐项核对）

| 检查项 | 结果 |
|---|---|
| 是否使用确定性脚本而非 LLM 打分？ | ✅ 评分/风险/SLA 全部由脚本产出；本方案不替脚本打分 |
| 是否在无数据时拒绝编造评分/认证/节省金额？ | ✅ 未输出任何具体供应商分数、认证状态、金额；明确标注 C2/C3/C4 冲突 |
| 是否区分事实/推断/待确认？ | ✅ 第 1 节三分 |
| 是否指出决策门槛和升级路径？ | ✅ 第 5 节门槛 + 第 6 节停止条件/升级 |
| 是否覆盖目标、依据、步骤、关键取舍、风险、衡量方式、下一步？ | ✅ 第 0–8 节 |
| 是否按强制问题深度优先顺序？ | ✅ 第 1.3 节 Q1–Q3 先于 Q4–Q6，并在阶段 B 重申 |
| 是否处理反模式（同 tier、年度评审、信问卷、无 break-glass、忘 offboarding、凭感觉打分）？ | ✅ 第 4/5/6 节均有对应项 |
| 脚本是否实际运行验证？ | ✅ 三个脚本 `--sample` 自检通过（工具链验证，非用户数据） |
| 是否越界覆盖合同谈判/价格优化/新供应商选型？ | ✅ 第 0 节明确边界；第 5 节只给门槛不替代 RFP |
| 输出是否为中文 Markdown？ | ✅ 本文件 |

---

## 10. 实际读取的 Skill 文件清单及对本方案的影响

| 文件 | 影响本结果的关键规则 |
|---|---|
| `SKILL.md` | 定义工作流 5 步、评分阈值、3 个脚本顺序、强制问题库、反模式 6 条、边界（When NOT to use）；本方案整体结构、停止条件、强制顺序、自检项均直接来自此文件 |
| `assets/vendor_catalog_template.md` | 决定第 3 节阶段 A 的 intake 字段（12 个必填）、数据来源优先级、`data_access` 必须书面确认、`break_glass_plan` 必须是书面预案 |
| `references/vendor_management_canon.md` | 第 7 节 MTTD 基准（Forrester，>60 天过长）、SIG-Lite vs 全 SIG 分层、tier-1 用 ISO 27036 + NIST 800-161；支撑"季度滚动评审"节奏 |
| `references/sla_design_patterns.md` | 第 4 节 R5（赔付窗口 30–90 天）、R7（西瓜 SLA：客户体验指标 vs 供应商自报）、拒绝 "best effort" 条款、信用赔付需主动申请不会自动发放 |
| `references/vendor_risk_anti_patterns.md` | 第 5 节 SBOM 要求（log4j）、24–72 小时通报条款（Okta）、风险等级 ≠ 业务关键度（Target/HVAC）、第四方风险（SolarWinds）；直接构成第 5 节门槛项与第 6 节 S6/S8 停止条件 |
| `scripts/vendor_scorer.py` | 确认评分逻辑确定性、阈值 75/50、auto-renew >$50k 自动加注、缺失字段默认值问题（第 2 节 C2）；不运行真实数据，仅 `--sample` 自检 |
| `scripts/sla_compliance_tracker.py` | 确认信用赔付触发条件（≥2 次违约或偏离 >0.5pp）、状态分类（met/at-risk/breached）、趋势判定；第 4 节 R5 直接引用 |
| `scripts/vendor_risk_classifier.py` | 确认 4 向量逻辑、total = worst-of（2 个 High 升 Critical）、healthcare/fintech 监管 Critical 条件、缺失 `data_access` 默认 Medium 导致的低估风险（第 2 节 C4） |

---

*本方案不构成法律意见或采购决定。所有结论性产出（评分、风险等级、SLA 赔付金额）须在真实台账数据齐备后由脚本与人工综合产生，并由 VMO/法务/CISO 按授权审批。*
