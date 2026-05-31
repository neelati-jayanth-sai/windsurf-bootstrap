---
description: Review the current changes in {{PROJECT_NAME}} before commit or PR, ending with a clean validation gate and a findings summary.
---

<!-- GENERATOR: Save to .windsurf/workflows/review.md. Invoked as /review. -->

# /review

1. Identify what to review: `git diff` against the base branch, or the staged changes.
2. Apply the **code-review** skill across that diff.
3. Run `bash .windsurf/validate.sh full`.
4. Summarize findings as **blocking** vs **nits**, each with location and a fix.
5. If there are blocking issues, hand off to /debug or /implement to address them.
