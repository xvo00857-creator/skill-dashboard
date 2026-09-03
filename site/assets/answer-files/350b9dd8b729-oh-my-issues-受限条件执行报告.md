# oh-my-issues 待办整理 — 受限条件执行报告

> 评测对象：`oh-my-issues`（分类：产品与策略）
> 执行时间：2026-08-12（Asia/Shanghai）
> 执行模式：时间与资源受限；所有不可验证信息标注「待确认」

---

## 一、环境与依赖核查（验证证据）

以下结果均来自实际命令执行，可复核：

| 核查项 | 命令 | 结果 | 结论 |
|---|---|---|---|
| Skill 包内容 | `unzip -l oh-my-issues.zip` | 仅 1 个文件：`oh-my-issues/SKILL.md`（11662 字节） | ZIP 完整，但**不含任何 issue 数据** |
| GitHub CLI | `which gh` / `gh --version` | `command not found` | **未安装** |
| 包管理器 | `which brew` | 无输出（未找到） | 无法用 brew 一键装 gh |
| GitHub 认证 | `env \| grep -iE 'GITHUB\|GH_TOKEN'` | 空 | **无令牌/未登录** |
| 本地仓库 | `git remote -v`（工作目录） | `not a git repository` | **无目标仓库** |
| issue 数据来源 | 全盘扫描解压目录 + 工作目录 | 仅 SKILL.md | **用户未指定仓库，也未提供 issue 导出** |
| GitHub API 连通性 | `curl -s -o /dev/null -w "%{http_code}" https://api.github.com` | `200` | 网络可达，但无认证时公共 API 限速 60 次/小时，且仍需知道目标仓库 |

**阻塞性结论**：SKILL.md 定义的 Mode 1（Cluster pass）需要对一个真实 GitHub 仓库执行 `gh issue list`、`gh issue create`、`gh issue close` 等读写操作。当前环境缺少：① 目标仓库；② `gh` CLI；③ GitHub 认证；④ issue 原始数据。四者缺一，无法执行真实聚类，也无法验证任何聚类结果。

按用户要求「不得编造数据、链接或已完成状态」，本报告**不虚构 issue 列表、不伪造聚类结果**，而是交付：受限条件下的方案调整、可立即执行的框架与模板、待确认清单，以及一旦输入齐备即可运行的命令。

---

## 二、受限条件导致的方案变化

SKILL.md 的理想 Mode 1 是一次性全量聚类：读完全部 issue 正文与评论 → 按根因聚类 → 开 master → 镜像 `plans/0X-*.md` → 关闭全部子 issue → 验证 `open issues == masters`。在「时间/资源有限 + 描述不完整 + 依赖缺失」条件下，做如下调整：

| 维度 | Skill 理想做法 | 受限调整 | 取舍说明 |
|---|---|---|---|
| 阅读范围 | 读每个 issue 正文**及全部评论**（SKILL.md 第 35 行明确警告：不读全会导致表面聚类） | 分两级：先标题+标签+反应数做**范围摸底**（非聚类），再按优先级深读正文与评论 | Skill 把「未读全就聚类」列为 failure mode worth refusing。因此深读不可跳过；调整的是**顺序与批次**，不是用标题代替正文。低优先级 issue 的聚类置信度会下降，须标「待确认」 |
| 聚类规模 | ~100 issue → 4–8 个 master | 先交付 P0 主计划（预计 2–4 个），P1/P2 分批 | 用最小可交付聚类先止住重复 issue 增长；P0 覆盖占比目标 ≥50%（待确认，取决于真实数据分布） |
| 描述不完整 issue | 评论里常有复现步骤和诊断输出（SKILL.md 第 35 行） | 评论仍无法补全的，进「needs-info」列表，**不强行塞进聚类** | 强行聚错类比留空更糟；Skill 要求按根因聚类，信息不足时根因无法判定 |
| 互相依赖 | Skill 以「一个架构修复退役一族症状」为模型，未显式处理 cluster 间依赖 | 在 master 文档的 `Out of scope` 与新增的 `Dependencies` 段记录跨计划依赖与先后顺序 | 这是对 Skill 模板的小幅扩展，不改变其核心模型 |
| 写操作 | 开 master、关子 issue、发 PR | 无认证/无仓库时，先产出本地 `plans/0X-*.md` + 路由表（CSV/Markdown）；有认证后由人或脚本执行 `gh` 命令 | 子 issue 必须在 master 开启**之后**才能关闭（SKILL.md 第 224 行）；本地阶段先生成 master 内容，保证顺序不被破坏 |
| 验收 | `gh issue list --state open` 只剩 master | 本地阶段验收：路由表内部一致性 + 每个 issue 恰好出现一次 + P0 master 四要素齐全 | 无法用 `gh` 验证线上状态时，用可离线检查的结构一致性替代，并标注「线上状态待确认」 |

---

## 三、优先级、取舍与验收标准

### 3.1 优先级定义

- **P0 — 立即聚类**：重复报告多（≥3 条指向同一根因）、根因可从正文+评论明确判定、修复边界可容纳在单个 PR 内。
- **P1 — 次轮聚类**：有共享根因迹象但证据不足，或修复跨多个模块需拆分。深读后仍不确定的标「待确认」。
- **P2 — 不聚类 / 暂缓**：真正独立的 feature request（Skill 第 225 行：非症状 issue 不应用重定向评论关闭）、描述严重缺失且评论无补充、需要产品决策而非架构修复。

### 3.2 取舍原则

1. **宁可少聚，不可错聚**：错聚类会把独立修复混进一个 PR，违反 Skill「一个 cluster 一个架构修复」原则。
2. **先止血，后求全**：P0 先交付以阻止重复 issue 继续累积；P1/P2 不阻塞 P0。
3. **信息不足不猜根因**：所有「待确认」项显式列出，不静默丢弃。
4. **master 必须暗示修复**（SKILL.md 第 71 行）：写不出一行架构范围的 cluster 就是错的，降级为 P1/P2。

### 3.3 验收标准

**本地阶段（当前可交付）：**
- [ ] 每个 issue 编号恰好出现在以下三处之一：某 P0 master 的 Children 列表、needs-info 列表、独立/feature 列表（无遗漏、无重复）
- [ ] 每个 P0 master 具备四要素：架构缺陷描述、Children 列表、修复顺序、测试矩阵草图
- [ ] P0 master 标题格式为 `[plan-XX] <架构缺陷> — <一行范围>`，且标题暗示修复而非主题
- [ ] 所有跨计划依赖在 `Dependencies`/`Out of scope` 中记录
- [ ] 所有未读全正文/评论而暂判的项标注「待确认」

**线上阶段（需补齐仓库+认证后）：**
- [ ] `gh issue list --state open` 仅返回 plan-master，无其他 open issue
- [ ] 每个子 issue 有关闭重定向评论，关闭原因为 `not planned`
- [ ] 每个 master 有对应 `plans/0X-*.md` 且互相引用一致
- [ ] 无「graveyard master」（5+ 轮 Round 评论无 PR）、无「over-broad master」（修复塞不进一个 PR）

---

## 四、可立即执行的聚类框架（待真实数据填入）

> 以下命令与模板均来自 SKILL.md，仅在顺序与分批上按受限条件调整。`OWNER/REPO`、issue 编号等均为占位，**待确认**。

### 4.1 前置：解析仓库与总数（需先装 gh 并登录）

```bash
# 安装 gh（macOS，无 brew 时可下载官方二进制；待确认是否允许安装）
# 官方地址：https://github.com/cli/cli/releases —— 具体版本待确认

# 登录（需交互式浏览器认证，待确认账号权限）
gh auth login

# 解析仓库（须在目标仓库本地目录内执行，或用 gh repo view OWNER/REPO）
repo_json=$(gh repo view --json owner,name)
owner=$(jq -r '.owner.login // .owner.name' <<<"$repo_json")
repo=$(jq -r '.name' <<<"$repo_json")

# 用 search API 获取纯 issue 数（gh issue list 的 --limit 会静默截断；REST API 把 PR 也算 issue）
total=$(gh api "search/issues?q=repo:$owner/$repo+is:issue+is:open" --jq '.total_count')
echo "Open issues: $total"
```

### 4.2 范围摸底（不替代全文阅读，仅用于排优先级）

```bash
# 标题+标签+作者+日期，用于识别重复簇和排序
gh issue list --state open --limit "$total" \
  --json number,title,labels,author,createdAt \
  --jq '.[] | "\(.number)\t\(.title)\t\([.labels[].name]|join(","))"'
```

### 4.3 分批全文深读（按 P0 候选优先）

```bash
# 正文
gh issue list --state open --limit "$total" \
  --json number,title,body,labels,author,createdAt > issues-bodies.json

# 每个 issue 的完整评论串（gh issue list --json comments 只返回数量占位，不含正文）
for n in $(jq -r '.[].number' issues-bodies.json); do
  echo "=== Issue #$n ==="
  gh issue view "$n" --json comments \
    --jq '.comments[] | "\(.author.login) (\(.createdAt)): \(.body)"'
  echo
done > issues-comments.txt
```

### 4.4 聚类判定问题（对每组候选 issue 自问）

> 「一个架构变更能否退役所有这些 issue？」——是则同簇；仅共享关键词（如「Windows」「auth」）是表面，不是根因。

### 4.5 产出物（本地阶段，无需认证即可生成）

1. **路由表** `issue-routing.csv`：列 `issue,title,cluster,confidence,status,notes`，每个 issue 一行。
2. **计划文档** `plans/0X-<slug>.md`：每个 P0 master 一份，模板见 4.6。
3. **needs-info 列表**：描述不完整且评论无法补全的 issue。
4. **独立/feature 列表**：不适用重定向关闭的 issue（SKILL.md 第 225 行）。

### 4.6 Plan master 文档模板（取自 SKILL.md，新增 Dependencies 段）

```markdown
# [plan-XX] <架构缺陷> — <一行范围>

## Defect
<一段：结构上哪里坏了，为什么会产生观察到的这一族症状。>

## Children
- #N — <症状一句话>
- #N — <症状一句话>

## Fix sequence
1. <第一个架构变更——有边界、可评审>
2. <第二个>

## Dependencies
<与其他 plan-master 的先后/依赖关系；无则写「无」。>

## Test matrix
| 轴 A | 轴 B | 期望行为 |
|---|---|---|
| ... | ... | ... |

矩阵须进 CI；未来回归必须在用户报 issue 前先让 CI 红。

## Out of scope
<本计划刻意不覆盖的内容，指向其他 plan-master。>
```

### 4.7 线上执行（认证齐备后，严格按顺序）

```bash
# 1) 先开 master（子 issue 必须有重定向目标后才能关）
gh issue create \
  --title "[plan-XX] <架构缺陷> — <一行范围>" \
  --body-file plans/0X-<slug>.md \
  --label plan,plan-XX

# 2) 对每个子 issue 发标准化重定向评论，再以 not planned 关闭
gh issue comment <CHILD> --body "Consolidating into #<MASTER> (plan-XX). The root cause and fix sequencing are tracked there alongside the rest of the cluster — please follow that issue for progress."
gh issue close <CHILD> --reason "not planned"

# 3) 验证终态：open 列表应只剩 master
gh issue list --state open --json number,title \
  | jq -r '.[] | "\(.number)\t\(.title)"'
```

### 4.8 标准化重定向评论（逐字使用，SKILL.md 第 86–88 行）

```text
Consolidating into #<MASTER> (plan-XX). The root cause and fix sequencing are tracked there alongside the rest of the cluster — please follow that issue for progress.
```

---

## 五、待确认清单

| 编号 | 待确认项 | 为何无法验证 | 需要谁/什么补齐 |
|---|---|---|---|
| C1 | 目标仓库（owner/repo） | 用户未指定，本地无 git 远程 | 用户提供仓库 URL 或在本地 clone 目标仓库 |
| C2 | `gh` CLI 是否允许安装 | 环境无 gh、无 brew；安装需写系统目录 | 用户确认安装方式与权限 |
| C3 | GitHub 认证凭据与账号权限 | 无 GITHUB_TOKEN/GH_TOKEN，未登录 | 用户完成 `gh auth login` 或提供 token |
| C4 | 全部 open issue 正文与评论 | 无仓库无法拉取；且 SKILL.md 要求读全，不能用标题代替 | C1–C3 齐备后执行 4.2–4.3 |
| C5 | issue 总数与重复/依赖/不完整的实际分布 | 无数据 | 同上 |
| C6 | 聚类数量与每个 cluster 的 children 归属 | 无数据，禁止编造 | 全文深读后判定 |
| C7 | 仓库是否已有 `plans/` 目录与纪律 | Skill 第 27 行：若无且用户不愿引入，应先提议不强加 | 检查仓库或与维护者确认 |
| C8 | 标签 `plan`、`plan-XX` 是否存在 | 无仓库无法查 | 开 master 前确认或创建 |
| C9 | P0 覆盖率 ≥50% 的目标是否合理 | 取决于真实分布 | 摸底后校准 |
| C10 | 是否存在跨 cluster 依赖及顺序 | 无数据 | 聚类后在 Dependencies 段记录 |

---

## 六、实际读取的 Skill 文件与规则影响

### 6.1 实际读取的文件

| 相对路径（相对于 ZIP 根） | 读取方式 | 说明 |
|---|---|---|
| `oh-my-issues/SKILL.md` | 解压后 `Read` 全文（226 行，11662 字节） | ZIP 内唯一文件，已完整读取 |

ZIP 中不存在其他 Skill 文件、脚本、模板或数据文件（已用 `unzip -l` 与 `find` 双重确认）。

### 6.2 实际影响执行的 SKILL.md 规则

1. **「读全部正文+评论，禁止只读标题就聚类」**（第 35 行；第 223 行 failure mode）→ 直接决定受限方案：摸底只用于排序，不用于聚类；信息不足的 issue 进 needs-info 而非硬聚。
2. **「按根因而非表面聚类」**（第 36 行；命名表第 73–80 行）→ 聚类判定问题与 master 命名规范据此制定。
3. **「master 标题必须暗示修复」**（第 71 行）→ 纳入验收标准与模板。
4. **「先开 master 再关子 issue」**（第 224 行）→ 线上执行步骤严格排序；本地阶段先生成 master 内容。
5. **「非症状 issue（如独立 feature request）不套用重定向关闭」**（第 225 行）→ P2 分类与「独立/feature 列表」据此设立。
6. **「关闭子 issue 用 `not planned` 而非 `completed`」**（第 90 行）→ 写入执行命令模板。
7. **「`gh issue list --json comments` 不含评论正文，须逐个 `gh issue view`」**（第 103 行）→ 4.3 节命令据此编写。
8. **「先查总数，`--limit` 不得静默截断；用 search API 取纯 issue 数」**（第 104–111 行）→ 4.1 节命令据此编写。
9. **「终态 open issues == masters」**（第 8、41、215 行）→ 线上验收标准据此制定。
10. **「~100 issue → 4–8 master；>10 是按表面聚类，<3 过宽」**（第 43 行）→ P0 分批与规模校准依据。
11. **「无 `plans/` 纪律时先提议不强加」**（第 27 行）→ 列入待确认 C7。
12. **健康检查（graveyard/over-broad/surface-clustered/drift）**（第 204–211 行）→ 纳入线上阶段验收。
13. **标准化重定向评论逐字使用**（第 86–88 行）→ 4.8 节原样提供。
14. **plan master 正文模板四要素**（第 172–202 行）→ 4.6 节模板基础上仅新增 Dependencies 段以处理互相依赖。

---

## 七、已完成范围与未完成范围

### 已完成
- 下载并解压 ZIP，确认完整性（1 个文件，11662 字节）。
- 完整阅读 `oh-my-issues/SKILL.md`（226 行）。
- 核查执行环境：gh、brew、令牌、git 仓库、issue 数据、网络连通性。
- 识别全部阻塞性缺失项并给出补齐路径。
- 按「时间/资源受限 + 描述不完整 + 互相依赖」调整方案，明确优先级、取舍、验收标准。
- 产出可立即执行的命令框架、模板、路由表结构与待确认清单。

### 未完成（因输入/依赖缺失，无法诚实完成）
- **未对任何真实 issue 执行聚类**：无仓库、无数据，任何聚类编号与归属都将是编造，已拒绝这样做。
- **未开启/关闭任何 GitHub issue、未创建 PR**：无 gh、无认证、无目标仓库。
- **未生成具体的 `plans/0X-*.md` 实例**：缺少真实 children 与根因，仅提供模板。
- **未验证线上终态**：无仓库可执行 `gh issue list` 验证。

### 恢复执行所需最小输入
1. 目标仓库：`owner/repo`（或本地已 clone 且配置远程的仓库路径）；
2. 安装并认证 `gh`（`gh auth login`，账号对目标仓库有读写 issue 权限）；
3. 确认允许引入 `plans/` 目录纪律（C7）。

以上三项齐备后，按第四节 4.1→4.3 拉取数据，即可在同一框架内完成真实聚类并回填本报告的待确认项。
