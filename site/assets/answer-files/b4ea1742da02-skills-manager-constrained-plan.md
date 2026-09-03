# skills-manager 受约束执行流程方案

> 基于 skills-manager/SKILL.md 制定，所有操作均在当前授权目录内完成，未静默创建、删除或覆盖任何外部资源。

## 一、预检（Pre-check）

| 检查项 | 命令/方式 | 本次结果 |
|--------|-----------|----------|
| Node.js 运行时 | `node --version` | v20.19.2 可用 |
| npx 包执行器 | `npx --version` | 10.8.2 可用 |
| 备用运行时 `$CHERRY_STUDIO_BUN_PATH` | `echo $CHERRY_STUDIO_BUN_PATH` | 未设置，走 npx 路径 |
| `find-skills` 优先命令 | `which find-skills` | 不存在，降级到 CLI |
| `skill-creator` 本地 Skill | 检查各 skills 根目录 | 未安装（注册表中存在 `anthropics/skills@skill-creator`，但需用户确认后才能安装） |
| `npx skills` CLI 可用性 | `npx skills --help` | 可用，支持 find/add/list/init/remove/update |
| 已安装 Skill 清单 | `npx skills list` / `list -g` | 项目级无；用户级有若干（lark-* 等） |

## 二、幂等（Idempotency）

- **创建前**：检查目标目录是否已存在（`ls <skill-name>`），存在则中止并提示，不覆盖。
- **安装前**：`npx skills list` 确认目标 Skill 未安装；重复安装应跳过或提示更新。
- **初始化**：`npx skills init <name>` 自身在目录已存在时不会覆盖已有 SKILL.md（本次实测前先手动确认目录不存在）。
- **搜索**：`npx skills find` 为只读操作，天然幂等。

## 三、重试（Retry）

- npx 首次运行需下载包，可能因网络超时；本次采用后台任务 + 等待完成方式，失败可重跑（npx 会使用缓存）。
- 网络类错误（如 `find` 请求失败）最多重试 2 次，仍失败则告知用户并建议直接完成任务。
- 脚本验证失败时，修正后重跑验证，直到通过（SKILL.md 第 25 行要求）。

## 四、人工确认点（Human Confirmation）

| 操作 | 风险等级 | 确认要求 |
|------|----------|----------|
| `npx skills find` | 无（只读） | 无需确认 |
| `npx skills list` | 无（只读） | 无需确认 |
| `npx skills add <repo> --list` | 低（仅克隆预览，不安装） | 无需确认，但需展示来源 URL |
| `npx skills add <repo>@<skill>` | **高**（第三方代码，有完整权限） | **必须**：展示安全警告 + 源码链接 + 用户明确确认后才执行 |
| `npx skills init <name>` | 中（在本地创建文件） | 需告知创建位置和内容，在授权目录内执行 |
| `npx skills remove` | 高（删除已安装 Skill） | 需用户确认目标和范围 |
| 安装 `skill-creator` | **高**（同上） | 需安全警告 + 来源链接 + 用户确认 |

## 五、本次实际执行的演示

### 5.1 搜索演示（只读，已完成）

```
npx skills find "pdf"
```
返回 18+ 条结果，包含名称、安装量、来源链接（如 `anthropics/skills@pdf`，177.1K installs）。

### 5.2 创建演示（已完成，可核验）

按 SKILL.md 降级路径执行：

1. 确认 `skill-creator` 本地不可用 → 明确告知降级
2. 幂等检查：`demo-skill-validator/` 不存在
3. 执行 `npx skills init demo-skill-validator`
4. 编写精简的 SKILL.md（含 name、description 触发描述）
5. 添加 `scripts/validate_skill.py` 校验脚本
6. 验证（SKILL.md 第 25 行要求）：
   - 对自身运行 → PASS
   - 对 skills-manager 原 Skill 运行 → PASS
   - 对占位文本负面用例运行 → FAIL（符合预期，退出码 1）

### 5.3 安装预览（只读，已完成）

```
npx skills add anthropics/skills --list
```
克隆仓库并列出 18 个可用 Skill，来源 `https://github.com/anthropics/skills.git`，**未执行安装**。若要实际安装，需按安全流程经用户确认。

## 六、未执行/需确认的操作

- **未安装任何第三方 Skill**：包括 `skill-creator`，因 SKILL.md 明确要求第三方代码安装前必须用户确认。
- **未删除/覆盖任何已有资源**：所有新建文件均在项目目录内。
- **未发布 Skill**：`npx skills init` 输出的发布指引仅作参考，未执行推送或托管。

## 七、Skill 真实能力边界说明

- skills-manager 本身是一个**流程编排型 Skill**，不包含可执行脚本，其能力依赖外部 `npx skills` CLI。
- 它不直接实现搜索/安装逻辑，而是规定何时调用 CLI、何时降级、安全确认流程。
- 题目假设的"评估或生命周期管理"中，`npx skills` 支持 `list`/`update`/`remove`，但 `remove`/`update` 属于高风险操作，本次未执行。
