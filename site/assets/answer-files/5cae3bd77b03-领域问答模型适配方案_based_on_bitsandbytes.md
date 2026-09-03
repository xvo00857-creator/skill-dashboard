# 有限规模领域问答数据的模型适配方案（基于 bitsandbytes Skill）

> 评测对象：bitsandbytes（分类：个人效率）
> 方案性质：在时间与资源受限条件下，基于 Skill 文档可验证内容制定的执行方案；所有无法在当前环境验证的条目均标注 **【待确认】**。

---

## 0. 前提与假设（均需在真实环境确认）

| 项 | 规划假设 | 状态 |
|---|---|---|
| 数据规模 | 领域问答约 5,000 条（训练/验证 9:1） | **【待确认】** 用户未提供实际数据量与字段 |
| 基座模型 | Llama-2-7b 起步，有余量再上 13b | **【待确认】** 需确认模型许可与可下载性 |
| 硬件 | 单卡消费级 GPU 24GB（如 RTX 4090），系统内存 ≥64GB | **【待确认】** 当前执行机为 Mac，无 NVIDIA GPU |
| 时间预算 | 单次冒烟 ≤1 小时；完整训练 ≤8 小时 | **【待确认】** 用户未指定 |
| 软件栈 | bitsandbytes + transformers + peft + accelerate + trl + datasets；CUDA 11.1+；PyTorch 2.0+ | 依赖要求来自 SKILL.md「Hardware requirements」与 QLoRA 工作流 |

**关键环境事实（已核查）**：当前执行机为 Apple Silicon Mac（Darwin arm64），Python 3.9.6，未安装 torch/bitsandbytes，无 `nvidia-smi`。bitsandbytes 要求 NVIDIA GPU（算力 7.0+，SKILL.md「Hardware requirements」），因此**本方案无法在当前机器实际运行**，以下配置、显存与指标均为基于 Skill 文档的可执行规划，运行时验证项已逐条标注。

---

## 1. 方法选择依据

### 1.1 选定路线：4-bit QLoRA 微调（NF4 + 双重量化 + 8-bit 分页优化器 + 梯度检查点）

依据均来自 Skill 原文：

1. **显存约束是第一优先级**。4-bit 量化带来 75% 显存压缩（SKILL.md 第 15、37-49 行；quantization-formats.md「Memory: 75% reduction」），7B 模型权重从 14GB 降至 3.5GB（公式见 SKILL.md 第 69-77 行，已复算一致）。
2. **QLoRA 精度损失可接受**。Skill 给出 QLoRA 相对全量微调「<1% degradation」（qlora-training.md 第 16 行）；NF4 在 MMLU 上显著优于 FP4（quantization-formats.md 对比表：7B 上 NF4 45.2% vs FP4 43.8% vs FP16 45.9%），且明确规则「Always use NF4 for transformers」。
3. **个人效率场景 = 单卡消费级 GPU**。Skill 的 qlora-training.md 工作流 1 正是「Train Llama 2 13B on RTX 4090 (24GB)」，与本场景吻合。
4. **8-bit 分页优化器**进一步压缩优化器状态 75%（标准 AdamW 对 7B 需 56GB，8-bit 仅 14GB；SKILL.md 第 289-296 行，已复算），且 `paged_adamw_8bit` 可防止优化器状态导致的硬 OOM（memory-optimization.md「Paged Optimizers」）。
5. **梯度检查点**以约 20% 训练速度换取 30-50% 激活显存节省（memory-optimization.md「Gradient Checkpointing」），在显存受限下是必要取舍。

### 1.2 不选其他路线的理由（依据 SKILL.md「When to use vs alternatives」）

| 备选 | 不选原因（Skill 原文依据） |
|---|---|
| 全量微调 | 7B 全量仅优化器状态就需 56GB，单卡 24GB 不可行 |
| 仅 8-bit 推理、不微调 | 任务是「领域适配」，需要学习领域知识；纯推理无法适配 |
| GPTQ/AWQ | Skill 指出其用于「Production serving (faster inference)」，训练适配阶段不需要 |
| GGUF/llama.cpp | 用于 CPU 推理，非训练路线 |
| FP8 | 仅 H100 等硬件支持，消费级卡不具备 |
| FP4 量化 | Skill 数据表明 NF4 对 Transformer 明显更优，无理由选 FP4 |

---

## 2. 配置样例

以下配置直接改编自 Skill 的 QLoRA 单卡工作流（qlora-training.md 工作流 1）与「Recommended Configurations」。

### 2.1 依赖安装

```bash
pip install bitsandbytes transformers peft accelerate trl datasets
```
（来源：SKILL.md 第 154 行；QLoRA 工作流额外需要 `trl`，见 qlora-training.md 第 60 行 `SFTTrainer`）

### 2.2 量化配置（4-bit NF4 + 双重量化）

```python
from transformers import BitsAndBytesConfig
import torch

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,                          # 75% 权重压缩
    bnb_4bit_compute_dtype=torch.bfloat16,      # Skill 推荐：BF16 平衡速度与稳定性
    bnb_4bit_quant_type="nf4",                  # Skill 规则：Transformer 一律用 NF4
    bnb_4bit_use_double_quant=True              # 额外 2-3% 显存节省，精度影响 <0.1%
)
```
依据：quantization-formats.md「QLoRA Training (Single GPU)」推荐配置；BF16 相对 FP16 不易溢出（同文档「Compute Dtype」表）。

### 2.3 加载模型 + 梯度检查点

```python
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import prepare_model_for_kbit_training

model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-2-7b-hf",                # 起步模型；有余量换 13b
    quantization_config=bnb_config,
    device_map="auto"
)
tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-2-7b-hf")
tokenizer.pad_token = tokenizer.eos_token

model.gradient_checkpointing_enable()
model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)
```
依据：qlora-training.md 第 118-135 行。

### 2.4 LoRA 配置（受限起步：r=8；质量优先时：r=16）

```python
from peft import LoraConfig, get_peft_model

lora_config = LoraConfig(
    r=8,                         # 受限起步用 8（Skill 表：7B 简单任务 r=8-16）；提质量升 16
    lora_alpha=16,               # Skill 建议 alpha = 2 × r
    target_modules="all-linear", # Skill 推荐 QLoRA 作用于所有线性层
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM"
)
model = get_peft_model(model, lora_config)
model.print_trainable_parameters()
# 参考输出（Skill 示例）：trainable params: 4.2M || all params: 6.7B || trainable%: 0.06%
# 【待确认】实际可训练参数量以真实 print 输出为准
```
依据：qlora-training.md「Hyperparameter Tuning」LoRA Rank 表与 alpha 规则；target_modules 推荐项。

### 2.5 训练参数（冒烟配置 → 完整配置两档）

```python
from transformers import TrainingArguments
from trl import SFTTrainer

# 档位 A：冒烟（先验证能跑通，≤1 小时）
training_args_smoke = TrainingArguments(
    output_dir="./qlora-smoke",
    per_device_train_batch_size=2,
    gradient_accumulation_steps=8,   # 有效 batch = 16
    num_train_epochs=1,
    max_steps=50,                    # 硬上限，快速验证
    learning_rate=2e-4,              # Skill：7-13B 推荐 2e-4~3e-4
    bf16=True,
    optim="paged_adamw_8bit",
    logging_steps=5,
    save_strategy="no",
    max_grad_norm=0.3
)

# 档位 B：完整训练（冒烟通过后）
training_args_full = TrainingArguments(
    output_dir="./qlora-output",
    per_device_train_batch_size=4,
    gradient_accumulation_steps=4,   # 有效 batch = 16
    num_train_epochs=2,              # 数据有限，防过拟合先设 2
    learning_rate=2e-4,
    bf16=True,
    optim="paged_adamw_8bit",
    logging_steps=10,
    save_strategy="steps",
    save_steps=100,
    eval_strategy="steps",
    eval_steps=100,
    max_grad_norm=0.3,
    warmup_steps=50
)

trainer = SFTTrainer(
    model=model,
    args=training_args_full,
    train_dataset=dataset["train"],
    eval_dataset=dataset["test"],
    tokenizer=tokenizer,
    max_seq_length=512               # 领域问答通常较短；【待确认】按实际长度分布调整
)
trainer.train()
model.save_pretrained("./qlora-adapters")  # 仅适配器，约 20MB 级
```
依据：qlora-training.md 工作流 1 第 157-184 行；有效 batch 公式 `per_device × accumulation × num_gpus`（同文档第 337 行）。

---

## 3. 显存预算

### 3.1 权重显存（Skill 公式，已复算）

公式（SKILL.md 第 69-77 行）：`显存(GB) = 参数量 × 每参数字节数 / 1e9`

| 模型 | FP16 | INT8 | 4-bit(NF4) |
|---|---|---|---|
| 7B | 14 GB | 7 GB | **3.5 GB** |
| 13B | 26 GB | 13 GB | **6.5 GB** |

### 3.2 QLoRA 训练总显存估算（24GB 目标卡）

参考 memory-optimization.md「Memory Breakdown」与 qlora-training.md 实测值：

| 组件 | 7B 估算 | 依据 |
|---|---|---|
| 模型权重（4-bit） | 3.5 GB | 公式复算 |
| LoRA 参数+梯度+优化器 | <0.5 GB | 可训练参数仅 ~0.06%（Skill 示例），8-bit 优化器 |
| 激活（梯度检查点+BF16） | 3-6 GB | memory-optimization.md：检查点将 13B 激活从 12GB 降至 3GB；7B 更小 |
| batch/seq 缓冲 | 2-4 GB | 与 batch=4、seq=512 相关 |
| CUDA 开销 | 2-5 GB | memory-optimization.md「Buffer = 2-5 GB」 |
| **合计** | **约 11-19 GB** | 落在 24GB 内 |

- Skill 实测：13B QLoRA 在 RTX 4090（24GB）上约 **18GB**（qlora-training.md 第 187 行）。7B 应低于此值。
- **【待确认】** 实际峰值显存须在目标机用 `torch.cuda.max_memory_allocated()` 测量（memory-optimization.md「Memory Profiling」提供了测量代码）。

### 3.3 OOM 降级阶梯（按 memory-optimization.md「Troubleshooting OOM」排序）

1. `per_device_train_batch_size=1`，加大 `gradient_accumulation_steps`
2. 降 LoRA rank：r=8
3. 确认梯度检查点已开启
4. 缩短 `max_seq_length`
5. 启用 CPU offload：`max_memory={0: "20GB", "cpu": "30GB"}`（代价：5-10× 慢）
6. 最后手段：磁盘 offload（`offload_folder`，约 100× 慢，仅保能跑）

---

## 4. 评测门槛

> 具体数值阈值 **【待确认】**，依赖实际数据分布与业务要求；以下给出可执行的门槛结构与 Skill 支持的相对基准。

### 4.1 量化质量门槛（训练前必过）

在领域验证集上比较 FP16 基座 vs NF4 基座：
- **困惑度（PPL）相对上升 < 1%**：依据 quantization-formats.md 困惑度表，7B FP16=5.12 → NF4=5.18（+1.2%）、NF4+DQ=5.19；13B 与 70B 均 <1%。7B 若略超 1% 可接受，但需记录。
- **MMLU/通用基准下降 < 1 个百分点**：Skill 表 7B FP16 45.9% → NF4 45.2%（-0.7pp），作为退化上限参考。
- 若 4-bit 退化不可接受，按 SKILL.md「Lower accuracy than expected」回退 8-bit（<0.5% 损失）。

### 4.2 领域适配门槛（训练后必过）

在留出的领域测试集上：
- **领域问答准确率（或人工/LLM 评判通过率）相对基座有正向提升**，且不低于预设业务线（**【待确认】** 业务线数值）。
- **验证集 loss 较训练前下降且无过拟合**：训练 loss 稳步下降，eval loss 不反弹（qlora-training.md「Best Practices」第 2、3 条）。
- **无灾难性遗忘**：在一小批通用问答上抽样，回答质量不低于基座（**【待确认】** 抽样集与评判标准）。

### 4.3 资源门槛

- 训练峰值显存 ≤ 目标卡显存的 90%（留安全余量）。
- 冒烟阶段（50 步）无 OOM、无 NaN loss。

---

## 5. 停止条件

满足以下任一即停止：

1. **成功停止**：评测门槛全部达成，保存适配器并交付。
2. **早停**：eval loss 连续 3 次评估（每 100 步）不下降，停止并回滚最佳 checkpoint。
3. **时间预算耗尽**：达到 8 小时上限，取当前最优 checkpoint 评测，决定是否追加。
4. **步数上限**：冒烟 50 步 / 完整训练 `max_steps` 命中即停。
5. **发散**：loss 出现 NaN/Inf 或持续上升，停止并降学习率/检查数据。
6. **资源耗尽**：OOM 且已用尽第 3.3 节全部降级手段仍无法运行，停止并报告硬件不足。
7. **质量退化**：量化后 PPL 上升 >2% 且 8-bit 回退仍不达标，停止并重新评估基座模型选择。

---

## 6. 时间/资源受限下的优先级、取舍与验收标准

### 6.1 优先级（P0 → P2）

| 优先级 | 事项 | 理由 |
|---|---|---|
| P0 | 环境可运行：依赖安装、模型可下载、50 步冒烟通过 | 不跑通一切免谈；Skill「Best Practices: Start small, Test on 7B before 70B」 |
| P0 | 显存不 OOM | 单卡硬约束 |
| P1 | 量化质量门槛（PPL/基准退化在限内） | 确保底座可用 |
| P1 | 领域评测有正向提升 | 任务核心目标 |
| P2 | 提质量：r 8→16、epoch 1→2、7B→13B、扩 target_modules | 有余量才做 |
| P2 | 超参搜索、多 seed、合并导出 | 时间允许才做 |

### 6.2 关键取舍

- **显存换时间**：梯度检查点省 30-50% 激活显存但慢约 20%（memory-optimization.md）——受限下接受。
- **精度换显存**：4-bit 比 8-bit 多省一半权重显存，但精度损失略大（1-2% vs <0.5%，SKILL.md「Lower accuracy」）——24GB 跑 7B/13B 训练必须 4-bit；推理可按需切 8-bit。
- **容量换稳定**：r=8 起步而非 16，减少过拟合风险与显存，数据量有限时低秩足够（Skill：7B 简单任务 r=8-16）。
- **速度换可跑**：CPU offload 仅作兜底，5-10× 慢不纳入常规路径。
- **不做超参网格搜索**：时间受限，直接采用 Skill 推荐值（lr=2e-4、alpha=2r、paged_adamw_8bit），最多两组对比。

### 6.3 验收标准

1. 冒烟 50 步在目标卡上无报错完成，输出 `print_trainable_parameters()` 与峰值显存记录。
2. 量化基座 PPL 退化 ≤1%（或记录实际值并说明）。
3. 完整训练后领域测试集指标达到/超过约定业务线，或给出「未达成+原因+下一步」结论。
4. 适配器文件成功保存（约 20MB 级，qlora-training.md「Deployment」）。
5. 所有 **【待确认】** 项在真实环境补齐实测值。

---

## 7. 约束导致的方案变化（与无约束方案对比）

| 维度 | 无约束方案 | 本受限方案 | 变化原因 |
|---|---|---|---|
| 模型规模 | 直接 13B/70B | 7B 起步，验证后再考虑 13B | 单卡 24GB 与时间预算 |
| 微调方式 | 全量微调或多组超参搜索 | QLoRA + 固定 Skill 推荐超参 | 全量微调 7B 仅优化器需 56GB，不可行 |
| 训练轮次 | 3-5 epoch + 早停搜索 | 1 epoch 冒烟 → 2 epoch 完整 | 数据有限防过拟合 + 时间盒 |
| LoRA 秩 | r=64、all-linear 大范围 | r=8 起步，最多 r=16 | 显存与过拟合控制 |
| 批大小 | 大 batch + 多卡 | batch=2-4 + 梯度累积到 16 | 单卡显存 |
| 评测 | 全量基准 + 多任务 | 领域集为主 + 少量通用抽样 | 时间受限，聚焦任务目标 |
| 优化器 | 标准 AdamW | paged_adamw_8bit | 省 75% 优化器显存且防 OOM |
| 验证方式 | 完整训练后评测 | 50 步冒烟先验证管线 | 快速失败，避免浪费时间 |

---

## 8. 验证证据清单

### 8.1 已实际验证

| 证据 | 方式 | 结果 |
|---|---|---|
| ZIP 完整解压、文件结构 | `unzip` + `find` | 4 个文件：SKILL.md + 3 个 references |
| Skill 文档全部阅读 | `Read` 工具逐文件 | 见第 9 节清单 |
| 当前执行环境 | `uname`/`python3`/`nvidia-smi` | Mac arm64、Python 3.9.6、无 torch/bitsandbytes、无 NVIDIA GPU |
| 权重显存公式 | `calculator` 复算 | 7B：FP16=14、INT8=7、INT4=3.5GB；13B：FP16=26、4-bit=6.5GB，与 SKILL.md 第 74-76 行、quantization-formats.md 第 74 行完全一致 |
| 优化器显存公式 | `calculator` 复算 | 7B 标准 AdamW=56GB、8-bit=14GB，与 SKILL.md 第 294-295 行一致 |
| 压缩率 | `calculator` 复算 | 8-bit 与 4-bit 均为 75% 压缩（相对 FP16），与 SKILL.md 第 15 行一致 |
| 文档内部一致性 | 交叉比对 | NF4 推荐、BF16 推荐、paged_adamw_8bit 推荐、梯度检查点取舍在 SKILL.md 与三个 reference 中一致 |

### 8.2 未能验证（均为 **【待确认】**，需在目标 NVIDIA 环境执行）

- bitsandbytes/transformers/peft/trl 在目标机的安装与 CUDA 版本匹配（SKILL.md「Common issues: CUDA error during loading」提示需匹配 CUDA）。
- 模型权重可下载性与许可（Llama-2 需 HuggingFace 授权）。
- 实际峰值显存（须用 `torch.cuda.max_memory_allocated()` 测量）。
- 实际训练吞吐（steps/s）与总耗时。
- 实际可训练参数量（`print_trainable_parameters()` 输出）。
- 量化后实际 PPL/MMLU 退化值。
- 领域问答实际评测指标。
- 数据规模、字段、长度分布（用户未提供数据）。
- 目标 GPU 型号与显存（用户未指定）。

---

## 9. 实际读取的 Skill 文件清单

| 相对路径（相对 bitsandbytes_skill/bitsandbytes/） | 读取情况 |
|---|---|
| `SKILL.md` | 完整读取（411 行） |
| `references/qlora-training.md` | 完整读取（521 行） |
| `references/quantization-formats.md` | 完整读取（447 行） |
| `references/memory-optimization.md` | 完整读取（521 行） |

ZIP 内无 `examples/` 目录、无脚本文件；qlora-training.md 第 514 行提到的 `examples/qlora_training.py` 在本压缩包中**不存在**，因此未读取也未引用其内容。

### 实际影响本方案的 SKILL.md 规则

1. **量化级别选择表（SKILL.md 第 81-87 行）**：决定 24GB/12GB 档位下 7B 用 4-bit。
2. **4-bit 推荐配置（第 104-111 行）**：NF4 + double quant + FP16/BF16 compute，直接成为第 2.2 节配置。
3. **QLoRA 工作流四步清单（第 143-149 行）**：决定方案结构（配置 4-bit 基座 → 加 LoRA → Trainer 训练）。
4. **8-bit 优化器替换（第 241-264 行）**：决定使用 `paged_adamw_8bit`。
5. **「When to use vs alternatives」（第 315-326 行）**：决定不选 GPTQ/AWQ/GGUF/FP8。
6. **Common issues / OOM 处理（第 353-381 行）**：形成第 3.3 节降级阶梯与精度回退路径。
7. **Hardware requirements（第 391-401 行）**：确认 NVIDIA GPU 要求，是判定当前 Mac 无法运行的直接依据。
8. **qlora-training.md 超参表（LoRA rank/alpha/LR/batch）**：决定 r=8 起步、lr=2e-4、alpha=2r、有效 batch=16。
9. **quantization-formats.md 的 NF4 vs FP4 数据与「Always use NF4」规则**：决定量化类型。
10. **memory-optimization.md 的显存分解表与 OOM 诊断步骤**：决定第 3 节显存预算与降级顺序。
11. **qlora-training.md「Best Practices: Start small / Test on 7B before 70B」**：决定先冒烟后完整训练的两档策略。

---

## 10. 缺失项与已完成范围（诚实声明）

**已完成**：
- ZIP 下载、解压、4 个文件全部阅读。
- 基于 Skill 原文制定完整适配方案：方法选择依据、配置样例、显存预算、评测门槛、停止条件。
- 受限条件下的优先级、取舍、验收标准，以及与无约束方案的差异说明。
- 对可复算项（显存公式、压缩率、优化器显存）做了独立算术验证，与 Skill 一致。
- 环境核查，确认当前 Mac 无 NVIDIA GPU，不具备运行条件。

**缺失/未能完成**：
- 未实际安装 bitsandbytes（当前 Mac 无 CUDA，安装也无法运行 GPU 量化路径；且未获用户指定目标环境）。
- 未实际下载模型、未运行任何量化或训练、未产出真实显存/吞吐/指标数据——这些项已全部标注 **【待确认】**。
- 用户未提供实际领域问答数据，数据规模与字段为假设。
- 用户未指定目标 GPU 型号/显存与时间预算，硬件与时间为规划假设。
- 压缩包未包含 `examples/qlora_training.py`，无法参考完整可运行脚本。

如需把本方案落到真实运行，请提供：目标 GPU 型号与显存、领域问答数据样例与规模、时间预算、基座模型偏好；我可据此把 **【待确认】** 项替换为实测值。
