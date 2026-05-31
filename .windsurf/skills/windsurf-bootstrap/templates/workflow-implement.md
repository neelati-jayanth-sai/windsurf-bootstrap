---
description: Implement a feature in {{PROJECT_NAME}} end to end, following project conventions and validating before completion.
---

<!-- GENERATOR: Save to .windsurf/workflows/implement.md. Invoked as /implement. The "how"
     lives in the feature-implementation skill; this is just the entry point. -->

# /implement

1. Restate the feature in one sentence and confirm scope with me.
2. Apply the **feature-implementation** skill: locate the right module, follow project
   conventions, write code + types + tests.
3. Run the gate: `bash .windsurf/validate.sh full`. Fix any failures before continuing.
4. Summarize what changed and which tests cover it.
5. Optionally: Call /review before committing.
