name: workflow-bug-investigation
description: >
  Orchestrates structured bug investigation: symptom isolation, root cause identification,
  minimum repair, and regression test. Activates for: "there's a bug in X", "X is broken",
  "getting an error in X", "X stopped working", "unexpected behavior in X", or when user
  pastes an error message or stack trace. Deliberately lightweight — does not require
  codebase-orienteer or research unless the bug is in a third-party integration.
---

# Workflow: Bug Investigation

Sequences: symptom isolation → root cause diagnosis → minimum repair →
regression test → commit. Fast and contained — does not run full blast-radius
unless the fix turns out to affect multiple layers.

---

## Step 0: DB Check

```bash
python .windsurf/wsdb.py map-get
# → Layer map helpful but not required for bug investigation
# → If empty: proceed without it, just note file paths manually

echo "git stash  # clear any in-progress work"
echo "git commit -m 'baseline before bug fix: [description]'"
```

---

## Step 1: Symptom Isolation

Ask for:
```
1. Exact error message (paste verbatim, not paraphrased)
2. Stack trace (full, not truncated)
3. Steps to reproduce (minimal)
4. Expected behavior
5. When did it start? (after a deploy? after a specific change?)
6. Is it consistent or intermittent?
```

**Activate:** `windsurf-prompt-maximizer` in debugging mode:

```
CONTEXT: [what the code is supposed to do]
BUG: [exact error message verbatim]
LOCATION: [file/function if known, else UNKNOWN]
INSTRUCTION:
  Do not suggest a fix yet.
  Identify exactly where in the code the failure originates.
  Trace the data flow that leads to this error.
  Only after I confirm your diagnosis, propose minimum fix.
CONSTRAINTS:
  - Do not modify any file yet
  - Do not suggest refactoring
```

Gate: diagnosis confirmed by user before any code changes.

---

## Step 2: Scope Assessment

After diagnosis, assess:

```
Single-file fix?   → proceed directly, no blast-radius needed
Multi-file fix?    → run blast-radius-planner with change_type=BEHAVIOR
Third-party bug?   → run research-first-coder to check known issues/workarounds
Data integrity?    → check if DB records are corrupt, may need data fix not code fix
```

If multi-file: activate blast-radius-planner before writing any fix.

---

## Step 3: Minimum Repair

**Activate:** `windsurf-prompt-maximizer`

```
CONTEXT: Bug confirmed in [file/function]. Root cause: [diagnosis].
GOAL: Fix [specific error condition] with minimum code change.
CONSTRAINTS:
  - Change only [specific file/function]
  - Do NOT refactor surrounding code
  - Do NOT change function signatures
  - Preserve all existing test behavior
ACCEPTANCE CRITERIA:
  - [specific reproduction case] no longer throws [specific error]
  - All existing tests pass
OUT OF SCOPE: Performance improvements, style changes, related issues
```

---

## Step 4: Regression Test

Always add a test that would have caught this bug:

```
CONTEXT: Bug in [function] — [description]. Now fixed.
GOAL: Add one test case that reproduces the exact bug condition and confirms the fix.
CONSTRAINTS:
  - Add to existing test file [path]
  - Do not modify the implementation
  - Test name should describe the bug: test_[function]_[condition]_[expected_behavior]
ACCEPTANCE CRITERIA:
  - New test passes
  - New test would have FAILED before the fix (verify by reverting fix, running test)
```

---

## Step 5: Commit and Record

```bash
git add [changed files]
git commit -m "fix: [description of bug] — [root cause in one line]"

# Record in DB
# write dec.json with Cascade file tool:
# {"change_id":N,"decision_type":"STRATEGY","description":"[what]","rationale":"[why]"}
python .windsurf/wsdb.py decision-add --file dec.json
```


## Hook Enforcement (applies to every step)

This workflow uses hooks so testing/commit/escalation are enforced. Per step:
```
python .windsurf/wsdb.py run-hook on_session_start          # preflight (once per session)
python .windsurf/wsdb.py run-hook before_implement --step <id>
python .windsurf/wsdb.py step-claim <id>
# ... implement ...
python .windsurf/wsdb.py run-hook on_step_complete --step <id>   # runs layer tests
#   pass  → run-hook on_gate_pass --step <id> → step-confirm <id>
#   fail  → step-fail <id> --error "<output>" → check-escalate <id>
#           (3 fails → research-first-coder on the error, then retry once)
```
See `.windsurf/hooks-interface.md` for the full hook contract and how to set test
commands per layer in `.windsurf/hooks/hooks.json`.
