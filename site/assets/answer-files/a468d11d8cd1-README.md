# EU AI Act Readiness — 使用说明

本目录包含 `ai-act-readiness` Skill 的完整实现，以及对一个真实小项目（AI 简历筛选工具）的合规审查。

## 目录结构

```
ai-act-readiness/
├── SKILL.md                          # Skill 原始说明（评估对象）
├── scripts/
│   ├── ai_system_risk_classifier.py  # Article 5/6/GPAI 风险分类器
│   ├── conformity_assessment_planner.py  # Article 43 合规路径规划器
│   └── ai_act_obligation_tracker.py  # Article 25 角色义务追踪器
├── examples/
│   ├── systems.json                  # 风险分类输入
│   ├── system.json                   # 合规评估输入
│   └── roles.json                    # 义务追踪输入
├── project-under-review/
│   ├── resume_screener.py            # 被审查项目：AI 简历筛选工具
│   └── sample_resumes.json           # 示例简历数据
├── tests/
│   ├── test_risk_classifier.py       # 风险分类器测试（20 项）
│   ├── test_conformity_planner.py    # 合规规划器测试（12 项）
│   ├── test_obligation_tracker.py    # 义务追踪器测试（17 项）
│   └── test_resume_screener.py       # 被审查项目测试（5 项）
└── verification-records/
    ├── EU_AI_Act_Readiness_Report.md # 最终评估报告
    ├── 01_risk_classification.json   # 风险分类输出
    ├── 02_conformity_assessment.json # 合规评估输出
    ├── 03_obligation_matrix.json     # 义务矩阵输出
    └── 04_resume_screener_output.json # 被审查项目功能输出
```

## 环境要求

- Python 3.9+（仅使用标准库，无任何第三方依赖）

## 可重复验证命令

在本目录下执行：

```bash
# 1. 运行全部测试（49 项）
python3 -m unittest discover tests/ -v

# 2. 运行被审查项目（简历筛选功能验证）
python3 project-under-review/resume_screener.py project-under-review/sample_resumes.json

# 3. 风险分类（Article 5/6/GPAI）
python3 scripts/ai_system_risk_classifier.py examples/systems.json

# 4. 合规评估路径（Article 43）
python3 scripts/conformity_assessment_planner.py examples/system.json

# 5. 义务矩阵（Article 25）
python3 scripts/ai_act_obligation_tracker.py examples/roles.json
```

## 约束导致的方案变化

1. **不新增非必要依赖**：三个评估脚本和被审查项目均仅使用 Python 标准库（json、sys、datetime、re），未引入 click/pydantic/pytest 等第三方包。测试使用标准库 `unittest` 而非 pytest。
2. **不修改无关文件**：SKILL.md 保持原样未做任何改动；所有新增文件均在 Skill 目录内，未触碰系统其他位置。
3. **无外部账号依赖**：评估完全基于本地 JSON 输入和法条规则，不调用任何外部 API、数据库或需要认证的服务。Article 43 公告机构（Notified Body）相关步骤仅做到"确认前"阶段——脚本输出"是否需要公告机构"的判断，但不模拟公告机构证书。
4. **SKILL.md 引用的脚本缺失**：原始 ZIP 仅含 SKILL.md，其中引用的 `ai_system_risk_classifier.py`、`conformity_assessment_planner.py`、`ai_act_obligation_tracker.py` 及 `cross_framework_mapper.py` 均不存在。前三个脚本已按 SKILL.md 描述实现；`cross_framework_mapper.py` 属于另一个 Skill（compliance-os），未实现，报告中的跨框架复用部分以人工判断填写。
5. **Python 版本兼容**：被审查项目的类型注解使用 `from __future__ import annotations` 以兼容 Python 3.9。

## 评估结论摘要

被审查项目"AI简历自动筛选工具"被分类为 **高风险**（Annex III point 4，就业领域，含 profiling），适用 **Module A** 内部控制路径（无需公告机构），但 15 项法定义务全部未满足、Annex IV 技术文档仅完成 2/8，最终结论为 **🔴 NOT-READY**。详见 `verification-records/EU_AI_Act_Readiness_Report.md`。
