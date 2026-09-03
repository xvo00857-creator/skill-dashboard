# 代码生成智能体小型评测集

基于 `agentic-eval` Skill 的评估模式构建，用于衡量代码生成智能体在小型 Python 编程任务上的表现。

## 目录结构

```
code-agent-eval/
├── README.md                 # 本文件
├── run_eval.py               # 主入口（命令行）
├── runner.py                 # 评测运行器（生成→测试→反思修复循环）
├── scoring.py                # 失败类型、评分量规、静态检查
├── mock_agent.py             # 模拟智能体（无需外部账号）
├── eval_cases/
│   ├── __init__.py
│   ├── base.py               # 用例基类 EvalCase
│   ├── case_01_reverse_words.py
│   ├── case_02_fizzbuzz.py
│   ├── case_03_group_by.py
│   ├── case_04_palindrome.py
│   └── case_05_calculator.py
├── result.json               # 运行后生成：结构化结果
└── report.md                 # 运行后生成：Markdown 报告
```

## 评测用例

| 编号 | 标题 | 分类 | 难度 | 考察点 |
|------|------|------|------|--------|
| C01 | 字符串按词反转 | string | easy | 字符串切片、空格分词、空串处理 |
| C02 | FizzBuzz 变体 | number | easy | 条件分支、边界值 n≤0 |
| C03 | 按字段分组 | data_transform | medium | 字典操作、缺失键处理、顺序保持 |
| C04 | 回文检测 | edge_case | medium | 字符过滤、大小写、空串/纯标点 |
| C05 | 安全计算器 | edge_case | hard | 四则运算、除零异常、非法运算符异常 |

每个用例包含：自然语言规格（`spec`）、入口函数名（`entry_point`）、预置 `unittest` 测试代码（`test_code`）、超时时间。

## 成功标准

单条用例 **通过** 需同时满足：
1. 代码可正常解析（无语法错误）；
2. 定义了要求的入口函数/类；
3. 全部 `unittest` 断言通过（无 FAIL、无 ERROR）；
4. 未检测到危险调用（eval/exec/os.system/subprocess 等）；
5. 在超时时间内完成。

整批评测 **达标** 需满足：平均加权得分 ≥ 阈值（默认 0.8）。

## 失败类型

| 失败类型 | 含义 |
|----------|------|
| `syntax_error` | 代码无法解析/编译 |
| `runtime_error` | 运行时抛出未预期异常（unittest ERROR） |
| `test_failure` | 断言失败（unittest FAIL） |
| `timeout` | 执行超过用例设定的超时秒数 |
| `incomplete` | 缺少要求的入口函数/类 |
| `security_risk` | 检测到 eval/exec/os.system 等危险调用（一票否决） |
| `import_error` | 依赖缺失或导入失败 |

## 评分规则

采用 Skill 推荐的 **Rubric-Based（量规加权）** 评分，各维度 0–1 分：

| 维度 | 权重 | 评分方式 |
|------|------|----------|
| accuracy（功能正确性） | 50% | 单元测试通过率 = 1 − 失败数/总数 |
| edge_case（边界与异常） | 20% | 边界相关测试的通过情况（与 accuracy 联动） |
| code_quality（代码质量） | 20% | AST 静态检查：docstring、函数长度、嵌套深度 |
| efficiency（效率） | 10% | 静态启发式：疑似死循环等性能反模式 |

加权总分 = Σ(维度分 × 权重)。安全风险命中时 accuracy 与 code_quality 直接归零。

## 运行方式

### 环境要求

- Python 3.8+（使用 `list[str]` 等类型注解需要 3.9+；如用 3.8 可去掉注解）
- **无任何第三方依赖**，仅标准库

### 可重复验证命令

```bash
# 进入评测目录
cd code-agent-eval

# 1. 默认模式（混合：部分正确部分有缺陷，3 轮反思）
python3 run_eval.py

# 2. 全部正确实现（验证通过率 100%）
python3 run_eval.py --mode correct

# 3. 全部有缺陷实现（验证失败检测与评分）
python3 run_eval.py --mode buggy

# 4. 关闭反思修复（仅单次生成，对比反思效果）
python3 run_eval.py --mode buggy --max-iterations 1

# 5. 自定义阈值与输出路径
python3 run_eval.py --mode mixed --threshold 0.6 --json-out out.json --md-out out.md
```

运行后生成：
- `result.json`：结构化 JSON 结果（逐用例分数、失败分布、维度均分）
- `report.md`：人可读的 Markdown 报告（含结果汇总模板）

### 接入真实智能体

编辑 `mock_agent.py` 中的 `CodeAgent` 类，将 `generate()` 和 `fix()` 替换为实际 LLM 调用即可，`runner.py` 无需改动。在未配置外部账号前，使用 `MockCodeAgent` 完成全部本地验证。

## 结果汇总模板

每次评测后在 `report.md` 末尾自动生成，也可手动复制使用：

```markdown
### 评测批次：____
- 智能体版本/标识：____
- 用例总数：5
- 通过率：____%
- 平均加权得分：____
- 合格阈值：0.8（达标/未达标）
- 主要失败类型：____
- 维度短板：____
- 与上批次差异：____
- 结论与改进项：____
```

## 约束导致的方案变化

本次新增约束为"不新增非必要依赖、不改动无关文件、本地可重复验证、外部账号只做模拟"。相比无约束方案，做了以下调整：

1. **测试框架**：Skill 示例使用 `pytest`，但为避免第三方依赖，改用 Python 标准库 `unittest`，通过 `python -m unittest` 子进程运行，零安装即可复现。
2. **LLM 调用**：Skill 示例中的 `llm()` 函数需要外部 API 账号。改为提供 `MockCodeAgent`（预置正确/有缺陷实现）完成本地端到端验证；真实 LLM 接入点以 `CodeAgent` 接口类预留，不实际发起外部请求。
3. **代码质量评估**：无约束时可引入 pylint/radon 等工具做质量评分；改为仅用标准库 `ast` 做轻量静态检查（docstring、函数长度、嵌套深度、死循环启发式）。
4. **代码执行安全**：不引入 docker 等沙箱依赖，改用子进程 + 超时 + 危险调用正则静态检测的组合，在本地环境中提供基础安全保障。
5. **文件范围**：所有新增文件均在 `code-agent-eval/` 目录内，不修改项目中任何无关文件；解压的 Skill 原文保留在 `agentic-eval-extracted/` 中只读参考。
6. **LLM-as-Judge 维度**：Skill 提供了 LLM-as-Judge 策略，但该策略依赖外部模型调用，在无账号约束下不纳入自动评分，仅在 README 中说明可作为扩展点接入。

## 验证证据

见本目录下运行后生成的 `result.json` 和 `report.md`，以及交付说明中记录的命令输出。
