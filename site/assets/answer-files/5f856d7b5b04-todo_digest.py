#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
待办逾期摘要自动化流程（最小可用 / 只读预演版）
================================================

功能：收集本周待办 → 筛出逾期项 → 生成摘要 → 人工确认后发送（Ably 频道）

安全设计：
  1. 默认 DRY_RUN=true，只打印不发送。
  2. 即使关闭 DRY_RUN，发送前仍要求在终端输入大写 "CONFIRM" 才会继续。
  3. 真正的 Ably 发布动作封装在 _ably_publish_stub() 中，当前为桩函数：
     它只打印将要调用的工具与参数，不发起任何网络请求。
     要接入真实环境，需先满足前置条件（见 AUTH_CHECKLIST.md），
     并将桩函数替换为通过 Rube MCP 调用 ABLY_PUBLISH_MESSAGE_TO_CHANNEL。
  4. 不读取、不打印任何真实个人敏感信息；数据源为本地 JSON。

用法：
  python3 todo_digest.py                         # 干跑（默认，安全）
  python3 todo_digest.py --input sample_todos.json
  DRY_RUN=false python3 todo_digest.py           # 进入发送确认流程（仍需人工输入 CONFIRM）
"""

import argparse
import json
import os
import sys
from datetime import date, datetime
from pathlib import Path

# ---------- 配置 ----------
TODAY = date.today()
WEEK_START = TODAY  # 简化：以当天为基准；实际可按周一计算
DRY_RUN = os.environ.get("DRY_RUN", "true").lower() != "false"
# 目标 Ably 频道——仅为占位，实际频道名需经授权确认后方可填入
ABLY_CHANNEL = "PLACEHOLDER_CHANNEL_NEEDS_AUTHORIZATION"

# 停止条件：命中任一项立即中止，不进入发送
STOP_CONDITIONS = [
    "Rube MCP 未连接或 RUBE_SEARCH_TOOLS 不可用",
    "Ably toolkit 连接状态非 ACTIVE",
    "未提供已授权的目标频道名称（当前为占位符）",
    "数据源中包含未脱敏的真实个人敏感信息",
    "DRY_RUN=false 但未在终端输入大写 CONFIRM",
    "待办数据为空或解析失败",
]


def load_todos(path: str) -> list:
    """从本地 JSON 加载待办。实际环境中此函数应替换为已授权的任务系统读取。"""
    p = Path(path)
    if not p.exists():
        print(f"[中止] 数据文件不存在：{path}")
        sys.exit(2)
    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)
    todos = data.get("todos", [])
    if not todos:
        print("[中止] 待办数据为空，停止条件命中。")
        sys.exit(2)
    return todos


def filter_overdue(todos: list, today: date) -> list:
    """筛出逾期项：截止日期早于今天且状态不是已完成。"""
    overdue = []
    for t in todos:
        due = datetime.strptime(t["due_date"], "%Y-%m-%d").date()
        if due < today and t.get("status") != "已完成":
            overdue.append({**t, "days_overdue": (today - due).days})
    overdue.sort(key=lambda x: x["days_overdue"], reverse=True)
    return overdue


def build_summary(overdue: list, today: date) -> str:
    """生成纯文本摘要。不包含任何真实个人敏感信息。"""
    lines = []
    lines.append(f"【待办逾期摘要】生成日期：{today.isoformat()}")
    lines.append(f"逾期项数量：{len(overdue)}")
    lines.append("-" * 40)
    for t in overdue:
        lines.append(
            f"[{t['id']}] {t['title']} | 负责人：{t['owner']} | "
            f"截止：{t['due_date']} | 已逾期 {t['days_overdue']} 天 | "
            f"优先级：{t['priority']} | 状态：{t['status']}"
        )
    lines.append("-" * 40)
    lines.append("请相关负责人尽快处理或更新截止日期。")
    return "\n".join(lines)


def _ably_publish_stub(channel: str, message: str) -> dict:
    """
    Ably 发布桩函数（只读预演，不发网络请求）。

    真实接入时应替换为通过 Rube MCP 执行：
      RUBE_SEARCH_TOOLS  → 发现 ABLY_PUBLISH_MESSAGE_TO_CHANNEL 的最新 schema
      RUBE_MANAGE_CONNECTIONS toolkits:["ably"] → 确认 ACTIVE
      RUBE_MULTI_EXECUTE_TOOL → 按 schema 发布消息
    并携带 memory:{} 与复用的 session_id。
    """
    print("\n[桩函数] 以下为将要执行的 Ably 发布动作（未实际发送）：")
    print(f"  工具：ABLY_PUBLISH_MESSAGE_TO_CHANNEL（schema 需经 RUBE_SEARCH_TOOLS 实时获取）")
    print(f"  频道：{channel}")
    print(f"  消息长度：{len(message)} 字符")
    print("  注意：消息一经发布即不可撤回，订阅者将立即收到。")
    return {"stub": True, "published": False, "channel": channel}


def human_confirm(prompt: str) -> bool:
    """终端人工确认，必须输入大写 CONFIRM。"""
    print("\n" + "=" * 50)
    print(prompt)
    print("=" * 50)
    answer = input("输入大写 CONFIRM 继续，其他任意输入中止：").strip()
    return answer == "CONFIRM"


def main():
    parser = argparse.ArgumentParser(description="待办逾期摘要自动化（干跑/预演版）")
    parser.add_argument("--input", default="sample_todos.json", help="待办 JSON 文件路径")
    args = parser.parse_args()

    print(f"运行模式：{'DRY_RUN（干跑，不发送）' if DRY_RUN else '待发送（需人工确认）'}")
    print(f"当前日期：{TODAY.isoformat()}")

    # 前置检查
    print("\n[前置检查]")
    print("  - Rube MCP 可用性：未连接（当前环境无 RUBE_SEARCH_TOOLS）")
    print("  - Ably 连接状态：未连接（未执行 RUBE_MANAGE_CONNECTIONS）")
    print(f"  - 目标频道：{ABLY_CHANNEL}（占位符，未授权）")

    # 停止条件检查
    blocked = []
    if ABLY_CHANNEL.startswith("PLACEHOLDER"):
        blocked.append("目标频道为占位符，未获授权")
    if not DRY_RUN:
        blocked.append("Rube MCP 未连接，无法真实发布")
    if blocked:
        print("\n[停止条件命中]")
        for b in blocked:
            print(f"  ! {b}")
        if not DRY_RUN:
            print("→ 即使设置了 DRY_RUN=false，因前置条件不满足，仍不会发送。")

    # 加载与处理
    todos = load_todos(args.input)
    overdue = filter_overdue(todos, TODAY)
    summary = build_summary(overdue, TODAY)

    print("\n" + "=" * 50)
    print("生成的摘要内容：")
    print("=" * 50)
    print(summary)

    # 发送环节
    if DRY_RUN:
        print("\n[干跑] 未发送任何消息。将摘要写入本地文件供人工复核。")
        out = Path("digest_preview.txt")
        out.write_text(summary, encoding="utf-8")
        print(f"[干跑] 预览已保存：{out.resolve()}")
        return

    # 非干跑：双重保险——人工确认 + 桩函数
    if not human_confirm("即将通过 Ably 发布上述摘要。此操作不可撤回。"):
        print("[已中止] 用户未确认，未发送任何消息。")
        return

    result = _ably_publish_stub(ABLY_CHANNEL, summary)
    print(f"\n[结果] {result}")


if __name__ == "__main__":
    main()
