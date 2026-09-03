# -*- coding: utf-8 -*-
"""模拟代码生成智能体。

为满足"不依赖外部账号"的约束，本模块提供一个本地模拟智能体：
- 对部分用例返回正确实现（演示通过）
- 对部分用例返回有缺陷的实现（演示失败检测）
- 支持反思接口：收到错误信息后尝试修复（演示 Skill 的 Code-Specific Reflection 模式）

接入真实智能体时，只需实现 CodeAgent 接口的 generate() 和 fix() 方法，
将其内部替换为实际 LLM 调用即可，无需改动 runner。
"""
from __future__ import annotations

# 预置的"正确"参考实现
_CORRECT = {
    "C01": '''\
def reverse_words(s: str) -> str:
    """按空格分词后逐词反转，保持词序。"""
    if not s:
        return ""
    return " ".join(word[::-1] for word in s.split(" "))
''',
    "C02": '''\
def fizzbuzz(n: int) -> list[str]:
    """经典 FizzBuzz，返回 1..n 的字符串列表。"""
    if n <= 0:
        return []
    result = []
    for i in range(1, n + 1):
        if i % 15 == 0:
            result.append("FizzBuzz")
        elif i % 3 == 0:
            result.append("Fizz")
        elif i % 5 == 0:
            result.append("Buzz")
        else:
            result.append(str(i))
    return result
''',
    "C03": '''\
def group_by_key(items: list[dict], key: str) -> dict:
    """按指定 key 对字典列表分组，缺失 key 归入 __missing__。"""
    result = {}
    for item in items:
        if key in item:
            group = item[key]
        else:
            group = "__missing__"
        result.setdefault(group, []).append(item)
    return result
''',
    "C04": '''\
def is_palindrome(s: str) -> bool:
    """忽略大小写和非字母数字字符，判断是否回文。"""
    cleaned = [c.lower() for c in s if c.isalnum()]
    return cleaned == cleaned[::-1]
''',
    "C05": '''\
def calculate(a, op, b):
    """四则运算，除零抛 ZeroDivisionError，非法运算符抛 ValueError。"""
    if op == "+":
        return a + b
    if op == "-":
        return a - b
    if op == "*":
        return a * b
    if op == "/":
        if b == 0:
            raise ZeroDivisionError("division by zero")
        return a / b
    raise ValueError(f"unsupported operator: {op}")
''',
}

# 预置的"有缺陷"实现（用于演示失败检测）
_BUGGY = {
    # 整体反转字符串而非逐词反转
    "C01": '''\
def reverse_words(s: str) -> str:
    return s[::-1]
''',
    # 忘记处理 n<=0
    "C02": '''\
def fizzbuzz(n: int) -> list[str]:
    result = []
    for i in range(1, n + 1):
        if i % 3 == 0:
            result.append("Fizz")
        elif i % 5 == 0:
            result.append("Buzz")
        else:
            result.append(str(i))
    return result
''',
    # 缺少 __missing__ 处理
    "C03": '''\
def group_by_key(items: list[dict], key: str) -> dict:
    result = {}
    for item in items:
        result.setdefault(item[key], []).append(item)
    return result
''',
    # 没有忽略非字母数字
    "C04": '''\
def is_palindrome(s: str) -> bool:
    return s == s[::-1]
''',
    # 除零不抛异常而是返回 None
    "C05": '''\
def calculate(a, op, b):
    if op == "+":
        return a + b
    if op == "-":
        return a - b
    if op == "*":
        return a * b
    if op == "/":
        if b == 0:
            return None
        return a / b
    return None
''',
}


class MockCodeAgent:
    """模拟代码生成智能体。

    mode:
      "correct" — 全部返回正确实现
      "buggy"   — 全部返回有缺陷实现
      "mixed"   — 偶数用例正确，奇数用例有缺陷（默认）
    """

    def __init__(self, mode: str = "mixed"):
        self.mode = mode
        self.call_log = []  # 记录调用历史（对应 Skill 的 log history）

    def _select(self, case_id: str) -> str:
        if self.mode == "correct":
            return _CORRECT[case_id]
        if self.mode == "buggy":
            return _BUGGY[case_id]
        # mixed：C01/C03/C05 正确，C02/C04 有缺陷
        return _CORRECT[case_id] if case_id in ("C01", "C03", "C05") else _BUGGY[case_id]

    def generate(self, case_id: str, spec: str) -> str:
        """根据任务规格生成代码。"""
        code = self._select(case_id)
        self.call_log.append({"action": "generate", "case_id": case_id})
        return code

    def fix(self, case_id: str, spec: str, previous_code: str, error: str) -> str:
        """根据测试错误信息修复代码（反思迭代）。

        模拟策略：如果有正确版本，直接返回正确版本；否则原样返回。
        真实智能体应将 error 反馈给 LLM 让其修复。
        """
        self.call_log.append({"action": "fix", "case_id": case_id, "error": error[:200]})
        # 模拟：有正确答案时修复成功
        if case_id in _CORRECT:
            return _CORRECT[case_id]
        return previous_code


class CodeAgent:
    """真实智能体接口占位。

    接入真实 LLM 时实现此类：
        def generate(self, case_id, spec) -> str:
            return call_llm(spec)
        def fix(self, case_id, spec, previous_code, error) -> str:
            return call_llm(f"修复以下代码，错误：{error}\\n{previous_code}")
    """

    def generate(self, case_id: str, spec: str) -> str:
        raise NotImplementedError("请接入真实 LLM 后实现此方法")

    def fix(self, case_id: str, spec: str, previous_code: str, error: str) -> str:
        raise NotImplementedError("请接入真实 LLM 后实现此方法")
