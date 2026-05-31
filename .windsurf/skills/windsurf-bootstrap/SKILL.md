---
name: windsurf-bootstrap
description: Use when bootstrapping or (re)configuring Windsurf/Cascade for a repository — analyzing the codebase, detecting its stack, dependencies, and conventions, then generating project-specific rules, skills, workflows, and hooks into the repo's own .windsurf/ directory. Invoked by the /setup-windsurf workflow.
---

# Windsurf Bootstrap

You are configuring Windsurf for **this specific repository**. Inspect the codebase and
emit a tailored `.windsurf/` configuration at the **repository root** — not a generic
template.

## Critical orientation

- **Format source of truth:** the templates in `./templates/` (relative to this
  SKILL.md). Copy their frontmatter exactly. Windsurf silently ignores files with wrong
  frontmatter, so do not improvise field names.
- **Generated files go to the repo root** `.windsurf/`, i.e. `<repo-root>/.windsurf/...`.
  **Never** write generated config inside the bootstrap folder. The bootstrap folder is
  disposable; the repo-root config is the deliverable.
- **Reconcile, don't clobber.** Before writing, detect what already exists and integrate
  with it (see Phase 0). Show diffs and confirm before overwriting anything.
- **Hard limits (enforced by Windsurf):** each rule file ≤ 12,000 chars; each workflow
  file ≤ 12,000 chars; the global rules file ≤ 6,000 chars. Keep always-on rules lean —
  push depth into model-decision rules and skills, which load on demand.

## Phase 0 — Reconcile with existing config

Check for and integrate, rather than duplicate:

- **`AGENTS.md`** (root or per-package): Windsurf reads these always-on. If present and
  maintained, treat it as the team's canonical brain — keep your generated
  `project-brain.md` minimal (or skip it) and point to AGENTS.md, so you don't double-
  spend the always-on budget or create two competing sources of truth.
- **`.windsurfrules`** (legacy single file): fold its still-true content into the new
  `.windsurf/rules/` files; don't leave contradictory copies.
- **Existing `.windsurf/` rules/skills/workflows/hooks:** diff and ask per file. Merge
  `hooks.json`; never overwrite it wholesale.

## Phase 1 — Analyze the repository

Work from evidence, never assumptions:

1. **Structure** — top-level dirs and their roles; monorepo layout (pnpm/yarn/Nx/Turbo,
   Cargo/Go/Maven/Gradle multi-module).
2. **Stack & versions** — from manifests: `package.json`, `pyproject.toml`/
   `requirements.txt`, `go.mod`, `Cargo.toml`, `pom.xml`/`build.gradle`, `Gemfile`,
   `composer.json`, `*.csproj`. Record pinned versions.
3. **Frameworks & key deps** — web framework, data layer/ORM, test framework, build tool,
   lint/format tooling.
4. **Conventions** — read real config (`.eslintrc*`, `.prettierrc*`, `ruff.toml`,
   `.rubocop.yml`, `rustfmt.toml`, `.editorconfig`, `tsconfig` strictness) AND 3–5
   representative source files. Describe what the code *actually* does.
5. **Commands** — the real invocations for install / dev / build / lint / typecheck /
   test (unit + e2e). Sources: `package.json` scripts, `Makefile`, `Taskfile.yml`,
   `justfile`, `pyproject [tool.*]`, `.github/workflows/*`. **These drive validate.sh,
   the hooks, and the workflows — get them exactly right.** If you can't find one, leave
   a `TODO:` rather than inventing it.
6. **Testing approach** — location, naming, runner, focused-run command, fixtures/mocks,
   coverage expectations.

Summarize findings and pause for confirmation before generating. Ask one targeted
question per genuine ambiguity (e.g. two plausible test commands).

## Phase 2 — Generate configuration

Generate into `<repo-root>/.windsurf/`. Use templates as scaffolds; replace every
`{{PLACEHOLDER}}` and delete every `<!-- GENERATOR: ... -->` comment. Be concise and
specific — vague rules get ignored by Cascade.

### a) The quality gate — `.windsurf/validate.sh`  (do this first)

Generate `validate.sh` from `templates/validate.sh`, filling in the detected commands.
This is the **single source of truth** for the gate; hooks and workflows call it instead
of repeating commands. It is git-aware (skips when the working tree is unchanged) and
takes a mode: `fast` (lint + typecheck) or `full` (+ tests). Make it executable
(`chmod +x`). Drop any step the project lacks.

### b) Rules — `.windsurf/rules/`

| File | Trigger | Purpose | Budget |
|------|---------|---------|--------|
| `project-brain.md` | `always_on` | Tight repo overview + canonical commands. Skip/minimize if a maintained AGENTS.md exists. | ≤ ~3,500 chars |
| `architecture.md` | `model_decision` | Deeper architecture, loaded on demand. | ≤ 12,000 |
| `coding-standards.md` | `always_on` | Core standards actually followed here. | ≤ 3,500 |
| `lang-<x>.md` | `glob` | File-type-specific rules; one per language/area as needed. | ≤ 12,000 |

### c) Skills — `.windsurf/skills/<name>/SKILL.md`  (model-decided; description must match)

- `feature-implementation/` — where code/types/tests go, conventions, ends by running
  `validate.sh full`. Include a short "behavior-preserving refactor" note (lock behavior
  with tests before changing it).
- `debugging/` — reproduce → isolate → fix root cause → add regression test.
- `testing/` — runner, placement, naming, fixtures/mocks, focused runs.
- `code-review/` — what to check before commit (correctness, conventions, tests, security,
  the validate gate); drives `/review`.
- `windsurf-config-maintenance/` — how to keep this config current; drives
  `/sync-windsurf`. **This persists after the bootstrap folder is deleted**, so the repo
  can refresh its own brain.

### d) Workflows — `.windsurf/workflows/`  (manual-only, `/[name]`, may call each other)

- `implement.md` → `/implement` — defers to feature-implementation; ends with the gate.
- `debug.md` → `/debug` — defers to debugging.
- `test.md` → `/test` — defers to testing; runs `validate.sh full`.
- `review.md` → `/review` — defers to code-review; for pre-commit/PR checks.
- `sync-windsurf.md` → `/sync-windsurf` — refreshes the brain/rules against the live repo.

### e) Hooks — `.windsurf/hooks.json`

Hooks fire on Cascade lifecycle events, **not** on file save. Generate one
`post_cascade_response` hook that calls `bash .windsurf/validate.sh fast` with
`"show_output": true`. The `fast` mode + git-skip keeps it quiet on non-editing turns.
Tests stay out of the per-response hook (run via `/test` or a pre-commit git hook) to
avoid latency. **Merge** into any existing `hooks.json`. Document disable/silence inside
the file.

## Phase 3 — Record & hand off

1. Write `<repo-root>/.windsurf/BOOTSTRAP_MANIFEST.md` (from `templates/MANIFEST.md`):
   every file created/edited, the detected stack, the gate commands, and any `TODO:`s.
   This makes the config auditable, the bootstrap folder safe to delete, and gives
   `/sync-windsurf` a baseline to diff against.
2. Summarize what was generated; call out detected commands to verify and any `TODO:`s.
3. Tell the user to reload Windsurf, then remove the `windsurf-bootstrap/` folder (or run
   `/teardown-windsurf` first if they want to undo the generated config instead).

## Guardrails

- Prefer fewer, sharper files over many vague ones.
- Every claim in a rule must be true of *this* repo — verify or omit.
- Never write secrets, tokens, or absolute machine paths into generated files.
- Leave explicit `TODO:` markers for anything undetermined; never guess.
