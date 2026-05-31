---
name: debugging
description: Use when diagnosing or fixing a bug, failing test, or unexpected behavior in {{PROJECT_NAME}} — reproducing, isolating, and fixing using this stack's tools.
---

<!-- GENERATOR: Save to .windsurf/skills/debugging/SKILL.md. Tailor to the stack. -->

# Debugging in {{PROJECT_NAME}}

## 1. Reproduce
- Establish the smallest reliable repro. Run: `{{REPRO_OR_TEST_CMD}}`.
- Capture the exact error, stack trace, and inputs.

## 2. Isolate
- Entry points / logs to check: {{LOG_LOCATIONS_OR_TOOLS}}.
- Narrow to a module using `architecture.md`. Add temporary instrumentation at
  {{INSTRUMENTATION_GUIDANCE}}; remove it before finishing.
- Form one hypothesis at a time; confirm or reject before moving on.

## 3. Fix
- Make the smallest change that addresses the root cause, not the symptom.
- Follow `coding-standards.md`.

## 4. Prove the fix
- Add a regression test that fails before the fix and passes after: `{{TEST_CMD}}`.
- Run the full gate: `bash .windsurf/validate.sh full`.

## 5. Summarize
- Report root cause, the fix, and the regression test added.
