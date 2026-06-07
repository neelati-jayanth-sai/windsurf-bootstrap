---
name: windsurf-prompt-maximizer
description: >
  Pulls the next pending execution step from DB and formats it as a ready-to-paste
  Cascade prompt optimized for SWE-1.5 and SWE-1.6. Also transforms ad-hoc raw task
  descriptions into structured Cascade prompts when no DB plan exists. Triggers on:
  "what's next", "give me the next prompt", "format this for Cascade", "structure this
  for Windsurf", "next step prompt", or any request to convert a task description into
  a Cascade instruction. When a DB plan exists, always reads from DB first — never
  reconstructs from conversation context. For single-file or simple tasks with no DB
  plan, applies transformation rules directly to user's raw input.
---

# Windsurf Prompt Maximizer

Pulls next step from DB and formats it for Cascade. When no DB plan exists,
transforms raw task descriptions into structured prompts. Never reconstructs
state from conversation — always reads DB first.

---

## DB Read (Always First)

```bash
python3 .windsurf/wsdb.py next       # next step (its cascade_prompt is ready to paste)
python3 .windsurf/wsdb.py progress   # overall progress
python3 .windsurf/wsdb.py health     # session step-count health
```

**If `wsdb next` returns a step:** Format that step as Cascade prompt. Do not ask user
for task description — it's already in DB.

**If `wsdb next` returns null and change is active:** All steps complete. Tell user to run
consistency verification.

**If no active change:** Apply ad-hoc transformation rules to user's raw input (see below).

---

## Mode A: DB-Driven (plan exists)

Pull the step from DB and format it:

```bash
python3 .windsurf/wsdb.py step-claim <step_id>   # atomic; fails if another session has it
```

Format the `cascade_prompt` field from DB. Prepend session hygiene reminders:

```
// ─── Session Check ──────────────────────────────────────────
// Step [N] of [total] — [step_type]: [layer_name]
// Progress: [steps_done] done, [steps_remaining] remaining
// Context: [health from wsdb]
// If context indicator > 60%: start fresh Cascade session first
// If message count > 18: start fresh Cascade session first
// Commit before starting this step
// Resume command: python3 .windsurf/wsdb.py next
// ────────────────────────────────────────────────────────────

[cascade_prompt from DB]
```

After user confirms step complete:
```bash
python3 .windsurf/wsdb.py step-confirm <step_id>
python3 .windsurf/wsdb.py next        # show what's next
python3 .windsurf/wsdb.py progress
```

---

## Mode B: Ad-Hoc Transformation (no DB plan)

Apply all transformation rules to raw user input.

### Rule 1 — Eliminate Vagueness
Every vague verb becomes specific and file-anchored:
- "fix this" → "correct [specific error] in [specific function] in [specific file]"
- "add feature" → "add [specific thing] to [specific file] exposed via [specific interface]"
- "refactor" → "extract [specific logic] from [specific function] into [new specific location]"
- "improve performance" → "eliminate [specific problem — N+1 / unnecessary rerender / etc.] in [specific file]"

### Rule 2 — Anchor to Existing Code
Replace all abstract references with real file paths and function names.
If user hasn't provided paths: use `[FILL: path to reference file]` — never invent.

### Rule 3 — Explicit Constraints
Every prompt needs at minimum:
- One "Do NOT modify" for adjacent code
- One "Preserve" for interfaces/signatures that must stay stable

### Rule 4 — Testable Acceptance Criteria
Each criterion independently verifiable:
- BAD: "it should work"
- GOOD: "existing tests in [specific file] pass without modification"
- GOOD: "[specific endpoint] returns [specific status] when [specific condition]"
- GOOD: "no TypeScript/mypy errors in modified files"

### Rule 5 — Explicit Out of Scope
Minimum 2-3 things that might seem related but must not be touched.

### Rule 6 — Scope Assessment
- SMALL (1 file, 1 function): CONTEXT + GOAL + CRITERIA only
- MEDIUM (2-5 files, 1 module): full template
- LARGE (6+ files or cross-module): do NOT produce single prompt →
  tell user to run blast-radius-planner first, then come back

### Rule 7 — Plan Gate for Complex Tasks
For 3+ files or business logic: prepend
"Before writing any code, list every file you will modify and what you will change.
Do not proceed until I confirm the plan."

### Rule 8 — SWE-1.6 Parallel Read Hint
For tasks requiring reading multiple files before acting: add
"Read all referenced files before making any edits."

### Output Format (Ad-Hoc Mode)

````
```cascade-prompt
// ─── Session Check ────────────────────────────────
// Ad-hoc task (no DB plan)
// If context > 60% or messages > 18: start fresh session
// Commit current state before starting
// ─────────────────────────────────────────────────

CONTEXT: [what exists, what works, what was just done]
GOAL: [single precise outcome]
CONSTRAINTS:
  - Do NOT modify [specific files/functions]
  - Preserve [specific behavior/signature]
  - Follow pattern in [specific reference file]
ACCEPTANCE CRITERIA:
  - [testable condition 1]
  - [testable condition 2]
OUT OF SCOPE: [explicit list]
```
````

**What changed:** [3-5 bullet list of transformations made]
**Risk flags:** [any [FILL:] items user must resolve before pasting]

---

## Debugging Prompt (Special Case)

When input describes a bug:

````
```cascade-prompt
CONTEXT: [what the code is supposed to do]
BUG: [exact error message verbatim]
LOCATION: [file and function, or [FILL: unknown]]
INSTRUCTION:
  Do not suggest a fix yet.
  Explain what this error means and identify exactly where the failure originates.
  Only after I confirm your diagnosis, propose the minimum code change to fix it.
CONSTRAINTS:
  - Do not modify any file other than [target]
  - Do not change the signature of [function]
```
````

---

## Session Update

After every step confirmation, update session log:

```bash
# Session health updates automatically on each step-claim (counts steps this
# session). Check it any time:
python3 .windsurf/wsdb.py health
```

When health turns AMBER (≥7 steps this session): suggest a fresh Cascade session soon.
When RED (≥12 steps): tell user to start a new Cascade session before the next step.
Note: health counts steps done this session, not chat messages — pair it with your
own watch on Windsurf's context indicator (fresh session above ~60%).
Resume command after a fresh session: `python3 .windsurf/wsdb.py next`
