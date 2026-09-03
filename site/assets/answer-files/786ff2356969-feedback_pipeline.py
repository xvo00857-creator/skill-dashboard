#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户反馈主题去重与优先级工作流（最小可用版）

输入：用户反馈 JSON（文件或 stdin）
输出：去重后的主题、优先级、下一步行动（JSON）

依赖：仅 Python 3.8+ 标准库，无需 pip 安装。

注意：本脚本为本地处理层。从 2chat 拉取真实反馈需 Rube MCP
（RUBE_SEARCH_TOOLS / RUBE_MANAGE_CONNECTIONS / RUBE_MULTI_EXECUTE_TOOL），
当前环境未连接该 MCP，数据拉取步骤为阻塞项，详见 README.md。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from typing import Any

# ---------------------------------------------------------------------------
# 1. 主题定义：基于 product_brief.md 的产品维度
#    每个主题含关键词、是否核心卖点、默认下一步行动模板
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ThemeSpec:
    key: str
    label: str
    keywords: tuple[str, ...]
    is_core_selling_point: bool = False
    default_action: str = ""


THEME_SPECS: tuple[ThemeSpec, ...] = (
    ThemeSpec(
        key="insulation",
        label="保温性能",
        keywords=("保温", "保冷", "温度", "凉了", "不热", "12小时", "十二小时", "烫", "热", "冰"),
        is_core_selling_point=True,
        default_action="核实保温时长实测数据；若与12小时宣传不符，转研发复测并更新FAQ",
    ),
    ThemeSpec(
        key="weight",
        label="重量与便携",
        keywords=("轻", "重", "280g", "280克", "便携", "随身", "通勤", "重量", "携带", "轻便"),
        is_core_selling_point=True,
        default_action="确认称重规格与标注一致；收集通勤场景便携性反馈用于详情页优化",
    ),
    ThemeSpec(
        key="lid_cleaning",
        label="杯盖与拆洗",
        keywords=("杯盖", "拆洗", "清洗", "清洁", "死角", "密封圈", "盖子", "拆不开", "组装"),
        is_core_selling_point=True,
        default_action="检查可拆洗结构是否存在清洁死角；必要时补充清洗指引图文",
    ),
    ThemeSpec(
        key="leak_seal",
        label="漏水与密封",
        keywords=("漏水", "渗水", "洒", "溢", "滴水", "封不严", "密封不好", "密封差", "不密封"),
        is_core_selling_point=False,
        default_action="排查密封圈装配与杯盖旋合结构；漏水属安全相关，优先安排复测",
    ),
    ThemeSpec(
        key="material_safety",
        label="材质与安全",
        keywords=("材质", "塑料", "味道", "异味", "食品级", "安全", "报告", "有味", "气味", "BPA"),
        is_core_selling_point=False,
        default_action="食品接触材料报告尚未提供（见简报不完整信息），列为待补项；异味问题转品控",
    ),
    ThemeSpec(
        key="waterproof",
        label="防水等级",
        keywords=("防水", "水洗", "浸泡", "淋", "IPX", "泡水"),
        is_core_selling_point=False,
        default_action="防水等级尚未提供（见简报不完整信息），列为待补项；勿在物料中承诺防水等级",
    ),
    ThemeSpec(
        key="price_value",
        label="价格与性价比",
        keywords=("价格", "贵", "便宜", "199", "性价比", "值得", "不值", "划算", "定价", "降价"),
        is_core_selling_point=False,
        default_action="汇总价格敏感度反馈；禁止编造竞品价格，如需对比须走外部数据采集流程",
    ),
    ThemeSpec(
        key="appearance",
        label="外观与颜色",
        keywords=("外观", "颜色", "好看", "颜值", "配色", "丑", "质感", "漆面", "造型"),
        is_core_selling_point=False,
        default_action="汇总外观偏好反馈；品牌主色 #176B87 相关建议转设计评估",
    ),
    ThemeSpec(
        key="capacity",
        label="容量",
        keywords=("容量", "装多少", "ml", "毫升", "大小", "不够喝", "装水"),
        is_core_selling_point=False,
        default_action="记录容量需求分布，作为后续SKU规划参考",
    ),
)

THEME_FALLBACK = ThemeSpec(
    key="other",
    label="其他",
    keywords=(),
    is_core_selling_point=False,
    default_action="人工复核归类",
)

# ---------------------------------------------------------------------------
# 2. 严重度关键词：命中则提升优先级
# ---------------------------------------------------------------------------

SEVERITY_KEYWORDS: tuple[str, ...] = (
    "漏水", "烫伤", "异味", "退货", "退款", "投诉", "安全", "坏了",
    "破损", "碎了", "割手", "过敏", "有毒", "不敢用", "差评",
)

# 负面情绪词（用于核心卖点主题的优先级判断）
NEGATIVE_KEYWORDS: tuple[str, ...] = (
    "不行", "不好", "不够", "不达", "不符", "太差", "差太", "差劲", "失望",
    "问题", "故障", "退货", "退款", "投诉", "坏了", "漏水", "渗水",
    "费劲", "容易掉", "麻烦", "鸡肋", "踩雷", "名不副实", "虚假",
    "别买", "后悔", "割手", "异味", "有味",
)

# ---------------------------------------------------------------------------
# 3. 去重：字符二元组 Jaccard 相似度
# ---------------------------------------------------------------------------

def _char_bigrams(text: str) -> set[str]:
    text = re.sub(r"\s+", "", text)
    if len(text) < 2:
        return {text} if text else set()
    return {text[i : i + 2] for i in range(len(text) - 1)}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def _overlap_coef(a: set[str], b: set[str]) -> float:
    """交集占较小集合的比例，用于检测一条是另一条子集式复述。"""
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


DEDUP_JACCARD_THRESHOLD = 0.5
DEDUP_OVERLAP_THRESHOLD = 0.65
DEDUP_MIN_BIGRAMS_FOR_OVERLAP = 8  # 较短文本至少 8 个二元组才启用重叠判据


def _is_duplicate(a: set[str], b: set[str]) -> bool:
    j = _jaccard(a, b)
    if j >= DEDUP_JACCARD_THRESHOLD:
        return True
    if min(len(a), len(b)) >= DEDUP_MIN_BIGRAMS_FOR_OVERLAP:
        return _overlap_coef(a, b) >= DEDUP_OVERLAP_THRESHOLD
    return False

# ---------------------------------------------------------------------------
# 4. 数据结构
# ---------------------------------------------------------------------------

@dataclass
class FeedbackItem:
    id: str
    content: str
    source: str = ""
    timestamp: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class DedupeGroup:
    representative_id: str
    representative_content: str
    member_ids: list[str]
    member_contents_preview: list[str]


@dataclass
class ThemeResult:
    theme_key: str
    theme_label: str
    is_core_selling_point: bool
    raw_feedback_count: int
    deduped_group_count: int
    priority: str
    priority_score: int
    priority_reasons: list[str]
    severity_hits: list[str]
    next_actions: list[str]
    deduped_groups: list[dict[str, Any]]
    source_feedback_ids: list[str]


# ---------------------------------------------------------------------------
# 5. 输入校验
# ---------------------------------------------------------------------------

class InputError(Exception):
    """输入格式错误，退出码 1"""


def parse_input(raw: str) -> list[FeedbackItem]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise InputError(f"输入不是合法 JSON：{e}") from e

    if isinstance(data, dict):
        # 允许 {"feedback": [...]} 或 {"items": [...]} 包裹
        for key in ("feedback", "items", "data"):
            if key in data and isinstance(data[key], list):
                data = data[key]
                break
        else:
            raise InputError("JSON 对象需包含 feedback/items/data 数组字段")

    if not isinstance(data, list):
        raise InputError("输入需为反馈数组或含数组字段的对象")

    items: list[FeedbackItem] = []
    seen_ids: set[str] = set()
    for idx, entry in enumerate(data):
        if not isinstance(entry, dict):
            raise InputError(f"第 {idx + 1} 条不是对象")
        content = entry.get("content") or entry.get("text") or entry.get("message")
        if not content or not isinstance(content, str):
            raise InputError(f"第 {idx + 1} 条缺少 content/text/message 文本字段")
        content = content.strip()
        if not content:
            raise InputError(f"第 {idx + 1} 条内容为空")

        fb_id = entry.get("id")
        if fb_id is None or str(fb_id).strip() == "":
            fb_id = f"auto-{idx + 1}"
        fb_id = str(fb_id)
        if fb_id in seen_ids:
            raise InputError(f"反馈 id 重复：{fb_id}")
        seen_ids.add(fb_id)

        items.append(
            FeedbackItem(
                id=fb_id,
                content=content,
                source=str(entry.get("source", "") or ""),
                timestamp=str(entry.get("timestamp", "") or ""),
                extra={
                    k: v
                    for k, v in entry.items()
                    if k not in ("id", "content", "text", "message", "source", "timestamp")
                },
            )
        )

    if not items:
        raise InputError("反馈数组为空")

    return items


# ---------------------------------------------------------------------------
# 6. 主题归类
# ---------------------------------------------------------------------------

def classify_theme(content: str) -> list[ThemeSpec]:
    """返回命中的主题列表（一条反馈可命中多个主题）。"""
    matched = [spec for spec in THEME_SPECS if any(kw in content for kw in spec.keywords)]
    return matched if matched else [THEME_FALLBACK]


# ---------------------------------------------------------------------------
# 7. 去重
# ---------------------------------------------------------------------------

def dedupe_feedback(items: list[FeedbackItem]) -> list[DedupeGroup]:
    groups: list[DedupeGroup] = []
    used = [False] * len(items)
    bigrams = [_char_bigrams(it.content) for it in items]

    for i, item in enumerate(items):
        if used[i]:
            continue
        group_indices = [i]
        used[i] = True
        for j in range(i + 1, len(items)):
            if used[j]:
                continue
            if _is_duplicate(bigrams[i], bigrams[j]):
                group_indices.append(j)
                used[j] = True
        members = [items[k] for k in group_indices]
        groups.append(
            DedupeGroup(
                representative_id=members[0].id,
                representative_content=members[0].content,
                member_ids=[m.id for m in members],
                member_contents_preview=[m.content for m in members],
            )
        )
    return groups


# ---------------------------------------------------------------------------
# 8. 优先级评分
# ---------------------------------------------------------------------------

def score_priority(
    spec: ThemeSpec,
    items: list[FeedbackItem],
    deduped_count: int,
) -> tuple[str, int, list[str], list[str]]:
    score = 0
    reasons: list[str] = []
    severity_hits: list[str] = []

    # 去重后反馈组数（独立问题数）
    score += deduped_count * 2
    if deduped_count >= 3:
        reasons.append(f"去重后仍有 {deduped_count} 组独立反馈，频次较高")
    elif deduped_count >= 1:
        reasons.append(f"去重后 {deduped_count} 组反馈")

    # 原始反馈量
    if len(items) >= 5:
        score += 3
        reasons.append(f"原始反馈量 {len(items)} 条，关注度高")

    # 严重度关键词
    for it in items:
        for kw in SEVERITY_KEYWORDS:
            if kw in it.content and kw not in severity_hits:
                severity_hits.append(kw)
    if severity_hits:
        score += 8
        reasons.append(f"命中严重度关键词：{'、'.join(severity_hits)}")

    # 核心卖点 + 负面情绪
    if spec.is_core_selling_point:
        neg_count = sum(
            1
            for it in items
            if any(nw in it.content for nw in NEGATIVE_KEYWORDS)
        )
        if neg_count > 0:
            score += 4
            reasons.append(
                f"涉及核心卖点「{spec.label}」且 {neg_count} 条含负面表述"
            )
        else:
            reasons.append(f"涉及核心卖点「{spec.label}」")

    # 定级
    if score >= 10 or severity_hits:
        priority = "P0"
    elif score >= 5:
        priority = "P1"
    else:
        priority = "P2"

    return priority, score, reasons, severity_hits


# ---------------------------------------------------------------------------
# 9. 下一步行动生成
# ---------------------------------------------------------------------------

def build_next_actions(
    spec: ThemeSpec,
    items: list[FeedbackItem],
    severity_hits: list[str],
) -> list[str]:
    actions: list[str] = [spec.default_action]

    if spec.key == "material_safety":
        actions.append("待补项：食品接触材料报告（product_brief.md 明确尚未提供）")
    if spec.key == "waterproof":
        actions.append("待补项：防水等级（product_brief.md 明确尚未提供）")
    if spec.key == "price_value":
        actions.append("待补项：如需竞品价格对比，须走外部数据采集，禁止编造")
    if "漏水" in severity_hits:
        actions.append("安全相关：48小时内安排密封复测并同步客服话术")
    if "异味" in severity_hits:
        actions.append("安全相关：留样送检并暂停相关批次发货建议")

    # 去重保持顺序
    seen: set[str] = set()
    unique = []
    for a in actions:
        if a not in seen:
            seen.add(a)
            unique.append(a)
    return unique


# ---------------------------------------------------------------------------
# 10. 主流程
# ---------------------------------------------------------------------------

def run_pipeline(items: list[FeedbackItem]) -> dict[str, Any]:
    # 按主题分组
    theme_to_items: dict[str, list[FeedbackItem]] = defaultdict(list)
    theme_spec_map: dict[str, ThemeSpec] = {}
    for item in items:
        for spec in classify_theme(item.content):
            theme_to_items[spec.key].append(item)
            theme_spec_map[spec.key] = spec

    results: list[ThemeResult] = []
    for key, theme_items in theme_to_items.items():
        spec = theme_spec_map[key]
        groups = dedupe_feedback(theme_items)
        priority, score, reasons, severity_hits = score_priority(
            spec, theme_items, len(groups)
        )
        actions = build_next_actions(spec, theme_items, severity_hits)
        results.append(
            ThemeResult(
                theme_key=key,
                theme_label=spec.label,
                is_core_selling_point=spec.is_core_selling_point,
                raw_feedback_count=len(theme_items),
                deduped_group_count=len(groups),
                priority=priority,
                priority_score=score,
                priority_reasons=reasons,
                severity_hits=severity_hits,
                next_actions=actions,
                deduped_groups=[asdict(g) for g in groups],
                source_feedback_ids=[it.id for it in theme_items],
            )
        )

    # 按优先级排序 P0 > P1 > P2，同级按分数降序
    priority_order = {"P0": 0, "P1": 1, "P2": 2}
    results.sort(key=lambda r: (priority_order[r.priority], -r.priority_score))

    return {
        "meta": {
            "total_feedback": len(items),
            "total_themes": len(results),
            "dedup_jaccard_threshold": DEDUP_JACCARD_THRESHOLD,
            "dedup_overlap_threshold": DEDUP_OVERLAP_THRESHOLD,
            "pipeline_version": "0.1.0",
            "note": "本地处理层结果；2chat真实反馈拉取需Rube MCP，当前环境未连接",
        },
        "themes": [asdict(r) for r in results],
    }


# ---------------------------------------------------------------------------
# 11. CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="用户反馈主题去重与优先级工作流",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  python3 feedback_pipeline.py -i feedback.json\n"
            "  cat feedback.json | python3 feedback_pipeline.py\n"
            "  python3 feedback_pipeline.py -i feedback.json -o result.json\n"
        ),
    )
    parser.add_argument("-i", "--input", help="输入 JSON 文件路径（缺省读 stdin）")
    parser.add_argument("-o", "--output", help="输出 JSON 文件路径（缺省写 stdout）")
    parser.add_argument(
        "--pretty", action="store_true", default=True, help="格式化输出 JSON（默认开启）"
    )
    args = parser.parse_args(argv)

    # 读取输入
    try:
        if args.input:
            with open(args.input, "r", encoding="utf-8") as f:
                raw = f.read()
        else:
            if sys.stdin.isatty():
                print("错误：未指定 -i 且 stdin 无数据", file=sys.stderr)
                return 1
            raw = sys.stdin.read()
    except OSError as e:
        print(f"错误：无法读取输入文件：{e}", file=sys.stderr)
        return 1

    # 解析
    try:
        items = parse_input(raw)
    except InputError as e:
        print(f"输入错误：{e}", file=sys.stderr)
        return 1

    # 处理
    try:
        result = run_pipeline(items)
    except Exception as e:  # noqa: BLE001
        print(f"处理错误：{type(e).__name__}: {e}", file=sys.stderr)
        return 2

    # 输出
    indent = 2 if args.pretty else None
    out_str = json.dumps(result, ensure_ascii=False, indent=indent)
    try:
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(out_str)
                f.write("\n")
            print(f"已写入 {args.output}", file=sys.stderr)
        else:
            sys.stdout.write(out_str + "\n")
    except OSError as e:
        print(f"错误：无法写入输出文件：{e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
