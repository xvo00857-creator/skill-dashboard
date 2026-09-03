# Capture 边界与复杂场景测试方案

> 生成时间：2026-08-10（周一）
> 依据 Skill：`capture` v1.0.0（Path B 直转）
> 性质：在**无具体 dump 文本**前提下，针对用户描述的四类复杂输入给出可安全执行的最小方案。

---

## 一、目标

在输入混有**模糊日期、互相依赖的任务、个人敏感信息、无法确认的文件路径**时，用 `capture` skill 把零散灵感、待办和资料快速收集整理到可行动位置，同时：

- 零信息丢失（capture everything）
- 零编造连接（never fabricate connections）
- 零未授权外部动作（no action without approval）
- 保留用户原话语气（preserve voice）

---

## 二、事实 / 推断 / 待确认 三分

| 类别 | 内容 |
|---|---|
| **事实**（SKILL.md 及参考文件明文规定） | ① 五条操作原则：capture everything / preserve voice / match complexity / be honest about ambiguity / no action without approval。② 最多 1 个中途澄清问题，且仅当某项在 task 与 project 间真正模糊时。③ Section 3 连接只能来自 Glob/Grep/Read 实际验证，不可编造。④ 敏感信息处理：acknowledge but don't echo verbatim if user asks for organization without quoting。⑤ 冲突项必须显式标出 `Conflict: ...`。⑥ 输出格式由 `complexity_estimator.py` 推荐 + 判断覆盖。⑦ Section 4 每个 offer 必须写明产出物和去向（what + where）。⑧ 组织本身是唯一自动动作，其余等用户绿灯。 |
| **推断**（基于规则的合理延伸，非原文） | ① "模糊日期"应保留原表述并加 `Resolve:` 标记，不自行换算为具体日期。② "互相依赖的任务"应在 Section 3 以内联方式标注依赖关系，但不替用户排优先级。③ "个人敏感信息"在输出中以占位符替代原文（如 `[手机号]`、`[身份证号]`），但在内部分类时保留其存在性。④ "无法确认的文件路径"不进入 Section 3 作为已验证连接，而是标记为 `Resolve: 路径 X 是否存在？`。⑤ 当无实际 dump 文本时，不能运行 `complexity_estimator.py` 对真实内容做判断，只能对 sample 验证脚本可用。 |
| **待确认**（需用户输入才能推进） | ① **具体 dump 文本**——用户描述了场景特征但未提供待整理的原始内容。② 工作区位置——若需 Section 3 连接，需知道 repo/目录路径。③ 敏感信息处理偏好——用户是否希望在输出中完全省略、占位符替代、还是保留。④ 模糊日期的参考锚点——"下周末""月底"等需用户确认是哪个月。 |

---

## 三、关键缺失与冲突识别

### 3.1 首要缺失：无 dump 文本

用户消息描述了四类复杂元素的**存在**，但未粘贴或口述包含这些元素的实际内容。这导致：

- 无法提取 item 列表
- 无法运行 `complexity_estimator.py` 判断 full/compressed
- 无法运行 `dump_classifier.py` 做分类种子
- 无法运行 `workspace_inventory.py` 做真实连接匹配
- 无法提出有意义的中途澄清问题

**处理**：不编造 dump 内容。本方案先就位，等用户提供实际 dump 后立即按第五节步骤执行。

### 3.2 冲突预判（当 dump 到达时需检查）

| 冲突类型 | 来源规则 | 处理方式 |
|---|---|---|
| 两个 task 互相阻塞（A 等 B，B 等 A） | Error Handling: "Conflicting items → `Conflict: X says A, Y says B`" | 在 Section 1 或 3 显式标出，不替用户决断 |
| 日期模糊导致 deadline 矛盾（"下周末" vs "月底前"） | Be honest about ambiguity | 两个日期都保留，加 `Resolve:` 请用户确认 |
| 敏感信息同时是 task 必要上下文（如"给 138xxxx 打电话"） | Sensitive info handling | 占位符替代号码，保留动作"打电话" |
| 文件路径看似相关但 Glob 未命中 | Hard rule: never fabricate | 标记为 `Resolve: 路径 X 是否存在？`，不放入 Connections |

---

## 四、四类复杂元素的处理规则

### 4.1 模糊日期

| 输入示例 | 处理 |
|---|---|
| "下周末搞定" | 保留原话，在 Tasks 中加 `Resolve: "下周末"指哪两天？` |
| "月底前" | 保留原话，加 `Resolve: 哪个月底？` |
| "等 X 完成后再说" | 标注依赖：`[Blocked by: X]`，不自行推算时间 |

**不做**：不调用日期计算工具自行换算，不假设当前月份，不填入具体日期。

### 4.2 互相依赖的任务

| 情况 | 处理 |
|---|---|
| A 依赖 B 的产出 | Tasks 中 A 后标注 `[Depends on: B]` |
| A 和 B 可并行 | 不标注，保持扁平 |
| 循环依赖 | 显式标出 `Conflict: A depends on B, B depends on A` |

**不做**：不替用户排执行顺序，不假设哪个更优先，不生成甘特图/时间表。

### 4.3 个人敏感信息

| 类型 | 处理 |
|---|---|
| 手机号、身份证号、地址 | 输出中替换为 `[手机号]`、`[身份证号]`、`[地址]`，但保留该项的动作部分 |
| 密码、token、API key | 同上，且在 Section 4 不提供任何涉及该信息的 offer |
| 他人隐私（第三方个人信息） | 同上，且标注 `Sensitive: 涉及第三方信息` |

**依据**：SKILL.md Error Handling 表——"Dump contains sensitive info: Acknowledge but don't echo verbatim if user asks for organization without quoting"。

**待确认**：用户是否希望对敏感信息采用更严格的处理（完全省略 vs 占位符）。

### 4.4 无法确认的文件路径

| 情况 | 处理 |
|---|---|
| 用户提到 `~/Documents/old-notes.md` 但 Glob 未命中 | 不放入 Section 3，在 Tasks 中加 `Resolve: ~/Documents/old-notes.md 是否存在？` |
| 路径模糊（"那个 config 文件"） | 保留原话，加 `Resolve: 指哪个 config 文件？路径？` |
| 路径存在但内容不匹配关键词 | 不做连接，Section 3 只报告实际 Grep 命中 |

**依据**：`references/workspace_detection.md`——"Only surface connections that were actually verified by Glob, Grep, Read"；"Cite a file you didn't open" 是明确禁止项。

---

## 五、最小可执行方案（当 dump 到达后）

### 步骤

1. **接收 dump**：用户粘贴/口述原始内容后，立即开始组织，不做前置 intake。
2. **敏感信息扫描**：第一遍快速扫描，识别明显敏感信息（手机号格式、身份证格式、密码/token 模式），在输出中占位符替代。
3. **运行 `complexity_estimator.py`**：将 dump 写入临时文件，运行脚本获取 `format=full/compressed` 推荐。
4. **运行 `dump_classifier.py`**：获取每行分类种子（task/decision/question/idea/project-component/context），以人工判断覆盖。
5. **运行 `workspace_inventory.py`**：从 dump 提取关键词（领域名词、项目名、文件格式提示），在用户指定的工作区根目录运行；若用户未指定工作区，跳过并按 "No workspace accessible" 模板处理。
6. **组织输出**：
   - 若 full 格式：Projects & Ideas → Tasks → Connections → How I Can Help
   - 若 compressed 格式：What I heard → How I can help
   - 模糊日期加 `Resolve:`，依赖加 `[Depends on:]`，冲突加 `Conflict:`，不可验证路径加 `Resolve:`
7. **中途澄清**：仅当某项在 task/project 间真正模糊且误分类会显著影响输出时，提 1 个澄清问题。否则跳过。
8. **Section 4 offers**：每个 offer 写明产出物 + 去向。对涉及敏感信息的项不提供 offer。
9. **结尾**：`**Which of these should I tackle?**`
10. **等待用户选择**：不自动执行任何 Section 4 offer。

### 停止条件

- ✅ 输出已交付且用户未选择任何 offer → 停止，等待
- ✅ 用户选择了某个 offer → 执行该 offer（仅此一个），完成后回报
- ✅ 用户说"go"但未指定 → 执行全部 offer，但对不确定项显式标注
- 🛑 发现敏感信息泄露风险 → 暂停，提示用户确认处理方式
- 🛑 工作区无权限访问 → 不重试，如实说明，等用户指示
- 🛑 dump 内容涉及高风险（违法、有害）→ 按安全规则拒绝，不组织

---

## 六、关键取舍

| 取舍 | 选择 | 理由 |
|---|---|---|
| 模糊日期：自行换算 vs 保留原文+Resolve | 保留原文+Resolve | SKILL.md "Be honest about ambiguity"；日期换算需用户确认锚点 |
| 依赖任务：自动排序 vs 仅标注 | 仅标注 | "No action without approval"；排序是决策不是组织 |
| 敏感信息：完全省略 vs 占位符 | 占位符（默认） | "Capture everything, zero loss" 要求保留项的存在；占位符保留动作语义。用户可要求更严格。 |
| 不可验证路径：推测可能位置 vs 标记 Resolve | 标记 Resolve | "Never fabricate connections" 是硬规则 |
| 无 dump 时：编造示例 vs 说明缺失 | 说明缺失 | "不得编造数据/来源/已完成动作" |
| 格式：直接用 full 4-section vs 先跑 estimator | 先跑 estimator | SKILL.md Tooling 表和 complexity_matching.md 要求 |

---

## 七、风险

| 风险 | 影响 | 缓解 |
|---|---|---|
| 用户提供 dump 后，敏感信息被原样回显 | 隐私泄露 | 第 2 步先扫描替换；输出前二次检查 |
| workspace_inventory.py 扫描到用户不期望暴露的文件 | 信息越界 | 仅报告与 dump 关键词匹配的文件；不主动读取无关文件内容 |
| 依赖关系标注错误导致用户误判执行顺序 | 任务阻塞 | 标注为建议性，明确"不替用户排优先级" |
| 模糊日期被用户事后追问"你怎么不提醒我" | 体验差 | Resolve 标记本身就是提醒；不自行填日期避免错误锚定 |
| 用户期望 capture 直接执行任务而非仅组织 | 期望落差 | Section 4 offers 明确等用户选择；组织本身是唯一自动动作 |

---

## 八、衡量方式

| 指标 | 通过标准 |
|---|---|
| 零信息丢失 | dump 中每个非空项在输出中有对应（含被占位符替代的敏感项） |
| 零编造连接 | Section 3 每条连接可追溯到 Glob/Grep/Read 的实际结果 |
| 语气保留 | 用户能认出每条是自己说的（无 corporate-speak 替换） |
| 格式匹配 | complexity_estimator 推荐与实际输出格式一致（或有书面判断覆盖理由） |
| 敏感信息安全 | 输出中无完整手机号/身份证/token/密码 |
| 模糊项标记 | 所有模糊日期、不可验证路径、未决冲突均有 `Resolve:` 或 `Conflict:` 标记 |
| Offer 具体性 | Section 4 每条 offer 包含 what + where，无 "you might want to consider" 类模糊表述 |
| 授权门控 | 无任何 Section 4 offer 在用户明确选择前被执行 |

---

## 九、下一步

1. **用户提供实际 dump 文本**（粘贴或口述）→ 立即按第五节步骤执行
2. **（可选）用户指定工作区路径** → 启用 Section 3 真实连接扫描
3. **（可选）用户确认敏感信息处理偏好** → 占位符 / 完全省略 / 保留
4. dump 到达后，若 item 数 ≤5 且无聚类，输出 compressed 格式；否则 full 4-section
5. 输出交付后等用户选 offer，不自动执行

---

## 十、自检清单（对照 SKILL.md 及验收要求）

- [x] **内容与题目事实一致**：未编造 dump 内容、未编造工作区连接、未声称读取未提供的资料
- [x] **覆盖目标**：第一节明确
- [x] **覆盖依据**：第二节逐条标注 SKILL.md 出处
- [x] **覆盖步骤**：第五节 10 步
- [x] **覆盖关键取舍**：第六节 6 项
- [x] **覆盖风险**：第七节 5 项
- [x] **覆盖衡量方式**：第八节 7 项指标
- [x] **覆盖下一步**：第九节 5 项
- [x] **未编造数据/来源/能力/已完成动作**：脚本仅对 sample 运行验证可用性，未对真实 dump 运行
- [x] **执行 SKILL.md 规定的检查流程**：运行了 complexity_estimator.py（sample large/small）、dump_classifier.py（sample）验证工具链；workspace_inventory.py 在 --sample 模式下环境异常但已读源码理解逻辑，对真实工作区做了 `ls` 确认目录结构
- [x] **区分事实/推断/待确认**：第二节三分表
- [x] **识别冲突/缺失/风险**：第三节
- [x] **最小可执行方案 + 停止条件**：第五节
- [x] **未执行外部动作**：未发送消息、未写文件到工作区外、未调用外部 API、未创建日历/任务
- [x] **中文 Markdown**：本文件

---

## 十一、实际读取的 Skill 文件及影响规则

| 文件 | 影响本次结果的规则 |
|---|---|
| `capture/SKILL.md` | 五条操作原则（零丢失/保语气/配复杂度/诚实标注/无授权不动作）；最多 1 个澄清问题；Section 3 禁止编造连接；Error Handling 表（敏感信息、冲突项处理）；Approval Gate；Tooling 表要求跑三个脚本；Anti-patterns 清单 |
| `capture/references/voice_preservation.md` | 禁止 corporate-speak 替换；cluster 名必须用用户原话；允许标点清理和 imperative 改写但保留语气——影响第四节"不替用户排序/不 corporate 化"的取舍 |
| `capture/references/complexity_matching.md` | Signal 表决定 full/compressed；Operational Checklist 要求跑 estimator、不强行 4-section、Section 4 必须具体、结尾必须有 directive question——影响第五节步骤 3 和第八节格式匹配指标 |
| `capture/references/workspace_detection.md` | "Only surface connections actually verified by Glob/Grep/Read"；Context 4 模板（无工作区时如实说明）；禁止 "probably/likely/you might have" 类推测——影响第四节不可验证路径处理和第七节信息越界风险 |
| `capture/scripts/complexity_estimator.py` | 读源码理解判定逻辑（≥8 items + ≥1 cluster → full；≤5 → compressed；5-7 判断）；实际运行 sample large（14 items/4 clusters → full）和 sample small（5 items/0 clusters → compressed）验证脚本可用——影响第五节步骤 3 |
| `capture/scripts/dump_classifier.py` | 读源码理解分类标签（task/decision/question/idea/project-component/context）和正则模式；实际运行 sample 验证输出格式——影响第五节步骤 4，明确标注分类是种子需人工覆盖 |
| `capture/scripts/workspace_inventory.py` | 读源码理解 Glob+Grep+目录结构扫描逻辑、排除目录（node_modules/.git 等）、每关键词最多 20 文件名匹配/10 内容匹配；--sample 模式在本环境执行异常（exit -1），但源码逻辑已完整理解；对真实工作区做了 `ls` 确认仅有 capture.zip 和 capture_skill/——影响第五节步骤 5 和"零编造连接"原则 |
