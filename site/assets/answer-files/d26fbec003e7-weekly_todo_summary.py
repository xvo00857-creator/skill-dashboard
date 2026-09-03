#!/usr/bin/env python3
"""weekly_todo_summary.py - 模拟演示脚本（详见 README_DEMO.md）"""
import json, sys, os, shutil
from datetime import date, datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
TODOS_FILE = SCRIPT_DIR / "todos.json"
OUTPUT_FILE = SCRIPT_DIR / "summary_output.md"
BACKUP_DIR = SCRIPT_DIR / ".backup"
TODAY = date(2026, 8, 10)

def load_todos():
    with open(TODOS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def filter_overdue(todos, members, today):
    mmap = {m["id"]: m for m in members}
    overdue = []
    for t in todos:
        due = datetime.strptime(t["due"], "%Y-%m-%d").date()
        if due < today and t["status"] != "done":
            a = mmap.get(t["assignee"], {})
            overdue.append({**t, "assignee_name": a.get("name","?"), "days_overdue": (today-due).days})
    overdue.sort(key=lambda x: x["days_overdue"], reverse=True)
    return overdue

def collect_all(todos, members, today):
    mmap = {m["id"]: m for m in members}
    result = []
    for t in todos:
        due = datetime.strptime(t["due"], "%Y-%m-%d").date()
        a = mmap.get(t["assignee"], {})
        result.append({**t, "assignee_name": a.get("name","?"), "due_date": due,
                       "is_overdue": due < today and t["status"] != "done"})
    return result

def gen_summary(data, overdue, all_t, today):
    L = []
    L.append(f"# 周待办摘要 - {data['team']}")
    L.append("")
    L.append(f"- 周期: {data['week']}")
    L.append(f"- 日期: {today.isoformat()}")
    L.append(f"- 人数: {len(data['members'])}, 待办: {len(all_t)}")
    L.append("")
    done = [t for t in all_t if t["status"]=="done"]
    ip = [t for t in all_t if t["status"]=="in_progress"]
    td = [t for t in all_t if t["status"]=="todo"]
    L.append("## 总览")
    L.append(f"- 已完成: {len(done)} | 进行中: {len(ip)} | 未开始: {len(td)} | **逾期: {len(overdue)}**")
    L.append("")
    L.append(f"## 逾期项 ({len(overdue)})")
    if overdue:
        L.append("| ID | 负责人 | 标题 | 截止 | 逾期天数 | 优先级 |")
        L.append("|---|---|---|---|---|---|")
        for t in overdue:
            L.append(f"| {t['id']} | {t['assignee_name']} | {t['title']} | {t['due']} | {t['days_overdue']}天 | {t['priority']} |")
    L.append("")
    L.append("## 按人汇总")
    for m in data["members"]:
        pt = [t for t in all_t if t["assignee"]==m["id"]]
        pd = [t for t in pt if t["status"]=="done"]
        po = [t for t in pt if t.get("is_overdue")]
        L.append(f"### {m['name']}({m['role']})")
        L.append(f"- 待办{len(pt)} 完成{len(pd)}" + (f" 逾期{len(po)}" if po else ""))
        for t in pt:
            icon = {"done":"[x]","in_progress":"[~]","todo":"[ ]"}.get(t["status"],"?")
            mark = " (逾期!)" if t.get("is_overdue") else ""
            L.append(f"  - {icon} {t['id']}: {t['title']} (截止{t['due']}){mark}")
        L.append("")
    L.append("---")
    L.append("*模拟数据生成，非真实团队信息*")
    return "\n".join(L)

def backup():
    if OUTPUT_FILE.exists():
        BACKUP_DIR.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        bp = BACKUP_DIR / f"summary_{ts}.md.bak"
        shutil.copy2(OUTPUT_FILE, bp)
        print(f"[BACKUP] {bp}")
        return bp
    return None

def main():
    dry = "--dry-run" in sys.argv
    print(f"[INFO] {'DRY-RUN' if dry else 'EXEC'} mode")
    data = load_todos()
    overdue = filter_overdue(data["todos"], data["members"], TODAY)
    all_t = collect_all(data["todos"], data["members"], TODAY)
    summary = gen_summary(data, overdue, all_t, TODAY)

    if dry:
        print("="*60)
        print("=== DRY RUN (借鉴 release-skills --dry-run) ===")
        print("="*60)
        print(f"源: {TODOS_FILE}")
        print(f"目标: {OUTPUT_FILE}")
        print(f"逾期: {len(overdue)} 项")
        print("--- 预览 ---")
        print(summary)
        print("="*60)
        print("No changes made. Run without --dry-run to execute.")
        return 0

    # Step 8 确认
    print()
    print("="*60)
    print("=== 人工确认 (借鉴 release-skills Step 8) ===")
    print("="*60)
    print(f"逾期项: {len(overdue)}")
    for t in overdue:
        print(f"  - {t['id']} {t['title']} ({t['assignee_name']}, 逾期{t['days_overdue']}天)")
    print(f"输出: {OUTPUT_FILE}")

    if os.environ.get("DEMO_AUTO_CONFIRM") != "1":
        print("\n[1]确认 [2]仅逾期 [3]取消")
        try:
            c = input("选择: ").strip()
        except:
            c = "3"
        if c not in ("1","2"):
            print("[CANCELLED] 已取消")
            return 1
    else:
        print("[AUTO] DEMO_AUTO_CONFIRM=1")

    bp = backup()
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(summary)
    print(f"[OK] 已写入 {OUTPUT_FILE}")
    print(f"[NOTE] '发送'=本地写入。真实发送需配置 <WEBHOOK_URL>")
    return 0

if __name__ == "__main__":
    sys.exit(main())
