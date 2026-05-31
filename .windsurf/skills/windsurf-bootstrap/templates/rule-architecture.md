---
trigger: model_decision
description: Use when reasoning about this repository's architecture — module boundaries, data flow, key abstractions, or cross-cutting concerns.
---

<!-- GENERATOR: Loaded only when Cascade judges it relevant, so the description above
     must be specific. Up to 12,000 chars, but stay focused. Replace {{PLACEHOLDER}}s and
     remove GENERATOR comments. -->

# Architecture — {{PROJECT_NAME}}

## High-level shape
{{DESCRIBE: the major components/services and how requests or data flow between them}}

## Module boundaries
<!-- GENERATOR: one entry per significant module/package. -->
- `{{MODULE}}`: {{RESPONSIBILITY}}. Depends on {{DEPENDS_ON}}. Do not {{ANTI_PATTERN}}.

## Key abstractions
- {{ABSTRACTION}}: {{WHAT_IT_IS_AND_WHERE_DEFINED}}

## Data & state
{{DESCRIBE: schema/models location, migrations, caching, external services}}

## Cross-cutting concerns
- Auth: {{HOW_AUTH_WORKS_OR_NA}}
- Config / env: {{HOW_CONFIG_IS_LOADED}}
- Error handling & logging: {{PATTERNS}}

## Gotchas
<!-- GENERATOR: real footguns discovered in the code — the things a newcomer breaks. -->
- {{GOTCHA}}
