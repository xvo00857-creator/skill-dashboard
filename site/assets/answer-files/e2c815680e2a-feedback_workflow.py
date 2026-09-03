#!/usr/bin/env python3
"""
用户反馈主题分析工作流（最小可用版）

输入：用户反馈列表（JSON）
输出：去重后的主题、优先级、下一步行动（JSON）

用法：
    python feedback_workflow.py --input feedback.json
    python feedback_workflow.py --input feedback.json --output result.json
    cat feedback.json | python feedback_workflow.py

设计约束（来自 product_brief.md）：
    - 不编造第三方检测结论、销量、用户评价、竞品价格
    - 结论与假设分开标注
    - 需要外部数据时列为待补项
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 异常定义
# ---------------------------------------------------------------------------

class InputError(Exception):
    """输入数据格式或读取错误。"""


# ---------------------------------------------------------------------------
# 常量与规则配置
# ---------------------------------------------------------------------------

# 高严重度关键词：命中即 P0（安全/质量事故类）
SEVERITY_HIGH_KEYWORDS: frozenset[str] = frozenset({
    "安全", "有毒", "烫伤", "漏水", "异味", "断裂", "爆炸", "着火",
    "漏电", "割手", "受伤", "发霉",
})

# 主题定义：(主题名, 关键词集合, 该主题涉及的待确认信息提示或 None)
THEME_DEFINITIONS: list[tuple[str, frozenset[str], str | None]] = [
    ("保温性能", frozenset({"保温", "保冷", "温度", "凉了", "不保温", "热水", "冰水"}), None),
    ("重量便携", frozenset({"重", "轻", "便携", "携带", "通勤", "重量", "轻便"}), None),
    ("杯盖清洗", frozenset({"杯盖", "盖子", "清洗", "拆洗", "清洁", "缝隙", "密封圈"}), None),
    ("价格价值", frozenset({"价格", "贵", "便宜", "199", "性价比", "值", "定价"}), None),
    ("外观颜色", frozenset({"颜色", "外观", "好看", "丑", "配色", "青色", "蓝绿", "颜值"}), None),
    ("质量耐用", frozenset({"坏了", "断裂", "掉漆", "变形", "破损", "质量", "耐用", "划痕"}), None),
    ("安全健康", frozenset({
        "安全", "异味", "有毒", "烫伤", "漏水", "食品接触", "材质",
        "304", "316", "不锈钢", "发霉",
    }), "食品接触材料报告尚未提供，相关结论需以检测报告为准"),
    ("防水性能", frozenset({"防水", "进水", "泡水", "淋水"}), "防水等级尚未提供，需向产品/工程团队确认"),
    ("物流包装", frozenset({"快递", "包装", "物流", "发货", "到货", "配送"}), None),
]

THEME_FALLBACK = "其他"

# 优先级频次阈值（P0 由严重度关键词触发，不受频次限制）
P1_MIN_COUNT = 3
P2_MIN_COUNT = 2

# 下一步行动映射：priority -> theme -> actions
NEXT_ACTIONS: dict[str, dict[str, list[str]]] = {
    "P0": {
        "default": ["立即组织工程/质量团队复盘", "24小时内给出初步处理方案", "联系反馈用户跟进具体情况"],
        "安全健康": ["暂停涉及材质安全的宣传话术", "优先获取食品接触材料报告", "联系反馈用户跟进具体情况"],
        "防水性能": ["暂停防水相关宣传", "向工程团队确认防水等级", "获取检测报告后再对外沟通"],
    },
    "P1": {
        "default": ["纳入本周迭代评审", "指定负责人跟进", "补充样本量后确认是否为普遍问题"],
    },
    "P2": {
        "default": ["纳入需求池观察", "持续收集同类反馈", "下个迭代评估是否处理"],
    },
    "P3": {
        "default": ["记录并持续观察", "暂不安排专项行动"],
    },
}

# 来自 product_brief.md「不完整信息」的全局待补项
PENDING_ITEMS: list[str] = [
    "首发日期尚未确定",
    "防水等级尚未提供",
    "食品接触材料报告尚未提供",
]


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FeedbackItem:
    """单条用户反馈（不可变值对象）。"""
    id: str
    text: str
    source: str | None = None
    timestamp: str | None = None


@dataclass
class ThemeResult:
    """一个去重后的主题及其分析结果。"""
    theme: str
    priority: str
    count: int
    feedback_ids: list[str] = field(default_factory=list)
    sample_texts: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    is_conclusion: bool = True
    note: str | None = None


# ---------------------------------------------------------------------------
# 核心逻辑
# ---------------------------------------------------------------------------

def normalize_text(text: str) -> str:
    """文本归一化：去首尾空白、压缩连续空白、转小写（用于精确去重）。"""
    return re.sub(r"\s+", " ", text.strip()).lower()


def match_themes(text: str) -> list[str]:
    """根据关键词匹配主题，返回命中的主题名列表；无命中则回退到「其他」。"""
    matched = [
        name
        for name, keywords, _ in THEME_DEFINITIONS
        if any(kw in text for kw in keywords)
    ]
    return matched if matched else [THEME_FALLBACK]


def has_high_severity(text: str) -> bool:
    """判断文本是否包含高严重度关键词。"""
    return any(kw in text for kw in SEVERITY_HIGH_KEYWORDS)


def determine_priority(count: int, severity: bool) -> str:
    """根据严重度和频次确定优先级：P0 > P1 > P2 > P3。"""
    if severity:
        return "P0"
    if count >= P1_MIN_COUNT:
        return "P1"
    if count >= P2_MIN_COUNT:
        return "P2"
    return "P3"


def get_next_actions(priority: str, theme: str) -> list[str]:
    """按优先级和主题获取下一步行动；主题无专属方案时使用 default。"""
    priority_map = NEXT_ACTIONS.get(priority, {})
    specific = priority_map.get(theme)
    if specific:
        return list(specific)
    return list(priority_map.get("default", []))


def analyze(feedback: list[FeedbackItem]) -> dict:
    """
    核心分析流程：
    1. 文本归一化后精确去重（相同文本合并，保留全部 ID）
    2. 关键词匹配主题（一条反馈可命中多个主题）
    3. 按主题分组，计算优先级与下一步行动
    4. 结论与假设分开标注
    """
    # 精确去重：归一化后文本相同的反馈合并为一组
    dedup_map: dict[str, list[FeedbackItem]] = defaultdict(list)
    for item in feedback:
        dedup_map[normalize_text(item.text)].append(item)

    # 主题 -> 反馈列表
    theme_groups: dict[str, list[FeedbackItem]] = defaultdict(list)
    theme_notes: dict[str, str] = {}

    for items in dedup_map.values():
        original_text = items[0].text
        for theme in match_themes(original_text):
            theme_groups[theme].extend(items)
            for name, _, pending_note in THEME_DEFINITIONS:
                if name == theme and pending_note:
                    theme_notes[theme] = pending_note

    results: list[ThemeResult] = []
    for theme, items in theme_groups.items():
        count = len(items)
        severity = any(has_high_severity(item.text) for item in items)
        priority = determine_priority(count, severity)
        actions = get_next_actions(priority, theme)

        # 安全健康主题：仅当反馈确实涉及材质/食品接触关键词时，才使用材质安全专项行动；
        # 纯漏水等密封质量问题走 P0 默认行动
        if theme == "安全健康" and priority == "P0":
            material_keywords = {"食品接触", "材质", "304", "316", "不锈钢", "有毒", "异味"}
            if not any(any(kw in item.text for kw in material_keywords) for item in items):
                actions = get_next_actions(priority, "default")

        is_conclusion = theme != THEME_FALLBACK
        note = theme_notes.get(theme)
        if theme == THEME_FALLBACK:
            note = "未命中预定义主题关键词，需人工复核分类"
            actions = ["人工复核该组反馈并补充主题关键词"]

        results.append(ThemeResult(
            theme=theme,
            priority=priority,
            count=count,
            feedback_ids=[item.id for item in items],
            sample_texts=[item.text for item in items[:3]],
            next_actions=actions,
            is_conclusion=is_conclusion,
            note=note,
        ))

    # 按优先级升序（P0 在前），同优先级按频次降序
    priority_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    results.sort(key=lambda r: (priority_order[r.priority], -r.count))

    total_raw = len(feedback)
    total_unique = len(dedup_map)

    return {
        "summary": {
            "total_feedback": total_raw,
            "unique_feedback": total_unique,
            "duplicates_removed": total_raw - total_unique,
            "theme_count": len(results),
        },
        "themes": [
            {
                "theme": r.theme,
                "priority": r.priority,
                "count": r.count,
                "feedback_ids": r.feedback_ids,
                "sample_texts": r.sample_texts,
                "next_actions": r.next_actions,
                "结论_假设": "结论" if r.is_conclusion else "待人工确认",
                "note": r.note,
            }
            for r in results
        ],
        "pending_items": PENDING_ITEMS,
    }


# ---------------------------------------------------------------------------
# 输入加载
# ---------------------------------------------------------------------------

def load_feedback(raw: object) -> list[FeedbackItem]:
    """
    从解析后的 JSON 对象加载反馈列表。

    支持两种顶层格式：
    1. {"feedback": [{"id": "...", "text": "..."}, ...]}
    2. [{"id": "...", "text": "..."}, ...]
    """
    if isinstance(raw, dict):
        items_raw = raw.get("feedback", [])
    elif isinstance(raw, list):
        items_raw = raw
    else:
        raise InputError("输入 JSON 顶层必须是对象（含 feedback 字段）或数组")

    if not isinstance(items_raw, list):
        raise InputError("feedback 字段必须是数组")

    items: list[FeedbackItem] = []
    seen_ids: set[str] = set()
    for i, entry in enumerate(items_raw):
        if not isinstance(entry, dict):
            raise InputError(f"第 {i + 1} 条反馈不是 JSON 对象")
        text = entry.get("text")
        if not isinstance(text, str) or not text.strip():
            raise InputError(f"第 {i + 1} 条反馈缺少有效的 text 字段")
        fb_id = entry.get("id") or f"auto-{i + 1}"
        if not isinstance(fb_id, str):
            fb_id = str(fb_id)
        if fb_id in seen_ids:
            raise InputError(f"反馈 ID 重复：{fb_id}")
        seen_ids.add(fb_id)
        items.append(FeedbackItem(
            id=fb_id,
            text=text.strip(),
            source=entry.get("source") if isinstance(entry.get("source"), str) else None,
            timestamp=entry.get("timestamp") if isinstance(entry.get("timestamp"), str) else None,
        ))

    if not items:
        raise InputError("反馈列表为空，至少需要一条有效反馈")

    return items


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------

def read_input(path: Path | None) -> object:
    """从文件或 stdin 读取并解析 JSON。"""
    if path is not None:
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            raise InputError(f"输入文件不存在：{path}")
        except OSError as e:
            raise InputError(f"无法读取输入文件：{e}")
    else:
        text = sys.stdin.read()

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise InputError(f"输入不是合法 JSON：{e}")


def write_output(data: dict, path: Path | None) -> None:
    """输出 JSON 到文件或 stdout（UTF-8、保留中文）。"""
    content = json.dumps(data, ensure_ascii=False, indent=2)
    if path is not None:
        path.write_text(content + "\n", encoding="utf-8")
        logger.info("结果已写入 %s", path)
    else:
        sys.stdout.write(content + "\n")


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="用户反馈主题分析工作流：去重主题、优先级、下一步行动",
    )
    parser.add_argument("--input", "-i", type=Path, default=None,
                        help="输入 JSON 文件路径（默认从 stdin 读取）")
    parser.add_argument("--output", "-o", type=Path, default=None,
                        help="输出 JSON 文件路径（默认输出到 stdout）")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="输出调试级别日志")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    try:
        raw = read_input(args.input)
        feedback = load_feedback(raw)
        result = analyze(feedback)
        write_output(result, args.output)
    except InputError as e:
        logger.error("输入错误：%s", e)
        return 1
    except Exception:
        logger.exception("未预期的内部错误")
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
