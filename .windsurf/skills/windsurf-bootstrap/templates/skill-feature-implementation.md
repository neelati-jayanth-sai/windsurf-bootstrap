---
name: feature-implementation
description: Use when implementing a new feature or non-trivial change in {{PROJECT_NAME}} — deciding where code, types, and tests go, following project conventions, and validating before done.
---

<!-- GENERATOR: Save to .windsurf/skills/feature-implementation/SKILL.md. Tailor every
     step to the detected stack and commands. Strip GENERATOR comments. -->

# Implementing a feature in {{PROJECT_NAME}}

## Before writing code
1. Locate the relevant module(s) using the layout in `project-brain.md`.
2. Read 1–2 sibling implementations to match local patterns.
3. Confirm where new code, types, and tests belong: {{PLACEMENT_RULES}}.

## Implement
- Follow `coding-standards.md` and any matching `lang-*` rule.
- {{STACK_SPECIFIC_STEP e.g. register the route / export from index / add migration}}.
- Add or update types: {{TYPE_GUIDANCE}}.
- Add tests alongside: {{TEST_PLACEMENT_AND_STYLE}}.

## Behavior-preserving refactors
If the change is a refactor rather than new behavior: ensure the affected code is covered
by tests *first* (add characterization tests if not), keep each step small, and run
`bash .windsurf/validate.sh full` between steps so a green suite proves nothing broke.

## Validation gate (do not skip)
Run `bash .windsurf/validate.sh full` and fix anything that fails.

## Done means
Gate passes, tests cover the new behavior, public surfaces are typed/documented per
project norms, and no TODO/debug code is left behind.
