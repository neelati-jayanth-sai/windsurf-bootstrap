---
description: One-time setup that analyzes this repository and generates a tailored Windsurf configuration (validate.sh, rules, skills, workflows, hooks) into the repo's .windsurf/ directory. Run once, then remove the bootstrap folder.
---

# /setup-windsurf

Bootstraps Windsurf for the current repository. The logic lives in the
**`windsurf-bootstrap` skill**; this workflow drives it. Follow in order and pause where
indicated.

## 1. Preflight & reconcile
1. Confirm you are at the Git repository root.
2. Run the skill's **Phase 0** — detect existing `AGENTS.md`, `.windsurfrules`, and any
   `.windsurf/` config, and decide how to integrate rather than duplicate. Report what
   you found.
3. Confirm the repo is committed/safe, since this writes new files.

## 2. Analyze
Run the skill's **Phase 1**: detect structure, stack, frameworks, conventions, the
canonical commands (install / dev / build / lint / typecheck / test), and the testing
approach — all from evidence.

**Pause.** Present findings, highlight the detected commands, and ask about any
ambiguity. Get confirmation before generating.

## 3. Generate
Run the skill's **Phase 2**, writing into `<repo-root>/.windsurf/`:
- `validate.sh` (the gate; `chmod +x`) — **generated first**, since hooks and workflows call it.
- `rules/` — `project-brain.md` (or minimized if AGENTS.md owns the brain),
  `architecture.md`, `coding-standards.md`, any `lang-*.md`.
- `skills/` — feature-implementation, debugging, testing, code-review,
  windsurf-config-maintenance.
- `workflows/` — implement, debug, test, review, sync-windsurf.
- `hooks.json` — a `post_cascade_response` hook running `validate.sh fast` (merged, not overwritten).

Respect format and character-limit rules; replace placeholders; strip generator comments.

## 4. Record & hand off
Run the skill's **Phase 3**: write `BOOTSTRAP_MANIFEST.md`, summarize, and surface any
`TODO:`s (especially commands to verify).

## 5. Cleanup
Tell me to reload Windsurf, then that I can delete the `windsurf-bootstrap/` folder — the
repo-root `.windsurf/` config is self-contained, and `/sync-windsurf` keeps it current
afterward. (To revert instead, run `/teardown-windsurf` before deleting.)
