# worker-delegation 执行方案：3 小时/周、无管理头衔、不造成绩

> 适用 Skill：`hive.worker-delegation`（随附 `worker-delegation/SKILL.md`）
> 文档定位：个人执行方案，不是 Skill 未覆盖领域的延伸建议
> 生成日期：2026-08-12

---

## 0. 能力边界声明（先于一切）

`worker-delegation` 解决的是一个**技术编排问题**：在 COLONY 模式下，如何把有 N 个独立单元的工作，通过 `tracker_sql` 建表、`write_skill` 写 worker 协议、`run_playbook` 跑确定性 Python 收敛脚本，扇出给并行 AI worker 完成，并支持重试/断点续跑。

它**不涉及**以下内容，本方案也不据此给建议：

- 不涉及管理真人下属、绩效考核、晋升答辩、组织政治——它"委派"的对象是 AI worker，不是人；
- 不涉及职业规划方法论、能力模型、向上管理套路；
- 不提供任何业务数据、项目结果或外部事实。

因此"无正式管理头衔"在本 Skill 语境下**不构成障碍**：你不需要头衔就能把工作扇出给 AI worker。可讲的职业故事是"个人贡献者用并行化工作流放大产出与质量"，而不是"我管了 N 个人"。这一边界直接决定了下文证据与话术的写法。

---

## 1. 聚焦方案

### 1.1 先判断：这件事该不该扇出？

Skill 明确：**N=1 或 N=2 且单元廉价时不要扇出**（spawn 有开销：全新 AgentLoop、独立对话、无共享上下文）；**探索性工作（"搞清楚 X"）也不要扇出**，worker 不擅长开放范围。正确顺序是"先分解，再把有界部分扇出"。

选题必须同时满足：

1. 有 **N≥3 个互相独立（disjoint）**的工作单元，且每个单元需要实质工具时间（浏览器、API、读文件、LLM 调用）；
2. 任意两个 worker 不需要同时写同一行；
3. 共享逻辑写进 skill 后，单行任务能用 <100 字描述；
4. 工作是**有界的填空/核查/补全**，不是开放探索。

不满足就自己做，不要为了"显得会委派"而硬拆。

### 1.2 选题标准（用你手头真实工作套）

从你当前真实在推进的事项里，挑一个符合下列特征的：

- 天然成行：竞品/功能条目、文档/页面清单、用户反馈条目、配置项、数据源、账号/片段等；
- 每行要填的字段结构化、可验证（金额、枚举、链接、计数、是/否）；
- 有明确"完成"判定（某字段非空、某状态置位）；
- 即使个别行拿不到数据也能收尾（写 `N/A` + 原因，不造假）。

**示例性范围（以下仅为示例形态，不是你的真实数据，必须替换）**：
"对 N 个已存在的条目，补全 3–5 个结构化字段（官网链接、某枚举分类、公开可查的计数、2–3 句备注），并在无法核实两次后写 `N/A`+原因。"
这与 Skill 自带的 worked example 同构，风险最低，适合第一次跑通模式。

> ⚠️ 待确认：你实际要做的是哪一类、N 大概多少、是否涉及登录态/浏览器 profile/API 配额。Skill 要求：对浏览器会话、API cursor、登录态等共享资源能否被 worker 使用**不确定就问，不要凭架构猜测拒绝或放行**。

### 1.3 三件产物的设计（本方案的核心）

Skill 的心智模型：**tracker 是状态，playbook 是控制器，skill 是可复用协议**。

**(A) Tracker 表（持久工作清单，状态列即进度）**

必须包含**完成谓词列**（状态枚举或 `*_at` 时间戳，完成前为 NULL）——playbook 的"还剩什么"查询依赖它；没有它就无法续跑。

```sql
CREATE TABLE work_units (
  slug        TEXT PRIMARY KEY,   -- 自然键，幂等 upsert 用
  name        TEXT,
  ref_url     TEXT,               -- 该行对应的源链接/定位
  field_a     TEXT,               -- 结构化字段示例
  field_b     TEXT,               -- 枚举值示例
  verified_count INTEGER,         -- 数值字段，查不到写 -1
  notes       TEXT,               -- 2-3 句备注 / N/A 原因
  status      TEXT DEFAULT 'new', -- new|done|needs_review|no_data
  done_at     TEXT                -- 完成谓词：NULL 即未完成
);
-- 先用真实 slug 插入 N 行（只插你真实拥有的条目，不编造）
```

```python
tracker_register_writable(
  table='work_units',
  write_columns=['ref_url','field_a','field_b','verified_count','notes','status','done_at'],
  key_columns=['slug'])
```

**(B) Worker skill（可复用操作规程，风险最高的部分）**

`write_skill(skill_name='unit-enrichment', skill_body=...)`，内容包含：schema、工具顺序、输出格式、质量标准。要点：

- 每个字段的取值规范（枚举、格式、查不到写 `N/A`/`-1`）；
- **最后一步才写 `done_at`**——它是完成标记；
- 同一字段核实两次仍无法确认 → 写 `N/A` 并在 notes 注明一行原因，**不要编造**（Skill 原文要求）；
- 若有外部副作用（发消息、写外部系统），动作本身必须幂等：先检测"今天是否已对该对象做过"，再决定是否执行，防止崩溃续跑导致重复操作；
- worker 不确定时在该行写 `needs_review` 并继续，不中途升级——跑完后由你统一裁决。

**(C) Playbook（确定性编排，廉价部分）**

一个 Python 脚本（`meta` + `async def run(args)`），调用 `converge`。严格遵守 Skill 的 API 契约：

- `tracker_query` / `tracker_count` 是**同步**的（不要 `await`）；`tracker_query` 返回**行字典列表**，`SELECT COUNT(*)` 返回单行 `[{'cnt': N}]` 只用于计数；
- `converge(...)` 和 `worker(...)` 是 **async**；并行只通过 `converge` 发生——`pending` 交行、`dispatch` 构造 worker 协程，**不要**裸 `for row: await worker(...)`（那是串行，`concurrency` 失效）；
- `pending` 必须 SELECT **未完成的行**，不是 COUNT。

```python
meta = {"name": "unit-enrichment-batch",
        "description": "Converge work_units: every row done",
        "concurrency": 3}          # 并发数由你决定，首次从小值开始

RECEIPT = {"type": "object",
           "required": ["slug", "status"],
           "properties": {"slug": {"type": "string"},
                          "status": {"enum": ["done", "no-data", "needs_review"]}}}

async def run(args):
    await converge(
        pending=lambda: tracker_query(
            "SELECT slug, name, ref_url FROM work_units WHERE done_at IS NULL"),
        dispatch=lambda row, i: worker(
            task=f"Enrich {row['slug']} ({row['name']}) with the unit-enrichment "
                 f"skill; source: {row['ref_url']}; upsert your row, write done_at LAST.",
            skill="unit-enrichment",
            timeout=400,
            schema=RECEIPT),
        max_rounds=3,              # 最多从 tracker 重新推导缺口 3 轮
        # circuit_breaker 可按需加：一轮失败过多就中止
    )
    gap = tracker_count("SELECT slug FROM work_units WHERE done_at IS NULL")
    log(f"converged; {gap} unresolved -> dead-letter")
    return {"unresolved": gap, "deadletter": deadletter.list()}
```

**路由/限速（仅当需要时）**：若 worker 共用同一个外部账号，必须用 `lane(...)` 限速并通过轮换 `profile` 分散账号（`profile` 就是账号绑定，没有单独的 `account` 参数）；若是登录态 Chrome profile，先用 queen 工具 `list_browser_profiles` 发现真实 label（不要编造 `Default`/`Profile 1`），再把 label 写进每个 worker 的任务串，worker 用 `--browser-profile <label>` 并校验回显。单 profile 时全部路由到它即可。

**GTM/CRM 书挡（仅当单元是人/线索/账号时才需要）**：若你做的是外联类工作，循环前后要由 queen（不是 worker）做 CLAIM（`hive-crm import` 去重 + `claim` 原子锁定，只种你抢到的人）和 PROMOTE（完成后 `import` 更新 + `release` 移交）。若你的单元是文档/条目/数据，**本节不适用**，不要硬加。

### 1.4 3 小时/周的时间盒策略

- playbook 是**异步**的：`run_playbook` 立即返回，完成时通知你。你的 3 小时不花在盯运行上，而花在**裁决、修补、决策**上；
- 每周固定两段：≤2 小时执行/审查，≥1 小时留缓冲（试点周和修补周可能吃满）；
- 一次只推进一个 playbook；不同时跑多个范围；
- N 很小（3–5）时可能几周就收敛，**不要用编造的工作填满 12 周**——提前进入总结周即可；
- 没有完成谓词列就没有续跑，也就没有"每周只花 3 小时、下周接着跑"——这是时间盒能成立的技术前提。

---

## 2. 可收集证据（全部真实、可验证、零编造）

下列每一项都是 Skill 运行过程中**自然产生的产物**，不是事后润色的成绩。任何一项拿不出来，就不写进总结。

| # | 证据 | 来源/形态 | 证明什么 |
|---|------|-----------|----------|
| 1 | Tracker 建表语句与行级状态 | `CREATE TABLE` DDL + 各行 `status`/`done_at` | 工作被建模成可追踪清单；状态列即进度 |
| 2 | Worker skill 全文 | `write_skill` 的 `skill_body` | 你把可复用逻辑沉淀成了协议，而非每行重复提示 |
| 3 | Playbook 脚本 | `playbooks/unit-enrichment-batch.play.py` | 你写了确定性编排（并发/重试/收敛/归约） |
| 4 | **试点记录**（最有说服力） | 选了哪行、每步工具结果、发现的 bug、对 skill 的就地补丁 | 你先自己跑通一行再放行 N 个 worker——质量控制 |
| 5 | 运行回执 | `run_playbook` 返回与 `[PLAYBOOK_COMPLETE]` 通知 | 编排真实执行过 |
| 6 | 收敛日志 | dispatch 数、`max_rounds` 重试轮次、失败率 | 你用收敛/重试而非人工盯每份报告 |
| 7 | 死信清单 | `deadletter.list()` 与 `needs_review` 行 | 你能识别并处理异常，而不是掩盖 |
| 8 | Worker 回执 | 每行的 receipt JSON（slug/status） | 逐行产出、可核对 |
| 9 | **续跑证据** | 第二次用 `run_playbook({playbook_name})` 时 done 行被跳过的日志 | 重跑即续跑，pending 查询即缺口 |
| 10 | 幂等证据 | 副作用步骤"已完成？"检测的实现/日志 | 崩溃续跑不会重复操作外部系统 |
| 11 | 时间记录 | 每周实际投入（≤3h） | 在硬约束下交付 |
| 12 | Reduce 总结 | 真实计数、死信数、N/A 数及原因 | 用数字收尾，不夸大 |

**不收集/不写入的东西**：没有发生的项目成果、没有核实过的数字、没有运行过的"结果截图"、别人的贡献。Skill 第 171 行"查不到写 `N/A`+原因，不要编造"既是字段规则，也是整个证据观。

---

## 3. 沟通脚本

以下脚本只用于**就这项真实工作做沟通**，不包装成人员管理业绩。对象默认为你的直属上级（徐峰），可按实际调整。

### 脚本 1｜提案（争取空间，第 1 周末）

> "我手上有一批【N 个某类条目】要补全/核查，单个做要反复切工具。我想试一种并行做法：先建一张状态表，写好一套统一操作规范，自己先完整跑通一条验证规则没问题，再让多个并行 worker 按同一规范跑剩下的，脚本自动重试和续跑。我每周投入控制在 3 小时以内，主要花在规则验证和异常裁决上。这件事不需要我带谁，产出是这批条目本身加上一套可复用的流程。可以按这个方向试一轮吗？"

要点：说清机制、说清时间盒、明确"不带人"、要的是许可不是资源。

### 脚本 2｜试点受阻（第 3 周，如实调整）

> "试点那一条我自己跑下来发现【具体问题，如：某字段实际在另一个页面/选择器不稳定/分页方式不同】。我已经把操作规范就地改了，现在这一条能干净跑通。这正是先试一条的目的——如果一开始就并行跑 N 条，会是 N 倍同样的失败。接下来我会按修订后的规范跑剩余部分。"

要点：把"发现问题"表述为试点设计的预期收益，不掩饰、不甩锅。

### 脚本 3｜中期进度（用 tracker 数字，第 6–8 周）

> "进度按状态表算：总共 N 条，已完成 X 条，重试后仍拿不到数据 Y 条（都标注了原因），需要人工判断 Z 条。我没有逐份看 worker 的产出，而是靠收敛脚本和死信清单定位问题——目前规则改过 2 次，重跑会自动跳过已完成的。下周我会集中处理 Z 条需要判断的。"

要点：用行状态说话；说明你怎么控质量（收敛+死信，不是人海检查）。

### 脚本 4｜死信/异常坦诚沟通（任意周）

> "有 K 条重试 3 轮后仍未完成，我把它们列进了死信清单。原因是【真实原因】。我不打算让 worker 反复试，准备这样处理：【补数据源/人工判定/标记 N/A】。这意味着最终会有 K 条没有完整字段，但每条都有原因记录，不会出现假数据。"

要点：宁可承认缺口，也不允许假完成；这比"100% 完成"更可信。

### 脚本 5｜期末发展对话（第 12 周）

> "这 12 周我用每周 3 小时，把一批 N 条的工作用'状态表 + 统一规范 + 自动收敛脚本'跑完了：X 条完成、Y 条 N/A 带原因、Z 条人工裁决。过程里我先自己试跑一条、修了规则再放量，脚本支持重试和断点续跑。我没有带下属，但这套方法可以直接给团队复用——任何'有 N 个独立条目要补全/核查'的事都能套。这是状态表、脚本和收敛记录，你可以核对。"

要点：定位为"个人贡献者的方法论与杠杆"，不是管理业绩；主动给出可核对产物。

---

## 4. 十二周行动计划（每周 ≤3 小时）

> 总预算 36 小时。若 N 较小提前收敛，不要编造工作填时间，直接进入第 11–12 周。

| 周 | 主题 | 具体动作（≤3h） | 关卡/产出 |
|----|------|------------------|-----------|
| 1 | 选题与分解 | 从真实工作中选定一个有 N≥3 独立单元的有界事项；写出单行 <100 字描述；确认是否涉及登录态/浏览器 profile/API 配额，不确定就问 | 选题成立？不成立则换题或自己做 |
| 2 | 建模与写规范 | 写 `CREATE TABLE`（含 `done_at` 完成谓词）；`tracker_register_writable`；起草 worker skill（字段规范、工具顺序、幂等、`N/A` 规则、最后写 `done_at`）；插入真实 N 行 | tracker 与 skill 草稿 |
| 3 | **试点（queen 自己跑一行）** | 选最有代表性的一行，用自己的工具按 skill 端到端跑；每步看结果；遇问题就地改 skill；直到该行干净完成 | **强制关卡**：跑不通就重新设计，不放行任何 worker |
| 4 | 编写 playbook | 写 `meta`（concurrency 首次取 2–3）、`pending`（选未完成行，非 COUNT）、`dispatch`、`max_rounds=3`、reduce；自检：`tracker_query` 不 await、并行只走 `converge`、不裸 await 循环 | playbook 脚本；dry-run 契约检查 |
| 5 | 首批运行 | `run_playbook({playbook: ...})`；等 `[PLAYBOOK_COMPLETE]`；只看收敛结果与死信，不逐份审报告 | 首批完成回执 |
| 6 | 复盘与修补 | 查 dead-letter 与 `needs_review`；修 skill 或补数据；用 `run_playbook({playbook_name})` 续跑（done 行自动跳过） | 补丁记录 + 续跑证据 |
| 7 | 继续收敛 | 第二批/继续；若有外部副作用，验证幂等（"已做过？"检测） | 幂等证据 |
| 8 | 收敛到缺口 | 跑到 gap=0 或全部进入死信；记录重试轮次 | 收敛日志 |
| 9 | 验证可续跑性 | 主动重跑 `playbook_name`，确认 done 行被跳过、pending 查询即缺口；整理 retry/dead-letter 证据（约 2h，1h 缓冲） | 续跑演示证据 |
| 10 | 死信裁决 | 对死信行 stop→decide→edit→rerun；补 `N/A` 并注明原因，不造假 | 死信清零或全部带原因关闭 |
| 11 | 归约与复盘 | 出 reduce 总结（真实计数）；写一页复盘；整理第 2 节的证据包 | 证据包 |
| 12 | 发展沟通与沉淀 | 用脚本 5 与上级做发展对话；把 tracker/skill/playbook 沉淀为团队可复用模板 | 可复用模板 + 对话记录 |

---

## 5. 无法访问的资源与待确认假设（不假装已完成）

1. **COLONY 运行环境不在本会话中**：`run_playbook`、`tracker_sql`、`write_skill`、`converge`、`worker`、`hive-crm`、`hive-browser`、`list_browser_profiles` 等是 Skill 描述的 colony 工具，本 MainAgent 环境里没有这些工具。因此上文的 SQL/Python 是**待在 colony 会话中执行的设计稿**，我没有、也不会声称已经运行过它们或产生任何结果。
2. **真实选题未知**：第 1.2 节的范围是示例形态，不是你的真实工作；N、字段、数据源都需要你用真实事项替换。
3. **共享资源待确认**：是否需要登录态 Chrome profile、有几个 profile/账号、API 限速是多少——这些决定 `lane`/`profile` 路由设计，需在第 1 周确认。
4. **是否涉及 GTM/CRM 待确认**：只有当单元是人/线索时才加 CLAIM/PROMOTE 书挡；若是文档/条目类工作则不适用。
5. **时间线可压缩**：若 N 很小，5–10 周可能提前收敛；第 11–12 周的总结与沟通仍保留，但中间不补虚构工作。
6. **本方案不构成人员管理或晋升建议**：相关话题超出 `worker-delegation` 的能力边界，如需应另寻对应资源。

---

## 6. 实际读取的 Skill 文件

- `worker-delegation/SKILL.md`（ZIP 内唯一文件，已完整读取，共 212 行）

### 实际影响本交付的 SKILL.md 规则（至少一条，以下多条均已落地）

- **"先试点再扇出，queen 自己跑第一条"（第 41–59 行）**：直接把第 3 周设为强制关卡——跑不通不放行 worker，并把"试点记录+skill 补丁"列为最有说服力的证据（证据 #4）。
- **"N<3 或探索性工作不要扇出"（第 35–37 行）**：决定了第 1 周的选题门槛，明确不满足就自己做，不为了凑方案硬拆。
- **"tracker 必须有完成谓词列，否则无法续跑"（第 63、70 行）**：决定了表结构里的 `done_at` 列，也是"每周 3 小时、下周续跑"能成立的前提。
- **"查不到写 `N/A`+原因，不要编造"（第 170–171 行）**：决定了整个证据观——死信和 N/A 如实记录，不写假完成、不造项目成绩。
- **API 契约（第 92–97 行）**：决定了 playbook 模板里 `tracker_query` 不 await、`pending` 选行不选 COUNT、并行只通过 `converge` 等具体写法。
