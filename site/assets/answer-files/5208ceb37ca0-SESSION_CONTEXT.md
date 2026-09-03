# Session Context - [Project Name]

> **Level 2-5 context**: Cross-session state for this two-week development task.
> Load this file at the start of EVERY session. Update it at the END of every session.
>
> **How to use**:
> 1. At session start: read this file top to bottom. You now know where the project stands.
> 2. During work: update sections as facts emerge, decisions are made, todos shift, hypotheses are confirmed or busted.
> 3. At session end: fill in the Session Handoff section so the next session starts fast.
>
> **Legend**:
> - [FACT] Confirmed, verified, not going to change without explicit notice
> - [DECISION] A choice made (with rationale). Revisit only if circumstances change.
> - [TODO] Work remaining. Includes owner and status.
> - [HYPOTHESIS] Assumed true but NOT yet verified. Must be promoted to [FACT] or killed before relying on it.

---

## 0. Task Overview

**Goal**: [One-sentence description of what this two-week task delivers]

**Timeline**: [Start date] to [Target end date] (10 working days)

**Definition of Done**:
- [ ] [Criterion 1]
- [ ] [Criterion 2]
- [ ] [Criterion 3]

---

## 1. Confirmed Facts [FACT]

> Facts are verified ground truth. They do not change unless the underlying reality changes.
> Source each fact. If you cannot point to where it was confirmed, it is not a fact.

| ID | Fact | Source | Confirmed |
|----|------|--------|-----------|
| F-01 | [e.g., API base URL is https://api.example.com/v2] | [e.g., env config / PR #42 / user confirmation] | [date] |
| F-02 | [e.g., User table columns: id, email, created_at] | [e.g., schema.prisma / migration 001] | [date] |
| F-03 | | | |

**Promotion rule**: A [HYPOTHESIS] becomes a [FACT] only after: (a) code/tests confirm it, (b) user explicitly confirms, or (c) documentation is verified against running system.

---

## 2. Decisions [DECISION]

> Decisions are choices made from alternatives. Record the rationale so future sessions do not re-litigate.
> If a decision needs revisiting, mark it SUPERSEDED with a pointer to the new decision. Do not delete.

| ID | Decision | Alternatives Considered | Rationale | Decided By | Date |
|----|----------|------------------------|-----------|------------|------|
| D-01 | [e.g., Use Zod for validation] | Joi, Yup, manual checks | Zod has best TS inference; already in deps | [name/agent] | [date] |
| D-02 | [e.g., WebSocket for real-time, not polling] | Polling, SSE | Need bidirectional; polling wastes bandwidth | [name/agent] | [date] |
| D-03 | | | | | |

**Revisiting a decision**: If a decision turns out wrong, add a new row D-XX and mark the old one:
D-01 SUPERSEDED by D-05 on [date] - reason: [what changed]

---

## 3. To-Dos [TODO]

> Track all remaining work. One row per actionable unit.
> Status: pending | in-progress | blocked | done

| ID | Task | Owner | Status | Depends On | Notes |
|----|------|-------|--------|------------|-------|
| T-01 | [e.g., Add Zod schema for task creation] | [agent/human] | pending | - | Follow pattern in src/lib/validation.ts |
| T-02 | [e.g., Wire schema into POST /api/tasks] | [agent/human] | pending | T-01 | |
| T-03 | [e.g., Add validation error tests] | [agent/human] | pending | T-02 | |
| T-04 | | | | | |

**Blocked tasks**: When a task is blocked, note what unblocks it (often a [HYPOTHESIS] needing verification or a [DECISION] from the user).

---

## 4. Hypotheses Needing Verification [HYPOTHESIS]

> These are assumptions we operate on but have NOT confirmed.
> Each hypothesis MUST eventually be: (a) promoted to [FACT], (b) killed (assumption wrong), or (c) converted to a [DECISION].
> Do NOT build on an unverified hypothesis without flagging the risk.

| ID | Hypothesis | Risk if Wrong | How to Verify | Verified? | Outcome |
|----|-----------|---------------|---------------|-----------|---------|
| H-01 | [e.g., Prisma handles connection pooling automatically] | May need external pooler in production | Check Prisma docs; test with 10 concurrent requests | NO | - |
| H-02 | [e.g., Auth middleware works for WebSocket upgrade] | WS connections may bypass auth | Test WS with expired token | NO | - |
| H-03 | | | | | |

**Verification log**:

| Date | Hypothesis | Result |
|------|-----------|--------|
| [date] | H-01 | [e.g., CONFIRMED - promoted to F-04] |
| [date] | H-02 | [e.g., BUSTED - created T-08 for WS auth] |

---

## 5. Confusion Log

> When context conflicts or requirements are incomplete, do NOT guess. Record here and surface to user.

### Open Confusions

| ID | Confusion | Options | Recommendation | Resolved? |
|----|-----------|---------|----------------|-----------|
| C-01 | [e.g., Spec says REST but code uses GraphQL] | A) Follow spec, B) Follow code, C) Ask | C - looks intentional | NO |
| C-02 | | | | |

### Resolved Confusions

| ID | Resolution | Date |
|----|-----------|------|
| C-01 | [e.g., User chose B - use GraphQL, update spec] | [date] |

---

## 6. Session Handoff

> Fill this in at the END of each session. The next session reads this first.

### Session [N] - [Date]

**What was done this session**:
- [e.g., Completed T-01, T-02; verified H-01 (promoted to F-04)]
- [e.g., Hit confusion C-01, surfaced to user - awaiting answer]

**Current state**:
- Working on: [T-XX or description]
- Last file touched: [path]
- Tests: [passing / failing - which one]

**What the next session needs to know**:
1. [Most important thing to remember]
2. [Second most important]
3. [Any gotchas, dead ends found, things NOT to do]

**Immediate next actions**:
1. [First thing to do next session]
2. [Second thing]

---

## 7. Inline Plans

> For multi-step work within a session, emit a plan before executing.

PLAN:
1. [Step 1 - what and why]
2. [Step 2]
3. [Step 3]
-> Executing unless redirected.

### Current Plan (if mid-task)

[Paste the active plan here. Clear when done.]

### Completed Plans (for reference)

| Date | Plan | Outcome |
|------|------|---------|
| [date] | [brief description] | [e.g., All 3 steps done; tests pass] |

---

## 8. Relevant Files (Selective Include)

> Do NOT load the entire codebase. List only files relevant to current task.

### Currently Active

| File | Why It Matters | Trust Level |
|------|---------------|-------------|
| [path] | [what it contains / why we touch it] | Trusted / Verify / Untrusted |
| | | |

### Patterns to Follow

> Before implementing, find ONE existing example and follow it.

| Pattern | Example File:Lines |
|---------|-------------------|
| [e.g., Input validation] | [src/lib/validation.ts:45-60] |
| [e.g., Error response format] | [src/middleware/errorHandler.ts:10-25] |

---

## 9. Known Gotchas

> Things that will waste time if rediscovered. Keep short and current.

- [e.g., Hot reload does not pick up .env changes - restart dev server]
- [e.g., Test DB is shared; do not run tests in parallel]
- [e.g., The id field is UUID, not auto-increment - do not assume sequential IDs]
