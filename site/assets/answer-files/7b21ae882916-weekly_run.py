#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Adyntel 每周数据收集与通知自动化 —— 编排脚本（仅 Python 3 标准库）

依据 adyntel-automation/SKILL.md 的三步模式：
  RUBE_SEARCH_TOOLS -> RUBE_MANAGE_CONNECTIONS -> RUBE_MULTI_EXECUTE_TOOL

用法：
  python3 weekly_run.py --mode simulate          # 本地模拟（默认，不连真实 MCP）
  python3 weekly_run.py --mode live              # 真实运行（需 Rube MCP 可用且已授权）
  python3 weekly_run.py --mode simulate --week 2026-08-10   # 指定本周任意一天

真实模式说明：
  当前运行环境若未接入 Rube MCP，live 模式会在阶段 1 失败并报 E10。
  本脚本不硬编码任何真实工具 slug 或参数；live 模式下全部从 search 结果动态获取。
"""

import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime, timedelta, date
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
LOGS_DIR = BASE_DIR / "logs"
OUTBOX_DIR = BASE_DIR / "outbox"
CONFIG_PATH = BASE_DIR / "config.json"


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def now_iso():
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def week_range(any_day=None):
    """返回本周一 00:00 到本周日 23:59 的日期字符串。"""
    if any_day is None:
        any_day = date.today()
    elif isinstance(any_day, str):
        any_day = datetime.strptime(any_day, "%Y-%m-%d").date()
    monday = any_day - timedelta(days=any_day.weekday())
    sunday = monday + timedelta(days=6)
    return monday.strftime("%Y-%m-%d"), sunday.strftime("%Y-%m-%d")


def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    # 默认配置（模拟用）
    return {"owner_contact": "owner@example.com", "simulate_records": 5}


# ---------------------------------------------------------------------------
# 模拟桩：Rube MCP 三件套（仅 simulate 模式使用）
# 这些桩的返回结构遵循 SKILL.md 描述的契约，但具体 slug/字段为桩数据，
# 不代表 Adyntel 真实工具。
# ---------------------------------------------------------------------------

def _stub_search_tools(use_case, session_id):
    """模拟 RUBE_SEARCH_TOOLS：返回工具 slug、input schema、推荐计划。"""
    return {
        "session_id": session_id,
        "tools": [
            {
                "tool_slug": "adyntel_list_records",
                "role": "data_collection",
                "description": "List Adyntel records within a date range (stub).",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "start_date": {"type": "string", "format": "date", "required": True},
                        "end_date": {"type": "string", "format": "date", "required": True},
                        "page_token": {"type": "string", "required": False},
                    },
                },
            },
            {
                "tool_slug": "adyntel_send_message",
                "role": "notification",
                "description": "Send a message to a recipient (stub).",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "recipient": {"type": "string", "required": True},
                        "message": {"type": "string", "required": True},
                    },
                },
            },
        ],
        "recommended_plan": ["discover", "connect", "collect", "notify"],
        "known_pitfalls": ["pagination", "schema_changes"],
    }


def _stub_manage_connections(toolkits, session_id, force_auth=False):
    """模拟 RUBE_MANAGE_CONNECTIONS。force_auth=True 时返回非 ACTIVE 以测试 E2。"""
    if force_auth:
        return {
            "session_id": session_id,
            "connections": [
                {
                    "toolkit": "adyntel",
                    "status": "PENDING_AUTH",
                    "auth_url": "https://example.com/auth/adyntel?session=" + session_id,
                }
            ],
        }
    return {
        "session_id": session_id,
        "connections": [{"toolkit": "adyntel", "status": "ACTIVE"}],
    }


def _stub_multi_execute(tools, memory, session_id):
    """模拟 RUBE_MULTI_EXECUTE_TOOL。根据 tool_slug 返回桩数据。"""
    assert isinstance(memory, dict), "memory must be a dict (SKILL.md pitfall)"
    results = []
    cfg = load_config()
    for t in tools:
        slug = t["tool_slug"]
        args = t["arguments"]
        if slug == "adyntel_list_records":
            # 分两页返回，验证分页逻辑
            page_token = args.get("page_token")
            n = cfg.get("simulate_records", 5)
            if page_token is None:
                half = (n + 1) // 2
                items = [
                    {
                        "id": "A-%04d" % (1000 + i),
                        "created_at": "2026-08-%02dT10:00:00Z" % (10 + i),
                        "type": "spend" if i % 2 == 0 else "income",
                        "value": round(10.5 + i * 3.25, 2),
                    }
                    for i in range(half)
                ]
                results.append({"tool_slug": slug, "data": {"items": items, "next_page_token": "page-2"}})
            else:
                half = (n + 1) // 2
                items = [
                    {
                        "id": "A-%04d" % (1000 + half + i),
                        "created_at": "2026-08-%02dT10:00:00Z" % (10 + half + i),
                        "type": "spend" if (half + i) % 2 == 0 else "income",
                        "value": round(10.5 + (half + i) * 3.25, 2),
                    }
                    for i in range(n - half)
                ]
                # 故意让最后一条缺日期，测试 E9
                if items:
                    items[-1] = dict(items[-1])
                    del items[-1]["created_at"]
                results.append({"tool_slug": slug, "data": {"items": items, "next_page_token": None}})
        elif slug == "adyntel_send_message":
            results.append(
                {"tool_slug": slug, "data": {"sent": True, "to": args.get("recipient"), "at": now_iso()}}
            )
        else:
            raise ValueError("Unknown tool slug (stub): %s" % slug)
    return {"session_id": session_id, "results": results}


# ---------------------------------------------------------------------------
# 真实模式占位：live 模式需要运行环境中存在 Rube MCP 工具。
# 本脚本不直接发起网络请求，而是通过约定的适配层调用；
# 若环境未提供适配层，则明确报错（不假装成功）。
# ---------------------------------------------------------------------------

class LiveMCPUnavailable(RuntimeError):
    pass


def _live_search_tools(use_case, session_id):
    raise LiveMCPUnavailable(
        "Rube MCP 不可用：当前环境未提供 RUBE_SEARCH_TOOLS。"
        "请按 SKILL.md 添加 https://rube.app/mcp 为 MCP server 后重试。"
    )


def _live_manage_connections(toolkits, session_id):
    raise LiveMCPUnavailable("Rube MCP 不可用：RUBE_MANAGE_CONNECTIONS 未提供。")


def _live_multi_execute(tools, memory, session_id):
    raise LiveMCPUnavailable("Rube MCP 不可用：RUBE_MULTI_EXECUTE_TOOL 未提供。")


# ---------------------------------------------------------------------------
# 字段映射（对应 02-字段映射.md）
# ---------------------------------------------------------------------------

DATE_KEYS = ("date", "created_at", "time", "updated_at")
ID_KEYS = ("id", "uid", "uuid", "key")
CATEGORY_KEYS = ("type", "category", "status", "kind")
AMOUNT_KEYS = ("amount", "value", "count", "total", "sum")


def _pick(record, keys):
    """在原始记录中按候选键名找值（大小写不敏感）。"""
    lower_map = {k.lower(): k for k in record.keys()}
    for cand in keys:
        if cand.lower() in lower_map:
            return record[lower_map[cand.lower()]]
    return None


def normalize_record(raw, index):
    """raw -> normalized_record。"""
    rec_id = _pick(raw, ID_KEYS)
    raw_date = _pick(raw, DATE_KEYS)
    record_date = None
    if raw_date:
        try:
            # 兼容 ISO8601 与纯日期
            record_date = raw_date[:10]
            datetime.strptime(record_date, "%Y-%m-%d")
        except (ValueError, TypeError):
            record_date = None
    amount = _pick(raw, AMOUNT_KEYS)
    if amount is not None:
        try:
            amount = float(amount)
        except (ValueError, TypeError):
            amount = None
    category = _pick(raw, CATEGORY_KEYS)
    return {
        "record_id": str(rec_id) if rec_id is not None else "rec_%d" % index,
        "record_date": record_date,
        "category": str(category) if category is not None else "unknown",
        "amount": amount,
        "raw": raw,
    }


def build_summary(normalized, week_start, week_end):
    """normalized -> summary 对象。"""
    total = len(normalized)
    date_missing = sum(1 for r in normalized if r["record_date"] is None)
    categories = {}
    amounts = []
    for r in normalized:
        categories[r["category"]] = categories.get(r["category"], 0) + 1
        if r["amount"] is not None:
            amounts.append(r["amount"])
    return {
        "week_start": week_start,
        "week_end": week_end,
        "total_records": total,
        "date_missing_count": date_missing,
        "categories": categories,
        "amount_sum": round(sum(amounts), 2) if amounts else None,
        "amount_avg": round(sum(amounts) / len(amounts), 2) if amounts else None,
        "empty_week": total == 0,
        "generated_at": now_iso(),
    }


def summary_text(s):
    lines = ["【Adyntel 周报】%s ~ %s" % (s["week_start"], s["week_end"])]
    if s["empty_week"]:
        lines.append("本周无数据。")
    else:
        lines.append("本周共 %d 条记录。" % s["total_records"])
        lines.append("分类分布：%s" % ", ".join("%s=%d" % (k, v) for k, v in sorted(s["categories"].items())))
        if s["amount_sum"] is not None:
            lines.append("金额合计：%s，均值：%s" % (s["amount_sum"], s["amount_avg"]))
        else:
            lines.append("金额合计：无有效数值")
    if s["date_missing_count"] > 0:
        lines.append("注意：%d 条记录日期缺失。" % s["date_missing_count"])
    lines.append("生成时间：%s" % s["generated_at"])
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 流程编排
# ---------------------------------------------------------------------------

class Runner:
    def __init__(self, mode="simulate", week_day=None, force_auth=False):
        self.mode = mode
        self.week_day = week_day
        self.force_auth = force_auth  # 测试 E2 用
        self.session_id = "sess-" + uuid.uuid4().hex[:12]
        self.run_id = "run-" + datetime.now().strftime("%Y%m%d%H%M%S")
        self.stages = []
        self.exceptions = []
        self.discovered = None
        self.summary = None
        self.final_status = "success"
        self.backoffs = [5, 15, 45]

        if mode == "simulate":
            self.search_tools = _stub_search_tools
            self.manage_connections = lambda t, s: _stub_manage_connections(t, s, force_auth=self.force_auth)
            self.multi_execute = _stub_multi_execute
        else:
            self.search_tools = _live_search_tools
            self.manage_connections = _live_manage_connections
            self.multi_execute = _live_multi_execute

    def _stage(self, name, func):
        t0 = time.time()
        entry = {"name": name, "status": "ok", "duration_ms": 0, "error": None}
        try:
            result = func()
            entry["status"] = "ok"
            return result
        except Exception as e:
            entry["status"] = "error"
            entry["error"] = str(e)
            self.exceptions.append({"stage": name, "message": str(e)})
            self.final_status = "failed"
            raise
        finally:
            entry["duration_ms"] = int((time.time() - t0) * 1000)
            self.stages.append(entry)

    # --- 阶段 1 ---
    def stage_discover(self):
        res = self.search_tools(
            use_case="每周收集 Adyntel 数据并生成摘要通知负责人",
            session_id=self.session_id,
        )
        tools = res.get("tools", [])
        self.data_tool = next((t for t in tools if t.get("role") == "data_collection"), None)
        self.notify_tool = next((t for t in tools if t.get("role") == "notification"), None)
        if not self.data_tool or not self.notify_tool:
            raise RuntimeError("E1: 工具发现结果缺少数据收集或通知工具: %s" % [t.get("tool_slug") for t in tools])
        self.discovered = res
        return res

    # --- 阶段 2 ---
    def stage_connect(self):
        res = self.manage_connections(["adyntel"], self.session_id)
        conns = {c["toolkit"]: c for c in res.get("connections", [])}
        conn = conns.get("adyntel")
        if not conn or conn.get("status") != "ACTIVE":
            auth_url = (conn or {}).get("auth_url", "(未返回授权链接)")
            self.final_status = "awaiting_auth"
            raise RuntimeError("E2: Adyntel 连接未就绪，需人工授权: %s" % auth_url)
        return res

    # --- 阶段 3 ---
    def stage_collect(self):
        ws, we = week_range(self.week_day)
        schema_props = self.data_tool["input_schema"]["properties"]
        # 动态构建参数：键名来自 schema，值按语义填充
        args = {}
        for field_name, field_def in schema_props.items():
            fl = field_name.lower()
            if "start" in fl:
                args[field_name] = ws
            elif "end" in fl:
                args[field_name] = we
            elif "page" in fl or "token" in fl:
                continue  # 分页字段在循环中填
            elif field_def.get("required"):
                args[field_name] = None  # 占位，实际按 schema 填
        all_items = []
        page_token = None
        pages = 0
        while True:
            page_args = dict(args)
            # 找到分页字段名
            page_field = next((n for n in schema_props if "token" in n.lower() or "page" in n.lower()), None)
            if page_field and page_token is not None:
                page_args[page_field] = page_token
            resp = self.multi_execute(
                tools=[{"tool_slug": self.data_tool["tool_slug"], "arguments": page_args}],
                memory={},
                session_id=self.session_id,
            )
            data = resp["results"][0]["data"]
            items = data.get("items", data.get("records", []))
            all_items.extend(items)
            pages += 1
            page_token = data.get("next_page_token") or data.get("pagination_token")
            if not page_token:
                break
        self._raw_count = len(all_items)
        self._pages = pages
        return all_items

    # --- 阶段 4 ---
    def stage_summarize(self, raw_records):
        normalized = [normalize_record(r, i) for i, r in enumerate(raw_records)]
        ws, we = week_range(self.week_day)
        self.summary = build_summary(normalized, ws, we)
        self.summary["_pages_fetched"] = getattr(self, "_pages", 1)
        self.summary["_raw_count"] = getattr(self, "_raw_count", len(raw_records))
        return self.summary

    # --- 阶段 5 ---
    def stage_notify(self):
        cfg = load_config()
        text = summary_text(self.summary)
        schema_props = self.notify_tool["input_schema"]["properties"]
        args = {}
        for field_name in schema_props:
            fl = field_name.lower()
            if any(k in fl for k in ("recipient", "to", "receiver", "contact")):
                args[field_name] = cfg["owner_contact"]
            elif any(k in fl for k in ("message", "content", "body", "text")):
                args[field_name] = text
        resp = self.multi_execute(
            tools=[{"tool_slug": self.notify_tool["tool_slug"], "arguments": args}],
            memory={},
            session_id=self.session_id,
        )
        return resp["results"][0]["data"]

    # --- 阶段 6 ---
    def stage_finalize(self, notify_result):
        report = {
            "run_id": self.run_id,
            "session_id": self.session_id,
            "mode": self.mode,
            "started_at": self._started,
            "finished_at": now_iso(),
            "stages": self.stages,
            "exceptions": self.exceptions,
            "summary": self.summary,
            "notify_result": notify_result,
            "final_status": self.final_status,
        }
        LOGS_DIR.mkdir(exist_ok=True)
        report_path = LOGS_DIR / ("%s.json" % self.run_id)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        report["_report_path"] = str(report_path)
        return report

    def run(self):
        self._started = now_iso()
        raw_records = None
        notify_result = None
        try:
            self._stage("discover", self.stage_discover)
            self._stage("connect", self.stage_connect)
            raw_records = self._stage("collect", self.stage_collect)
            self._stage("summarize", lambda: self.stage_summarize(raw_records))
            notify_result = self._stage("notify", self.stage_notify)
        except RuntimeError as e:
            msg = str(e)
            if msg.startswith("E2:"):
                # E2：暂停在授权前，不继续
                self.final_status = "awaiting_auth"
            elif msg.startswith("E1:"):
                self.final_status = "failed"
            else:
                self.final_status = "failed"
        except LiveMCPUnavailable as e:
            self.final_status = "failed"
            if not any(ex["message"] == str(e) for ex in self.exceptions):
                self.exceptions.append({"stage": "mcp", "message": str(e)})
        finally:
            report = self.stage_finalize(notify_result)
        return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Adyntel 每周自动化编排")
    parser.add_argument("--mode", choices=["simulate", "live"], default="simulate")
    parser.add_argument("--week", help="本周任意一天 YYYY-MM-DD，用于计算周范围", default=None)
    parser.add_argument("--force-auth", action="store_true", help="模拟 E2：连接返回待授权")
    args = parser.parse_args()

    runner = Runner(mode=args.mode, week_day=args.week, force_auth=args.force_auth)
    report = runner.run()

    print("=" * 60)
    print("运行 ID: %s" % report["run_id"])
    print("模式: %s | session: %s" % (report["mode"], report["session_id"]))
    print("最终状态: %s" % report["final_status"])
    print("-" * 60)
    for s in report["stages"]:
        mark = "OK" if s["status"] == "ok" else "ERR"
        line = "  [%s] %s (%dms)" % (mark, s["name"], s["duration_ms"])
        if s["error"]:
            line += " -> %s" % s["error"]
        print(line)
    if report.get("summary"):
        print("-" * 60)
        print(summary_text(report["summary"]))
    if report.get("notify_result"):
        print("-" * 60)
        print("通知结果: %s" % json.dumps(report["notify_result"], ensure_ascii=False))
    print("-" * 60)
    print("报告文件: %s" % report["_report_path"])
    print("=" * 60)

    return 0 if report["final_status"] in ("success", "awaiting_auth") else 1


if __name__ == "__main__":
    sys.exit(main())
