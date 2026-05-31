---
name: windsurf-config-maintenance
description: Use when this repo's Windsurf config may be stale — after dependency changes, new or moved modules, a stack/tooling change, or when project-brain/architecture/standards rules no longer match the code. Drives /sync-windsurf.
---

<!-- GENERATOR: Save to .windsurf/skills/windsurf-config-maintenance/SKILL.md. This is the
     maintenance counterpart to the (disposable) bootstrap skill, so the project can keep
     its own config current after the bootstrap folder is gone. -->

# Keeping {{PROJECT_NAME}}'s Windsurf config current

The config in `.windsurf/` is a snapshot; code drifts away from it. This refreshes it.

## How to sync
1. Read `.windsurf/BOOTSTRAP_MANIFEST.md` for the recorded stack and commands (baseline).
2. Re-inspect the live repo: directory layout, manifests/dependencies, lint/test config,
   and the canonical commands. Note every difference from the baseline.
3. **Update only what drifted:**
   - `rules/project-brain.md` — layout and commands.
   - `rules/architecture.md` — new/removed/renamed modules and boundaries.
   - `rules/coding-standards.md` and `lang-*` — changed tooling/conventions.
   - `validate.sh` — if lint/typecheck/test commands changed.
   - new language present → propose a new `lang-*.md` glob rule.
4. Respect the char limits (always-on rules ≤ ~3,500). Show a diff and confirm before
   writing.
5. Leave skills/workflows alone unless their referenced commands or conventions changed.
6. Update `BOOTSTRAP_MANIFEST.md` (note it as a sync, with the date).

Flag, don't silently fix, anything ambiguous. Never invent commands — mark `TODO:`.
