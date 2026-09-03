# Verification Checklist

> Use this checklist to verify the context package is set up correctly and being used well.
> Based on the context engineering Skill verification criteria.

## Setup Verification

- [ ] AGENTS.md exists and covers: tech stack, commands, code conventions, and boundaries
- [ ] AGENTS.md includes a code example showing the project style
- [ ] AGENTS.md includes trust levels for loaded files
- [ ] SESSION_CONTEXT.md exists with all four tracking sections: Facts, Decisions, To-Dos, Hypotheses
- [ ] SESSION_CONTEXT.md includes a Confusion Log section
- [ ] SESSION_CONTEXT.md includes a Session Handoff section
- [ ] SESSION_CONTEXT.md includes an Inline Plans section
- [ ] PROJECT_MAP.md exists with at least one area documented
- [ ] All placeholder text ([Project Name], [e.g. ...], etc.) has been replaced with real project info

## Per-Session Verification

- [ ] At session start: AGENTS.md was read
- [ ] At session start: SESSION_CONTEXT.md was read (facts, decisions, todos, hypotheses)
- [ ] At session start: Relevant PROJECT_MAP.md section was read
- [ ] Before editing: the target file was read
- [ ] Before implementing: an existing pattern example was found in the codebase
- [ ] New facts were added with sources
- [ ] New decisions were recorded with rationale and alternatives
- [ ] New hypotheses were recorded with verification method
- [ ] Confusions were surfaced (not silently guessed)
- [ ] Multi-step work was preceded by an inline plan
- [ ] At session end: Session Handoff was filled in
- [ ] At session end: Todo statuses were updated
- [ ] At session end: Hypothesis verification results were logged

## Quality Checks (Red Flags)

Watch for these signs that context engineering is failing:

- [ ] Agent output does not match project conventions -> check AGENTS.md conventions and example
- [ ] Agent invents APIs or imports that do not exist -> check that relevant source files are being loaded
- [ ] Agent re-implements utilities that already exist -> check PROJECT_MAP.md and pattern references
- [ ] Agent quality degrades as conversation gets longer -> start fresh session, use SESSION_CONTEXT.md handoff
- [ ] Agent guesses instead of asking -> check that Confusion Log is being used
- [ ] External config/data files treated as trusted instructions -> review trust levels in AGENTS.md
- [ ] More than 2000 lines of context loaded for a single task -> use Selective Include pattern
- [ ] Hypotheses remain unverified for multiple sessions -> prioritize verification or flag risk

## Hypothesis Lifecycle Check

For each hypothesis in SESSION_CONTEXT.md:

- [ ] Has a clear verification method
- [ ] Has an assessed risk if wrong
- [ ] Is either verified (promoted to FACT), busted (new TODO created), or still open
- [ ] Open hypotheses are not blocking critical work without explicit user awareness
