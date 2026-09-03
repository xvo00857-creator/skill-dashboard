# -*- coding: utf-8 -*-
"""评分规则与失败类型定义。

依据 agentic-eval Skill 的 Rubric-Based 评估策略：
- 多维度加权评分（accuracy / edge_case / code_quality / efficiency）
- 结构化 JSON 结果
- 失败类型枚举，便于统计分析
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# 失败类型
# ---------------------------------------------------------------------------
class FailureType(str, Enum):
    """代码生成智能体的失败分类。"""

    NONE = "none"                    # 全部通过
    SYNTAX_ERROR = "syntax_error"    # 代码无法解析/编译
    RUNTIME_ERROR = "runtime_error"  # 运行时抛出未预期异常
    TEST_FAILURE = "test_failure"    # 断言失败
    TIMEOUT = "timeout"              # 执行超时
    INCOMPLETE = "incomplete"        # 缺少入口函数/类
    SECURITY_RISK = "security_risk"  # 检测到危险调用（eval/exec/os.system 等）
    IMPORT_ERROR = "import_error"    # 依赖缺失或导入失败


# ---------------------------------------------------------------------------
# 评分量规（权重合计 1.0）
# ---------------------------------------------------------------------------
RUBRIC = {
    "accuracy":     {"weight": 0.50, "desc": "功能正确性：单元测试通过率"},
    "edge_case":    {"weight": 0.20, "desc": "边界与异常处理：零值/空值/非法输入/除零"},
    "code_quality": {"weight": 0.20, "desc": "代码质量：结构清晰、命名规范、无冗余"},
    "efficiency":   {"weight": 0.10, "desc": "效率：无明显性能反模式（死循环/嵌套灾难）"},
}

# 合格阈值（对应 Skill 中 score_threshold，默认 0.8）
DEFAULT_THRESHOLD = 0.8


# ---------------------------------------------------------------------------
# 危险模式检测（不新增依赖，用正则做基础静态检查）
# ---------------------------------------------------------------------------
_DANGEROUS_PATTERNS = [
    (r"\beval\s*\(", "eval()"),
    (r"\bexec\s*\(", "exec()"),
    (r"\bos\.system\s*\(", "os.system()"),
    (r"\bsubprocess\.(call|run|Popen)\s*\(", "subprocess"),
    (r"\b__import__\s*\(", "__import__()"),
    (r"\bopen\s*\(.+['\"]w", "file write"),
]


def detect_security_risk(code: str) -> list[str]:
    """返回检测到的危险调用描述列表。"""
    hits = []
    for pattern, label in _DANGEROUS_PATTERNS:
        if re.search(pattern, code):
            hits.append(label)
    return hits


def static_quality_check(code: str) -> dict:
    """轻量静态检查，返回 code_quality 和 efficiency 的启发式得分（0-1）。

    不依赖外部 linter，仅用标准库 ast：
    - 函数/类有 docstring 加分
    - 函数过长（>50 行）扣分
    - 嵌套深度 >4 扣分
    - 存在 while True 且无 break 视为潜在死循环，扣 efficiency
    """
    quality = 1.0
    efficiency = 1.0
    notes = []

    try:
        tree = ast.parse(code)
    except SyntaxError:
        return {"code_quality": 0.0, "efficiency": 0.0,
                "notes": ["代码存在语法错误，无法做静态分析"]}

    func_count = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func_count += 1
            # docstring 检查
            if not ast.get_docstring(node):
                quality -= 0.05
                notes.append(f"函数 {node.name} 缺少 docstring")
            # 函数长度
            length = node.end_lineno - node.lineno if node.end_lineno else 0
            if length > 50:
                quality -= 0.10
                notes.append(f"函数 {node.name} 过长（{length} 行）")
            # 嵌套深度
            max_depth = _max_nest_depth(node)
            if max_depth > 4:
                quality -= 0.10
                notes.append(f"函数 {node.name} 嵌套过深（{max_depth} 层）")
            # 死循环启发式
            if _has_infinite_loop(node):
                efficiency -= 0.5
                notes.append(f"函数 {node.name} 疑似存在无退出的 while True")

    if func_count == 0:
        quality -= 0.2
        notes.append("未定义任何函数")

    return {
        "code_quality": max(0.0, quality),
        "efficiency": max(0.0, efficiency),
        "notes": notes,
    }


def _max_nest_depth(node: ast.AST, depth: int = 0) -> int:
    """递归计算控制流最大嵌套深度。"""
    max_d = depth
    nesting_types = (ast.If, ast.For, ast.While, ast.With,
                     ast.Try, ast.AsyncFor, ast.AsyncWith)
    for child in ast.iter_child_nodes(node):
        if isinstance(child, nesting_types):
            max_d = max(max_d, _max_nest_depth(child, depth + 1))
        else:
            max_d = max(max_d, _max_nest_depth(child, depth))
    return max_d


def _has_infinite_loop(func_node: ast.FunctionDef) -> bool:
    """检测 while True 且函数体内无 break/return/raise。"""
    for node in ast.walk(func_node):
        if isinstance(node, ast.While):
            if isinstance(node.test, ast.Constant) and node.test.value is True:
                has_exit = any(
                    isinstance(n, (ast.Break, ast.Return, ast.Raise))
                    for n in ast.walk(node)
                )
                if not has_exit:
                    return True
    return False


# ---------------------------------------------------------------------------
# 单条用例评分结果
# ---------------------------------------------------------------------------
@dataclass
class CaseResult:
    case_id: str
    title: str
    category: str
    difficulty: str
    passed: bool
    failure_type: FailureType
    tests_run: int = 0
    tests_failed: int = 0
    error_output: str = ""
    scores: dict = field(default_factory=dict)   # 各维度 0-1
    weighted_score: float = 0.0                  # 加权总分 0-1
    iterations: int = 1                          # 反思迭代次数
    quality_notes: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "title": self.title,
            "category": self.category,
            "difficulty": self.difficulty,
            "passed": self.passed,
            "failure_type": self.failure_type.value,
            "tests_run": self.tests_run,
            "tests_failed": self.tests_failed,
            "weighted_score": round(self.weighted_score, 4),
            "scores": {k: round(v, 4) for k, v in self.scores.items()},
            "iterations": self.iterations,
            "quality_notes": self.quality_notes,
            "error_output": self.error_output[:2000],
        }


def score_case(
    case_id: str,
    title: str,
    category: str,
    difficulty: str,
    code: str,
    tests_run: int,
    tests_failed: int,
    failure_type: FailureType,
    error_output: str,
    iterations: int = 1,
) -> CaseResult:
    """根据测试结果和静态检查计算单条用例的加权得分。"""
    # accuracy：测试通过率
    accuracy = 1.0 - (tests_failed / tests_run) if tests_run > 0 else 0.0

    # edge_case：通过边界相关测试的比例（简化：全部通过=1，否则按通过率折算）
    edge_case = accuracy

    # 静态质量
    sq = static_quality_check(code)

    # 安全风险一票否决
    security_hits = detect_security_risk(code)
    if security_hits:
        failure_type = FailureType.SECURITY_RISK
        accuracy = 0.0
        edge_case = 0.0
        sq["code_quality"] = 0.0
        sq["notes"].append(f"检测到危险调用: {', '.join(security_hits)}")

    # 语法错误/超时/不完整：accuracy 归零
    if failure_type in (FailureType.SYNTAX_ERROR, FailureType.TIMEOUT,
                        FailureType.INCOMPLETE, FailureType.IMPORT_ERROR):
        accuracy = 0.0
        edge_case = 0.0

    scores = {
        "accuracy": accuracy,
        "edge_case": edge_case,
        "code_quality": sq["code_quality"],
        "efficiency": sq["efficiency"],
    }
    weighted = sum(scores[d] * RUBRIC[d]["weight"] for d in RUBRIC)

    return CaseResult(
        case_id=case_id,
        title=title,
        category=category,
        difficulty=difficulty,
        passed=(tests_failed == 0 and failure_type == FailureType.NONE),
        failure_type=failure_type,
        tests_run=tests_run,
        tests_failed=tests_failed,
        error_output=error_output,
        scores=scores,
        weighted_score=weighted,
        iterations=iterations,
        quality_notes=sq["notes"],
    )
