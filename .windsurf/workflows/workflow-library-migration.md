---
name: workflow-library-migration
description: >
  Orchestrates a complete library/framework migration from research through implementation
  through test migration through verification. Activates for: "migrate from X to Y",
  "replace X with Y", "upgrade X to major version", "switch from X to Y".
  This workflow is the active orchestrator — it does not do any work itself, it sequences
  the component skills, enforces gates between them, and tracks overall state in DB.
---

# Workflow: Library Migration

Sequences: codebase-orienteer → research-first-coder → blast-radius-planner →
migration-test-strategist → windsurf-prompt-maximizer (per step) → verification.

---

## Step 0: Pre-Flight Check

```bash
# Check DB exists and is initialized
python3 .windsurf/wsdb.py init        # idempotent — safe to run every time
python3 .windsurf/wsdb.py map-get     # [] means codebase not mapped yet
# → If 0: run codebase-orienteer FIRST. Do not proceed.

# Check for abandoned active changes
python3 .windsurf/wsdb.py progress
# → If exists: confirm with user whether to continue or abandon before starting new migration.

# Confirm clean git state
echo "Run: git status — confirm clean working tree before starting."
echo "Then: git commit if anything unstaged."
```

---

## Step 1: Research

**Activate:** `research-first-coder`

Target libraries to research:
- The library being migrated FROM (current version, known deprecated patterns)
- The library being migrated TO (current version, API signatures, migration guide)
- Any compatibility layer or bridge library
- Cross-library compatibility constraints (e.g. shared dependency versions)

Gate: research_findings rows written for all involved libraries.

```bash
python3 .windsurf/wsdb.py research-get
# → Must show rows for FROM and TO library before proceeding
```

---

## Step 2: Blast Radius Audit

**Activate:** `blast-radius-planner`

Context to provide from Step 1:
- Deprecated patterns from the FROM library (so audit flags every usage)
- API changes in the TO library (so each file's required change is specific)
- Verified dependency versions (so acceptance criteria use exact versions)

Gate: change_registry row written, blast_radius rows written, execution_steps (IMPL only)
written, all confirmed by user.

```bash
python3 .windsurf/wsdb.py board
# → Must show IMPL steps in pending status before proceeding
```

---

## Step 3: Test Strategy

**Activate:** `migration-test-strategist`

Context from DB (automatic):
- IMPL steps from execution_steps
- Test layer from codebase_map
- Research findings for library-specific test patterns

Gate: TEST steps interleaved in execution_steps. T0 step inserted before IMPL step 1.
Final cleanup step inserted at end.

```bash
python3 .windsurf/wsdb.py board
# → Must show alternating IMPL / TEST steps before proceeding
```

Record test isolation strategy decision:
```bash
cat > /tmp/dec.json << 'JSON'
{"change_id":N,"decision_type":"STRATEGY","description":"[what]","rationale":"[why]"}
JSON
python3 .windsurf/wsdb.py decision-add < /tmp/dec.json
```

---

## Step 4: Baseline

Before any implementation:

```bash
# Run full test suite, record result
echo "Run your full test suite now."
echo "Record the pass count — this is your baseline."
echo "Command: [test runner command from codebase_map]"

# Store baseline
cat > /tmp/dec.json << 'JSON'
{"change_id":N,"decision_type":"ARCHITECTURE","description":"Test baseline: [N] tests passing","rationale":"Must not drop below this at any gate"}
JSON
python3 .windsurf/wsdb.py decision-add < /tmp/dec.json

# Final git commit before starting
echo "git add -A && git commit -m 'baseline before migration: [from] → [to]'"
```

---

## Step 5: Execute Steps (Repeat Per Step)

**Activate:** `windsurf-prompt-maximizer` for each step

```bash
# Get next step
python3 .windsurf/wsdb.py next
```

For each step:
0. `python3 .windsurf/wsdb.py next` then `python3 .windsurf/wsdb.py step-claim <step_id>`
1. Paste the `cascade_prompt` from DB into a fresh Cascade conversation if:
   - session health = RED, or
   - this is a new IMPL→TEST boundary
   Otherwise continue in current session.
2. Run implementation/test changes
3. Run gate command (test suite / type check)
4. Confirm gate passed
5. `git commit -m "step [N]: [layer_name]"`
6. Update DB:
   ```bash
   python3 .windsurf/wsdb.py step-confirm <step_id>
   ```
7. Repeat for next step

**Session hygiene between steps:**
```bash
python3 .windsurf/wsdb.py progress
# Shows done/remaining/failed counts at any point
```

---

## Step 6: Consistency Verification

**Activate:** Final VERIFY step from `blast-radius-planner`

```bash
# Search for remaining FROM library imports
grep -r "[OLD_LIBRARY]" . \
  --include="*.py" --include="*.ts" --include="*.tsx" \
  -l ! -path "*/.git/*" ! -path "*/node_modules/*"

# Should return nothing (or only files intentionally kept)

# Run full test suite
# Should match or exceed baseline count

# Type check
# Should return 0 errors
```

---

## Step 7: Close

```bash
# Mark change complete
python3 .windsurf/wsdb.py change-complete <change_id>

# Final summary
python3 .windsurf/wsdb.py progress

# Tag the completion
echo "git tag migration/[from]-to-[to]-complete"
echo "git push"
```

---

## Resume Protocol (After Any Break)

```bash
# Full state in one query
python3 .windsurf/wsdb.py progress
python3 .windsurf/wsdb.py next
python3 .windsurf/wsdb.py board
python3 .windsurf/wsdb.py health

# Paste next_step.cascade_prompt into Cascade
# Continue from where you left off — no context reconstruction needed
```
