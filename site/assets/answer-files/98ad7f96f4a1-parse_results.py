#!/usr/bin/env python3
"""Cosmos Policy 评估结果解析脚本。

对应 SKILL.md Workflow 1 Step 4「Validate and parse results」与 Workflow 2
Step 3「Inspect the final Success rate: line in the log」。在官方日志目录中
查找 JSON 结果与日志中的 Success rate 行，按修改时间排序并展示。

仅使用 Python 标准库，不假设 JSON 结果的具体 schema（SKILL.md 只给出了
json.load + print 的最小片段），因此以原样 pretty-print 为主，并尝试高亮
常见的成功率字段（若存在）。

用法:
    python scripts/parse_results.py                         # 展示 LIBERO 最新一次结果
    python scripts/parse_results.py --benchmark robocasa    # 展示 RoboCasa 最新结果
    python scripts/parse_results.py --list                  # 列出全部结果文件
    python scripts/parse_results.py --last 3                # 展示最近 3 次结果
    python scripts/parse_results.py --log-dir /custom/path  # 自定义日志目录
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# SKILL.md 中记录的官方默认日志目录（相对仓库根）
DEFAULT_LOG_DIRS = {
    "libero": "cosmos_policy/experiments/robot/libero/logs",
    "robocasa": "cosmos_policy/experiments/robot/robocasa/logs",
}

# 日志中成功率行的模式（SKILL.md RoboCasa Step 3: "Success rate:" 行）
SUCCESS_RATE_RE = re.compile(r"success\s*rate\s*[:=]\s*([0-9.]+%?)", re.IGNORECASE)

# JSON 中常见的成功率字段名（仅在存在时高亮，不做假设）
SUCCESS_KEYS = {
    "success_rate",
    "success",
    "success_rate_mean",
    "successes",
    "num_successes",
    "num_trials",
    "score",
}


def find_json_files(log_dir: Path) -> list[Path]:
    """递归查找日志目录下所有 JSON 文件，按修改时间倒序。"""
    if not log_dir.is_dir():
        return []
    files = [p for p in log_dir.rglob("*.json") if p.is_file()]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files


def find_log_files(log_dir: Path) -> list[Path]:
    """递归查找日志目录下可能的文本日志文件。"""
    if not log_dir.is_dir():
        return []
    exts = {".log", ".txt", ".out"}
    files = [p for p in log_dir.rglob("*") if p.is_file() and p.suffix.lower() in exts]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files


def highlight_success_keys(obj: object, prefix: str = "") -> list[str]:
    """在 JSON 对象中递归查找成功率相关字段并返回可展示行。"""
    hits: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.lower() in SUCCESS_KEYS and not isinstance(v, (dict, list)):
                hits.append(f"{prefix}{k}: {v}")
            else:
                hits.extend(highlight_success_keys(v, f"{prefix}{k}."))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            hits.extend(highlight_success_keys(v, f"{prefix}[{i}]."))
    return hits


def scan_success_rate_lines(log_files: list[Path]) -> list[tuple[Path, int, str]]:
    """在日志文件中扫描 Success rate 行，返回 (文件, 行号, 行内容)。"""
    found: list[tuple[Path, int, str]] = []
    for lf in log_files:
        try:
            with lf.open("r", encoding="utf-8", errors="replace") as f:
                for lineno, line in enumerate(f, 1):
                    if SUCCESS_RATE_RE.search(line):
                        found.append((lf, lineno, line.strip()))
        except OSError:
            continue
    return found


def show_result(json_path: Path) -> None:
    print(f"-- 结果文件: {json_path}")
    try:
        with json_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"   读取失败: {exc}")
        return

    # 先高亮成功率字段（若存在），再原样输出完整 JSON
    hits = highlight_success_keys(data)
    if hits:
        print("   成功率相关字段:")
        for h in hits:
            print(f"     - {h}")
    else:
        print("   （未发现常见成功率字段，输出完整 JSON 供人工查看）")
    print("   完整内容:")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    print()


def main() -> int:
    parser = argparse.ArgumentParser(description="解析 Cosmos Policy 评估结果")
    parser.add_argument(
        "--benchmark",
        choices=["libero", "robocasa"],
        default="libero",
        help="评估目标，决定默认日志目录（默认 libero）",
    )
    parser.add_argument(
        "--log-dir",
        default=None,
        help="自定义日志目录（覆盖 --benchmark 对应的默认目录）",
    )
    parser.add_argument(
        "--last",
        type=int,
        default=1,
        help="展示最近 N 次 JSON 结果（默认 1）",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="仅列出找到的结果文件，不打印内容",
    )
    parser.add_argument(
        "--no-logs",
        action="store_true",
        help="跳过对文本日志中 Success rate 行的扫描",
    )
    args = parser.parse_args()

    log_dir = Path(args.log_dir) if args.log_dir else Path(DEFAULT_LOG_DIRS[args.benchmark])
    print(f"日志目录: {log_dir.resolve()}")
    print()

    json_files = find_json_files(log_dir)
    if not json_files:
        print(
            f"未在 {log_dir} 下找到 JSON 结果文件。请确认评估已运行且 "
            "--local_log_dir 指向该目录。"
        )
        return 1

    if args.list:
        print(f"共找到 {len(json_files)} 个 JSON 结果文件（按修改时间倒序）:")
        for p in json_files:
            mtime = p.stat().st_mtime
            print(f"  {p}  (mtime={mtime:.0f})")
        return 0

    n = max(1, args.last)
    print(f"展示最近 {min(n, len(json_files))} 次 JSON 结果:")
    print()
    for jf in json_files[:n]:
        show_result(jf)

    if not args.no_logs:
        log_files = find_log_files(log_dir)
        rate_lines = scan_success_rate_lines(log_files)
        if rate_lines:
            print("-- 日志中的 Success rate 行 --")
            for lf, lineno, line in rate_lines[-10:]:  # 最近 10 条
                print(f"  {lf}:{lineno}: {line}")
        else:
            print("（未在文本日志中匹配到 Success rate 行；RoboCasa 评估通常会打印该行）")

    return 0


if __name__ == "__main__":
    sys.exit(main())
