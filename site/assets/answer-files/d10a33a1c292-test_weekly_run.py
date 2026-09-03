#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
weekly_run.py 的单元测试（仅 Python 3 标准库 unittest）。

运行：
  cd adyntel-weekly-automation
  python3 -m unittest test_weekly_run.py -v
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# 确保能导入同目录模块
sys.path.insert(0, str(Path(__file__).resolve().parent))

import weekly_run as wr


class TestFieldMapping(unittest.TestCase):
    """字段映射测试（对应 02-字段映射.md）。"""

    def test_normalize_full_record(self):
        raw = {"id": "X-1", "created_at": "2026-08-10T14:30:00Z", "type": "spend", "value": 42.5}
        r = wr.normalize_record(raw, 0)
        self.assertEqual(r["record_id"], "X-1")
        self.assertEqual(r["record_date"], "2026-08-10")
        self.assertEqual(r["category"], "spend")
        self.assertEqual(r["amount"], 42.5)
        self.assertEqual(r["raw"], raw)

    def test_normalize_missing_date(self):
        raw = {"id": "X-2", "type": "income", "value": 10}
        r = wr.normalize_record(raw, 1)
        self.assertIsNone(r["record_date"])
        self.assertEqual(r["record_id"], "X-2")

    def test_normalize_bad_amount(self):
        raw = {"id": "X-3", "created_at": "2026-08-10", "value": "N/A"}
        r = wr.normalize_record(raw, 2)
        self.assertIsNone(r["amount"])

    def test_normalize_generated_id(self):
        raw = {"created_at": "2026-08-10", "value": 1}
        r = wr.normalize_record(raw, 5)
        self.assertEqual(r["record_id"], "rec_5")
        self.assertEqual(r["category"], "unknown")

    def test_summary_aggregation(self):
        records = [
            wr.normalize_record({"id": "1", "created_at": "2026-08-10", "type": "a", "value": 10}, 0),
            wr.normalize_record({"id": "2", "created_at": "2026-08-11", "type": "a", "value": 20}, 1),
            wr.normalize_record({"id": "3", "type": "b", "value": "bad"}, 2),
        ]
        s = wr.build_summary(records, "2026-08-10", "2026-08-16")
        self.assertEqual(s["total_records"], 3)
        self.assertEqual(s["date_missing_count"], 1)
        self.assertEqual(s["categories"], {"a": 2, "b": 1})
        self.assertEqual(s["amount_sum"], 30.0)
        self.assertEqual(s["amount_avg"], 15.0)
        self.assertFalse(s["empty_week"])

    def test_summary_empty_week(self):
        s = wr.build_summary([], "2026-08-10", "2026-08-16")
        self.assertTrue(s["empty_week"])
        self.assertEqual(s["total_records"], 0)
        self.assertIsNone(s["amount_sum"])


class TestWeekRange(unittest.TestCase):
    def test_week_range_monday(self):
        ws, we = wr.week_range("2026-08-10")  # 周一
        self.assertEqual(ws, "2026-08-10")
        self.assertEqual(we, "2026-08-16")

    def test_week_range_sunday(self):
        ws, we = wr.week_range("2026-08-16")  # 周日
        self.assertEqual(ws, "2026-08-10")
        self.assertEqual(we, "2026-08-16")


class TestSimulatedRun(unittest.TestCase):
    """模拟模式端到端流程测试。"""

    def test_full_run_success(self):
        runner = wr.Runner(mode="simulate", week_day="2026-08-10")
        report = runner.run()
        self.assertEqual(report["final_status"], "success")
        stage_names = [s["name"] for s in report["stages"]]
        self.assertEqual(stage_names, ["discover", "connect", "collect", "summarize", "notify"])
        for s in report["stages"]:
            self.assertEqual(s["status"], "ok", msg=s.get("error"))
        # 分页：桩数据分两页
        self.assertEqual(report["summary"]["_pages_fetched"], 2)
        self.assertEqual(report["summary"]["total_records"], 5)
        # 通知已发送
        self.assertTrue(report["notify_result"]["sent"])
        # 报告文件已落盘
        self.assertTrue(Path(report["_report_path"]).exists())
        with open(report["_report_path"], "r", encoding="utf-8") as f:
            on_disk = json.load(f)
        self.assertEqual(on_disk["run_id"], report["run_id"])

    def test_run_pending_auth_e2(self):
        runner = wr.Runner(mode="simulate", week_day="2026-08-10", force_auth=True)
        report = runner.run()
        self.assertEqual(report["final_status"], "awaiting_auth")
        # 流程应停在 connect，不继续 collect
        stage_names = [s["name"] for s in report["stages"]]
        self.assertNotIn("collect", stage_names)
        self.assertTrue(any("E2" in ex["message"] for ex in report["exceptions"]))

    def test_memory_param_required(self):
        """SKILL.md：memory 必须传，即使为空 dict。"""
        with self.assertRaises(AssertionError):
            wr._stub_multi_execute(
                tools=[{"tool_slug": "adyntel_list_records", "arguments": {}}],
                memory=None,  # 故意传 None
                session_id="sess-test",
            )

    def test_live_mode_mcp_unavailable(self):
        """live 模式在无 Rube MCP 环境下应明确失败，不假装成功。"""
        runner = wr.Runner(mode="live", week_day="2026-08-10")
        report = runner.run()
        self.assertEqual(report["final_status"], "failed")
        self.assertTrue(any("Rube MCP" in ex["message"] for ex in report["exceptions"]))


class TestIdempotencyAndOutbox(unittest.TestCase):
    def test_summary_text_contains_key_info(self):
        s = wr.build_summary(
            [wr.normalize_record({"id": "1", "created_at": "2026-08-10", "type": "x", "value": 5}, 0)],
            "2026-08-10", "2026-08-16",
        )
        text = wr.summary_text(s)
        self.assertIn("Adyntel 周报", text)
        self.assertIn("2026-08-10", text)
        self.assertIn("1 条记录", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
