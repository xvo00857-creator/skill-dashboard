# 跨会话工作记录可检索工作台

基于 self-improvement 技能规范搭建的工作记录管理工作台，用于沉淀跨会话的学习、错误与功能请求，支持分类检索、状态跟踪与知识提升。

---

## 一、输入假设

本次任务的输入情况如下：

1. **Skill 输入**：已接收并解压 `self-improvement.zip`，完整阅读了 `SKILL.md` 及全部 assets、references 文件。
2. **工作记录输入**：消息中**未附带实际的跨会话工作记录数据**（无文本、表格、日志或历史会话导出文件）。当前工作目录仅包含 Skill ZIP 本身。
3. **种子数据假设**：为使工作台可验证、可查询，使用 Skill 自带的示例记录（来源：`references/examples.md`）作为种子数据填入三个核心文件。这些示例数据明确标注，不代表真实工作记录。
4. **环境假设**：工作台位于项目根目录 `.learnings/` 下，使用标准 grep 命令检索，无需额外依赖。

**如需录入真实工作记录**，请将记录内容（文本、Markdown、CSV、JSON 等任意格式）提供给我，我将按 Skill 规范解析、分类并追加到对应文件，同时更新索引。

---

## 二、验收标准

本工作台满足以下可验证条件：

| 编号 | 验收项 | 验证方式 |
|------|--------|----------|
| V1 | 三个核心记录文件存在且格式符合 SKILL.md 规范 | 检查文件结构与字段完整性 |
| V2 | 每条记录有唯一 ID（TYPE-YYYYMMDD-XXX） | `grep "^## \[" .learnings/*.md` |
| V3 | 分类索引覆盖全部条目，统计数与实际一致 | 对比 INDEX.md 与 grep 计数 |
| V4 | 查询命令可实际执行并返回正确结果 | 运行 QUERIES.md 中命令 |
| V5 | 维护规则覆盖记录、状态流转、提升、审查全流程 | 检查 MAINTENANCE.md 章节 |
| V6 | 种子数据来源明确标注 | 检查文件头部说明 |
| V7 | 无虚构的工具调用、文件或已完成状态 | 全部产物可在文件系统中核验 |

---

## 三、目录结构

```
.learnings/
├── README.md              # 本文件：工作台说明与输入假设
├── INDEX.md               # 分类索引：按类型/状态/优先级/区域的总览
├── QUERIES.md             # 查询示例：可直接执行的 grep 命令集
├── MAINTENANCE.md         # 维护规则：记录、流转、提升、审查规范
├── LEARNINGS.md           # 学习记录（correction / knowledge_gap / best_practice）
├── ERRORS.md              # 错误记录（命令失败、API 错误、异常行为）
└── FEATURE_REQUESTS.md    # 功能请求（用户需要但尚缺失的能力）
```

### 文件职责

| 文件 | 记录什么 | ID 前缀 |
|------|----------|---------|
| LEARNINGS.md | 用户修正、知识缺口、最佳实践 | LRN- |
| ERRORS.md | 命令失败、API 错误、超时、异常 | ERR- |
| FEATURE_REQUESTS.md | 用户请求的缺失能力 | FEAT- |

---

## 四、快速开始

### 4.1 查看总览

打开 `INDEX.md`，或运行：

```bash
grep "^## \[" .learnings/*.md
```

### 4.2 查找待处理高优先级项

```bash
grep -B5 "Priority\*\*: high" .learnings/*.md | grep "^## \["
```

### 4.3 搜索关键词

```bash
grep -rn "docker" .learnings/
```

更多查询见 `QUERIES.md`。

---

## 五、录入新记录

### 5.1 手动录入

1. 判断类型：学习 / 错误 / 功能请求
2. 打开对应文件，按文件中已有条目格式追加
3. 生成 ID：`类型前缀-当天日期-三位序号`（如 `LRN-20260811-001`）
4. 填写全部必填字段（见 MAINTENANCE.md 第二节）
5. 更新 INDEX.md 对应表格和统计数

### 5.2 录入真实跨会话记录

将原始记录提供给我后，我将：

1. 逐条解析原始内容
2. 按类型分类（学习/错误/功能请求）
3. 为每条记录生成规范 ID 和完整字段
4. 追加到对应文件
5. 更新 INDEX.md 分类索引
6. 运行 QUERIES.md 统计命令核对一致性

### 5.3 自动提醒（可选）

Skill 提供 hook 脚本，可在 Claude Code / Codex CLI 中配置自动提醒：

- `scripts/activator.sh`：每次提交提示后注入学习评估提醒
- `scripts/error-detector.sh`：Bash 工具调用后自动检测错误模式

配置方法见 Skill 的 `references/hooks-setup.md`。

---

## 六、数据来源与缺失项声明

### 已完成

- Skill ZIP 解压与 SKILL.md 完整阅读
- 三个核心记录文件创建（含规范头部和示例种子数据）
- 分类索引 INDEX.md
- 查询示例 QUERIES.md（命令已验证可执行）
- 维护规则 MAINTENANCE.md
- 本说明文件

### 缺失项

| 缺失项 | 影响 | 解决方式 |
|--------|------|----------|
| 真实跨会话工作记录数据 | 工作台目前仅含 Skill 示例数据，无法反映真实工作内容 | 提供记录文件或直接粘贴内容，我将解析录入 |
| self-healing 技能（配对技能） | 活跃运行时故障的修复与验证流程不可用 | 如需运行时自愈能力，需另行安装 self-healing 技能 |
| Hook 配置 | 自动错误检测与提醒未启用 | 按需配置 .claude/settings.json，见 Skill 说明 |
| gh / npx skills CLI | 无法通过 `gh skill install` 正式安装 | 本工作台已手动按规范搭建，不依赖 CLI |

### 种子数据说明

三个核心文件中的 9 条记录全部来自 Skill 包内 `references/examples.md` 的官方示例，
内容为英文场景（pytest、Docker、pnpm、API 超时等），仅用于演示格式和验证查询。
录入真实数据时可保留或删除这些示例。
