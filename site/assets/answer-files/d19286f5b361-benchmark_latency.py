#!/usr/bin/env python3
"""
推理延迟与显存基准（对应 SKILL.md 第 4-5 步与 references/deployment-optimization.md）。

按 Skill 要求：先 warmup，再 benchmark，报告平均延迟、标准差、tokens/s、显存占用。
用于对比基础模型与微调（或合并/量化后）模型的推理性能。

用法：
    python src/benchmark_latency.py --config configs/experiment_config.yaml \
        --prompts data/prompts.txt [--adapter checkpoints/.../lora-adapter]

注意：本脚本未在本次环境运行，未产生任何实际延迟数字。
"""
import argparse
import json
import statistics
import sys
import time
from pathlib import Path

import yaml


def load_prompts(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def load_model(model_name, adapter_path=None, merged_path=None):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    if merged_path:
        tokenizer = AutoTokenizer.from_pretrained(merged_path, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(merged_path, torch_dtype=torch.bfloat16,
                                                     device_map="auto", trust_remote_code=True)
    else:
        tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=torch.bfloat16,
                                                     device_map="auto", trust_remote_code=True)
        if adapter_path:
            from peft import PeftModel
            model = PeftModel.from_pretrained(model, adapter_path)
    return model, tokenizer


def benchmark(model, tokenizer, prompts, max_new_tokens, warmup_runs, benchmark_runs):
    import torch
    model.eval()

    # 预热
    print(f"预热 {warmup_runs} 次...")
    for i in range(min(warmup_runs, len(prompts))):
        enc = tokenizer(prompts[i], return_tensors="pt").to(model.device)
        with torch.no_grad():
            model.generate(**enc, max_new_tokens=max_new_tokens, do_sample=False,
                           pad_token_id=tokenizer.pad_token_id)
    torch.cuda.synchronize()
    torch.cuda.empty_cache()

    latencies, n_tokens = [], []
    print(f"基准 {benchmark_runs} 次...")
    for prompt in prompts[:benchmark_runs]:
        enc = tokenizer(prompt, return_tensors="pt").to(model.device)
        input_len = enc["input_ids"].shape[1]
        torch.cuda.synchronize()
        t0 = time.perf_counter()
        with torch.no_grad():
            out = model.generate(**enc, max_new_tokens=max_new_tokens, do_sample=False,
                                 pad_token_id=tokenizer.pad_token_id)
        torch.cuda.synchronize()
        latencies.append(time.perf_counter() - t0)
        n_tokens.append(out.shape[1] - input_len)

    avg_lat = statistics.mean(latencies)
    avg_tok = statistics.mean(n_tokens)
    mem_alloc = torch.cuda.max_memory_allocated() / 1024 ** 3
    mem_res = torch.cuda.max_memory_reserved() / 1024 ** 3

    return {
        "avg_latency_ms": avg_lat * 1000,
        "latency_std_ms": statistics.stdev(latencies) * 1000 if len(latencies) > 1 else 0.0,
        "avg_tokens_per_second": avg_tok / avg_lat if avg_lat > 0 else 0.0,
        "requests_per_second": 1 / avg_lat if avg_lat > 0 else 0.0,
        "avg_new_tokens": avg_tok,
        "memory_allocated_gb": mem_alloc,
        "memory_reserved_gb": mem_res,
        "warmup_runs": warmup_runs,
        "benchmark_runs": len(latencies),
        "max_new_tokens": max_new_tokens,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--prompts", required=True, help="每行一个 prompt 的文本文件")
    ap.add_argument("--adapter", default=None)
    ap.add_argument("--merged", default=None, help="已合并模型目录（与 --adapter 二选一）")
    args = ap.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    if cfg["model"]["name"].startswith("TBD") and not args.merged:
        print("[错误] model.name 仍为 TBD，请先确认基础模型。", file=sys.stderr)
        sys.exit(2)

    prompts = load_prompts(Path(args.prompts))
    if not prompts:
        print("[错误] prompts 文件为空。", file=sys.stderr)
        sys.exit(2)

    model, tokenizer = load_model(cfg["model"]["name"], args.adapter, args.merged)
    metrics = benchmark(
        model, tokenizer, prompts,
        max_new_tokens=cfg["eval"]["max_new_tokens"],
        warmup_runs=cfg["eval"]["warmup_runs"],
        benchmark_runs=cfg["eval"]["benchmark_runs"],
    )
    metrics["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
    metrics["adapter"] = args.adapter
    metrics["merged"] = args.merged

    out_dir = Path(cfg["experiment"]["results_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"latency_{int(time.time())}.json"
    with out_file.open("w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)

    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    print(f"\n结果已保存: {out_file}")


if __name__ == "__main__":
    main()
