# 查询示例（QUERIES）

本文件提供 `.learnings/` 工作台的常用检索命令。所有命令均在项目根目录执行，
基于 grep 文本检索，无需额外依赖。

- 三个核心记录文件：`LEARNINGS.md`、`ERRORS.md`、`FEATURE_REQUESTS.md`
- 统计类命令只搜索这三个文件（用 `CORE` 变量指代），避免匹配到本说明文档中的示例文字
- 全文搜索类命令搜索整个 `.learnings/` 目录

> 提示：以下命令均已在当前种子数据上验证可执行。

```bash
# 定义核心文件变量（统计命令使用）
CORE=".learnings/LEARNINGS.md .learnings/ERRORS.md .learnings/FEATURE_REQUESTS.md"
```

---

## 一、状态统计

### 1.1 统计待处理（pending）条目总数

```bash
grep -h "^\*\*Status\*\*: pending" $CORE | wc -l
```

### 1.2 列出所有待处理的高优先级条目

```bash
grep -h -B5 -E "^\*\*Priority\*\*: high" $CORE | grep "^## \["
```

### 1.3 列出所有 critical 级条目

```bash
grep -h -B5 -E "^\*\*Priority\*\*: critical" $CORE | grep "^## \["
```

### 1.4 按状态分组统计

```bash
echo "=== pending ===" && grep -h "^\*\*Status\*\*: pending" $CORE | wc -l
echo "=== in_progress ===" && grep -h "^\*\*Status\*\*: in_progress" $CORE | wc -l
echo "=== resolved ===" && grep -h "^\*\*Status\*\*: resolved" $CORE | wc -l
echo "=== wont_fix ===" && grep -h "^\*\*Status\*\*: wont_fix" $CORE | wc -l
echo "=== promoted ===" && grep -h "^\*\*Status\*\*: promoted$" $CORE | wc -l
echo "=== promoted_to_skill ===" && grep -h "^\*\*Status\*\*: promoted_to_skill" $CORE | wc -l
```

---

## 二、按区域查询

### 2.1 查找包含指定区域条目的文件

```bash
# backend 区域
grep -l "^\*\*Area\*\*: backend" $CORE

# infra 区域
grep -l "^\*\*Area\*\*: infra" $CORE
```

### 2.2 列出某区域下所有条目标题

```bash
grep -h -B10 "^\*\*Area\*\*: backend" $CORE | grep "^## \["
```

---

## 三、按类型查询

### 3.1 列出所有学习条目

```bash
grep "^## \[LRN-" .learnings/LEARNINGS.md
```

### 3.2 列出所有错误条目

```bash
grep "^## \[ERR-" .learnings/ERRORS.md
```

### 3.3 列出所有功能请求条目

```bash
grep "^## \[FEAT-" .learnings/FEATURE_REQUESTS.md
```

### 3.4 按学习分类筛选

```bash
# 用户修正
grep "^## \[LRN-.*correction" .learnings/LEARNINGS.md

# 知识缺口
grep "^## \[LRN-.*knowledge_gap" .learnings/LEARNINGS.md

# 最佳实践
grep "^## \[LRN-.*best_practice" .learnings/LEARNINGS.md
```

---

## 四、关键词检索

### 4.1 跨文件全文搜索关键词

```bash
grep -rn "docker" .learnings/
```

### 4.2 按标签（Tags）检索

```bash
grep -rn "Tags:.*api" .learnings/
```

### 4.3 按关联文件检索

```bash
grep -rn "Related Files:.*Dockerfile" .learnings/
```

### 4.4 按来源检索

```bash
# 来自用户反馈的学习
grep -rn "Source: user_feedback" .learnings/

# 来自错误的学习
grep -rn "Source: error" .learnings/
```

---

## 五、关联与复发检测

### 5.1 查找存在关联（See Also）的条目

```bash
grep -rn "See Also:" $CORE
```

### 5.2 查找已提升为技能的条目

```bash
grep -rn "^\*\*Status\*\*: promoted_to_skill" $CORE
```

### 5.3 查找已提升到项目记忆的条目

```bash
grep -rn "^\*\*Promoted\*\*:" $CORE
```

### 5.4 按 Pattern-Key 查找复发模式（simplify-and-harden 来源）

```bash
grep -rn "Pattern-Key:" $CORE
```

### 5.5 查找可复现的错误

```bash
grep -rn "Reproducible: yes" .learnings/ERRORS.md
```

---

## 六、按日期查询

### 6.1 查找指定日期的条目

```bash
grep "^## \[.*20250115" $CORE
```

### 6.2 查找指定日期范围内的条目（如 1月15日至1月20日）

```bash
grep -E "^## \[.*2025011[5-9]|^## \[.*20250120" $CORE
```

### 6.3 按记录时间（Logged）检索

```bash
grep -rn "^\*\*Logged\*\*: 2025-01-15" $CORE
```

---

## 七、维护检查

### 7.1 检查是否有条目缺少 ID（格式校验）

应无输出（所有 `## ` 标题均符合 ID 格式）：

```bash
grep -n "^## \[" $CORE | grep -vE "\[(LRN|ERR|FEAT)-[0-9]{8}-[A-Z0-9]{3}\]"
```

### 7.2 检查每个核心文件的状态字段数量

```bash
grep -c "^\*\*Status\*\*:" $CORE
```

### 7.3 列出所有已解决但缺少 Resolution 块的条目

应无输出（所有 resolved 条目均有 Resolution 块）：

```bash
for f in $CORE; do
  awk '/^## \[/{id=$0; has_res=0; has_status=0}
       /^\*\*Status\*\*: resolved/{has_status=1}
       /### Resolution/{has_res=1}
       /^---$/{if(has_status && !has_res) print FILENAME": "id; has_res=0; has_status=0}' "$f"
done
```

### 7.4 快速总览：每个文件各有多少条目

```bash
echo "Learnings:" $(grep -c "^## \[LRN-" .learnings/LEARNINGS.md)
echo "Errors:" $(grep -c "^## \[ERR-" .learnings/ERRORS.md)
echo "Feature Requests:" $(grep -c "^## \[FEAT-" .learnings/FEATURE_REQUESTS.md)
```

---

## 八、组合查询示例

### 8.1 查找 backend 区域所有 pending 的高优先级条目

```bash
awk '/^## \[/{title=$0; p=0; s=0; a=0}
     /^\*\*Priority\*\*: high/{p=1}
     /^\*\*Status\*\*: pending/{s=1}
     /^\*\*Area\*\*: backend/{a=1}
     /^---$/{if(p && s && a) print title; p=0; s=0; a=0}' $CORE
```

### 8.2 查找所有涉及 Docker 的条目并显示文件名

```bash
grep -rn -E "docker|Docker" .learnings/ --include="*.md"
```

### 8.3 查找重复出现（有 See Also）且优先级为 high/critical 的错误

```bash
awk '/^## \[/{title=$0; pri=""; see=0}
     /^\*\*Priority\*\*:/{pri=$0}
     /See Also:/{see=1}
     /^---$/{if(see && (pri ~ /high/ || pri ~ /critical/)) print title; see=0}' .learnings/ERRORS.md
```
