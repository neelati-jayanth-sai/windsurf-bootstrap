---
description: Run and extend the test suite for {{PROJECT_NAME}} using the project's runner and conventions.
---

<!-- GENERATOR: Save to .windsurf/workflows/test.md. Invoked as /test. -->

# /test

1. Ask what to target: full suite, a focused area, or new tests for recent changes.
2. Apply the **testing** skill for placement, naming, fixtures, and mocking.
3. Iterate fast with `{{FOCUSED_TEST_CMD}}`, then run the full gate:
   `bash .windsurf/validate.sh full`.
4. If anything fails, hand off to /debug.
5. Report pass/fail and coverage of the changed code.
