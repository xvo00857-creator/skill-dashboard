# 有限规模领域问答数据的模型适配方案（GRPO + RLVR）

> 依据 Skill：`grpo-rlvr-training`（分类：趣味互动）。本方案严格基于该 Skill 解压后的三个文件，未引用 ZIP 外任何关联 Skill 的内容；凡 Skill 未规定或本环境无法核实的内容，一律标注 **【待确认】**。

---

## 0. 执行环境与可验证性边界（实测）

| 项 | 实测结果 | 来源 |
|---|---|---|
| GPU | 无 NVIDIA GPU（Mac 环境，`nvidia-smi` 不可用） | 本机命令实测 |
| Python | 3.9.6 | 本机命令实测 |
| TRL | **未安装**，无法运行时校验 `GRPOConfig` 字段名 | 本机命令实测 |
| torch | 2.8.0，CUDA 不可用（CPU 版） | 本机命令实测 |
| 奖励函数代码 | `format_reward` / `correctness_reward` / `with_length_penalty` 语法与行为自检通过 | 本机 `py_compile` + 断言实测 |

**结论**：本环境无法实跑 GRPO 训练。本交付物是符合 Skill 规范的"可执行配置与门控方案"，所有需在 GPU 机器上验证的项均标注【待确认】。

---

## 1. 适用性判断（方法选择依据）

Skill 的硬性前置条件（`SKILL.md` "When RL Applies"）：

1. **任务成功必须可算法判定**——单测通过、解析器接受、schema 匹配、答案与标准答案一致。若需人工主观打分，那是 `eval-harness-first` 的 judge 校准问题，**不是直接上 GRPO 的理由**。
2. **基模型必须"有时"能成功**。GRPO 是把已存在的能力重新加权，不能从零植入能力：
   - 模型在低温、多样本下**从不成功** → 缺口是格式/任务理解，**先回到 SFT**（`lora-qlora-recipes`），基成功率非零后再回来；
   - 模型**有时成功、不稳定** → 这是 GRPO 甜点区。
3. 插件通则：**DPO 管口味，GRPO 管推理**。偏好对信号走 `preference-optimization`，不走本 Skill。

### 领域问答数据的分流（数据未提供，以下分支均需按实际数据确认）

| 数据形态 | 奖励信号 | 是否适用 GRPO |
|---|---|---|
| 封闭答案/事实查询，有唯一标准答案字符串 | `correctness_reward`（精确匹配） | 适用 |
| 要求结构化输出/工具调用格式 | `schema_reward`（JSON Schema 校验） | 适用 |
| 代码类问答 | `test_execution_reward`（隔离沙箱跑单测） | 适用，但**必须**有隔离边界 |
| 开放式问答，"正确"需主观判断 | judge reward | **不直接适用**；须先经 `eval-harness-first` 校准 judge（该 Skill 不在本 ZIP，**【待确认/缺失依赖】**） |
| 基模型在该任务上零成功率 | 无 | **不适用**；先 SFT（`lora-qlora-recipes` 不在本 ZIP，**【待确认/缺失依赖】**） |

**方法选择结论**：在确认"答案可算法验证 + 基模型非零成功率"两项后，选择 **GRPO + RLVR**（TRL `GRPOTrainer` + vLLM 生成），奖励为**格式奖励 + 正确性奖励的复合奖励**。任一前置不满足时，按上表分流，不得强行开跑。

---

## 2. 资源受限下的优先级、取舍与验收标准

### 优先级（按"花 GPU 之前能砍掉的风险"排序）

| 优先级 | 事项 | 依据 |
|---|---|---|
| **P0** | 确认数据有可验证 pass/fail 信号；低温采样评测基模型成功率，确认非零 | "When RL Applies" 前置 |
| **P0** | 奖励函数对 **50–100 条**采样输出做人工检查，与人工判断一致后才开跑 | **The Inspection Rule（强制门控，非可选项）** |
| **P1** | 单卡最小可行配置：≤3B 模型 + 24GB 卡 + 三杠杆全开，纯 GRPO，参考超参原样用 | The Recipe + grpo-memory.md |
| **P2** | 仅在观测到特定失败模式后，才切换 DAPO / Dr.GRPO / GSPO | Variant Selection（"反应式，不预选"） |

### 关键取舍（哪些能省、哪些不能省）

- **`num_generations=8` 是地板，不能用降它来省显存**：少于 8 个样本会使组内相对优势基线噪声过大（`SKILL.md` 明确用语 floor / "not a suggestion"）。
- **省显存的优先顺序**：降模型规模 ＞ 三杠杆（vLLM sleep + 8-bit AdamW + gradient checkpointing）同时开启 ＞ `vllm_mode="server"` 把生成拆到独立进程/卡；**不靠降 `num_generations` 或 batch size 到地板以下**。
- **不预扫超参**：`learning_rate=5e-7`、`beta=0.01` 是 settled 起始点，Skill 要求基础跑稳并完成奖励检查后才偏离——受限条件下直接采用，省掉超参扫描。
- **不预选变体**：DAPO/Dr.GRPO/GSPO 只在对应症状出现后上，不做预防性实验。
- **长上下文**：仅当 rollout 确实超长时才考虑 Unsloth 分块；其"约 7×"数字 Skill 自己声明未重新测量，须对照当前 Unsloth release notes——**【待确认】**。

### 验收标准

1. 门控验收：基模型非零成功率有实测数字；50–100 条奖励-人工一致性检查通过（不一致则奖励函数返工，不算通过）。
2. 训练验收：`format_reward` 与 `correctness_reward` 分别记录且可区分——格式对但答案错、与格式错，得分不得相同。
3. 上线验收：在密封测试集上的正确性指标达到业务门槛——**具体数值 Skill 未规定，【待确认】**，需业务方给定。
4. 反作弊验收：训练奖励上升的同时，密封集正确性必须同向上升；若奖励升而正确性不升，判为 reward-hacking，不予通过。

---

## 3. 配置样例

以下超参**逐字来自 `SKILL.md` The Recipe**；显存杠杆来自 `references/grpo-memory.md`；注释中标注【待确认】的为运行时需核实项。

```python
from trl import GRPOConfig, GRPOTrainer

# SFT_CHECKPOINT / tokenizer 由上游 finetuning-method-selection 与 model-catalog 决定；
# Skill 故意不具名基础模型，实际检查点【待确认】（model-catalog.md 不在本 ZIP）。

grpo_args = GRPOConfig(
    output_dir="./outputs-grpo",
    use_vllm=True,
    vllm_mode="colocate",        # 单卡；多卡生成/训练分离用 "server"
    num_generations=8,           # 地板，不得低于 8
    learning_rate=5e-7,          # settled 起始值
    beta=0.01,                   # 相对参考策略的 KL 系数
    per_device_train_batch_size=8,
    gradient_accumulation_steps=4,
    bf16=True,
    logging_steps=10,
    seed=3407,

    # —— 24GB 单卡跑 ≤3B 的三杠杆（grpo-memory.md 要求三者同时开启，缺一不可）——
    optim="adamw_8bit",          # 8-bit AdamW，需 bitsandbytes【待确认：运行环境是否安装】
    gradient_checkpointing=True, # 重计算换激活显存
    # vLLM sleep 模式：在 rollout 与训练步之间释放生成引擎 KV-cache/权重，
    # 避免两者同时常驻。TRL 中对应字段名随版本变化（如 vllm_sleep_level 等），
    # 本机未装 TRL 无法核实 → 【待确认：对照所装 TRL 版本 GRPOConfig 字段】
)

trainer = GRPOTrainer(
    model=SFT_CHECKPOINT,
    args=grpo_args,
    reward_funcs=[format_reward, correctness_reward],  # 复合奖励，见第 4 节
    train_dataset=prompts,        # 仅 prompt；GRPO 自行生成 completion
    processing_class=tokenizer,
)
trainer.train()
```

**对话格式注意**（`reward-functions.md` 明确）：若数据集是 TRL 对话格式，每条 completion 为 `[{"role":"assistant","content":"..."}]`，必须在每个奖励函数里先取 `completion[0]["content"]` 再做字符串操作；上述示例按标准字符串 completion 格式编写。

---

## 4. 奖励函数（复合奖励 + 检查门控）

采用 Skill 库中的两个函数，已在本机通过语法与行为自检：

- `format_reward`：检查 `<reasoning>...</reasoning>` 后接 `<answer>...</answer>`，符合得 1.0，否则 0.0。这是门控，不是正确性信号。
- `correctness_reward`：抽取 `<answer>` 块与标准答案列 `answer` 精确匹配，匹配得 2.0，否则 0.0。

> 代码原文见 `references/reward-functions.md`（Format Reward / Correctness Reward — Exact Match 两节），本交付不复制全文以避免与源文件产生偏差。

- 若领域问答是结构化输出：把 `correctness_reward` 换成 `schema_reward`（JSON Schema 校验）。
- 若出现偶发长度溢出：用 `with_length_penalty` 包装；若长度偏差是系统性的，不堆 wrapper，改走 Dr.GRPO 变体。
- 代码类问答：用 `test_execution_reward`，**必须**传入 `sandbox_cmd`（断网、限资源容器）；函数在 `sandbox_cmd` 为空时拒绝执行并全部返回 0.0，绝不回退到宿主执行。

**The Inspection Rule（强制）**：开跑前，把奖励函数跑到 50–100 条采样输出上并人工阅读。若奖励判断与人工阅读不一致，**先修奖励函数**；对着未检查的奖励训练或用超参去补偿一个悄悄打错分的奖励，正是 reward-hack 的成因。这也是 `/finetune` Phase 1 的门控输入。

---

## 5. 显存预算

来自 `references/grpo-memory.md` 的 Memory Anchors（Skill 只给量级锚点，不点名具体模型）：

| 模型量级 | 可行硬件 | 条件 |
|---|---|---|
| 小模型（≤~3B） | 24GB 级 GPU | **必须同时**开启 vLLM sleep + 8-bit AdamW + gradient checkpointing，三者缺一不可 |
| ~32B 级 | H200 级 GPU | 策略模型 + 参考模型（KL 项）+ 同驻 vLLM 引擎在该级别以下放不下 |
| ~70B 级 | B200 级 GPU | 同上三者驻留，规模更大 |

补充规则（同文件）：

- 这些是**起始锚点而非硬地板**；`vllm_mode="server"`（独立生成进程，可在独立卡上）会改变驻留计算，判定某量级在某机器上不可行前需重新推算。
- **DGX Spark 带宽瓶颈**：GRPO rollout 是 decode 重负载，受显存带宽而非算力约束。该文件引用 `dgx-spark-ops` 插件的持续带宽预算 180–192 GB/s（非 273 GB/s 标称值）——该插件**不在本 ZIP，数字无法独立核实【待确认】**。在 Spark 上优先选小模型，降量级通常比继续调 GRPO 超参更有效。
- **Unsloth 长上下文 RL 分块**：同显存预算下可用上下文约 7×，但该数字来自 Unsloth 公开基准、Skill 未重新测量——**【待确认】**，精确预算前对照当前 release notes。

**本方案的受限选择**：锁定 **≤3B + 24GB 单卡 + 三杠杆全开 + colocate**；`server` 模式与更大模型列为备选，需有对应硬件后重新推算。

---

## 6. 评测门槛

Skill 规定的是**结构性门控**，未给具体数值指标；数值类门槛均标【待确认】。

| 阶段 | 门槛 | 性质 |
|---|---|---|
| 开跑前 | 基模型在目标任务上低温多样本成功率 **> 0** | Skill 强制前置；为 0 先去 SFT |
| 开跑前 | 奖励函数对 50–100 条采样输出与人工判断一致 | **The Inspection Rule 强制门控** |
| 训练中 | `format_reward`、`correctness_reward` 分项监控，可区分"格式对答案错"与"格式错" | Skill 复合奖励要求 |
| 训练中 | 若用 judge reward：judge 须先在 train/dev/sealed-test 上校准，报告 TPR/TNR，并固定快照 | `reward-functions.md` 硬性前提；校准流程在 `eval-harness-first`（**缺失【待确认】**） |
| 验收 | 密封测试集正确性达到业务阈值 | **具体数值 Skill 未规定【待确认】** |
| 反作弊 | 训练奖励上升时，密封集正确性须同向上升；背离即判 reward-hack | 依据 Inspection Rule 反 reward-hack 原则 |

---

## 7. 停止条件与变体切换

Skill 未给"多少 step 无提升就停"的数值早停（**具体早停步数/耐心值【待确认】**），但给出了明确的失败模式 → 变体映射。停止/切换条件如下：

| 观测到的现象 | 动作 | 依据 |
|---|---|---|
| 奖励函数判断与人工阅读不一致 | **停止训练**，先修奖励函数，再谈超参 | Inspection Rule |
| 训练奖励升但密封集正确性不升/人工判读变差 | **停止**，判定 reward-hack，回查奖励 | Inspection Rule |
| 熵崩塌 / 退化的长链思考 | 停当前 run，换 **DAPO**（解耦 clip 范围、放松过长推理上过度正则化的 KL） | Variant Selection |
| 奖励或输出长度不论质量持续上升 | 换 **Dr.GRPO**（去除长度归一化偏差）；偶发溢出先用 `with_length_penalty` | Variant Selection + reward-functions.md |
| 训练 MoE 模型且 per-token 重要性比不稳定 | **必须换 GSPO**（序列级重要性比），非可选 | Variant Selection |
| 时间/显存预算耗尽 | 停止，保留 checkpoint 与日志供复盘 | 外部资源约束 |
| 基础 run 未稳定前 | **不得**调 lr/beta、不得预选变体 | The Recipe / Variant Selection |

---

## 8. 约束导致的方案变化（受限版 vs 无约束标准版）

| 维度 | 无约束标准版 | 时间/资源受限版（本方案） | 变化原因 |
|---|---|---|---|
| 模型量级 | 可按任务选 ~32B/H200 甚至更大 | 锁定 ≤3B / 24GB 单卡 | 显存锚点 + 带宽约束下小模型优先 |
| 显存策略 | 按需选配 | 三杠杆**强制全开**，缺一不可 | grpo-memory.md：24GB 仅在三者同时开启时可行 |
| 并行方式 | 可 server 模式多卡分离 | colocate 单卡，server 仅备选 | 硬件受限 |
| 变体 | 可并行试 DAPO/Dr.GRPO | 纯 GRPO 起步，**反应式**切换 | 省实验时间；Skill 要求不预选 |
| 超参 | 可做 lr/beta 扫描 | 直接用 5e-7 / 0.01，不扫描 | Skill：基础跑稳并奖励检查后才偏离 |
| `num_generations` | 可能加大以降方差 | 守 8 地板，不降不升 | 地板不可破；加大增显存 |
| 前期门控 | 可快速跳过 | **P0 最高优先级**：非零成功率 + 50–100 奖励人工检查 | 受限下 GPU 时间最贵，先在 CPU/人工阶段砍掉风险 |
| 长上下文 | 可直接上 Unsloth | 仅必要时启用，7× 数字待核实 | Skill 自己声明该数字需复核 |
| judge 类问答 | 可校准 judge 后上 | 标注为**不直接适用**，依赖缺失的 eval-harness-first | 关联 Skill 不在 ZIP，不能编造校准流程 |

---

## 9. 验证证据与缺失项

### 已验证
- ZIP 解压得到 3 个文件，均已完整读取：`SKILL.md`、`references/grpo-memory.md`、`references/reward-functions.md`。
- 环境实测：无 NVIDIA GPU、Python 3.9.6、TRL 未安装、torch 2.8.0 CPU 版。
- 奖励函数 `format_reward`、`correctness_reward`、`with_length_penalty` 通过 `py_compile` 语法检查与 4 条行为断言（格式命中/未命中、答案对/错）。

### 无法验证 / 缺失项（未假装成功）
1. **未提供实际数据集**：规模、领域、答案形式（精确匹配 / schema / 主观）均未知 → 适用性分支无法落到具体一种，全部【待确认】。
2. **未提供基模型与当前成功率**：无法确认"非零成功率"前置 → 【待确认】。
3. **未提供 GPU 型号/显存/时间预算的具体数字**：显存预算仅能量级锚点 → 【待确认】。
4. **TRL 未安装**：`GRPOConfig` 中 vLLM sleep 等字段的确切参数名无法运行时核实 → 【待确认】。
5. **关联 Skill 不在本 ZIP**，其内容不得编造：`finetuning-method-selection`、`lora-qlora-recipes`、`preference-optimization`、`eval-harness-first`、`llm-finetuning-training-engineer`、`dgx-spark-ops`（含 `spark-training-gotchas`）、`references/model-catalog.md`。
6. **未能实跑训练**：本环境无 GPU/TRL，配置正确性止于"与 Skill 原文一致 + 代码语法自检"，端到端可运行性需在目标 GPU 机器上确认。
7. Unsloth 7×、DGX Spark 180–192 GB/s 为 Skill 引用的外部数字，本环境无法复核 → 【待确认】。

---

## 10. 实际读取的 Skill 文件清单

| 文件（相对 ZIP 根） | 读取情况 | 实际影响执行的规则 |
|---|---|---|
| `grpo-rlvr-training/SKILL.md` | 完整读取（205 行） | ①RL 适用条件与"先确认非零成功率"前置；②The Recipe 的全部超参（colocate、num_generations≥8、lr=5e-7、beta=0.01、batch=8、ga=4、bf16、seed=3407）；③复合奖励；④The Inspection Rule 50–100 样本门控；⑤变体选择表（DAPO/Dr.GRPO/GSPO 反应式切换）；⑥VLM RL 不可执行（本任务不涉及） |
| `grpo-rlvr-training/references/grpo-memory.md` | 完整读取（93 行） | ①三量级显存锚点（≤3B/24GB 三杠杆、32B/H200、70B/B200）；②24GB 必须三杠杆同时开启；③server 模式改变驻留计算；④Unsloth 7× 需复核；⑤DGX Spark 带宽优先选小模型 |
| `grpo-rlvr-training/references/reward-functions.md` | 完整读取（316 行） | ①format/correctness/schema/test_execution 奖励实现；②对话格式须先取 content；③Inspection Rule 重申；④length-penalty 与 Dr.GRPO 的边界；⑤judge reward 必须先校准且用异族模型；⑥test_execution_reward 强制沙箱、空 sandbox 拒绝执行 |

