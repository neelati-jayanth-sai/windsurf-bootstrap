---
name: init
description: >
  One-shot project bootstrap for the Windsurf skills system. Run this ONCE when setting
  up the system in a new or existing project, or when you type "/init", "initialize the
  project", "set up wsdb", "bootstrap windsurf system", or "get this project ready".
  It creates the state DB, hooks config, and gitignore; verifies git; runs codebase
  orientation to map the project layers; and reports readiness. After this runs, every
  other skill and workflow has what it needs (a populated codebase_map, a clean DB, and
  enforced hooks). Safe to re-run — it detects what already exists and only fills gaps.
---

# init — Project Bootstrap

Gets a project fully ready for the skills system in one pass. Run once per project.
Idempotent: re-running detects existing state and only fills what's missing.

---

## Step 1: Verify Location & Python

Confirm we're at the project root and Python is available:

```
python --version
```
(If `python` isn't found, try `python3 --version`. Use whichever works in every
command below — the system works with either.)

Confirm `.windsurf/wsdb.py` exists and runs:
```
python .windsurf/wsdb.py hooks-show
```
If this prints JSON (or a "run init" message), wsdb is working. If it errors with
"file not found", the system files aren't installed — the `.windsurf/` folder (with
`wsdb.py`, `skills/`, `workflows/`, `hooks-interface.md`, `wsdb-interface.md`) must be
unzipped into the project root first.

---

## Step 2: Initialize the State DB

```
python .windsurf/wsdb.py init
```

This creates (if missing): the SQLite schema, `.windsurf/hooks/hooks.json`,
and `.windsurf/.gitignore` (so the DB never dirties git). The schema also
auto-creates on any command, so this step mainly confirms setup and reports the
schema version.

Expected output includes `"ok": true` and a schema version.

---

## Step 3: Verify Git

The system relies on git for safe rollback and the preflight gate.

```
git status
```

- **Not a git repo?** Initialize one: `git init`, then make an initial commit so there's
  a baseline to roll back to.
- **Dirty working tree?** That's fine right now — but note it. The first workflow you run
  will require a clean tree (preflight enforces this). Commit or stash before starting work.

---

## Step 4: Map the Codebase (codebase-orienteer)

Check whether the project is already mapped:

```
python .windsurf/wsdb.py map-get
```

- **Returns `[]`** → run the **codebase-orienteer** skill now. It detects your stack,
  maps the architectural layers, and writes them to the DB with canonical `layer_role`
  values that every other skill depends on.
- **Returns rows** → already mapped. Ask the user: "Re-map, or keep the existing map?"

Do not skip this. Without a codebase map, blast-radius-planner guesses file paths
instead of using your real structure.

---

## Step 5: Configure Test Commands (hooks)

Open `.windsurf/hooks/hooks.json` and confirm the test commands match this project.
The defaults assume pytest/npm; adjust per layer:

```
python .windsurf/wsdb.py hooks-show
```

Key things to verify in `layer_test_commands`:
- The test runner is correct (pytest / jest / vitest / go test / etc.)
- The test paths exist (e.g. `tests/unit`, `tests/integration`)
- `FRONTEND` command matches your frontend test setup (or remove if no frontend)

Ask the user to confirm or correct these before any workflow runs them.

---

## Step 6: Readiness Report

Produce a final summary:

```
## Project Ready

[ ] wsdb state DB initialized (schema v3)
[ ] hooks.json present — test commands: [confirmed / needs adjustment]
[ ] .gitignore protects the DB
[ ] git repo: [clean / dirty — commit before starting]
[ ] codebase mapped: [N] layers ([list roles: DB, MODEL, API, TEST, ...])

You can now run a workflow:
  • Migrate a library        → workflow-library-migration
  • Change a DB schema        → workflow-schema-propagation
  • Build a new feature       → workflow-new-feature
  • Investigate a bug         → workflow-bug-investigation

Each workflow enforces: preflight gate → blast-radius audit → gated per-layer
execution → auto-test via hooks → 3-strike research escalation.
```

---

## Re-run Behavior

Running init again is safe:
- DB already exists → schema-ensure is a no-op, data preserved
- hooks.json exists → left untouched (edit it manually to change test commands)
- map exists → asks before overwriting
- Reports current state without destroying anything

To fully reset a project (destructive — only if asked):
```
# Removes all tracked state. The user must confirm explicitly.
python .windsurf/wsdb.py change-abandon <id>   # for each active change
# or delete .windsurf/state.db to wipe everything and start fresh
```
