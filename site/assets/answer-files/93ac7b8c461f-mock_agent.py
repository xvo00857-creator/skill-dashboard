#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mock 代码生成智能体 —— 仅用于本地验证评测框架，不访问网络、不需要账号。

接口契约（与 run_eval.py 配套）：
    stdin  : {"prompt": "...", "case_id": "C01"}
    stdout : {"code": "..."}

行为设计（用于验证框架的失败检测与反模式惩罚）：
    C01-C04：返回正确实现
    C05：返回有边界缺陷的二分查找（空列表时崩溃）
    C06：返回含硬编码默认密码的实现（触发 HARDCODED_SECRET 反模式）
"""
import json
import sys

SOLUTIONS = {
    "C01": "def two_sum(nums, target):\n"
           "    seen = {}\n"
           "    for i, n in enumerate(nums):\n"
           "        if target - n in seen:\n"
           "            return [seen[target - n], i]\n"
           "        seen[n] = i\n"
           "    return []\n",

    "C02": "def reverse_words(s):\n"
           "    if not s:\n"
           "        return ''\n"
           "    return ' '.join(s.split()[::-1])\n",

    "C03": "def fib(n):\n"
           "    a, b = 0, 1\n"
           "    for _ in range(n):\n"
           "        a, b = b, a + b\n"
           "    return a\n",

    "C04": "def most_common_char(s):\n"
           "    if not s:\n"
           "        return None\n"
           "    counts = {}\n"
           "    order = []\n"
           "    for ch in s:\n"
           "        if ch not in counts:\n"
           "            counts[ch] = 0\n"
           "            order.append(ch)\n"
           "        counts[ch] += 1\n"
           "    best_ch, best_count = None, -1\n"
           "    for ch in order:\n"
           "        if counts[ch] > best_count:\n"
           "            best_count = counts[ch]\n"
           "            best_ch = ch\n"
           "    return best_ch\n",

    # 故意缺陷：空数组时 arr[lo] 抛 IndexError
    "C05": "def binary_search(arr, target):\n"
           "    lo, hi = 0, len(arr) - 1\n"
           "    while lo < hi:\n"
           "        mid = (lo + hi) // 2\n"
           "        if arr[mid] < target:\n"
           "            lo = mid + 1\n"
           "        else:\n"
           "            hi = mid\n"
           "    return lo if arr[lo] == target else -1\n",

    # 故意反模式：硬编码默认密码
    "C06": "DEFAULT_PASSWORD = 'Admin1234'\n"
           "\n"
           "def validate_password(password):\n"
           "    issues = []\n"
           "    if len(password) < 8:\n"
           "        issues.append('too short')\n"
           "    if not any(c.isdigit() for c in password):\n"
           "        issues.append('need digit')\n"
           "    if not any(c.isupper() for c in password):\n"
           "        issues.append('need uppercase')\n"
           "    if password == DEFAULT_PASSWORD:\n"
           "        issues.append('default password not allowed')\n"
           "    return {'valid': len(issues) == 0, 'issues': issues}\n",
}


def main():
    data = json.load(sys.stdin)
    case_id = data.get("case_id", "")
    code = SOLUTIONS.get(case_id, "# no solution for this case\n")
    json.dump({"code": code}, sys.stdout)


if __name__ == "__main__":
    main()
