#!/usr/bin/env python3
"""
QLoRA/LoRA 训练脚本（对应 SKILL.md 第 2-3 步与 references/lora-peft.md、hyperparameter-tuning.md）。

用法：
    python src/train.py --config configs/experiment_config.yaml

硬性规则（来自 SKILL.md Constraints）：
- 训练前必须已通过 validate_dataset.py（本脚本检查 processed 目录存在）
- 大模型（>7B）必须用参数高效方法（本脚本只支持 lora/qlora）
- 必须包含 learning rate warmup（warmup_ratio 来自配置，默认 0.03）
- 监控 train/val loss，过拟合告警
- 记录超参、版本化 checkpoint
- 仅保存 adapter 权重（PEFT 惯例）

注意：本脚本未在本次环境运行；实际 GPU、CUDA、transformers 版本可能需要微调参数。
"""
import argparse
import json
import os
import random
import sys
from pathlib import Path

import yaml


def set_seed(seed: int):
    random.seed(seed)
    try:
        import numpy as np
        np.random.seed(seed)
    except ImportError:
        pass
    try:
        import torch
        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
    except ImportError:
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    args = ap.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    if cfg["model"]["name"].startswith("TBD"):
        print("[错误] configs/experiment_config.yaml 中 model.name 仍为 TBD，"
              "请先确认基础模型与许可证。", file=sys.stderr)
        sys.exit(2)

    data_dir = Path(cfg["data"]["output_dir"])
    if not (data_dir / "train.jsonl").exists():
        print(f"[错误] 未找到 {data_dir}/train.jsonl。请先运行 validate_dataset.py 与 prepare_data.py。",
              file=sys.stderr)
        sys.exit(2)

    import torch
    from datasets import load_dataset
    from transformers import (AutoModelForCausalLM, AutoTokenizer,
                              TrainingArguments, TrainerCallback)
    from peft import LoraConfig, get_peft_model, TaskType, prepare_model_for_kbit_training
    from trl import SFTTrainer

    set_seed(cfg["experiment"]["seed"])

    model_name = cfg["model"]["name"]
    method = cfg["method"].lower()
    if method not in ("lora", "qlora"):
        print(f"[错误] method 仅支持 lora/qlora（>7B 按 Skill MUST 使用参数高效方法），当前: {method}",
              file=sys.stderr)
        sys.exit(2)

    # ---------- 1. tokenizer ----------
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # ---------- 2. 模型加载（QLoRA 时 4-bit 量化） ----------
    model_kwargs = {"torch_dtype": torch.bfloat16, "device_map": "auto",
                    "trust_remote_code": True}
    if method == "qlora":
        from transformers import BitsAndBytesConfig
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
        )
        model_kwargs["quantization_config"] = bnb_config

    model = AutoModelForCausalLM.from_pretrained(model_name, **model_kwargs)

    if method == "qlora":
        # k-bit 训练准备（开启 gradient checkpointing 省显存）
        model = prepare_model_for_kbit_training(
            model, use_gradient_checkpointing=cfg["training"]["gradient_checkpointing"]
        )

    # ---------- 3. LoRA 配置 ----------
    lcfg = cfg["lora"]
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=lcfg["r"],                       # rank：中等任务从 16 起，数据少可减半防过拟合
        lora_alpha=lcfg["lora_alpha"],     # 通常 2*r
        target_modules=lcfg["target_modules"],
        lora_dropout=lcfg["lora_dropout"],
        bias=lcfg["bias"],
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()  # 期望可训练参数约 0.1%-1%

    # ---------- 4. 数据 ----------
    dataset = load_dataset(
        "json",
        data_files={"train": str(data_dir / "train.jsonl"),
                    "test": str(data_dir / "val.jsonl")},
    )

    def format_prompt(example):
        # Alpaca 风格；若数据为 messages 格式，建议改用 tokenizer.apply_chat_template
        if "messages" in example:
            msgs = example["messages"]
            text = tokenizer.apply_chat_template(msgs, tokenize=False)
        else:
            inst = example.get("instruction", "")
            inp = example.get("input", "")
            out = example.get("output", "")
            text = f"### Instruction:\n{inst}\n\n### Input:\n{inp}\n\n### Response:\n{out}"
        return {"text": text}

    dataset = dataset.map(format_prompt)

    # ---------- 5. 训练参数（完整注释） ----------
    t = cfg["training"]
    output_dir = Path(cfg["experiment"]["output_dir"]) / cfg["experiment"]["id"]
    training_args = TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=t["num_train_epochs"],
        per_device_train_batch_size=t["per_device_train_batch_size"],
        gradient_accumulation_steps=t["gradient_accumulation_steps"],  # 有效 batch = 两者乘积
        learning_rate=t["learning_rate"],       # QLoRA 1e-4 / LoRA 2e-4 起步
        lr_scheduler_type=t["lr_scheduler_type"],
        warmup_ratio=t["warmup_ratio"],         # Skill MUST：必须有 warmup
        weight_decay=t["weight_decay"],         # 小数据正则化，防过拟合
        max_grad_norm=t["max_grad_norm"],
        logging_steps=t["logging_steps"],
        save_strategy="steps",
        save_steps=t["save_steps"],
        save_total_limit=t["save_total_limit"],
        eval_strategy="steps",
        eval_steps=t["eval_steps"],
        load_best_model_at_end=True,            # 以 eval_loss 选最佳 checkpoint
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        bf16=t["bf16"],
        gradient_checkpointing=t["gradient_checkpointing"],
        gradient_checkpointing_kwargs={"use_reentrant": False},
        optim=t["optim"],                       # qlora 用 paged_adamw_8bit 省显存
        group_by_length=t["group_by_length"],
        report_to="none",                       # 有 wandb 可改 ["wandb"]
        seed=cfg["experiment"]["seed"],
    )

    # ---------- 6. 过拟合监控回调 ----------
    class OverfittingCallback(TrainerCallback):
        def on_evaluate(self, args, state, control, metrics=None, **kwargs):
            if metrics is None:
                return
            eval_loss = metrics.get("eval_loss")
            # 从日志取最近 train loss
            train_loss = None
            for log in reversed(state.log_history):
                if "loss" in log:
                    train_loss = log["loss"]
                    break
            if train_loss and eval_loss and eval_loss > train_loss * 1.5:
                print(f"[过拟合告警] train_loss={train_loss:.4f} eval_loss={eval_loss:.4f}；"
                      f"按 Skill 建议：减 epoch / 加 dropout / 加 weight decay / 早停。")

    # ---------- 7. 训练 ----------
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=dataset["train"],
        eval_dataset=dataset["test"],
        tokenizer=tokenizer,
        dataset_text_field="text",
        max_seq_length=cfg["model"]["max_seq_length"],
        packing=True,
    )
    trainer.add_callback(OverfittingCallback())

    train_result = trainer.train()

    # ---------- 8. 保存 adapter 与训练元信息 ----------
    adapter_dir = output_dir / "lora-adapter"
    model.save_pretrained(str(adapter_dir))
    tokenizer.save_pretrained(str(adapter_dir))

    metrics = train_result.metrics
    trainer.log_metrics("train", metrics)
    trainer.save_metrics("train", metrics)

    with open(output_dir / "train_config_snapshot.json", "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

    print(f"训练完成。adapter 保存于: {adapter_dir}")
    print("下一步：运行 src/evaluate.py 在独立测试集上对比基线与微调模型。")


if __name__ == "__main__":
    main()
