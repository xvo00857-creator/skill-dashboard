# PR 发布前检查清单

基于 pr-to-main Skill 工作流，针对 `fix/vscode-changesets-changelog` → `main`。

## 1. 上下文收集
- [x] `git status` 干净（所有变更已提交）
- [x] `git diff main...HEAD` 仅包含 vscode 包相关文件 + changeset
- [x] `git log main..HEAD --oneline` 审阅全部 3 个提交
- [x] 确认无远程 upstream（本地分支，需 `git push -u`）

## 2. 范围与类型
- [x] 受影响包：`packages/vscode` → npm 包名 `cc-wf-studio`
- [x] 变更类型：`fix`（来自提交前缀 `fix(vscode):`）
- [x] 未触及 `packages/core`、`packages/mcp`、`packages/cli`
- [x] 未触及根配置、`.github/`、docs 等无关文件

## 3. Changeset（发布管线关键项）
- [x] 已创建 `.changeset/fix-changesets-changelog.md`
- [x] 目标包正确：`cc-wf-studio`（仅 vscode 扩展）
- [x] bump 级别：`patch`（bug 修复）
- [x] `pnpm changeset status` 确认识别为 patch
- [x] 非空 changeset（需要发布，非 CI/文档类变更）

## 4. 构建验证
- [x] `pnpm check` 通过（TypeScript 类型检查）
- [x] `pnpm build` 通过（完整编译）
- [x] 回归测试 10/10 通过
- [x] 未新增任何运行时依赖（仅 @types/node 为必要类型依赖）

## 5. PR 格式
- [x] 类型：fix → 使用 `assets/fix-template.md`
- [x] 标题：`fix(vscode): parse Changesets-format CHANGELOG`（≤50 字符，祈使语气）
- [x] 正文使用英文（仓库规则）
- [x] Changes 段使用真实 monorepo 路径
- [x] 正文提及 changeset 的发布效果
- [x] squash 合并后标题即为提交主题

## 6. 推送与创建 PR（需外部账号，待确认）
- [ ] `git push -u origin fix/vscode-changesets-changelog`
- [ ] `gh pr create --base main --title "..." --body-file ...`
- [ ] 确认 CI 通过
- [ ] 人工 code review 后 squash 合并
- [ ] 发布由人工通过 Release PR 触发（Skill 明确禁止自行触发发布）
