# 自我改进工作台（.learnings/ INDEX）

本工作台依据 self-improvement Skill（`SKILL.md`）规范搭建，用于跨会话工作记录的分类、检索与维护。

---

## 0. 数据来源与约束声明（务必先读）

| 项目 | 说明 |
|------|------|
| 数据来源 | self-improvement Skill 自带的 `references/examples.md` 中的 9 条示例条目 |
| 数据性质 | **示例数据，非真实跨会话工作记录**；ID、时间戳、内容均原样保留，未编造 |
| 真实记录 | **待确认**：用户未提供真实工作记录，待提供后追加或替换 |
| 搭建时间 | 2026-08-12（UTC+8） |
| 适用环境 | 本环境无 Claude Code / Codex / Copilot / OpenClaw 钩子运行时，故 Skill 的自动钩子（activator.sh、error-detector.sh）与 OpenClaw 集成**未启用**，仅采用 Skill 的文件格式与 grep 检索规范 |

---

## 1. 分类结果

### 1.1 按记录类型

| 类型 | 文件 | 数量 | 条目 ID |
|------|------|------|---------|
| 经验（Learning） | `LEARNINGS.md` | 5 | LRN-20250115-001, LRN-20250115-002, LRN-20250115-003, LRN-20250116-001, LRN-20250118-001 |
| 错误（Error） | `ERRORS.md` | 2 | ERR-20250115-A3F, ERR-20250120-B2C |
| 功能请求（Feature） | `FEATURE_REQUESTS.md` | 2 | FEAT-20250115-001, FEAT-20250110-002 |
| **合计** | | **9** | |

### 1.2 按领域（Area）

| Area | 数量 | 条目 |
|------|------|------|
| backend | 4 | LRN-20250115-003, LRN-20250116-001, ERR-20250120-B2C, FEAT-20250115-001 |
| infra | 2 | LRN-20250118-001, ERR-20250115-A3F |
| tests | 1 | LRN-20250115-001 |
| config | 1 | LRN-20250115-002 |
| frontend | 1 | FEAT-20250110-002 |
| docs | 0 | — |

### 1.3 按优先级（Priority）

| Priority | 数量 | 条目 |
|----------|------|------|
| critical | 1 | ERR-20250120-B2C |
| high | 5 | LRN-20250115-001, LRN-20250115-003, LRN-20250116-001, LRN-20250118-001, ERR-20250115-A3F |
| medium | 2 | LRN-20250115-002, FEAT-20250115-001 |
| low | 1 | FEAT-20250110-002 |

### 1.4 按状态（Status）

| Status | 数量 | 条目 |
|--------|------|------|
| pending | 4 | LRN-20250115-001, ERR-20250115-A3F, ERR-20250120-B2C, FEAT-20250115-001 |
| resolved | 2 | LRN-20250115-002, FEAT-20250110-002 |
| promoted | 2 | LRN-20250115-003 → CLAUDE.md；LRN-20250116-001 → AGENTS.md |
| promoted_to_skill | 1 | LRN-20250118-001 → skills/docker-m1-fixes |

### 1.5 经验子类（仅 LRN）

| Category | 数量 | 条目 |
|----------|------|------|
| correction | 1 | LRN-20250115-001 |
| knowledge_gap | 1 | LRN-20250115-002 |
| best_practice | 3 | LRN-20250115-003, LRN-20250116-001, LRN-20250118-001 |

---

## 2. 条目清单（含定位）

| ID | 类型 | 标题 | Area | Priority | Status | 文件 |
|----|------|------|------|----------|--------|------|
| LRN-20250115-001 | correction | pytest fixture 作用域误判 | tests | high | pending | LEARNINGS.md |
| LRN-20250115-002 | knowledge_gap | 项目用 pnpm 而非 npm | config | medium | resolved | LEARNINGS.md |
| LRN-20250115-003 | best_practice | API 响应须回传 correlation ID | backend | high | promoted → CLAUDE.md | LEARNINGS.md |
| LRN-20250116-001 | best_practice | OpenAPI 变更后须重新生成 API client | backend | high | promoted → AGENTS.md | LEARNINGS.md |
| LRN-20250118-001 | best_practice | Apple Silicon 上 Docker 构建平台不匹配 | infra | high | promoted_to_skill | LEARNINGS.md |
| ERR-20250115-A3F | docker_build | M1 Mac Docker 构建失败 | infra | high | pending | ERRORS.md |
| ERR-20250120-B2C | api_timeout | 第三方支付 API 超时 | backend | critical | pending | ERRORS.md |
| FEAT-20250115-001 | export_to_csv | 分析结果导出 CSV | backend | medium | pending | FEATURE_REQUESTS.md |
| FEAT-20250110-002 | dark_mode | 仪表盘深色模式 | frontend | low | resolved | FEATURE_REQUESTS.md |

---

## 3. 关联与待确认项

### 3.1 已验证的关联
- **LRN-20250118-001 ↔ ERR-20250115-A3F**：同一 Docker M1 平台问题，错误条目与提升为 skill 的经验条目互相关联（LRN 的 See Also 引用了该 ERR，且 ERR 存在于本数据集）。

### 3.2 悬空引用（待确认）
以下 See Also 引用的 ID 在本数据集中**不存在**，无法验证其真实性，可能是示例数据中的占位引用：

| 来源条目 | 悬空引用 | 状态 |
|----------|----------|------|
| LRN-20250118-001 | ERR-20250117-B2D | 待确认：数据集中无此条目 |
| ERR-20250120-B2C | ERR-20250115-X1Y | 待确认：数据集中无此条目 |
| ERR-20250120-B2C | ERR-20250118-Z3W | 待确认：数据集中无此条目 |

### 3.3 晋升规则核查（待确认）
SKILL.md「Promotion Rule」规定， recurring 模式晋升须同时满足：Recurrence-Count ≥ 3、跨至少 2 个不同任务、30 天窗口内。
- 当前 9 条示例均**未设置** `Pattern-Key` / `Recurrence-Count` / `First-Seen` / `Last-Seen` 字段，无法据此判定任何新模式是否达到晋升阈值。
- LRN-20250115-003、LRN-20250116-001、LRN-20250118-001 的 promoted / promoted_to_skill 状态为示例数据自带，**其晋升前提是否满足三条件无法验证**，标注为待确认。
- 因此本次**未新建** CLAUDE.md / AGENTS.md，也未运行 extract-skill.sh 创建新 skill——在缺乏验证证据时执行这些操作将构成编造已完成状态。

### 3.4 其他待确认
- 示例中 `Commit/PR: #142`、`src/middleware/correlation.ts` 等文件路径与 PR 编号均来自示例，**未在本环境验证存在性**。
- 示例时间戳为 2025-01，与当前日期 2026-08-12 不符，属示例数据原貌，未改动。

---

## 4. 查询示例

以下命令均在项目根目录（`.learnings/` 的父目录）执行，兼容 SKILL.md「Periodic Review」节给出的 grep 用法。

> 注意：因本目录新增了 INDEX.md，用 `.learnings/*.md` 会把 INDEX.md 自身的命令示例也匹配进去。故数据查询一律显式列出三个数据文件，或加 `--exclude=INDEX.md`。所有 grep 使用 `-F`（固定字符串）避免 `**` 被当作正则运算符；多文件查询加 `-h` 抑制文件名前缀。

```bash
# 数据文件变量（可选，便于复用）
L=".learnings/LEARNINGS.md .learnings/ERRORS.md .learnings/FEATURE_REQUESTS.md"

# 4.1 统计待处理条目数
grep -hF "Status**: pending" $L | wc -l

# 4.2 列出高优先级条目标题
grep -h -B5 -F "Priority**: high" $L | grep "^## \["

# 4.3 列出 critical 优先级条目
grep -h -B5 -F "Priority**: critical" $L | grep "^## \["

# 4.4 按领域筛选（如 backend），列出命中文件
grep -lF "Area**: backend" $L

# 4.5 按状态筛选（如 resolved）
grep -h -B8 -F "Status**: resolved" $L | grep "^## \["

# 4.6 按 ID 直接定位
grep -nF "LRN-20250118-001" .learnings/LEARNINGS.md

# 4.7 按关键词检索全文（如 docker）
grep -rnF "docker" .learnings/ --include=LEARNINGS.md --include=ERRORS.md --include=FEATURE_REQUESTS.md

# 4.8 按标签检索（如 api）
grep -rnF "Tags:" $L | grep -F "api"

# 4.9 查找含 See Also 关联的条目
grep -rnF "See Also" $L

# 4.10 查找已晋升条目
grep -rnF "Promoted" $L

# 4.11 录入前查重（SKILL.md「Recurring Pattern Detection」要求先搜）
grep -rnF "docker" $L

# 4.12 统计各类型条目总数
grep -c "^## \[" $L
```

> 检索机制说明：Skill 原生检索即基于 Markdown + grep，未引入数据库或额外索引工具。这是在时间/资源受限下的刻意取舍——零依赖、与 Skill 规范一致、可跨会话直接使用；代价是不支持复杂结构化查询，条目量大后需考虑升级（见第 5 节维护规则）。

---

## 5. 维护规则（提炼自 SKILL.md）

### 5.1 录入规则
1. **即时记录**：问题发生后立即记录，上下文最新鲜（SKILL.md Best Practices #1）。
2. **写入正确文件**：
   - 用户纠正 / 知识过时 / 发现更好做法 → `LEARNINGS.md`（category: correction / knowledge_gap / best_practice）
   - 命令失败 / API 错误 / 异常 / 超时 → `ERRORS.md`
   - 用户要求缺失能力 → `FEATURE_REQUESTS.md`
3. **ID 格式**：`TYPE-YYYYMMDD-XXX`，TYPE 为 LRN/ERR/FEAT，XXX 为顺序号或 3 位随机字符（如 `001`、`A7B`）。
4. **必填字段**：Logged（ISO-8601）、Priority（critical/high/medium/low）、Status（pending 起）、Area（frontend/backend/infra/tests/docs/config）。
5. **具体可执行**：Summary 一行说清；Details 写清前因后果；Suggested Action 给具体修复，不写"待调查"。

### 5.2 查重与关联
6. **录入前先搜**：`grep -r "关键词" .learnings/`，避免重复（SKILL.md Recurring Pattern Detection）。
7. **相似条目**：在 Metadata 加 `**See Also**: <ID>`；反复出现则提升优先级。
8. **循环模式跟踪**：对 simplify-and-harden 来源的重复模式，使用 `Pattern-Key`、`Recurrence-Count`、`First-Seen`、`Last-Seen` 字段。

### 5.3 状态流转
9. **修复后**：将 `Status: pending` 改为 `resolved`，并追加 Resolution 块（Resolved 时间、Commit/PR、Notes）。
10. **其他状态**：in_progress（处理中）、wont_fix（不处理，须注明原因）、promoted（已晋升到 CLAUDE.md/AGENTS.md 等）、promoted_to_skill（已抽取为 skill）。

### 5.4 晋升规则
11. **广泛适用的经验**应晋升到项目记忆文件：
    - `CLAUDE.md`：项目事实、约定、陷阱
    - `AGENTS.md`：agent 工作流、工具使用模式
    - `.github/copilot-instructions.md`：Copilot 项目约定
12. **晋升阈值（三条件须同时满足）**：Recurrence-Count ≥ 3、跨至少 2 个不同任务、发生在 30 天窗口内。
13. 晋升后将原条目 Status 改为 `promoted`，并加 `**Promoted**: <目标文件>`。

### 5.5 Skill 抽取
14. 当经验满足以下任一条件时可抽取为独立 skill：重复出现（2+ See Also）、已验证解决、非显而易见、跨项目通用、用户明确要求。
15. 可用 `scripts/extract-skill.sh <name> [--dry-run]` 生成脚手架，再填充内容；抽取后原条目状态改为 `promoted_to_skill` 并加 `Skill-Path`。
16. 抽取前过质量门：方案已测试、描述脱离上下文仍清晰、代码自包含、无项目硬编码、命名小写连字符。

### 5.6 定期评审
17. **评审时机**：大任务开始前、功能完成后、涉及历史经验领域时、活跃开发期每周。
18. **评审动作**：关闭已修复项、晋升符合条件的经验、关联相似条目、上报反复出现的问题。
19. **本环境限制**：自动钩子（activator/error-detector）需 Claude Code/Codex/Copilot 运行时，本环境不可用；改为在任务收尾时人工执行第 4 节查询命令检查。

### 5.7 资源受限时的取舍（本次新增）
20. **优先级**：先保证录入格式正确与可检索（grep），再做晋升与 skill 抽取；无验证证据的晋升一律不做。
21. **单一入口**：分类、查询、维护规则集中于本 INDEX.md，减少文件数与维护成本；条目量超过 ~50 条或多人协作时再拆分为独立文件。
22. **待确认标注**：任何无法在本环境验证的信息（悬空引用、提交号、文件存在性、晋升前提）一律标注"待确认"，不假定为真。
