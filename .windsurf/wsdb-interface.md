# wsdb — State DB Interface (shared reference)

All skills read and write project state through `python .windsurf/wsdb.py`.
**Never** use raw `sqlite3 db "..."` shell commands — multi-line Cascade prompts
contain quotes, apostrophes, and newlines that break shell/SQL escaping. The
helper uses parameterized queries and enforces foreign keys on every connection.

## Setup (automatic)
The schema, `hooks/hooks.json`, and `.gitignore` are created automatically on the
first wsdb command you run — no manual setup needed. Running `init` explicitly is
optional and just reports state. Existing DBs from older versions are auto-migrated
(missing columns added) on connect.

## Reads (print JSON to stdout)
```bash
python .windsurf/wsdb.py next        # next actionable step (failed steps first, then pending)
python .windsurf/wsdb.py progress    # done/remaining/failed counts for active change
python .windsurf/wsdb.py board       # full step list with statuses
python .windsurf/wsdb.py health      # session health (step-count based — see note)
python .windsurf/wsdb.py map-get     # codebase layer map
python .windsurf/wsdb.py research-get # recent research findings
```

## Writes (JSON payload via --file PATH — Windows-safe, no shell escaping)
Cascade writes the JSON using its own file-creation tool (NOT a shell heredoc),
then passes the path. This works identically on Windows cmd, PowerShell, and bash:
```
python .windsurf/wsdb.py <command> --file payload.json
```
Use `python` or `python3` — whichever your machine has.

### change-add
```json
{"change_type":"SCHEMA","impact_scope":"SYSTEMIC","change_description":"...","confirmed_by_user":1}
```
Returns `{"change_id": N}`. Also auto-creates a session_log row.

### map-add  (codebase-orienteer)
```json
{"replace": true, "rows": [
  {"layer_name":"Models","layer_role":"MODEL","layer_order":2,"path_pattern":"src/models/","tech_stack":"SQLAlchemy"}
]}
```
`layer_role` is the canonical enum used for matching by other skills:
`DB / MODEL / REPO / SERVICE / API / TYPE / FRONTEND / TEST / CONFIG / AUTH / OTHER`.
`layer_name` is the free-text display name. Skills match on `layer_role`, never on name.

### research-add
```json
{"library":"PyIceberg","version_found":"0.11.1","version_targeted":"0.11.1",
 "source_urls":["..."],"key_findings":["..."],
 "deprecated_patterns":[{"old":"HadoopCatalog","new":"RestCatalog"}],
 "verified_deps":["pyiceberg==0.11.1","pyarrow>=15.0"],"raw_summary":"..."}
```

### blast-add  (one row or {"rows":[...]})
```json
{"rows":[{"change_id":1,"layer_number":1,"layer_name":"Migrations","file_path":"db/migrations/002.py",
          "what_changes":"new migration","required":1,"risk_level":"LOW","confirmed":1}]}
```

### step-add  (one or {"steps":[...]}; seq auto-assigned if omitted)
```json
{"steps":[{"change_id":1,"step_label":"1","step_type":"IMPL","layer_name":"Migrations",
           "files":["db/migrations/002.py"],"acceptance_criteria":["runs clean"],
           "cascade_prompt":"CONTEXT: ...\nGOAL: ..."}]}
```
`step_type`: IMPL / TEST / VERIFY. `seq` is an integer; UNIQUE per change — no collisions.

### Step lifecycle (atomic)
```bash
python .windsurf/wsdb.py step-claim   <step_id>   # only succeeds if pending/failed → prevents two sessions grabbing same step
python .windsurf/wsdb.py step-confirm <step_id>   # gate passed
python .windsurf/wsdb.py step-fail    <step_id> "failure notes"
```

### decision-add
```json
{"change_id":1,"step_id":null,"decision_type":"STRATEGY","description":"...","rationale":"..."}
```

### Close-out
```bash
python .windsurf/wsdb.py change-complete <change_id>
python .windsurf/wsdb.py change-abandon  <change_id>   # cascades delete of its steps/blast/decisions
```

## Resume after any break
```bash
python .windsurf/wsdb.py progress && python .windsurf/wsdb.py next
```
Paste the `cascade_prompt` from `next` into Cascade. No context reconstruction.

## Honest note on `health`
`health` counts **steps touched in this session**, not chat messages — a skill
can't see Cascade's true message count. Treat GREEN/AMBER/RED as "how much work
this session has done" (AMBER ≥ 7 steps, RED ≥ 12). It's a proxy reminder to
start a fresh Cascade session, not an exact message gauge. Still pair it with
your own eye on Windsurf's context indicator (start fresh above ~60%).
