# 发布检查清单 — v1.2.1

分支: `fix/release-1.2.1` → 目标: `main`

## 一、提交结构检查

- [x] 工作区干净 (`git status` 无未提交变更)
- [x] 共 5 个原子提交，满足最小提交数 ceil(8/3)=3
- [x] 每个提交 ≤2 文件，测试与实现同提交
- [x] 每个提交可独立回滚 (`git revert` 验证通过)
- [x] 提交信息遵循仓库 PLAIN 英文风格（与历史一致）

### 提交列表

| # | 提交 | 文件 | 说明 |
|---|------|------|------|
| 1 | `6b1aa5b` | src/formatter.py, tests/test_formatter.py | 新增 formatter 模块及测试 |
| 2 | `6da32e0` | src/calculator.py, tests/test_calculator.py | 修复除零异常类型 |
| 3 | `67d35fc` | src/validator.py, tests/test_validator.py | 修复邮箱正则 |
| 4 | `613b733` | config/settings.py | 修正默认超时 300→30 |
| 5 | `4315a8a` | README.md | 更新 1.2.1 发布说明 |

## 二、约束合规检查

- [x] 未新增非必要依赖（requirements.txt 未变更）
- [x] 未修改无关文件（仅 8 个与修复直接相关的文件）
- [x] 验证命令可在本地重复执行（`bash verify_release.sh`）
- [x] 不依赖外部账号或服务

## 三、功能验证

- [x] `divide(10, 0)` 抛出 `ValueError("Cannot divide by zero")`（原为 ZeroDivisionError）
- [x] `validate_email("user+tag@example.com")` 返回 True（原为 False）
- [x] `validate_email("user@mail.example.com")` 返回 True（原为 False）
- [x] `DEFAULT_TIMEOUT` 为 30（原为 300）
- [x] 新增 `format_date()` 和 `truncate()` 功能正常
- [x] 全部 15 个测试通过（原 7 个 + 新增 8 个）

## 四、发布前待执行步骤（需人工确认）

> 以下步骤涉及推送/合并，按约束仅列出命令，不自动执行。

```bash
# 1. 推送分支到远程（需要远程仓库和账号权限）
git push -u origin fix/release-1.2.1

# 2. 创建 Pull Request: fix/release-1.2.1 → main
#    在代码托管平台（GitHub/GitLab 等）Web 界面操作

# 3. PR 评审通过后合并

# 4. 合并后打标签
git checkout main
git pull
git tag -a v1.2.1 -m "Release 1.2.1: fix divide-by-zero, email regex, timeout; add formatter"
git push origin v1.2.1
```

## 五、回滚方案

如需回滚单个修复，可独立执行：
```bash
git revert <commit-hash>   # 每个提交可独立回滚，不影响其他修复
```

如需整体回滚：
```bash
git revert -m 1 <merge-commit-hash>   # 回滚整个 PR 合并
```
