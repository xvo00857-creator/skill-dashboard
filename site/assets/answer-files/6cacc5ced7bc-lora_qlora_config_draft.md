# LoRA/QLoRA 适配器配置草案（按 lora-qlora-recipes Skill）

## 能力边界与冲突说明

表格把本 Skill 归入"内容与写作"，但 SKILL.md 明确：输入是"路由决策（SFT via LoRA/QLoRA）+ 目标规模档"，输出是"经验证的适配器配置——即 kwarg 值，而非自由建议"，供下游 llm-finetuning-training-engineer 直接消费。它不写研究报告、不整理证据、不跑实验，也不负责数据准备（dataset-curation）与模型选型（finetuning-method-selection）。因此本交付以具体配置块为主体；本轮无既有稿件，"修订稿"即首份合规草案。

## 待确认假设（未提供，无法访问）

- 基座规模档与具体 checkpoint：未提供。hyperparameters.md 明确基座模型不在此文件命名，需查 model-catalog。
- 硬件与 BF16 支持：未提供，无法运行 `torch.cuda.is_bf16_supported()` 实测。
- 数据形态：未说明是否 messages 型对话、是否需要 assistant_only_loss；这决定走 Unsloth 还是 plain TRL。
- 以下采用"通用默认档 r=32"，上述信息确认后需联动复核。

## 修订稿：通用默认适配器配置（QLoRA，r=32，未实际运行）

```python
target_modules = ["q_proj","k_proj","v_proj","o_proj",
                  "gate_proj","up_proj","down_proj"]
# get_peft_model
r=32, lora_alpha=64, lora_dropout=0, bias="none",
use_gradient_checkpointing="unsloth", random_state=3407,
use_rslora=False
# SFTConfig
load_in_4bit=True, learning_rate=2e-4, bf16=True,
optim="adamw_8bit", per_device_train_batch_size=4,
gradient_accumulation_steps=4, num_train_epochs=3,
max_length=2048, dataset_text_field="text", seed=3407
# 有效批量 = 4*4*1 = 16 < 32
```

bf16=True 以硬件支持为前提；不支持则换硬件，不得回退 fp16。

## 具体例子

SKILL.md 记载的场景：65B 级模型在 48GB 卡上做 SFT，bf16 放不下→选 QLoRA（NF4 冻结基座 + BF16 适配器，省显存来自量化基座而非适配器），配 r=32、alpha=64、LR 2e-4、有效批量 16、全线性模块。

## 反例

为省显存把 target_modules 砍成只剩 q_proj/v_proj（注意力-only）。SKILL.md 将其列为 Failure Mode：gate/up/down 三层参数占比小、省显存极少，却明显掉点；内存紧张应先转 QLoRA 或降 rank/batch/pack 长度，而非删模块。另一常见反例：把全量微调 LR 原样搬到 LoRA（LoRA LR 约为全量 FT 的 10 倍），导致欠拟合。

## 主要取舍

- LoRA vs QLoRA：默认 LoRA，仅 bf16 放不下才升 QLoRA。SKILL.md 另载：DGX Spark 上 QLoRA 可能因 bitsandbytes 反量化缓冲瞬时峰值先 OOM，下一步应试 bf16 LoRA，而非继续压缩 QLoRA（此为文件记载，非本人实测）。
- rank：通用默认 16–32，不预设 256；小数据上高 rank 记忆快于泛化，仅当 held-out eval 证明确实欠拟合才升。
- rsLoRA：r≥32 才值得开；r=32 阈值处默认关，观察到不稳定再开。
- Unsloth vs plain TRL：Unsloth 是默认快路径；但 messages 型数据 + assistant_only_loss=True 时，Unsloth 2026.7.x 编译 trainer 无此路径，plain TRL 是该组合的默认而非罕见回退（据 unsloth-trl-mapping.md，最后核验 2026-07-14）。

## 行动清单

1. 确认基座规模档与 checkpoint（来自 model-catalog，本 Skill 不提供）。
2. 目标硬件跑 `python -c "import torch; print(torch.cuda.is_bf16_supported())"`；不支持 BF16 则换硬件，不用 fp16。
3. 判数据形态：messages+assistant_only_loss→plain TRL/PEFT，按映射表翻译 kwarg；否则 Unsloth 快路径并显式传 padding_free=False。
4. 按规模档选 rank 与 LR；改 rank/量化/batch 任一值后联动复核其余项。
5. 算有效批量 = per_device × accumulation × num_devices，保持 <32。
6. 若 packing，先套 chat template 再 pack，并抽检解码样本。
7. 跑通后用 held-out eval 判欠拟合，再决定是否升 rank，勿默认加高。

## 实际读取的 Skill 文件（相对路径）

- lora-qlora-recipes/SKILL.md
- lora-qlora-recipes/references/hyperparameters.md
- lora-qlora-recipes/references/unsloth-trl-mapping.md

## 影响交付的一条 SKILL.md 规则

SKILL.md"Output format"节规定输出必须是"经验证的适配器配置——kwarg 值，而非自由建议"。这直接决定本交付以配置块为主体，而非按题目"研究设计/证据整理"框架写散文；其中 alpha=2r、QLoRA LR=2e-4、有效批量<32、全线性 target_modules 等规则逐一约束了配置块里的每个数值。
