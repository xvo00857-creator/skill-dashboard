#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
待办事项周报自动化 —— 只读预演脚本（dry-run）

功能：
  1. 收集本周待办事项
  2. 筛出逾期项
  3. 生成摘要
  4. 在"发送"前停止，保留人工确认

安全边界：
  - 本脚本仅使用内置模拟数据，不连接任何外部服务
  - 不读取真实任务系统、不访问网络、不发送任何消息
  - 所有"发送"动作仅打印预演内容，不执行
  - 不包含任何真实个人信息（姓名均为化名）
"""

import json
from datetime import datetime, timedelta
from typing import NamedTuple

# ============================================================
# 配置区：实际部署时应由授权配置文件或环境变量提供，禁止硬编码凭据
# ============================================================

CONFIG = {
    "dry_run": True,           # 安全默认值：始终为 True，需显式授权才可关闭
    "week_start": None,        # 本周起始日期，None 时自动取本周一
    "send_channel": None,      # 发送渠道：None=不发送 / "feishu" / "email" / ...
    "send_target": None,       # 发送目标（群 ID / 邮件地址），None=不发送
    "data_source": "builtin_mock",  # 数据源：builtin_mock=内置模拟数据
}

# ============================================================
# 模拟数据（化名，非真实人员；实际部署时替换为授权的数据源读取逻辑）
# ============================================================

class TodoItem(NamedTuple):
    id: str
    owner: str          # 负责人（化名）
    title: str
    due_date: str       # YYYY-MM-DD
    status: str         # pending / in_progress / done
    priority: str       # high / medium / low


MOCK_TODOS = [
    TodoItem("T-001", "成员甲", "完成需求评审文档", "2026-08-10", "in_progress", "high"),
    TodoItem("T-002", "成员乙", "修复登录页崩溃问题", "2026-08-09", "pending", "high"),
    TodoItem("T-003", "成员丙", "设计数据看板原型", "2026-08-12", "in_progress", "medium"),
    TodoItem("T-004", "成员丁", "编写接口测试用例", "2026-08-14", "pending", "medium"),
    TodoItem("T-005", "成员戊", "整理用户反馈清单", "2026-08-08", "done", "low"),
    TodoItem("T-006", "成员甲", "输出竞品分析报告", "2026-08-13", "pending", "high"),
    TodoItem("T-007", "成员乙", "优化首页加载速度", "2026-08-11", "in_progress", "medium"),
    TodoItem("T-008", "成员丙", "对齐下周迭代目标", "2026-08-15", "pending", "low"),
    TodoItem("T-009", "成员丁", "部署预发环境验证", "2026-08-07", "pending", "high"),
    TodoItem("T-010", "成员戊", "更新团队知识库", "2026-08-12", "in_progress", "low"),
]


# ============================================================
# 工具函数
# ============================================================

def get_week_range(today: datetime) -> tuple[datetime, datetime]:
    """返回本周一 00:00 到本周日 23:59。"""
    weekday = today.weekday()  # 周一=0
    monday = datetime(today.year, today.month, today.day) - timedelta(days=weekday)
    sunday = monday + timedelta(days=6, hours=23, minutes=59, seconds=59)
    return monday, sunday


def collect_this_week(todos: list[TodoItem], week_start: datetime,
                      week_end: datetime) -> list[TodoItem]:
    """收集本周待办：截止日期落在本周内，或本周仍未完成的事项。"""
    result = []
    for t in todos:
        due = datetime.strptime(t.due_date, "%Y-%m-%d")
        in_this_week = week_start <= due <= week_end
        still_open = t.status in ("pending", "in_progress")
        if in_this_week or (still_open and due < week_start):
            result.append(t)
    return result


def filter_overdue(todos: list[TodoItem], today: datetime) -> list[TodoItem]:
    """筛出逾期项：截止日期早于今天且未完成。"""
    result = []
    for t in todos:
        due = datetime.strptime(t.due_date, "%Y-%m-%d")
        if due.date() < today.date() and t.status in ("pending", "in_progress"):
            result.append(t)
    return sorted(result, key=lambda x: x.due_date)


def generate_summary(week_todos: list[TodoItem], overdue: list[TodoItem],
                     today: datetime) -> str:
    """生成文本摘要。"""
    lines = []
    lines.append(f"【五人产品团队 · 本周待办摘要】")
    lines.append(f"生成日期：{today.strftime('%Y-%m-%d')}（只读预演，未发送）")
    lines.append("")

    # 按负责人分组统计
    owners = {}
    for t in week_todos:
        owners.setdefault(t.owner, []).append(t)

    lines.append(f"本周待办共 {len(week_todos)} 项，涉及 {len(owners)} 人：")
    for owner in sorted(owners):
        items = owners[owner]
        done = sum(1 for i in items if i.status == "done")
        lines.append(f"  - {owner}：{len(items)} 项（已完成 {done}，进行中/待办 {len(items) - done}）")
    lines.append("")

    # 逾期项
    lines.append(f"⚠ 逾期未完成：{len(overdue)} 项")
    if overdue:
        for t in overdue:
            days_overdue = (today.date() - datetime.strptime(t.due_date, "%Y-%m-%d").date()).days
            lines.append(
                f"  - [{t.id}] {t.title}（负责人：{t.owner}，"
                f"截止：{t.due_date}，已逾期 {days_overdue} 天，"
                f"优先级：{t.priority}，状态：{t.status}）"
            )
    else:
        lines.append("  无")
    lines.append("")

    # 本周内待完成（按日期排序）
    upcoming = sorted(
        [t for t in week_todos if t.status != "done" and t not in overdue],
        key=lambda x: x.due_date,
    )
    lines.append(f"本周待完成（不含逾期）：{len(upcoming)} 项")
    for t in upcoming:
        lines.append(
            f"  - [{t.id}] {t.title}（负责人：{t.owner}，"
            f"截止：{t.due_date}，优先级：{t.priority}）"
        )

    lines.append("")
    lines.append("—— 以上为只读预演结果，需人工确认后方可发送 ——")
    return "\n".join(lines)


def human_confirmation(summary: str) -> bool:
    """
    人工确认环节。
    安全规则：dry-run 模式下永远返回 False，不执行任何发送动作。
    实际部署时应通过交互界面或审批工单获取明确授权。
    """
    print("=" * 60)
    print("人工确认点（HUMAN CHECKPOINT）")
    print("=" * 60)
    print(summary)
    print("=" * 60)

    if CONFIG["dry_run"]:
        print("[DRY-RUN] 当前为只读预演模式，跳过发送。")
        print("[DRY-RUN] 如需实际发送，须同时满足：")
        print("         1. 配置文件中 dry_run 设为 false")
        print("         2. 已配置授权的发送渠道与目标")
        print("         3. 人工在确认界面明确点击「确认发送」")
        return False

    # 非 dry-run 时的交互确认（实际部署中替换为正式审批流）
    answer = input("确认发送以上摘要？(输入 YES 确认，其他任意键取消)：").strip()
    return answer == "YES"


def send_summary(summary: str) -> dict:
    """
    发送摘要（占位）。
    安全规则：仅在 human_confirmation 返回 True 后调用。
    当前实现不执行任何真实发送，仅返回操作记录。
    """
    channel = CONFIG.get("send_channel")
    target = CONFIG.get("send_target")

    if not channel or not target:
        return {
            "sent": False,
            "reason": "未配置发送渠道或目标，已阻止发送",
            "channel": channel,
            "target": target,
        }

    # 实际部署时在此处调用授权的消息 API，并记录审计日志
    # 严禁在此处硬编码任何 token / webhook / 密码
    return {
        "sent": False,
        "reason": "发送功能未启用：当前预演版本不包含真实发送逻辑",
        "channel": channel,
        "target": "***（已脱敏）",
    }


# ============================================================
# 主流程
# ============================================================

def main():
    today = datetime.now()
    week_start, week_end = get_week_range(today)

    print(f"今天日期：{today.strftime('%Y-%m-%d %A')}")
    print(f"本周范围：{week_start.strftime('%Y-%m-%d')} ~ {week_end.strftime('%Y-%m-%d')}")
    print(f"数据源：{CONFIG['data_source']}（内置模拟数据，非真实数据）")
    print()

    # Step 1: 收集本周待办
    week_todos = collect_this_week(MOCK_TODOS, week_start, week_end)
    print(f"[Step 1] 收集本周待办：{len(week_todos)} 项")

    # Step 2: 筛出逾期项
    overdue = filter_overdue(week_todos, today)
    print(f"[Step 2] 筛出逾期项：{len(overdue)} 项")

    # Step 3: 生成摘要
    summary = generate_summary(week_todos, overdue, today)
    print(f"[Step 3] 摘要已生成（{len(summary)} 字符）")
    print()

    # Step 4: 人工确认（dry-run 下不发送）
    confirmed = human_confirmation(summary)

    if confirmed:
        result = send_summary(summary)
        print(f"[Step 4] 发送结果：{json.dumps(result, ensure_ascii=False, indent=2)}")
    else:
        print("[Step 4] 未发送。流程在人工确认点安全停止。")


if __name__ == "__main__":
    main()
