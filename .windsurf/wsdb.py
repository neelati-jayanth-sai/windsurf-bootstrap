#!/usr/bin/env python
"""
wsdb.py - Windsurf State DB + Hook Runner. Windows-safe.

Cross-platform rules:
  * No heredocs, no /tmp, no shell quoting of data. Payloads pass as FILE PATHS.
    Cascade writes JSON with its own file-creation tool, then runs:
        python .windsurf/wsdb.py step-add --file payload.json
  * Works with `python` or `python3`. Uses the launching interpreter for sub-calls.
  * All paths via pathlib; forward slashes are fine in Python on Windows.

READS (print JSON):
  init  next  progress  board  health  map-get  research-get  hooks-show

WRITES (payload via --file PATH, never inline):
  change-add  map-add  research-add  blast-add  step-add  decision-add

STEP LIFECYCLE:
  step-claim <id>   step-confirm <id>
  step-fail <id> --error "msg"   (or --file err.json with {"error": "..."})
  check-escalate <id>

ENFORCEMENT GATES (exit 0 = pass, exit 2 = blocked):
  preflight
  require-research <library>
  require-confirmed-blast <change_id>
  require-clean-refs <old_entity>

HOOK RUNNER:
  run-hook <event> [--step <id>] [--change <id>] [--library <name>] [--old-entity <name>]

CLOSE-OUT:
  change-complete <change_id>   change-abandon <change_id>
"""
import sqlite3, sys, json, os, subprocess, argparse
from pathlib import Path

ROOT = Path(os.environ.get("WSDB_ROOT", ".windsurf"))
DB_PATH = Path(os.environ.get("WSDB_PATH", str(ROOT / "state.db")))
HOOKS_PATH = ROOT / "hooks" / "hooks.json"
SCHEMA_VERSION = 3
PY = sys.executable or "python"


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(DB_PATH), timeout=30)
    c.execute("PRAGMA foreign_keys=ON;")
    c.execute("PRAGMA journal_mode=WAL;")
    c.execute("PRAGMA busy_timeout=30000;")
    c.row_factory = sqlite3.Row
    return c


def out(obj):
    print(json.dumps(obj, indent=2, default=str))


def load_file(path):
    if not path:
        sys.exit("ERROR: this command needs --file PATH (a JSON file Cascade writes)")
    p = Path(path)
    if not p.exists():
        sys.exit("ERROR: payload file not found: " + str(path))
    return json.loads(p.read_text(encoding="utf-8"))


SCHEMA = r"""
CREATE TABLE IF NOT EXISTS schema_meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS research_findings (
    id INTEGER PRIMARY KEY, library TEXT NOT NULL, version_found TEXT,
    version_targeted TEXT, source_urls TEXT, key_findings TEXT,
    deprecated_patterns TEXT, verified_deps TEXT, raw_summary TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS change_registry (
    id INTEGER PRIMARY KEY, change_type TEXT NOT NULL, impact_scope TEXT NOT NULL,
    change_description TEXT NOT NULL, confirmed_by_user INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP);
CREATE TABLE IF NOT EXISTS blast_radius (
    id INTEGER PRIMARY KEY,
    change_id INTEGER NOT NULL REFERENCES change_registry(id) ON DELETE CASCADE,
    layer_number INTEGER NOT NULL, layer_name TEXT NOT NULL, file_path TEXT NOT NULL,
    what_changes TEXT NOT NULL, required INTEGER DEFAULT 1,
    risk_level TEXT DEFAULT 'MEDIUM', confirmed INTEGER DEFAULT 0, notes TEXT);
CREATE TABLE IF NOT EXISTS execution_steps (
    id INTEGER PRIMARY KEY,
    change_id INTEGER NOT NULL REFERENCES change_registry(id) ON DELETE CASCADE,
    seq INTEGER NOT NULL, step_label TEXT NOT NULL, step_type TEXT NOT NULL,
    layer_name TEXT NOT NULL, layer_role TEXT DEFAULT 'OTHER',
    files TEXT NOT NULL, acceptance_criteria TEXT NOT NULL, cascade_prompt TEXT,
    status TEXT DEFAULT 'pending', gate_passed INTEGER DEFAULT 0,
    fail_count INTEGER DEFAULT 0, last_error TEXT, failure_notes TEXT,
    started_at TIMESTAMP, completed_at TIMESTAMP, UNIQUE(change_id, seq));
CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY,
    change_id INTEGER REFERENCES change_registry(id) ON DELETE CASCADE,
    step_id INTEGER REFERENCES execution_steps(id) ON DELETE SET NULL,
    decision_type TEXT NOT NULL, description TEXT NOT NULL, rationale TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS codebase_map (
    id INTEGER PRIMARY KEY, layer_name TEXT NOT NULL, layer_role TEXT NOT NULL,
    layer_order INTEGER NOT NULL, path_pattern TEXT NOT NULL, tech_stack TEXT,
    notes TEXT, mapped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS session_log (
    id INTEGER PRIMARY KEY,
    change_id INTEGER REFERENCES change_registry(id) ON DELETE CASCADE,
    cascade_session_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active_step_id INTEGER REFERENCES execution_steps(id) ON DELETE SET NULL,
    steps_touched INTEGER DEFAULT 0, health TEXT DEFAULT 'GREEN', notes TEXT);

CREATE VIEW IF NOT EXISTS v_next_step AS
SELECT es.id AS step_id, es.seq, es.step_label, es.step_type, es.layer_name,
       es.layer_role, es.files, es.acceptance_criteria, es.cascade_prompt,
       es.status, es.fail_count, es.last_error, cr.change_description
FROM execution_steps es JOIN change_registry cr ON cr.id = es.change_id
WHERE cr.status='active' AND es.status IN ('escalated','failed','pending')
ORDER BY (es.status='escalated') DESC, (es.status='failed') DESC, es.seq LIMIT 1;

CREATE VIEW IF NOT EXISTS v_current_progress AS
SELECT cr.id AS change_id, cr.change_type, cr.impact_scope, cr.change_description,
       COUNT(es.id) AS total_steps,
       SUM(es.status='confirmed') AS steps_done,
       SUM(es.status='in_progress') AS steps_active,
       SUM(es.status='pending') AS steps_remaining,
       SUM(es.status='failed') AS steps_failed,
       SUM(es.status='escalated') AS steps_escalated
FROM change_registry cr LEFT JOIN execution_steps es ON es.change_id = cr.id
WHERE cr.status='active' GROUP BY cr.id;

CREATE VIEW IF NOT EXISTS v_step_board AS
SELECT es.seq, es.step_label, es.step_type, es.layer_name, es.status,
       es.fail_count, es.gate_passed, es.failure_notes
FROM execution_steps es JOIN change_registry cr ON cr.id = es.change_id
WHERE cr.status='active' ORDER BY es.seq;
"""

DEFAULT_HOOKS = {
    "test_command": "pytest -x --tb=short",
    "layer_test_commands": {
        "MODEL": "pytest tests/unit -x --tb=short",
        "REPO": "pytest tests/unit -x --tb=short",
        "SERVICE": "pytest tests/unit -x --tb=short",
        "API": "pytest tests/integration -x --tb=short",
        "TYPE": "pytest tests/unit -x --tb=short",
        "FRONTEND": "npm test -- --watchAll=false",
        "DB": "pytest tests/unit -x --tb=short",
        "AUTH": "pytest tests/integration -x --tb=short",
        "CONFIG": "pytest -x --tb=short"
    },
    "escalation": {"fail_threshold": 3, "max_retries_after_research": 1},
    "hooks": {
        "on_session_start": [
            {"command": "{PY} .windsurf/wsdb.py preflight", "when": "always", "on_fail": "block"}
        ],
        "before_implement": [
            {"command": "{PY} .windsurf/wsdb.py require-confirmed-blast {change_id}", "when": "always", "on_fail": "block"},
            {"command": "{PY} .windsurf/wsdb.py require-research {library}", "when": "change_type==DEPENDENCY", "on_fail": "block"}
        ],
        "on_step_complete": [
            {"command": "{layer_test_command}", "when": "always", "on_fail": "escalate"}
        ],
        "on_gate_pass": [
            {"command": "git add -A", "when": "always", "on_fail": "warn"},
            {"command": "git commit -m \"wsdb step {step_label}: {layer_name}\"", "when": "always", "on_fail": "warn"}
        ],
        "before_change_complete": [
            {"command": "{PY} .windsurf/wsdb.py require-clean-refs {old_entity}", "when": "has_old_entity", "on_fail": "block"}
        ]
    }
}


def cmd_init(conn, a):
    conn.executescript(SCHEMA)
    conn.execute("INSERT OR REPLACE INTO schema_meta(key,value) VALUES('version',?)", (str(SCHEMA_VERSION),))
    conn.commit()
    HOOKS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not HOOKS_PATH.exists():
        HOOKS_PATH.write_text(json.dumps(DEFAULT_HOOKS, indent=2), encoding="utf-8")
    # Keep the runtime DB out of git so it never dirties the tree / blocks preflight.
    gi = ROOT / ".gitignore"
    if not gi.exists():
        gi.write_text("state.db\nstate.db-wal\nstate.db-shm\n", encoding="utf-8")
    out({"ok": True, "schema_version": SCHEMA_VERSION, "db": str(DB_PATH), "hooks": str(HOOKS_PATH)})


def cmd_next(conn, a):
    r = conn.execute("SELECT * FROM v_next_step").fetchone()
    out(dict(r) if r else {"next": None, "message": "No actionable steps."})


def cmd_progress(conn, a):
    r = conn.execute("SELECT * FROM v_current_progress").fetchone()
    out(dict(r) if r else {"message": "No active change."})


def cmd_board(conn, a):
    out([dict(r) for r in conn.execute("SELECT * FROM v_step_board")])


def cmd_health(conn, a):
    r = conn.execute("SELECT health,steps_touched,cascade_session_start FROM session_log ORDER BY id DESC LIMIT 1").fetchone()
    out(dict(r) if r else {"message": "No session."})


def cmd_map_get(conn, a):
    out([dict(r) for r in conn.execute("SELECT layer_order,layer_name,layer_role,path_pattern,tech_stack FROM codebase_map ORDER BY layer_order")])


def cmd_research_get(conn, a):
    out([dict(r) for r in conn.execute("SELECT id,library,version_found,version_targeted,key_findings,deprecated_patterns,verified_deps,created_at FROM research_findings ORDER BY created_at DESC LIMIT 10")])


def cmd_hooks_show(conn, a):
    out(json.loads(HOOKS_PATH.read_text(encoding="utf-8")) if HOOKS_PATH.exists() else {"message": "No hooks.json — run init."})


def cmd_change_add(conn, a):
    p = load_file(a.file)
    cur = conn.execute("INSERT INTO change_registry (change_type,impact_scope,change_description,confirmed_by_user) VALUES (?,?,?,?)",
                       (p["change_type"], p["impact_scope"], p["change_description"], int(p.get("confirmed_by_user", 0))))
    cid = cur.lastrowid
    conn.execute("INSERT INTO session_log (change_id,health) VALUES (?,'GREEN')", (cid,))
    conn.commit()
    out({"ok": True, "change_id": cid})


def cmd_map_add(conn, a):
    p = load_file(a.file)
    rows = p.get("rows", [p])
    if p.get("replace"):
        conn.execute("DELETE FROM codebase_map")
    for r in rows:
        conn.execute("INSERT INTO codebase_map (layer_name,layer_role,layer_order,path_pattern,tech_stack,notes) VALUES (?,?,?,?,?,?)",
                     (r["layer_name"], r.get("layer_role", "OTHER"), r["layer_order"], r["path_pattern"], r.get("tech_stack"), r.get("notes")))
    conn.commit()
    out({"ok": True, "layers": len(rows)})


def cmd_research_add(conn, a):
    p = load_file(a.file)
    conn.execute("INSERT INTO research_findings (library,version_found,version_targeted,source_urls,key_findings,deprecated_patterns,verified_deps,raw_summary) VALUES (?,?,?,?,?,?,?,?)",
                 (p["library"], p.get("version_found"), p.get("version_targeted"),
                  json.dumps(p.get("source_urls", [])), json.dumps(p.get("key_findings", [])),
                  json.dumps(p.get("deprecated_patterns", [])), json.dumps(p.get("verified_deps", [])), p.get("raw_summary", "")))
    conn.commit()
    out({"ok": True, "library": p["library"]})


def cmd_blast_add(conn, a):
    p = load_file(a.file)
    rows = p.get("rows", [p])
    for r in rows:
        conn.execute("INSERT INTO blast_radius (change_id,layer_number,layer_name,file_path,what_changes,required,risk_level,confirmed,notes) VALUES (?,?,?,?,?,?,?,?,?)",
                     (r["change_id"], r["layer_number"], r["layer_name"], r["file_path"], r["what_changes"],
                      int(r.get("required", 1)), r.get("risk_level", "MEDIUM"), int(r.get("confirmed", 0)), r.get("notes")))
    conn.commit()
    out({"ok": True, "inserted": len(rows)})


def cmd_step_add(conn, a):
    p = load_file(a.file)
    steps = p.get("steps", [p])
    res = []
    for s in steps:
        cid = s["change_id"]
        seq = s.get("seq") or conn.execute("SELECT COALESCE(MAX(seq),0)+1 AS n FROM execution_steps WHERE change_id=?", (cid,)).fetchone()["n"]
        cur = conn.execute("INSERT INTO execution_steps (change_id,seq,step_label,step_type,layer_name,layer_role,files,acceptance_criteria,cascade_prompt,status) VALUES (?,?,?,?,?,?,?,?,?,?)",
                           (cid, seq, s.get("step_label", str(seq)), s["step_type"], s["layer_name"], s.get("layer_role", "OTHER"),
                            json.dumps(s.get("files", [])), json.dumps(s.get("acceptance_criteria", [])), s.get("cascade_prompt", ""), s.get("status", "pending")))
        res.append({"step_id": cur.lastrowid, "seq": seq})
    conn.commit()
    out({"ok": True, "steps": res})


def cmd_decision_add(conn, a):
    p = load_file(a.file)
    conn.execute("INSERT INTO decisions (change_id,step_id,decision_type,description,rationale) VALUES (?,?,?,?,?)",
                 (p.get("change_id"), p.get("step_id"), p["decision_type"], p["description"], p.get("rationale")))
    conn.commit()
    out({"ok": True})


def cmd_step_claim(conn, a):
    sid = int(a.args[0])
    cur = conn.execute("UPDATE execution_steps SET status='in_progress', started_at=CURRENT_TIMESTAMP WHERE id=? AND status IN ('pending','failed','escalated')", (sid,))
    conn.commit()
    if cur.rowcount == 0:
        r = conn.execute("SELECT status FROM execution_steps WHERE id=?", (sid,)).fetchone()
        out({"ok": False, "reason": "already claimed or not claimable", "current_status": r["status"] if r else "not found"})
        return
    conn.execute("UPDATE session_log SET last_active_step_id=?, steps_touched=steps_touched+1, health=CASE WHEN steps_touched>=12 THEN 'RED' WHEN steps_touched>=7 THEN 'AMBER' ELSE 'GREEN' END WHERE id=(SELECT MAX(id) FROM session_log)", (sid,))
    conn.commit()
    out({"ok": True, "claimed": sid})


def cmd_step_confirm(conn, a):
    sid = int(a.args[0])
    conn.execute("UPDATE execution_steps SET status='confirmed', gate_passed=1, failure_notes=NULL, completed_at=CURRENT_TIMESTAMP WHERE id=?", (sid,))
    conn.commit()
    out({"ok": True, "confirmed": sid})


def cmd_step_fail(conn, a):
    sid = int(a.args[0])
    err = a.error
    if a.file:
        err = load_file(a.file).get("error", err)
    conn.execute("UPDATE execution_steps SET status='failed', fail_count=fail_count+1, last_error=?, failure_notes=? WHERE id=?", (err, err, sid))
    conn.commit()
    r = conn.execute("SELECT fail_count FROM execution_steps WHERE id=?", (sid,)).fetchone()
    out({"ok": True, "failed": sid, "fail_count": r["fail_count"], "error": err})


def cmd_check_escalate(conn, a):
    sid = int(a.args[0])
    hooks = json.loads(HOOKS_PATH.read_text(encoding="utf-8")) if HOOKS_PATH.exists() else DEFAULT_HOOKS
    threshold = hooks.get("escalation", {}).get("fail_threshold", 3)
    r = conn.execute("SELECT fail_count,last_error,layer_name FROM execution_steps WHERE id=?", (sid,)).fetchone()
    if not r:
        out({"ok": False, "reason": "step not found"})
        return
    if r["fail_count"] >= threshold:
        conn.execute("UPDATE execution_steps SET status='escalated' WHERE id=?", (sid,))
        conn.commit()
        out({"ok": True, "escalate": True, "fail_count": r["fail_count"], "threshold": threshold,
             "action": "Run research-first-coder with this error, then retry once.", "last_error": r["last_error"]})
    else:
        out({"ok": True, "escalate": False, "fail_count": r["fail_count"], "threshold": threshold,
             "action": "Diagnose and retry with minimum change."})


def cmd_preflight(conn, a):
    problems = []
    try:
        st = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, timeout=15)
        if st.returncode != 0:
            problems.append("git not available or not a repo")
        else:
            # Ignore the state dir itself — its DB/WAL files are not project code.
            dirty = [ln for ln in st.stdout.splitlines()
                     if ln.strip() and ".windsurf/" not in ln]
            if dirty:
                problems.append("git working tree is dirty - commit or stash before starting "
                                "(" + str(len(dirty)) + " files)")
    except Exception as e:
        problems.append("git check failed: " + str(e))
    n = conn.execute("SELECT COUNT(*) c FROM codebase_map").fetchone()["c"]
    if n == 0:
        problems.append("codebase not mapped - run codebase-orienteer first")
    z = conn.execute("SELECT id,change_description FROM change_registry WHERE status='active'").fetchone()
    if z:
        problems.append("active change #" + str(z["id"]) + " already in progress - finish or abandon it")
    if problems:
        out({"ok": False, "blocked": True, "problems": problems})
        sys.exit(2)
    out({"ok": True, "blocked": False})


def cmd_require_research(conn, a):
    lib = a.args[0] if a.args else None
    if not lib or lib == "None":
        out({"ok": True, "skipped": "no library specified"})
        return
    r = conn.execute("SELECT id,created_at FROM research_findings WHERE lower(library)=lower(?) AND created_at >= datetime('now','-7 days') ORDER BY created_at DESC LIMIT 1", (lib,)).fetchone()
    if r:
        out({"ok": True, "blocked": False, "research_id": r["id"]})
    else:
        out({"ok": False, "blocked": True, "reason": "no recent research for '" + lib + "' - run research-first-coder first"})
        sys.exit(2)


def cmd_require_confirmed_blast(conn, a):
    cid = int(a.args[0])
    r = conn.execute("SELECT confirmed_by_user FROM change_registry WHERE id=?", (cid,)).fetchone()
    if r and r["confirmed_by_user"] == 1:
        out({"ok": True, "blocked": False})
    else:
        out({"ok": False, "blocked": True, "reason": "blast radius not confirmed - confirm the audit first"})
        sys.exit(2)


def cmd_require_clean_refs(conn, a):
    entity = a.args[0] if a.args else None
    if not entity or entity == "None":
        out({"ok": True, "skipped": "no entity"})
        return
    hits = []
    exts = (".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".java", ".rb")
    skip = {".git", "node_modules", "__pycache__", ".venv", "dist", "build", ".windsurf"}
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in skip]
        for fn in files:
            if fn.endswith(exts):
                fp = Path(root) / fn
                try:
                    if entity in fp.read_text(encoding="utf-8", errors="ignore"):
                        hits.append(str(fp))
                except Exception:
                    pass
    if hits:
        out({"ok": False, "blocked": True, "reason": "'" + entity + "' still referenced", "files": hits[:20], "count": len(hits)})
        sys.exit(2)
    out({"ok": True, "blocked": False})


def eval_when(when, ctx):
    if when in (None, "", "always"):
        return True
    if when == "has_old_entity":
        return bool(ctx.get("old_entity") and ctx.get("old_entity") != "None")
    if when == "has_library":
        return bool(ctx.get("library") and ctx.get("library") != "None")
    if "==" in when:
        k, v = [x.strip() for x in when.split("==", 1)]
        return str(ctx.get(k, "")).upper() == v.upper()
    return True


def cmd_run_hook(conn, a):
    event = a.args[0]
    hooks = json.loads(HOOKS_PATH.read_text(encoding="utf-8")) if HOOKS_PATH.exists() else DEFAULT_HOOKS
    entries = hooks.get("hooks", {}).get(event, [])
    ctx = {"PY": PY, "step_id": a.step, "change_id": a.change, "library": a.library, "old_entity": a.old_entity}
    step = None
    if a.step:
        step = conn.execute("SELECT * FROM execution_steps WHERE id=?", (a.step,)).fetchone()
        if step:
            ctx["step_label"] = step["step_label"]
            ctx["layer_name"] = step["layer_name"]
            ctx["layer_role"] = step["layer_role"]
            ctx["change_id"] = ctx["change_id"] or step["change_id"]
    if ctx.get("change_id"):
        cr = conn.execute("SELECT change_type FROM change_registry WHERE id=?", (ctx["change_id"],)).fetchone()
        if cr:
            ctx["change_type"] = cr["change_type"]
    if step:
        ctx["layer_test_command"] = hooks.get("layer_test_commands", {}).get(step["layer_role"], hooks.get("test_command", ""))
    else:
        ctx["layer_test_command"] = hooks.get("test_command", "")

    results = []
    for entry in entries:
        when = entry.get("when", "always")
        if not eval_when(when, ctx):
            results.append({"command": entry.get("command"), "skipped": "when=" + when + " not met"})
            continue
        cmd = entry.get("command", "")
        for k, v in ctx.items():
            cmd = cmd.replace("{" + k + "}", str(v) if v is not None else "")
        on_fail = entry.get("on_fail", "warn")
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=600)
            ok = (r.returncode == 0)
            res = {"command": cmd, "returncode": r.returncode, "on_fail": on_fail,
                   "stdout_tail": r.stdout[-800:], "stderr_tail": r.stderr[-400:]}
            if not ok:
                res["action"] = on_fail
            results.append(res)
            if not ok and on_fail == "block":
                out({"event": event, "blocked": True, "results": results})
                sys.exit(2)
            if not ok and on_fail == "escalate":
                out({"event": event, "escalate": True, "results": results})
                return
        except subprocess.TimeoutExpired:
            results.append({"command": cmd, "error": "timeout", "on_fail": on_fail})
            if on_fail == "block":
                out({"event": event, "blocked": True, "results": results})
                sys.exit(2)
    out({"event": event, "blocked": False, "results": results})


def cmd_change_complete(conn, a):
    conn.execute("UPDATE change_registry SET status='complete', completed_at=CURRENT_TIMESTAMP WHERE id=?", (int(a.args[0]),))
    conn.commit()
    out({"ok": True, "completed": int(a.args[0])})


def cmd_change_abandon(conn, a):
    conn.execute("UPDATE change_registry SET status='abandoned' WHERE id=?", (int(a.args[0]),))
    conn.commit()
    out({"ok": True, "abandoned": int(a.args[0])})


COMMANDS = {
    "init": cmd_init, "next": cmd_next, "progress": cmd_progress, "board": cmd_board,
    "health": cmd_health, "map-get": cmd_map_get, "research-get": cmd_research_get,
    "hooks-show": cmd_hooks_show, "change-add": cmd_change_add, "map-add": cmd_map_add,
    "research-add": cmd_research_add, "blast-add": cmd_blast_add, "step-add": cmd_step_add,
    "decision-add": cmd_decision_add, "step-claim": cmd_step_claim, "step-confirm": cmd_step_confirm,
    "step-fail": cmd_step_fail, "check-escalate": cmd_check_escalate, "preflight": cmd_preflight,
    "require-research": cmd_require_research, "require-confirmed-blast": cmd_require_confirmed_blast,
    "require-clean-refs": cmd_require_clean_refs, "run-hook": cmd_run_hook,
    "change-complete": cmd_change_complete, "change-abandon": cmd_change_abandon,
}


def main():
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("command")
    ap.add_argument("args", nargs="*")
    ap.add_argument("--file")
    ap.add_argument("--error")
    ap.add_argument("--step", type=int)
    ap.add_argument("--change", type=int)
    ap.add_argument("--library")
    ap.add_argument("--old-entity", dest="old_entity")
    a = ap.parse_args()
    if a.command not in COMMANDS:
        print(__doc__)
        print("Commands:", ", ".join(sorted(COMMANDS)))
        sys.exit(1)
    conn = connect()
    try:
        COMMANDS[a.command](conn, a)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
