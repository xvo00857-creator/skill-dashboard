#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""代码生成智能体评测集 —— 主入口。

用法：
    python run_eval.py                     # 默认 mixed 模式模拟智能体，最多 3 轮反思
    python run_eval.py --mode correct      # 全部正确实现
    python run_eval.py --mode buggy        # 全部有缺陷实现
    python run_eval.py --mode mixed        # 混合（默认）
    python run_eval.py --max-iterations 1  # 关闭反思修复，仅单次生成
    python run_eval.py --threshold 0.6     # 自定义合格阈值
    python run_eval.py --json-out result.json --md-out report.md

不依赖任何第三方库，仅使用 Python 标准库。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime

# 确保可以 import 同目录模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mock_agent import MockCodeAgent
from runner import run_all, summarize, load_cases


def render_markdown(summary: dict, agent_mode: str, max_iterations: int) -> str:
    """将结构化结果渲染为 Markdown 报告。"""
    lines = []
    lines.append("# 代码生成智能体评测报告")
    lines.append("")
    lines.append(f"- 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"- 智能体模式：`{agent_mode}`（模拟）")
    lines.append(f"- 最大反思轮数：{max_iterations}")
    lines.append(f"- 合格阈值：{summary['threshold']}")
    lines.append("")

    lines.append("## 总览")
    lines.append("")
    lines.append(f"| 指标 | 值 |")
    lines.append(f"|------|-----|")
    lines.append(f"| 用例总数 | {summary['total_cases']} |")
    lines.append(f"| 通过数 | {summary['passed']} |")
    lines.append(f"| 通过率 | {summary['pass_rate']:.1%} |")
    lines.append(f"| 平均加权得分 | {summary['average_score']:.4f} |")
    lines.append(f"| 是否达标 | {'是' if summary['meets_threshold'] else '否'} |")
    lines.append("")

    lines.append("## 维度均分")
    lines.append("")
    lines.append("| 维度 | 权重 | 均分 |")
    lines.append("|------|------|------|")
    weights = {"accuracy": 0.50, "edge_case": 0.20, "code_quality": 0.20, "efficiency": 0.10}
    descs = {
        "accuracy": "功能正确性",
        "edge_case": "边界与异常处理",
        "code_quality": "代码质量",
        "efficiency": "效率",
    }
    for dim, score in summary["dimension_averages"].items():
        lines.append(f"| {descs[dim]}（{dim}） | {weights[dim]:.0%} | {score:.4f} |")
    lines.append("")

    lines.append("## 失败类型分布")
    lines.append("")
    if summary["failure_distribution"]:
        lines.append("| 失败类型 | 数量 |")
        lines.append("|----------|------|")
        for ftype, count in sorted(summary["failure_distribution"].items()):
            lines.append(f"| {ftype} | {count} |")
    else:
        lines.append("无失败。")
    lines.append("")

    lines.append("## 分类与难度均分")
    lines.append("")
    lines.append("### 按分类")
    lines.append("")
    lines.append("| 分类 | 均分 |")
    lines.append("|------|------|")
    for cat, score in sorted(summary["average_by_category"].items()):
        lines.append(f"| {cat} | {score:.4f} |")
    lines.append("")
    lines.append("### 按难度")
    lines.append("")
    lines.append("| 难度 | 均分 |")
    lines.append("|------|------|")
    for diff, score in sorted(summary["average_by_difficulty"].items()):
        lines.append(f"| {diff} | {score:.4f} |")
    lines.append("")

    lines.append("## 逐用例明细")
    lines.append("")
    lines.append("| 用例 | 标题 | 分类 | 难度 | 结果 | 失败类型 | 测试通过/总数 | 加权分 | 轮数 |")
    lines.append("|------|------|------|------|------|----------|---------------|--------|------|")
    for c in summary["cases"]:
        passed_str = "PASS" if c["passed"] else "FAIL"
        tests_str = f"{c['tests_run'] - c['tests_failed']}/{c['tests_run']}"
        lines.append(
            f"| {c['case_id']} | {c['title']} | {c['category']} | {c['difficulty']} "
            f"| {passed_str} | {c['failure_type']} | {tests_str} "
            f"| {c['weighted_score']:.4f} | {c['iterations']} |"
        )
    lines.append("")

    # 失败用例的错误摘要
    failed_cases = [c for c in summary["cases"] if not c["passed"]]
    if failed_cases:
        lines.append("## 失败用例错误摘要")
        lines.append("")
        for c in failed_cases:
            lines.append(f"### {c['case_id']} {c['title']}")
            lines.append(f"- 失败类型：`{c['failure_type']}`")
            if c["quality_notes"]:
                lines.append(f"- 质量提示：{'; '.join(c['quality_notes'])}")
            lines.append("")
            lines.append("```")
            # 只取最后 30 行错误输出
            err_lines = c["error_output"].strip().splitlines()
            lines.extend(err_lines[-30:])
            lines.append("```")
            lines.append("")

    lines.append("## 结果汇总模板")
    lines.append("")
    lines.append("> 以下模板可用于多次评测间对比，复制后填写即可。")
    lines.append("")
    lines.append("```markdown")
    lines.append("### 评测批次：____")
    lines.append("- 智能体版本/标识：____")
    lines.append(f"- 用例总数：{summary['total_cases']}")
    lines.append("- 通过率：____%")
    lines.append("- 平均加权得分：____")
    lines.append(f"- 合格阈值：{summary['threshold']}（达标/未达标）")
    lines.append("- 主要失败类型：____")
    lines.append("- 维度短板：____")
    lines.append("- 与上批次差异：____")
    lines.append("- 结论与改进项：____")
    lines.append("```")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="代码生成智能体小型评测集")
    parser.add_argument("--mode", choices=["correct", "buggy", "mixed"],
                        default="mixed", help="模拟智能体模式（默认 mixed）")
    parser.add_argument("--max-iterations", type=int, default=3,
                        help="反思修复最大轮数（默认 3，对应 Skill 建议）")
    parser.add_argument("--threshold", type=float, default=0.8,
                        help="合格阈值（默认 0.8）")
    parser.add_argument("--json-out", default="",
                        help="JSON 结果输出路径（默认 result.json）")
    parser.add_argument("--md-out", default="",
                        help="Markdown 报告输出路径（默认 report.md）")
    args = parser.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    json_path = args.json_out or os.path.join(here, "result.json")
    md_path = args.md_out or os.path.join(here, "report.md")

    print("=" * 60)
    print("代码生成智能体评测集")
    print(f"模式: {args.mode}  最大反思轮数: {args.max_iterations}  阈值: {args.threshold}")
    print("=" * 60)

    agent = MockCodeAgent(mode=args.mode)
    cases = load_cases()
    results = run_all(agent, cases=cases, max_iterations=args.max_iterations)
    summary = summarize(results, threshold=args.threshold)

    # 写 JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"\nJSON 结果已写入: {json_path}")

    # 写 Markdown
    md = render_markdown(summary, args.mode, args.max_iterations)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"Markdown 报告已写入: {md_path}")

    # 控制台汇总
    print("\n" + "=" * 60)
    print(f"通过率: {summary['pass_rate']:.1%}  "
          f"平均分: {summary['average_score']:.4f}  "
          f"达标: {'是' if summary['meets_threshold'] else '否'}")
    print("=" * 60)

    return 0 if summary["meets_threshold"] else 1


if __name__ == "__main__":
    sys.exit(main())
