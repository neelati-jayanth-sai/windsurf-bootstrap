#!/usr/bin/env python3
"""
wsdb — Windsurf State DB helper.
The ONLY safe way for skills to read/write .windsurf/state.db.

Why this exists: skills run inside Cascade, which executes shell commands.
Passing multi-line Cascade prompts (full of quotes, apostrophes, newlines,
and JSON) through inline `sqlite3 db "INSERT...'$text'"` is fundamentally
broken — the escaping fails on virtually every real prompt. This script
takes values as argv or stdin, uses parameterized queries (no escaping
needed), and enforces foreign keys on every connection.

Usage (Cascade calls these):
  python3 .windsurf/wsdb.py init
  python3 .windsurf/wsdb.py next
  python3 .windsurf/wsdb.py progress
  python3 .windsurf/wsdb.py board
  python3 .windsurf/wsdb.py health

  # Writes read the payload from stdin as JSON — no shell escaping issues:
  echo '{...json...}' | python3 .windsurf/wsdb.py research-add
  echo '{...json...}' | python3 .windsurf/wsdb.py change-add
  echo '{...json...}' | python3 .windsurf/wsdb.py blast-add
  echo '{...json...}' | python3 .windsurf/wsdb.py step-add
  python3 .windsurf/wsdb.py step-claim <step_id>
  python3 .windsurf/wsdb.py step-confirm <step_id>
  python3 .windsurf/wsdb.py step-fail <step_id> "failure notes"
  python3 .windsurf/wsdb.py change-complete <change_id>
  python3 .windsurf/wsdb.py change-abandon <change_id>

For writes, prefer writing the JSON payload to a temp file and piping it:
  python3 .windsurf/wsdb.py step-add < payload.json
This avoids ALL shell-escaping problems because the data never touches argv.
"""
import sqlite3, sys, json, os, pathlib

DB_PATH = os.environ.get("WSDB_PATH", ".windsurf/state.db")
SCHEMA_VERSION = 2


def connect():
    pathlib.Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA foreign_keys=ON;")   # MUST be per-connection
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=30000;") # handle concurrent sessions
    conn.row_factory = sqlite3.Row
    return conn


def out(obj):
    print(json.dumps(obj, indent=2, default=str))


def read_payload():
    """Read JSON from stdin (preferred — no escaping) or fail clearly."""
    data = sys.stdin.read().strip()
    if not data:
        sys.exit("ERROR: expected JSON payload on stdin")
    return json.loads(data)


SCHEMA = r"""
CREATE TABLE IF NOT EXISTS schema_meta (
    key TEXT PRIMARY KEY, value TEXT
);

CREATE TABLE IF NOT EXISTS research_findings (
    id INTEGER PRIMARY KEY, library TEXT NOT NULL,
    version_found TEXT, version_targeted TEXT, source_urls TEXT,
    key_findings TEXT, deprecated_patterns TEXT, verified_deps TEXT,
    raw_summary TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS change_registry (
    id INTEGER PRIMARY KEY, change_type TEXT NOT NULL,
    impact_scope TEXT NOT NULL, change_description TEXT NOT NULL,
    confirmed_by_user INTEGER DEFAULT 0, status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, completed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS blast_radius (
    id INTEGER PRIMARY KEY,
    change_id INTEGER NOT NULL REFERENCES change_registry(id) ON DELETE CASCADE,
    layer_number INTEGER NOT NULL, layer_name TEXT NOT NULL,
    file_path TEXT NOT NULL, what_changes TEXT NOT NULL,
    required INTEGER DEFAULT 1, risk_level TEXT DEFAULT 'MEDIUM',
    confirmed INTEGER DEFAULT 0, notes TEXT
);

CREATE TABLE IF NOT EXISTS execution_steps (
    id INTEGER PRIMARY KEY,
    change_id INTEGER NOT NULL REFERENCES change_registry(id) ON DELETE CASCADE,
    seq INTEGER NOT NULL,            -- explicit ordering, no float collisions
    step_label TEXT NOT NULL,        -- display label e.g. "2 / T2"
    step_type TEXT NOT NULL,         -- IMPL/TEST/VERIFY
    layer_name TEXT NOT NULL,
    files TEXT NOT NULL, acceptance_criteria TEXT NOT NULL,
    cascade_prompt TEXT,
    status TEXT DEFAULT 'pending',   -- pending/in_progress/confirmed/failed
    gate_passed INTEGER DEFAULT 0, failure_notes TEXT,
    started_at TIMESTAMP, completed_at TIMESTAMP,
    UNIQUE(change_id, seq)           -- prevents ordering collisions
);

CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY,
    change_id INTEGER REFERENCES change_registry(id) ON DELETE CASCADE,
    step_id INTEGER REFERENCES execution_steps(id) ON DELETE SET NULL,
    decision_type TEXT NOT NULL, description TEXT NOT NULL,
    rationale TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS codebase_map (
    id INTEGER PRIMARY KEY, layer_name TEXT NOT NULL,
    layer_role TEXT NOT NULL,        -- canonical: DB/MODEL/REPO/SERVICE/API/TYPE/FRONTEND/TEST/CONFIG/AUTH/OTHER
    layer_order INTEGER NOT NULL, path_pattern TEXT NOT NULL,
    tech_stack TEXT, notes TEXT, mapped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS session_log (
    id INTEGER PRIMARY KEY,
    change_id INTEGER REFERENCES change_registry(id) ON DELETE CASCADE,
    cascade_session_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active_step_id INTEGER REFERENCES execution_steps(id) ON DELETE SET NULL,
    steps_touched INTEGER DEFAULT 0,  -- honest name: counts skill-steps, not msgs
    health TEXT DEFAULT 'GREEN', notes TEXT
);

-- Next actionable step: FAILED steps surface FIRST (must resolve before moving on),
-- then pending. in_progress is excluded (claimed by another session).
CREATE VIEW IF NOT EXISTS v_next_step AS
SELECT es.id AS step_id, es.seq, es.step_label, es.step_type, es.layer_name,
       es.files, es.acceptance_criteria, es.cascade_prompt, es.status,
       cr.change_description
FROM execution_steps es
JOIN change_registry cr ON cr.id = es.change_id
WHERE cr.status = 'active' AND es.status IN ('failed','pending')
ORDER BY (es.status='failed') DESC, es.seq
LIMIT 1;

CREATE VIEW IF NOT EXISTS v_current_progress AS
SELECT cr.id AS change_id, cr.change_type, cr.impact_scope, cr.change_description,
       COUNT(es.id) AS total_steps,
       SUM(es.status='confirmed') AS steps_done,
       SUM(es.status='in_progress') AS steps_active,
       SUM(es.status='pending') AS steps_remaining,
       SUM(es.status='failed') AS steps_failed,
       MIN(CASE WHEN es.status IN ('pending','failed') THEN es.seq END) AS next_seq
FROM change_registry cr
LEFT JOIN execution_steps es ON es.change_id = cr.id
WHERE cr.status='active' GROUP BY cr.id;

CREATE VIEW IF NOT EXISTS v_step_board AS
SELECT es.seq, es.step_label, es.step_type, es.layer_name, es.status,
       es.gate_passed, es.failure_notes
FROM execution_steps es
JOIN change_registry cr ON cr.id = es.change_id
WHERE cr.status='active' ORDER BY es.seq;
"""


def cmd_init(conn, args):
    conn.executescript(SCHEMA)
    conn.execute("INSERT OR REPLACE INTO schema_meta(key,value) VALUES('version',?)",
                 (str(SCHEMA_VERSION),))
    conn.commit()
    out({"ok": True, "schema_version": SCHEMA_VERSION, "db": DB_PATH})


def cmd_next(conn, args):
    row = conn.execute("SELECT * FROM v_next_step").fetchone()
    out(dict(row) if row else {"next": None, "message": "No pending or failed steps."})


def cmd_progress(conn, args):
    row = conn.execute("SELECT * FROM v_current_progress").fetchone()
    out(dict(row) if row else {"message": "No active change."})


def cmd_board(conn, args):
    rows = conn.execute("SELECT * FROM v_step_board").fetchall()
    out([dict(r) for r in rows])


def cmd_health(conn, args):
    row = conn.execute(
        "SELECT health, steps_touched, cascade_session_start "
        "FROM session_log ORDER BY id DESC LIMIT 1").fetchone()
    out(dict(row) if row else {"message": "No session yet."})


def cmd_research_add(conn, args):
    p = read_payload()
    conn.execute(
        """INSERT INTO research_findings
           (library,version_found,version_targeted,source_urls,key_findings,
            deprecated_patterns,verified_deps,raw_summary)
           VALUES (?,?,?,?,?,?,?,?)""",
        (p["library"], p.get("version_found"), p.get("version_targeted"),
         json.dumps(p.get("source_urls", [])), json.dumps(p.get("key_findings", [])),
         json.dumps(p.get("deprecated_patterns", [])),
         json.dumps(p.get("verified_deps", [])), p.get("raw_summary", "")))
    conn.commit()
    out({"ok": True, "library": p["library"]})


def cmd_change_add(conn, args):
    p = read_payload()
    cur = conn.execute(
        """INSERT INTO change_registry
           (change_type,impact_scope,change_description,confirmed_by_user)
           VALUES (?,?,?,?)""",
        (p["change_type"], p["impact_scope"], p["change_description"],
         int(p.get("confirmed_by_user", 0))))
    conn.commit()
    cid = cur.lastrowid
    conn.execute("INSERT INTO session_log (change_id, health) VALUES (?, 'GREEN')", (cid,))
    conn.commit()
    out({"ok": True, "change_id": cid})


def cmd_blast_add(conn, args):
    p = read_payload()
    rows = p["rows"] if "rows" in p else [p]
    for r in rows:
        conn.execute(
            """INSERT INTO blast_radius
               (change_id,layer_number,layer_name,file_path,what_changes,required,risk_level,confirmed,notes)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (r["change_id"], r["layer_number"], r["layer_name"], r["file_path"],
             r["what_changes"], int(r.get("required", 1)), r.get("risk_level", "MEDIUM"),
             int(r.get("confirmed", 0)), r.get("notes")))
    conn.commit()
    out({"ok": True, "inserted": len(rows)})


def cmd_step_add(conn, args):
    """Accepts {steps:[...]} or a single step. seq auto-assigned if absent."""
    p = read_payload()
    steps = p["steps"] if "steps" in p else [p]
    inserted = []
    for s in steps:
        cid = s["change_id"]
        if "seq" in s:
            seq = s["seq"]
        else:
            row = conn.execute(
                "SELECT COALESCE(MAX(seq),0)+1 AS n FROM execution_steps WHERE change_id=?",
                (cid,)).fetchone()
            seq = row["n"]
        cur = conn.execute(
            """INSERT INTO execution_steps
               (change_id,seq,step_label,step_type,layer_name,files,acceptance_criteria,cascade_prompt,status)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (cid, seq, s.get("step_label", str(seq)), s["step_type"], s["layer_name"],
             json.dumps(s.get("files", [])), json.dumps(s.get("acceptance_criteria", [])),
             s.get("cascade_prompt", ""), s.get("status", "pending")))
        inserted.append({"step_id": cur.lastrowid, "seq": seq})
    conn.commit()
    out({"ok": True, "steps": inserted})


def cmd_step_claim(conn, args):
    """Atomic claim: only succeeds if step is still pending/failed."""
    sid = int(args[0])
    cur = conn.execute(
        """UPDATE execution_steps
           SET status='in_progress', started_at=CURRENT_TIMESTAMP
           WHERE id=? AND status IN ('pending','failed')""", (sid,))
    conn.commit()
    if cur.rowcount == 0:
        row = conn.execute("SELECT status FROM execution_steps WHERE id=?", (sid,)).fetchone()
        out({"ok": False, "reason": "already claimed or not claimable",
             "current_status": row["status"] if row else "not found"})
    else:
        conn.execute("UPDATE session_log SET last_active_step_id=?, steps_touched=steps_touched+1, "
                     "health=CASE WHEN steps_touched>=12 THEN 'RED' WHEN steps_touched>=7 THEN 'AMBER' ELSE 'GREEN' END "
                     "WHERE id=(SELECT MAX(id) FROM session_log)", (sid,))
        conn.commit()
        out({"ok": True, "claimed": sid})


def cmd_step_confirm(conn, args):
    sid = int(args[0])
    conn.execute(
        """UPDATE execution_steps
           SET status='confirmed', gate_passed=1, failure_notes=NULL,
               completed_at=CURRENT_TIMESTAMP
           WHERE id=?""", (sid,))
    conn.commit()
    out({"ok": True, "confirmed": sid})


def cmd_step_fail(conn, args):
    sid = int(args[0])
    notes = args[1] if len(args) > 1 else None
    conn.execute("UPDATE execution_steps SET status='failed', failure_notes=? WHERE id=?",
                 (notes, sid))
    conn.commit()
    out({"ok": True, "failed": sid, "notes": notes})


def cmd_decision_add(conn, args):
    p = read_payload()
    conn.execute(
        """INSERT INTO decisions (change_id,step_id,decision_type,description,rationale)
           VALUES (?,?,?,?,?)""",
        (p.get("change_id"), p.get("step_id"), p["decision_type"],
         p["description"], p.get("rationale")))
    conn.commit()
    out({"ok": True})


def cmd_map_add(conn, args):
    p = read_payload()
    rows = p["rows"] if "rows" in p else [p]
    if p.get("replace"):
        conn.execute("DELETE FROM codebase_map")
    for r in rows:
        conn.execute(
            """INSERT INTO codebase_map (layer_name,layer_role,layer_order,path_pattern,tech_stack,notes)
               VALUES (?,?,?,?,?,?)""",
            (r["layer_name"], r.get("layer_role", "OTHER"), r["layer_order"],
             r["path_pattern"], r.get("tech_stack"), r.get("notes")))
    conn.commit()
    out({"ok": True, "layers": len(rows)})


def cmd_map_get(conn, args):
    rows = conn.execute(
        "SELECT layer_order,layer_name,layer_role,path_pattern,tech_stack FROM codebase_map ORDER BY layer_order").fetchall()
    out([dict(r) for r in rows])


def cmd_change_complete(conn, args):
    cid = int(args[0])
    conn.execute("UPDATE change_registry SET status='complete', completed_at=CURRENT_TIMESTAMP WHERE id=?", (cid,))
    conn.commit()
    out({"ok": True, "completed": cid})


def cmd_change_abandon(conn, args):
    cid = int(args[0])
    conn.execute("UPDATE change_registry SET status='abandoned' WHERE id=?", (cid,))
    conn.commit()
    out({"ok": True, "abandoned": cid})


def cmd_research_get(conn, args):
    rows = conn.execute(
        "SELECT id,library,version_found,version_targeted,key_findings,deprecated_patterns,verified_deps,created_at "
        "FROM research_findings ORDER BY created_at DESC LIMIT 10").fetchall()
    out([dict(r) for r in rows])


COMMANDS = {
    "init": cmd_init, "next": cmd_next, "progress": cmd_progress,
    "board": cmd_board, "health": cmd_health,
    "research-add": cmd_research_add, "research-get": cmd_research_get,
    "change-add": cmd_change_add, "blast-add": cmd_blast_add,
    "step-add": cmd_step_add, "step-claim": cmd_step_claim,
    "step-confirm": cmd_step_confirm, "step-fail": cmd_step_fail,
    "decision-add": cmd_decision_add, "map-add": cmd_map_add,
    "map-get": cmd_map_get, "change-complete": cmd_change_complete,
    "change-abandon": cmd_change_abandon,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        print("Commands:", ", ".join(sorted(COMMANDS)))
        sys.exit(1)
    conn = connect()
    try:
        COMMANDS[sys.argv[1]](conn, sys.argv[2:])
    finally:
        conn.close()


if __name__ == "__main__":
    main()
