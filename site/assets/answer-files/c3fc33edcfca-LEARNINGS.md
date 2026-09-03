# Learnings

Corrections, insights, and knowledge gaps captured during development.

**Categories**: correction | knowledge_gap | best_practice
**Areas**: frontend | backend | infra | tests | docs | config
**Statuses**: pending | in_progress | resolved | wont_fix | promoted | promoted_to_skill

> **数据来源与状态（待确认）**：本文件当前条目均来自 self-improvement Skill 自带的 `references/examples.md` 示例数据，**并非真实跨会话工作记录**。真实记录待用户提供后替换或追加。条目内容、ID、时间戳均原样保留，未作编造。

## Status Definitions

| Status | Meaning |
|--------|---------|
| `pending` | Not yet addressed |
| `in_progress` | Actively being worked on |
| `resolved` | Issue fixed or knowledge integrated |
| `wont_fix` | Decided not to address (reason in Resolution) |
| `promoted` | Elevated to CLAUDE.md, AGENTS.md, or copilot-instructions.md |
| `promoted_to_skill` | Extracted as a reusable skill |

## Skill Extraction Fields

When a learning is promoted to a skill, add these fields:

```markdown
**Status**: promoted_to_skill
**Skill-Path**: skills/skill-name
```

---

## [LRN-20250115-001] correction

**Logged**: 2025-01-15T10:30:00Z
**Priority**: high
**Status**: pending
**Area**: tests

### Summary
Incorrectly assumed pytest fixtures are scoped to function by default

### Details
When writing test fixtures, I assumed all fixtures were function-scoped.
User corrected that while function scope is the default, the codebase
convention uses module-scoped fixtures for database connections to
improve test performance.

### Suggested Action
When creating fixtures that involve expensive setup (DB, network),
check existing fixtures for scope patterns before defaulting to function scope.

### Metadata
- Source: user_feedback
- Related Files: tests/conftest.py
- Tags: pytest, testing, fixtures
- Provenance: self-improvement/references/examples.md（示例数据，待确认真实性）

---

## [LRN-20250115-002] knowledge_gap

**Logged**: 2025-01-15T14:22:00Z
**Priority**: medium
**Status**: resolved
**Area**: config

### Summary
Project uses pnpm not npm for package management

### Details
Attempted to run `npm install` but project uses pnpm workspaces.
Lock file is `pnpm-lock.yaml`, not `package-lock.json`.

### Suggested Action
Check for `pnpm-lock.yaml` or `pnpm-workspace.yaml` before assuming npm.
Use `pnpm install` for this project.

### Metadata
- Source: error
- Related Files: pnpm-lock.yaml, pnpm-workspace.yaml
- Tags: package-manager, pnpm, setup
- Provenance: self-improvement/references/examples.md（示例数据，待确认真实性）

### Resolution
- **Resolved**: 2025-01-15T14:30:00Z
- **Commit/PR**: N/A - knowledge update
- **Notes**: Added to CLAUDE.md for future reference

---

## [LRN-20250115-003] best_practice

**Logged**: 2025-01-15T16:00:00Z
**Priority**: high
**Status**: promoted
**Promoted**: CLAUDE.md
**Area**: backend

### Summary
API responses must include correlation ID from request headers

### Details
All API responses should echo back the X-Correlation-ID header from
the request. This is required for distributed tracing. Responses
without this header break the observability pipeline.

### Suggested Action
Always include correlation ID passthrough in API handlers.

### Metadata
- Source: user_feedback
- Related Files: src/middleware/correlation.ts
- Tags: api, observability, tracing
- Provenance: self-improvement/references/examples.md（示例数据，待确认真实性）

---

## [LRN-20250116-001] best_practice

**Logged**: 2025-01-16T09:00:00Z
**Priority**: high
**Status**: promoted
**Promoted**: AGENTS.md
**Area**: backend

### Summary
Must regenerate API client after OpenAPI spec changes

### Details
When modifying API endpoints, the TypeScript client must be regenerated.
Forgetting this causes type mismatches that only appear at runtime.
The generate script also runs validation.

### Suggested Action
Add to agent workflow: after any API changes, run `pnpm run generate:api`.

### Metadata
- Source: error
- Related Files: openapi.yaml, src/client/api.ts
- Tags: api, codegen, typescript
- Provenance: self-improvement/references/examples.md（示例数据，待确认真实性）

---

## [LRN-20250118-001] best_practice

**Logged**: 2025-01-18T11:00:00Z
**Priority**: high
**Status**: promoted_to_skill
**Skill-Path**: skills/docker-m1-fixes
**Area**: infra

### Summary
Docker build fails on Apple Silicon due to platform mismatch

### Details
When building Docker images on M1/M2 Macs, the build fails because
the base image doesn't have an ARM64 variant. This is a common issue
that affects many developers.

### Suggested Action
Add `--platform linux/amd64` to docker build command, or use
`FROM --platform=linux/amd64` in Dockerfile.

### Metadata
- Source: error
- Related Files: Dockerfile
- Tags: docker, arm64, m1, apple-silicon
- See Also: ERR-20250115-A3F, ERR-20250117-B2D
- Provenance: self-improvement/references/examples.md（示例数据，待确认真实性）

---
