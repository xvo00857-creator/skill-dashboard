# timeline-report Skill 落地方案

> 基于 Skill 文件 `timeline-report/SKILL.md` 的真实能力边界制定，未编造任何数据或运行结果。

---

## 一、当前环境检查结果（实测）

| 检查项 | 结果 |
|---|---|
| Worker 端口解析 | `37701`（fallback 值，因 `~/.claude-mem/settings.json` 不存在） |
| `~/.claude-mem/` 目录 | **不存在** |
| claude-mem worker 进程 | **未运行**（localhost:37701 无响应） |
| SQLite 数据库 `~/.claude-mem/claude-mem.db` | **不存在** |
| 当前目录是否 git 仓库 | 否 |
| 当前目录是否代码项目 | 否（仅含本次解压的 Skill 文件） |
| node 可用性 | v20.19.2（可用） |
| sqlite3 可用性 | 3.51.0（可用） |

**结论：** 按照 SKILL.md「Prerequisites」要求，claude-mem worker 必须运行且项目须有观察记录，当前两项均不满足，**无法立即生成真实的项目发展历程报告**。下文给出从零到可用的最小流程。

---

## 二、Skill 能力边界（以 SKILL.md 为准）

**Skill 能做的：**
- 从本地 claude-mem worker（`http://localhost:${WORKER_PORT}`）拉取指定项目的完整时间线
- 查询本地 SQLite 数据库 `~/.claude-mem/claude-mem.db` 获取 token 经济指标
- 生成 3000–6000 字的叙述性报告「Journey Into [项目名]」，含 10 个固定章节
- 将报告保存为 `./journey-into-<项目名>.md`

**Skill 不做的（题目假设但文件未授权）：**
- **不提供旧资料导入/迁移功能**——SKILL.md 全文无任何导入 API 或批量录入入口；claude-mem 的观察记录由 worker 在开发过程中自动产生，不能把结构混乱的旧文档直接灌进去
- **不做敏感信息脱敏**——Skill 本身只访问 localhost 和本地数据库，天然不上传外部，但它不包含脱敏/过滤模块
- **不管理日常维护任务**——Skill 是一次性报告生成器，不是持续运维工具
- **不支持非 claude-mem 数据源**——无法解析通用 Markdown、Word、Confluence 等旧资料

---

## 三、最小流程（首次生成报告）

严格对应 SKILL.md 的 Step 1–6：

1. **确认 worker 运行**
   ```bash
   WORKER_PORT="${CLAUDE_MEM_WORKER_PORT:-$(node -e "const fs=require('fs'),p=require('path'),os=require('os');const uid=(typeof process.getuid==='function'?process.getuid():77;const fallback=String(37700+(uid%100));try{const s=JSON.parse(fs.readFileSync(p.join(os.homedir(),'.claude-mem','settings.json'),'utf-8'));process.stdout.write(String(s.CLAUDE_MEM_WORKER_PORT||fallback));}catch{process.stdout.write(fallback);}" 2>/dev/null)}"
   curl -s --max-time 3 "http://localhost:${WORKER_PORT}/api/search?query=*&limit=1"
   ```
   无响应则需先启动 claude-mem worker（启动方式取决于你的安装方式，SKILL.md 未指定具体命令）。

2. **确定项目名**——在项目根目录执行，若为 git worktree 则取父仓库名（SKILL.md Step 1 有检测脚本）。

3. **拉取完整时间线**
   ```bash
   curl -s "http://localhost:${WORKER_PORT}/api/context/inject?project=<项目名>&full=true"
   ```

4. **估算 token**——约 1 token / 4 字符；超过 100K token 须经用户确认（SKILL.md Step 3 强制要求）。

5. **生成报告**——将完整时间线交分析子任务，按 10 个章节撰写，同时查 SQLite 取 token 经济指标。

6. **保存**——输出到 `./journey-into-<项目名>.md`。

---

## 四、旧资料迁移步骤（受限说明）

> ⚠️ **SKILL.md 未提供任何批量导入能力。** 以下步骤是在 Skill 能力边界内、让旧资料价值不丢失的务实做法，不是把旧资料写入 claude-mem 数据库。

**第 1 步：安装并启动 claude-mem worker**
- 按你团队的 claude-mem 安装文档部署（SKILL.md 未包含安装步骤，无法代为指定）。
- 确认 `~/.claude-mem/claude-mem.db` 生成、worker 端口可访问。

**第 2 步：旧资料人工提炼为「里程碑清单」（一次性，建议 ≤60 分钟）**
- 不逐字搬运混乱旧资料，只提炼关键节点：日期、事件、决策、文件、原因。
- 存为项目根目录的 `MILESTONES.md`，作为人工补充上下文。
- 此文件**不进入** claude-mem 数据库，但可在首次生成报告时作为补充背景一并提供给分析环节。

**第 3 步：从现在起让 claude-mem 自动记录**
- 在日常开发中保持 worker 运行，新观察自动入库。
- 旧资料无法回填为历史观察（SKILL.md 无此 API），报告的「Project Genesis」等章节对 claude-mem 上线前的时期只能依赖 `MILESTONES.md` 人工补充，并在报告中明确标注来源为人工整理而非自动记录。

**第 4 步：积累 ≥2 周后首次生成完整报告**
- 数据量不足时报告章节会空洞，建议至少积累 1–2 周真实观察后再跑首次完整报告。

---

## 五、日常维护（≤15 分钟/天）

claude-mem 为自动后台记录，日常无需手动录入。15 分钟预算分配：

| 频率 | 动作 | 耗时 |
|---|---|---|
| 每天 | 检查 worker 存活：`curl -s http://localhost:${WORKER_PORT}/api/search?query=*&limit=1` | 1 分钟 |
| 每周五 | 拉取本周时间线、估算 token、生成/更新报告 | 10–15 分钟 |
| 每月初 | 检查 SQLite 体积、归档旧 session（如需） | 5 分钟 |

---

## 六、敏感信息约束

- Skill 的全部网络请求均为 `http://localhost`，数据库为本地文件 `~/.claude-mem/claude-mem.db`，**报告生成过程不调用任何外部服务**。
- ⚠️ **待确认假设：** claude-mem worker 自身是否会将观察数据同步到远端，取决于 claude-mem 本身的配置，SKILL.md 未说明。若你的环境有此顾虑，需在 claude-mem 配置层面关闭遥测/同步（本 Skill 不控制该行为）。
- 报告文件 `journey-into-*.md` 为本地 Markdown，不含自动上传逻辑；分享前自行审阅是否含敏感路径、密钥、内部人名等。

---

## 七、报告模板（对应 SKILL.md 的 10 个 Required Sections）

```markdown
# Journey Into [项目名]

## 1. Project Genesis
（项目何时、如何启动；最初提交、初始愿景、奠基技术决策、解决什么问题）

## 2. Architectural Evolution
（架构随时间如何变化；重大转向及原因；从初始设计到每次重构的脉络）

## 3. Key Breakthroughs
（「啊哈」时刻：难题攻克、新方法解锁进展、原型首次跑通；标注观察 ID 和时间戳）

## 4. Work Patterns
（开发节奏：调试集群、功能冲刺、重构阶段、探索阶段）

## 5. Technical Debt
（捷径在哪里取、何时还；积累模式与清偿模式）

## 6. Challenges and Debugging Sagas
（最难的问题：跨会话调试、架构死胡同、平台特定问题）

## 7. Memory and Continuity
（持久记忆如何影响开发；召回上下文节省时间或避免重复错误的时刻）

## 8. Token Economics & Memory ROI
（量化分析：总 discovery_tokens、有上下文注入的会话数、压缩比、
  最高价值观察 Top5、显式召回事件、被动/主动召回节省估算、净 ROI；
  按月分表；数据来自 SQLite 查询）

## 9. Timeline Statistics
（日期范围、观察/会话总数、按类型分布、最活跃日/周、最长调试会话）

## 10. Lessons and Meta-Observations
（全历史呈现的模式；新开发者能学到什么；反复出现的主题或原则）
```

写作要求（来自 SKILL.md）：技术叙述体而非要点罗列；引用具体观察 ID 和时间戳；跨时间关联事件；如实记录挣扎与死胡同；3000–6000 字；按时间顺序分析全部历史，不跳过早期。

---

## 八、一周试运行计划

> 前提：第 0 天需完成 claude-mem worker 安装启动。安装方式 SKILL.md 未提供，需你确认。

| 天 | 动作 | 耗时 | 产出/检查点 |
|---|---|---|---|
| 第 0 天 | 安装启动 claude-mem worker；验证端口和 `claude-mem.db` 生成；在目标项目跑一次健康检查 | 30 分钟（一次性） | worker 返回正常响应 |
| 第 1 天 | 正常开发，让 worker 自动记录；人工提炼旧资料为 `MILESTONES.md` | 开发+15 分钟 | 首批观察入库 |
| 第 2 天 | 日常开发；当天结束检查 worker 存活 | 1 分钟 | 观察持续增长 |
| 第 3 天 | 日常开发；中段检查：`curl .../api/context/inject?project=X&full=true` 看时间线是否非空 | 5 分钟 | 确认有数据 |
| 第 4 天 | 日常开发 | 1 分钟 | — |
| 第 5 天 | **首次试生成报告**：拉时间线→估算 token→生成→保存 | 15 分钟 | `journey-into-X.md` 初稿 |
| 第 6 天 | 审阅初稿：检查 10 个章节是否完整、时间线是否有断层、旧资料补充是否标注来源 | 15 分钟 | 问题清单 |
| 第 7 天 | 根据问题清单调整（如项目名错误、worker 配置、补充里程碑）；确定正式周更节奏 | 15 分钟 | 可复用的周更 SOP |

**一周后评估标准：**
- worker 连续 7 天无中断
- 报告 10 个章节均有实质内容（非空章节 ≤1 个）
- 每周维护总耗时 ≤ 30 分钟（日均 ≤5 分钟，远低于 15 分钟上限）
- 报告文件全程本地生成，无外部上传

---

## 九、无法访问的资源与待确认假设

1. **claude-mem 安装包/文档**：SKILL.md 未包含安装步骤，无法代为安装；需你提供安装方式或确认已安装。
2. **目标项目路径**：当前目录非项目目录，需你指定要分析的项目根目录。
3. **旧资料位置与格式**：题目称「旧资料结构混乱」但未提供文件，无法评估其内容或提炼里程碑。
4. **claude-mem worker 远端遥测行为**：Skill 不控制 worker 自身是否外传数据，需在 claude-mem 配置层面确认。
5. **无任何真实观察数据**：在 worker 运行并积累数据前，报告中的项目历史、token 指标、统计数字均无法生成，本方案不编造任何此类数据。
