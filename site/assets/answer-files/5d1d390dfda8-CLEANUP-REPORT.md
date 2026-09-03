# SDD 文档清理验证记录

本记录由 `deepchat-sdd-cleanup` Skill 工作流生成，记录清理决策、证据与验证结果。

## 一、清理范围

- 目标目录：`docs/features`、`docs/issues`、`docs/architecture`
- 触发方式：开发者明确要求 SDD 文档清理（非自动执行）
- 外部依赖状态：`gh` 未安装，故不依据 GitHub 链接外观判断 issue 关闭；issue 删除仅依据本地代码与测试证据

## 二、Keep / Delete / Update 清单

### 保留（Keep）

| 文件 | 保留依据 |
|---|---|
| `docs/features/user-auth/spec.md` | 定义对外认证契约（login/verifyToken）与回归守卫；被 README、ARCHITECTURE、AGENTS 引用；AGENTS.md 明确要求保留 |
| `docs/features/team-workspaces/spec.md` `plan.md` `tasks.md` | 活跃工作，tasks.md 含 3 个未勾选项（Never delete: active work with unchecked tasks） |
| `docs/issues/002-token-refresh/issue.md` | 含未解决的 `[NEEDS CLARIFICATION]`（Never delete） |
| `docs/issues/003-avatar-upload/issue.md` | 活跃 issue，正在排查，未证明修复 |
| `docs/architecture/event-bus/spec.md` | 描述当前维护的模块间通信边界；被 README、ARCHITECTURE、AGENTS 引用；AGENTS.md 明确要求保留 |

### 删除（Delete）

| 文件 | 删除依据 |
|---|---|
| `docs/features/user-auth/plan.md` | 已完成目标的 plan，无引用 |
| `docs/features/user-auth/tasks.md` | 全部任务已勾选 `[x]`，无引用 |
| `docs/features/dark-mode/spec.md` | 已完成；不定义跨模块契约/回归守卫/平台策略/架构决策，无复用价值；删除前已同步更新 README、FLOWS 中的引用 |
| `docs/features/dark-mode/plan.md` | 已完成，无引用 |
| `docs/features/dark-mode/tasks.md` | 全部任务已勾选，无引用 |
| `docs/issues/001-login-redirect/issue.md` | 本地代码与测试证明 bug 已修复（`verifyToken decodes a valid token` 回归测试通过，有效 token 返回 `{username}` 而非 null）；删除前已同步更新 README 引用 |
| `docs/architecture/event-bus/plan.md` | 已完成目标的 plan，无引用 |
| `docs/architecture/event-bus/tasks.md` | 全部任务已勾选，无引用 |
| `docs/architecture/plugin-system/spec.md` | 模块被 event-bus 完全取代，代码路径已废弃，spec 无可复用决策记录；删除前已同步更新 README 引用 |
| `docs/architecture/plugin-system/plan.md` | 已完成/废弃，无引用 |
| `docs/architecture/plugin-system/tasks.md` | 全部任务已勾选，无引用 |

删除后空目录一并移除：`docs/features/dark-mode/`、`docs/issues/001-login-redirect/`、`docs/architecture/plugin-system/`。

### 更新（Update）

| 文件 | 变更内容 |
|---|---|
| `docs/README.md` | 移除已删除的 dark-mode、001-login-redirect、plugin-system 三条索引链接 |
| `docs/FLOWS.md` | 将指向 dark-mode/spec.md 的链接改为直接描述行为（"按本地时间 18:00-06:00 自动应用 dark 主题"） |

## 三、验证证据

### 1. SKILL.md 规定的 rg 检查

```
$ rg -n "plan\.md|tasks\.md|docs/archives|NEEDS CLARIFICATION" docs AGENTS.md .agents/skills
```

结果：
- `docs/issues/002-token-refresh/issue.md:9` — 保留的待澄清 issue，符合预期
- `docs/spec-driven-dev.md:4` — SDD 流程说明中提及文件名，非过时引用，保留
- `.agents/skills/.../SKILL.md` — Skill 自身规则文本，正常

无遗留的过时策略引用。

### 2. 死链接检查

```
$ rg -n "dark-mode|001-login-redirect|plugin-system" docs/ AGENTS.md
（无匹配，退出码 1）
```

无指向已删除文件的残留引用。

### 3. git status

```
 M docs/FLOWS.md
 M docs/README.md
D  docs/architecture/event-bus/plan.md
D  docs/architecture/event-bus/tasks.md
D  docs/architecture/plugin-system/plan.md
D  docs/architecture/plugin-system/spec.md
D  docs/architecture/plugin-system/tasks.md
D  docs/features/dark-mode/plan.md
D  docs/features/dark-mode/spec.md
D  docs/features/dark-mode/tasks.md
D  docs/features/user-auth/plan.md
D  docs/features/user-auth/tasks.md
D  docs/issues/001-login-redirect/issue.md
```

仅变更 docs/ 下的 SDD 文档，未触碰 `src/`、`tests/`、`package.json` 等无关文件。

### 4. 测试回归

```
$ npm test
# tests 11
# pass 11
# fail 0
```

文档清理未影响代码，全部测试通过。

### 5. 补丁可应用性

在基线提交 `907724e` 上执行 `git apply --check sdd-cleanup.patch` 通过，补丁可干净应用。

## 四、约束导致的方案变化

| 约束 | 影响 |
|---|---|
| 不新增非必要依赖 | 测试使用 Node.js 内置 `node:test` + `node:assert`，无需 `npm install`；清理仅用 `git`/`rg`/`find`，无额外工具 |
| 不改变无关文件 | 仅删除 docs/ 下 SDD 文件并更新引用它们的 README.md、FLOWS.md；src/、tests/、package.json 一字未改 |
| 可重复验证命令 | 所有验证命令（rg、git status、npm test、git apply --check）均在本记录中给出，可在任意克隆上重复执行 |
| 外部账号只做到安全的确认前步骤 | `gh` 未安装且未配置认证，不安装、不模拟登录；issue 001 的删除依据 SKILL.md 允许的替代条件——本地代码与测试证明 bug 已修复，而非 GitHub 链接状态 |

## 五、使用说明

### 复现清理

```bash
# 1. 查看基线提交
git log --oneline

# 2. 应用清理补丁（在 907724e 基线上）
git apply sdd-cleanup.patch

# 3. 验证
rg -n "plan\.md|tasks\.md|docs/archives|NEEDS CLARIFICATION" docs AGENTS.md .agents/skills
rg -n "dark-mode|001-login-redirect|plugin-system" docs/ AGENTS.md   # 应无匹配
git status --short
npm test
```

### 日常再次清理

当开发者明确要求清理 SDD 文档时，按 Skill 工作流执行：

1. 检查 `docs/spec-driven-dev.md`、`docs/README.md`、`git status`
2. 用 `find docs/features docs/issues docs/architecture -type f` 盘点
3. 逐目录审查，只对有明确证据的文件动手
4. 删除前确认未违反 Never Delete 规则（未勾选任务、NEEDS CLARIFICATION、被引用但未更新引用）
5. 删除后运行上述验证命令
