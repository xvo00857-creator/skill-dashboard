#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
affinda_workflow.py —— Affinda 文档解析自动化（受约束流程）

依据 affinda-automation Skill 的 SKILL.md 实现：
  - 预检：Rube MCP 工具可用性 / Affinda 连接状态 / 输入文件 / 状态目录 / 网络
  - 幂等：session_id 复用、已处理文件(SHA-256)去重、结果不静默覆盖
  - 重试：仅瞬时错误重试，指数退避；鉴权/schema 错误不重试
  - 人工确认点：连接授权、执行前确认、结果复核

重要：本脚本不直接调用 MCP 工具（RUBE_SEARCH_TOOLS 等需在 Agent 框架内调用）。
它负责本地预检、状态管理与干跑演示；真实 MCP 调用由 Agent 在预检通过后按 SKILL.md 执行。
"""

import argparse
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

# ============ 配置 ============
STATE_DIR = Path(".affinda_state")
SESSION_FILE = STATE_DIR / "session_id"
PROCESSED_LOG = STATE_DIR / "processed_files.tsv"
RESULT_DIR = Path("affinda_results")
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2  # 秒
MCP_ENDPOINT = "https://rube.app/mcp"
MCP_HOST = "rube.app"
# SKILL.md 要求的 MCP 工具（不硬编码 schema，仅用于存在性检查）
REQUIRED_MCP_TOOLS = [
    "RUBE_SEARCH_TOOLS",
    "RUBE_MANAGE_CONNECTIONS",
    "RUBE_MULTI_EXECUTE_TOOL",
]
AFFINDA_SUPPORTED_EXT = {".pdf", ".docx", ".doc", ".png", ".jpg", ".jpeg", ".tiff", ".txt"}

# ============ 日志工具 ============
def log(level, msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [{level}] {msg}", flush=True)

def ok(msg):   log("通过", msg)
def info(msg): log("信息", msg)
def warn(msg): log("警告", msg)
def fail(msg): log("失败", msg)

# ============ 幂等：状态管理 ============
def ensure_state_dir():
    STATE_DIR.mkdir(parents=True, exist_ok=True)

def get_or_create_session():
    ensure_state_dir()
    if SESSION_FILE.exists():
        sid = SESSION_FILE.read_text(encoding="utf-8").strip()
        if sid:
            return sid, False  # 复用
    sid = f"sess-{uuid.uuid4().hex[:12]}"
    SESSION_FILE.write_text(sid, encoding="utf-8")
    return sid, True  # 新建

def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def load_processed():
    """返回 {sha256: (path, timestamp)}"""
    processed = {}
    if PROCESSED_LOG.exists():
        for line in PROCESSED_LOG.read_text(encoding="utf-8").splitlines():
            parts = line.split("\t")
            if len(parts) >= 3:
                processed[parts[2]] = (parts[0], parts[1])
    return processed

def mark_processed(path: Path, sha: str):
    ensure_state_dir()
    with open(PROCESSED_LOG, "a", encoding="utf-8") as f:
        f.write(f"{path}\t{datetime.now().isoformat()}\t{sha}\n")

# ============ 人工确认点 ============
def human_confirm(prompt, default_no=True):
    suffix = " [y/N]: " if default_no else " [Y/n]: "
    try:
        ans = input(prompt + suffix).strip().lower()
    except EOFError:
        return False
    if not ans:
        return not default_no
    return ans in ("y", "yes")

# ============ 预检 ============
def check_mcp_tools_available():
    """P1: 检查 Rube MCP 工具是否在当前 Agent 工具集中可用。

    本脚本运行在 Agent 之外，无法直接枚举 Agent 工具；
    通过环境变量与 MCP 配置文件做间接判断，并给出明确结论。
    """
    info("P1 检查 Rube MCP 工具可用性...")

    # 检查环境变量线索
    env_hints = [k for k in os.environ if any(
        t in k.upper() for t in ("RUBE", "COMPOSIO", "MCP"))]
    if env_hints:
        warn(f"发现相关环境变量: {env_hints}（但不代表工具已注册）")

    # 检查常见 MCP 配置文件
    mcp_config_paths = [
        Path.home() / ".cursor" / "mcp.json",
        Path.home() / ".claude" / "mcp.json",
        Path.home() / ".config" / "mcp" / "config.json",
    ]
    found_config = False
    for p in mcp_config_paths:
        if p.exists():
            try:
                content = p.read_text(encoding="utf-8", errors="ignore")
                if "rube" in content.lower():
                    ok(f"在 {p} 中发现 rube 配置")
                    found_config = True
            except Exception:
                pass

    # 检查端点域名解析
    try:
        socket.gethostbyname(MCP_HOST)
        dns_ok = True
    except socket.gaierror:
        dns_ok = False

    if not dns_ok:
        fail(f"P1 未通过：{MCP_HOST} 无法解析，Rube MCP 端点不可达")
        return False, "DNS 解析失败"
    if not found_config:
        fail("P1 未通过：未找到包含 rube 的 MCP 客户端配置，"
             f"且当前脚本环境无法直接调用 {REQUIRED_MCP_TOOLS[0]}")
        return False, "MCP 工具/配置缺失"
    ok("P1 通过：Rube MCP 配置存在且端点可达（仍需在 Agent 内确认工具可调）")
    return True, None

def check_affinda_connection(dry_run):
    """P2: 检查 Affinda 连接是否 ACTIVE。

    真实环境需 Agent 调用 RUBE_MANAGE_CONNECTIONS(toolkits=['affinda'])。
    干跑模式下仅说明该步骤将做什么。
    """
    info("P2 检查 Affinda 连接状态...")
    if dry_run:
        warn("干跑模式：将调用 RUBE_MANAGE_CONNECTIONS(toolkits=['affinda'])，"
             "期望返回 status=ACTIVE；非 ACTIVE 时进入人工确认点 H1")
        return True, None  # 干跑不阻断
    fail("P2 无法执行：当前环境无 RUBE_MANAGE_CONNECTIONS 工具，"
         "需在 Agent 框架内由预检 P1 通过后调用")
    return False, "MCP 工具不可用"

def check_input_files(inputs):
    """P3: 检查待解析文件。"""
    info("P3 检查待解析文件...")
    if not inputs:
        fail("P3 未通过：未提供任何待解析文件")
        return False, "无输入文件", []

    valid, problems = [], []
    for raw in inputs:
        p = Path(raw)
        if not p.exists():
            problems.append(f"{raw}: 文件不存在")
            continue
        if p.stat().st_size == 0:
            problems.append(f"{raw}: 文件大小为 0")
            continue
        if p.suffix.lower() not in AFFINDA_SUPPORTED_EXT:
            problems.append(f"{raw}: 扩展名 {p.suffix} 不在支持列表")
            continue
        valid.append(p)

    for prob in problems:
        warn(prob)
    if not valid:
        fail("P3 未通过：没有可解析的有效文件")
        return False, "无有效文件", []
    ok(f"P3 通过：{len(valid)} 个有效文件待处理")
    return True, None, valid

def check_state_writable():
    """P4: 状态目录可写。"""
    info("P4 检查状态目录可写性...")
    try:
        ensure_state_dir()
        test_file = STATE_DIR / ".write_test"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink()
        ok("P4 通过：状态目录可写")
        return True
    except Exception as e:
        fail(f"P4 未通过：状态目录不可写 - {e}")
        return False

def check_network():
    """P5: 网络可达性诊断。"""
    info("P5 网络可达性诊断...")
    try:
        ip = socket.gethostbyname(MCP_HOST)
        ok(f"P5: {MCP_HOST} 解析到 {ip}")
        return True
    except socket.gaierror:
        fail(f"P5: {MCP_HOST} DNS 解析失败（端点不可达）")
        return False

# ============ 重试逻辑（演示） ============
def with_retry(func, desc, *args, **kwargs):
    """仅对瞬时错误重试；鉴权/schema 错误不重试。"""
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return func(*args, **kwargs)
        except RetryableError as e:
            last_err = e
            wait = RETRY_BACKOFF_BASE ** attempt
            warn(f"{desc} 第 {attempt} 次失败（可重试）: {e}；{wait}s 后重试")
            time.sleep(wait)
        except NonRetryableError as e:
            fail(f"{desc} 失败（不重试）: {e}")
            raise
    fail(f"{desc} 重试 {MAX_RETRIES} 次后仍失败: {last_err}")
    raise last_err

class RetryableError(Exception): pass
class NonRetryableError(Exception): pass

# ============ 主流程 ============
def main():
    parser = argparse.ArgumentParser(description="Affinda 文档解析自动化（受约束流程）")
    parser.add_argument("inputs", nargs="*", help="待解析文件路径")
    parser.add_argument("--dry-run", action="store_true", help="干跑：只预检与演示，不调用外部服务")
    parser.add_argument("--force", action="store_true", help="允许覆盖已存在的结果文件")
    parser.add_argument("--yes", action="store_true", help="跳过人工确认（仅限自动化场景）")
    args = parser.parse_args()

    info("=" * 60)
    info("Affinda 文档解析自动化流程启动")
    info(f"模式: {'干跑(dry-run)' if args.dry_run else '正式'}")
    info(f"工作目录: {Path.cwd()}")
    info("=" * 60)

    # 幂等：session
    session_id, created = get_or_create_session()
    if created:
        info(f"已创建新 session_id: {session_id}")
    else:
        info(f"复用已有 session_id: {session_id}（SKILL.md: 同工作流复用 session）")

    # ---- 预检 ----
    info("-" * 40 + " 预检阶段 " + "-" * 40)
    p4_ok = check_state_writable()
    p1_ok, p1_err = check_mcp_tools_available()
    p5_ok = check_network()
    p2_ok, p2_err = check_affinda_connection(args.dry_run)
    p3_ok, p3_err, valid_files = check_input_files(args.inputs)

    if not (p4_ok and p1_ok and p5_ok and p2_ok and p3_ok):
        fail("预检未全部通过，流程终止。")
        info("阻断项汇总：")
        if not p1_ok: info(f"  - P1 Rube MCP 工具: {p1_err}")
        if not p5_ok: info(f"  - P5 网络: {MCP_HOST} 不可达")
        if not p2_ok: info(f"  - P2 Affinda 连接: {p2_err}")
        if not p3_ok: info(f"  - P3 输入文件: {p3_err}")
        if not p4_ok: info("  - P4 状态目录不可写")
        info("修复建议：")
        info("  1. 在客户端添加 MCP server: " + MCP_ENDPOINT)
        info("  2. 完成 Affinda 授权连接（RUBE_MANAGE_CONNECTIONS 返回 ACTIVE）")
        info("  3. 提供待解析文档（PDF/图片等）")
        info("  4. 重新运行本脚本（同目录将复用 session_id，保证幂等）")
        # 干跑模式下预检失败不算脚本错误，用于演示
        if args.dry_run:
            warn("干跑模式：预检失败已如实记录，这是预期的可核实演示结果")
            write_demo_report(session_id, args, valid_files,
                              preflight_passed=False)
            return 0
        return 1

    # ---- 幂等：去重 ----
    info("-" * 40 + " 幂等去重 " + "-" * 40)
    processed = load_processed()
    todo = []
    for p in valid_files:
        sha = file_sha256(p)
        if sha in processed and not args.force:
            warn(f"跳过已处理文件: {p} (sha256={sha[:12]}...)")
            continue
        todo.append((p, sha))
    if not todo:
        ok("所有文件均已处理，幂等退出")
        return 0
    info(f"待处理: {len(todo)} 个文件")

    # ---- 人工确认点 H2：执行前确认 ----
    info("-" * 40 + " 人工确认 H2 " + "-" * 40)
    info("即将按 SKILL.md 执行：")
    info("  1. RUBE_SEARCH_TOOLS 发现 Affinda 解析工具（不硬编码 slug）")
    info("  2. RUBE_MULTI_EXECUTE_TOOL 提交解析（含 memory: {}）")
    info("  3. 循环拉取分页结果直到无分页令牌")
    if not args.yes:
        if not human_confirm("确认提交以上文件到 Affinda 解析？"):
            warn("用户取消，流程终止（未产生任何外部调用）")
            return 2

    # ---- 执行（干跑模式只演示结构，不伪造结果） ----
    info("-" * 40 + " 执行阶段 " + "-" * 40)
    if args.dry_run:
        warn("干跑模式：不调用 RUBE_MULTI_EXECUTE_TOOL，不产生解析结果")
        warn("（SKILL.md 禁止硬编码 schema；真实 tool_slug 与参数须由 "
             "RUBE_SEARCH_TOOLS 返回，干跑无法获取，故不模拟）")
        write_demo_report(session_id, args, valid_files,
                          preflight_passed=True, todo=todo)
        return 0

    # 正式执行路径：以下代码在 Rube MCP 可用时由 Agent 驱动
    # 本脚本不直接发起 MCP 调用（MCP 工具仅在 Agent 框架内可调）
    fail("正式执行需在 Agent 框架内调用 RUBE_* 工具；本脚本仅负责预检与状态管理")
    return 1

def write_demo_report(session_id, args, valid_files, preflight_passed, todo=None):
    """落盘一份可核实的演示报告（JSON）。"""
    report = {
        "report_time": datetime.now().isoformat(),
        "session_id": session_id,
        "mode": "dry-run",
        "preflight_passed": preflight_passed,
        "mcp_endpoint": MCP_ENDPOINT,
        "mcp_host_resolvable": _dns_resolvable(MCP_HOST),
        "required_mcp_tools": REQUIRED_MCP_TOOLS,
        "input_files": [str(p) for p in valid_files],
        "pending_after_dedup": len(todo) if todo else 0,
        "skill_rules_applied": [
            "Always call RUBE_SEARCH_TOOLS first (不硬编码 slug/schema)",
            "Verify RUBE_MANAGE_CONNECTIONS shows ACTIVE before executing",
            "RUBE_MULTI_EXECUTE_TOOL 必须包含 memory 参数(可为空对象)",
            "同工作流复用 session_id",
            "分页结果循环拉取直到无分页令牌",
        ],
        "note": "本报告为预检/干跑的真实输出；未调用 Affinda，未产生或伪造任何解析数据。",
    }
    out = STATE_DIR / "demo_report.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    ok(f"演示报告已落盘: {out}")

def _dns_resolvable(host):
    try:
        socket.gethostbyname(host)
        return True
    except socket.gaierror:
        return False

if __name__ == "__main__":
    sys.exit(main())
