#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
周待办逾期摘要 —— 只读预演脚本（dry-run by default）

设计原则：
1. 默认只读：只读取本地 JSON、筛选、生成摘要、写入本地草稿文件，不发送任何消息。
2. 发送闸门：即使加 --send，也必须在终端二次输入大写 CONFIRM 才会执行；
   且发送动作在本预演版中为桩函数（仅打印+写日志），不触达任何真实渠道。
3. 无网络、无凭据、无真实个人信息：数据来源为本地合成数据文件。
4. 全程日志，每步可审计；失败有明确退出码。

用法：
    python3 weekly_todo_digest.py --data mock_todos.json            # 只读预演（默认）
    python3 weekly_todo_digest.py --data mock_todos.json --send     # 尝试发送（仍需二次确认，且为桩函数）
    python3 weekly_todo_digest.py --rollback                        # 回滚最近一次发送（桩函数，仅说明）
"""

import argparse
import json
import logging
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# 常量与退出码
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
DRAFT_DIR = SCRIPT_DIR / "drafts"
LOG_DIR = SCRIPT_DIR / "logs"
SEND_LOG = LOG_DIR / "send_history.jsonl"
ROLLBACK_NOTE = LOG_DIR / "rollback_notes.md"

EXIT_OK = 0
EXIT_DATA_ERROR = 2
EXIT_DATE_ERROR = 3
EXIT_USER_ABORT = 4
EXIT_ROLLBACK_NOTHING = 5
EXIT_UNAUTHORIZED = 6

# 人工确认口令：必须逐字输入才会继续
CONFIRM_PHRASE = "CONFIRM"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("todo-digest")


# ---------------------------------------------------------------------------
# 日期工具
# ---------------------------------------------------------------------------
def week_range(today: date):
    """返回本周一与本周日的日期。周一为一周起点。"""
    monday = today - timedelta(days=today.weekday())  # weekday(): Monday=0
    sunday = monday + timedelta(days=6)
    return monday, sunday


def parse_date(s):
    if not s:
        return None
    return datetime.strptime(s, "%Y-%m-%d").date()


# ---------------------------------------------------------------------------
# 数据加载（只读）
# ---------------------------------------------------------------------------
def load_todos(path: Path):
    if not path.exists():
        log.error("数据文件不存在：%s", path)
        sys.exit(EXIT_DATA_ERROR)
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    # 基本结构校验
    if not isinstance(data, dict) or "team" not in data or "todos" not in data:
        log.error("数据文件结构非法：需要顶层 team 与 todos 字段")
        sys.exit(EXIT_DATA_ERROR)
    log.info("已加载数据：团队 %s，待办 %d 条（来源：本地文件，只读）",
             data.get("team", {}).get("name", "未知"), len(data["todos"]))
    return data


# ---------------------------------------------------------------------------
# 筛选逻辑
# ---------------------------------------------------------------------------
def classify_todos(todos, today: date):
    """
    返回分类结果：
      - overdue:   截止日期 < today 且未完成
      - due_today: 截止日期 == today 且未完成
      - this_week: 截止日期在本周内（today < due <= sunday）且未完成
      - done:      已完成（不论截止日期）
      - no_due:    未完成且无截止日期（需人工确认）
    """
    monday, sunday = week_range(today)
    buckets = {
        "overdue": [],
        "due_today": [],
        "this_week": [],
        "done": [],
        "no_due": [],
    }
    for t in todos:
        status = t.get("status", "open")
        due = parse_date(t.get("due_date"))
        if status == "done":
            buckets["done"].append(t)
        elif due is None:
            buckets["no_due"].append(t)
        elif due < today:
            buckets["overdue"].append(t)
        elif due == today:
            buckets["due_today"].append(t)
        elif monday <= due <= sunday:
            buckets["this_week"].append(t)
        # 晚于本周的暂不纳入摘要
    return buckets


# ---------------------------------------------------------------------------
# 摘要生成
# ---------------------------------------------------------------------------
def build_summary(data, buckets, today: date):
    monday, sunday = week_range(today)
    members = {m["id"]: m["name"] for m in data["team"].get("members", [])}

    lines = []
    lines.append(f"【周待办摘要（只读预演）】")
    lines.append(f"统计日期：{today.isoformat()}（周三）")
    lines.append(f"本周范围：{monday.isoformat()} ~ {sunday.isoformat()}")
    lines.append(f"团队：{data['team'].get('name', '未知')}（共 {len(members)} 人）")
    lines.append("")

    lines.append(f"== 逾期未完成（{len(buckets['overdue'])} 条）==")
    for t in sorted(buckets["overdue"], key=lambda x: x.get("due_date", "")):
        owner = members.get(t.get("owner_id"), "未指派")
        days_over = (today - parse_date(t["due_date"])).days
        lines.append(f"  - [{t['due_date']}] {t['title']}  负责人：{owner}  已逾期 {days_over} 天")
    lines.append("")

    lines.append(f"== 今日到期（{len(buckets['due_today'])} 条）==")
    for t in buckets["due_today"]:
        owner = members.get(t.get("owner_id"), "未指派")
        lines.append(f"  - [今日] {t['title']}  负责人：{owner}")
    lines.append("")

    lines.append(f"== 本周后续到期（{len(buckets['this_week'])} 条）==")
    for t in sorted(buckets["this_week"], key=lambda x: x.get("due_date", "")):
        owner = members.get(t.get("owner_id"), "未指派")
        lines.append(f"  - [{t['due_date']}] {t['title']}  负责人：{owner}")
    lines.append("")

    lines.append(f"== 已完成（{len(buckets['done'])} 条）==")
    for t in buckets["done"]:
        owner = members.get(t.get("owner_id"), "未指派")
        lines.append(f"  - {t['title']}  负责人：{owner}")
    lines.append("")

    if buckets["no_due"]:
        lines.append(f"== 无截止日期、需人工确认（{len(buckets['no_due'])} 条）==")
        for t in buckets["no_due"]:
            owner = members.get(t.get("owner_id"), "未指派")
            lines.append(f"  - {t['title']}  负责人：{owner}")
        lines.append("")

    lines.append("（本摘要由只读预演脚本生成，未发送至任何渠道。发送前须经人工复核。）")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 草稿落盘（本地，可删除，无副作用）
# ---------------------------------------------------------------------------
def save_draft(summary: str, today: date):
    DRAFT_DIR.mkdir(exist_ok=True)
    fname = DRAFT_DIR / f"draft_{today.isoformat()}.txt"
    fname.write_text(summary, encoding="utf-8")
    log.info("草稿已写入本地：%s", fname)
    return fname


# ---------------------------------------------------------------------------
# 发送（桩函数：预演版不触达真实渠道）
# ---------------------------------------------------------------------------
def send_summary_stub(summary: str, today: date, recipients: list):
    """
    预演版发送桩：仅记录日志，不连接任何 IM / 邮件 / API。
    真实环境中此处应替换为经过授权的渠道 API 调用，
    且必须在调用前完成：授权范围确认、收件人核对、凭据从安全配置读取。
    """
    LOG_DIR.mkdir(exist_ok=True)
    record = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "date": today.isoformat(),
        "recipients": recipients,
        "channel": "STUB（未真实发送）",
        "summary_preview": summary[:80] + "...",
        "status": "stub_no_effect",
    }
    with SEND_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    log.warning("发送动作被桩函数拦截：未连接任何真实渠道，仅写入本地日志。")
    log.warning("如需真实发送，须：1) 配置授权凭据 2) 替换桩函数 3) 经人工确认。")
    return record


def rollback_last_send():
    """
    回滚桩：真实消息一旦发出通常无法撤回（邮件尤其如此）。
    本函数仅输出回滚指引，不执行任何撤回动作。
    """
    LOG_DIR.mkdir(exist_ok=True)
    if not SEND_LOG.exists():
        log.error("没有发送记录可回滚。")
        sys.exit(EXIT_ROLLBACK_NOTHING)
    lines = SEND_LOG.read_text(encoding="utf-8").strip().splitlines()
    last = json.loads(lines[-1])
    note = (
        f"# 回滚指引（最近一次发送）\n\n"
        f"- 时间：{last['time']}\n"
        f"- 渠道：{last['channel']}\n"
        f"- 收件人：{last['recipients']}\n\n"
        f"## 回滚步骤（真实环境）\n"
        f"1. 若渠道支持撤回（如部分 IM 2 分钟内），立即在渠道内撤回。\n"
        f"2. 邮件无法可靠撤回：立即向收件人发送更正声明，说明前一封作废。\n"
        f"3. 通知团队负责人与数据/安全接口人，记录事件。\n"
        f"4. 检查发送日志，确认是否还有其他误发。\n\n"
        f"本预演版中发送为桩函数，无真实消息需要回滚。\n"
    )
    ROLLBACK_NOTE.write_text(note, encoding="utf-8")
    log.info("回滚指引已写入：%s", ROLLBACK_NOTE)
    print(note)


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="周待办逾期摘要（只读预演）")
    parser.add_argument("--data", default="mock_todos.json", help="待办数据 JSON 路径")
    parser.add_argument("--today", default=None, help="覆盖统计日期（YYYY-MM-DD），仅用于测试")
    parser.add_argument("--send", action="store_true", help="尝试发送（仍需二次确认，预演版为桩函数）")
    parser.add_argument("--rollback", action="store_true", help="输出最近一次发送的回滚指引")
    args = parser.parse_args()

    if args.rollback:
        rollback_last_send()
        return

    # 解析日期
    if args.today:
        today = parse_date(args.today)
        if today is None:
            log.error("--today 日期格式错误，应为 YYYY-MM-DD")
            sys.exit(EXIT_DATE_ERROR)
    else:
        today = date.today()
    log.info("统计基准日期：%s", today.isoformat())

    # 1. 加载（只读）
    data_path = Path(args.data)
    if not data_path.is_absolute():
        data_path = SCRIPT_DIR / data_path
    data = load_todos(data_path)

    # 2. 筛选
    buckets = classify_todos(data["todos"], today)
    log.info("分类完成：逾期 %d，今日到期 %d，本周后续 %d，已完成 %d，无截止日期 %d",
             len(buckets["overdue"]), len(buckets["due_today"]),
             len(buckets["this_week"]), len(buckets["done"]), len(buckets["no_due"]))

    # 3. 生成摘要
    summary = build_summary(data, buckets, today)

    # 4. 写本地草稿
    draft = save_draft(summary, today)

    # 5. 输出到控制台供人工复核
    print("\n" + "=" * 60)
    print(summary)
    print("=" * 60 + "\n")

    # 6. 发送闸门
    if not args.send:
        log.info("当前为只读预演模式（未加 --send）。流程到此结束，未发送任何消息。")
        log.info("请人工打开草稿复核：%s", draft)
        return

    # 即使加了 --send，也必须二次确认
    log.warning("你选择了发送。请仔细核对上方摘要内容与收件人。")
    recipients = data["team"].get("notify_recipients", [])
    log.warning("拟发送收件人（来自数据文件，须人工核对）：%s", recipients)
    answer = input(f"如确认发送，请输入 {CONFIRM_PHRASE}（其他任意输入取消）：").strip()
    if answer != CONFIRM_PHRASE:
        log.warning("未收到确认口令，发送已取消。")
        sys.exit(EXIT_USER_ABORT)

    record = send_summary_stub(summary, today, recipients)
    log.info("发送桩执行完毕：%s", record["status"])


if __name__ == "__main__":
    main()
