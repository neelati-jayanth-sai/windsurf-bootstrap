---
name: workflow-schema-propagation
description: >
  Orchestrates any database schema or data model change across all affected layers.
  Activates for: "new column", "rename field", "drop table", "change column type",
  "add relation", "modify model", "update schema", or any change that starts at the
  database layer and must propagate upward through ORM, service, API, types, frontend,
  and tests. Does NOT require research step unless the ORM/migration library itself is
  involved. Skips migration-test-strategist (uses blast-radius test layer instead).
---

# Workflow: Schema Propagation

Sequences: blast-radius-planner → windsurf-prompt-maximizer (per step) → verification.
Skips research (schema changes are internal). Uses blast-radius test layers directly.

---

## Step 0: Pre-Flight Check

```bash
# Verify DB initialized and codebase mapped
python3 .windsurf/wsdb.py map-get
# → If 0: run codebase-orienteer first

# Clean git state
echo "Confirm clean working tree: git status"
echo "Then: git commit -m 'baseline before schema change: [description]'"
```

---

## Step 1: Blast Radius Audit

**Activate:** `blast-radius-planner` with change_type = SCHEMA

Provide:
- Exact column/field names being added/changed/removed
- Their types
- Whether they are nullable or have defaults (critical for migration safety)

The audit must find ALL of these (verify each exists in your codebase):
```
Migration file          ← always required
ORM model               ← always required
Repository queries      ← any raw query selecting * will miss new columns
Service layer           ← if it constructs objects directly
DTO / serializer        ← response shape must include new fields
Type definitions        ← TypeScript interfaces, Pydantic schemas
API route handlers      ← request validation if field is an input
Frontend consumers      ← components rendering or sending the field
Validation schemas      ← Zod, Joi, Yup, Pydantic validators
Test fixtures/factories ← must produce valid objects with new fields
E2E tests               ← may assert on specific field values
Seed files              ← dev/staging data must include new fields
```

Gate: full audit confirmed, IMPL steps + TEST steps in DB.

---

## Step 2: Migration Safety Check

Before writing the migration file, ask:

```
Is the column nullable or does it have a DEFAULT?
  → YES: safe to deploy to existing data, no backfill needed
  → NO (NOT NULL, no default): migration will FAIL on non-empty table
     Solution: add as nullable first, backfill, then add NOT NULL constraint

Is this a rename (not an add)?
  → Rename = effectively drop + add = data loss risk
  → Safe approach: add new column, dual-write, backfill, drop old column
  → Ask: is dual-write needed or is this a greenfield table?

Is this a type change?
  → May require explicit CAST in migration
  → Test migration against a copy of production data volume if possible
```

Record decisions:
```bash
cat > /tmp/dec.json << 'JSON'
{"change_id":N,"decision_type":"STRATEGY","description":"[what]","rationale":"[why]"}
JSON
python3 .windsurf/wsdb.py decision-add < /tmp/dec.json
```

---

## Step 3: Execute Steps

**Activate:** `windsurf-prompt-maximizer` per step

Strict execution order for schema changes:
```
Step 1: Migration file          ← write and run migration
Step 2: ORM model               ← add field definitions
Step 3: Repository layer        ← update queries that need new fields
Step 4: Service layer           ← update object construction if needed
Step 5: DTO / serializer        ← add to response shape
Step 6: Type definitions        ← update interfaces/Pydantic schemas
Step 7: API validation          ← update request validators if input field
Step 8: Frontend                ← consume new field
Step 9: Test fixtures           ← update factories/seeds
Step 10: Test assertions        ← update tests asserting on field values
Step 11: Seed/dev data          ← update seed files
```

After migration step (Step 1), always verify:
```bash
# Check migration ran without errors
# Check column exists in DB
sqlite3 [your.db] ".schema [table_name]"
# or psql: \d table_name
```

Between every step: `git commit -m "schema: [field_name] — step [N] [layer]"`

---

## Step 4: Consistency Verification

```bash
# Search for references to old field name (if renamed)
grep -r "[old_field_name]" . --include="*.py" --include="*.ts" -l

# Type check
# Test suite — must pass fully

# Check no "select *" queries that would silently miss new column
grep -r "SELECT \*" . --include="*.py" --include="*.ts" -l
```

```bash
python3 .windsurf/wsdb.py change-complete <change_id>
```
