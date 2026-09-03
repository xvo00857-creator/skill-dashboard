---
name: demo-skill-validator
description: 校验本地 Skill 目录的 SKILL.md 是否合规：frontmatter 必须含 name 和 description，name 须与目录名一致，description 不得为占位文本。当用户说"检查 skill"、"校验技能"、"skill 合规吗"或需要批量检查已安装 Skill 结构时触发。
---

# demo-skill-validator

校验本地 Skill 目录结构是否合规。

## 用法

对单个或多个 Skill 目录运行：

```bash
python3 scripts/validate_skill.py <skill-dir> [<skill-dir> ...]
```

## 检查项

1. `SKILL.md` 存在
2. YAML frontmatter 以 `---` 包裹
3. frontmatter 含 `name` 和 `description` 字段且非空
4. `name` 与目录名一致
5. `description` 不是占位文本（如 "A brief description..."）

退出码 0 表示全部通过，1 表示存在不合规项。
