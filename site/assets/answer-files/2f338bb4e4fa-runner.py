# -*- coding: utf-8 -*-
"""评测运行器。

对应 agentic-eval Skill 的 Pattern 3（Code-Specific Reflection）：
  生成 → 运行测试 → 失败则反馈错误 → 修复 → 再测试（最多 max_iterations）

安全措施：
- 被测代码在独立子进程中运行，设置超时
- 不引入额外依赖，仅用标准库 subprocess / tempfile / unittest
- 危险调用（eval/exec/os.system 等）在评分阶段静态检测并标记
"""
from __future__ import annotations

import json
import ast
import os
import re
import subprocess
import sys
import tempfile
from typing import Optional

from eval_cases.base import EvalCase
from scoring import (
    CaseResult,
    FailureType,
    score_case,
)


def load_cases() -> list[EvalCase]:
    """自动发现并加载 eval_cases 下所有用例。"""
    from eval_cases import (
        case_01_reverse_words,
        case_02_fizzbuzz,
        case_03_group_by,
        case_04_palindrome,
        case_05_calculator,
    )

    modules = [
        case_01_reverse_words,
        case_02_fizzbuzz,
        case_03_group_by,
        case_04_palindrome,
        case_05_calculator,
    ]
    return [m.CASE for m in modules]


def _run_tests_in_subprocess(workdir: str, timeout: int) -> dict:
    """在子进程中运行 unittest，返回结构化结果。

    返回 dict:
      success: bool        — 全部通过
      tests_run: int
      tests_failed: int
      failure_type: FailureType
      output: str          — 原始输出（截断）
    """
    test_file = os.path.join(workdir, "test_solution.py")
    cmd = [sys.executable, "-m", "unittest", "-v", "test_solution"]

    try:
        proc = subprocess.run(
            cmd,
            cwd=workdir,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "tests_run": 0,
            "tests_failed": 0,
            "failure_type": FailureType.TIMEOUT,
            "output": f"执行超过 {timeout} 秒，判定超时",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "success": False,
            "tests_run": 0,
            "tests_failed": 0,
            "failure_type": FailureType.RUNTIME_ERROR,
            "output": f"子进程启动失败: {exc}",
        }

    output = (proc.stdout or "") + (proc.stderr or "")
    return _parse_unittest_output(output, proc.returncode)


def _parse_unittest_output(output: str, returncode: int) -> dict:
    """解析 unittest 输出，判断失败类型。"""
    # 统计行：Ran N tests in ...
    m = re.search(r"Ran\s+(\d+)\s+tests?", output)
    tests_run = int(m.group(1)) if m else 0

    # 语法错误 / 导入错误
    if "SyntaxError" in output:
        return {
            "success": False,
            "tests_run": tests_run,
            "tests_failed": tests_run,
            "failure_type": FailureType.SYNTAX_ERROR,
            "output": output,
        }
    if "ImportError" in output or "ModuleNotFoundError" in output:
        return {
            "success": False,
            "tests_run": tests_run,
            "tests_failed": tests_run,
            "failure_type": FailureType.IMPORT_ERROR,
            "output": output,
        }

    # 运行时错误（Error）vs 断言失败（Failure）
    error_count = len(re.findall(r"^\w+.*\.\.\.\s*ERROR", output, re.MULTILINE))
    fail_count = len(re.findall(r"^\w+.*\.\.\.\s*FAIL", output, re.MULTILINE))

    # unittest 汇总行
    m2 = re.search(r"failures=(\d+)", output)
    m3 = re.search(r"errors=(\d+)", output)
    if m2:
        fail_count = max(fail_count, int(m2.group(1)))
    if m3:
        error_count = max(error_count, int(m3.group(1)))

    tests_failed = fail_count + error_count

    if returncode == 0 and tests_failed == 0:
        return {
            "success": True,
            "tests_run": tests_run,
            "tests_failed": 0,
            "failure_type": FailureType.NONE,
            "output": output,
        }

    # 有 ERROR 视为运行时错误，有 FAIL 视为断言失败
    if error_count > 0 and fail_count == 0:
        ftype = FailureType.RUNTIME_ERROR
    else:
        ftype = FailureType.TEST_FAILURE

    return {
        "success": False,
        "tests_run": tests_run,
        "tests_failed": tests_failed,
        "failure_type": ftype,
        "output": output,
    }


def _check_entry_point(code: str, entry_point: str) -> Optional[str]:
    """检查代码是否定义了要求的入口函数/类。"""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None  # 语法错误由测试阶段报告
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name == entry_point:
                return None
    return f"代码中未找到入口 '{entry_point}'"


def run_single_case(
    case: EvalCase,
    agent,
    max_iterations: int = 3,
) -> CaseResult:
    """对单个用例执行完整的 生成→测试→反思修复 循环。

    参数 max_iterations 对应 Skill Best Practice 的迭代上限（默认 3）。
    """
    history = []  # 对应 Skill: log history
    code = agent.generate(case.case_id, case.spec)
    history.append({"iteration": 1, "action": "generate"})

    last_result = None
    for iteration in range(1, max_iterations + 1):
        # 入口检查
        missing = _check_entry_point(code, case.entry_point)
        if missing:
            result = score_case(
                case_id=case.case_id, title=case.title,
                category=case.category, difficulty=case.difficulty,
                code=code, tests_run=0, tests_failed=1,
                failure_type=FailureType.INCOMPLETE,
                error_output=missing, iterations=iteration,
            )
            history.append({"iteration": iteration, "status": "incomplete"})
            last_result = result
            # 尝试修复
            if iteration < max_iterations:
                code = agent.fix(case.case_id, case.spec, code, missing)
                history.append({"iteration": iteration + 1, "action": "fix"})
                continue
            else:
                break

        # 写入临时目录并运行测试
        with tempfile.TemporaryDirectory(prefix=f"eval_{case.case_id}_") as tmpdir:
            sol_path = os.path.join(tmpdir, "solution.py")
            test_path = os.path.join(tmpdir, "test_solution.py")
            with open(sol_path, "w", encoding="utf-8") as f:
                f.write(code)
            with open(test_path, "w", encoding="utf-8") as f:
                f.write(case.test_code)

            run_result = _run_tests_in_subprocess(tmpdir, case.timeout)

        result = score_case(
            case_id=case.case_id, title=case.title,
            category=case.category, difficulty=case.difficulty,
            code=code,
            tests_run=run_result["tests_run"],
            tests_failed=run_result["tests_failed"],
            failure_type=run_result["failure_type"],
            error_output=run_result["output"],
            iterations=iteration,
        )
        last_result = result
        history.append({
            "iteration": iteration,
            "status": "pass" if result.passed else "fail",
            "failure_type": result.failure_type.value,
            "score": round(result.weighted_score, 4),
        })

        # 收敛检查：通过则停止（对应 Skill: convergence check）
        if result.passed:
            break

        # 未通过且还有迭代次数，反馈错误让智能体修复
        if iteration < max_iterations:
            code = agent.fix(
                case.case_id, case.spec, code,
                run_result["output"][-1500:],
            )
            history.append({"iteration": iteration + 1, "action": "fix"})

    # 将历史附加到结果（不进入 JSON 评分，但用于调试）
    last_result.history = history  # type: ignore[attr-defined]
    return last_result


def run_all(
    agent,
    cases: Optional[list[EvalCase]] = None,
    max_iterations: int = 3,
) -> list[CaseResult]:
    """运行全部用例。"""
    if cases is None:
        cases = load_cases()
    results = []
    for case in cases:
        print(f"[{case.case_id}] {case.title} ...", end=" ", flush=True)
        r = run_single_case(case, agent, max_iterations=max_iterations)
        status = "PASS" if r.passed else f"FAIL({r.failure_type.value})"
        print(f"{status}  score={r.weighted_score:.3f}  iters={r.iterations}")
        results.append(r)
    return results


def summarize(results: list[CaseResult], threshold: float = 0.8) -> dict:
    """汇总结果，返回结构化统计（对应 Skill 的 structured output）。"""
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    avg_score = sum(r.weighted_score for r in results) / total if total else 0.0

    # 按失败类型统计
    failure_counts = {}
    for r in results:
        key = r.failure_type.value
        failure_counts[key] = failure_counts.get(key, 0) + 1

    # 按分类统计
    by_category = {}
    for r in results:
        by_category.setdefault(r.category, []).append(r.weighted_score)
    by_category = {k: round(sum(v) / len(v), 4) for k, v in by_category.items()}

    # 按难度统计
    by_difficulty = {}
    for r in results:
        by_difficulty.setdefault(r.difficulty, []).append(r.weighted_score)
    by_difficulty = {k: round(sum(v) / len(v), 4) for k, v in by_difficulty.items()}

    # 维度均分
    dim_avgs = {}
    for dim in ("accuracy", "edge_case", "code_quality", "efficiency"):
        vals = [r.scores.get(dim, 0) for r in results]
        dim_avgs[dim] = round(sum(vals) / len(vals), 4) if vals else 0.0

    return {
        "total_cases": total,
        "passed": passed,
        "pass_rate": round(passed / total, 4) if total else 0.0,
        "average_score": round(avg_score, 4),
        "threshold": threshold,
        "meets_threshold": avg_score >= threshold,
        "failure_distribution": failure_counts,
        "average_by_category": by_category,
        "average_by_difficulty": by_difficulty,
        "dimension_averages": dim_avgs,
        "cases": [r.to_dict() for r in results],
    }
