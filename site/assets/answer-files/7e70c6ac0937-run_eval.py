#!/usr/bin/env python3
"""
mini_code_eval 运行器 —— 零外部依赖的代码生成智能体小型评测工具。

设计参考 bigcode-evaluation-harness 的核心流程：
  1. 加载题目（prompt + 单元测试 + 入口函数）
  2. 调用 agent.generate(prompt) 获取生成代码
  3. 后处理（按停止词截断）
  4. 在隔离子进程中执行单元测试（带超时）
  5. 统计 pass@1 并按失败类型分类
  6. 输出 JSON 结果

用法：
  python run_eval.py --agent mock_agent.py
  python run_eval.py --agent mock_agent.py --limit 3
  python run_eval.py --check-references          # 用标准答案自检题目
  python run_eval.py --agent mock_agent.py --n-samples 5
"""

import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from collections import Counter

# ---------------------------------------------------------------------------
# 失败类型定义（对应 Skill 中 process_results 的错误分类思想）
# ---------------------------------------------------------------------------
FAIL_EMPTY = "empty_generation"        # agent 未返回有效代码
FAIL_SYNTAX = "syntax_error"           # 生成代码无法编译
FAIL_MISSING = "missing_function"      # 未定义入口函数
FAIL_RUNTIME = "runtime_error"         # 运行时异常（非断言）
FAIL_WRONG = "wrong_answer"            # 断言失败（测试不通过）
FAIL_TIMEOUT = "timeout"               # 执行超时
FAIL_INTERNAL = "internal_error"       # 评测器自身异常

PASS = "passed"

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PROBLEMS = os.path.join(HERE, "problems.json")
DEFAULT_TIMEOUT = 10  # 秒，参考 Skill 中 code_eval 的 timeout=10.0


# ---------------------------------------------------------------------------
# 题目与 agent 加载
# ---------------------------------------------------------------------------
def load_problems(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_agent(agent_path):
    """动态加载 agent 模块，要求其暴露 generate(prompt: str) -> str。"""
    agent_path = os.path.abspath(agent_path)
    if not os.path.isfile(agent_path):
        raise FileNotFoundError(f"agent 文件不存在: {agent_path}")
    spec = importlib.util.spec_from_file_location("eval_agent", agent_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "generate"):
        raise AttributeError(
            f"agent 模块 {agent_path} 必须定义 generate(prompt: str) -> str 函数"
        )
    return module


# ---------------------------------------------------------------------------
# 后处理：参考 Skill custom-tasks.md 的 stop_words 截断
# ---------------------------------------------------------------------------
PYTHON_STOP_WORDS = ["\nclass ", "\ndef ", "\n# ", "\nif __name__", "\nprint("]


def postprocess(generation, entry_point):
    """
    清理生成结果：
    1. 去除首尾空行（保留函数体缩进）
    2. 如果生成结果包含完整函数定义，从该 def 处截取
    3. 按停止词截断多余内容（后续的 class/def/注释/print 等）
    """
    if not generation or not generation.strip():
        return ""

    # 仅去除首尾空行和尾部空白，保留函数体前导缩进
    code = generation.strip("\n")
    # 去除尾部每行多余空白
    code = "\n".join(line.rstrip() for line in code.split("\n"))

    # 尝试定位入口函数定义，截取从该 def 开始的部分
    def_marker = f"def {entry_point}("
    idx = code.find(def_marker)
    if idx != -1:
        code = code[idx:]

    # 按停止词截断（从第二行开始查找，避免截断函数首行）
    lines = code.split("\n")
    kept = [lines[0]]
    for line in lines[1:]:
        if any(line.startswith(sw.lstrip("\n")) for sw in PYTHON_STOP_WORDS):
            break
        kept.append(line)
    code = "\n".join(kept)

    return code.strip("\n")


# ---------------------------------------------------------------------------
# 隔离执行：将生成代码与测试写入临时文件，子进程运行
# ---------------------------------------------------------------------------
EXEC_TEMPLATE = """
import sys, json

{generated_code}

{test_code}

try:
    check({entry_point})
    print(json.dumps({{"status": "passed"}}))
except AssertionError as e:
    print(json.dumps({{"status": "wrong_answer", "detail": str(e)}}))
except Exception as e:
    print(json.dumps({{"status": "runtime_error", "detail": f"{{type(e).__name__}}: {{e}}"}}))
"""


def classify_compile(code):
    """编译期检查，返回 (ok, error_type, detail)。"""
    try:
        compile(code, "<generated>", "exec")
        return True, None, None
    except SyntaxError as e:
        return False, FAIL_SYNTAX, f"SyntaxError: {e}"
    except Exception as e:
        return False, FAIL_SYNTAX, f"{type(e).__name__}: {e}"


def run_one(problem, generated_code, timeout):
    """
    执行单题，返回 dict:
      status, detail, duration

    generated_code 是 agent 返回的补全内容（函数体或完整函数）。
    若不含函数定义，则与 prompt 拼接（与 bigcode harness 的 prompt+completion 一致）。
    """
    entry = problem["entry_point"]
    prompt = problem["prompt"]

    if not generated_code:
        return {"status": FAIL_EMPTY, "detail": "生成结果为空", "duration": 0.0}

    has_entry_def = f"def {entry}(" in generated_code
    # 检测是否定义了其他函数（函数名写错的情况）
    has_other_def = bool(re.search(r"(^|\n)def\s+", generated_code)) and not has_entry_def

    if has_other_def:
        return {
            "status": FAIL_MISSING,
            "detail": f"生成代码定义了函数但未找到入口函数 {entry}",
            "duration": 0.0,
        }

    # 若生成内容不含函数定义，则作为函数体拼接到 prompt 之后（标准 HumanEval 补全格式）
    if not has_entry_def:
        full_code = prompt + generated_code
    else:
        full_code = generated_code

    # 编译期检查
    ok, etype, detail = classify_compile(full_code)
    if not ok:
        return {"status": etype, "detail": detail, "duration": 0.0}

    # 组装执行脚本
    script = EXEC_TEMPLATE.format(
        generated_code=full_code,
        test_code=problem["test"],
        entry_point=entry,
    )

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as tf:
        tf.write(script)
        script_path = tf.name

    start = time.time()
    try:
        proc = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        duration = time.time() - start
        out = proc.stdout.strip().splitlines()
        if out:
            try:
                result = json.loads(out[-1])
                return {
                    "status": result["status"],
                    "detail": result.get("detail", ""),
                    "duration": round(duration, 3),
                }
            except json.JSONDecodeError:
                pass
        # 未输出预期 JSON，归类为运行时错误
        err = proc.stderr.strip()[-500:] if proc.stderr else "无 stderr 输出"
        return {
            "status": FAIL_RUNTIME,
            "detail": f"子进程未返回有效结果。stderr: {err}",
            "duration": round(duration, 3),
        }
    except subprocess.TimeoutExpired:
        duration = time.time() - start
        return {
            "status": FAIL_TIMEOUT,
            "detail": f"执行超过 {timeout} 秒",
            "duration": round(duration, 3),
        }
    except Exception as e:
        duration = time.time() - start
        return {
            "status": FAIL_INTERNAL,
            "detail": f"{type(e).__name__}: {e}",
            "duration": round(duration, 3),
        }
    finally:
        try:
            os.unlink(script_path)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# pass@k 计算（参考 benchmarks.md 公式）
#   pass@k = E[1 - C(n-c, k) / C(n, k)]
# 对单次采样 n=1 时 pass@1 即通过率；多采样时用无偏估计。
# ---------------------------------------------------------------------------
def estimate_pass_at_k(num_samples, num_correct, k):
    """无偏估计 pass@k。num_samples / num_correct 可为标量或等长列表。"""
    import math

    def estimator(n, c):
        if n - c < k:
            return 1.0
        return 1.0 - math.prod(1.0 - k / (n - i) for i in range(c))

    if hasattr(num_samples, "__len__"):
        return sum(estimator(n, c) for n, c in zip(num_samples, num_correct)) / len(
            num_samples
        )
    return estimator(num_samples, num_correct)


# ---------------------------------------------------------------------------
# 主评测流程
# ---------------------------------------------------------------------------
def evaluate(args):
    problems = load_problems(args.problems)
    if args.limit is not None:
        problems = problems[: args.limit]

    using_references = args.check_references
    agent = None
    if not using_references:
        agent = load_agent(args.agent)

    n_samples = args.n_samples
    results = []
    # 用于 pass@k 聚合：每题 (n, c)
    per_problem_nc = []

    for problem in problems:
        task_id = problem["task_id"]
        prompt = problem["prompt"]
        sample_results = []

        for s in range(n_samples):
            if using_references:
                # 标准答案模式：直接用 canonical_solution 拼到 prompt 后
                raw = problem["canonical_solution"]
            else:
                try:
                    raw = agent.generate(prompt)
                except Exception as e:
                    raw = ""
                    sample_results.append(
                        {
                            "sample_index": s,
                            "status": FAIL_INTERNAL,
                            "detail": f"agent.generate 异常: {type(e).__name__}: {e}",
                            "duration": 0.0,
                            "generated_code": "",
                        }
                    )
                    continue

            code = postprocess(raw, problem["entry_point"])
            outcome = run_one(problem, code, args.timeout)
            outcome["sample_index"] = s
            outcome["generated_code"] = code
            sample_results.append(outcome)

        n = len(sample_results)
        c = sum(1 for r in sample_results if r["status"] == PASS)
        per_problem_nc.append((n, c))

        # 单题状态：任一样本通过即视为该题通过（pass@1 视角取首个样本）
        first = sample_results[0]
        results.append(
            {
                "task_id": task_id,
                "category": problem.get("category", ""),
                "difficulty": problem.get("difficulty", ""),
                "entry_point": problem["entry_point"],
                "status": first["status"],
                "detail": first.get("detail", ""),
                "duration": first.get("duration", 0.0),
                "n_samples": n,
                "n_correct": c,
                "samples": sample_results if n_samples > 1 else None,
            }
        )

    # 聚合统计
    total = len(results)
    passed = sum(1 for r in results if r["status"] == PASS)
    fail_counter = Counter(r["status"] for r in results if r["status"] != PASS)

    # pass@k
    pass_at = {}
    for k in args.k_values:
        if k > n_samples:
            pass_at[f"pass@{k}"] = None
        else:
            pass_at[f"pass@{k}"] = round(
                estimate_pass_at_k(
                    [n for n, _ in per_problem_nc],
                    [c for _, c in per_problem_nc],
                    k,
                ),
                4,
            )

    # 按类别/难度分组 pass@1（以首个样本为准）
    by_category = {}
    by_difficulty = {}
    for r in results:
        cat = r["category"] or "未分类"
        diff = r["difficulty"] or "未标注"
        by_category.setdefault(cat, [0, 0])
        by_difficulty.setdefault(diff, [0, 0])
        by_category[cat][0] += 1
        by_difficulty[diff][0] += 1
        if r["status"] == PASS:
            by_category[cat][1] += 1
            by_difficulty[diff][1] += 1

    summary = {
        "eval_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "agent": os.path.basename(args.agent) if args.agent else "(references)",
        "mode": "check_references" if using_references else "agent",
        "n_problems": total,
        "n_samples_per_problem": n_samples,
        "timeout_seconds": args.timeout,
        "passed": passed,
        "pass_rate_at1": round(passed / total, 4) if total else 0.0,
        "pass_at_k": pass_at,
        "failure_breakdown": dict(fail_counter),
        "by_category": {
            k: {"total": v[0], "passed": v[1], "pass_rate": round(v[1] / v[0], 4)}
            for k, v in sorted(by_category.items())
        },
        "by_difficulty": {
            k: {"total": v[0], "passed": v[1], "pass_rate": round(v[1] / v[0], 4)}
            for k, v in sorted(by_difficulty.items())
        },
    }

    output = {"summary": summary, "results": results}

    # 输出
    out_path = args.output
    if out_path:
        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

    # 终端摘要
    print("=" * 60)
    print(f"评测完成: {summary['n_problems']} 题, "
          f"通过 {summary['passed']} 题, "
          f"pass@1 = {summary['pass_rate_at1']:.2%}")
    for k, v in summary["pass_at_k"].items():
        if v is not None:
            print(f"  {k} = {v:.4f}")
    if fail_counter:
        print("失败类型分布:")
        for ftype, cnt in fail_counter.most_common():
            print(f"  {ftype}: {cnt}")
    print("=" * 60)
    if out_path:
        print(f"详细结果已写入: {out_path}")

    return output


def main():
    parser = argparse.ArgumentParser(
        description="mini_code_eval —— 代码生成智能体小型评测（零外部依赖）"
    )
    parser.add_argument(
        "--agent", type=str, default=None,
        help="agent 模块路径（需暴露 generate(prompt)->str 函数）",
    )
    parser.add_argument(
        "--problems", type=str, default=DEFAULT_PROBLEMS,
        help="题目 JSON 文件路径",
    )
    parser.add_argument("--limit", type=int, default=None, help="只评测前 N 题")
    parser.add_argument(
        "--n-samples", type=int, default=1,
        help="每题采样数（用于 pass@k，默认 1）",
    )
    parser.add_argument(
        "--k-values", type=int, nargs="+", default=[1],
        help="要计算的 pass@k 中的 k 值列表，如 --k-values 1 5",
    )
    parser.add_argument(
        "--timeout", type=int, default=DEFAULT_TIMEOUT,
        help=f"单题执行超时秒数（默认 {DEFAULT_TIMEOUT}）",
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="JSON 结果输出路径",
    )
    parser.add_argument(
        "--check-references", action="store_true",
        help="用标准答案自检题目（不需要 agent）",
    )
    args = parser.parse_args()

    if not args.check_references and not args.agent:
        parser.error("必须指定 --agent，或使用 --check-references 自检题目")

    evaluate(args)


if __name__ == "__main__":
    main()
