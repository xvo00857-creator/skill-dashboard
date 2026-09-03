#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每周待办逾期摘要 - 最小可用版本（默认 dry-run 只读预演）

流程（对应 CI/CD 质量门禁思想，每一步不可跳过）：
  门禁1 收集    → 从数据源读取本周待办
  门禁2 校验    → 校验数据完整性（id/owner/due_date/status 非空）
  门禁3 筛选    → 筛出逾期项（due_date < 今天 且 status != done）
  门禁4 摘要    → 按负责人聚合，生成可读摘要
  门禁5 人工确认 → 打印摘要并等待人工确认（默认 dry-run，不发送）
  门禁6 发送    → 仅在 --confirm 且配置了发送渠道时执行（本版本未接入真实渠道）

安全设计：
  - 默认 dry-run，只读取和打印，不写入、不发送
  - 不硬编码任何凭据；真实发送凭据须从环境变量读取
  - 发送前必须人工确认，无自动发送
  - 每一步失败即中止，不跳过门禁
"""

import argparse
import json
import os
import sys
from datetime import date, datetime
from pathlib import Path

# ---------- 配置 ----------

# 今天的日期（实际运行时取系统日期；预演可用 --today 覆盖）
DEFAULT_TODAY = date.today().isoformat()

# 合法状态
VALID_STATUSES = {"todo", "in_progress", "done", "blocked"}

# 发送渠道凭据环境变量名（本版本不实际使用，仅声明所需权限）
REQUIRED_ENV_FOR_SEND = ["DIGEST_WEBHOOK_URL"]  # 例如飞书群机器人 webhook


# ---------- 门禁1：收集 ----------

def collect_tasks(data_path: str) -> dict:
    """从本地 JSON 文件读取待办数据（模拟从任务系统收集）。"""
    p = Path(data_path)
    if not p.exists():
        raise FileNotFoundError(f"数据源不存在: {data_path}")
    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if "tasks" not in data or not isinstance(data["tasks"], list):
        raise ValueError("数据格式错误：缺少 tasks 数组")
    print(f"[门禁1 收集] 读取到 {len(data['tasks'])} 条待办")
    return data


# ---------- 门禁2：校验 ----------

def validate_tasks(tasks: list) -> list:
    """校验每条任务必填字段，不合法的记录并中止（不静默丢弃）。"""
    errors = []
    for t in tasks:
        for field in ("id", "owner", "title", "due_date", "status"):
            if field not in t or t[field] in (None, ""):
                errors.append(f"任务缺少字段 {field}: {t}")
        if t.get("status") not in VALID_STATUSES:
            errors.append(f"任务 {t.get('id')} 状态非法: {t.get('status')}")
        try:
            datetime.strptime(t["due_date"], "%Y-%m-%d")
        except (ValueError, TypeError):
            errors.append(f"任务 {t.get('id')} 日期格式非法: {t.get('due_date')}")
    if errors:
        raise ValueError("数据校验失败：\n  - " + "\n  - ".join(errors))
    print(f"[门禁2 校验] {len(tasks)} 条任务全部通过字段校验")
    return tasks


# ---------- 门禁3：筛选逾期 ----------

def filter_overdue(tasks: list, today: date) -> list:
    """筛出逾期项：截止日期早于今天且未完成。"""
    overdue = []
    for t in tasks:
        due = datetime.strptime(t["due_date"], "%Y-%m-%d").date()
        if due < today and t["status"] != "done":
            days_overdue = (today - due).days
            overdue.append({**t, "days_overdue": days_overdue})
    overdue.sort(key=lambda x: x["days_overdue"], reverse=True)
    print(f"[门禁3 筛选] 逾期项 {len(overdue)} 条（共 {len(tasks)} 条）")
    return overdue


# ---------- 门禁4：生成摘要 ----------

def build_summary(overdue: list, today: date, week_range: dict) -> str:
    """按负责人聚合逾期项，生成 Markdown 摘要。"""
    lines = []
    lines.append(f"# 本周待办逾期摘要（{today.isoformat()}）")
    lines.append(f"统计周期：{week_range.get('start', '?')} ~ {week_range.get('end', '?')}")
    lines.append("")
    if not overdue:
        lines.append("无逾期项。")
        return "\n".join(lines)

    # 按负责人聚合
    by_owner = {}
    for t in overdue:
        by_owner.setdefault(t["owner"], []).append(t)

    lines.append(f"共 **{len(overdue)}** 项逾期，涉及 **{len(by_owner)}** 人：")
    lines.append("")
    for owner, items in sorted(by_owner.items()):
        lines.append(f"## {owner}（{len(items)} 项）")
        for t in items:
            status_label = {"todo": "未开始", "in_progress": "进行中", "blocked": "阻塞"}.get(
                t["status"], t["status"]
            )
            lines.append(
                f"- [{t['id']}] {t['title']}（截止 {t['due_date']}，"
                f"逾期 {t['days_overdue']} 天，状态：{status_label}）"
            )
        lines.append("")
    return "\n".join(lines)


# ---------- 门禁5：人工确认 ----------

def human_confirm(summary: str, dry_run: bool) -> bool:
    """打印摘要并请求人工确认。dry-run 模式下只展示，不进入发送。"""
    print("\n" + "=" * 60)
    print(summary)
    print("=" * 60)
    if dry_run:
        print("\n[门禁5 人工确认] 当前为 dry-run 只读预演，不执行发送。")
        print("如需真实发送，需：1) 配置发送渠道凭据 2) 加 --confirm 参数 3) 人工输入 YES 确认")
        return False
    answer = input("\n确认发送以上摘要？输入 YES 继续，其他任意键取消：").strip()
    if answer != "YES":
        print("[门禁5 人工确认] 已取消发送。")
        return False
    print("[门禁5 人工确认] 已确认。")
    return True


# ---------- 门禁6：发送（占位，未接入真实渠道） ----------

def send_summary(summary: str) -> None:
    """发送摘要。本版本为占位实现，不执行真实发送。

    真实接入时应：
      - 从环境变量读取 webhook（不得硬编码）
      - 使用最小权限的机器人凭据
      - 记录发送日志（时间、接收方、消息ID）以便回滚/撤回
      - 失败重试不超过 3 次，失败即告警
    """
    missing = [v for v in REQUIRED_ENV_FOR_SEND if not os.environ.get(v)]
    if missing:
        raise RuntimeError(
            f"发送凭据未配置，缺少环境变量: {', '.join(missing)}。"
            "本版本不执行真实发送。"
        )
    # 真实发送逻辑应在此处实现；当前版本主动拒绝
    raise NotImplementedError(
        "真实发送渠道未接入。按安全要求，本最小可用版本不执行实际发送。"
    )


# ---------- 主流程 ----------

def main():
    parser = argparse.ArgumentParser(description="每周待办逾期摘要（默认 dry-run）")
    parser.add_argument("--data", default="sample_tasks.json", help="待办数据 JSON 路径")
    parser.add_argument("--today", default=DEFAULT_TODAY, help="覆盖今天日期（YYYY-MM-DD），用于预演")
    parser.add_argument("--confirm", action="store_true", help="启用真实发送（仍需人工确认和凭据）")
    args = parser.parse_args()

    dry_run = not args.confirm
    today = datetime.strptime(args.today, "%Y-%m-%d").date()

    print(f"=== 每周待办逾期摘要 ===")
    print(f"运行模式: {'dry-run 只读预演' if dry_run else '发送模式'}")
    print(f"基准日期: {today.isoformat()}\n")

    try:
        # 门禁1-4 顺序执行，任一失败即中止
        data = collect_tasks(args.data)
        tasks = validate_tasks(data["tasks"])
        overdue = filter_overdue(tasks, today)
        summary = build_summary(overdue, today, data.get("week_range", {}))

        # 门禁5 人工确认
        confirmed = human_confirm(summary, dry_run)

        # 门禁6 发送（仅确认后）
        if confirmed and not dry_run:
            send_summary(summary)
            print("[门禁6 发送] 发送完成。")
        else:
            print("\n流程结束（未发送）。")

    except Exception as e:
        print(f"\n[流程中止] {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
