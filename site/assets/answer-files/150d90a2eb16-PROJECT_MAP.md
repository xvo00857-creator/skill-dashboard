# Project Map - [Project Name]

> **Level 2 context**: Hierarchical summary of the codebase.
> Load ONLY the relevant section when working in a specific area.
> This prevents context flooding (loading 5000+ irrelevant lines).

## How to Use

1. Find the area you are working on below
2. Read that section only (do not read the whole file)
3. Follow the pattern pointers to find example code
4. When you add a new area, append a section here

---

## [Area 1 Name] ([path/to/dir/])

**What it does**: [one-sentence description]

**Key files**:
- [file1.ts] - [role]
- [file2.ts] - [role]
- [file3.ts] - [role]

**Patterns in this area**:
- [e.g., All routes use authMiddleware; errors use AreaError class]
- [e.g., Database access goes through the repository layer, not direct Prisma calls]

**Gotchas**:
- [e.g., The socket handler must be registered after auth middleware or connections are unauthenticated]

---

## [Area 2 Name] ([path/to/dir/])

**What it does**: [one-sentence description]

**Key files**:
- [file1.ts] - [role]
- [file2.ts] - [role]

**Patterns in this area**:
- [e.g., Optimistic updates via WebSocket with server reconciliation]

**Gotchas**:
- [e.g., Do not mutate task objects directly; use the store actions]

---

## Shared ([path/to/lib/])

**What it does**: Cross-cutting utilities used by all areas.

**Key files**:
- validation.ts - Zod schemas and validation helpers
- errors.ts - Custom error classes (ValidationError, AuthError, NotFoundError)
- db.ts - Prisma client singleton
- logger.ts - Structured logging

**Patterns**:
- All errors thrown should extend AppError (see errors.ts)
- All validation uses Zod schemas defined in validation.ts
- Database access: import the singleton from db.ts, do not create new PrismaClient

---

## File Naming Conventions

| Type | Pattern | Example |
|------|---------|---------|
| Components | PascalCase.tsx | UserProfile.tsx |
| Hooks | camelCase.ts | useAuth.ts |
| Utilities | camelCase.ts | formatDate.ts |
| Types | camelCase.types.ts | user.types.ts |
| Tests | [source].test.ts | UserProfile.test.tsx |
| Config | kebab-case.config.ts | vite.config.ts |
