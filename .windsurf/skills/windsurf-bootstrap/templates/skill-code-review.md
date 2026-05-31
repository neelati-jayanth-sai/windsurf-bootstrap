---
name: code-review
description: Use when reviewing changes in {{PROJECT_NAME}} before commit or in a PR — checking correctness, conventions, test coverage, and obvious security/perf issues.
---

<!-- GENERATOR: Save to .windsurf/skills/code-review/SKILL.md. Tailor to the stack. -->

# Reviewing changes in {{PROJECT_NAME}}

Scope the review to the diff (`git diff` / the PR), not the whole repo.

## Check, in order
1. **Correctness** — does it do what it claims? Edge cases and error paths handled?
2. **Conventions** — matches `coding-standards.md`, the relevant `lang-*` rule, and the
   patterns in neighbouring files? Naming, structure, imports.
3. **Tests** — new/changed behavior is covered; tests are meaningful, not just present.
4. **Architecture** — respects module boundaries in `architecture.md`; no leaks across
   layers; no unnecessary new dependencies.
5. **Security / safety** — no secrets committed, inputs validated, no obvious injection
   or unsafe calls for this stack.
6. **Footprint** — diff is as small as it can be; no stray debug code or dead code.

## Then
- Run `bash .windsurf/validate.sh full`.
- Report findings grouped as **blocking** vs **nits**, each with file:line and a concrete
  suggested fix. Don't rubber-stamp; if it's clean, say what you verified.
