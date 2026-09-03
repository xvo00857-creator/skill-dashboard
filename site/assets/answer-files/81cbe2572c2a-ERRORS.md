# Errors

开发过程中捕获的命令失败、API 错误与异常行为。

**区域（Areas）**: frontend | backend | infra | tests | docs | config
**状态（Statuses）**: pending | in_progress | resolved | wont_fix | promoted | promoted_to_skill

## 状态定义

| 状态 | 含义 |
|------|------|
| `pending` | 尚未处理 |
| `in_progress` | 正在处理 |
| `resolved` | 问题已修复（添加 Resolution 块） |
| `wont_fix` | 决定不处理（原因写入 Resolution） |
| `promoted` | 已提升至 CLAUDE.md、AGENTS.md 或 copilot-instructions.md |
| `promoted_to_skill` | 已提取为可复用技能 |

条目格式见 self-improvement 技能的"Error Entry"章节。ID 使用 `ERR-YYYYMMDD-XXX`。

> 以下条目为 Skill 自带示例种子数据（来源：references/examples.md），用于演示格式与验证查询。

---

## [ERR-20250115-A3F] docker_build

**Logged**: 2025-01-15T09:15:00Z
**Priority**: high
**Status**: pending
**Area**: infra

### Summary
Docker 构建在 M1 Mac 上因平台不匹配而失败

### Error
```
error: failed to solve: python:3.11-slim: no match for platform linux/arm64
```

### Context
- Command: `docker build -t myapp .`
- Dockerfile 使用 `FROM python:3.11-slim`
- 运行于 Apple Silicon (M1/M2)

### Suggested Fix
添加平台标志：`docker build --platform linux/amd64 -t myapp .`
或更新 Dockerfile：`FROM --platform=linux/amd64 python:3.11-slim`

### Metadata
- Reproducible: yes
- Related Files: Dockerfile

---

## [ERR-20250120-B2C] api_timeout

**Logged**: 2025-01-20T11:30:00Z
**Priority**: critical
**Status**: pending
**Area**: backend

### Summary
第三方支付 API 在结账时超时

### Error
```
TimeoutError: Request to payments.example.com timed out after 30000ms
```

### Context
- Command: POST /api/checkout
- 超时设置为 30s
- 发生在高峰时段（午餐、晚间）

### Suggested Fix
实现带指数退避的重试。考虑熔断器模式。

### Metadata
- Reproducible: yes（高峰时段）
- Related Files: src/services/payment.ts
- See Also: ERR-20250115-X1Y, ERR-20250118-Z3W

---
