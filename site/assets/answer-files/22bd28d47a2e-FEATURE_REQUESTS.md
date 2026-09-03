# Feature Requests

Missing capabilities requested by users, captured during development.

**Areas**: frontend | backend | infra | tests | docs | config
**Statuses**: pending | in_progress | resolved | wont_fix
**Complexity**: simple | medium | complex

> **数据来源与状态（待确认）**：本文件当前条目均来自 self-improvement Skill 自带的 `references/examples.md` 示例数据，**并非真实跨会话工作记录**。真实记录待用户提供后替换或追加。条目内容、ID、时间戳均原样保留，未作编造。

## Status Definitions

| Status | Meaning |
|--------|---------|
| `pending` | Not yet addressed |
| `in_progress` | Actively being built |
| `resolved` | Capability implemented (add Resolution block) |
| `wont_fix` | Decided not to build (reason in Resolution) |

Entry format: see the self-improvement skill's "Feature Request Entry" section. IDs use `FEAT-YYYYMMDD-XXX`.

---

## [FEAT-20250115-001] export_to_csv

**Logged**: 2025-01-15T16:45:00Z
**Priority**: medium
**Status**: pending
**Area**: backend

### Requested Capability
Export analysis results to CSV format

### User Context
User runs weekly reports and needs to share results with non-technical
stakeholders in Excel. Currently copies output manually.

### Complexity Estimate
simple

### Suggested Implementation
Add `--output csv` flag to the analyze command. Use standard csv module.
Could extend existing `--output json` pattern.

### Metadata
- Frequency: recurring
- Related Features: analyze command, json output
- Provenance: self-improvement/references/examples.md（示例数据，待确认真实性）

---

## [FEAT-20250110-002] dark_mode

**Logged**: 2025-01-10T14:00:00Z
**Priority**: low
**Status**: resolved
**Area**: frontend

### Requested Capability
Dark mode support for the dashboard

### User Context
User works late hours and finds the bright interface straining.
Several other users have mentioned this informally.

### Complexity Estimate
medium

### Suggested Implementation
Use CSS variables for colors. Add toggle in user settings.
Consider system preference detection.

### Metadata
- Frequency: recurring
- Related Features: user settings, theme system
- Provenance: self-improvement/references/examples.md（示例数据，待确认真实性）

### Resolution
- **Resolved**: 2025-01-18T16:00:00Z
- **Commit/PR**: #142
- **Notes**: Implemented with system preference detection and manual toggle

---
