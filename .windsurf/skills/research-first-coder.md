---
name: research-first-coder
description: >
  Enforces research-before-implementation for any task involving third-party libraries,
  frameworks, SDKs, APIs, cloud services, databases, build tools, or rapidly evolving
  technology. Writes verified findings to .windsurf/state.db so all downstream skills
  consume facts, not assumptions. Triggers on any named library or package, version-specific
  behavior, driver/connector config, cloud service integration, CLI tool usage, or phrases
  like "how do I use X", "implement X with Y", "connect to X", "configure X", "migrate to X".
  CRITICAL: Activates even when the answer seems obvious — pre-trained knowledge is
  frequently outdated. Accuracy > Speed. Research first, always.
---

# Research-First Coder

Verifies current library state via web research before any implementation.
Writes all findings to DB so downstream skills (blast-radius-planner,
migration-test-strategist, windsurf-prompt-maximizer) work from verified facts.

**Priority:** Accuracy → Current Best Practices → Correct Implementation → Speed.

---

## DB Read (Always First)

```bash
python3 .windsurf/wsdb.py research-get   # existing research (avoid duplicate)
python3 .windsurf/wsdb.py progress       # active change context
```

If recent research exists for the same library (within 7 days): show it and ask
"Use existing research or re-research?" Do not duplicate unless asked.

---

## Phase 1: Technology Assessment

Identify before searching:

```
Library/framework:   [exact name]
Language/ecosystem:  [Python / Node / Go / etc.]
Package manager:     [pip / npm / etc.]
Version in use:      [from pyproject.toml / package.json / go.mod — or UNKNOWN]
Task:                [install / configure / connect / query / migrate / deploy]
Staleness risk:      HIGH / MEDIUM / LOW

HIGH  → Cloud SDKs, data platforms, auth libs, AI frameworks, major version ≥ 2
MEDIUM → Established frameworks (Django, Spring, Rails)
LOW   → Language stdlib, stable specs (SQL-92, HTTP/1.1, POSIX)
```

If LOW and behavior is certain: skip to DB Write, note research skipped and why.

---

## Phase 2: Targeted Web Research

**Mandatory first search — package registry for current version:**
```
[library] current version site:pypi.org
[library] current version site:npmjs.com
[library] latest release site:github.com
```

This version becomes the staleness baseline. Any search result discussing an older
version is downweighted. Any result more than 6 months old on a HIGH-staleness
library is treated as potentially outdated.

**Then search in priority order:**

1. Official documentation — exact API signatures, config keys, current examples
2. Official GitHub CHANGELOG.md / MIGRATION.md — breaking changes
3. Official release announcements — version-specific upgrade notes
4. Package registry metadata — dependency requirements
5. Community (secondary, verify against official) — Stack Overflow filtered by date,
   GitHub Discussions, official Discord pinned messages

**Search query patterns:**
```
[library] [version] official documentation [current year]
[library] changelog breaking changes latest
[library] [specific feature/API] current example
[library] deprecation [pattern user is asking about]
[library] [dependency name] compatibility version
```

**Extract for each source:**
- Current stable version + release date
- Exact API signatures (not from memory)
- Required dependencies + their versions
- Config keys and values (auth, connections, catalogs)
- Deprecated patterns that match what user might expect
- Breaking changes since user's version
- Known bugs relevant to the task

---

## Phase 3: Research Summary

Present this block before any code. Always present even if brief.

```
## Research Summary: [Library] [Version]

Sources consulted: [URL list]
Current stable version: [version] (released [date])
Version targeted: [version]

### Key Findings
- [Finding 1]
- [Finding 2]
- [Finding 3]

### Deprecated Patterns to Avoid
- [old pattern] → replaced by [new pattern] (since v[X])
- [old pattern] → removed in v[X]

### Verified Dependencies
[lib]==[version]
[dep]==[version]

### Breaking Changes Since User's Version
- [change 1] — affects [what]
- [change 2] — affects [what]

### Implementation Approach
[2-3 sentences based on verified docs, not assumptions]
```

---

## Phase 4: Implementation

Write code only after Research Summary is presented. Code must:

- Use only verified API signatures
- Match exact import paths from official docs
- Pin versions in any dependency declarations
- Cite source inline for non-obvious patterns:
  ```python
  # Per [Library] docs v[X]: [brief reason]
  actual_code_here()
  ```
- Use `[FILL: description]` for environment-specific values
- Note version compatibility in docstrings for public functions

---

## Phase 5: Verification Checklist

```
[ ] All imports verified against current official docs
[ ] No deprecated APIs used (or explicitly flagged if unavoidable)
[ ] Dependency versions pinned correctly
[ ] Breaking changes since user's version accounted for
[ ] Auth/connection pattern matches current recommended approach
[ ] All examples derived from official source, not training memory
```

---

## DB Write

Cascade runs these commands after research is complete:

```bash
cat > /tmp/research.json << 'JSON'
{"library":"[name]","version_found":"[registry version]","version_targeted":"[target]",
 "source_urls":["url1","url2"],
 "key_findings":["finding1","finding2"],
 "deprecated_patterns":[{"old":"pattern","new":"replacement"}],
 "verified_deps":["lib==version","dep==version"],
 "raw_summary":"[full summary]"}
JSON
python3 .windsurf/wsdb.py research-add < /tmp/research.json
python3 .windsurf/wsdb.py research-get
```

---

## Special Cases

**User's code uses deprecated pattern:**
Flag explicitly: "Pattern `X` deprecated in v[N]. Current: `Y`."
Ask: "Use current approach or maintain v[N] compatibility?"
Record decision to DB:
```bash
cat > /tmp/dec.json << 'JSON'
{"change_id":null,"decision_type":"DEPRECATION","description":"[pattern choice]","rationale":"[reason]"}
JSON
python3 .windsurf/wsdb.py decision-add < /tmp/dec.json
```

**Official docs ambiguous or missing:**
Check library's GitHub test suite — tests are authoritative intended behavior.
Note ambiguity in Research Summary. Flag implementation as
"based on best available evidence — verify against your environment."

**Multiple libraries involved:**
Research each independently. Pay explicit attention to cross-library compatibility.
Write one `research_findings` row per library.

**User specifies pinned version:**
Research that specific version. Check tagged release on GitHub.
Check if versioned docs exist (docs.example.com/v1.2/).
Note any known CVEs or critical bugs in that version.
