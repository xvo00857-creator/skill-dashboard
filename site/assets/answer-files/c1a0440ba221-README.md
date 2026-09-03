# 代码生成智能体小型评测集

本评测集依据 `evaluation-methodology` Skill 的方法论构建，用于在**本地、无第三方依赖、
可重复**的条件下评测一个代码生成智能体。

## 目录结构

```
codegen-eval/
├── README.md              # 本文件（运行方式与约束说明）
├── rubric.md              # 六维 0-1 锚点评分规则与失败类型定义
├── RESULT_TEMPLATE.md     # 结果汇总模板
├── run_eval.py            # 评测运行器（仅 Python 标准库）
├── mock_agent.py          # 本地 mock 智能体（不访问网络，用于验证框架）
├── cases/
│   └── cases.json         # 6 个测试用例（含功能测试与边界测试）
└── results/               # 运行后生成 report_*.json / report_*.md
```

## 成功标准

- **单用例通过**：综合分 ≥ 70（等级 C 及以上）
- **整体通过**：全部用例综合分 ≥ 70，且无 SECURITY_ANTIPATTERN 类失败
- **生产候选**：整体综合分 ≥ 80（B），失败率为 0，多次运行 CV = 0

## 失败类型

见 `rubric.md`：SYNTAX_ERROR、FUNCTIONAL_FAILURE、BOUNDARY_FAILURE、ROBUSTNESS_FAILURE、
SECURITY_ANTIPATTERN、SCOPE_OVERREACH、SCOPE_UNDERDELIVERY、NON_REPRODUCIBLE。

## 评分规则

- 六个维度加权：功能正确性 0.30、意图理解 0.20、代码质量 0.15、边界鲁棒性 0.15、
  范围契合 0.10、安全与可执行性 0.10
- 三层评估：Layer 1 静态+确定性测试、Layer 2 规则评委、Layer 3 多次运行统计
- 反模式乘法惩罚：`max(0.5, 1 − 0.05 × 反模式数)`
- 综合分：`Σ(权重 × 维度分) × 100 × 惩罚系数`

## 运行方式（可重复验证命令）

```bash
# 0. 前置：Python 3.7+，无需 pip install 任何依赖
python3 --version

# 1. 框架自检（内置正确/有缺陷智能体，验证评分逻辑本身）
python3 codegen-eval/run_eval.py --self-test

# 2. 用 mock 智能体跑 standard 深度（静态 + 规则评委）
python3 codegen-eval/run_eval.py --agent "python3 codegen-eval/mock_agent.py" --depth standard

# 3. 全量三层（含蒙特卡洛多次运行，默认 N=5）
python3 codegen-eval/run_eval.py --agent "python3 codegen-eval/mock_agent.py" --depth deep --mc-runs 5

# 4. 仅静态层（最快，<2 秒/用例）
python3 codegen-eval/run_eval.py --agent "python3 codegen-eval/mock_agent.py" --depth quick
```

报告输出到 `codegen-eval/results/report_<时间戳>.{json,md}`。

## 接入真实智能体

智能体只需满足命令行接口契约：

- 从 stdin 读取 JSON：`{"prompt": "...", "case_id": "C01"}`
- 向 stdout 写入 JSON：`{"code": "def ..."}`

示例（接入任意 HTTP API 的包装脚本需自行提供 API Key；本仓库**不包含**任何真实账号
或密钥，也不会在未确认时发起外部请求）：

```bash
python3 codegen-eval/run_eval.py --agent "python3 your_agent_wrapper.py" --depth deep
```

## 约束导致的方案变化

1. **不新增非必要依赖**：未使用 pytest、pyflakes、openai 等第三方库；语法检查用标准库
   `ast`，测试执行用 `subprocess` + 断言，统计用 `statistics`。
2. **不调用外部 LLM 评委**：Skill 描述的 Layer 2 默认使用 Sonnet 等外部模型，需要账号与
   网络。本实现将 Layer 2 落为**本地规则评委**（基于 AST 与测试证据按 rubric 打分），
   不发起任何外部请求；如需人工评委，可在报告基础上覆写分数。
3. **蒙特卡洛不依赖真实智能体调用**：Layer 3 的多次运行通过同一智能体命令本地完成；
   mock 智能体是确定性的，用于验证统计通路；接入真实非确定性智能体后可直接得到 CV/失败率。
4. **不改动无关文件**：所有产物位于 `codegen-eval/` 目录；解压出的 Skill 目录保持只读。
5. **外部账号只做安全模拟**：`mock_agent.py` 模拟一个有对有错的智能体，不访问网络；
   真实 API 接入留给用户自行提供包装脚本与密钥。

## 与原 Skill 方法论的对应关系

| evaluation-methodology Skill | 本评测集 |
|---|---|
| Layer 1 静态分析（<2s，确定性） | `static_scan` + 隐藏测试子进程执行 |
| Layer 2 LLM Judge（Sonnet） | 本地规则评委（无外部调用） |
| Layer 3 蒙特卡洛（N=50） | 多次运行（默认 N=5，可调），统计激活率/失败率/CV |
| 十维加权 | 六维加权（针对代码生成裁剪） |
| 反模式乘法惩罚 | 5 类代码反模式，同一公式 |
| 字母等级 A–F | 同一阈值 |
| `--depth quick/standard/deep` | 同名参数 |
| JSON + Markdown 报告 | `results/report_*.{json,md}` |
| `--threshold` CI 门禁 | 通过线 70 分，可在 CI 中解析 JSON |
