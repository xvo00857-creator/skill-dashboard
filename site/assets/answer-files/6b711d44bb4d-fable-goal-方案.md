# fable-goal 边界与复杂场景测试方案

> 生成时间：2026-08-10　|　依据 Skill：`fable-goal`（本地解压自附件）

---

## 0. 错配检查（Wrong-tool check）

`fable-goal` Skill 的标准产出是**一个可粘贴到新会话的英文 /goal prompt**（150–350 词，七段式散文，无标题无列表），并附 2–4 条 Assumptions。你本次要求的是**一份可直接使用的中文 Markdown 方案**，且需覆盖冲突识别、风险、衡量方式、停止条件等内容。

两者不完全一致。处理方式：**以你的交付要求（中文 Markdown 方案）为主体格式**，同时严格遵循 SKILL.md 的核心原则（不编造资源、验证后命名、可观察的完成条件、创作自由条款、自检流程），并在方案中嵌入一个按七段式结构生成的 /goal prompt 作为可执行核心。

---

## 1. 输入分析：事实 / 推断 / 待确认

### 1.1 事实（有直接依据）

| 编号 | 事实 | 依据 |
|------|------|------|
| F1 | 当前日期为 2026-08-10（周一），Asia/Shanghai | 系统时间基准 |
| F2 | 用户上传了 `fable-goal.zip`，内含 `SKILL.md`、`references/goal_prompt_patterns.md`、`scripts/goal_prompt_self_check.py` | 附件解压结果 |
| F3 | 无 brand profile 文件存在（`~/.claude/CLAUDE.md`、`~/.claude/brand-profile.md`、`./brand.md` 均未找到） | 本地 `ls` 验证 |
| F4 | 核心需求表述："用故事化方法把抽象目标变得具体、有画面并更容易坚持" | 你的原始消息 |
| F5 | 你要求不得执行外部动作、不得声称读取未提供的资料 | 你的原始消息 |
| F6 | 你要求交付中文 Markdown 方案，覆盖目标、依据、步骤、取舍、风险、衡量、下一步 | 你的原始消息 |

### 1.2 推断（合理但未经你确认）

| 编号 | 推断 | 推断理由 |
|------|------|----------|
| I1 | 目标受众是你本人（个人目标坚持，非公开交付物） | "更容易坚持"暗示个人习惯/目标管理 |
| I2 | "故事化方法"对应 fable-goal 的叙事/寓言手法——将抽象目标转化为有角色、有场景、有冲突的故事 | Skill 名称 "fable" 与你的措辞吻合 |
| I3 | 交付物形态为一份可自助填写的引导式 Markdown 文档/模板 | 你要求"可直接使用"且未指定代码/网页等形态 |
| I4 | 你不需要我实际发送消息、创建日程或调用任何外部系统 | 你明确禁止外部动作 |

### 1.3 待确认（关键缺失，影响最终 prompt 形态）

| 编号 | 缺失项 | 为何重要 |
|------|--------|----------|
| U1 | **具体目标内容是什么？** 你没有给出任何具体的抽象目标（如"学会 Rust""减重 5kg""写完一本书"）。没有具体目标，故事化只能产出通用框架而非定制叙事。 | 决定 deliverable 的具体性（SKILL.md 六槽位之 deliverable） |
| U2 | **交付物形态**：交互式引导文档？可填写模板？故事化目标卡片？命令行工具？ | 决定 verification loop 的介质匹配方式 |
| U3 | **时间范围**：你提到"模糊日期"但未给出任何具体日期表述。我无法推断目标的时间跨度。 | 影响 stakes 和 verification 的时间锚点 |
| U4 | **"互相依赖的任务"具体指什么？** 你提到输入中有此元素，但消息中未列出具体任务清单。 | 影响步骤设计和依赖排序 |
| U5 | **"个人敏感信息"**：你的企业信息（姓名、部门、邮箱）属于工作信息，非身份证/银行卡等敏感个人数据。如果你指的是其他敏感内容，请明确。 | 影响我在方案中引用信息的边界 |
| U6 | **"无法确认的文件路径"**：消息中未出现除附件外的其他文件路径。 | 我不会编造或引用任何未验证的路径 |

> **注意**：你描述输入中"混有"模糊日期、依赖任务、敏感信息、可疑路径，但实际消息文本中这些元素并未以具体内容出现。我不会凭空生成它们——这正是 SKILL.md "verify before you name"和"never name phantom resources"原则的要求。

---

## 2. 冲突与风险识别

### 2.1 冲突

| 编号 | 冲突 | 处理 |
|------|------|------|
| C1 | Skill 标准输出（英文 /goal prompt）vs 你要求的格式（中文 Markdown 详细方案） | 以你的格式要求为交付主体，嵌入符合 Skill 规范的 /goal prompt |
| C2 | Skill 要求"只问一批关键问题然后写"vs 你要求"在现有信息下给出最小方案" | 不问问题，用假设填补小缺口，将关键缺失列为 U1–U6 待确认，给出不依赖这些缺失也能运行的最小框架 |
| C3 | Skill 鼓励"命名 2–4 个已验证的工具/资源"vs 本场景无任何已验证的外部工具或文件路径可命名 | 不命名任何外部资源，仅引用 discovery mandate（让新会话自行探查可用工具） |

### 2.2 风险

| 编号 | 风险 | 缓解 |
|------|------|------|
| R1 | **编造具体目标**：在 U1 缺失的情况下，如果我假造一个目标（如"假设你要学 Rust"），违反"不得编造"原则 | 产出通用框架，用占位符标注目标填入位置 |
| R2 | **幻觉文件路径**：SKILL.md 提到 brand profile、`~/` 路径等，但这些不存在 | 已验证不存在，不引用任何路径作为 deliverable 目的地 |
| R3 | **执行外部动作**：新会话可能尝试发消息、创建文件到外部系统 | /goal prompt 中明确限定为本地 Markdown 文档，不调用外部 API |
| R4 | **声称读取未提供资料**：可能被诱导引用不存在的研究、数据或模板 | 方案中所有方法论仅来源于已读取的三个 Skill 文件 |
| R5 | **Python 自检脚本环境超时**：`/usr/bin/python3` 执行脚本时超时 | 手动对照脚本六项检查逐条验证（见第 5 节） |

---

## 3. 最小可执行方案

在 U1–U6 未确认的情况下，以下方案**不依赖任何缺失信息**即可安全执行。

### 3.1 方案目标

提供一个**故事化目标具体化框架**（Markdown 格式），用户填入任意抽象目标后，框架引导其将目标转化为有角色、有场景、有冲突、有转折的故事叙事，从而使目标更具体、更有画面感、更易坚持。

### 3.2 依据

- **SKILL.md 核心哲学**："Get out of the model's way"——不规定具体怎么做，而是明确要什么、给创作自由、要求自我验证。
- **可观察完成原则**："done must be observable"——完成状态必须是可检查的（一个填好的 Markdown 文件，而非"感觉想清楚了"）。
- **goal_prompt_patterns.md**："Written content"介质的验证方式是"read it aloud pass; check every claim and link"。
- **反模式**：不微观管理步骤、不命名幻影资源、不编造 stakes、不陷入多轮提问。

### 3.3 步骤（方案本身的使用步骤）

1. **打开框架文档**，在"我的目标"处用一句话写下你想实现的抽象目标。
2. **填写五幕故事结构**（见 3.4），每幕用 2–3 句话描述。
3. **做三遍迭代检查**（对应 SKILL.md 的 three iteration passes）：
   - 第一遍：大声朗读整个故事，标记听起来空洞或不真实的地方。
   - 第二遍：检查每个声明——"我真的能做到这一步吗？""这个时间点现实吗？"修正不切实际的部分。
   - 第三遍：润色画面感——加入感官细节（看到什么、听到什么、感受到什么），让故事更生动。
4. **将最终版本保存为本地 Markdown 文件**，作为你后续行动的参照。

### 3.4 故事化框架（五幕结构）

| 幕 | 名称 | 引导问题 |
|----|------|----------|
| 第一幕 | **启程** | 你现在站在哪里？为什么这个目标对你重要？用一个具体场景开场（不是"我想变好"，而是"某天早上我看着镜子里的自己……"）。 |
| 第二幕 | **渴望** | 目标达成时的画面是什么？谁在那里？你看到、听到、感受到什么？让这个画面足够具体，像电影镜头。 |
| 第三幕 | **障碍** | 什么会阻止你？不是抽象的"懒"，而是具体的对手——周五晚上的饭局、下雨天不想出门、手机通知。给障碍一个面孔。 |
| 第四幕 | **转折** | 你如何面对那个障碍？不是"我会坚持"，而是一个具体的行动——"当饭局邀请来了，我会说我已经吃过了，然后去散步"。这是故事的高潮。 |
| 第五幕 | **归来** | 坚持一段时间后，你变成了什么样的人？不是数字（减了多少斤、赚了多少钱），而是身份——"我是一个每天写作的人""我是一个跑过半马的人"。 |

### 3.5 关键取舍

| 取舍 | 选择 | 理由 |
|------|------|------|
| 通用框架 vs 定制故事 | 通用框架 | U1 缺失，无法定制；框架本身可复用，价值不依赖具体目标 |
| 详细步骤 vs 创作自由 | 给出结构骨架，释放内容创作 | SKILL.md："A great /goal prompt does not micromanage the how" |
| 问你要更多信息 vs 直接产出 | 直接产出最小方案，标注待确认 | 你要求"在现有信息下可安全执行"，且 SKILL.md 说"如果 ramble 覆盖了基础，就不问" |
| 英文 /goal prompt vs 中文方案 | 中文方案为主，附英文 /goal prompt | 你的明确要求优先；/goal prompt 作为可复用资产保留 |

### 3.6 衡量方式

| 维度 | 如何衡量"做到了" |
|------|------------------|
| 具体性 | 故事中没有"坚持""努力""变好"等抽象词，每句话都有具体场景或行动 |
| 画面感 | 第三方读完能在脑中形成电影般的画面（有时间、地点、人物、动作、感官细节） |
| 可坚持性 | 第四幕的"转折行动"是一个你明天就能做的具体行为，而非需要长期意志力的决心 |
| 可观察完成 | 存在一个填好的 Markdown 文件，五幕均已填写，且通过了三遍迭代检查 |

### 3.7 停止条件

在以下情况下**停止执行并回到你这里确认**，而不是自行推进：

1. 需要你提供具体目标内容才能继续定制时（U1）。
2. 需要写入除本地 Markdown 之外的任何外部系统时（发消息、创建日历、调用 API 等）。
3. 需要引用本地文件系统中我未验证存在的路径时。
4. 发现输入中出现真实的个人敏感信息（身份证号、银行卡号等），需要你确认处理方式时。
5. 任何需要编造数据、来源或已完成动作才能继续的情况。

---

## 4. /goal prompt（按 fable-goal 七段式生成）

以下 prompt 可直接粘贴到新会话中运行。它指导新会话帮用户将任意抽象目标转化为故事化 Markdown 文档。

```
I want you to help me turn an abstract goal into a vivid, concrete fable—a short narrative in Chinese with a character, a setting, obstacles, and a turning point—so the goal feels tangible and easier to stick to. The deliverable is a single Markdown document that walks me through a five-act story structure (departure, longing, obstacle, turning point, return), each act with 2–3 guiding questions I answer in my own words, followed by my filled-in story. You have full creative freedom on how you guide me, how you phrase the questions, and how you help me sharpen vague answers into concrete scenes—show me what you're capable of. You can accomplish this many ways, so before you start, take stock of the tools and MCPs you actually have, go find or fetch any references, frameworks, or assets you need along the way, but do not call any external APIs, send messages, or touch anything outside a single local Markdown file. Before you call it done, do at least three iteration passes: read the entire story aloud and flag anything hollow or clichéd, check every claim for realism ("would I actually do this tomorrow?"), and polish in sensory details so a stranger could picture it like a film scene. When it's ready, save the complete Markdown document—framework plus my filled-in story—to a local file named fable-goal-story.md in the current working directory and show me the full text. A Chinese Markdown document with a five-act story framework, my filled-in fable, and three iteration passes completed, saved as fable-goal-story.md, is your /goal. Work completely autonomously and do not ask me for anything until you are all done.
```

**Assumptions:**
- 交付物为本地 Markdown 文件（`fable-goal-story.md`），因为你未指定其他目的地，且你禁止外部动作。
- 故事语言为中文，因为你要求中文方案。
- 五幕结构来自叙事学经典框架（启程→渴望→障碍→转折→归来），非编造的数据或来源。
- 新会话会先向你询问具体目标内容（因为 U1 缺失，这是 prompt 运行时唯一需要你输入的部分），然后自主完成其余工作。

---

## 5. 自检结果

### 5.1 /goal prompt 机械检查（对照 `goal_prompt_self_check.py` 六项）

| # | 检查项 | 结果 | 说明 |
|---|--------|------|------|
| 1 | 词数 150–350 | **通过** | 约 260 词（英文） |
| 2 | 目标行 "is your /goal" | **通过** | 包含 "...is your /goal." |
| 3 | 自主指令 "work completely autonomously" / "do not ask me" | **通过** | 包含 "Work completely autonomously and do not ask me for anything until you are all done." |
| 4 | 验证循环（iteration passes / 介质匹配动作） | **通过** | 包含 "three iteration passes: read the entire story aloud..., check every claim..., polish in sensory details..."（匹配 goal_prompt_patterns.md 中 "Written content" 介质的 "read it aloud pass; check every claim"） |
| 5 | 创作自由条款 | **通过** | 包含 "You have full creative freedom..." 和 "You can accomplish this many ways..." |
| 6 | 交付目的地 | **通过** | 包含 "save...to a local file named fable-goal-story.md in the current working directory" |

> 注：`goal_prompt_self_check.py` 在当前环境因 Python 执行超时无法运行，以上为逐条手动对照脚本源码中的正则表达式验证。

### 5.2 判断性检查（SKILL.md step 5 中的人工项）

| # | 检查项 | 结果 |
|---|--------|------|
| 1 | deliverable + quantity 足够具体，陌生人能判断完成 | **通过**——"a single Markdown document with five-act story framework + filled-in fable + three iteration passes"，完成条件可观察 |
| 2 | 每个命名的资源都已验证 | **通过**——未命名任何外部工具/路径/MCP；仅用 discovery mandate 让新会话自行探查 |

### 5.3 反模式检查

| 反模式 | 是否触犯 |
|--------|----------|
| 微观管理 how | 否——未规定步骤顺序或具体写法 |
| 幻影资源 | 否——未引用任何未验证的路径或工具 |
| 不可验证的完成 | 否——完成 = 存在填好的 Markdown 文件 + 三遍检查 |
| 目标行被埋没 | 否——目标行是最后一句，之后无内容 |
| 编造 stakes | 否——未编造受众数字或虚假紧迫感 |
| 多轮提问螺旋 | 否——未提问，用假设+待确认列表替代 |

---

## 6. 下一步

1. **你提供具体目标**（U1）后，我可以将通用框架定制为你的专属故事化目标文档。
2. 如果你确认交付物形态不是 Markdown 文档而是其他（如网页、模板卡片等），告诉我，我会调整 /goal prompt。
3. 如果你希望我直接运行上面的 /goal prompt（即在当前会话中帮你生成故事化目标文档），请给出你的具体目标。
4. 如果你有具体的时间节点或依赖任务需要纳入故事，请一并提供。

---

## 7. 实际读取的 Skill 文件及影响规则

| 文件路径 | 读取状态 | 对本方案的影响 |
|----------|----------|----------------|
| `fable-goal/fable-goal/SKILL.md` | 已完整读取 | **核心依据**。决定了：七段式 prompt 结构、wrong-tool check 流程、六槽位提取法、"验证后命名"原则、三遍迭代验证、150–350 词限制、反模式清单、Assumptions 输出格式。本方案第 0 节的错配检查直接来自第 10 行 "Wrong-tool check first"；第 3 节的三遍检查来自 step 5；第 5 节自检表来自 step 5 的六项清单。 |
| `fable-goal/fable-goal/references/goal_prompt_patterns.md` | 已完整读取 | **验证介质匹配依据**。"Written content" 行（"read it aloud pass; check every claim and link"）直接决定了 /goal prompt 中三遍迭代的具体动作设计。失败模式表（幻影资源、不可验证完成、编造 stakes）指导了第 2 节风险识别。 |
| `fable-goal/fable-goal/scripts/goal_prompt_self_check.py` | 已完整读取源码 | **机械自检依据**。六项正则检查（goal_line、autonomy_directive、verification_loop、creative_freedom、destination、word_count）直接对应第 5.1 节的检查表。因环境超时未执行脚本，改为手动逐条对照源码中的正则模式验证。 |

### 关键规则如何塑造了本方案

- **"Never name phantom resources"** → 我没有引用任何未验证存在的文件路径、工具或 MCP，尽管 SKILL.md 提到了 `brand.md`、`~/.claude/CLAUDE.md` 等——我验证了它们不存在后选择不引用。
- **"Done must be observable"** → 方案的完成标准不是"想清楚了"而是"存在一个填好的 Markdown 文件且通过三遍检查"。
- **"Never invent stakes"** → 我没有编造受众规模、虚假截止日期或紧迫感。
- **"Ask only when it matters; one batch max"** → 我没有向你提问，而是将缺失项列为待确认（U1–U6），给出不依赖它们也能运行的最小方案。
- **"Micromanage the how" 反模式** → 故事框架只给引导问题和结构，不规定你必须怎么写每一句话。
- **"Freedom without a concrete deliverable is scope-creep"** → /goal prompt 中创作自由条款紧接在明确的 deliverable（"a single Markdown document with five-act story structure"）之后，防止新会话跑偏。
