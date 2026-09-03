# Inbox Triage 约束变化调整方案

> 场景：可用时间临时减半 + 周三（2026-08-12）新增不可移动评审会 + 结果需交接给另一位同事
> 基准日期：2026-08-10（周一）
> 依据 Skill：`inbox-triage` v1.0.0

---

## 一、约束变化如何改变原方案

Skill 默认方案建立在三个隐含前提上：**时间充裕**（每天 1–3 次、每次 9 小时窗口全量处理）、**单人闭环**（报告发给自己、上下文在脑中）、**节奏稳定**（按固定 cadence 运行、KB 持续学习）。本次三个变化分别击穿了这三个前提：

| 变化 | 击穿的前提 | 对原方案的影响 |
|---|---|---|
| 可用时间减半 | 时间充裕 | 不能再对所有非低优先级邮件读完整线程+起草；必须提高跳过阈值、压缩单封邮件处理深度 |
| 周三不可移动评审会 | 节奏稳定 | 周三当天无法执行常规 triage；周二必须完成"周三前需响应"的所有事项，否则断档 |
| 交接给同事 | 单人闭环 | 报告不能再是"给自己看的 30 秒扫描"；必须补足上下文、明确待办、标注决策依据，让接手人无需追问即可行动 |

**核心判断**：这不是"做少一点"，而是**从"全量深度处理"切换到"分级分流+可交接产出"模式**。目标从"清空收件箱"变为"确保关键事项不遗漏、其余事项可被同事安全接手"。

---

## 二、目标

1. **不遗漏关键邮件**：截止周三评审会前，所有需要本人回复/决策/出席的邮件均已处理或明确委派。
2. **产出可交接**：接手同事拿到 triage 报告 + 更新后的 KB，能独立继续处理后续邮件，无需反向确认上下文。
3. **守住安全底线**：全程只创建草稿、绝不发送（Skill 非协商规则）；不因赶时间而跳过安全校验。
4. **可衡量**：有明确的"完成定义"，让接手人和本人都能判断本次 triage 是否达标。

---

## 三、依据

本方案严格依据 `inbox-triage` Skill 的规定流程与约束，针对变化做调整。引用的关键规则：

- **Step 0 Grill-me**：本次属于 on-demand 非常态运行，应问 Q1（搜索窗口覆盖）和 Q2（类别跳过）。
- **Step 1 搜索窗口**：默认 9h（2x-daily），但 on-demand 默认 24h、可 Q1 覆盖。
- **Step 3 分类**：最低优先级（newsletter/automation/spam）跳过线程读取——此规则在时间压缩时应更激进地应用。
- **Step 5 决策框架**：TAKE IT / WORTH / PASS / FLAG 四类，FLAG 不起草。
- **Step 6 草稿**：只为合理候选起草；FLAG 不起草；绝不发送。
- **Step 7 报告**：固定 6 段结构（Overview / Stats / Action Needed / Quick Reference / Detailed Cards / Footer）。
- **Step 8 KB 更新**：blocklist 追加、tracker 更新、学习模式观察。
- **Critical Rules**：DRAFTS ONLY、Accuracy over speed（不确定就 FLAG）、Respect the KB、Transparency。
- **Error Handling**：100+ 封新邮件时聚焦优先类别；缺少工具时 halt 并说明。

---

## 四、调整后的执行步骤

### 前置检查（不可跳过）

1. **运行 `kb_reader.py --workspace <WORKSPACE>`**，确认 4 个必需文件（`email-taxonomy.md`、`email-patterns.md`、`blocklist.md`、`tracker.md`）和 `triage-log/` 目录存在。若缺失 → halt，先运行 `inbox-setup`。本次不编造 KB 内容。
2. **确认邮件工具可用**（Gmail MCP / Outlook MCP / IMAP 至少一个）。若不可用 → halt，告知"无邮件工具注册"。
3. **运行 `search_window_calculator.py`** 确定本次窗口。

### Step 0：Grill-me 覆盖问题（本次必问，非常态运行）

- **Q1**：本次为 on-demand 非常态运行+交接场景，建议覆盖搜索窗口为 **48 小时**（覆盖周末+周一，确保接手同事不会漏掉周一前的邮件），而非默认 24h。理由：交接场景下"漏邮件"的代价远大于"多扫几封低优先级"。
- **Q2**：建议跳过 **newsletters / automation / spam** 三类（Skill 本就跳过其线程读取，本次直接跳过搜索结果中的呈现，只在 Stats 中计数）。不跳过其他类别——交接时不能替同事决定忽略整类业务邮件。

### Step 1：搜索窗口

使用 `search_window_calculator.py --cadence on-demand --override-hours 48 --now <当前ISO时间>`。

以 2026-08-10（周一）下午执行为例：
- Window start：2026-08-08（周六）下午
- Window end：执行时刻
- Run label：Afternoon/Evening（视执行时间而定）
- 额外做一次 **starred unread** 搜索（Skill Step 2 规定的 secondary query），捕获被标记但可能超出 48h 窗口的邮件。

### Step 2：邮件搜索

按 Skill 规定执行两条查询：
- Primary：Inbox + sent，after window_start
- Secondary：Starred unread

收集 sender / subject / date / snippet / thread ID / labels。

### Step 3：分类（调整：三级分流而非两级）

Skill 默认对"非最低优先级"读完整线程。时间减半后改为**三级分流**：

| 级别 | 判定条件 | 处理深度 |
|---|---|---|
| **P0 立即处理** | 发件人在 VIP 列表；或 subject/snippet 含紧急关键词（deadline、today、ASAP、评审、cancel、reschedule、合同、审批）；或 Active Conversation 中本人是最后待回复方；或与周三评审会直接相关 | 读完整线程 → Step 4/5/6 全流程 |
| **P1 快速判断** | 非 P0，但属于 Action Required / Active Conversations / New Opportunities / Important-Personal | 只读 snippet + tracker 历史 → 快速归类为 TAKE/WORTH/PASS/FLAG；仅 TAKE IT 和明确 Action Required 起草，其余只记录判断和理由 |
| **P2 批量跳过** | Newsletters / automation / spam / 已知 blocklist 匹配 / FYI 类 informational | 不读线程，按 Skill 规则直接跳过；在 Stats 中计数 |

**关键取舍**：P1 中原本会起草的 WORTH CONSIDERING 邮件，本次**只写判断要点、不起草完整回复**，改为在交接报告中标注"建议接手人跟进"。这节省了草稿撰写时间，但增加了接手人的工作量——这是时间减半下的必然转移，需在报告中明确说明。

### Step 4：发件人研究（调整：大幅收窄）

Skill 默认对未知机会发件人做 web 研究。时间减半后：
- **跳过所有 P2 邮件的发件人研究**。
- **P1 邮件**：仅查 blocklist + tracker，不做 web 研究；不认识的发件人直接标注"unknown sender, flagged for接手人判断"。
- **P0 邮件**：按 Skill 原流程做（blocklist → tracker → web 研究如需要）。
- 若 web 搜索不可用：按 Skill Error Handling，跳过研究步骤并在日志中注明。

### Step 5：建议（决策框架不变，应用范围收窄）

对 P0 和 P1 邮件应用 `triage_decision_framework.md` 的四类判断：

| 类别 | 本次处理 |
|---|---|
| **TAKE IT** | P0 → 起草完整回复；P1 → 起草简短回复（3 句以内） |
| **WORTH CONSIDERING** | P0 → 起草带 1–2 个澄清问题的回复；P1 → **不起草**，在报告中标注建议接手人跟进 |
| **PASS** | P0 → 起草礼貌拒绝；P1 → 批量记录拒绝理由，不起草单封回复（除非对方明确等待回复） |
| **FLAG FOR REVIEW** | 不起草，在报告 Detailed Cards 中完整呈现；**交接场景下 FLAG 比例会更高**——拿不准的宁可 FLAG 给接手人，不要在时间压力下做错判断 |

**Financial 类邮件**：按框架规定始终 FLAG，不起草——交接场景下更不能替本人做财务决策。

**VIP override**：VIP 发件人绕过 PASS 过滤，但不绕过 FLAG。VIP 的非常规请求仍然 FLAG。

### Step 6：草稿（安全底线不变）

- **只创建草稿，绝不发送**。此规则在时间压力下更需严格遵守——赶时间时最容易误点发送。
- 使用 `email-patterns.md` 的 voice rules、forbidden tokens、sign-offs、hard rules。
- 草稿创建在原线程中，设置 `to` 和 `subject`（`Re: [原主题]`）。
- **交接场景额外要求**：每封草稿在 triage-log 中记录 draft 所在线程 ID + 一封简短的中文备注（给接手人看），说明"这封草稿为什么这样写、发送前需确认什么"。Skill 默认报告不包含 draft text preview（避免与邮件客户端重复），但交接时在**日志**中加备注是合理的补充——备注是给接手人的上下文，不是邮件正文预览。

### Step 7：报告交付（调整：从"给自己看"变为"给接手人用"）

Skill 默认报告格式为"发给自己的 HTML 草稿"。本次改为**Markdown 文件**（可直接在飞书/邮件/文档中分享给同事），保留 Skill 规定的 6 段结构，但每段做交接增强：

**报告标题**：`Inbox Triage — 交接报告 — 2026-08-10（周一）`

1. **Overview**（调整）：除"发生了什么、有无紧急事项"外，增加一段**交接说明**——本人可用时间减半、周三评审会不可用、哪些事项已处理、哪些需接手人跟进、KB 状态。
2. **Stats**（不变）：processed / drafts created / action needed / skipped 计数。增加 P0/P1/P2 分布计数。
3. **Action Needed**（增强）：按截止时间排序，每项标注 **谁来做**（本人周三前 / 接手人 / 待确认）。周三评审会相关事项单独列出并置顶。
4. **Quick Reference**（不变）：按发件人字母序，一行一封：`**发件人** — 一句话摘要 + 建议`。
5. **Detailed Cards**（增强）：P0 邮件和 FLAG 邮件必须有详细卡片。每张卡片增加 **"交接备注"** 字段：背景上下文、已做的判断、建议接手人怎么做、风险点。
6. **Footer**（增强）：生成时间戳 + KB 更新摘要 + **接手人下一步指引**（如何运行下一次 triage、KB 在哪、遇到问题联系谁）。

**格式说明**：Skill 规定 HTML 时用 inline CSS + 颜色编码。本次交付 Markdown，用文字标签替代颜色（如 `[TAKE IT]`、`[FLAG]`、`[PASS]`），不损失信息。

### Step 8：KB 更新（核心保留，学习循环简化）

| KB 文件 | 本次操作 |
|---|---|
| `blocklist.md` | **正常追加**新的拒绝发件人和模式——接手人需要这些来避免重复处理。不删除任何条目。 |
| `tracker.md` | **正常更新**：新增 follow-up、标记 overdue、更新状态。这是交接最核心的文件——接手人通过 tracker 知道什么在等、什么逾期。在 Update Log 中明确标注"2026-08-10 交接 triage 更新"。 |
| 学习模式观察 | **简化**：本次不做模式提炼（如"你总是拒绝 X"的建议），这是长期优化，非当务之急。但如发现明显的新 blocklist 模式，仍正常追加。 |

### Step 9：内部日志（不变，但增加交接字段）

写入 `${WORKSPACE}/Email/triage-log/2026-08-10-handover.md`：
- 所有 Skill 规定的字段（processed / recommendations / drafts with IDs / KB updates / follow-ups / observations）
- **增加**：交接备注（每封草稿的中文说明）、P0/P1/P2 分流结果、周三评审会相关事项清单、未处理事项及原因

### Step 10：空收件箱处理（不适用但需检查）

即使无新邮件，仍需：
- 检查 `tracker.md` 中今日到期和逾期项
- 周三评审会前的待办事项必须在本报告中呈现
- 如有逾期项 → 在 Action Needed 中标红

### 后置校验（不可跳过）

1. **运行 `draft_safety_validator.py --action-log <log文件>`**，确认无 send-shaped 调用。若 FAIL → 立即检查是否有误发送，按 validator 输出的 ACTION REQUIRED 处理。
2. **自检 checklist**（见第七节）。

---

## 五、优先级与取舍总结

### 优先级排序（从高到低）

1. **周三评审会相关邮件** — 不可移动的硬约束，相关邮件必须在周二结束前处理完毕
2. **P0 邮件**（VIP / 紧急 / 本人待回复的活跃线程）— 完整处理+起草
3. **tracker.md 更新** — 交接的核心载体，必须准确
4. **P1 中的 TAKE IT 和明确 Action Required** — 简短起草
5. **FLAG 邮件的详细卡片** — 让接手人能做判断
6. **P1 中的 WORTH/PASS** — 只记录判断，不起草
7. **blocklist 追加** — 防止接手人重复劳动
8. **P2 批量跳过** — 只计数
9. **KB 学习模式提炼** — 本次不做

### 关键取舍

| 取 | 舍 | 理由 |
|---|---|---|
| 扩大搜索窗口到 48h | 单封邮件处理深度 | 交接场景下漏邮件的代价 > 多扫邮件的成本 |
| P1 的 WORTH 不起草，标注给接手人 | 为所有候选起草 | 时间减半，草稿撰写是最大时间消耗；接手人有判断能力 |
| FLAG 阈值降低（更多 FLAG） | 在时间压力下快速做判断 | Skill 规则"Accuracy over speed"；错判比 FLAG 代价大，交接场景下尤甚 |
| 报告写成交接文档（更长、更详细） | 30 秒自扫式简报 | 接手人没有本人的上下文，必须补足 |
| 保留 blocklist/tracker 更新 | 简化/跳过 KB 更新 | 这两个文件是接手人继续工作的基础；学习提炼是锦上添花 |
| 周三前事项周二全部处理完 | 均匀分配到三天 | 周三当天不可用，不能留到周三 |
| Markdown 文件交付 | HTML 邮件草稿给自己 | 交接需要可分享的文档格式；Markdown 通用且可转换 |

---

## 六、风险

| 风险 | 影响 | 缓解 |
|---|---|---|
| 漏判 P0 邮件（紧急邮件被分到 P1/P2） | 关键事项延误 | 搜索时用 secondary query（starred unread）兜底；分类后人工快速扫一遍所有 subject 行，确认无遗漏 |
| 接手人看不懂上下文 | 交接失败、反复追问 | Detailed Cards 中每封 FLAG/P0 邮件都写交接备注；tracker.md 中每项有足够 context |
| 赶时间误点发送 | 错误邮件发出、不可撤回 | 严格只用 draft verb；运行 draft_safety_validator 后置校验；Skill 规定此为非协商规则 |
| 周三评审会相关邮件在周二之后才到达 | 评审准备不充分 | 在报告中明确标注"周三评审会相关邮件如在周二后到达，请立即转发/电话通知本人"；tracker 中设置评审会 follow-up |
| KB 文件缺失或损坏 | triage 无法运行 | 前置运行 kb_reader.py 校验；缺失则 halt 并先运行 inbox-setup，不编造 KB 内容 |
| 邮件工具不可用 | 无法搜索邮件 | 前置检查工具可用性；不可用则 halt 并明确告知，不假装处理 |
| 接手人修改了 KB 导致后续 triage 行为变化 | 预期外的分类/草稿行为 | 在 Footer 中注明 KB 位置和修改风险；建议接手人首次运行时先观察不改动 |
| 48h 窗口邮件量过大（>100 封） | 时间仍然不够 | 按 Skill Error Handling 规则，聚焦优先类别；在报告中说明总量并标注"P2 未逐一阅读" |

---

## 七、衡量方式（完成定义）

本次 triage 达标当且仅当：

- [ ] `kb_reader.py` 运行结果为 PASS（4 个必需文件 + triage-log/ 目录均存在）
- [ ] 搜索窗口已通过 `search_window_calculator.py` 计算，覆盖 ≥48h
- [ ] 所有搜索结果邮件已被分类为 P0/P1/P2 之一，无遗漏
- [ ] 所有 P0 邮件已读完整线程并完成 Step 4/5/6 流程
- [ ] 周三评审会相关邮件已全部识别并在 Action Needed 中置顶
- [ ] 所有草稿均通过 draft API 创建（非 send），`draft_safety_validator.py` 运行结果为 PASS
- [ ] `blocklist.md` 已追加新发现的拒绝项（如有）
- [ ] `tracker.md` 已更新：新增 follow-up、标记 overdue、Update Log 有交接条目
- [ ] 交接报告（Markdown）包含 Skill 规定的 6 段结构，且每段的交接增强字段已填写
- [ ] triage-log 已写入，包含交接备注
- [ ] 报告 Footer 包含接手人下一步指引
- [ ] 未编造任何邮件数据、发件人、KB 内容或已完成动作

---

## 八、下一步

### 本人（周三评审会前）

1. **周二结束前**：review 所有 P0 草稿，确认后发送（Skill 规定草稿只创建不发送，发送需本人手动操作）。
2. **周二结束前**：确认 tracker 中所有周三前到期项已处理或委派。
3. **周三评审会前**：检查是否有新到的评审相关邮件（本次 triage 窗口之后到达的）。

### 接手同事

1. 阅读交接报告的 Overview + Action Needed + Footer。
2. 确认 KB 位置（`${WORKSPACE}/Email/`），可运行 `kb_reader.py --workspace <WORKSPACE>` 查看状态。
3. 按常规 cadence 继续运行 triage（`2x-daily`，9h 窗口），使用 `search_window_calculator.py --cadence 2x-daily`。
4. 处理报告中标注为"建议接手人跟进"的 WORTH/FLAG 邮件。
5. 如遇需本人决策的事项，通过 tracker 中记录的联系方式沟通（本次不编造联系方式）。
6. 本人回来后，运行一次 triage 并 review tracker 变化，重新接管。

---

## 九、实际读取的 Skill 文件及影响本次结果的规则

### 读取的文件清单

| 文件 | 路径 | 读取状态 |
|---|---|---|
| SKILL.md | `inbox-triage/inbox-triage/SKILL.md` | 完整读取 |
| kb_file_contract.md | `references/kb_file_contract.md` | 完整读取 |
| triage_decision_framework.md | `references/triage_decision_framework.md` | 完整读取 |
| drafts_only_safety.md | `references/drafts_only_safety.md` | 完整读取 |
| kb_reader.py | `scripts/kb_reader.py` | 完整读取 + `--sample` 运行验证 PASS |
| search_window_calculator.py | `scripts/search_window_calculator.py` | 完整读取 + 实际运行验证输出 |
| draft_safety_validator.py | `scripts/draft_safety_validator.py` | 完整读取 + `--sample-pass`/`--sample-fail` 双向运行验证 |

### 影响本次结果的关键规则

1. **DRAFTS ONLY — NEVER SEND**（SKILL.md Critical Rules #1、drafts_only_safety.md 全文）：决定了本方案中所有"回复"均为草稿、后置校验必须运行 validator、赶时间时更不能妥协。这是本次方案中唯一标注为"非协商"的规则。

2. **Fail-fast on missing KB**（SKILL.md Prerequisites、kb_file_contract.md、kb_reader.py）：决定了前置检查步骤——不编造 KB 内容，缺失则 halt。本方案明确说明"本次不编造 KB 内容"。

3. **最低优先级跳过线程读取**（SKILL.md Step 3）：原方案已有的分级思想，本次扩展为 P0/P1/P2 三级分流。P2 的处理方式直接沿用此规则。

4. **FLAG for Review 不起草**（SKILL.md Step 5、triage_decision_framework.md）：决定了时间压力下"拿不准就 FLAG"的策略——FLAG 给接手人比错判更安全。Financial 类始终 FLAG 的规则也直接沿用。

5. **Accuracy over speed**（SKILL.md Critical Rules #3）：时间减半场景下最容易被牺牲的原则，但 Skill 明确规定"错误的自动草稿比没有草稿更糟"，直接影响了"降低 FLAG 阈值"和"P1 WORTH 不起草"的取舍。

6. **报告 6 段结构**（SKILL.md Step 7）：决定了交接报告的组织方式。本方案保留结构、增强内容，而非另起炉灶。

7. **tracker.md 和 blocklist.md 每次更新**（SKILL.md Step 8、kb_file_contract.md）：决定了即使时间压缩，这两个文件的更新仍保留——它们是接手人继续工作的基础。学习模式观察被简化，但核心读写不跳过。

8. **triage-log 为审计追踪**（SKILL.md Step 9、drafts_only_safety.md）：决定了日志必须写入、且是 validator 的检查对象。交接场景下日志额外承载了"给接手人的备注"功能。

9. **100+ 邮件时聚焦优先类别**（SKILL.md Error Handling）：预见到 48h 窗口可能带来大量邮件，此规则为"聚焦 P0、批量处理 P2"提供了 Skill 内的依据。

10. **Grill-me Q1/Q2 仅在非常态时问**（SKILL.md Step 0）：本次属于 on-demand 非常态+交接，因此 Q1（覆盖窗口为 48h）和 Q2（跳过 newsletters 等）都应问，而非默认跳过。

11. **报告不含 draft text preview**（SKILL.md Step 7 Anti-pattern、drafts_only_safety.md）：Skill 明确禁止在报告中预览草稿正文。本方案的"交接备注"是写给接手人的上下文说明（为什么这样写、发送前确认什么），不是邮件正文预览，两者不矛盾。

12. **VIP bypass 不绕过 FLAG**（triage_decision_framework.md VIP Override Discipline）：决定了即使是 VIP 的非常规邮件，交接场景下仍然 FLAG 给本人/接手人判断，不自动起草。
