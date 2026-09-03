# 代码生成智能体评测报告

- 生成时间：2026-08-12 06:33:01
- 智能体模式：`buggy`（模拟）
- 最大反思轮数：1
- 合格阈值：0.8

## 总览

| 指标 | 值 |
|------|-----|
| 用例总数 | 5 |
| 通过数 | 0 |
| 通过率 | 0.0% |
| 平均加权得分 | 0.7483 |
| 是否达标 | 否 |

## 维度均分

| 维度 | 权重 | 均分 |
|------|------|------|
| 功能正确性（accuracy） | 50% | 0.6548 |
| 边界与异常处理（edge_case） | 20% | 0.6548 |
| 代码质量（code_quality） | 20% | 0.9500 |
| 效率（efficiency） | 10% | 1.0000 |

## 失败类型分布

| 失败类型 | 数量 |
|----------|------|
| runtime_error | 1 |
| test_failure | 4 |

## 分类与难度均分

### 按分类

| 分类 | 均分 |
|------|------|
| data_transform | 0.8733 |
| edge_case | 0.7275 |
| number | 0.8900 |
| string | 0.5233 |

### 按难度

| 难度 | 均分 |
|------|------|
| easy | 0.7067 |
| hard | 0.8150 |
| medium | 0.7567 |

## 逐用例明细

| 用例 | 标题 | 分类 | 难度 | 结果 | 失败类型 | 测试通过/总数 | 加权分 | 轮数 |
|------|------|------|------|------|----------|---------------|--------|------|
| C01 | 字符串按词反转 | string | easy | FAIL | test_failure | 2/6 | 0.5233 | 1 |
| C02 | FizzBuzz 变体 | number | easy | FAIL | test_failure | 6/7 | 0.8900 | 1 |
| C03 | 按字段分组 | data_transform | medium | FAIL | runtime_error | 5/6 | 0.8733 | 1 |
| C04 | 回文检测（含边界） | edge_case | medium | FAIL | test_failure | 4/8 | 0.6400 | 1 |
| C05 | 安全计算器 | edge_case | hard | FAIL | test_failure | 6/8 | 0.8150 | 1 |

## 失败用例错误摘要

### C01 字符串按词反转
- 失败类型：`test_failure`
- 质量提示：函数 reverse_words 缺少 docstring

```
AssertionError: 'dlrow olleh' != 'olleh dlrow'
- dlrow olleh
+ olleh dlrow


======================================================================
FAIL: test_palindrome_word (test_solution.TestReverseWords)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/s1/g82qmjcs1kv5cswcl2pjhj0m0000gn/T/eval_C01_po4b_xx1/test_solution.py", line 19, in test_palindrome_word
    self.assertEqual(solution.reverse_words("level radar"), "level radar")
AssertionError: 'radar level' != 'level radar'
- radar level
+ level radar


======================================================================
FAIL: test_single_char_words (test_solution.TestReverseWords)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/s1/g82qmjcs1kv5cswcl2pjhj0m0000gn/T/eval_C01_po4b_xx1/test_solution.py", line 22, in test_single_char_words
    self.assertEqual(solution.reverse_words("a b c"), "a b c")
AssertionError: 'c b a' != 'a b c'
- c b a
+ a b c


======================================================================
FAIL: test_three_words (test_solution.TestReverseWords)
-----
```

### C02 FizzBuzz 变体
- 失败类型：`test_failure`
- 质量提示：函数 fizzbuzz 缺少 docstring

```
test_basic (test_solution.TestFizzBuzz) ... ok
test_first_three (test_solution.TestFizzBuzz) ... ok
test_fizzbuzz_at_15 (test_solution.TestFizzBuzz) ... FAIL
test_length (test_solution.TestFizzBuzz) ... ok
test_negative (test_solution.TestFizzBuzz) ... ok
test_one (test_solution.TestFizzBuzz) ... ok
test_zero (test_solution.TestFizzBuzz) ... ok

======================================================================
FAIL: test_fizzbuzz_at_15 (test_solution.TestFizzBuzz)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/s1/g82qmjcs1kv5cswcl2pjhj0m0000gn/T/eval_C02_jz4gdevd/test_solution.py", line 13, in test_fizzbuzz_at_15
    self.assertEqual(result[14], "FizzBuzz")
AssertionError: 'Fizz' != 'FizzBuzz'
- Fizz
+ FizzBuzz


----------------------------------------------------------------------
Ran 7 tests in 0.002s

FAILED (failures=1)
```

### C03 按字段分组
- 失败类型：`runtime_error`
- 质量提示：函数 group_by_key 缺少 docstring

```
test_basic (test_solution.TestGroupByKey) ... ok
test_empty (test_solution.TestGroupByKey) ... ok
test_missing_key (test_solution.TestGroupByKey) ... ERROR
test_order_preserved (test_solution.TestGroupByKey) ... ok
test_single_group (test_solution.TestGroupByKey) ... ok
test_string_values (test_solution.TestGroupByKey) ... ok

======================================================================
ERROR: test_missing_key (test_solution.TestGroupByKey)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/s1/g82qmjcs1kv5cswcl2pjhj0m0000gn/T/eval_C03_q885pa8y/test_solution.py", line 23, in test_missing_key
    result = solution.group_by_key(data, "a")
  File "/private/var/folders/s1/g82qmjcs1kv5cswcl2pjhj0m0000gn/T/eval_C03_q885pa8y/solution.py", line 4, in group_by_key
    result.setdefault(item[key], []).append(item)
KeyError: 'a'

----------------------------------------------------------------------
Ran 6 tests in 0.002s

FAILED (errors=1)
```

### C04 回文检测（含边界）
- 失败类型：`test_failure`
- 质量提示：函数 is_palindrome 缺少 docstring

```
test_with_spaces (test_solution.TestIsPalindrome) ... FAIL

======================================================================
FAIL: test_case_insensitive (test_solution.TestIsPalindrome)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/s1/g82qmjcs1kv5cswcl2pjhj0m0000gn/T/eval_C04_0e53qboh/test_solution.py", line 24, in test_case_insensitive
    self.assertTrue(solution.is_palindrome("Aa"))
AssertionError: False is not true

======================================================================
FAIL: test_classic (test_solution.TestIsPalindrome)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/s1/g82qmjcs1kv5cswcl2pjhj0m0000gn/T/eval_C04_0e53qboh/test_solution.py", line 7, in test_classic
    self.assertTrue(
AssertionError: False is not true

======================================================================
FAIL: test_only_punctuation (test_solution.TestIsPalindrome)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/s1/g82qmjcs1kv5cswcl2pjhj0m0000gn/T/eval_C04_0e53qboh/test_solution.py", line 18, in test_only_punctuation
    self.assertTrue(solution.is_palindrome("!!!,,,"))
AssertionError: False is not true

======================================================================
FAIL: test_with_spaces (test_solution.TestIsPalindrome)
----------------------------------------------------------------------
Trace
```

### C05 安全计算器
- 失败类型：`test_failure`
- 质量提示：函数 calculate 缺少 docstring

```
test_add (test_solution.TestCalculate) ... ok
test_divide (test_solution.TestCalculate) ... ok
test_divide_zero (test_solution.TestCalculate) ... FAIL
test_float (test_solution.TestCalculate) ... ok
test_invalid_op (test_solution.TestCalculate) ... FAIL
test_multiply (test_solution.TestCalculate) ... ok
test_negative (test_solution.TestCalculate) ... ok
test_subtract (test_solution.TestCalculate) ... ok

======================================================================
FAIL: test_divide_zero (test_solution.TestCalculate)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/s1/g82qmjcs1kv5cswcl2pjhj0m0000gn/T/eval_C05_pdfv4hm1/test_solution.py", line 20, in test_divide_zero
    solution.calculate(1, "/", 0)
AssertionError: ZeroDivisionError not raised

======================================================================
FAIL: test_invalid_op (test_solution.TestCalculate)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/s1/g82qmjcs1kv5cswcl2pjhj0m0000gn/T/eval_C05_pdfv4hm1/test_solution.py", line 24, in test_invalid_op
    solution.calculate(1, "%", 2)
AssertionError: ValueError not raised

----------------------------------------------------------------------
Ran 8 tests in 0.001s

FAILED (failures=2)
```

## 结果汇总模板

> 以下模板可用于多次评测间对比，复制后填写即可。

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
