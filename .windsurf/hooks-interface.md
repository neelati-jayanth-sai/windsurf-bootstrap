# Hooks — Enforcement Layer (Windows-safe)

Hooks turn the system's "shoulds" into enforced "musts". Instead of prose telling
Cascade to test/research/commit (which it can skip), hooks run real commands that
**block** the workflow when policy isn't met.

Everything is Python — no bash, no heredocs, no `/tmp`. Works on Windows.

## How Cascade calls hooks

```
python .windsurf/wsdb.py run-hook <event> --step <id> [--library NAME] [--old-entity NAME]
```

The runner reads `.windsurf/hooks/hooks.json`, evaluates each entry's `when`
condition, substitutes `{tokens}`, runs the command, and acts on `on_fail`.

Exit code 2 means a `block` hook fired — Cascade must stop and fix the cause.

## Passing data to writes (the Windows-safe rule)

Never inline JSON in a shell command. Cascade writes a JSON file with its own
file-creation tool, then passes the path:

```
python .windsurf/wsdb.py step-add --file payload.json
```

This avoids every shell-quoting and heredoc problem across cmd/powershell/bash.

## Hook events

| Event | Fires when | Default policy |
|---|---|---|
| `on_session_start` | start of a workflow | preflight (git clean + mapped + no zombie change) → **block** |
| `before_implement` | before editing code for a step | blast radius confirmed → **block**; research exists if DEPENDENCY → **block** |
| `on_step_complete` | after implementing a step | run layer test command → **escalate** on fail |
| `on_gate_pass` | after tests pass | `git add -A` + commit → warn |
| `before_change_complete` | before marking change done | no old-entity refs remain → **block** |

## on_fail modes

- `block` — print result, exit 2. Cascade cannot proceed.
- `escalate` — signal the escalation flow (see below). Does not exit non-zero.
- `warn` — log and continue.

## Conditions (`when`)

- `always` — always run
- `change_type==DEPENDENCY` — only for that change type (any type works)
- `has_old_entity` — only if `--old-entity` was passed
- `has_library` — only if `--library` was passed

Conditions prevent deadlock: the research gate only fires on dependency changes,
so a pure schema change never blocks waiting for research that doesn't apply.

## Template tokens (substituted at run time)

`{PY}` (the python interpreter), `{step_id}`, `{step_label}`, `{layer_name}`,
`{layer_role}`, `{change_id}`, `{change_type}`, `{library}`, `{old_entity}`,
`{layer_test_command}` (resolved from `layer_test_commands[layer_role]`).

## The escalation flow (3 strikes → research)

This is the loop that fixes "it didn't test and didn't fix properly":

```
implement step
  → run-hook on_step_complete   (runs the layer test command)
       PASS → run-hook on_gate_pass (commit) → next step
       FAIL → wsdb step-fail <id> --error "<test output>"
              wsdb check-escalate <id>
                  fail_count < 3 → "diagnose, minimum fix, retry"
                  fail_count >=3 → status=escalated, returns the exact last_error
                                   → run research-first-coder scoped to that error
                                   → write findings, regenerate the step prompt
                                   → retry once
                                   → still failing → stays escalated, surfaces to you
```

`next` always surfaces escalated and failed steps FIRST, so you can never silently
build on a broken step.

Tune the threshold in hooks.json:
```json
"escalation": { "fail_threshold": 3, "max_retries_after_research": 1 }
```

## Customizing test commands

Edit `layer_test_commands` in hooks.json to match your project. The runner picks
the command by the step's `layer_role`:

```json
"layer_test_commands": {
  "API": "pytest tests/integration -x --tb=short",
  "FRONTEND": "npm test -- --watchAll=false"
}
```

If a role isn't listed, the top-level `test_command` is used.

## Notes

- `state.db`, `state.db-wal`, `state.db-shm` are auto-gitignored by `init` so the
  DB never dirties your tree or blocks preflight.
- Hooks run with `shell=True` and a 600s timeout. Long test suites: raise it in code.
- To disable a hook temporarily, set its `when` to a condition that won't match,
  or remove the entry from hooks.json.
