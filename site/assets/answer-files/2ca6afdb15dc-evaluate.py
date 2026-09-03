#!/usr/bin/env python3
"""
评估脚本（对应 SKILL.md 第 4 步与 references/evaluation-metrics.md）。

在同一测试集、同一解码配置下比较基础模型与 LoRA 微调模型：
  - 困惑度（perplexity，越低越好）
  - 任务指标：generation -> ROUGE / BLEU；classification -> Accuracy / F1
  - 结果写入 results/ 下带时间戳的 JSON，便于版本化对比

用法：
    python src/evaluate.py --config configs/experiment_config.yaml \
        --test data/processed/test.jsonl \
        --adapter checkpoints/qlora-instruct-2w-v1/lora-adapter

注意：
- 评估用贪心解码（do_sample=False），保证基线与微调可复现对比。
- 不报告延迟；延迟请用 benchmark_latency.py（含预热）。
- 本脚本未在本次环境运行，未产生任何实际指标。
"""
import argparse
import json
import math
import sys
import time
from pathlib import Path

import yaml
from tqdm import tqdm


def load_test_examples(path: Path):
    examples = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                examples.append(json.loads(line))
    return examples


def build_text(example, tokenizer, for_generation=False):
    """把样本拼成 prompt（输入）与 reference（期望输出）。"""
    if "messages" in example:
        msgs = example["messages"]
        user_msgs = [m for m in msgs if m["role"] == "user"]
        asst_msgs = [m for m in msgs if m["role"] == "assistant"]
        prompt_msgs = user_msgs  # 生成时只给 user 轮
        prompt = tokenizer.apply_chat_template(prompt_msgs, tokenize=False, add_generation_prompt=True)
        reference = asst_msgs[-1]["content"] if asst_msgs else ""
        full_text = tokenizer.apply_chat_template(msgs, tokenize=False)
        return prompt, reference, full_text
    inst = example.get("instruction", "")
    inp = example.get("input", "")
    reference = example.get("output", "")
    prompt = f"### Instruction:\n{inst}\n\n### Input:\n{inp}\n\n### Response:\n"
    full_text = prompt + reference
    return prompt, reference, full_text


def calculate_perplexity(model, tokenizer, texts, max_length=2048, batch_size=4):
    import torch
    model.eval()
    total_loss, total_tokens = 0.0, 0
    for i in tqdm(range(0, len(texts), batch_size), desc="perplexity"):
        batch = texts[i:i + batch_size]
        enc = tokenizer(batch, truncation=True, max_length=max_length,
                        padding=True, return_tensors="pt")
        input_ids = enc["input_ids"].to(model.device)
        attention_mask = enc["attention_mask"].to(model.device)
        with torch.no_grad():
            out = model(input_ids=input_ids, attention_mask=attention_mask, labels=input_ids)
        num_tokens = attention_mask.sum().item()
        total_loss += out.loss.item() * num_tokens
        total_tokens += num_tokens
    return math.exp(total_loss / total_tokens) if total_tokens else float("inf")


def generate_predictions(model, tokenizer, examples, max_new_tokens, do_sample):
    import torch
    preds, refs, inputs = [], [], []
    model.eval()
    for ex in tqdm(examples, desc="generating"):
        prompt, reference, _ = build_text(ex, tokenizer, for_generation=True)
        enc = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=2048).to(model.device)
        with torch.no_grad():
            out = model.generate(
                **enc,
                max_new_tokens=max_new_tokens,
                do_sample=do_sample,
                pad_token_id=tokenizer.pad_token_id,
            )
        gen = tokenizer.decode(out[0][enc["input_ids"].shape[1]:], skip_special_tokens=True).strip()
        preds.append(gen)
        refs.append(reference)
        inputs.append(prompt)
    return preds, refs, inputs


def eval_generation(preds, refs):
    from evaluate import load
    bleu = load("bleu")
    rouge = load("rouge")
    b = bleu.compute(predictions=preds, references=[[r] for r in refs])
    r = rouge.compute(predictions=preds, references=refs)
    return {
        "bleu": b["bleu"] * 100,
        "rouge1": r["rouge1"],
        "rouge2": r["rouge2"],
        "rougeL": r["rougeL"],
    }


def eval_classification(preds, refs, labels=None):
    from sklearn.metrics import accuracy_score, f1_score
    if labels is None:
        labels = sorted(set(refs))
    norm_preds, norm_refs = [], []
    for p, ref in zip(preds, refs):
        pl = p.strip().lower()
        hit = None
        for lab in labels:
            if lab.lower() in pl:
                hit = lab
                break
        norm_preds.append(hit if hit is not None else labels[0])
        norm_refs.append(ref)
    return {
        "accuracy": accuracy_score(norm_refs, norm_preds),
        "f1_macro": f1_score(norm_refs, norm_preds, average="macro", zero_division=0),
    }


def load_model(model_name, adapter_path=None, method="qlora"):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    if adapter_path:
        from peft import PeftModel
        if method == "qlora":
            from transformers import BitsAndBytesConfig
            bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                                     bnb_4bit_compute_dtype=torch.bfloat16,
                                     bnb_4bit_use_double_quant=True)
            base = AutoModelForCausalLM.from_pretrained(model_name, quantization_config=bnb,
                                                        device_map="auto", trust_remote_code=True)
        else:
            base = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=torch.bfloat16,
                                                        device_map="auto", trust_remote_code=True)
        model = PeftModel.from_pretrained(base, adapter_path)
        label = f"finetuned({Path(adapter_path).name})"
    else:
        model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=torch.bfloat16,
                                                     device_map="auto", trust_remote_code=True)
        label = "base"
    return model, tokenizer, label


def evaluate_one(model_name, adapter_path, method, examples, eval_cfg):
    model, tokenizer, label = load_model(model_name, adapter_path, method)
    full_texts = [build_text(ex, tokenizer)[2] for ex in examples]
    ppl = calculate_perplexity(model, tokenizer, full_texts,
                               max_length=eval_cfg.get("max_new_tokens", 256) * 8)
    preds, refs, _ = generate_predictions(model, tokenizer, examples,
                                          max_new_tokens=eval_cfg["max_new_tokens"],
                                          do_sample=eval_cfg["do_sample"])
    if eval_cfg["task_type"] == "classification":
        task_metrics = eval_classification(preds, refs)
    else:
        task_metrics = eval_generation(preds, refs)
    # 释放显存
    del model
    try:
        import torch
        torch.cuda.empty_cache()
    except ImportError:
        pass
    return {"label": label, "perplexity": ppl, "task_metrics": task_metrics,
            "num_examples": len(examples), "do_sample": eval_cfg["do_sample"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--test", required=True, help="测试集 JSONL（训练与调参全程不可见）")
    ap.add_argument("--adapter", default=None, help="LoRA adapter 目录；不提供则只评基线")
    ap.add_argument("--skip-base", action="store_true", help="跳过基线，只评 adapter")
    args = ap.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    if cfg["model"]["name"].startswith("TBD"):
        print("[错误] model.name 仍为 TBD，请先确认基础模型。", file=sys.stderr)
        sys.exit(2)

    test_path = Path(args.test)
    if not test_path.exists():
        print(f"[错误] 测试集不存在: {test_path}", file=sys.stderr)
        sys.exit(2)
    examples = load_test_examples(test_path)
    if len(examples) < 30:
        print(f"[警告] 测试集仅 {len(examples)} 条，指标方差可能较大，结论需谨慎。", file=sys.stderr)

    results = {"timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
               "model_name": cfg["model"]["name"], "method": cfg["method"],
               "test_file": str(test_path), "runs": []}

    if not args.skip_base:
        print("=== 评估基础模型 ===")
        results["runs"].append(
            evaluate_one(cfg["model"]["name"], None, cfg["method"], examples, cfg["eval"]))

    if args.adapter:
        print(f"=== 评估微调模型: {args.adapter} ===")
        results["runs"].append(
            evaluate_one(cfg["model"]["name"], args.adapter, cfg["method"], examples, cfg["eval"]))

    # 计算 delta（基线 vs 微调）
    if len(results["runs"]) == 2:
        base_run, ft_run = results["runs"]
        delta = {"perplexity_delta": ft_run["perplexity"] - base_run["perplexity"]}
        for k in ft_run["task_metrics"]:
            delta[f"{k}_delta"] = ft_run["task_metrics"][k] - base_run["task_metrics"].get(k, 0)
        results["delta_ft_minus_base"] = delta

    out_dir = Path(cfg["experiment"]["results_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"eval_{int(time.time())}.json"
    with out_file.open("w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"\n结果已保存: {out_file}")
    print("提醒：以上为同测试集同解码下的内部对比，只支持'该次训练在该测试集上的效果'，"
          "不构成对真实业务效果的因果断言。")


if __name__ == "__main__":
    main()
