---
trigger: always_on
description: Core coding standards and conventions actually followed in this repository.
---

<!-- GENERATOR: ALWAYS in context — keep under ~3,500 chars. State only standards the
     code actually follows (read real files to confirm). Prefer positive, specific rules
     over vague ones. Push language-specific detail into a glob rule (lang-*.md). -->

# Coding Standards — {{PROJECT_NAME}}

## Style & formatting
- Formatter: {{FORMATTER}} — run `{{FORMAT_CMD}}`; do not hand-format against it.
- {{NAMING_CONVENTION_RULE}}
- {{IMPORT_ORDER_RULE}}

## Types & safety
- {{TYPE_STRICTNESS_RULE}}
- {{ERROR_HANDLING_RULE}}

## Structure
- {{FILE_PLACEMENT_RULE}}
- {{MODULE_SIZE_OR_BOUNDARY_RULE}}

## Testing expectations
- {{WHEN_TESTS_ARE_REQUIRED}}
- {{TEST_LOCATION_AND_NAMING}}

## Don't
<!-- GENERATOR: concrete anti-patterns specific to this repo, not generic advice. -->
- {{ANTI_PATTERN}}
