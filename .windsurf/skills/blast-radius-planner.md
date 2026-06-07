---
name: blast-radius-planner
description: >
  Intercepts any cross-cutting change and enforces impact-mapping before execution.
  Reads codebase_map and research_findings from DB — never guesses file paths.
  Writes the full audit, confirmed file list, and gated execution plan to DB so
  windsurf-prompt-maximizer always works from a real plan, not conversation context.
  Triggers for: schema/model changes, API contract changes, shared type changes,
  component renames/moves, config/env changes, auth logic changes, state management
  changes, library upgrades, error handling standardization, or any "update everything
  that uses X" request. Also triggers on recursive fix loops: "still broken",
  "fixing one thing breaks another", "circular errors".
---

# Blast Radius Planner

Maps the full impact of any cross-cutting change before execution begins.
Reads real codebase structure from DB. Writes a confirmed, gated execution
plan to DB that windsurf-prompt-maximizer pulls from step by step.

---

## DB Interface

All DB access goes through `python3 .windsurf/wsdb.py` (see `wsdb-interface.md`).
Never use raw `sqlite3 "..."` — it breaks on the quotes/newlines in Cascade prompts.

## DB Read (Always First)

```bash
python3 .windsurf/wsdb.py map-get        # codebase layers (empty array = not mapped)
python3 .windsurf/wsdb.py research-get   # verified versions / deprecated patterns
python3 .windsurf/wsdb.py progress       # any already-active change
```

If `map-get` returns `[]`: STOP. Tell user to run codebase-orienteer first.

If `progress` shows an active change: ask "Continue existing change or start new one?"
Match layers by `layer_role` (DB/MODEL/REPO/SERVICE/API/TYPE/FRONTEND/TEST/CONFIG/AUTH),
never by display name.

---

## Phase 0: Change Classification

```
Change type:  [SCHEMA/CONTRACT/TYPE/COMPONENT/CONFIG/AUTH/STATE/DEPENDENCY/BEHAVIOR/COMPOUND]
Impact scope: [CONTAINED/LAYERED/SYSTEMIC]

CONTAINED  → 1-3 files, single layer → lightweight audit only
LAYERED    → 2-3 architectural layers → full protocol
SYSTEMIC   → 4+ layers or uncertain  → full protocol + extra verification
COMPOUND   → multiple types          → treat as SYSTEMIC
```

---

## Phase 1: Blast Radius Audit

Use the layer map from DB as the structural template — not invented paths.
For each layer in codebase_map, assess what changes in that layer.

Ask user to run this discovery command before auditing:

```bash
# Find all references to the changed entity across the codebase
grep -r "[ENTITY_NAME]" . \
  --include="*.py" --include="*.ts" --include="*.tsx" \
  --include="*.js" --include="*.go" --include="*.java" \
  -l \
  ! -path "*/.git/*" ! -path "*/node_modules/*" ! -path "*/__pycache__/*"
```

Then produce the audit using real file paths from grep output + layer map:

```
## Blast Radius Audit: [Change Description]

Change summary: [what is changing and what it means structurally]

### Affected Layers (bottom → top, from codebase_map)

Layer [N] — [layer_name from DB]
  Files:    [real paths from grep output]
  Changes:  [what specifically changes in each file]
  Required: YES / NO
  Risk:     HIGH / MEDIUM / LOW

[repeat for each layer]

### Cross-Cutting Concerns
[ ] Validation schemas ([detected schema lib from codebase_map])
[ ] OpenAPI / Swagger spec (if exists)
[ ] GraphQL schema / resolvers (if exists)
[ ] Event payloads / message queue schemas (if exists)
[ ] Cache keys encoding changed fields
[ ] Audit logs / analytics events
[ ] CI/CD config (if change affects build/deploy)

### Risk Flags
[files where change is ambiguous, high-risk, or unclear scope]

### Files NOT affected (explicit)
[2-3 things that seem related but are out of scope]

### Total: [N] files across [N] layers
```

After audit: "Review this. Add missed files, correct any paths, then confirm."
**No code until user confirms.**

---

## Phase 2: User Confirmation Gate

Wait for explicit confirmation.
For each correction user makes: acknowledge, re-assess which layer it belongs in.
On confirmation → Phase 3.

---

## Phase 3: Gated Execution Plan

Build step list from confirmed audit. Each step:
- One layer only
- Independently committable
- Explicit acceptance criteria
- Pre-built Cascade prompt (see format below)

```
## Execution Plan: [Change Description]

⚠️  BEFORE STEP 1: git commit your clean baseline.
⚠️  Session hygiene: Watch context indicator. Above 60% → start fresh Cascade session.
⚠️  Message limit: After 20 messages in a session, start a new one.
    Resume with: python3 .windsurf/wsdb.py next

Step 1 — [Layer Name] ([IMPL/TEST])
Files:    [list]
Criteria: [testable conditions]
Gate:     [what to run — pytest / tsc / npm test] before Step 2

[continue for all steps]

Final — Consistency Verification (VERIFY step)
```

---

## Cascade Prompt Format

For each step, generate a ready-to-paste Cascade prompt:

```
CONTEXT: [what exists, what was done in previous steps, verified versions from research]
GOAL: [single precise outcome for this layer only]
CONSTRAINTS:
  - Do NOT modify files outside [this layer's paths]
  - Preserve [interfaces/signatures that must stay stable]
  - Follow pattern in [reference file from same layer]
  - Use [specific library version verified in research]
ACCEPTANCE CRITERIA:
  - [testable condition 1]
  - [testable condition 2]
OUT OF SCOPE: [explicit list of adjacent things to leave untouched]
// Session: commit before this step. Start fresh Cascade session if context > 60%.
```

---

## DB Write

Use temp files for payloads (never inline) so quotes/newlines in prompts survive:

```bash
# 1. Register the change → returns {"change_id": N}
cat > /tmp/change.json << 'JSON'
{"change_type":"[type]","impact_scope":"[scope]","change_description":"[desc]","confirmed_by_user":1}
JSON
python3 .windsurf/wsdb.py change-add < /tmp/change.json
# note the change_id from output, use below

# 2. Write all blast-radius files at once
cat > /tmp/blast.json << 'JSON'
{"rows":[
  {"change_id":N,"layer_number":1,"layer_name":"Migrations","file_path":"...","what_changes":"...","risk_level":"LOW","confirmed":1}
]}
JSON
python3 .windsurf/wsdb.py blast-add < /tmp/blast.json

# 3. Write all execution steps (seq auto-assigned in array order)
cat > /tmp/steps.json << 'JSON'
{"steps":[
  {"change_id":N,"step_label":"1","step_type":"IMPL","layer_name":"Migrations",
   "files":["..."],"acceptance_criteria":["..."],"cascade_prompt":"CONTEXT: ...\nGOAL: ..."}
]}
JSON
python3 .windsurf/wsdb.py step-add < /tmp/steps.json

# 4. Confirm the plan
python3 .windsurf/wsdb.py board
```

---

## Phase 4: Layer Execution

For each step, Cascade:

1. Get next step: `python3 .windsurf/wsdb.py next`
2. Claim it atomically (prevents two sessions doing the same step):
   ```bash
   python3 .windsurf/wsdb.py step-claim <step_id>
   ```
   If claim returns `{"ok": false}` → another session has it; stop.
3. Announce: "Executing Step <label> — <layer_name>"
4. Implement files for this step only
5. Present acceptance checklist, wait for user
6. On gate pass:
   ```bash
   python3 .windsurf/wsdb.py step-confirm <step_id>
   ```
7. Do NOT proceed until confirmed and user replies

**If step fails:**
```bash
python3 .windsurf/wsdb.py step-fail <step_id> "what went wrong"
```
A failed step is surfaced FIRST by `next` — you cannot skip past it. Resolve, then
re-claim and retry. Do not proceed to later steps.

**If scope expands (file not in plan needs changing):**
Stop. Ask user. If yes, add to blast_radius first via `blast-add`, then implement.

---

## Phase 5: Consistency Verification

After all IMPL and TEST steps confirmed:

```bash
python3 .windsurf/wsdb.py board   # confirm all steps confirmed
```

Search for residual references to old entity:
```bash
grep -r "[OLD_ENTITY_NAME]" . \
  --include="*.py" --include="*.ts" --include="*.tsx" -l \
  ! -path "*/.git/*" ! -path "*/node_modules/*"
```

Produce verification block. On clean pass:
```bash
python3 .windsurf/wsdb.py change-complete <change_id>
```

---

## Recursive Fix Loop Recovery

Triggered by: "still broken", "fixing one breaks another", "circular errors".

```bash
python3 .windsurf/wsdb.py board   # shows failed steps and their failure_notes
```

Produce diagnosis:
```
## Recursive Fix Recovery

Modified files:   [list from DB or user]
Per-file state:   [what each file currently expects as input/output]
Mismatch:         [File A produces X → File B expects Y → mismatch is Z]
Minimum repair:   [smallest set of simultaneous changes that resolves all mismatches]
Why loop failed:  [why patching symptoms kept regenerating the error]
```

Then resume from the failed step in the execution plan.
