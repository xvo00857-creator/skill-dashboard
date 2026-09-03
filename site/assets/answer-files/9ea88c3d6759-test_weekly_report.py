#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
weekly_report.py 的自动化验证测试。
仅使用 Python 标准库 unittest，运行：python3 test_weekly_report.py
"""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime

# 确保能导入同目录的 weekly_report
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from weekly_report import (
    DataValidationError,
    MCPToolNotFoundError,
    _normalize_status,
    filter_this_week,
    find_tool,
    render_markdown,
    run_mock,
    summarize,
    validate_tasks,
    main,
)


class TestStatusNormalization(unittest.TestCase):
    """测试状态归一化"""

    def test_done_variants(self):
        self.assertEqual(_normalize_status("已完成"), "已完成")
        self.assertEqual(_normalize_status("done"), "已完成")
        self.assertEqual(_normalize_status("Closed"), "已完成")
        self.assertEqual(_normalize_status("已上线"), "已完成")

    def test_doing_variants(self):
        self.assertEqual(_normalize_status("进行中"), "进行中")
        self.assertEqual(_normalize_status("Doing"), "进行中")
        self.assertEqual(_normalize_status("开发中"), "进行中")

    def test_blocked_variants(self):
        self.assertEqual(_normalize_status("阻塞"), "阻塞")
        self.assertEqual(_normalize_status("Blocked"), "阻塞")

    def test_todo_variants(self):
        self.assertEqual(_normalize_status("待开始"), "待开始")
        self.assertEqual(_normalize_status("TODO"), "待开始")
        self.assertEqual(_normalize_status("Open"), "待开始")

    def test_empty_and_unknown(self):
        self.assertEqual(_normalize_status(""), "其他")
        self.assertEqual(_normalize_status(None), "其他")
        self.assertEqual(_normalize_status("未知状态"), "其他")


class TestValidation(unittest.TestCase):
    """测试数据校验"""

    def test_valid_tasks(self):
        tasks = validate_tasks([
            {"title": "任务A", "owner": "张三", "status": "进行中"},
            {"title": "任务B", "owner": "李四", "status": "done"},
        ])
        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[0]["status"], "进行中")
        self.assertEqual(tasks[1]["status"], "已完成")

    def test_not_a_list(self):
        with self.assertRaises(DataValidationError):
            validate_tasks({"not": "a list"})

    def test_missing_required_field(self):
        with self.assertRaises(DataValidationError):
            validate_tasks([{"title": "缺负责人"}])
        with self.assertRaises(DataValidationError):
            validate_tasks([{"owner": "缺标题"}])

    def test_non_dict_item(self):
        with self.assertRaises(DataValidationError):
            validate_tasks(["not a dict"])


class TestWeekFilter(unittest.TestCase):
    """测试本周筛选"""

    def _make_task(self, due_date, status="已完成"):
        return {
            "title": "t",
            "owner": "o",
            "status_raw": status,
            "status": _normalize_status(status),
            "due_date": due_date,
            "priority": "",
            "url": "",
        }

    def test_filters_this_week_by_due_date(self):
        # 2026-08-12 是周三，本周为 08-10 ~ 08-16
        fixed = datetime(2026, 8, 12)
        tasks = [
            self._make_task("2026-08-11"),  # 本周
            self._make_task("2026-08-16"),  # 本周日
            self._make_task("2026-07-20"),  # 过期
            self._make_task("2026-08-20"),  # 下周
        ]
        result = filter_this_week(tasks, today=fixed)
        self.assertEqual(len(result), 2)

    def test_no_due_date_but_active(self):
        fixed = datetime(2026, 8, 12)
        tasks = [
            self._make_task("", "进行中"),
            self._make_task("", "阻塞"),
            self._make_task("", "已完成"),  # 无日期且已完成，不纳入
        ]
        result = filter_this_week(tasks, today=fixed)
        self.assertEqual(len(result), 2)


class TestSummarize(unittest.TestCase):
    """测试汇总逻辑"""

    def test_summary_counts(self):
        tasks = validate_tasks([
            {"title": "A", "owner": "张三", "status": "已完成"},
            {"title": "B", "owner": "张三", "status": "进行中"},
            {"title": "C", "owner": "李四", "status": "阻塞"},
            {"title": "D", "owner": "李四", "status": "阻塞"},
        ])
        s = summarize(tasks)
        self.assertEqual(s["total"], 4)
        self.assertEqual(s["done"], 1)
        self.assertEqual(s["doing"], 1)
        self.assertEqual(s["blocked"], 2)
        self.assertEqual(len(s["by_owner"]["张三"]["已完成"]), 1)
        self.assertEqual(len(s["by_owner"]["李四"]["阻塞"]), 2)


class TestRenderMarkdown(unittest.TestCase):
    """测试 Markdown 渲染"""

    def test_render_contains_key_sections(self):
        tasks = validate_tasks([
            {"title": "任务A", "owner": "张三", "status": "已完成", "priority": "高", "url": "http://x"},
            {"title": "任务B", "owner": "李四", "status": "阻塞", "priority": "", "url": ""},
        ])
        s = summarize(tasks)
        md = render_markdown(s, "2026-08-10 ~ 2026-08-16")
        self.assertIn("团队周报", md)
        self.assertIn("张三", md)
        self.assertIn("李四", md)
        self.assertIn("任务A", md)
        self.assertIn("任务B", md)
        self.assertIn("阻塞", md)
        self.assertIn("http://x", md)
        self.assertIn("存在阻塞任务", md)


class TestToolMatching(unittest.TestCase):
    """测试工具匹配逻辑（不假设具体工具名）"""

    def test_match_by_keywords(self):
        tools = [
            {"name": "some_doc_tool", "description": "Create and edit Feishu documents"},
            {"name": "sheet_reader", "description": "Read Feishu spreadsheets and bitable"},
            {"name": "im_sender", "description": "Send Feishu IM messages"},
            {"name": "unrelated", "description": "Calendar operations"},
        ]
        self.assertIsNotNone(find_tool(tools, "document"))
        self.assertIsNotNone(find_tool(tools, "sheet"))
        self.assertIsNotNone(find_tool(tools, "im"))
        # email 不在预定义域中，且工具列表无 email 关键词
        self.assertIsNone(find_tool(tools, "email"))

    def test_no_tools_returns_none(self):
        self.assertIsNone(find_tool([], "document"))


class TestMockEndToEnd(unittest.TestCase):
    """mock 模式端到端测试"""

    def test_mock_generates_report(self):
        config = {"mock_data_file": "mock_data/tasks.json"}
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "report.md")
            md = run_mock(config, out)
            self.assertTrue(os.path.isfile(out))
            with open(out, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertEqual(content, md)
            self.assertIn("团队周报", content)
            # mock 数据中 2026-07-20 的过期任务应被过滤
            self.assertNotIn("数据迁移验证" if False else "上月复盘", content)


class TestCLIExitCodes(unittest.TestCase):
    """测试 CLI 异常退出码"""

    def test_missing_config(self):
        rc = main(["--config", "/nonexistent/config.json", "--mode", "mock"])
        self.assertEqual(rc, 2)

    def test_live_missing_server_command(self):
        # 写一个没有 mcp.server_command 的配置
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump({"mcp": {}}, f)
            f.flush()
            rc = main(["--config", f.name, "--mode", "live"])
        self.assertEqual(rc, 2)
        os.unlink(f.name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
