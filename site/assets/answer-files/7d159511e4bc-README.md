# mini_code_eval —— 代码生成智能体小型评测集

基于 bigcode-evaluation-harness Skill 的核心方法论，为代码生成智能体建立的**零依赖、可本地重复运行**的小型评测集。

## 一、设计目标

为一个代码生成智能体提供快速、可重复的功能正确性评测，覆盖：

- 成功标准定义
- 失败类型分类
- 评分规则
- 本地运行方式
- 结果汇总模板

## 二、成功标准

| 维度 | 标准 |
|------|------|
| 单题通过 | 生成代码通过该题**全部**单元测试（`AssertionError` 即失败） |
| 整体通过 | `pass@1` = 通过题数 / 总题数 |
| 可重复性 | 同一 agent、同一题目、同一参数多次运行结果一致（确定性 agent） |
| 安全执行 | 生成代码在隔离子进程中运行，单题超时 10 秒自动终止 |

**pass@1 含义**：对每道题采样 1 次，该次生成通过全部测试的概率估计。多采样时支持 pass@k（无偏估计，公式同 Skill 文档）。

## 三、失败类型

| 失败类型 | 含义 | 对应 Skill 中的处理 |
|----------|------|---------------------|
| `syntax_error` | 生成代码无法通过 Python 编译 | Skill 中 postprocess 后执行阶段报错 |
| `runtime_error` | 代码运行时抛出非断言异常（除零、类型错误等） | Skill 中 code_eval 执行捕获 |
| `wrong_answer` | 代码可运行但断言失败（逻辑错误） | 单元测试不通过 |
| `timeout` | 执行超过 10 秒（死循环等） | Skill 建议 Docker 隔离，本工具用子进程超时 |
| `empty_generation` | agent 返回空字符串或纯空白 | Skill 中 postprocess 后为空 |
| `missing_function` | 未定义要求的入口函数 | Skill 中 reference 检查 `entry_point` |
| `internal_error` | 评测器自身异常（agent.generate 抛异常等） | 防御性分类 |

## 四、评分规则

1. **pass@1**（默认）：每题采样 1 次，通过全部测试记为 1 分，否则 0 分；总分 = 平均分。
2. **pass@k**（可选）：每题采样 n 次（n ≥ k），用无偏估计：
   ```
   pass@k = 1 - C(n-c, k) / C(n, k)
   ```
   其中 n 为总采样数，c 为通过采样数。与 Skill `benchmarks.md` 中的公式一致。
3. **分组统计**：按题目类别（算术/字符串/列表/数学）和难度（入门/简单/中等）分别统计通过率。
4. **失败分布**：统计各类失败类型的数量，定位 agent 主要短板。

## 五、题目集

共 10 道 Python 函数补全题（HumanEval 风格），每题包含：

- `prompt`：函数签名 + docstring
- `canonical_solution`：参考答案
- `test`：单元测试（3~6 条 assert）
- `entry_point`：入口函数名
- `category` / `difficulty`：分类与难度

| 题号 | 函数 | 类别 | 难度 |
|------|------|------|------|
| 0 | add | 算术 | 入门 |
| 1 | reverse_string | 字符串 | 入门 |
| 2 | find_max | 列表 | 入门 |
| 3 | factorial | 数学 | 简单 |
| 4 | is_palindrome | 字符串 | 简单 |
| 5 | count_vowels | 字符串 | 简单 |
| 6 | remove_duplicates | 列表 | 简单 |
| 7 | is_prime | 数学 | 中等 |
| 8 | merge_sorted | 列表 | 中等 |
| 9 | longest_word | 字符串 | 中等 |

## 六、运行方式

### 环境要求

- Python 3.7+（仅标准库，**无需安装任何第三方依赖**）
- 无需 GPU、无需 HuggingFace 账号、无需 Docker

### 验证命令

```bash
# 1. 题目自检：确认所有参考答案通过测试（对应 Skill 的 --check_references）
python run_eval.py --check-references

# 2. oracle agent 评测：模拟完美 agent，预期 pass@1 = 1.0
python run_eval.py --agent mock_agent.py --output results_oracle.json

# 3. 有缺陷 agent 评测：验证失败分类
MOCK_AGENT_MODE=flawed python run_eval.py --agent mock_agent.py --output results_flawed.json

# 4. 只跑前 3 题（对应 Skill 的 --limit）
python run_eval.py --agent mock_agent.py --limit 3

# 5. 多采样 pass@5（对应 Skill 的 n_samples + pass@k）
python run_eval.py --agent mock_agent.py --n-samples 5 --k-values 1 5
```

### 接入真实代码生成智能体

编写一个 Python 模块，实现以下接口：

```python
def generate(prompt: str) -> str:
    """接收函数签名+docstring，返回函数体代码（含缩进）。"""
    # 例如调用本地模型、API 等
    return "    return result\n"
```

然后运行：

```bash
python run_eval.py --agent your_agent.py --output results.json
```

> **外部账号说明**：若你的 agent 需要调用 HuggingFace 模型或云 API，请在 agent 模块内部自行完成登录/鉴权（如 `huggingface-cli login` 或设置 API Key 环境变量）。本评测框架本身不接触任何外部账号，只通过 `generate()` 函数与 agent 交互。若账号未就绪，agent 应在 `generate()` 中抛出明确异常，评测器会将其归类为 `internal_error` 而非崩溃。

## 七、结果汇总模板

运行后输出 JSON，结构见 `results_template.json`。核心字段：

```json
{
  "summary": {
    "pass_rate_at1": 0.8,
    "pass_at_k": {"pass@1": 0.8},
    "failure_breakdown": {"wrong_answer": 1, "syntax_error": 1},
    "by_category": {"字符串": {"total": 4, "passed": 3, "pass_rate": 0.75}},
    "by_difficulty": {"中等": {"total": 3, "passed": 2, "pass_rate": 0.667}}
  },
  "results": [
    {"task_id": "MiniEval/0", "status": "passed", "duration": 0.05}
  ]
}
```

## 八、约束导致的方案变化说明

| 约束 | 原 Skill 做法 | 本方案调整 | 原因 |
|------|--------------|-----------|------|
| 不新增非必要依赖 | `pip install -e .` 安装 torch/transformers/accelerate/datasets 等 | 仅用 Python 标准库，零 pip 安装 | 重型依赖需 GPU 且安装耗时长，小评测集不需要 |
| 不改动无关文件 | 在 bigcode-evaluation-harness 仓库内新增 task 文件并注册 | 所有文件独立放在 `mini_code_eval/` 目录 | 避免克隆和修改上游仓库 |
| 本地可重复验证 | 需 GPU + HuggingFace 账号下载模型 | 提供 mock_agent（oracle/flawed 两种模式），确定性输出 | 无 GPU/账号环境下仍可端到端验证评测流程 |
| 外部账号安全 | `huggingface-cli login` + `--use_auth_token` | agent 接口隔离，框架本身不碰账号；账号未就绪时安全失败 | 符合"只做到安全的模拟或确认前步骤" |
| 安全执行 | 推荐 Docker 容器隔离 | 子进程 + 10 秒超时隔离（Python 单语言） | 避免 Docker 依赖；子进程超时可阻断死循环 |
| 评测规模 | HumanEval 164 题 / MBPP 500 题，n_samples=200 | 10 题，默认 n_samples=1（支持扩展） | 快速验证，秒级完成；公式与大规模评测一致 |

## 九、文件清单

| 文件 | 说明 |
|------|------|
| `problems.json` | 10 道评测题（prompt + 参考答案 + 测试） |
| `run_eval.py` | 评测运行器（零依赖） |
| `mock_agent.py` | 模拟 agent（oracle/flawed 两种模式） |
| `results_template.json` | 结果汇总模板 |
| `README.md` | 本文档 |
