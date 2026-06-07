name: workflow-new-feature
description: >
  Orchestrates building a new feature from scratch: codebase orientation (if needed),
  optional research for new libraries, blast-radius planning for the feature's touch points,
  and step-by-step implementation with Cascade prompts. Activates for: "build X feature",
  "add X functionality", "implement X", "create X module", "new endpoint for X".
---

# Workflow: New Feature

Sequences: codebase-orienteer (if needed) → research-first-coder (if new libs) →
blast-radius-planner → windsurf-prompt-maximizer (per step) → verification.

---

## Step 0: Pre-Flight Check

```bash
python .windsurf/wsdb.py map-get
# → If 0: run codebase-orienteer first

echo "git checkout -b feature/[feature-name]"
echo "git commit -m 'baseline before feature: [name]'"
```

---

## Step 1: Feature Spec (Before Any Code)

Do not proceed without a spec. Ask the user:

```
1. What is the feature? (1-2 sentence description)
2. What are the inputs? (user action, API call, event, etc.)
3. What are the outputs? (response, side effect, state change, etc.)
4. What are the edge cases? (validation, error states, permission boundaries)
5. What is explicitly OUT OF SCOPE for this iteration?
6. Does this require any new third-party library?
```

Record to DB:
Write this JSON to a file (use Cascade's file tool), then call wsdb with --file:
```json
{"change_id":N,"decision_type":"STRATEGY","description":"[what]","rationale":"[why]"}
```
```
python .windsurf/wsdb.py decision-add --file payload.json
```

---

## Step 2: Research (If New Library Needed)

**Activate:** `research-first-coder` — only if answer to question 6 was YES.

Skip if feature is built entirely on existing stack.

Gate: research_findings written for any new library before proceeding.

---

## Step 3: Blast Radius Audit

**Activate:** `blast-radius-planner` with change_type = appropriate to feature

For new features, the "blast radius" is the feature's footprint:
- What layers does this feature touch?
- What existing code does it integrate with?
- What existing interfaces does it extend vs create new?

The audit for a new feature should identify:
```
New files to create (per layer, bottom → top)
Existing files to modify (integration points)
Shared types/interfaces to extend
Test files to create
```

---

## Step 4: Execute Steps

**Activate:** `windsurf-prompt-maximizer` per step

Build bottom-up:
```
Step 1: DB migration (if new table/column needed)
Step 2: Model/entity
Step 3: Repository methods
Step 4: Service/business logic
Step 5: API endpoint + request validation
Step 6: Types/interfaces/schemas
Step 7: Frontend hook/store
Step 8: Frontend component
Step 9: Unit tests per layer
Step 10: Integration test
Step 11: E2E test (if applicable)
```

Between every step: `git commit -m "feature/[name]: step [N] [layer]"`

---

## Step 5: Feature Verification

```bash
# Type check
# Full test suite
# Manual smoke test against spec acceptance criteria
# Review against original feature spec — does every requirement have test coverage?

python .windsurf/wsdb.py change-complete <change_id>

echo "git push origin feature/[feature-name]"
echo "Open PR"
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
