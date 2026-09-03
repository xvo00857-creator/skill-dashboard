# 编辑说明

## 一、修订原则

- 保留原稿全部事实与时间顺序，未增删任何情节、人物或对话。
- 修订重点为结构梳理、用词订正与语句节奏微调，不续写结局、不添加新设定。

## 二、具体改动

| 位置 | 原文 | 修订 | 理由 |
|------|------|------|------|
| 第一章首段 | 一团橙色的**晴影** | 一团橙色的**光晕** | "晴影"非汉语通用词，语义与雾中灯火弥散的意象不符；"光晕"指雾气中灯光形成的模糊光圈，贴合原意。 |
| 全篇结构 | 六个连续段落，无章节划分 | 分为三章（一、码头登船；二、舱内异象；三、船尾对话） | 原稿起承转合隐含但未显化，分章后结构完整、层次清晰。 |
| 第一章末段 | 林迟不记得自己见过他**，但**对方已经把一张旧船票推过窗口**。**票面上的日期是十年前**，**背面却写着今天的时间。 | 林迟不记得自己见过他**。**对方已经把一张旧船票推过窗口**：**票面上的日期是十年前，背面却写着今天的时间。 | 长句拆短，以冒号引出船票细节，节奏更利落。 |
| 第二章首句 | **她**登船后发现 | 登船后，**她**发现 | 主语后置，更符合汉语叙事习惯。 |
| 第二章 | "只有林迟两手空空"接在列举后同一段 | 独立成段 | 强化林迟与其他乘客的对比，突出"两手空空"这一关键伏笔。 |
| 第三章 | "船尾传来三下敲击声。水手告诉她……"同一段 | "船尾传来三下敲击声。"独立成段 | 制造停顿与悬念，引出水手的台词。 |
| 第三章 | 抵达对岸**前** | 抵达对岸**之前** | 语气更自然。 |

## 三、实际读取的 Skill 文件（ZIP 内相对路径）

1. `after-hours-editorial-template/SKILL.md`
2. `after-hours-editorial-template/assets/template.html`
3. `after-hours-editorial-template/references/checklist.md`
4. `after-hours-editorial-template/example.html`

## 四、影响本次结果的具体规则

**直接适用：**

- **SKILL.md Workflow 第 3 条**："Keep three narrative pages in sequence; do not increase default page dwell above 3 seconds."——据此将原稿划分为三章，保持叙事顺序不变；每章篇幅简短，对应"每页停留不超过 3 秒"的克制原则。
- **checklist.md P0**："The template preserves a three-page editorial narrative in one scene flow."——三章划分遵循同一叙事流，不插入额外情节或倒叙。
- **checklist.md P1**："Typography hierarchy clearly separates kicker, display serif, and metadata labels."——映射到文本层面，以章节序号（一/二/三）作为层级标签，与正文区分。

**未适用（Skill 面向 HTML 动效产物，与本次纯文本修订任务无关）：**

- Workflow 第 1 条"Read active `DESIGN.md`"：Skill 包内不存在 DESIGN.md 文件，该步骤无法执行；不影响文本修订。
- Workflow 第 2、4、5、6 条（复制 template.html 为 index.html、保留 GSAP 动效、单文件 HTML 内联 CSS/JS、禁用 localStorage/confirm 等沙箱 API）：本次交付物为 Markdown 文本，不涉及 HTML/CSS/JS。
- checklist 中关于 1920×1080 画布、多列擦除转场、胶片颗粒、键盘章节跳转（1/2/3/R）、cursor-follow 光晕、30fps 导出等 P0/P1/P2 项：均为视频/HTML 动效验收项，不适用于文本。

## 五、其他发现（备查）

- checklist.md P0 要求 SKILL frontmatter 包含 `od.scenario: live-artifacts`，但 SKILL.md 实际 frontmatter 中无此字段（仅有 `od.mode: template`、`od.surface: video`、`od.type: hyperframes` 等）。此为 Skill 包内部不一致，不影响本次修订。
- 原稿结尾为开放式悬念（水手台词"那你要交还的，可能是你自己"），修订稿原样保留，未续写，以遵守"保留所有事实"的要求。
