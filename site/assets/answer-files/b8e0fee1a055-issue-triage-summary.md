---
emoji: 🏷️
description: 自动分拣新提交的 GitHub Issue：分类打标签、生成摘要评论、检测疑似重复
on:
  issues:
    types: [opened]
  workflow_dispatch:
  skip-bots: [dependabot, renovate]
permissions:
  contents: read
  issues: read
tools:
  github:
    mode: gh-proxy
    toolsets: [default]
  bash: [mkdir, gh, jq, cat]
steps:
  - name: 预取 Issue 与仓库标签数据
    run: |
      set -euo pipefail
      mkdir -p /tmp/gh-aw/data
      gh issue view "$ISSUE_NUMBER" --repo "$GITHUB_REPOSITORY" \
        --json number,title,body,labels,author,createdAt,milestone \
        > /tmp/gh-aw/data/issue.json
      gh label list --repo "$GITHUB_REPOSITORY" --json name,description \
        > /tmp/gh-aw/data/labels.json
      ISSUE_TITLE=$(jq -r '.title' /tmp/gh-aw/data/issue.json)
      gh search issues --repo "$GITHUB_REPOSITORY" --state open --limit 10 \
        --json number,title,labels "$ISSUE_TITLE" \
        > /tmp/gh-aw/data/similar.json 2>/dev/null || echo '[]' > /tmp/gh-aw/data/similar.json
    env:
      ISSUE_NUMBER: ${{ github.event.issue.number }}
safe-outputs:
  mentions: false
  max-bot-mentions: 0
  add-labels:
    allowed: [bug, enhancement, documentation, question, duplicate, invalid, "good first issue", "help wanted"]
    max: 3
  add-comment:
    max: 1
network:
  allowed:
    - defaults
---

# Issue 自动分拣与摘要

## Task

对新打开的 Issue 进行自动分拣。读取 `/tmp/gh-aw/data/` 下的预取数据，完成分类、摘要和疑似重复检测。

1. 读取以下文件，不要重新发起广泛的在线查询：
   - `/tmp/gh-aw/data/issue.json` — 当前 Issue 详情
   - `/tmp/gh-aw/data/labels.json` — 仓库已有标签及说明
   - `/tmp/gh-aw/data/similar.json` — 标题相似的开放 Issue
2. 从 `labels.json` 与 `add-labels.allowed` 的交集中选择最多 3 个最贴切的标签。
3. 检查 `similar.json`：若存在标题和内容高度重合的开放 Issue，在摘要中以 `#编号` 标注疑似重复。
4. 生成一段简洁的中文摘要（100–200 字），使用 GitHub 风格 Markdown，包含：
   - 问题概述
   - 分类理由
   - 建议优先级（高 / 中 / 低）及依据
   - 后续行动建议
5. 通过 `add_comment` 发布摘要评论，通过 `add_labels` 添加标签。

## 规则

- 只使用仓库中已存在且在 `allowed` 列表中的标签；不要创建新标签，不要建议列表外的标签。
- 摘要中不要 `@` 提及任何人；不要使用 `fixes` / `closes` 等关闭关键字。
- 标题层级从 `###` 开始；不要使用 `#` 或 `##`。
- 如果 Issue 已有分类标签（检查 `issue.json` 的 `labels` 字段非空），调用 `noop("issue 已有标签，跳过自动分拣")`。
- 如果 Issue 内容为空、仅为测试内容、或信息严重不足无法分类，调用 `noop` 并说明原因，不添加标签也不评论。

## Safe Outputs

- 使用 `add-labels` 添加分类标签。
- 使用 `add-comment` 发布摘要评论。
- 无需任何可见操作时调用 `noop` 并附简短原因。
