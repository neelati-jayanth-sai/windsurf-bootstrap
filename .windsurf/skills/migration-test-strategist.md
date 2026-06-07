---
name: migration-test-strategist
description: >
  Designs a parallel test migration strategy from DB state — reads the exact execution
  plan from blast-radius-planner and inserts matching TEST steps interleaved with IMPL
  steps. Ensures the test suite is never fully broken at any gate. Triggers for any
  migration involving existing tests: ORM, HTTP client, state library, data layer,
  auth provider, cloud SDK, data format, message queue. Also triggers when blast_radius
  table has rows and execution_steps has only IMPL steps (test steps not yet planned).
  Also triggers on: "tests broken after migration", "update fixtures for new library",
  "test isolation strategy", "how do I test with [new library]".
---

# Migration Test Strategist

Reads the execution plan from DB. Inserts TEST steps interleaved with IMPL steps
so every implementation gate has a corresponding test gate. Suite must pass after
every single step — broken tests are not an acceptable intermediate state.

---

## DB Read (Always First)

```bash
python3 .windsurf/wsdb.py board        # current plan (IMPL steps so far)
python3 .windsurf/wsdb.py map-get      # test layer (match layer_role='TEST')
python3 .windsurf/wsdb.py research-get # library-specific test patterns
```

If `board` shows no IMPL steps: tell user to run blast-radius-planner first.

---

## Phase 0: Test Audit

Using the test layer from codebase_map, produce:

```
## Test Audit

Test runner:      [from codebase_map tech_stack]
Config file:      [from codebase_map path_pattern]
Shared fixtures:  [conftest.py / test helpers location]
Factory library:  [factory_boy / fishery / faker / etc.]
Mock strategy:    [unittest.mock / MSW / pytest-mock / etc.]
Test DB:          [SQLite in-memory / Docker / testcontainers / none]

Baseline: Ask user to run test suite now and record pass count.
  → Command: [pytest tests/ / npm test / go test ./...]
  → This number must never drop below baseline at any gate.

Migration-affected test files:
  [list files that import the OLD library, from grep or user input]
  
Test coupling:
  Tightly coupled (tests old library internals): [files] — HIGH effort
  Loosely coupled (tests behavior via interface): [files] — LOW effort  
  Integration tests hitting old layer:            [files] — MEDIUM effort
```

---

## Phase 1: Isolation Strategy Selection

Choose based on migration type and test coupling. Present options, recommend one.
Record decision to DB after user confirms.

### Strategy A — Local Stand-In
Replace catalog/client/session with lightweight local equivalent for tests.
Production code changes. Tests use local stand-in with same interface.

```python
# Example pattern (adapt to detected stack from codebase_map)
# Production: [real client pointing at real service]
# Tests: [local/in-memory equivalent — same interface, no network]

# Python/PyIceberg example:
@pytest.fixture(scope="session")
def test_catalog(tmp_path_factory):
    warehouse = tmp_path_factory.mktemp("warehouse")
    from pyiceberg.catalog.sql import SqlCatalog
    return SqlCatalog("test", **{
        "uri": f"sqlite:///{warehouse}/catalog.db",
        "warehouse": f"file://{warehouse}",
    })

# Node/Prisma example:
beforeAll(async () => {
  process.env.DATABASE_URL = "file:./test.db";
  await prisma.$connect();
});
```

**Use when:** New library has local/in-memory implementation (PyIceberg SqlCatalog,
DuckDB, SQLite, in-memory Redis, Prisma SQLite, etc.)
**Gap:** Tests don't cover production behavior (network, auth). Compensate with one
integration test against real service in CI.

---

### Strategy B — Interface Shim
Extract thin interface. Both old and new implementations satisfy it.
Tests parametrize over both during migration window — proves behavioral equivalence.

```python
# Python example
from abc import ABC, abstractmethod

class [Entity]Repository(ABC):
    @abstractmethod
    def get_by_id(self, id: str) -> [EntityDTO]: ...

# Tests run against both implementations
@pytest.mark.parametrize("repo_fixture", ["old_repo", "new_repo"])
def test_get_by_id(request, repo_fixture):
    repo = request.getfixturevalue(repo_fixture)
    ...
```

```typescript
// TypeScript example
interface [Entity]Repository {
  getById(id: string): Promise<[Entity]>
}

// Parametrize via test.each or describe.each
```

**Use when:** Migrating between two implementations of the same interface.
**Requirement:** Interface must be extracted BEFORE migration begins (Step T0).

---

### Strategy C — Parallel Test Files
Copy affected test files. Old tests remain. New tests built alongside new implementation.
Delete old files only after all layers migrated.

```
tests/
  [entity]/
    test_[entity]_repository.py        ← old, keep running
    test_[entity]_repository_new.py    ← new, built in parallel
```

**Use when:** Tests are tightly coupled to old library internals.
**Tradeoff:** Temporary duplication.

---

### Strategy D — Mock Boundary
Business logic tests untouched. Replace only the mock target when new library in place.

```python
# Old mock target
with patch("src.repositories.[entity].Session") as mock: ...

# New mock target  
with patch("src.repositories.[entity].load_catalog") as mock: ...
```

**Use when:** Business logic tests don't need changing — only infrastructure mocks do.

---

## Phase 2: Fixture Migration Plan

```
## Fixture Migration

Factory/fixture library: [detected from codebase_map]
Current fixture approach: [ORM factories / JSON files / seed scripts / etc.]

Migration approach:
  [describe specific changes needed for detected stack]
  
Builder function pattern (replaces ORM factories):
  [code example adapted to detected language/framework]

JSON/YAML fixtures:
  [migration script if fixtures are large — generate it]
  
Shared fixtures (conftest.py / test helpers):
  [what changes in shared setup files]
```

---

## Phase 3: Insert TEST Steps into DB

For each IMPL step in the plan, insert a corresponding TEST step with a seq value
as a decimal (e.g. IMPL step 2 → TEST step 2.5, runs after IMPL 2 gate passes).

Add one T0 step before all IMPL steps (interface extraction or test infrastructure setup).

```bash
# TEST steps interleave with IMPL steps. Add them via step-add with explicit seq
# values that slot between existing IMPL seqs. Because seq is an integer with a
# UNIQUE constraint, first RENUMBER: plan IMPL steps as seq 10,20,30... leaving
# gaps, then insert TEST steps at 15,25,35. Simplest: rebuild the whole step list
# in one step-add call with the final interleaved order.

cat > /tmp/teststeps.json << 'JSON'
{"steps":[
  {"change_id":N,"step_label":"T0","step_type":"TEST","layer_name":"Test Infrastructure Setup",
   "files":["tests/conftest.py"],"acceptance_criteria":["Baseline recorded","Stand-in configured","Old tests pass"],
   "cascade_prompt":"CONTEXT: ...
GOAL: set up test stand-in / interface / parallel files"},
  {"change_id":N,"step_label":"T1","step_type":"TEST","layer_name":"[Layer] Tests",
   "files":["tests/[layer]/test_[file].py"],"acceptance_criteria":["N tests pass","No old-lib imports"],
   "cascade_prompt":"CONTEXT: ...
GOAL: migrate tests for this layer"},
  {"change_id":N,"step_label":"T-final","step_type":"TEST","layer_name":"Test Cleanup",
   "files":["all test files"],"acceptance_criteria":["Zero old-lib imports","Full suite green","Coverage >= baseline"],
   "cascade_prompt":"CONTEXT: ...
GOAL: remove old factories, parallel files, old mocks"}
]}
JSON
python3 .windsurf/wsdb.py step-add < /tmp/teststeps.json
python3 .windsurf/wsdb.py board
```

> Ordering note: if you need a TEST step to run immediately after a specific IMPL
> step, pass explicit `seq` values. Leave gaps in IMPL seqs (10,20,30) so TEST
> steps slot between (15,25). The UNIQUE(change_id,seq) constraint guarantees no
> two steps collide on ordering.

---

## Phase 4: Verification Checklist

After all test steps confirmed:

```
## Test Migration Complete

[ ] Zero imports of old library in any test file
[ ] All factories/builders produce correct schema for new library
[ ] Test stand-in confirmed behaviorally equivalent for unit tests
[ ] At least one integration test runs against real service (not just stand-in)
[ ] Test run time within acceptable range
[ ] No unexplained test skips introduced
[ ] CI pipeline runs new test suite successfully
[ ] Coverage >= pre-migration baseline
[ ] No parallel test files or old factory files remaining
```

---

## Common Failure Patterns (by category)

**Empty results from new data layer (e.g. table scan returns nothing)**
→ Data not loaded before query. Add explicit data-load step to fixture setup.

**Schema mismatch between factory output and new library schema**
→ New library enforces schema strictly. Define schema explicitly in builder function,
don't rely on type inference.

**Old factory fails after session/connection removed**
→ Factory depends on removed infrastructure. Switch to plain builder functions
that return dicts or dataclasses.

**Old tests pass, new tests fail on same logic**
→ Behavioral divergence. Use Strategy B (parametrize) to run same test against both —
divergence becomes explicit and localizable.

**Integration tests time out**
→ New library reads all data with no filter. Add filter/limit to all test queries.
Keep test fixtures small (< 100 rows).

**Module-level imports block isolation**
→ Old library imported at top of test file, runs before any fixture. Move imports
inside test functions or conftest fixtures, then replace layer by layer.
