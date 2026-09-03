#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每周 Adobe 数据收集 -> 摘要 -> 通知：安全模拟器
=================================================
本脚本是 adobe-automation Skill 的离线模拟，不连接 Rube MCP、不调用 Adobe、不联网。
它严格按照 SKILL.md 规定的工作流模式打印日志：
  Step 1 RUBE_SEARCH_TOOLS  (发现工具)
  Step 2 RUBE_MANAGE_CONNECTIONS (检查连接)
  Step 3 RUBE_MULTI_EXECUTE_TOOL (执行：收集 -> 摘要 -> 通知)

用法:
  python3 simulate_weekly_report.py                      # 正常路径
  python3 simulate_weekly_report.py --inject auth_fail   # 模拟 E_AUTH
  python3 simulate_weekly_report.py --inject empty       # 模拟 E_EMPTY
  python3 simulate_weekly_report.py --inject bad_data    # 模拟 E_DATA
  python3 simulate_weekly_report.py --inject exec_fail   # 模拟 E_EXEC
  python3 simulate_weekly_report.py --inject notify_fail # 模拟 E_NOTIFY
  python3 simulate_weekly_report.py --now 2026-08-12T09:00:00+08:00  # 固定运行时刻

仅依赖 Python 3 标准库；不新增任何第三方依赖。
"""

import argparse
import json
import os
import sys
import time
from collections import Counter
from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------------------------
# 路径与常量
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MOCK_DATA = os.path.join(BASE_DIR, "mock_data", "adobe_assets.json")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
TZ = timezone(timedelta(hours=8))  # Asia/Shanghai

# 模拟的工具 slug —— 明确标注 MOCK，真实运行时必须由 RUBE_SEARCH_TOOLS 返回
MOCK_TOOLS = {
    "collect": "MOCK_ADOBE_LIST_ASSETS",
    "summary": "MOCK_ADOBE_CREATE_SUMMARY_DOC",
    "notify": "MOCK_ADOBE_SHARE_AND_NOTIFY",
}

OWNER_EMAIL = "owner@example.com"  # 模拟配置，不真实发送


# ---------------------------------------------------------------------------
# 日志
# ---------------------------------------------------------------------------
class Logger:
    def __init__(self, log_path):
        self.log_path = log_path
        self._fh = open(log_path, "w", encoding="utf-8")

    def log(self, msg):
        line = f"[{datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S%z')}] {msg}"
        print(line)
        self._fh.write(line + "\n")
        self._fh.flush()

    def section(self, title):
        bar = "=" * 70
        self.log(bar)
        self.log(title)
        self.log(bar)

    def close(self):
        self._fh.close()


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------
def parse_iso(s):
    """解析 ISO8601 时间字符串，失败抛 ValueError。"""
    return datetime.fromisoformat(s)


def week_range(now):
    """返回 now 所在周的周一 00:00 和下周一 00:00（Asia/Shanghai）。"""
    monday = (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    next_monday = monday + timedelta(days=7)
    return monday, next_monday


def iso_week_label(dt):
    return f"{dt.isocalendar()[0]}-W{dt.isocalendar()[1]:02d}"


# ---------------------------------------------------------------------------
# Step 1: 模拟 RUBE_SEARCH_TOOLS
# ---------------------------------------------------------------------------
def step1_search_tools(logger):
    logger.section("Step 1: RUBE_SEARCH_TOOLS（发现工具）")
    logger.log("queries: [{use_case: 'weekly collect adobe assets data and generate summary'}]")
    logger.log("session: {generate_id: true}")
    session_id = f"mock-session-{int(time.time())}"
    logger.log(f"-> session_id = {session_id}")
    logger.log("-> 返回可用工具（MOCK，真实 slug 以 RUBE_SEARCH_TOOLS 为准）:")
    for role, slug in MOCK_TOOLS.items():
        logger.log(f"     {role:8s}: {slug}")
    logger.log("-> 无分页 token，工具发现完成。")
    return session_id


# ---------------------------------------------------------------------------
# Step 2: 模拟 RUBE_MANAGE_CONNECTIONS
# ---------------------------------------------------------------------------
def step2_check_connection(logger, session_id, inject):
    logger.section("Step 2: RUBE_MANAGE_CONNECTIONS（检查 Adobe 连接）")
    logger.log(f"toolkits: [\"adobe\"]  session_id: {session_id}")
    if inject == "auth_fail":
        logger.log("-> 连接状态: PENDING（非 ACTIVE）")
        logger.log("-> 授权链接: https://mock-composio.example.com/auth/adobe?session=" + session_id)
        logger.log("-> 异常码 E_AUTH：需负责人手动完成 OAuth，流程暂停。")
        return False
    logger.log("-> 连接状态: MOCK_ACTIVE（模拟，非真实 Adobe 连接）")
    logger.log("-> 声明：本模拟器不持有任何 Adobe 凭据，不发起真实认证。")
    return True


# ---------------------------------------------------------------------------
# Step 3: 模拟 RUBE_MULTI_EXECUTE_TOOL
# ---------------------------------------------------------------------------
def step3_execute(logger, session_id, now, inject):
    logger.section("Step 3: RUBE_MULTI_EXECUTE_TOOL（执行每周工作流）")
    logger.log(f"tools: [{MOCK_TOOLS['collect']} -> {MOCK_TOOLS['summary']} -> {MOCK_TOOLS['notify']}]")
    logger.log("memory: {}")
    logger.log(f"session_id: {session_id}")

    # --- 3a 收集数据 ---
    logger.log("")
    logger.log("[3a] 收集数据 ...")
    if inject == "exec_fail":
        return _simulate_retries(logger, "E_EXEC", "收集工具返回 500")

    if inject == "empty":
        records = []
        logger.log(f"-> {MOCK_TOOLS['collect']} 返回 0 条记录（空结果）")
    else:
        with open(MOCK_DATA, "r", encoding="utf-8") as f:
            records = json.load(f)
        logger.log(f"-> {MOCK_TOOLS['collect']} 返回 {len(records)} 条记录")

    # --- 3b 数据校验与摘要 ---
    logger.log("")
    logger.log("[3b] 数据校验与摘要生成 ...")
    anomalies = []
    clean = []
    for rec in records:
        ok, reason = _validate_record(rec)
        if not ok:
            anomalies.append(f"E_DATA: 记录 {rec.get('item_id', '?')} 已跳过，原因：{reason}")
            logger.log(f"   !! 跳过 {rec.get('item_id', '?')}: {reason}")
            continue
        clean.append(rec)

    if inject == "bad_data":
        # 额外注入一条坏数据以演示 E_DATA
        bad = {"item_id": "adobe:file:bad001", "item_name": None}
        ok, reason = _validate_record(bad)
        anomalies.append(f"E_DATA: 记录 {bad['item_id']} 已跳过，原因：{reason}")
        logger.log(f"   !! 跳过 {bad['item_id']}: {reason}")

    if not clean and records:
        # 所有记录都坏了
        logger.log("-> 异常码 E_EXEC：无有效记录可汇总，终止。")
        return 2

    summary = _build_summary(clean, now, anomalies)
    logger.log(f"-> 周次: {summary['report_week']}")
    logger.log(f"-> 总数: {summary['total_items']}  新增: {summary['new_items_this_week']}  "
               f"修改: {summary['modified_items_this_week']}")
    logger.log(f"-> 类型分布: {json.dumps(summary['items_by_type'], ensure_ascii=False)}")
    logger.log(f"-> 异常数: {len(anomalies)}")

    # 落盘摘要
    summary_path = os.path.join(OUTPUT_DIR, f"summary_{summary['report_week']}.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    logger.log(f"-> 摘要已写入: {os.path.relpath(summary_path, BASE_DIR)}")

    # --- 3c 通知 ---
    logger.log("")
    logger.log("[3c] 通知负责人 ...")
    if inject == "notify_fail":
        return _simulate_notify_failure(logger, summary)

    notify_path = _write_notification(summary)
    logger.log(f"-> 通知内容已写入: {os.path.relpath(notify_path, BASE_DIR)}")
    logger.log("-> （模拟模式不真实发送邮件/消息）")
    return 0


def _validate_record(rec):
    required = ["item_id", "item_name", "item_type", "size_bytes",
                "owner_email", "created_at", "modified_at", "status"]
    for field in required:
        if field not in rec or rec[field] is None:
            return False, f"缺少或为空字段 {field}"
    try:
        parse_iso(rec["created_at"])
        parse_iso(rec["modified_at"])
    except (ValueError, TypeError) as e:
        return False, f"时间格式无法解析 ({e})"
    if not isinstance(rec["size_bytes"], int) or rec["size_bytes"] < 0:
        return False, "size_bytes 非非负整数"
    return True, ""


def _build_summary(records, now, anomalies):
    monday, next_monday = week_range(now)
    new_count = 0
    modified_count = 0
    type_counter = Counter()
    owner_counter = Counter()
    total_size = 0
    archived = 0

    for rec in records:
        created = parse_iso(rec["created_at"])
        modified = parse_iso(rec["modified_at"])
        type_counter[rec["item_type"]] += 1
        owner_counter[rec["owner_email"]] += 1
        total_size += rec["size_bytes"]
        if rec["status"] == "archived":
            archived += 1
        if monday <= created < next_monday:
            new_count += 1
        elif monday <= modified < next_monday:
            modified_count += 1

    if archived:
        anomalies.append(f"其中 {archived} 项为 archived 状态，已计入总数。")

    top_owners = [
        {"owner_email": e, "count": c}
        for e, c in owner_counter.most_common(3)
    ]

    return {
        "report_week": iso_week_label(now),
        "generated_at": now.isoformat(),
        "week_start": monday.isoformat(),
        "week_end": next_monday.isoformat(),
        "total_items": len(records),
        "items_by_type": dict(type_counter),
        "new_items_this_week": new_count,
        "modified_items_this_week": modified_count,
        "total_size_bytes": total_size,
        "top_owners": top_owners,
        "anomalies": anomalies,
        "_note": "MOCK 摘要，由模拟器基于本地样例数据生成，非真实 Adobe 数据。",
    }


def _write_notification(summary):
    lines = [
        f"Adobe 每周数据摘要 {summary['report_week']}",
        f"生成时间：{summary['generated_at']}",
        "",
        f"本周资源总数：{summary['total_items']}",
        f"本周新增：{summary['new_items_this_week']}",
        f"本周修改：{summary['modified_items_this_week']}",
        f"总大小：{summary['total_size_bytes']} 字节",
        "",
        "类型分布：",
    ]
    for t, c in sorted(summary["items_by_type"].items()):
        lines.append(f"  - {t}: {c}")
    lines.append("")
    lines.append("贡献者 Top3：")
    for o in summary["top_owners"]:
        lines.append(f"  - {o['owner_email']}: {o['count']} 项")
    lines.append("")
    lines.append(f"异常：{len(summary['anomalies'])} 条")
    for a in summary["anomalies"]:
        lines.append(f"  - {a}")
    lines.append("")
    lines.append("（模拟模式：未真实发送，通知文件即交付凭证。）")

    path = os.path.join(OUTPUT_DIR, f"notification_{summary['report_week']}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return path


def _simulate_retries(logger, code, detail):
    for attempt in (1, 2, 3):
        logger.log(f"-> 尝试 {attempt}/3 失败：{detail}")
        if attempt < 3:
            logger.log("   退避等待 0.1 秒（真实环境为 5s/15s）...")
            time.sleep(0.1)
    logger.log(f"-> 异常码 {code}：重试 2 次后仍失败，流程终止。")
    logger.log("-> 已通知负责人（模拟）。")
    return 2


def _simulate_notify_failure(logger, summary):
    for attempt in (1, 2, 3):
        logger.log(f"-> 通知尝试 {attempt}/3 失败：模拟通知服务不可用")
        if attempt < 3:
            time.sleep(0.1)
    path = _write_notification(summary)
    logger.log(f"-> 异常码 E_NOTIFY：通知重试失败，已将通知内容落盘: {os.path.relpath(path, BASE_DIR)}")
    logger.log("-> 建议负责人检查通知渠道凭据。")
    return 2


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Adobe 周报流程安全模拟器")
    parser.add_argument("--inject", choices=["auth_fail", "empty", "bad_data",
                                             "exec_fail", "notify_fail"],
                        help="注入异常场景")
    parser.add_argument("--now", help="覆盖运行时刻，ISO8601，如 2026-08-12T09:00:00+08:00")
    args = parser.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    now = parse_iso(args.now) if args.now else datetime.now(TZ)

    log_path = os.path.join(OUTPUT_DIR, f"run_{now.strftime('%Y%m%d_%H%M%S')}.log")
    logger = Logger(log_path)

    logger.section("Adobe 每周数据收集 -> 摘要 -> 通知（安全模拟）")
    logger.log(f"运行时刻: {now.isoformat()}")
    logger.log(f"注入场景: {args.inject or '无（正常路径）'}")
    logger.log("声明: Rube MCP 未连接，Adobe 未授权；本运行仅为离线模拟，不触网。")

    # Step 0: 前置条件
    logger.section("Step 0: 前置条件检查")
    logger.log("P1 Rube MCP 可用 (RUBE_SEARCH_TOOLS): 不满足（当前环境无 RUBE_* 工具）")
    logger.log("P2 Adobe 连接 ACTIVE: 不满足（P1 未满足，无法检查）")
    logger.log("P3 Adobe API key 凭据: 不满足（无 Adobe 账号授权）")
    logger.log("-> 按 SKILL.md 要求，前置条件不满足时不得真实执行；进入安全模拟模式。")

    # Step 1
    session_id = step1_search_tools(logger)

    # Step 2
    connected = step2_check_connection(logger, session_id, args.inject)
    if not connected:
        logger.section("结果: 流程暂停（E_AUTH）")
        logger.log(f"日志文件: {os.path.relpath(log_path, BASE_DIR)}")
        logger.close()
        return 1

    # Step 3
    rc = step3_execute(logger, session_id, now, args.inject)

    logger.section("结果")
    if rc == 0:
        logger.log("状态: 成功（模拟）")
    else:
        logger.log(f"状态: 失败（异常退出码 {rc}）")
    logger.log(f"日志文件: {os.path.relpath(log_path, BASE_DIR)}")
    logger.close()
    return rc


if __name__ == "__main__":
    sys.exit(main())
