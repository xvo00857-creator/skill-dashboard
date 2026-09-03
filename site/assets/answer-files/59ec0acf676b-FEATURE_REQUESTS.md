# Feature Requests

开发过程中捕获的用户所需但尚缺失的能力。

**区域（Areas）**: frontend | backend | infra | tests | docs | config
**状态（Statuses）**: pending | in_progress | resolved | wont_fix
**复杂度（Complexity）**: simple | medium | complex

## 状态定义

| 状态 | 含义 |
|------|------|
| `pending` | 尚未处理 |
| `in_progress` | 正在开发 |
| `resolved` | 能力已实现（添加 Resolution 块） |
| `wont_fix` | 决定不实现（原因写入 Resolution） |

条目格式见 self-improvement 技能的"Feature Request Entry"章节。ID 使用 `FEAT-YYYYMMDD-XXX`。

> 以下条目为 Skill 自带示例种子数据（来源：references/examples.md），用于演示格式与验证查询。

---

## [FEAT-20250115-001] export_to_csv

**Logged**: 2025-01-15T16:45:00Z
**Priority**: medium
**Status**: pending
**Area**: backend

### Requested Capability
将分析结果导出为 CSV 格式

### User Context
用户每周运行报告，需要将结果分享给使用 Excel 的非技术干系人。目前只能手动复制输出。

### Complexity Estimate
simple

### Suggested Implementation
为 analyze 命令添加 `--output csv` 标志。使用标准 csv 模块。可扩展已有的 `--output json` 模式。

### Metadata
- Frequency: recurring
- Related Features: analyze command, json output

---

## [FEAT-20250110-002] dark_mode

**Logged**: 2025-01-10T14:00:00Z
**Priority**: low
**Status**: resolved
**Area**: frontend

### Requested Capability
仪表盘支持深色模式

### User Context
用户工作到很晚，觉得明亮的界面刺眼。其他几位用户也非正式地提到过。

### Complexity Estimate
medium

### Suggested Implementation
使用 CSS 变量管理颜色。在用户设置中添加切换开关。考虑系统偏好检测。

### Metadata
- Frequency: recurring
- Related Features: user settings, theme system

### Resolution
- **Resolved**: 2025-01-18T16:00:00Z
- **Commit/PR**: #142
- **Notes**: 已实现系统偏好检测与手动切换

---
