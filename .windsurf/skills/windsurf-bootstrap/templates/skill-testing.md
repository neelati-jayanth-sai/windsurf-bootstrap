---
name: testing
description: Use when writing, running, or extending tests in {{PROJECT_NAME}} — test placement, naming, fixtures/mocks, and running focused subsets with this project's runner.
---

<!-- GENERATOR: Save to .windsurf/skills/testing/SKILL.md. Tailor to the runner. -->

# Testing in {{PROJECT_NAME}}

## Where & how
- Runner: {{TEST_FRAMEWORK}}. Full suite: `{{TEST_CMD}}`.
- Focused run: `{{FOCUSED_TEST_CMD}}` (use while iterating to stay fast).
- Tests live in {{TEST_LOCATION}}, named {{TEST_NAMING}}.

## Writing tests
- Structure: {{TEST_STRUCTURE e.g. arrange/act/assert, describe/it}}.
- Fixtures / setup: {{FIXTURE_PATTERN}}.
- Mocking external calls: {{MOCK_PATTERN}} — never hit real network/DB in unit tests.
- Cover the happy path plus the failure/edge cases that motivated the change.

## Before declaring done
- `{{TEST_CMD}}` passes; new code is covered; no skipped/focused tests left in.
- {{COVERAGE_EXPECTATION_OR_NA}}.
