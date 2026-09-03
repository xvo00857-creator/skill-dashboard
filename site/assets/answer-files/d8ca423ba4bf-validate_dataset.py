#!/usr/bin/env python3
"""
数据校验脚本（对应 SKILL.md 第 1 步 checkpoint）。

用法：
    python src/validate_dataset.py --input data/raw/train.jsonl
    python src/validate_dataset.py --input data/raw/train.jsonl --model TBD_BASE_MODEL --histogram

退出码：
    0 = 无 error（可能有 warning）
    1 = 存在 error（缺字段、空字段、长度超限等），必须修复后才能进入训练

注意：本脚本不联网、不训练；tokenizer 若无法加载（模型未确认/未下载），
会回退到按字符估算长度并明确提示，不伪造 token 统计。
"""
import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional


# 中文数据常见的拒答/占位模式；与 Skill 参考中的英文模式合并使用
BAD_PATTERNS = [
    r"I cannot", r"I'm sorry, but", r"As an AI", r"I don't have access",
    r"我无法", r"抱歉，?我(是|作为)?(一个)?(AI|人工智能|语言模型)", r"我不能(提供|协助)",
]


@dataclass
class DatasetStats:
    total_examples: int = 0
    avg_input_chars: float = 0.0
    avg_output_chars: float = 0.0
    max_input_chars: int = 0
    max_output_chars: int = 0
    empty_inputs: int = 0
    empty_outputs: int = 0
    duplicate_inputs: int = 0
    format_errors: int = 0
    quality_flagged: int = 0
    length_estimation: str = "chars"  # "tokens" 或 "chars"（回退）


def load_jsonl(path: Path):
    examples = []
    with path.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                examples.append(json.loads(line))
            except json.JSONDecodeError as e:
                examples.append({"__parse_error__": str(e), "__lineno__": lineno})
    return examples


def get_io_text(ex: dict):
    """统一抽取 input/output 文本，支持 Alpaca 与 messages 两种格式。"""
    if "instruction" in ex:
        inp = f"{ex.get('instruction', '')} {ex.get('input', '')}".strip()
        out = str(ex.get("output", "")).strip()
        return inp, out
    if "messages" in ex:
        msgs = ex["messages"]
        inp = " ".join(m.get("content", "") for m in msgs if m.get("role") == "user").strip()
        out = " ".join(m.get("content", "") for m in msgs if m.get("role") == "assistant").strip()
        return inp, out
    return None, None


def load_tokenizer(model_name: Optional[str]):
    """尝试加载 tokenizer；失败则返回 None，调用方回退到字符估算。"""
    if not model_name or model_name.startswith("TBD"):
        return None
    try:
        from transformers import AutoTokenizer
        tok = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        if tok.pad_token is None:
            tok.pad_token = tok.eos_token
        return tok
    except Exception as e:  # noqa: BLE001
        print(f"[警告] 无法加载 tokenizer({model_name}): {e}\n"
              f"       回退为按字符数估算长度（非真实 token 数）。", file=sys.stderr)
        return None


def validate(examples, tokenizer=None, max_total_tokens: int = 4096):
    stats = DatasetStats()
    errors, warnings = [], []
    input_lens, output_lens = [], []
    seen_inputs = set()

    for i, ex in enumerate(examples):
        if "__parse_error__" in ex:
            stats.format_errors += 1
            errors.append(f"第 {ex['__lineno__']} 行 JSON 解析失败: {ex['__parse_error__']}")
            continue

        inp, out = get_io_text(ex)
        if inp is None:
            stats.format_errors += 1
            errors.append(f"样本 {i}: 缺少 instruction/messages 字段")
            continue

        if not inp:
            stats.empty_inputs += 1
            errors.append(f"样本 {i}: 输入为空")
        if not out:
            stats.empty_outputs += 1
            errors.append(f"样本 {i}: 输出为空")

        # 长度统计：有 tokenizer 用 token，否则用字符
        if tokenizer is not None:
            ilen = len(tokenizer.encode(inp))
            olen = len(tokenizer.encode(out))
            stats.length_estimation = "tokens"
        else:
            ilen, olen = len(inp), len(out)
        input_lens.append(ilen)
        output_lens.append(olen)

        if tokenizer is not None and ilen + olen > max_total_tokens:
            errors.append(f"样本 {i}: 总长 {ilen + olen} 超过 {max_total_tokens} tokens")

        # 简单质量标记（拒答模板）
        import re
        flagged = False
        for pat in BAD_PATTERNS:
            if re.search(pat, out, re.IGNORECASE):
                flagged = True
                warnings.append(f"样本 {i}: 输出疑似拒答/占位模板（{pat}）")
                break
        if flagged:
            stats.quality_flagged += 1

        # 输入重复检测（精确）
        key = inp
        if key in seen_inputs:
            stats.duplicate_inputs += 1
            warnings.append(f"样本 {i}: 与更早样本输入重复")
        seen_inputs.add(key)

    n = len(input_lens) or 1
    stats.total_examples = len(examples)
    stats.avg_input_chars = sum(input_lens) / n
    stats.avg_output_chars = sum(output_lens) / n
    stats.max_input_chars = max(input_lens) if input_lens else 0
    stats.max_output_chars = max(output_lens) if output_lens else 0
    return stats, errors, warnings, input_lens, output_lens if tokenizer is None else (input_lens, output_lens)


def print_histogram(lengths, title, bins=10):
    if not lengths:
        return
    lo, hi = min(lengths), max(lengths)
    if hi == lo:
        print(f"  {title}: 全部为 {lo}")
        return
    step = (hi - lo) / bins
    counts = [0] * bins
    for x in lengths:
        idx = min(bins - 1, int((x - lo) / step))
        counts[idx] += 1
    print(f"  {title} 分布（长度单位见上）：")
    maxc = max(counts) or 1
    for b, c in enumerate(counts):
        left = int(lo + b * step)
        right = int(lo + (b + 1) * step)
        bar = "█" * int(c / maxc * 40)
        print(f"    {left:>6}-{right:<6} | {bar} {c}")


def main():
    ap = argparse.ArgumentParser(description="微调数据校验（fine-tuning-expert Skill）")
    ap.add_argument("--input", required=True, help="待校验 JSONL 文件路径")
    ap.add_argument("--model", default=None, help="用于 token 长度统计的模型名/路径（可选）")
    ap.add_argument("--max-total-tokens", type=int, default=4096)
    ap.add_argument("--histogram", action="store_true", help="打印长度分布直方图")
    ap.add_argument("--report", default=None, help="将统计结果写入 JSON 文件")
    args = ap.parse_args()

    path = Path(args.input)
    if not path.exists():
        print(f"[错误] 文件不存在: {path}", file=sys.stderr)
        sys.exit(2)

    examples = load_jsonl(path)
    tokenizer = load_tokenizer(args.model)
    stats, errors, warnings, in_lens, out_lens = validate(
        examples, tokenizer, args.max_total_tokens
    )

    print("=" * 60)
    print(f"文件: {path}")
    print(f"样本总数: {stats.total_examples}")
    print(f"长度统计方式: {stats.length_estimation}")
    print(f"平均输入长度: {stats.avg_input_chars:.1f}；最大输入长度: {stats.max_input_chars}")
    print(f"平均输出长度: {stats.avg_output_chars:.1f}；最大输出长度: {stats.max_output_chars}")
    print(f"空输入: {stats.empty_inputs}；空输出: {stats.empty_outputs}")
    print(f"重复输入: {stats.duplicate_inputs}；格式错误: {stats.format_errors}")
    print(f"疑似拒答/占位: {stats.quality_flagged}")
    print("=" * 60)

    if args.histogram:
        print_histogram(in_lens, "输入长度")
        print_histogram(out_lens, "输出长度")

    if warnings:
        print(f"\n[警告] 共 {len(warnings)} 条，前 10 条：")
        for w in warnings[:10]:
            print(f"  - {w}")
    if errors:
        print(f"\n[错误] 共 {len(errors)} 条，前 10 条：")
        for e in errors[:10]:
            print(f"  - {e}")
        print("\n结论：存在必须修复的错误，按 SKILL.md 要求修复前不得进入训练。")
    else:
        print("\n结论：无阻断性错误，可进入数据准备/训练流程（请同时处理警告）。")

    if args.report:
        with open(args.report, "w", encoding="utf-8") as f:
            json.dump({"stats": asdict(stats),
                       "errors_count": len(errors), "warnings_count": len(warnings),
                       "errors_sample": errors[:50], "warnings_sample": warnings[:50]},
                      f, ensure_ascii=False, indent=2)
        print(f"报告已写入: {args.report}")

    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
