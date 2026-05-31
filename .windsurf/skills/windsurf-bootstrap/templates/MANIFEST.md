<!-- GENERATOR: Save to <repo-root>/.windsurf/BOOTSTRAP_MANIFEST.md. Records what was
     generated so the config is auditable, the bootstrap folder is safe to delete, and
     /sync-windsurf has a baseline to diff against. -->

# Windsurf Bootstrap Manifest

- Generated: {{DATE}}   (update to "Synced: {{DATE}}" on /sync-windsurf runs)
- Repository: {{PROJECT_NAME}}

## Detected stack
- Languages: {{LANGUAGES_WITH_VERSIONS}}
- Frameworks: {{FRAMEWORKS}}
- Test framework: {{TEST_FRAMEWORK}}
- Lint / format: {{LINT_AND_FORMAT_TOOLS}}

## Commands wired into validate.sh / workflows
- Lint:      `{{LINT_CMD}}`
- Typecheck: `{{TYPECHECK_CMD_OR_NA}}`
- Test:      `{{TEST_CMD}}`
- Build:     `{{BUILD_CMD}}`

## Files created / updated
<!-- GENERATOR: list every path touched; created | updated | merged. -->
- `.windsurf/validate.sh` — {{created|updated}}
- `.windsurf/rules/project-brain.md` — {{created|updated|skipped: AGENTS.md present}}
- `.windsurf/rules/architecture.md` — {{created|updated}}
- `.windsurf/rules/coding-standards.md` — {{created|updated}}
- `.windsurf/skills/feature-implementation/SKILL.md` — {{created|updated}}
- `.windsurf/skills/debugging/SKILL.md` — {{created|updated}}
- `.windsurf/skills/testing/SKILL.md` — {{created|updated}}
- `.windsurf/skills/code-review/SKILL.md` — {{created|updated}}
- `.windsurf/skills/windsurf-config-maintenance/SKILL.md` — {{created|updated}}
- `.windsurf/workflows/implement.md` — {{created|updated}}
- `.windsurf/workflows/debug.md` — {{created|updated}}
- `.windsurf/workflows/test.md` — {{created|updated}}
- `.windsurf/workflows/review.md` — {{created|updated}}
- `.windsurf/workflows/sync-windsurf.md` — {{created|updated}}
- `.windsurf/hooks.json` — {{created|merged}}

## Reconciled with existing config
- AGENTS.md: {{found+integrated | not present}}
- .windsurfrules (legacy): {{folded in | not present}}

## Open items
<!-- GENERATOR: every TODO left for the user. "None" if clean. -->
- {{TODO_OR_NONE}}

## Notes
The `windsurf-bootstrap/` folder is no longer required and can be deleted. To refresh this
config later, run /sync-windsurf. Reload Windsurf to pick up changes.
