#!/usr/bin/env python3
"""
数据准备流水线（对应 SKILL.md 第 1 步与 references/dataset-preparation.md）。

流程：加载原始 JSONL -> 校验 -> 质量过滤 -> 精确/模糊去重 -> 切分 -> 落盘
输出：train.jsonl / val.jsonl / test.jsonl（若配置 test_size>0）

用法：
    python src/prepare_data.py --config configs/experiment_config.yaml \
        --raw data/raw/train.jsonl

注意：
- 本脚本只处理本地 JSONL；HuggingFace 数据集请先下载/转换为 JSONL 再传入。
- 模糊去重依赖 datasketch；未安装时自动跳过并警告，不伪造去重结果。
- 所有随机操作固定 seed（来自配置），保证可复现。
"""
import argparse
import json
import random
import re
import sys
from pathlib import Path

import yaml

# 复用 validate_dataset 中的逻辑
sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_dataset import get_io_text, load_tokenizer, BAD_PATTERNS  # noqa: E402


def load_raw(path: Path):
    data = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                data.append(json.loads(line))
    return data


def quality_filter(ex, tokenizer, cfg):
    """返回 True 表示保留。长度按 tokenizer（若有）否则按字符。"""
    inp, out = get_io_text(ex)
    if not inp or not out:
        return False
    if tokenizer is not None:
        ilen = len(tokenizer.encode(inp))
        olen = len(tokenizer.encode(out))
        max_total = cfg["data"]["max_total_tokens"]
        if ilen + olen > max_total:
            return False
    min_in = cfg["data"]["min_input_tokens"]
    max_in = cfg["data"]["max_input_tokens"]
    min_out = cfg["data"]["min_output_tokens"]
    max_out = cfg["data"]["max_output_tokens"]
    if tokenizer is None:
        # 字符回退：粗略按 1 token≈3 字符换算，仅用于粗筛
        ilen, olen = len(inp), len(out)
        min_in, max_in = min_in * 3, max_in * 3
        min_out, max_out = min_out * 3, max_out * 3
    if not (min_in <= ilen <= max_in and min_out <= olen <= max_out):
        return False
    for pat in BAD_PATTERNS:
        if re.search(pat, out, re.IGNORECASE):
            return False
    return True


def exact_dedup(examples, key="instruction"):
    seen, unique = set(), []
    for ex in examples:
        if "instruction" in ex:
            k = ex.get("instruction", "")
        else:
            k = " ".join(m.get("content", "") for m in ex.get("messages", []) if m.get("role") == "user")
        if k not in seen:
            seen.add(k)
            unique.append(ex)
    return unique


def fuzzy_dedup(examples, threshold=0.85, num_perm=128):
    """按 output 做 MinHash 近似去重；datasketch 缺失时返回原列表并警告。"""
    try:
        from datasketch import MinHash, MinHashLSH
    except ImportError:
        print("[警告] 未安装 datasketch，跳过模糊去重。请 `pip install datasketch` 后重跑。",
              file=sys.stderr)
        return examples

    lsh = MinHashLSH(threshold=threshold, num_perm=num_perm)
    unique = []
    for i, ex in enumerate(examples):
        _, out = get_io_text(ex)
        words = (out or "").lower().split()
        m = MinHash(num_perm=num_perm)
        for w in words:
            m.update(w.encode("utf-8"))
        if not lsh.query(m):
            lsh.insert(str(i), m)
            unique.append(ex)
    return unique


def split_data(examples, val_size, test_size, seed, stratify_field=None):
    random.seed(seed)
    shuffled = examples[:]
    random.shuffle(shuffled)
    n = len(shuffled)
    n_test = int(n * test_size) if test_size else 0
    n_val = int(n * val_size)
    test = shuffled[:n_test]
    val = shuffled[n_test:n_test + n_val]
    train = shuffled[n_test + n_val:]
    return train, val, test


def save_jsonl(examples, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--raw", required=True, help="原始 JSONL 文件")
    args = ap.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    seed = cfg["experiment"]["seed"]
    out_dir = Path(cfg["data"]["output_dir"])
    raw_path = Path(args.raw)
    if not raw_path.exists():
        print(f"[错误] 原始文件不存在: {raw_path}", file=sys.stderr)
        sys.exit(2)

    tokenizer = load_tokenizer(cfg["model"]["name"])

    print(f"[1/5] 加载原始数据: {raw_path}")
    data = load_raw(raw_path)
    print(f"      原始样本数: {len(data)}")

    print("[2/5] 质量过滤（长度/空字段/拒答模板）")
    filtered = [ex for ex in data if quality_filter(ex, tokenizer, cfg)]
    print(f"      过滤后: {len(filtered)}（剔除 {len(data) - len(filtered)}）")

    print("[3/5] 去重：先精确（输入）后模糊（输出）")
    filtered = exact_dedup(filtered)
    print(f"      精确去重后: {len(filtered)}")
    before = len(filtered)
    filtered = fuzzy_dedup(filtered, threshold=cfg["data"]["fuzzy_dedup_threshold"])
    print(f"      模糊去重后: {len(filtered)}（剔除 {before - len(filtered)}）")

    if len(filtered) < 100:
        print(f"[警告] 清洗后仅 {len(filtered)} 条，低于 Skill 建议的指令任务下限（1000）。"
              f"两周内可继续，但结论可推广性有限，需在报告中说明。", file=sys.stderr)

    print("[4/5] 切分 train/val/test")
    train, val, test = split_data(
        filtered,
        val_size=cfg["data"]["val_size"],
        test_size=cfg["data"]["test_size"],
        seed=seed,
        stratify_field=cfg["data"].get("stratify_field"),
    )
    print(f"      train={len(train)} val={len(val)} test={len(test)}")

    print("[5/5] 落盘")
    save_jsonl(train, out_dir / "train.jsonl")
    save_jsonl(val, out_dir / "val.jsonl")
    if test:
        save_jsonl(test, out_dir / "test.jsonl")
    else:
        print("      test_size=0，未生成 test.jsonl；请确保使用数据集自带的独立测试集。")

    # 记录数据版本信息（用于可复现性，不含数据内容本身）
    meta = {
        "raw_file": str(raw_path),
        "raw_count": len(data),
        "after_filter": len(filtered),
        "train": len(train), "val": len(val), "test": len(test),
        "seed": seed,
        "length_estimation": "tokens" if tokenizer else "chars(fallback)",
    }
    with open(out_dir / "data_meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"完成。元信息: {out_dir / 'data_meta.json'}")


if __name__ == "__main__":
    main()
