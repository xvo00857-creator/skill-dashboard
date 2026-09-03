#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Confluence 受约束操作工作流（干跑演示版）
依据 Skill: confluence-assistant SKILL.md v1.0.0 (CC-BY-4.0, author: Waldemar Neto)

本脚本实现四道约束：预检(P)、幂等(I)、重试(R)、人工确认(C)。
当环境中没有 Atlassian MCP 工具时，自动进入干跑模式，
使用明确标注的【示例数据】演示完整流程，不接触任何外部 Confluence 资源。

真实执行前提（缺一不可）：
  1. 环境已接入 Atlassian MCP Server，提供 search/getConfluencePage/
     createConfluencePage/updateConfluencePage/getConfluenceSpaces 等工具；
  2. 已配置 Cloud ID（UUID）或站点 URL；
  3. 身份认证通过；
  4. 写入操作经人工确认。
"""

import sys
import re
import json
import time
import difflib
from datetime import datetime, timezone

# ============================================================
# 全局配置
# ============================================================
MAX_RETRIES = 3
RETRY_BACKOFF = [1, 2, 4]  # 秒

# 干跑标志：预检后自动判定。True = 不调用任何外部工具，仅模拟。
DRY_RUN = None
CLOUD_ID = None  # 真实环境需由用户提供或从上下文获取

# ------------------------------------------------------------
# 【示例数据】仅用于干跑演示，非真实 Confluence 数据
# ------------------------------------------------------------
MOCK_SPACES = {
    "TECH": {"id": "10001", "key": "TECH", "name": "技术文档空间", "type": "global"},
    "DS":   {"id": "10002", "key": "DS",   "name": "设计空间",     "type": "global"},
}
MOCK_PAGES = {
    "20001": {
        "id": "20001", "spaceKey": "TECH",
        "title": "API 文档",
        "version": 3,
        "body": "# API 文档\n\n## 认证\n使用 Bearer Token。\n\n## 端点\n- GET /v1/users\n",
        "status": "current",
    },
    "20002": {
        "id": "20002", "spaceKey": "TECH",
        "title": "新员工入职指南",
        "version": 1,
        "body": "# 新员工入职指南\n\n第一天完成账号申请。\n",
        "status": "current",
    },
}

# ============================================================
# 日志工具
# ============================================================
def log(level, msg):
    ts = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [{level}] {msg}")

def banner(title):
    print("\n" + "=" * 64)
    print(f"  {title}")
    print("=" * 64)

# ============================================================
# P: 预检
# ============================================================
def detect_mcp_tools():
    """
    P1: 检测 Atlassian MCP 工具是否可用。
    真实环境中应检查 MCP 客户端能否列出/调用这些工具。
    本环境无 MCP 桥接，返回不可用。
    """
    required = [
        "search", "getConfluencePage", "createConfluencePage",
        "updateConfluencePage", "getConfluenceSpaces",
    ]
    # 本脚本运行在无 MCP 的环境中，这些工具名不在 Python 全局/可调用范围内
    available = []
    missing = [t for t in required if t not in available]
    return available, missing

def preflight():
    """执行预检 P1-P3，返回 (ok, results)。"""
    global DRY_RUN, CLOUD_ID
    results = []

    # P1: MCP 工具
    available, missing = detect_mcp_tools()
    p1 = len(missing) == 0
    results.append(("P1", "Atlassian MCP 工具可用", p1,
                    "全部可用" if p1 else f"缺少: {', '.join(missing)}"))

    # P2: Cloud ID / 站点 URL
    p2 = CLOUD_ID is not None and str(CLOUD_ID).strip() != ""
    results.append(("P2", "Cloud ID / 站点 URL 已配置", p2,
                    CLOUD_ID if p2 else "未提供（SKILL.md 要求：无则询问用户）"))

    # P3: 身份与权限（只读探测）——依赖 P1
    if p1 and p2:
        p3 = _probe_permission(CLOUD_ID)
        results.append(("P3", "身份认证与只读权限", p3,
                        "只读探测成功" if p3 else "认证/权限失败"))
    else:
        p3 = False
        results.append(("P3", "身份认证与只读权限", False, "跳过（P1/P2 未通过）"))

    ok = p1 and p2 and p3
    DRY_RUN = not ok  # 预检不通过 => 强制干跑
    return ok, results

def _probe_permission(cloud_id):
    """真实环境：调用 search 或 getConfluenceSpaces 做只读探测。"""
    return True  # 干跑不会走到这里

# ============================================================
# ID 与格式校验（P5-P7）
# ============================================================
def validate_page_id(pid):
    """P5: Page ID 应为数字。"""
    if not re.fullmatch(r"\d+", str(pid)):
        raise ValueError(f"Page ID 应为数字，收到: {pid!r}")

def validate_space_key(key):
    """P5: Space Key 通常为大写字母数字串。"""
    if not re.fullmatch(r"[A-Z][A-Z0-9_]*", str(key)):
        raise ValueError(f"Space Key 应为大写字母开头的串，收到: {key!r}")

def validate_markdown_body(body):
    """P6: body 必须为 Markdown，禁止 HTML 标签。"""
    if not isinstance(body, str) or not body.strip():
        raise ValueError("body 不能为空，且必须为 Markdown 字符串")
    if re.search(r"<[a-zA-Z/][^>]*>", body):
        raise ValueError("body 含 HTML 标签；SKILL.md 要求始终使用 Markdown，禁止 HTML")

def validate_title(title):
    """P7: 标题非空，不含 Confluence 非法字符。"""
    if not title or not str(title).strip():
        raise ValueError("标题不能为空")
    if re.search(r"[#?&]", str(title)):
        raise ValueError(f"标题含 Confluence 非法字符(# ? &): {title!r}")

# ============================================================
# MCP 工具抽象层（真实调用 / 干跑模拟）
# ============================================================
def mcp_search(query):
    if DRY_RUN:
        log("DRY-RUN", f"search({query!r}) -> 【示例数据】")
        hits = []
        for p in MOCK_PAGES.values():
            if any(kw in p["title"] or kw in p["body"] for kw in re.findall(r"\w+", query)):
                hits.append({"id": p["id"], "title": p["title"],
                             "spaceKey": p["spaceKey"], "excerpt": p["body"][:40] + "..."})
        return hits
    # 真实环境：return mcp_client.search(query)
    raise RuntimeError("未接入 MCP")

def mcp_get_spaces(keys):
    if DRY_RUN:
        log("DRY-RUN", f"getConfluenceSpaces(keys={keys}) -> 【示例数据】")
        return [MOCK_SPACES[k] for k in keys if k in MOCK_SPACES]
    raise RuntimeError("未接入 MCP")

def mcp_get_page(cloud_id, page_id):
    if DRY_RUN:
        log("DRY-RUN", f"getConfluencePage(cloudId, pageId={page_id}) -> 【示例数据】")
        p = MOCK_PAGES.get(str(page_id))
        if not p:
            return None
        return dict(p)
    raise RuntimeError("未接入 MCP")

def mcp_create_page(cloud_id, space_id, title, body):
    if DRY_RUN:
        new_id = str(30000 + len(MOCK_PAGES) + 1)
        log("DRY-RUN", f"createConfluencePage -> 将创建【示例】页面 id={new_id}（未真正写入）")
        return {"id": new_id, "title": title, "spaceId": space_id,
                "_links": {"webui": f"/spaces/.../pages/{new_id}"}}
    raise RuntimeError("未接入 MCP")

def mcp_update_page(cloud_id, page_id, title, body, version):
    if DRY_RUN:
        log("DRY-RUN", f"updateConfluencePage(pageId={page_id}, version={version}) -> 【示例】未真正写入")
        return {"id": page_id, "title": title, "version": version + 1}
    raise RuntimeError("未接入 MCP")

# ============================================================
# R: 重试（仅对可重试错误）
# ============================================================
class TransientError(Exception):
    pass

class PermanentError(Exception):
    pass

def with_retry(func, *args, _is_write=False, **kwargs):
    """
    对瞬时错误（网络/5xx/429）指数退避重试；
    对 4xx 认证/参数/404 不重试。
    写入操作重试前须重新确认前置状态（此处由调用方保证幂等）。
    """
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return func(*args, **kwargs)
        except TransientError as e:
            last_err = e
            if attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF[attempt - 1]
                log("RETRY", f"第{attempt}次失败（瞬时错误: {e}），{wait}s 后重试...")
                time.sleep(wait)
            else:
                log("RETRY", f"已达最大重试次数 {MAX_RETRIES}，放弃。")
                raise
        except PermanentError as e:
            log("ERROR", f"永久错误，不重试: {e}")
            raise

# ============================================================
# C: 人工确认
# ============================================================
def human_confirm(checkpoint, description, preview=""):
    """
    人工确认点。干跑模式下自动通过并标注【干跑自动确认】；
    真实环境应暂停并等待用户输入"确认"/"YES"。
    """
    print("\n" + "-" * 64)
    print(f"[人工确认点 {checkpoint}] {description}")
    if preview:
        print("---- 预览 ----")
        print(preview)
        print("--------------")
    if DRY_RUN:
        log("CONFIRM", f"{checkpoint} 干跑模式：自动确认（真实环境需用户输入“确认”）")
        return True
    # 真实环境：
    # ans = input("输入“确认”继续，其他取消：").strip()
    # return ans in ("确认", "YES")
    return False

# ============================================================
# 业务操作
# ============================================================
def op_search(query):
    """6.1 搜索页面（只读，天然幂等）。"""
    banner("场景一：搜索页面（只读）")
    log("INFO", f"自然语言查询: {query!r}（SKILL.md: 优先使用 search）")
    hits = with_retry(mcp_search, query)
    log("INFO", f"命中 {len(hits)} 条：")
    for h in hits:
        print(f"  - [{h['id']}] {h['title']}  (space: {h['spaceKey']})")
        print(f"    摘要: {h['excerpt']}")
    return hits

def op_create_page(space_key, title, body, allow_duplicate=False):
    """6.2 创建页面（预检 + 查重 + 人工确认）。"""
    banner("场景二：创建页面（含幂等查重）")
    # P4-P7
    validate_space_key(space_key)
    validate_title(title)
    validate_markdown_body(body)

    # P4: 验证空间存在
    spaces = with_retry(mcp_get_spaces, [space_key])
    if not spaces:
        raise PermanentError(f"空间 {space_key!r} 不存在，中止创建（P4）")
    space = spaces[0]
    log("INFO", f"P4 通过：空间 {space_key} 存在 (spaceId={space['id']})")

    # I: 查重
    existing = with_retry(mcp_search, title)
    same_title = [h for h in existing if h["title"] == title]
    if same_title and not allow_duplicate:
        log("WARN", f"幂等拦截：已存在同名页面，不创建。")
        for h in same_title:
            print(f"  已存在: [{h['id']}] {h['title']} (space: {h['spaceKey']})")
        log("INFO", "如确需创建，请设置 allow_duplicate=True 并经 C3 确认。")
        return {"status": "skipped_duplicate", "existing": same_title}

    if same_title and allow_duplicate:
        human_confirm("C3", "同名页面已存在，仍要创建",
                      "\n".join(f"  [{h['id']}] {h['title']}" for h in same_title))

    # C1: 人工确认
    preview = f"空间: {space_key} (spaceId={space['id']})\n标题: {title}\n\n{body}"
    if not human_confirm("C1", "即将创建 Confluence 页面", preview):
        log("INFO", "用户取消创建。")
        return {"status": "cancelled"}

    result = with_retry(mcp_create_page, CLOUD_ID, space["id"], title, body, _is_write=True)
    log("INFO", f"创建完成（干跑）: {result}")
    return {"status": "created", "result": result}

def op_update_page(page_id, new_title, new_body):
    """6.3 更新页面（预检 + 取当前版本 + diff + 无变更跳过 + 人工确认）。"""
    banner("场景三：更新页面（含版本比对与 diff）")
    validate_page_id(page_id)
    validate_title(new_title)
    validate_markdown_body(new_body)

    # I: 取当前内容与版本
    current = with_retry(mcp_get_page, CLOUD_ID, page_id)
    if not current:
        raise PermanentError(f"页面 {page_id} 不存在，中止更新（404 不重试）")
    log("INFO", f"当前页面: [{current['id']}] {current['title']} (version={current['version']})")

    # I: 比对（忽略首尾空白）
    cur_body_norm = current["body"].strip()
    new_body_norm = new_body.strip()
    title_changed = (current["title"] != new_title)

    if not title_changed and cur_body_norm == new_body_norm:
        log("INFO", "幂等跳过：标题与正文均无变更，不调用 updateConfluencePage。")
        return {"status": "no_change"}

    # 生成 diff
    diff = difflib.unified_diff(
        current["body"].splitlines(), new_body.splitlines(),
        fromfile=f"当前 v{current['version']}", tofile="待写入",
        lineterm="", n=1)
    diff_text = "\n".join(diff)
    if title_changed:
        diff_text = f"标题: {current['title']!r} -> {new_title!r}\n" + diff_text

    # C2: 人工确认
    if not human_confirm("C2", "即将更新 Confluence 页面", diff_text):
        log("INFO", "用户取消更新。")
        return {"status": "cancelled"}

    # 乐观锁：携带当前版本号
    result = with_retry(mcp_update_page, CLOUD_ID, page_id, new_title, new_body,
                        current["version"], _is_write=True)
    log("INFO", f"更新完成（干跑）: {result}")
    return {"status": "updated", "result": result}

# ============================================================
# 重试演示（瞬时错误 -> 成功）
# ============================================================
def demo_retry():
    banner("场景四：重试策略演示（瞬时错误自动退避）")
    attempts = {"n": 0}
    def flaky_call():
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise TransientError("503 Service Unavailable（模拟）")
        return "OK"
    log("INFO", "模拟前两次返回 503，第三次成功：")
    # 把退避时间缩短以免演示等待过久
    global RETRY_BACKOFF
    RETRY_BACKOFF = [0, 0, 0]
    r = with_retry(flaky_call)
    log("INFO", f"结果: {r}，共尝试 {attempts['n']} 次")

# ============================================================
# 主流程
# ============================================================
def main():
    banner("Confluence 受约束操作工作流 — 干跑演示")
    print(f"依据: confluence-assistant SKILL.md v1.0.0")
    print(f"时间: {datetime.now(timezone.utc).astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"说明: 本演示不连接真实 Confluence，所有数据均为【示例数据】。")

    # ---- 预检 ----
    banner("预检（Pre-flight）")
    ok, results = preflight()
    for pid, name, passed, detail in results:
        status = "PASS" if passed else "FAIL"
        print(f"  [{pid}] {name}: {status} — {detail}")
    print(f"\n预检结论: {'通过，可执行真实操作' if ok else '未通过 -> 进入干跑模式（不接触外部资源）'}")

    # ---- 场景一：搜索 ----
    op_search("API 文档")

    # ---- 场景二：创建（首次：同名已存在 -> 幂等跳过） ----
    try:
        op_create_page(
            space_key="TECH",
            title="API 文档",  # 与示例数据中已有页面同名
            body="# API 文档\n\n## 认证\n使用 Bearer Token。\n",
        )
    except PermanentError as e:
        log("ERROR", str(e))

    # ---- 场景二续：创建（新标题 -> 经 C1 确认 -> 干跑写入） ----
    op_create_page(
        space_key="TECH",
        title="ADR-001: 使用 Markdown 编写 Confluence",
        body="# ADR-001: 使用 Markdown 编写 Confluence\n\n## 状态\nAccepted\n\n## 决策\n"
             "依据 SKILL.md，body 始终使用 Markdown，禁止 HTML。\n",
    )

    # ---- 场景三：更新（有变更 -> diff -> C2 确认 -> 干跑写入） ----
    op_update_page(
        page_id="20001",
        new_title="API 文档",
        new_body="# API 文档\n\n## 认证\n使用 Bearer Token。\n\n## 端点\n"
                 "- GET /v1/users\n- POST /v1/users  # 新增\n",
    )

    # ---- 场景三续：更新（无变更 -> 幂等跳过） ----
    page = MOCK_PAGES["20002"]
    op_update_page(
        page_id="20002",
        new_title=page["title"],
        new_body=page["body"],
    )

    # ---- 场景四：重试演示 ----
    demo_retry()

    # ---- 格式校验演示（P6: 拒绝 HTML） ----
    banner("场景五：格式校验（P6 拒绝 HTML body）")
    try:
        validate_markdown_body("<h1>这是 HTML</h1>")
    except ValueError as e:
        log("BLOCK", f"P6 拦截: {e}")

    banner("演示结束")
    print("以上所有写入均为干跑模拟，未对任何 Confluence 实例产生副作用。")
    print("真实执行需：接入 Atlassian MCP Server + 提供 Cloud ID + 完成认证 + 人工确认。")

if __name__ == "__main__":
    main()
