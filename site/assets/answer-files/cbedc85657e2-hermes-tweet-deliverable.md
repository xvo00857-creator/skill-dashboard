# Hermes Tweet 社媒发布工作交付

> 生成时间：2026-08-12（UTC+8）
> Skill：hermes-tweet v0.1.6
> 分类：社媒发布

---

## 一、执行摘要（Summary）

- **检查内容**：按 hermes-tweet SKILL.md 要求，检查 Hermes Agent 运行时、`XQUIK_API_KEY`、动作开关 `HERMES_TWEET_ENABLE_ACTIONS`，确认是否具备执行 `tweet_explore` / `tweet_read` / `tweet_action` 的条件。
- **检查原因**：SKILL.md 明确规定，`tweet_read` 需要 `XQUIK_API_KEY`，`tweet_action` 需要显式开启动作开关并经过操作者批准；未满足条件时不得伪造读取结果或执行发布。

### 环境检查结果

| 检查项 | 状态 | 说明 |
|---|---|---|
| Hermes Agent 运行时（`~/.hermes/hermes-agent/venv/`） | **不可用** | 本机未安装 Hermes Agent，`hermes` 命令不存在 |
| `hermes-tweet` 插件 | **未安装** | PyPI 在当前环境无法解析该包；SKILL.md 指定的安装路径依赖 Hermes venv |
| `XQUIK_API_KEY` | **未设置** | 无法调用任何 `tweet_read` 只读端点 |
| `HERMES_TWEET_ENABLE_ACTIONS` | **未设置（默认 false）** | 符合"只读优先"默认值，但即使设为 true 也因缺少运行时无法执行 |
| `tweet_explore` / `tweet_read` / `tweet_action` 工具 | **不可调用** | 三者均为 Hermes Agent 插件工具，仅在 Hermes 运行时内可用 |

### 缺失的必要输入（依据 SKILL.md「Inputs」章节）

SKILL.md 要求在选择路由前确认以下输入，当前均未提供：

1. **Objective（目标）**：未明确——是产品发布、活动推广、客户支持，还是品牌声量监测？
2. **Target（目标对象）**：未提供——账号 handle、推文 URL、关键词、列表或趋势话题均未指定。
3. **Time window（时间窗口）**：未指定——需要分析哪个时间段的时间线？
4. **Action scope（动作范围）**：用户提到"审批后发布"，但未确认本次会话是否需要将 `HERMES_TWEET_ENABLE_ACTIONS` 设为 `true`。
5. **API Key 确认**：未确认 Hermes 运行时主机上已配置 `XQUIK_API_KEY`。

> **结论**：当前无法执行真实的 X/Twitter 内容研究、时间线读取或发布动作。以下交付物为**规划阶段产物**，所有需实时数据或真实操作的部分均已标注「待确认」或「待 Hermes 环境就绪后执行」。未编造任何读取结果、用户评价或已完成操作。

---

## 二、读取路由记录（Read routes）

依据 SKILL.md 工作流，正常应先以 `tweet_explore` 检索端点目录，再以 `tweet_read` 调用目录列出的只读端点。由于 `tweet_explore` 工具在当前环境不可调用，以下为**依据 SKILL.md 与项目 README 规划的预期路由**，尚未实际执行：

| 计划用途 | 预期目录查询词 | 预期工具 | 预期端点（以目录返回为准） | 实际状态 |
|---|---|---|---|---|
| 搜索相关推文 | `search tweets by query` | `tweet_read` | `/api/v1/x/search`（示例，以 `tweet_explore` 返回为准） | **未执行**——缺少 API Key 与运行时 |
| 读取目标账号时间线 | `list recent tweets posted by a user` | `tweet_read` | 目录列出的用户时间线路由 | **未执行**——目标账号未指定 |
| 查看当前趋势 | `/xtrends`（斜杠命令）或 trends 路由 | `tweet_read` | 目录列出的 trends 路由 | **未执行**——缺少运行时 |
| 监控关键词 | `create monitor` | `tweet_action` | 目录列出的 monitor 路由 | **未执行**——动作门控未开启且未审批 |

> 注意：SKILL.md 明确要求"Validate the exact catalog path before calling `tweet_read` or `tweet_action`"，以上端点路径仅为 README 示例，实际路径必须以 `tweet_explore` 返回的目录为准，不得猜测。

---

## 三、推文草稿（Drafts）

### 3.1 字数规则说明

- X 标准帖子上限：**280 个加权字符**。
- 中文/日文/韩文（CJK）字符：每个计 **2** 个加权字符，因此纯中文帖实际上限约 **140 个汉字**。
- URL：固定计 **23** 个字符（无论实际长度）。
- 多数 emoji：计 **2** 个字符。
- 换行：计 **1** 个字符。
- @mention 和 #话题：按可见文本长度计算。

> 以下每条草稿均标注加权字符数，均在 280 以内。

### 3.2 草稿模板（待填入具体主题后定稿）

由于未提供具体产品/活动/品牌信息，以下为合规模板。`【】`内为待替换占位符。

---

#### 草稿 A：产品/功能更新

**简体中文版**

```text
【产品名】上线了【功能名】：一句话说明它解决什么问题。
现已向全部用户开放，欢迎体验后告诉我们你的想法。
#【话题标签】
```

- 加权字符数（不含占位符实际内容）：约 50–70（占位符替换后需重新核算）
- 合规检查：无"行业第一"等绝对化表述；无虚构用户评价；无未经验证的数据。

**自然英文版**

```text
【Product】just shipped 【Feature】: one line on what it helps you do.
Available now for all users — try it and let us know what you think.
#【Hashtag】
```

- 字符数（不含占位符实际内容）：约 110–130（占位符替换后需重新核算）

---

#### 草稿 B：活动/公告

**简体中文版**

```text
【活动名称】将于【日期】开始。
一句话说明参与方式或核心看点。
详情见：【链接】
#【话题标签】
```

- 加权字符数：链接计 23，中文部分约 40–60，总计约 65–85（占位符替换后需重新核算）

**自然英文版**

```text
【Event】kicks off on 【Date】.
One line on how to join or what to expect.
Details: 【URL】
#【Hashtag】
```

- 字符数：链接计 23，英文部分约 80–100，总计约 105–125（占位符替换后需重新核算）

---

#### 草稿 C：内容分享/观点

**简体中文版**

```text
关于【主题】，我们整理了几点观察：
1. 要点一
2. 要点二
3. 要点三
你怎么看？欢迎讨论。
#【话题标签】
```

- 加权字符数：约 60–90（占位符替换后需重新核算）

**自然英文版**

```text
A few notes on 【Topic】:
1. Point one
2. Point two
3. Point three
What's your take? Reply and let us know.
#【Hashtag】
```

- 字符数：约 120–150（占位符替换后需重新核算）

---

### 3.3 草稿使用约束

1. **禁止使用**"行业第一""全网首发""最佳""唯一"等无法证实的绝对化表述（用户明确要求）。
2. **禁止引用**不存在的用户评价、虚构的客户名称或伪造的数据指标（用户明确要求）。
3. 如草稿中包含数据，必须标注来源，且来源须为可验证的公开材料或经确认的内部数据。
4. 中文与英文为**两个独立版本**，分别发布或按目标受众选择；不建议在单条推文中同时塞入两种语言（280 字符上限下 CJK 双倍计重会导致空间不足）。
5. 占位符替换后，必须用 X 官方编辑器或兼容计数器重新核算加权字符数。

---

## 四、素材清单（Asset List）

| 序号 | 素材类型 | 说明 | 状态 | 备注 |
|---|---|---|---|---|
| 1 | 推文正文（中文） | 草稿 A/B/C 三选一或另行定稿 | 待主题确认 | 需替换占位符并核字数 |
| 2 | 推文正文（英文） | 对应中文版本的自然英文翻译 | 待主题确认 | 非机翻，需母语者或等效审核 |
| 3 | 配图/封面图 | 建议尺寸 1200×675（16:9）或 1:1 | 未制作 | 如需生成，明确使用 Seedream 5.0 Pro；需确认是否需要 |
| 4 | 链接落地页 | 公告/活动/功能说明页面 URL | 待提供 | 计入 23 字符；需确认链接可公开访问 |
| 5 | 话题标签 | 1–2 个相关 #hashtag | 待确认 | 避免使用与品牌无关的热门标签蹭流量 |
| 6 | @提及账号 | 如需提及合作方或同事 | 待确认 | 需提前征得被提及方同意 |
| 7 | 媒体素材（视频/GIF） | 如需附加视频或动图 | 未提供 | X 支持 MP4/MOV；GIF 需符合尺寸限制 |
| 8 | 发布时间 | 计划发布日期与时刻 | 待确认 | 需结合目标受众时区；建议先用 `tweet_read` 分析账号活跃时段 |
| 9 | 目标账号 | 发布所用的 X 账号 handle | 待提供 | Hermes 运行时需已授权该账号 |
| 10 | API 凭证 | `XQUIK_API_KEY` | **未配置** | 须在 Hermes 运行时主机环境变量中设置，不得写入提示词或工单 |

---

## 五、发布前核对项（Pre-publish Checklist）

### A. 环境与权限（依据 SKILL.md）

- [ ] Hermes Agent 运行时已安装并可运行（`hermes` 命令可用）
- [ ] `hermes-tweet` 插件已安装并启用（`hermes plugins enable hermes-tweet`）
- [ ] `XQUIK_API_KEY` 已在 Hermes 运行时主机设置（`echo $XQUIK_API_KEY` 非空）
- [ ] 已重启 Hermes 会话使环境变量生效（SKILL.md 最佳实践要求）
- [ ] 已用 `tweet_explore` 确认发布路由的准确目录路径
- [ ] 本次会话确需发布：`HERMES_TWEET_ENABLE_ACTIONS=true` 已由操作者**有意设置**（SKILL.md Controlled Publishing 第 1 步）

### B. 内容合规

- [ ] 中文稿加权字符数 ≤ 280（CJK 每个计 2）
- [ ] 英文稿字符数 ≤ 280
- [ ] 无"行业第一""全网首发""最佳"等无法证实的绝对化用语
- [ ] 无虚构用户评价、虚构客户名称或伪造数据
- [ ] 所有数据/事实均有可验证来源，来源已标注
- [ ] 链接可公开访问且指向正确落地页
- [ ] 话题标签与内容相关，无蹭无关热搜
- [ ] @提及已征得对方同意
- [ ] 配图/视频已确认版权或为原创
- [ ] 英文版为自然英文，非逐字机翻

### C. 审批流程（依据 SKILL.md「approval-gated」模型）

- [ ] 草稿已提交操作者审核
- [ ] 操作者已明确批准发布（书面/口头确认记录在案）
- [ ] 已展示媒体、回复设置、定时设置等全部 `tweet_action` 输入参数（workflows.md Controlled Publishing 第 3 步）
- [ ] 仅调用已批准的路由，不附带未授权的额外动作
- [ ] 发布后确认推文已成功发出（记录返回的推文 ID/URL）

### D. 发布后

- [ ] 记录发布时间与推文 URL
- [ ] 设定后续监测节奏（如发布后 2h / 24h 用 `tweet_read` 查看互动）
- [ ] 如需回复互动，回复草稿与动作调用分开拟定，再次走审批（workflows.md Support Triage 第 3–4 步）
- [ ] 发布完成后将 `HERMES_TWEET_ENABLE_ACTIONS` 恢复为 `false`

---

## 六、动作计划（Action plan）

以下为**拟执行的账号变更动作**，依据 SKILL.md 均处于「等待明确批准」状态，当前未执行：

1. **发布推文**（待批准）
   - 工具：`tweet_action`
   - 路由：以 `tweet_explore` 查询 `create tweet` 返回的目录路径为准（不得猜测）
   - 输入：定稿后的中英文正文、媒体 ID（如有）、回复设置、定时时间（如需）
   - 前提：`HERMES_TWEET_ENABLE_ACTIONS=true`、`XQUIK_API_KEY` 已配置、操作者已批准
   - 当前状态：**未执行——等待环境就绪、主题确认与操作者批准**

2. **创建关键词监控**（可选，待批准）
   - 工具：`tweet_action`
   - 路由：以 `tweet_explore` 查询 `create monitor` 返回的目录路径为准
   - 用途：监测品牌词/活动词的提及
   - 当前状态：**未执行——等待确认是否需要**

---

## 七、后续检查（Next check）

1. **环境就绪后**：在 Hermes 运行时主机上执行 `tweet_explore`，确认搜索、时间线、发布路由的准确路径。
2. **主题确认后**：用 `tweet_read` 读取目标账号近期时间线与相关关键词搜索结果，分析内容风格与活跃时段，再定稿草稿。
3. **发布后**：建议发布后 2 小时与 24 小时各用 `tweet_read` 检查一次互动数据（回复、转发、点赞），如需回复则另走审批。
4. **监测节奏**：如为活动/发布类内容，建议设置 7 天关键词监控（`tweet_action` → create monitor，需审批）。

---

## 八、无法访问的资源与待确认假设

| 项目 | 状态 | 影响 |
|---|---|---|
| Hermes Agent 运行时 | 本机未安装 | 无法调用 `tweet_explore`/`tweet_read`/`tweet_action` |
| `XQUIK_API_KEY` | 未设置 | 无法读取任何 X/Twitter 实时数据 |
| X/Twitter 实时时间线数据 | 无法访问 | 时间线分析仅提供方法论框架，无真实数据 |
| 发布目标账号 | 未提供 | 无法确定发布身份与受众 |
| 推文主题/产品/活动信息 | 未提供 | 草稿为模板，含占位符，需替换后定稿 |
| 配图需求 | 未确认 | 未生成图片；如需将使用 Seedream 5.0 Pro |
| 发布时间 | 未指定 | 无法安排定时或即时发布 |
| `hermes-tweet` PyPI 包 | 当前环境无法安装 | 不影响规划，但实际执行需在 Hermes 环境内安装 |

---

## 九、实际读取的 Skill 文件

以下为本任务实际读取的 Skill 文件（相对路径，相对于解压目录 `hermes-tweet-skill/`）：

1. `hermes-tweet/SKILL.md`（主文件，155 行，全文读取）
2. `hermes-tweet/references/workflows.md`（工作流模式参考，31 行，全文读取）

此外，为核实端点目录与安装方式，读取了项目公开 README（`https://github.com/Xquik-dev/hermes-tweet` master 分支），该文件不属于 Skill 包内文件，仅作交叉参考。

---

## 十、影响交付结果的 SKILL.md 规则

**规则：「Keep `HERMES_TWEET_ENABLE_ACTIONS` false for read-first sessions. Set it to `true` only for sessions that intentionally need posting」（第 49–51 行）以及「Execute account-changing routes with `tweet_action` only after explicit approval」（第 67 行）。**

**对交付结果的实际影响**：由于该规则要求发布类动作必须经过显式批准且默认关闭动作开关，加上当前环境缺少 Hermes 运行时和 `XQUIK_API_KEY`，本次交付**未执行任何真实发布操作**，也未伪造任何时间线读取结果。所有发布相关内容均以「待批准」「待环境就绪」状态呈现为动作计划，草稿为含占位符的模板而非已发布内容。这直接决定了本交付物的性质为**发布前规划文档**而非已执行的发布记录。

另一条影响交付的规则是 SKILL.md「Inputs」章节（第 55–61 行）要求在选择路由前确认 Objective、Target、Time window、Action scope、API Key 五项输入——由于这些输入均缺失，草稿无法定稿为具体内容，只能以模板形式交付并标注待确认项。
