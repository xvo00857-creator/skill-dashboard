#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
feedback-triage: 智能随行杯用户反馈最小可用分诊脚本。

输入: JSON 数组或 JSONL（每条含 id, text）。
输出: JSON —— 去重后的主题、优先级(P0-P3)、下一步行动。

设计依据: 随附 product_brief.md
  - 核心卖点: 12小时保温、280g、可拆洗杯盖
  - 禁止编造: 第三方检测结论、销量、用户评价、竞品价格
  - 待补项: 首发日期、防水等级、食品接触材料报告
  - 交付要求: 中文；结论与假设分开；外部数据列为待补项

仅使用 Python 标准库，确定性规则，无外部 API/账号依赖。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from typing import Any

# ── 产品约束（来自 product_brief.md，不得编造） ─────────────────────────────

PRODUCT_NAME = "智能随行杯"
CORE_SELLING_POINTS = ["12小时保温", "280g", "可拆洗杯盖"]
FORBIDDEN_FABRICATION = ["第三方检测结论", "销量", "用户评价", "竞品价格"]
PENDING_INFO = ["首发日期", "防水等级", "食品接触材料报告"]

# ── 严重度关键词（按优先级从高到低匹配，命中即止） ─────────────────────────

SEVERITY_KEYWORDS: list[tuple[str, list[str]]] = [
    ("critical", [
        "受伤", "烫伤", "割手", "划伤出血", "中毒", "危险", "爆炸", "起火",
        "漏电", "触电", "短路", "发霉", "变质", "拉肚子", "呕吐",
    ]),
    ("high", [
        "漏水", "渗水", "漏了", "洒了", "不保温", "保不了温", "不热", "凉了",
        "坏了", "故障", "失效", "用不了", "掉漆", "破损", "裂了", "断裂",
        "异味", "臭味", "怪味", "塑料味", "味道大", "有毒", "生锈", "掉底",
    ]),
    ("medium", [
        "难清洗", "不好洗", "洗不干净", "太重", "沉", "色差", "颜色不对",
        "有划痕", "缝隙", "缝隙大", "密封不严", "有点漏", "保温一般",
        "不够保温", "贵", "不划算", "物流慢", "包装破", "掉毛", "毛刺",
    ]),
    ("low", [
        "建议", "希望", "要是", "如果能", "能不能", "最好", "有点", "稍微",
        "还行", "一般般", "期待", "可以加",
    ]),
]

SEVERITY_ORDER = {"critical": 3, "high": 2, "medium": 1, "low": 0, "none": -1}

# ── 主题词表（按顺序匹配，第一条命中的主题为主主题） ───────────────────────
# is_safety: 涉及安全/合规，命中高严重度直接 P0
# is_core: 命中核心卖点，高严重度至少 P1
# action: 下一步行动模板；pending: 该主题依赖的待补外部数据

THEMES: list[dict[str, Any]] = [
    {
        "id": "safety-material",
        "name": "材质与食品安全",
        "keywords": ["食品接触", "材质", "塑料味", "异味", "臭味", "怪味", "味道",
                     "不锈钢", "涂层", "发霉", "变质", "安全", "认证", "报告", "有毒"],
        "is_safety": True,
        "is_core": False,
        "action": "待食品接触材料报告提供后核实；报告齐备前，对外口径不得宣称任何认证或检测结论。",
        "pending": ["食品接触材料报告"],
    },
    {
        "id": "electronic-waterproof",
        "name": "电子功能与防水",
        "keywords": ["防水", "充电", "电池", "电量", "漏电", "触电", "短路",
                     "智能", "蓝牙", "app", "屏幕", "显示", "按键", "起火", "爆炸"],
        "is_safety": True,
        "is_core": False,
        "action": "防水等级尚未提供，列为待补项；等级确认前不得宣传防水能力。同步排查电子件安全。",
        "pending": ["防水等级"],
    },
    {
        "id": "insulation",
        "name": "保温性能",
        "keywords": ["保温", "保冷", "不热", "凉了", "温度", "12小时", "不保温",
                     "保不了温", "不够保温", "保温一般"],
        "is_safety": False,
        "is_core": True,
        "action": "安排内部12小时保温复测，记录实测温度曲线；如需对外引用检测结论，须先取得第三方报告（待补项）。",
        "pending": [],
    },
    {
        "id": "sealing-leak",
        "name": "密封与漏水",
        "keywords": ["漏水", "渗水", "漏了", "洒了", "密封", "密封圈", "倒置",
                     "有点漏", "密封不严"],
        "is_safety": False,
        "is_core": False,
        "action": "做倒置与通勤颠簸密封测试，定位漏点（密封圈/杯口/杯盖），输出改进方案。",
        "pending": [],
    },
    {
        "id": "lid-cleaning",
        "name": "杯盖与可拆洗",
        "keywords": ["杯盖", "盖子", "拆洗", "拆卸", "清洗", "难清洗", "不好洗",
                     "洗不干净", "卫生死角", "缝隙", "胶圈"],
        "is_safety": False,
        "is_core": True,
        "action": "核查杯盖可拆洗结构与密封圈卫生死角，更新清洗指引并验证拆装体验。",
        "pending": [],
    },
    {
        "id": "weight-portability",
        "name": "重量与便携",
        "keywords": ["重", "太重", "沉", "轻", "便携", "随身", "通勤", "280g",
                     "重量", "轻便"],
        "is_safety": False,
        "is_core": True,
        "action": "抽样复称实物重量，核对与标称280g一致性；若偏差超出公差，评估产线或标注问题。",
        "pending": [],
    },
    {
        "id": "appearance-build",
        "name": "外观与做工",
        "keywords": ["掉漆", "划痕", "色差", "颜色", "外观", "做工", "瑕疵",
                     "毛刺", "掉毛", "破损", "裂了", "断裂", "生锈", "掉底"],
        "is_safety": False,
        "is_core": False,
        "action": "排查产线外观质检标准，确认是否批次问题；必要时留样并联系供应商。",
        "pending": [],
    },
    {
        "id": "price-value",
        "name": "价格与性价比",
        "keywords": ["贵", "便宜", "199", "价格", "性价比", "划算", "值", "不值"],
        "is_safety": False,
        "is_core": False,
        "action": "汇总价格相关反馈进入需求池；竞品价格属于禁止编造项，如需对比须另行采购真实数据。",
        "pending": ["竞品价格（如需对比，须另行获取真实数据）"],
    },
    {
        "id": "logistics-packaging",
        "name": "物流与包装",
        "keywords": ["快递", "物流", "包装", "发货", "到货", "破损", "慢", "压坏"],
        "is_safety": False,
        "is_core": False,
        "action": "对接物流方核损，优化包装缓冲结构；跟踪破损率。",
        "pending": [],
    },
    {
        "id": "other",
        "name": "其他与建议",
        "keywords": [],  # 兜底主题
        "is_safety": False,
        "is_core": False,
        "action": "进入需求池，月度评审；若涉及首发日期等未确定信息，统一回复以官方发布为准。",
        "pending": ["首发日期"],
    },
]


# ── 文本工具 ───────────────────────────────────────────────────────────────

_PUNCT_RE = re.compile("[\\s\u3000，。！？、；：“”‘’（）【】《》…—·,.!?;:()<>\\[\\]-]+")


def normalize(text: str) -> str:
    """归一化：小写 + 去空白与标点，用于重复检测。"""
    return _PUNCT_RE.sub("", text.lower())


def detect_severity(text: str) -> str:
    """返回 critical/high/medium/low/none。"""
    low = text.lower()
    for level, kws in SEVERITY_KEYWORDS:
        for kw in kws:
            if kw in low:
                return level
    return "none"


def classify_theme(text: str) -> dict[str, Any]:
    """按词表顺序返回第一条命中的主题；无命中返回兜底主题。"""
    low = text.lower()
    for theme in THEMES:
        if not theme["keywords"]:
            continue
        for kw in theme["keywords"]:
            if kw in low:
                return theme
    return THEMES[-1]


# ── 优先级计算 ─────────────────────────────────────────────────────────────

def compute_priority(severity: str, count: int, is_safety: bool, is_core: bool) -> str:
    """根据严重度、数量、安全/核心卖点标记计算 P0-P3。"""
    sev = SEVERITY_ORDER[severity]
    # P0: 单条 critical；或安全/合规主题且严重度 >= high
    if severity == "critical":
        return "P0"
    if is_safety and sev >= SEVERITY_ORDER["high"]:
        return "P0"
    # P1: 高严重度且（命中核心卖点 或 同主题 >=2 条）；或中严重度且同主题 >=3 条
    if sev >= SEVERITY_ORDER["high"] and (is_core or count >= 2):
        return "P1"
    if sev >= SEVERITY_ORDER["medium"] and count >= 3:
        return "P1"
    # P2: 其余高严重度（非核心、单条）；或中严重度
    if sev >= SEVERITY_ORDER["medium"]:
        return "P2"
    # P3: low / none
    return "P3"


# ── 输入解析 ───────────────────────────────────────────────────────────────

def load_feedback(path: Path) -> tuple[list[dict], list[dict]]:
    """读取 JSON 数组或 JSONL。返回 (有效反馈列表, 跳过记录列表)。"""
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise
    except UnicodeDecodeError as exc:
        raise ValueError(f"文件编码不是 UTF-8：{exc}") from exc

    items: list[Any] = []
    stripped = raw.strip()
    if not stripped:
        return [], [{"index": 0, "reason": "文件为空"}]

    # JSONL: 多行且首字符不是 [ 时按行解析
    if not stripped.startswith("["):
        for lineno, line in enumerate(stripped.splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"JSONL 第 {lineno} 行解析失败：{exc.msg}（位置 {exc.pos}）"
                ) from exc
    else:
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"JSON 解析失败：{exc.msg}（行 {exc.lineno}，列 {exc.colno}）"
            ) from exc
        if not isinstance(parsed, list):
            raise ValueError("JSON 顶层必须是数组")
        items = parsed

    feedback: list[dict] = []
    skipped: list[dict] = []
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            skipped.append({"index": idx, "reason": "不是对象"})
            continue
        if "id" not in item or item["id"] is None or str(item["id"]).strip() == "":
            skipped.append({"index": idx, "reason": "缺少 id"})
            continue
        if "text" not in item or not isinstance(item["text"], str) or not item["text"].strip():
            skipped.append({"index": idx, "id": item.get("id"), "reason": "缺少或空的 text"})
            continue
        feedback.append({
            "id": str(item["id"]),
            "text": item["text"].strip(),
            "source": item.get("source"),
            "timestamp": item.get("timestamp"),
        })
    return feedback, skipped


# ── 核心分诊 ───────────────────────────────────────────────────────────────

def triage(feedback: list[dict]) -> dict[str, Any]:
    """对反馈列表做去重、归类、优先级计算，返回结果字典。"""
    # 1) 文本级去重（归一化后相同视为重复，保留首条）
    seen_norm: dict[str, str] = {}
    unique: list[dict] = []
    duplicate_count = 0
    for fb in feedback:
        key = normalize(fb["text"])
        if key in seen_norm:
            duplicate_count += 1
            continue
        seen_norm[key] = fb["id"]
        unique.append(fb)

    # 2) 归类
    buckets: "OrderedDict[str, dict]" = OrderedDict()
    for fb in unique:
        theme = classify_theme(fb["text"])
        severity = detect_severity(fb["text"])
        bucket = buckets.setdefault(theme["id"], {
            "theme_id": theme["id"],
            "theme": theme["name"],
            "is_safety_related": theme["is_safety"],
            "is_core_selling_point": theme["is_core"],
            "items": [],
            "pending_items": list(theme["pending"]),
            "action": theme["action"],
        })
        bucket["items"].append({**fb, "severity": severity})

    # 3) 汇总每个主题
    themes_out: list[dict] = []
    counts = {"P0": 0, "P1": 0, "P2": 0, "P3": 0}
    for bucket in buckets.values():
        items = bucket["items"]
        count = len(items)
        # 主题严重度 = 该主题下最高严重度
        max_sev = max((it["severity"] for it in items),
                      key=lambda s: SEVERITY_ORDER[s])
        priority = compute_priority(
            max_sev, count,
            bucket["is_safety_related"], bucket["is_core_selling_point"],
        )
        counts[priority] += 1
        # 代表反馈：取严重度最高的一条；若并列取第一条
        representative = next(
            it for it in items
            if it["severity"] == max_sev
        )
        themes_out.append({
            "theme_id": bucket["theme_id"],
            "theme": bucket["theme"],
            "count": count,
            "priority": priority,
            "severity": max_sev,
            "is_safety_related": bucket["is_safety_related"],
            "is_core_selling_point": bucket["is_core_selling_point"],
            "feedback_ids": [it["id"] for it in items],
            "representative_feedback": representative["text"],
            "next_actions": [bucket["action"]],
            "pending_items": bucket["pending_items"],
        })

    # 4) 排序：P0 > P1 > P2 > P3，同级按 count 降序
    priority_rank = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    themes_out.sort(key=lambda t: (priority_rank[t["priority"]], -t["count"]))

    return {
        "product": PRODUCT_NAME,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "summary": {
            "total_feedback": len(feedback),
            "unique_feedback": len(unique),
            "duplicate_feedback": duplicate_count,
            "theme_count": len(themes_out),
            **counts,
        },
        "themes": themes_out,
        "pending_items": PENDING_INFO,
        "assumptions": [
            "主题归类与严重度判定基于关键词词表，未使用语义模型或外部 API。",
            "文本级去重按归一化（去标点/空白/大小写）后完全相同判定；近义复述不会被合并。",
            "优先级为规则计算结果，最终处理顺序需产品负责人确认。",
            f"核心卖点依据 product_brief.md：{ '、'.join(CORE_SELLING_POINTS) }。",
        ],
        "constraints": [
            f"未编造以下信息：{ '、'.join(FORBIDDEN_FABRICATION) }。",
            "需要外部数据的事项均列入 pending_items，未作为结论输出。",
        ],
    }


# ── CLI ────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="智能随行杯用户反馈分诊：去重主题 + 优先级 + 下一步行动",
    )
    parser.add_argument("input", help="输入文件（JSON 数组或 JSONL）")
    parser.add_argument("-o", "--output", help="输出文件（默认 stdout）")
    parser.add_argument("--strict", action="store_true",
                        help="存在被跳过的无效反馈时以退出码 1 结束")
    args = parser.parse_args(argv)

    in_path = Path(args.input)
    try:
        feedback, skipped = load_feedback(in_path)
    except FileNotFoundError:
        print(json.dumps({"error": f"输入文件不存在：{in_path}"},
                         ensure_ascii=False), file=sys.stderr)
        return 2
    except ValueError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False),
              file=sys.stderr)
        return 2

    result = triage(feedback)
    result["skipped"] = skipped

    out = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(out + "\n", encoding="utf-8")
    else:
        print(out)

    if args.strict and skipped:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
