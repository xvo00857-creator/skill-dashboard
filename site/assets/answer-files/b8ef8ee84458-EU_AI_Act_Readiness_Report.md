# EU AI Act Readiness: AI简历自动筛选工具 (ResumeScreener)

**Date:** 2026-08-12
**Article Citations:** 以下每项结论均引用具体法条。

## The Decision Being Made

classify + conformity-route + obligation-scope（新系统准入审查，拟投放欧盟市场）

## Risk Classification

- **Tier:** high_risk
- **Citation:** Article 6(2) + Annex III, point 4（就业与人力资源）；Article 6(3) last sentence（profiling 覆盖豁免）
- **Rationale:** 系统用于招聘场景中的简历自动评分与排序，对自然人进行自动化评估和推荐（interview/review/reject），构成对自然人的 profiling。根据 Article 6(3) 末句，profiling 覆盖 carve-out，不适用 Article 6(3) 豁免条件，因此构成高风险 AI 系统。系统不包含 Article 5(1) 禁止的 AI 实践。
- **GPAI:** no
- **Systemic-risk GPAI:** no（非通用 AI 模型，不适用 Article 51 的 10^25 FLOPs 阈值）

## Conformity Assessment (if high-risk)

- **Module:** A
- **Citation:** Article 43(2) + Annex VI + Article 40
- **Notified body required:** no（非生物识别类高风险系统，全面采用协调标准时可通过内部控制完成）
- **Annex IV pack status:** in-progress（8 项中 2 项完成，6 项未完成）

| Annex IV 项目 | 状态 | 法条 |
|---|---|---|
| 系统总体描述 | complete | Article 11 |
| 预期用途与使用条件 | complete | Article 11 |
| 风险管理体系 | in-progress | Article 9 |
| 数据治理与数据质量 | not-started | Article 10 |
| 模型开发技术文档 | in-progress | Article 11 |
| 日志记录能力 | not-started | Article 12 |
| 人类监督措施 | in-progress | Article 14 |
| 准确性、稳健性与网络安全 | not-started | Article 15 |

## Obligation Matrix

- **Total obligations:** 15（provider + deployer 双重角色）
- **By deadline phase:**
  - 2025-02-02 (A): 1 项 — Article 4 AI 素养（unmet）
  - 2025-08-02 (B): 1 项 — Article 50 透明度（unmet）
  - 2026-08-02 (C): 13 项 — 高风险系统主体义务（全部 unmet）
  - 2027-08-02 (D): 0 项
- **Highest-priority unmet obligation:** Article 9 — 建立、实施、记录和维护风险管理体系（critical，截止 2026-08-02）

**已逾期义务（截至 2026-08-12）：**
- Article 4 AI 素养（应于 2025-02-02 前完成）
- Article 50 透明度（应于 2025-08-02 前完成）

## Transparency (Article 50)

- **50(1) interaction disclosure:** no — 系统对求职者进行自动化决策，须在招聘流程中明确告知求职者其简历正由 AI 系统处理
- **50(2) synthetic content marking:** NA
- **50(3) emotion recognition disclosure:** NA
- **50(4) deepfake disclosure:** NA

## Cross-Framework Reuse

- **ISO 42001 evidence applicable to Article 17 QMS:** no（当前未建立 AI 管理体系，若引入 ISO 42001 可复用）
- **ISO 27001 evidence applicable to Article 15 cybersecurity:** no（当前未建立 ISMS，若已有 ISO 27001 认证可部分复用）
- **GDPR DPIA usable for Article 27 FRIA:** NA（非公共部门部署者，不适用 Article 27 FRIA；但招聘场景涉及个人数据自动化处理，GDPR Article 22 DPIA 可与 Article 9 风险管理协同）

## Verdict

🔴 NOT-READY

系统被正确分类为高风险，但 15 项适用义务全部未满足，其中 2 项已逾期（Article 4、Article 50），Annex IV 技术文档仅完成 2/8。在完成合规评估并签署 EU 合规声明前，不得投放欧盟市场。

## Top 3 Actions

1. **立即补做 Article 50 透明度告知**（负责人：产品/法务，截止：立即，已逾期）— 在招聘页面和提交流程中加入 AI 处理告知，说明自动化决策逻辑和求职者申诉途径。
2. **建立 Article 9 风险管理体系**（负责人：工程/合规，截止：2026-08-02 前）— 识别简历筛选中的偏见风险、歧视风险和错误拒绝风险，形成书面风险评估和缓解措施。
3. **完成 Annex IV 技术文档**（负责人：工程/技术写作，截止：2026-08-02 前）— 优先补齐 Article 10 数据治理（训练/关键词数据来源与偏见审计）、Article 12 日志记录、Article 14 人类监督（强制人工复核机制）和 Article 15 准确性测试。

## Legal Review Required

- **Article 25 substantial-modification 边界：** 若公司仅作为 deployer 使用第三方筛选引擎但自行调整关键词权重和阈值，是否构成"实质修改"从而转为 provider 角色，需外部律师确认。
- **Article 50(1) 告知范围：** 简历筛选非典型"交互"场景，告知义务的具体形式和内容需法律确认。
- **GDPR Article 22 交叉：** 自动化决策对求职者产生重大影响，需同时评估 GDPR 下的合法性基础和人工干预权。
