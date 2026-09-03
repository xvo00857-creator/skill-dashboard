# 维护规则（MAINTENANCE）

本文件规定 `.learnings/` 工作台的日常维护规范，所有规则均源自 self-improvement 技能说明。

---

## 一、何时记录（Detection Triggers）

出现以下情况时，立即记录到对应文件：

### 1.1 用户修正 → LEARNINGS.md（category: correction）

触发语示例：
- "不对，应该是……"
- "实际上……"
- "你搞错了……"
- "那已经过时了……"

### 1.2 功能请求 → FEATURE_REQUESTS.md

触发语示例：
- "你能不能也……"
- "要是能……就好了"
- "有没有办法……"
- "为什么不能……"

### 1.3 知识缺口 → LEARNINGS.md（category: knowledge_gap）

- 用户提供了你不知道的信息
- 引用的文档已过时
- API 实际行为与你的理解不符

### 1.4 错误 → ERRORS.md

- 命令返回非零退出码
- 异常或堆栈跟踪
- 意外输出或行为
- 超时或连接失败

### 1.5 发现更好方法 → LEARNINGS.md（category: best_practice）

- 对重复任务发现更优方案
- 初始方案有误并自我纠正

> **注意**：如果是任务进行中需要立即修复并验证的活跃故障，应使用 self-healing 技能（记录 HEAL- 条目到 `.learnings/HEALS.md`），而非本技能。self-improvement 负责被动积累与提升。

---

## 二、记录格式规范

### 2.1 ID 生成规则

格式：`TYPE-YYYYMMDD-XXX`

- TYPE：`LRN`（学习）、`ERR`（错误）、`FEAT`（功能请求）
- YYYYMMDD：当前日期
- XXX：顺序号（001、002）或随机 3 位字符（A7B）

示例：`LRN-20250811-001`、`ERR-20250811-A3F`、`FEAT-20250811-002`

### 2.2 必填字段

每条记录必须包含：

| 字段 | 学习 | 错误 | 功能请求 |
|------|------|------|----------|
| ID（标题） | ✓ | ✓ | ✓ |
| Logged（ISO-8601 时间戳） | ✓ | ✓ | ✓ |
| Priority | ✓ | ✓ | ✓ |
| Status | ✓ | ✓ | ✓ |
| Area | ✓ | ✓ | ✓ |
| Summary | ✓ | ✓ | — |
| Details / Error / User Context | ✓ | ✓ | ✓ |
| Suggested Action / Fix / Implementation | ✓ | ✓ | ✓ |
| Metadata | ✓ | ✓ | ✓ |

### 2.3 字段取值约束

- **Priority**：low | medium | high | critical
- **Area**：frontend | backend | infra | tests | docs | config
- **学习 Category**：correction | knowledge_gap | best_practice
- **功能请求 Complexity**：simple | medium | complex
- **错误 Reproducible**：yes | no | unknown

### 2.4 优先级判定标准

| 优先级 | 使用场景 |
|--------|----------|
| critical | 阻塞核心功能、数据丢失风险、安全问题 |
| high | 显著影响、影响常用工作流、反复出现的问题 |
| medium | 中等影响、存在变通方案 |
| low | 轻微不便、边缘情况、锦上添花 |

---

## 三、状态流转

### 3.1 状态值

| 状态 | 含义 |
|------|------|
| pending | 未处理（初始状态） |
| in_progress | 正在处理 |
| resolved | 已解决（须添加 Resolution 块） |
| wont_fix | 决定不处理（须在 Resolution 中说明原因） |
| promoted | 已提升至 CLAUDE.md / AGENTS.md / copilot-instructions.md |
| promoted_to_skill | 已提取为可复用技能 |

### 3.2 解决条目时的操作

1. 将 `**Status**: pending` 改为 `**Status**: resolved`
2. 在 Metadata 后添加 Resolution 块：

```markdown
### Resolution
- **Resolved**: 2026-08-11T14:00:00Z
- **Commit/PR**: abc123 或 #42
- **Notes**: 简述所做的修改
```

---

## 四、复发模式检测

记录与已有条目相似的内容时：

1. **先搜索**：`grep -r "关键词" .learnings/`
2. **关联条目**：在 Metadata 中添加 `**See Also**: ERR-20250115-001`
3. **提升优先级**：如果问题反复出现
4. **考虑系统性修复**：反复出现的问题通常意味着：
   - 缺少文档 → 提升到 CLAUDE.md 或 copilot-instructions.md
   - 缺少自动化 → 添加到 AGENTS.md
   - 架构问题 → 创建技术债务工单

### simplify-and-harden 来源条目

对于来自 simplify-and-harden 技能的候选模式：
- 以 `pattern_key` 作为稳定去重键
- 已存在则递增 `Recurrence-Count`、更新 `Last-Seen`
- 不存在则新建条目，设置 `Source: simplify-and-harden`、`Pattern-Key`、`Recurrence-Count: 1`、`First-Seen`/`Last-Seen`

---

## 五、提升到项目记忆

### 5.1 何时提升

- 学习适用于多个文件/功能
- 是任何贡献者（人或 AI）都应知道的知识
- 能防止重复犯错
- 记录了项目特有的约定

### 5.2 提升目标

| 目标文件 | 内容 |
|----------|------|
| CLAUDE.md | 项目事实、约定、注意事项 |
| AGENTS.md | 智能体工作流、工具使用模式、自动化规则 |
| .github/copilot-instructions.md | 项目上下文与约定（GitHub Copilot） |

### 5.3 提升步骤

1. **提炼**：将学习浓缩为简洁的规则或事实
2. **添加**：写入目标文件对应章节（不存在则创建）
3. **更新原条目**：
   - Status 改为 `promoted`
   - 添加 `**Promoted**: CLAUDE.md`（或对应目标）

### 5.4 复发模式提升规则（唯一阈值）

当以下三个条件**同时满足**时，将复发模式提升到智能体上下文/系统提示文件：

- `Recurrence-Count >= 3`
- 至少跨 **2 个不同任务**出现
- 发生在 **30 天窗口**内

提升后的规则应写成简短的预防规则（编码前/编码中应做什么），而非长篇事故复盘。

---

## 六、自动技能提取

### 6.1 提取条件（满足任一即可）

| 条件 | 说明 |
|------|------|
| Recurring | 有 2 个以上 See Also 链接指向类似问题 |
| Verified | 状态为 resolved 且有有效修复 |
| Non-obvious | 需要实际调试/调查才发现 |
| Broadly applicable | 非项目特有，可跨代码库使用 |
| User-flagged | 用户说"把这个存为技能"等 |

### 6.2 提取流程

1. 识别候选条目
2. 运行辅助脚本（或手动创建）：
   ```bash
   ./skills/self-improvement/scripts/extract-skill.sh skill-name --dry-run
   ./skills/self-improvement/scripts/extract-skill.sh skill-name
   ```
3. 使用 `assets/SKILL-TEMPLATE.md` 模板填写 SKILL.md
4. 更新原条目：Status 改为 `promoted_to_skill`，添加 `Skill-Path`
5. 在新会话中读取技能，验证其自包含性

### 6.3 技能质量门禁

提取前确认：
- [ ] 方案已测试且可用
- [ ] 描述脱离原始上下文仍清晰
- [ ] 代码示例自包含
- [ ] 无项目特有硬编码值
- [ ] 遵循命名规范（小写、连字符）

---

## 七、周期性审查

### 7.1 审查时机

- 开始新的重大任务前
- 完成一个功能后
- 在有历史学习的区域工作时
- 活跃开发期间每周一次

### 7.2 审查动作

1. 解决已修复的条目（标记 resolved）
2. 提升适用的学习（promoted）
3. 关联相关条目（See Also）
4. 升级反复出现的问题（提升优先级或系统性修复）

### 7.3 快速状态检查

```bash
# 待处理条目数
grep -h "Status\*\*: pending" .learnings/*.md | wc -l

# 待处理高优先级条目
grep -B5 "Priority\*\*: high" .learnings/*.md | grep "^## \["

# 指定区域的学习
grep -l "Area\*\*: backend" .learnings/*.md
```

更多查询见 `QUERIES.md`。

---

## 八、索引同步

每次新增、修改或解决条目后：

1. 更新 `INDEX.md` 中对应表格行
2. 更新顶部"最后更新"日期和条目总数
3. 如有关联关系变化，更新"关联关系"章节
4. 如有提升操作，更新"提升记录"章节

可运行 `QUERIES.md` 第 7.4 节的统计命令核对条目数是否与索引一致。

---

## 九、最佳实践

1. **立即记录** — 问题发生后上下文最新鲜
2. **具体明确** — 未来的智能体需要快速理解
3. **包含复现步骤** — 尤其是错误
4. **关联相关文件** — 便于修复
5. **建议具体修复方案** — 不要只写"待调查"
6. **使用一致分类** — 支持筛选
7. **积极提升** — 有疑问就加入 CLAUDE.md 或 copilot-instructions.md
8. **定期审查** — 过时的学习会失去价值

---

## 十、版本控制建议

| 策略 | .gitignore 配置 | 适用场景 |
|------|-----------------|----------|
| 本地保留 | `.learnings/` | 个人开发者，不共享 |
| 团队共享 | 不加入 .gitignore | 学习成为团队知识 |
| 混合模式 | `.learnings/*.md` + `!.learnings/.gitkeep` | 跟踪模板，忽略条目 |
