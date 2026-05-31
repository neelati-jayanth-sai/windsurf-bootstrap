---
trigger: always_on
description: Core context about this repository — what it is, its stack, and where things live.
---

<!-- GENERATOR: This file is ALWAYS in context. Keep it under ~3,500 chars. Put deep
     detail in architecture.md instead. Replace every {{PLACEHOLDER}}; delete every
     GENERATOR comment before saving. -->

# Project Brain — {{PROJECT_NAME}}

## What this is
{{ONE_PARAGRAPH: what the project does and who uses it}}

## Stack
- Language(s): {{LANGUAGES_WITH_VERSIONS}}
- Framework(s): {{FRAMEWORKS}}
- Data layer: {{DB_AND_ORM_OR_NONE}}
- Build tool: {{BUILD_TOOL}}
- Test framework: {{TEST_FRAMEWORK}}
- Lint / format: {{LINT_AND_FORMAT_TOOLS}}

## Repository layout
<!-- GENERATOR: list only the directories that matter, one line each. -->
- `{{DIR}}` — {{ROLE}}
- `{{DIR}}` — {{ROLE}}

## Canonical commands
<!-- GENERATOR: use the EXACT commands found in the repo. Mark unknowns as TODO. -->
- Install:   `{{INSTALL_CMD}}`
- Dev / run: `{{DEV_CMD}}`
- Build:     `{{BUILD_CMD}}`
- Lint:      `{{LINT_CMD}}`
- Typecheck: `{{TYPECHECK_CMD_OR_NA}}`
- Test:      `{{TEST_CMD}}`

## Ground rules
- Match existing conventions in the file you are editing over any general preference.
- Run the lint/typecheck/test gate before considering a change done.
- See `architecture.md` for module boundaries and `coding-standards.md` for style.
