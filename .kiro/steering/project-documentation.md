---
inclusion: auto
---

# Project Documentation Standards

## Project Updates

This project maintains a narrative series of project update documents at `docs/project-updates/`. These serve as the project's decision log and context handoff between sessions.

### When to Create or Update Project Docs

- **New project update** (`docs/project-updates/NN-project-update-*.md`): When a significant milestone is reached, a major decision is made, or a new phase of work begins. Each update should capture decisions, rationale, results, and next steps.
- **Update existing doc**: When execution results change the plan described in an existing update.

### Format Requirements

Every project update must include:
1. Sequential number and descriptive title
2. Date, context, and audience fields
3. Referenced Kiro Specs section
4. Prerequisite Reading section
5. Decision log with numbered decisions (continuing the global sequence)
6. Files created/modified list
7. "What the Next Agent Should Do" section

### Decision Numbering

Decisions are numbered globally across all project updates. Check the latest update for the current highest decision number before adding new ones.

### When NOT to Create a Doc

- Minor bug fixes or typo corrections
- Routine test runs without significant findings
- Code refactoring that doesn't change behavior

## Spec References

When working on a spec, always check `docs/project-updates/` for context. The updates contain decisions and rationale that may not be in the spec files themselves.
