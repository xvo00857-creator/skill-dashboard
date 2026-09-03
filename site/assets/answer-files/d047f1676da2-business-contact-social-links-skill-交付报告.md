# business-contact-social-links-skill 交付报告

> 交付时间：2026-08-12
> Skill 名称：business-contact-social-links-skill
> 表格分类：网页与互动
> 安装位置：`~/.doubao/agent_mode/workspace/.user_skills/business-contact-social-links-skill/`

---

## 一、Skill 真实能力边界（以 SKILL.md 为准）

本 Skill 是一个**命令行数据提取工具**，通过 BrowserAct 云端浏览器 API 完成两类任务：

1. 输入**公司名** → 调用 Google 商务联系人模板，返回公司官网与社媒主页；
2. 输入**网址 URL** → 调用社媒链接抓取模板，返回 LinkedIn / Facebook / X(Twitter) / Instagram / YouTube / TikTok 的规范主页链接。

脚本自动判断输入类型并路由到对应模板，输出结构化 JSON。它**不是网页前端组件**，没有 DOM、没有页面路由、没有 CSS/视觉系统，也不生成任何可交互网页界面。

### 与题目假设的冲突说明

题目要求"支持键盘操作、加载与空状态、慢网络、窄屏设备，不破坏现有路由和视觉规范，并交付无障碍说明和跨尺寸测试结果"。这些是典型的**网页前端验收项**。经核对 SKILL.md 与脚本源码，本 Skill 无前端界面，因此：

- **未新建任何网页 / H5 / 交互页面**——那将超出 SKILL.md 定义的职责边界（SKILL.md 第 9–17 行明确其能力为"提取官网与社媒链接"，调用方式为 `python -u ./scripts/...py`）。
- 题目中的前端概念在本 CLI 工具上存在**可验证的对应物**，下文逐项给出实测结果；无法对应的项已明确标注。
- "不破坏现有路由和视觉规范"：本次仅新增安装，未改动任何现有文件，不存在路由或视觉被破坏的可能。

---

## 二、改动说明

### 实际改动

| 项 | 内容 |
|---|---|
| 安装 | 将解压后的 Skill 完整复制到用户技能目录 `~/.doubao/agent_mode/workspace/.user_skills/business-contact-social-links-skill/` |
| 文件清单 | `SKILL.md`、`scripts/business_contact_social_links.py`（共 2 个文件，与源 ZIP 逐字节一致，已用 `diff -r` 校验） |
| 脚本改动 | **未改动**。脚本已具备输入路由、加载日志、慢网超时/重试、空结果兜底等机制；强行改造会偏离 SKILL.md 的输出契约与调用约定 |
| 现有路由/视觉 | 未触碰任何其他 Skill 或系统文件，无破坏风险 |

### 未改动脚本的原因

SKILL.md「调用方法」（第 33–42 行）与「数据输出」（第 51–62 行）规定了固定的命令行调用方式和 JSON 输出契约，Agent 依赖 stdout 中的 `Detected ...`、`[HH:MM:SS] Task Status:`、`Error:` 等前缀做状态判断。修改这些格式会破坏 Skill 与 Agent 之间的约定，故保持原样。

---

## 三、各项要求的验证结果

### 1. 键盘操作

- **结论：原生支持，无需改动。**
- 本 Skill 唯一交互方式是命令行：`python -u ./scripts/business_contact_social_links.py "<目标>"`，全程键盘输入、文本输出，不依赖鼠标。
- 实测：无参数时输出 Usage 并以退出码 1 退出；有参数时直接执行。

### 2. 加载状态（Loading）

- **结论：已具备，实测通过。**
- 脚本在轮询阶段每 10 秒输出一行带时间戳的状态日志，格式为 `[HH:MM:SS] Task Status: <status>`（源码第 83–84 行）。
- SKILL.md 第 44–49 行明确要求 Agent 据此判断任务仍在运行，不要误判为卡死。
- 实测（假密钥触发启动阶段）：能看到 `Detected ...` 路由提示与后续错误输出；时间戳日志格式与文档一致。

### 3. 空状态（Empty State）

- **结论：代码层面有兜底，但表现为"回传原始任务 JSON"而非显式空提示，已如实标注。**
- 源码第 110–116 行：任务完成后若 `output.string` 为空，则回退返回 `json.dumps(task_info, ensure_ascii=False)`（完整任务对象），而非打印"无结果"。
- SKILL.md 第 71 行规定：若返回空结果，Agent 应**自动重试一次**；第二次仍失败则停止并报错。
- **未用真实空结果任务实测**（需有效 API Key 与一个恰好无输出的任务），此项为**代码审查确认**，非运行时验证。

### 4. 慢网络 / 网络异常

- **结论：已具备超时与轮询重试，实测连接失败路径通过。**
- 三处 HTTP 请求均设 `timeout=30` 秒（源码第 52、79、107 行）。
- 启动任务连接失败：捕获异常并输出 `Error: Connection to API failed - <原因>`，返回 None（第 54–56 行）。
- 轮询阶段网络抖动：捕获异常后输出 `[HH:MM:SS] Polling error: ... Retrying...`，sleep 10 秒后继续轮询，不中断（第 93–97 行）。
- 总轮询上限 900 秒（15 分钟），超时输出 `Error: Task polling timed out after 900 seconds.`（第 72、100 行）。
- **实测**：用仅作用于子进程的死代理（`HTTPS_PROXY=http://127.0.0.1:1`）模拟断网，脚本正确输出 `Error: Connection to API failed - ... ProxyError ... Connection refused`。
- 观察：启动阶段连接失败时脚本退出码为 0（非非零），但 stdout 含 `Error:` 前缀；SKILL.md 第 71 行正是以"output starts with `Error:`"作为失败判据，二者一致。

### 5. 窄屏设备

- **结论：纯文本输出，无固定宽表格，任意宽度可自然折行；实测 30/40 列可读。**
- 各输出路径最大行长：Usage 100 字符、无 Key 错误 78 字符、鉴权错误 69 字符。
- 无 ANSI 颜色/控制码、无等宽表格、无水平排版依赖。
- **实测**：用 `fold -w 40`、`fold -w 30` 模拟窄屏，文本逐行折行后语义完整；URL 在真实终端中为视觉折行、底层文本不截断，不影响复制。
- 说明：`fold` 为保守模拟（硬插入换行），真实终端表现优于该模拟。

### 6. 路由

- **结论：输入自动路由正确，实测 5 组输入全部通过。**
- 脚本通过启发式规则判断输入是 URL 还是公司名（第 26–27 行）：以 `http://`、`https://`、`www.` 开头，或含 `.` 且不含空格 → 走 URL 模板；否则走公司名模板。
- 实测结果：

| 输入 | 路由结果 |
|---|---|
| `OpenAI` | Company Name（Google 商务联系人模板） |
| `https://www.example.com/` | URL（社媒链接抓取模板） |
| `www.example.com` | URL |
| `example.com` | URL |
| `ByteDance Inc` | Company Name（含空格，未误判为域名） |

### 7. 视觉规范

- **结论：无 UI 视觉系统；CLI 输出格式统一。**
- 状态日志统一为 `[HH:MM:SS] Task Status: <status>`；错误统一以 `Error:` 开头；成功输出为结构化 JSON。
- 无颜色、无图标、无排版，不存在视觉规范冲突。

---

## 四、无障碍说明

本 Skill 为纯文本 CLI，无障碍特性如下：

1. **屏幕阅读器兼容**：全部输出为 UTF-8 纯文本（脚本第 10–11 行强制 stdout/stderr 使用 UTF-8），无 ANSI 转义码、无颜色、无图标装饰，屏幕阅读器可逐行朗读。
2. **键盘可达**：无鼠标依赖，所有操作通过键盘命令完成。
3. **无低对比度/色盲问题**：不使用颜色编码传递信息。
4. **状态可感知**：加载阶段有持续的时间戳文本日志，不会出现无反馈的静默等待。
5. **错误可读**：错误信息为完整英文句子，包含原因与下一步指引（如无 Key 时给出 Console 地址）。
6. **局限**：错误与日志为英文；JSON 结果在超窄屏（<30 列）会频繁折行，建议在 ≥40 列终端查看结构化结果。

---

## 五、跨尺寸测试结果

| 模拟宽度 | 测试内容 | 结果 |
|---|---|---|
| 默认宽度（≥100 列） | Usage / 无 Key 错误 / 鉴权错误 | 单行完整显示，通过 |
| 40 列 | Usage 折行 | 命令名与 URL 视觉折行，语义完整，通过 |
| 30 列 | 无 Key 错误折行 | 步骤文本与 URL 折行，层级清晰，通过 |
| 任意宽度 | 时间戳状态日志 | 单行最长 69 字符，≥70 列可单行显示；更窄时折行不影响信息，通过 |

测试方式：实际运行脚本捕获 stdout，用 `fold -w N` 模拟窄屏硬折行；行长用 `awk` 统计。未在真实移动设备上测试（CLI 工具运行于桌面 Python 环境，移动端不适用）。

---

## 六、未完成项 / 需用户提供

### 阻塞项：BrowserAct API Key 未配置

- 环境检查确认 `BROWSERACT_API_KEY` **未设置**。
- 依据 SKILL.md 第 19–22 行的硬性规定：**未设置 Key 时不得采取其他措施，须请用户提供**。
- 因此**未执行任何真实的公司名/网址提取任务**，也未产生真实社媒链接数据。报告中所有"实测"均为不依赖 Key 的边界测试（参数校验、路由判断、错误分支、网络异常、输出格式）。

> 由于您尚未配置 BrowserAct API Key，请访问 [BrowserAct Console](https://www.browseract.com/reception/integrations) 获取您的 Key。提供后我可立即按 SKILL.md 执行真实提取任务。

### 其他说明

- 假密钥测试仅验证了"Invalid authorization"错误分支（SKILL.md 第 67 行：不得重试，引导检查 Key），**未验证**"concurrent / too many running tasks"并发限制分支（需有效 Key 且账号达并发上限，无法构造）。
- 真实提取结果的 JSON 结构（公司名模式与 URL 模式的字段）以 SKILL.md 第 54–62 行描述为准，本次未运行时验证。

---

## 七、实际读取的 Skill 文件（相对路径）

1. `business-contact-social-links-skill/SKILL.md`（完整读取，86 行）
2. `business-contact-social-links-skill/scripts/business_contact_social_links.py`（完整读取，141 行）

压缩包内仅含以上两个文件，无其他附件或资源。

---

## 八、实际影响交付结果的 SKILL.md 规则

**规则：第 19–22 行「API Key Setup」——"Before running, check the `BROWSERACT_API_KEY` environment variable. If not set, do not take other measures; ask and wait for the user to provide it."**

这条规则直接决定了本次交付的边界：

- 因为环境变量未设置，我**没有**尝试用其他方式绕过（如硬编码 Key、改用其他抓取服务、或自行编造社媒链接结果）；
- 真实提取任务被阻塞，交付物改为"安装 + 不依赖 Key 的边界实测 + 评估报告"，并明确标注未完成项；
- 这也符合题目"不得编造运行结果、无法访问的资源要明确标注"的要求。

另一条影响交付的规则是第 9–17 行对能力的界定（仅做链接提取的 CLI 工具），它使我判定题目中的网页前端验收项不能通过"新建一个网页"来满足，否则属于扩张职责。
