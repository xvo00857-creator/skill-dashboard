# PR to Main 清理检查清单

适用场景：特性分支已通过 squash merge 合入 main，需要清理本地与远程分支。
依据：`pr-to-main-cleanup/SKILL.md`

## 执行前确认

- [ ] 当前在正确的 git 仓库目录内
- [ ] PR 已在平台上合入 main（squash merge）
- [ ] 特性分支上的工作已全部合入，无未提交改动（`git status` 干净）
- [ ] 已知要删除的特性分支名称（通过 `git branch` 确认）

## 执行步骤（严格按 SKILL.md）

1. [ ] 收集上下文：
   - `git branch`（确认当前分支与待删分支）
   - `git log --oneline -1`（确认当前状态）
2. [ ] 切换到 main：`git checkout main`
3. [ ] 拉取最新 main：`git pull origin main`
4. [ ] 删除本地特性分支（squash 合并必须用 `-D`）：`git branch -D <branch-name>`
5. [ ] 删除远程特性分支：`git push origin --delete <branch-name>`

## 执行后验证

- [ ] `git branch` 输出中不再有该特性分支（本地仅剩 main）
- [ ] `git branch -r` 输出中不再有 `origin/<branch-name>`
- [ ] `git log --oneline -5` 中可见 squash 合并提交
- [ ] 修复涉及的文件仍存在于 main 工作区

## 注意事项（来自 SKILL.md Important Notes）

- PR 到 main 始终是 squash merge，因此必须用 `-D`（强制删除），git 无法将 squash merge 识别为"已合并"
- 删除前务必先 pull 最新 main，以同步合并状态

## 真实环境中的安全边界

- `git pull origin main` 与 `git push origin --delete <branch-name>` 涉及远程仓库，需要网络与账号权限
- 若无远程权限或处于模拟环境，应停在 `git branch -D` 之前或使用本地裸仓库模拟
- `git push origin --delete` 不可逆，执行前应确认 PR 确实已合入
