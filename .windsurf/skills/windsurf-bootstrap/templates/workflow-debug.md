---
description: Diagnose and fix a bug or failing test in {{PROJECT_NAME}}, ending with a regression test and a clean validation gate.
---

<!-- GENERATOR: Save to .windsurf/workflows/debug.md. Invoked as /debug. -->

# /debug

1. Ask me for the symptom, error, or failing test if not already given.
2. Apply the **debugging** skill: reproduce → isolate → fix root cause.
3. Add a regression test that fails before the fix and passes after.
4. Run the gate: `{{LINT_CMD}}` then `{{TEST_CMD}}`. Fix any fallout.
5. Report root cause, the fix, and the test added.
