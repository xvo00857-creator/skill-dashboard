# nuwa-skill 评测报告：面向"整理研究资料并生成汇报"的最小可用技能组合

**评测对象**：nuwa-skill（frontmatter name: `huashu-nuwa`，分类：思考与决策）
**评测日期**：2026-08-11
**评测环境**：macOS / Python 3.9.6 / 豆包 Agent 运行时

---

## 一、输入假设

| # | 假设项 | 说明 |
|---|--------|------|
| 1 | **需求语义** | "整理研究资料并生成汇报"指：围绕某个人物或主题，采集/接收多源资料，按维度结构化整理，综合提炼后产出可供他人阅读的汇报物（文档或演示文稿）。 |
| 2 | **资料来源** | 可能包含用户已有素材（PDF、transcript、字幕、笔记）和/或需要联网新检索的公开信息。nuwa-skill 的"本地语料模式"和"纯网络搜索模式"分别对应这两种情况。 |
| 3 | **汇报形态** | "汇报"在中文职场语境下通常指结构化文档或 PPT 演示文稿，而非一个可运行的程序文件。 |
| 4 | **运行时** | 本环境支持 Agent Skills 协议，skill 目录为 `~/.claude/skills/`；具备联网搜索能力、Python3、bash；可调用 lark-doc / lark-ppt 等已装 skill。 |
| 5 | **不假设** | 不假设研究对象一定是公众人物（nuwa 支持主题 Skill 和非公众人物的本地语料模式）；不假设用户一定需要联网检索。 |

## 二、验收标准

1. **能力覆盖**：所选组合必须端到端覆盖"资料采集 → 结构化整理 → 综合提炼 → 汇报物生成"四个环节，无断链。
2. **最小性**：在满足覆盖的前提下，skill 数量最少；能用 1 个不用 2 个，能用 2 个不用 3 个。
3. **可安装**：每个 skill 在本环境可实际安装或已安装，目录结构和 frontmatter 可被运行时识别。
4. **可执行**：组合中涉及的脚本/工具经实际运行验证，而非仅凭文档推断。
5. **可验证**：给出明确的验证方法和通过标准，第三方可复跑确认。
6. **诚实边界**：明确标注 nuwa-skill 不适用的环节和已知缺陷，不夸大能力。

---

## 三、nuwa-skill 能力实测

### 3.1 它实际做什么

nuwa-skill 是一个**人物/主题思维框架蒸馏器**。输入人名或主题，经 6 路并行调研 → 三重验证提炼 → 生成可运行的人物视角 SKILL.md。其完整流程为 Phase 0（入口分流）→ Phase 0.5（建目录）→ Phase 1（6 Agent 并行采集）→ Phase 1.5（调研检查点）→ Phase 2（框架提炼）→ Phase 2.5（提炼确认）→ Phase 3（构建 SKILL.md）→ Phase 4（质量验证）→ Phase 5（双 Agent 精炼）。

### 3.2 与"整理研究资料并生成汇报"的逐项对照

| 环节 | nuwa-skill 覆盖情况 | 依据 |
|------|---------------------|------|
| 多源资料采集 | **部分覆盖** | Phase 1 的 6 Agent 框架可采集，但 6 个维度（著作/对话/表达/他者/决策/时间线）是为人物蒸馏设计的；主题 Skill 变体（SKILL.md"特殊场景"节）可调整为按流派/人物分配，但仍非通用调研维度。 |
| 本地素材整理 | **覆盖** | "本地语料模式"支持 PDF/transcript/SRT/博客/社媒导出/内部文档，按 6 维度分类、识别信息缺口、定向补充。srt_to_transcript.py 可清洗字幕。 |
| 资料结构化存储 | **覆盖** | Phase 0.5 规定了自包含目录结构（`references/research/01-06.md`），所有调研文件存于 skill 目录内，可独立复制使用。 |
| 来源质量管控 | **覆盖** | 信息源优先级表（一手>二手>推测）、黑名单（知乎/微信公众号/百度百科永远排除）、每条信息标注来源 URL 和可信度、区分"他说的/别人说他的/我推断的"。 |
| 调研汇总 | **覆盖（有脚本）** | `merge_research.py` 自动扫描 01-06.md，统计来源数、一手/二手占比、关键发现、矛盾点，输出检查点表格。**已实测通过**。 |
| 综合提炼 | **部分覆盖** | Phase 2 的三重验证（跨域复现/生成力/排他性）和矛盾保留原则是优秀的综合方法论，但提炼目标是"心智模型"而非通用调研结论；用于人物汇报可直接用，用于通用主题需改造。 |
| 质量自检 | **覆盖（有脚本，有缺陷）** | `quality_check.py` 检查 6 项标准。**已实测可运行，但存在误报缺陷**（见 3.3）。 |
| 汇报物生成 | **不覆盖** | nuwa 的最终产物是一个**可运行的 SKILL.md**（人物视角 skill），不是面向利益相关方的汇报文档或 PPT。它没有文档排版、演示文稿生成、图表绘制能力。Phase 1.5/2.5 的检查点表格是内部确认用，非交付物。 |

### 3.3 实测发现的缺陷与限制

| # | 问题 | 实测证据 |
|---|------|---------|
| 1 | **quality_check.py 对有序列表误报** | 对 paul-graham 示例运行时，"诚实边界"项报 FAIL（0 条），但该文件第 375 行起有 `## 诚实边界` 且含 5 条编号列表（`1.` `2.`…）。脚本正则只匹配 `^[-*]\s+`（无序列表），不识别有序列表。这是脚本 bug，不是示例内容缺失。 |
| 2 | **merge_research.py 只认标准目录结构** | 对 munger 示例运行时报"目录不存在"，因为该示例的调研文件直接放在 `references/` 下（中文文件名），而非 `references/research/01-06.md`。脚本不兼容非标准布局。 |
| 3 | **引用的外部 skill 均未安装** | SKILL.md Phase 1"利用已安装的信息获取 Skill"节列出了 `gemini-video`、`web-article-reader`、`agent-reach`、`huashu-research`、`pdf` 五个 skill。实测在本环境所有 skill 根目录下均未找到，这些增强能力不可用。 |
| 4 | **并行 subagent 依赖运行时支持** | SKILL.md 失败模式表明确提到"部分 runtime 会在 Phase 1 挂起死等"，需降级为串行。本环境的 subagent 机制与 nuwa 假设的 Claude Code 式 spawn 不同，实际使用时需按降级表串行执行。 |
| 5 | **产物形态错配** | nuwa 产物是 SKILL.md + 调研底稿，不是汇报文档/PPT。直接把 SKILL.md 当汇报交付，受众无法使用（它是给 AI runtime 加载的指令文件）。 |

### 3.4 脚本实测结果

```
=== merge_research.py（paul-graham 示例）===
┌──────────────┬──────────┬──────────────────────────┐
│ Agent        │ 来源数量  │ 关键发现                  │
├──────────────┼──────────┼──────────────────────────┤
│ 著作           │ 47       │ 一、人物背景, 二、核心著作... │
│ 对话           │ 40       │ 一、重要播客与访谈...        │
│ 表达           │ 21       │ 1. 风格总论...              │
│ 他者           │ 32       │ 一、对PG思维模式的深层分析... │
│ 决策           │ 47       │ 一、职业轨迹...             │
│ 时间线          │ 0        │ 时间线总览...              │
├──────────────┼──────────┼──────────────────────────┤
│ 总来源数      │ 187      │ 一手占比: 81/153          │
│ 矛盾点        │ 5处      │ ...                       │
│ 信息不足维度   │ 无       │ —                         │
└──────────────┴──────────┴──────────────────────────┘
→ 正常退出，输出符合预期

=== quality_check.py（paul-graham 示例）===
  心智模型数量       ✅ PASS  5个心智模型
  模型局限性        ✅ PASS
  表达DNA辨识度     ✅ PASS  23项
  诚实边界         ❌ FAIL  0条（误报：实际有5条编号列表）
  内在张力         ✅ PASS  4处
  一手来源占比       ✅ PASS（跳过：来源区未标注类型关键词）
结果: 5/6 通过

=== srt_to_transcript.py ===
构造测试 SRT → 输出干净文本，去时间戳/序号/HTML，正常

=== download_subtitles.sh ===
依赖 yt-dlp，实测 /Users/bytedance/.local/bin/yt-dlp 已安装
```

---

## 四、最小可用技能组合

### 4.1 结论

| 组合 | Skill | 职责 | 必要性 |
|------|-------|------|--------|
| **组合 A（汇报=文档）** | **nuwa-skill（huashu-nuwa）** | 资料采集编排、结构化整理、来源质量管控、调研汇总、综合提炼方法论 | 必需：提供调研整理的骨架和质量门禁 |
| | **lark-doc** | 将整理提炼后的内容生成为飞书文档（汇报正文） | 必需：nuwa 不产出面向人的汇报文档 |
| **组合 B（汇报=PPT）** | **nuwa-skill（huashu-nuwa）** | 同上 | 必需 |
| | **lark-ppt** | 将整理提炼后的内容生成为 PPT 演示文稿 | 必需：nuwa 不产出 PPT |

**最小数量：2 个 skill。** nuwa-skill 单独无法生成汇报物；lark-doc/lark-ppt 单独不具备 nuwa 的多维度调研编排、来源黑名单、检查点门禁和汇总脚本能力。

### 4.2 为什么不选其他 skill

| 候选 skill | 不选原因 |
|------------|---------|
| doubao-academic-researcher | 面向学术文献调研（论文/学术方向），有系统检索和引用核验能力，但不提供 nuwa 的人物/主题多维调研框架、自包含目录结构、merge_research 汇总脚本和检查点门禁。若需求是纯学术文献综述可替代 nuwa，但本需求是"整理研究资料并生成汇报"，nuwa 的框架更通用且已实测。 |
| doubao-book-writer | 面向长文档写作（手册/白皮书/书稿），有组装/精修/去 AI 味能力，但它是写作工作台，不负责资料采集和结构化整理；与 lark-doc 功能重叠，不是最小集所需。 |
| doubao-visualization | 仅在汇报需要图表时按需加入，不是端到端最小集的必要组件。 |
| nuwa 引用的 gemini-video 等 5 个外部 skill | 本环境均未安装，无法纳入可用组合。 |

### 4.3 兼容性分析

| 维度 | 情况 |
|------|------|
| **协议兼容** | nuwa-skill 使用标准 Agent Skills 协议（YAML frontmatter + markdown），与 lark-doc/lark-ppt 同协议，可共存于同一 skill 目录。 |
| **目录兼容** | nuwa 安装到 `~/.claude/skills/nuwa-skill/`，lark-doc/lark-ppt 已在 `.skills/` 目录，互不冲突。nuwa 生成的子 skill 放在 `~/.claude/skills/[name]-perspective/`，与母体隔离。 |
| **运行时兼容** | nuwa 的并行 subagent 在本环境需降级为串行（按其失败模式表）；lark-doc/lark-ppt 通过 skill 机制调用，无并行依赖。两者无冲突。 |
| **数据流兼容** | nuwa 的产出物（`references/research/01-06.md` 调研底稿 + Phase 2 提炼结论）是 markdown 文本，可直接作为 lark-doc/lark-ppt 的输入素材，格式无障碍。 |
| **已知不兼容** | quality_check.py 的有序列表误报不影响主流程（它是质检辅助工具，可人工复核）；merge_research.py 要求标准 `references/research/01-06.md` 布局，使用时需遵守。 |

---

## 五、安装与调用顺序

### 5.1 安装顺序

```
步骤 1：安装 nuwa-skill
  cp -R nuwa-skill-main ~/.claude/skills/nuwa-skill
  验证：ls ~/.claude/skills/nuwa-skill/SKILL.md 存在
        head -9 ~/.claude/skills/nuwa-skill/SKILL.md 显示 name: huashu-nuwa
        python3 ~/.claude/skills/nuwa-skill/scripts/merge_research.py --help 可运行

步骤 2：确认 lark-doc（或 lark-ppt）已安装
  本环境已预装于 .skills/lark-doc 和 .skills/lark-ppt，无需额外安装。
  验证：对应目录下 SKILL.md 存在且 frontmatter 可读。

步骤 3（可选）：安装 yt-dlp（仅当需要下载 YouTube 字幕时）
  本环境已安装于 /Users/bytedance/.local/bin/yt-dlp，无需操作。
```

### 5.2 调用顺序（端到端）

```
阶段 1：nuwa-skill 负责"整理研究资料"
  ├─ Phase 0/0A/0B：明确研究对象（人物走直接路径，主题走主题 Skill 变体，模糊需求走诊断路径）
  ├─ Phase 0.5：创建工作目录，遵守 references/research/01-06.md 标准布局
  ├─ Phase 1：采集资料
  │   ├─ 有本地素材 → 本地语料模式（先读素材，按维度分类，缺口定向补搜）
  │   ├─ 无本地素材 → 网络搜索模式（6 维度串行采集，本环境不并行）
  │   ├─ 视频字幕 → download_subtitles.sh + srt_to_transcript.py
  │   └─ 遵守来源黑名单（知乎/微信公众号/百度百科排除）
  ├─ Phase 1.5：运行 merge_research.py 生成检查点表格，人工确认调研质量
  └─ Phase 2：按三重验证方法论综合提炼（人物→心智模型；主题→共识框架+流派分歧）

阶段 2：lark-doc / lark-ppt 负责"生成汇报"
  ├─ 将 Phase 2 提炼结论 + references/research/ 底稿作为输入素材
  ├─ 用 lark-doc 创建飞书文档（汇报正文：背景/方法/发现/结论/来源）
  │   或用 lark-ppt 创建演示文稿（汇报幻灯片）
  └─ 交付在线文档链接或文件

质检（可选但建议）：
  └─ 若汇报涉及人物视角 skill 的产出，运行 quality_check.py 并人工复核其误报项
```

**关键边界**：nuwa 的 Phase 3-5（构建 SKILL.md、质量验证、双 Agent 精炼）在本需求中**不执行**——那些步骤服务于生成可运行人物 skill，不是生成汇报。停在 Phase 2 的提炼结论，交给 lark-doc/lark-ppt 产出汇报物。

---

## 六、验证方法

### 6.1 安装验证

| 验证项 | 方法 | 通过标准 |
|--------|------|---------|
| nuwa-skill 可发现 | `ls ~/.claude/skills/nuwa-skill/SKILL.md` | 文件存在 |
| frontmatter 合法 | `head -9 ~/.claude/skills/nuwa-skill/SKILL.md` | 含 `name: huashu-nuwa` |
| 脚本可执行 | `python3 ~/.claude/skills/nuwa-skill/scripts/merge_research.py` 无参数 | 打印用法提示而非报错 |
| lark-doc 可用 | 检查 `.skills/lark-doc/SKILL.md` 存在 | 文件存在且可读 |

### 6.2 功能验证（端到端冒烟测试）

| 步骤 | 方法 | 通过标准 |
|------|------|---------|
| 调研汇总 | 对任一标准结构示例运行 `python3 scripts/merge_research.py examples/paul-graham-perspective` | 输出 6 行维度表格 + 总来源数 + 矛盾点，退出码 0 |
| 字幕清洗 | 构造小型 SRT 运行 `srt_to_transcript.py` | 输出无时间戳/序号的纯文本 |
| 质量检查 | 运行 `quality_check.py examples/paul-graham-perspective/SKILL.md` | 输出 6 项检查结果（注意：诚实边界项可能误报，需人工确认内容实际存在） |
| 汇报生成 | 用 lark-doc 基于一份调研底稿创建测试文档 | 文档可访问，内容含调研发现和来源 |

### 6.3 已知需人工复核项

- **quality_check.py "诚实边界"误报**：若你的 SKILL.md 使用有序列表（`1.` `2.`），脚本会报 0 条。需人工打开文件确认 `## 诚实边界` 节下实际有 ≥3 条局限。这是脚本正则缺陷，不是内容问题。
- **merge_research.py 布局要求**：调研文件必须放在 `references/research/` 下且命名为 `01-writings.md` 至 `06-timeline.md`，否则脚本报"目录不存在"。

---

## 七、实际读取的 Skill 文件清单

以下为本次评测中我**实际打开并阅读**的 nuwa-skill 文件（相对 nuwa-skill-main/ 根目录）：

| 相对路径 | 阅读目的 |
|----------|---------|
| `SKILL.md` | 主文件，理解完整流程、能力边界、硬规则 |
| `README.md` | 安装方式、运行时兼容性、仓库结构 |
| `references/extraction-framework.md` | 三重验证方法论、矛盾处理、质量自检清单 |
| `references/fidelity-scorecard.md` | 保真度评分卡（双 agent 盲测方法） |
| `references/skill-template.md` | 产物模板，确认 nuwa 输出是 SKILL.md 而非汇报文档 |
| `scripts/merge_research.py` | 确认汇总脚本的输入要求和输出格式 |
| `scripts/quality_check.py` | 确认质检脚本的检查项和正则逻辑（发现有序列表误报） |
| `scripts/srt_to_transcript.py` | 确认字幕清洗脚本的功能和用法 |
| `scripts/download_subtitles.sh` | 确认字幕下载脚本的依赖（yt-dlp）和语言优先级 |
| `examples/paul-graham-perspective/SKILL.md`（第 373-400 行） | 确认 quality_check 误报原因：诚实边界用有序列表 |

此外，我通过 `head` 命令读取了以下已安装 skill 的 frontmatter 以确认能力描述（未全文阅读）：
- `.skills/lark-doc/SKILL.md`（前 20 行）
- `.skills/lark-ppt/SKILL.md`（前 15 行）

## 八、哪些 SKILL.md 规则实际影响了本次执行

| SKILL.md 规则 | 对执行的影响 |
|---------------|-------------|
| **"关键区分：捕捉的是 HOW they think，不是 WHAT they said"** | 让我准确判断 nuwa 的提炼目标是心智模型而非通用调研结论，这是它与"生成汇报"需求错配的核心原因。 |
| **Phase 0.5"所有调研文件必须存在 skill 目录内部""Skill 必须是自包含的"** | 我据此验证了目录结构要求，并发现 merge_research.py 强制 `references/research/01-06.md` 布局（munger 示例因非标准布局而脚本报错）。 |
| **Phase 1"利用已安装的信息获取 Skill"节列出的 5 个外部 skill** | 我逐一检查了这 5 个 skill 在本环境是否存在，结论是均未安装，因此未将它们纳入组合。 |
| **Phase 1 信息源黑名单（知乎/微信公众号/百度百科）** | 这是 nuwa 调研质量管控的核心规则，我将其列为 nuwa 在组合中不可替代的价值之一。 |
| **Phase 1 失败模式与降级路径表** | 其中"运行环境不支持并行 subagent → 降级为串行执行"直接影响了调用顺序设计：本环境需串行采集。 |
| **Phase 1.5 检查点 + merge_research.py** | 我实际运行了该脚本验证其可用性，确认它是调研整理环节的可执行工具。 |
| **Phase 3 读取 skill-template.md 构建 SKILL.md** | 我读了模板，确认 nuwa 的最终产物是人物视角 SKILL.md（含角色扮演规则、身份卡、心智模型等），不是汇报文档——这是需要 lark-doc/lark-ppt 补位的直接依据。 |
| **Phase 4 通过标准表 + quality_check.py** | 我实际运行了质检脚本，发现了有序列表误报缺陷，并在验证方法中标注需人工复核。 |
| **"特殊场景 > 主题 Skill"变体表** | 让我确认 nuwa 对非人物主题有适配路径（按流派分配 Agent、提取共识+分歧），因此它对主题类调研整理也有条件适用，而非仅限人物。 |
| **反模式黑名单第 4 条"在信息不足时强行生成"** | 我在报告中明确标注了 nuwa 不覆盖汇报生成环节，没有假装它能产出文档/PPT。 |
| **反模式黑名单第 7 条"不报成本量级直接开跑"** | 我在调用顺序中保留了 Phase 0A 的档位确认环节（快速/标准/深度）。 |

---

## 九、缺失项与已完成范围声明

| 项 | 状态 |
|----|------|
| nuwa-skill.zip 解压与 SKILL.md 全文阅读 | ✅ 已完成 |
| 全部 3 个 references 文件阅读 | ✅ 已完成 |
| 全部 4 个 scripts 文件阅读 | ✅ 已完成 |
| 脚本实际运行验证 | ✅ 已完成（merge_research / quality_check / srt_to_transcript 均实跑；download_subtitles 仅验证依赖 yt-dlp 存在，未实际下载视频） |
| nuwa-skill 安装到本环境 | ✅ 已完成（`~/.claude/skills/nuwa-skill/`） |
| 外部依赖 skill 存在性检查 | ✅ 已完成（5 个引用 skill 均未安装） |
| lark-doc / lark-ppt 能力确认 | ✅ 已完成（读取 frontmatter 确认） |
| 端到端实际生成一份汇报 | ❌ 未执行——本任务要求是"筛选最小可用技能组合并说明"，不是实际执行一次完整调研汇报。组合的可行性基于脚本实测和能力对照，而非一次完整端到端跑通。 |
| quality_check.py 误报修复 | ❌ 未修改——评测任务不要求改代码，仅报告缺陷。 |
| nuwa 引用的 5 个外部 skill 安装 | ❌ 未安装——它们不在本环境中，且不是最小组合的必要组件（nuwa 可降级用通用搜索工具替代）。 |
