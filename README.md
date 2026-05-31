# Windsurf Bootstrap

A drop-in folder that teaches Windsurf to configure itself for your codebase. Run the
setup workflow once and Cascade analyzes the project — structure, stack, dependencies,
conventions — then generates the Windsurf configuration tailored to *that* repository.

After setup, this folder can be removed. The generated configuration stays in the repo,
and a generated `/sync-windsurf` workflow keeps it current as the codebase evolves.

## What gets generated

Into your repository's own `.windsurf/` directory:

- **`validate.sh`** — one quality gate (lint / typecheck / test) that every hook and
  workflow calls, so commands live in exactly one place.
- **Rules** — `project-brain.md` (always-on; minimized if the repo already has an
  `AGENTS.md`), `architecture.md` (model-decision), `coding-standards.md` (always-on),
  and optional per-language glob rules.
- **Skills** — `feature-implementation`, `debugging`, `testing`, `code-review`, and
  `windsurf-config-maintenance`; Cascade activates these automatically when a task matches.
- **Workflows** — `/implement`, `/debug`, `/test`, `/review`, `/sync-windsurf`; manual
  entry points that defer to the skills so behavior stays consistent.
- **Hooks** (`hooks.json`) — a post-response gate that runs `validate.sh fast` after
  Cascade edits.
- **A manifest** recording everything generated.

## Usage

1. Copy this `windsurf-bootstrap/` folder into the **root** of your project.
2. Open Cascade. Windsurf scans sub-directories for `.windsurf/`, so the setup workflow
   and skill register automatically — no install step. (Reload the window if they don't
   appear.)
3. Run **`/setup-windsurf`** in Cascade.
4. Review the detected stack and commands when prompted, then let it generate.
5. Reload Windsurf, then delete this folder (or run `/teardown-windsurf` first to revert).

## How it works

The folder ships its own Windsurf skill and workflows under `.windsurf/`:

```
windsurf-bootstrap/
└── .windsurf/
    ├── workflows/
    │   ├── setup-windsurf.md           # the /setup-windsurf entry point
    │   └── teardown-windsurf.md         # /teardown-windsurf to revert a run
    └── skills/
        └── windsurf-bootstrap/
            ├── SKILL.md                 # reconcile → analyze → generate → record
            └── templates/               # correctly-formatted scaffolds Cascade fills in
```

`/setup-windsurf` drives the run; the skill writes generated files to the **repo-root**
`.windsurf/` (never inside this folder).

## Design notes (Windsurf specifics this respects)

- **The gate is git-aware and quiet.** Hooks fire on Cascade lifecycle events, not on
  file save — so a naive "run tests after every response" hook fires on Q&A and planning
  turns too. Instead, the hook calls `validate.sh fast`, which **skips when the working
  tree is unchanged** and runs only lint + typecheck. Full tests run via `/test`,
  `/review`, or a pre-commit git hook — keeping the per-response hook fast.
- **One source of truth for commands.** Hooks and workflows all call `validate.sh`, so
  changing a command is a one-line edit, not a hunt across files.
- **It reconciles with what's already there.** Existing `AGENTS.md`, `.windsurfrules`, or
  `.windsurf/` config is integrated, not duplicated — avoiding two competing brains and
  double-spending the always-on context budget.
- **It doesn't go stale silently.** A `windsurf-config-maintenance` skill and
  `/sync-windsurf` workflow are generated *into the repo*, so they survive deleting this
  folder. Re-run `/sync-windsurf` after big dependency or structure changes.
- **Rules have a budget.** Each rule file is capped at 12,000 chars (global rules 6,000).
  Always-on rules are kept lean; depth goes into model-decision rules and skills that
  load on demand.
- **Workflows are manual-only.** Cascade never auto-runs a workflow — that's a skill's
  job. So generated workflows are explicit `/commands`, and the skills carry the "how."
- **Nothing is overwritten silently.** Existing config is diffed and confirmed;
  `hooks.json` is merged.

### Why these workflows (and not more)

A workflow earns its place only if you'd otherwise retype the procedure regularly.
`/implement`, `/debug`, `/test`, `/review`, and `/sync-windsurf` cover the loops that
actually repeat. Refactoring is handled as guidance inside `feature-implementation`
(lock behavior with tests, then change) rather than a separate workflow, and commit/PR
conventions are left to your team rather than imposed. Add your own with
`/sync-windsurf` or by dropping files in `.windsurf/workflows/`.

## Requirements

Windsurf 2 (Cascade) with Rules, Skills, Workflows, and Hooks support.
