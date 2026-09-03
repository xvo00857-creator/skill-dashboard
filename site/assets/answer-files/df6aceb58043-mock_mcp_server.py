#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地 mock MCP server，用于验证 weekly_report.py 的 live 模式逻辑。
仅用于本地验证，不连接任何外部服务。

模拟两种场景：
  --scenario full   暴露文档/表格/IM 三类工具（验证 dry-run 计划输出）
  --scenario partial 只暴露文档工具（验证工具缺失错误提示）

通信方式：JSON-RPC 2.0 over stdio（MCP 标准）
"""

import argparse
import json
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", choices=["full", "partial"], default="full")
    args = parser.parse_args()

    if args.scenario == "full":
        tools = [
            {"name": "feishu_docx_create", "description": "Create a new Feishu/Lark document (docx)"},
            {"name": "feishu_bitable_records_search", "description": "Search records in a Feishu bitable spreadsheet"},
            {"name": "feishu_im_message_create", "description": "Send a message to a Feishu/Lark chat"},
        ]
    else:
        tools = [
            {"name": "feishu_docx_create", "description": "Create a new Feishu/Lark document (docx)"},
        ]

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue

        method = req.get("method")
        req_id = req.get("id")

        if method == "initialize":
            resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": "mock-feishu-tools", "version": "0.0.1"},
                    "capabilities": {"tools": {}},
                },
            }
        elif method == "notifications/initialized":
            continue  # 通知无需响应
        elif method == "tools/list":
            resp = {"jsonrpc": "2.0", "id": req_id, "result": {"tools": tools}}
        elif method == "tools/call":
            # mock 返回：表格查询返回任务列表，其他返回成功
            params = req.get("params", {})
            tool_name = params.get("name", "")
            if "bitable" in tool_name or "records" in tool_name:
                mock_records = [
                    {"title": "Mock任务A", "owner": "测试员", "status": "已完成", "due_date": "2026-08-12"},
                    {"title": "Mock任务B", "owner": "测试员", "status": "进行中", "due_date": "2026-08-14"},
                ]
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"content": [{"type": "text", "text": json.dumps(mock_records, ensure_ascii=False)}]},
                }
            elif "docx" in tool_name or "doc" in tool_name:
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"content": [{"type": "text", "text": json.dumps({"url": "https://example.feishu.cn/docx/mock123"}, ensure_ascii=False)}]},
                }
            else:
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"content": [{"type": "text", "text": "ok"}]},
                }
        else:
            resp = {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Method not found: {method}"}}

        sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
