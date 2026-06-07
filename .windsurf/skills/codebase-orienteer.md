---
name: codebase-orienteer
description: >
  Maps an unfamiliar or inherited codebase into a structured layer model that all other
  skills can use. MUST run before any other skill when the project has not been mapped yet
  (no rows in codebase_map table), or when explicitly asked to re-map. Triggers on:
  "I'm new to this codebase", "just inherited this project", "unfamiliar codebase",
  "map the project", "understand the structure", "what does this project look like",
  "orient me", or any blast-radius-planner run that finds codebase_map is empty.
  Also triggers when the user says the layer model is wrong or outdated.
---

# Codebase Orienteer

Maps an unfamiliar project into the layer model that blast-radius-planner, 
migration-test-strategist, and all workflows depend on. Without this map,
every other skill invents file paths. With it, every other skill reads reality.

---

## DB Read (Always First)

```bash
python3 .windsurf/wsdb.py map-get    # [] means not yet mapped
python3 .windsurf/wsdb.py progress   # any active change
```

If `map-get` returns rows: show last mapped date and ask "Re-map from scratch, or update specific
layers only?" Do not proceed without answer.

If `map-get` returns `[]`: proceed with full orientation protocol below.

---

## Phase 0: Ask for Structure Signal

Do not guess the stack. Ask the user to run these commands in their terminal and paste output:

```bash
# Paste the output of ALL of these:

# 1. Top-level structure
find . -maxdepth 2 -type f \( -name "*.toml" -o -name "*.json" -o -name "*.yaml" \
  -o -name "*.lock" -o -name "Makefile" -o -name "Dockerfile" \) \
  ! -path "*/node_modules/*" ! -path "*/.git/*" ! -path "*/__pycache__/*"

# 2. Source directories
find . -maxdepth 4 -type d \
  ! -path "*/node_modules/*" ! -path "*/.git/*" ! -path "*/__pycache__/*" \
  ! -path "*/dist/*" ! -path "*/.venv/*" ! -path "*/build/*"

# 3. Test structure  
find . -type f -name "test_*.py" -o -name "*.test.ts" -o -name "*.spec.ts" \
  -o -name "*.test.js" -o -name "conftest.py" 2>/dev/null | head -40

# 4. Lock file (pick whichever exists)
cat pyproject.toml 2>/dev/null || cat package.json 2>/dev/null || \
  cat go.mod 2>/dev/null || cat pom.xml 2>/dev/null | head -60
```

---

## Phase 1: Stack Detection

From the pasted output, identify:

```
## Stack Detection

Language:        [Python / TypeScript / Go / Java / Ruby / etc.]
Runtime:         [Node 20 / Python 3.11 / Go 1.22 / etc.]
Package manager: [pip+pyproject / npm / yarn / pnpm / go mod / etc.]
Web framework:   [FastAPI / Django / Express / NestJS / Gin / etc.]
ORM/data layer:  [SQLAlchemy / Prisma / GORM / ActiveRecord / none]
Database:        [Postgres / MySQL / SQLite / MongoDB / etc.]
Test runner:     [pytest / jest / vitest / go test / etc.]
Frontend:        [React / Vue / None / etc.]
Infra:           [Docker / Kubernetes / Terraform / etc.]
```

---

## Phase 2: Layer Mapping

Produce the layer map. This becomes the canonical reference for all other skills.
Order layers bottom → top (same order blast-radius-planner executes in).

```
## Codebase Layer Map

Layer 1 — [e.g. Database / Migrations]
  Paths:     [e.g. db/migrations/, alembic/]
  Tech:      [e.g. Alembic, raw SQL]
  Purpose:   Schema definitions and version history
  Key files: [list 2-3 representative files]

Layer 2 — [e.g. Models / ORM]
  Paths:     [e.g. src/models/, app/models/]
  Tech:      [e.g. SQLAlchemy declarative]
  Purpose:   Data model definitions
  Key files: [list 2-3 representative files]

Layer 3 — [e.g. Repository / Data Access]
  Paths:     [e.g. src/repositories/]
  Tech:      [e.g. SQLAlchemy Session]
  Purpose:   All DB queries isolated here
  Key files: [list 2-3 representative files]

Layer 4 — [e.g. Services / Business Logic]
  Paths:     [e.g. src/services/]
  Tech:      [e.g. Plain Python]
  Purpose:   Business rules, orchestration
  Key files: [list 2-3 representative files]

Layer 5 — [e.g. API / Routes]
  Paths:     [e.g. src/api/, src/routers/]
  Tech:      [e.g. FastAPI routers]
  Purpose:   HTTP endpoints, request/response handling
  Key files: [list 2-3 representative files]

Layer 6 — [e.g. Schemas / DTOs / Types]
  Paths:     [e.g. src/schemas/, src/types/]
  Tech:      [e.g. Pydantic v2]
  Purpose:   Request/response shapes, validation
  Key files: [list 2-3 representative files]

Layer 7 — [e.g. Frontend / Consumers]
  Paths:     [e.g. frontend/src/]
  Tech:      [e.g. React + TanStack Query]
  Purpose:   UI and API consumption
  Key files: [list 2-3 representative files]

Layer 8 — [e.g. Tests]
  Paths:     [e.g. tests/, __tests__/]
  Tech:      [e.g. pytest + factory_boy]
  Purpose:   Test suite
  Sub-layers:
    Unit:        tests/unit/
    Integration: tests/integration/
    E2E:         tests/e2e/
  Fixtures:  [e.g. tests/conftest.py, tests/factories/]

Cross-cutting:
  Config:    [e.g. src/config.py, .env]
  Auth:      [e.g. src/middleware/auth.py]
  Logging:   [e.g. src/core/logging.py]
```

---

## Phase 3: Dependency Direction

Explicitly state what depends on what. This is what blast-radius-planner uses to
determine execution order.

```
## Dependency Direction (arrows = "depends on")

Tests → everything
Frontend → API schemas/types
API routes → Services → Repositories → Models → Database
Schemas/DTOs → Models (for shape)
Config → read by all layers
Auth middleware → called by API routes
```

Flag any **circular dependencies** found — they are high-risk blast-radius zones.

---

## Phase 4: Test Topology

```
## Test Topology

Test runner:     [pytest / jest / etc.]
Config file:     [pytest.ini / jest.config.ts / etc.]
Shared fixtures: [conftest.py path / test helpers path]
Factory library: [factory_boy / faker / fishery / etc.]
Mock strategy:   [unittest.mock / MSW / pytest-mock / etc.]
Test DB:         [SQLite in-memory / Docker / testcontainers / none]
Coverage tool:   [coverage.py / c8 / etc.]
CI command:      [e.g. pytest tests/ --cov=src]

Known test gaps: [any areas the user mentions have no tests]
```

---

## Phase 5: Risk Zones

Identify areas that are structurally risky for future changes:

```
## Risk Zones

HIGH — [e.g. User model: imported by 23 files, any change has wide blast radius]
HIGH — [e.g. auth middleware: no unit tests, only tested via E2E]
MEDIUM — [e.g. OrderService: mixes business logic and DB queries, hard to isolate]
LOW — [e.g. email utilities: only used in 2 places, self-contained]
```

---

## DB Write

Write the map to the database. Cascade runs these commands:

```bash
cat > /tmp/map.json << 'JSON'
{"replace": true, "rows": [
  {"layer_name":"Migrations","layer_role":"DB","layer_order":1,"path_pattern":"db/migrations/","tech_stack":"Alembic"},
  {"layer_name":"Models","layer_role":"MODEL","layer_order":2,"path_pattern":"src/models/","tech_stack":"SQLAlchemy"},
  {"layer_name":"Repositories","layer_role":"REPO","layer_order":3,"path_pattern":"src/repositories/","tech_stack":"SQLAlchemy"},
  {"layer_name":"Services","layer_role":"SERVICE","layer_order":4,"path_pattern":"src/services/","tech_stack":"Python"},
  {"layer_name":"API","layer_role":"API","layer_order":5,"path_pattern":"src/api/","tech_stack":"FastAPI"},
  {"layer_name":"Schemas","layer_role":"TYPE","layer_order":6,"path_pattern":"src/schemas/","tech_stack":"Pydantic"},
  {"layer_name":"Frontend","layer_role":"FRONTEND","layer_order":7,"path_pattern":"frontend/src/","tech_stack":"React"},
  {"layer_name":"Tests","layer_role":"TEST","layer_order":8,"path_pattern":"tests/","tech_stack":"pytest"}
]}
JSON
python3 .windsurf/wsdb.py map-add < /tmp/map.json
python3 .windsurf/wsdb.py map-get
```

> `layer_role` MUST be one of: DB / MODEL / REPO / SERVICE / API / TYPE / FRONTEND
> / TEST / CONFIG / AUTH / OTHER. Other skills match on `layer_role`, never on the
> free-text `layer_name`. Use the roles that actually exist in this project; omit
> layers that don't apply, add OTHER rows for anything unusual.

---

## Output to User

```
## Orientation Complete

[N] layers mapped and written to the state DB via wsdb.
Stack: [summary line]
Test runner: [runner]
Risk zones: [count] identified

You can now run any workflow. blast-radius-planner will read this map
automatically instead of guessing file paths.

Next step options:
  → Start a migration:    run workflow: library-migration
  → Make a schema change: run workflow: schema-propagation
  → Build a new feature:  run workflow: new-feature
  → Investigate a bug:    run workflow: bug-investigation
```
