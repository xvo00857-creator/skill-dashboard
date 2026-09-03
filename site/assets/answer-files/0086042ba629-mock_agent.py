#!/usr/bin/env python3
"""
mock_agent.py —— 用于可重复验证的模拟代码生成智能体。

该 agent 不依赖任何模型或外部账号，仅根据 prompt 在本地题目库中
查找标准答案并返回，用于验证 run_eval.py 的评测流程是否正确。

两种模式（通过环境变量 MOCK_AGENT_MODE 切换）：
  oracle（默认）: 对所有题目返回标准答案，预期 pass@1 = 1.0
  flawed       : 对部分题目返回有缺陷的代码，用于验证失败分类
                 - 第 0 题：返回错误逻辑（wrong_answer）
                 - 第 1 题：返回语法错误代码（syntax_error）
                 - 第 2 题：返回运行时异常代码（runtime_error）
                 - 第 3 题：返回空字符串（empty_generation）
                 - 第 4 题：不定义入口函数（missing_function）
                 - 第 5 题：返回死循环代码（timeout）
                 - 其余题：返回标准答案

真实模型接入方式：
  将本文件替换为调用实际代码生成模型的实现，只需保持
  generate(prompt: str) -> str 这一接口签名即可。
  若模型需要 HuggingFace 账号/GPU，请在调用前完成登录与环境准备，
  本评测框架本身不涉及任何外部账号。
"""

import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROBLEMS_PATH = os.path.join(_HERE, "problems.json")

with open(_PROBLEMS_PATH, "r", encoding="utf-8") as _f:
    _PROBLEMS = json.load(_f)

# 建立 prompt -> canonical_solution 的查找表
_LOOKUP = {p["prompt"]: p["canonical_solution"] for p in _PROBLEMS}

_MODE = os.environ.get("MOCK_AGENT_MODE", "oracle")


def generate(prompt: str) -> str:
    """模拟代码生成：接收 prompt，返回补全代码。"""
    if _MODE == "flawed":
        return _generate_flawed(prompt)
    # oracle 模式：返回标准答案
    solution = _LOOKUP.get(prompt, "")
    if solution:
        return solution
    # 兜底：返回一个空函数（会触发 missing_function 或 wrong_answer）
    return "    pass\n"


def _generate_flawed(prompt: str) -> str:
    """有缺陷的生成结果，用于验证失败分类。"""
    # 通过 prompt 特征判断题号
    if "def add(a, b)" in prompt:
        # 错误逻辑：用减法代替加法
        return "    return a - b\n"
    if "def reverse_string" in prompt:
        # 语法错误：切片括号未闭合
        return "    return s[::-1\n"
    if "def find_max" in prompt:
        # 运行时错误：除零
        return "    return 1 / 0\n"
    if "def factorial" in prompt:
        # 空生成
        return ""
    if "def is_palindrome" in prompt:
        # 不定义入口函数，定义了别的函数
        return "def helper():\n    return True\n"
    if "def count_vowels" in prompt:
        # 死循环，触发超时
        return "    while True:\n        pass\n"
    # 其余题返回标准答案
    return _LOOKUP.get(prompt, "    pass\n")
