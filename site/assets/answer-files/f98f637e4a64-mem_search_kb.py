#!/usr/bin/env python3
"""
mem-search 本地知识库 —— 在 MCP 工具不可用时的受限替代实现。

严格遵循 SKILL.md 的三层工作流：
  Step 1: search  —— 仅返回索引（ID/时间/类型/标题），~50-100 tokens/条
  Step 2: timeline —— 返回锚点前后上下文
  Step 3: get_observations —— 仅对筛选后的 ID 批量取详情，~500-1000 tokens/条

去重规则：
  - 连续的 assistant 文本 + 紧随其后的纯工具调用合并为一条 observation
  - queue-operation / last-prompt 等非内容记录已剔除
  - "hello world" 测试会话保留但标记为 test 类型
"""

import json, re, sys
from pathlib import Path

# ============================================================
# 知识库数据：从 3 个旧会话 .jsonl 中提取、去重、主题归档
# ============================================================

KNOWLEDGE_BASE = [
    {
        "id": 1,
        "time": "2026-08-10T13:07:39Z",
        "type": "session",
        "obs_type": "test",
        "project": "eval-remote-work",
        "title": "连通性测试：hello world",
        "subtitle": "da221365 会话，验证模型响应",
        "source_file": "~/.claude/projects/-Users-bytedance-Doubao-chats-2026-08-10-new-chat-403/da221365-4d8a-4486-b58c-c6deee348599.jsonl",
        "source_line": 3,
        "narrative": "用户要求模型逐字输出 'hello world'，模型正确响应。此为环境连通性测试，无项目实质内容。",
        "facts": [
            "测试指令：Say exactly: hello world",
            "模型响应：hello world",
            "会话 ID: da221365-4d8a-4486-b58c-c6deee348599"
        ],
        "concepts": ["连通性测试", "hello world"],
        "files": []
    },
    {
        "id": 2,
        "time": "2026-08-10T13:09:05Z",
        "type": "observation",
        "obs_type": "decision",
        "project": "eval-remote-work",
        "title": "研究计划评审：远程办公与创新效率（advisor #1）",
        "subtitle": "board advisor 对 6-worker 研究计划的批判",
        "source_file": "~/.claude/projects/-Users-bytedance-Doubao-chats-2026-08-10-new-chat-403/3173a89b-2011-4c21-b471-0d9513efbd44.jsonl",
        "source_line": 3,
        "narrative": "用户以 board advisor 角色要求评审一份关于'远程办公是否必然降低团队创新效率'的中文研究简报计划。计划分 2 波 6 个 worker（W1 理论框架、W2 元分析、W3 自然实验/RCT、W4 机制、W5 边界条件、W6 反方证据）。Advisor 判定计划结构合理但有漏洞。",
        "facts": [
            "研究问题：远程办公是否必然降低团队创新效率",
            "计划分 2 波 6 个并行 worker",
            "成功标准：区分相关/因果、≥6 项可验证研究、≥3 个争议点、所有外部事实有可核验引用、中文撰写",
            "advisor 指出三大风险：(1)搜索不系统可能产生虚构引用 (2)W1 与 W4 重叠 (3)无人负责'创新效率'操作化定义",
            "修复建议：W4 合并入 W1，新设'测量与操作化'worker；要求 ≥2 数据库检索协议；W3 不限于 COVID；增加交叉验证步骤",
            "advisor 认为 Wave 1/2 区分是装饰性的，6 个任务可全部并行"
        ],
        "concepts": ["研究设计评审", "因果推断强度", "远程办公", "创新效率", "worker 编排", "文献检索协议"],
        "files": []
    },
    {
        "id": 3,
        "time": "2026-08-10T13:13:59Z",
        "type": "observation",
        "obs_type": "bugfix",
        "project": "eval-remote-work",
        "title": "引用验证失败：沙箱网络限制导致无法外部核验",
        "subtitle": "评审者尝试 Crossref/DOI 验证 3 条可疑引用但被沙箱阻断",
        "source_file": "~/.claude/projects/-Users-bytedance-Doubao-chats-2026-08-10-new-chat-403/de8be236-7f3d-44e4-a060-0dd0b9ea3e0f.jsonl",
        "source_line": 5,
        "narrative": "在交付物评审中，评审者为验证标准 #4（无虚构数据），尝试通过 Bash 调用外部服务核验 Siemroth et al. (2024)、Choudhury (2017)、Criscuolo et al. (2023) 三条引用。多次尝试（含禁用沙箱重试、写脚本文件规避管道问题）均因网络限制失败。最终基于文献知识评审并明确标注验证缺口。",
        "facts": [
            "尝试验证的引用：Siemroth et al. (2024) Scientific Reports、Choudhury (2017) Organization Science、Criscuolo et al. (2023) OECD",
            "失败原因：sandbox network restrictions",
            "尝试了 3 种方式：直接 Bash、禁用沙箱重试、写脚本文件",
            "共产生 16 次纯工具调用（另有 4 条文本+工具调用混合记录），已去重合并",
            "评审者明确声明：I was unable to complete external verification due to sandbox network restrictions"
        ],
        "concepts": ["引用验证", "沙箱限制", "网络访问", "虚构数据风险", "降级处理"],
        "files": []
    },
    {
        "id": 4,
        "time": "2026-08-10T13:13:59Z",
        "type": "observation",
        "obs_type": "decision",
        "project": "eval-remote-work",
        "title": "交付物评审结论：CONDITIONAL PASS",
        "subtitle": "critical taste reviewer 对远程办公研究简报的终审",
        "source_file": "~/.claude/projects/-Users-bytedance-Doubao-chats-2026-08-10-new-chat-403/de8be236-7f3d-44e4-a060-0dd0b9ea3e0f.jsonl",
        "source_line": 48,
        "narrative": "评审者对中文研究简报《远程办公是否必然降低团队创新效率？》给出 CONDITIONAL PASS。简报含 12 项研究证据矩阵、因果机制分析、5 个争议点、局限性与待验证问题。评审者认为结构健全但需修复 4 项问题后方可发布。",
        "facts": [
            "判定：CONDITIONAL PASS（有条件通过）",
            "简报含 12 项研究，证据强度从 RCT ★★★★★ 到横截面 ★★☆☆☆",
            "核心结论：完全远程对突破式创新有因果性负面影响，对渐进式创新影响不一",
            "问题 1：证据矩阵列 12 项研究但参考文献称 13 项，数量不一致",
            "问题 2：3 条引用无法外部验证（Siemroth 2024、Choudhury 2017、Criscuolo 2023）",
            "问题 3：Bloom et al. (2015) 缺期刊名（应为 Quarterly Journal of Economics）",
            "问题 4：星级评分缺少评级标准说明",
            "可忽略项：不应要求创新主题的 RCT（领域限制）；不应要求二元结论；降级 worker 流程已披露不扣分"
        ],
        "concepts": ["交付物评审", "证据矩阵", "因果推断", "引用核验", "CONDITIONAL PASS", "远程办公", "创新效率"],
        "files": []
    }
]

# ============================================================
# Step 1: search —— 返回精简索引
# ============================================================

def search(query="", limit=20, project=None, obs_type=None, dateStart=None, dateEnd=None, offset=0, orderBy="date_desc"):
    """模拟 SKILL.md 的 search MCP 工具：仅返回 ID/时间/类型/标题。"""
    results = KNOWLEDGE_BASE[:]

    if query:
        q = query.lower()
        results = [
            o for o in results
            if q in o["title"].lower()
            or q in o["subtitle"].lower()
            or q in o["narrative"].lower()
            or any(q in f.lower() for f in o["facts"])
            or any(q in c.lower() for c in o["concepts"])
        ]

    if project:
        results = [o for o in results if o["project"] == project]
    if obs_type:
        results = [o for o in results if o["obs_type"] == obs_type]
    if dateStart:
        results = [o for o in results if o["time"][:10] >= dateStart]
    if dateEnd:
        results = [o for o in results if o["time"][:10] <= dateEnd]

    if orderBy == "date_asc":
        results.sort(key=lambda o: o["time"])
    elif orderBy == "date_desc":
        results.sort(key=lambda o: o["time"], reverse=True)

    results = results[offset:offset + limit]

    # SKILL.md 格式：| ID | Time | T | Title | Read |
    rows = []
    for o in results:
        t_icon = {"observation": "🔴", "session": "🟣", "prompt": "🟡"}.get(o["type"], "⚪")
        read_est = len(o["narrative"]) // 8 + sum(len(f) for f in o["facts"]) // 8
        rows.append({
            "ID": f"#{o['id']}",
            "Time": o["time"][:19].replace("T", " "),
            "T": t_icon,
            "Type": o["obs_type"],
            "Title": o["title"],
            "Read~": f"~{read_est}"
        })
    return rows


# ============================================================
# Step 2: timeline —— 返回锚点前后上下文
# ============================================================

def timeline(anchor=None, query=None, depth_before=5, depth_after=5, project=None):
    """模拟 SKILL.md 的 timeline MCP 工具。"""
    if anchor is None and query:
        hits = search(query=query, limit=1, project=project)
        if not hits:
            return []
        anchor = int(hits[0]["ID"].lstrip("#"))

    sorted_obs = sorted(KNOWLEDGE_BASE, key=lambda o: o["time"])
    ids = [o["id"] for o in sorted_obs]
    if anchor not in ids:
        return []
    idx = ids.index(anchor)
    start = max(0, idx - depth_before)
    end = min(len(sorted_obs), idx + depth_after + 1)

    rows = []
    for o in sorted_obs[start:end]:
        marker = " >>>" if o["id"] == anchor else "    "
        rows.append({
            "marker": marker,
            "ID": f"#{o['id']}",
            "Time": o["time"][:19].replace("T", " "),
            "Type": o["obs_type"],
            "Title": o["title"]
        })
    return rows


# ============================================================
# Step 3: get_observations —— 批量取详情
# ============================================================

def get_observations(ids, orderBy="date_desc", limit=None, project=None):
    """模拟 SKILL.md 的 get_observations MCP 工具。ALWAYS 批量。"""
    id_set = set(ids)
    results = [o for o in KNOWLEDGE_BASE if o["id"] in id_set]
    if project:
        results = [o for o in results if o["project"] == project]
    if orderBy == "date_asc":
        results.sort(key=lambda o: o["time"])
    else:
        results.sort(key=lambda o: o["time"], reverse=True)
    if limit:
        results = results[:limit]
    return results


# ============================================================
# 演示
# ============================================================

def print_table(rows, title=""):
    if not rows:
        print(f"  (无结果)")
        return
    if title:
        print(f"\n{'='*70}\n{title}\n{'='*70}")
    keys = list(rows[0].keys())
    widths = {k: max(len(str(k)), max(len(str(r.get(k,""))) for r in rows)) for k in keys}
    header = " | ".join(k.ljust(widths[k]) for k in keys)
    print(header)
    print("-+-".join("-" * widths[k] for k in keys))
    for r in rows:
        print(" | ".join(str(r.get(k,"")).ljust(widths[k]) for k in keys))

def main():
    print("=" * 70)
    print("mem-search 本地知识库演示（MCP 工具不可用环境下的受限替代）")
    print("=" * 70)
    print(f"知识库记录数: {len(KNOWLEDGE_BASE)}")
    print(f"来源文件数: 3 个 .jsonl 会话文件")
    print()

    # ---- 查询 1: 远程办公相关研究 ----
    print("\n" + "█" * 70)
    print("查询 1: search(query='远程办公 创新', limit=10)")
    print("█" * 70)
    q1_results = search(query="远程办公", limit=10)
    print_table(q1_results, "Step 1: search 索引结果")

    print("\nStep 2: timeline(anchor=2, depth_before=1, depth_after=2)")
    tl1 = timeline(anchor=2, depth_before=1, depth_after=2)
    print_table(tl1, "时间线上下文")

    print("\nStep 3: get_observations(ids=[2, 4])  # 仅取筛选后的相关 ID")
    details1 = get_observations(ids=[2, 4])
    for o in details1:
        print(f"\n  ── #{o['id']} {o['title']} ──")
        print(f"  来源: {o['source_file']}:{o['source_line']}")
        print(f"  叙述: {o['narrative'][:200]}...")
        print(f"  关键事实 ({len(o['facts'])} 条):")
        for f in o['facts'][:3]:
            print(f"    • {f}")
        print(f"  概念: {', '.join(o['concepts'][:5])}")

    # ---- 查询 2: 引用验证 / 虚构数据 ----
    print("\n\n" + "█" * 70)
    print("查询 2: search(query='引用 验证', obs_type='bugfix')")
    print("█" * 70)
    q2_results = search(query="验证", obs_type="bugfix", limit=10)
    print_table(q2_results, "Step 1: search 索引结果")

    print("\nStep 2: timeline(query='验证', depth_before=1, depth_after=1)")
    tl2 = timeline(query="验证", depth_before=1, depth_after=1)
    print_table(tl2, "时间线上下文")

    print("\nStep 3: get_observations(ids=[3])  # 批量取详情")
    details2 = get_observations(ids=[3])
    for o in details2:
        print(f"\n  ── #{o['id']} {o['title']} ──")
        print(f"  来源: {o['source_file']}:{o['source_line']}")
        print(f"  叙述: {o['narrative']}")
        print(f"  关键事实:")
        for f in o['facts']:
            print(f"    • {f}")

    # ---- 查询 3: 评审结论 / 决策 ----
    print("\n\n" + "█" * 70)
    print("查询 3: search(query='PASS', obs_type='decision')")
    print("█" * 70)
    q3_results = search(query="PASS", obs_type="decision", limit=10)
    print_table(q3_results, "Step 1: search 索引结果")

    print("\nStep 2: timeline(anchor=4, depth_before=2, depth_after=0)")
    tl3 = timeline(anchor=4, depth_before=2, depth_after=0)
    print_table(tl3, "时间线上下文（锚点前 2 条）")

    print("\nStep 3: get_observations(ids=[4])  # 批量取详情")
    details3 = get_observations(ids=[4])
    for o in details3:
        print(f"\n  ── #{o['id']} {o['title']} ──")
        print(f"  来源: {o['source_file']}:{o['source_line']}")
        print(f"  叙述: {o['narrative']}")
        print(f"  关键事实:")
        for f in o['facts']:
            print(f"    • {f}")
        print(f"  概念: {', '.join(o['concepts'])}")

    # ---- 去重与归档统计 ----
    print("\n\n" + "=" * 70)
    print("去重与主题归档统计")
    print("=" * 70)
    print(f"  原始 .jsonl 记录行数: 60 (3 文件合计，含 queue-operation 等)")
    print(f"  提取的 user/assistant 内容记录: 26")
    print(f"  去重合并后 observation 数: {len(KNOWLEDGE_BASE)}")
    print(f"    - 合并规则: 连续 assistant 文本 + 纯工具调用 → 1 条")
    print(f"    - 剔除: queue-operation(enqueue/dequeue)、last-prompt")
    print(f"    - 测试会话保留并标记 obs_type=test")
    print()
    topics = {}
    for o in KNOWLEDGE_BASE:
        t = o["obs_type"]
        topics.setdefault(t, []).append(o["id"])
    for t, ids in topics.items():
        print(f"  主题 [{t}]: IDs {ids}")

if __name__ == "__main__":
    main()
