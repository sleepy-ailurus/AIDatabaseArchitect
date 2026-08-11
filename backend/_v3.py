import sys, os, sqlite3, json

BACKEND_DIR = r"C:\Users\Tby\Desktop\AIDatabaseArchitect\backend"
DB_PATH = os.path.join(BACKEND_DIR, "app.db")
sys.path.insert(0, BACKEND_DIR)
os.chdir(BACKEND_DIR)
os.environ.setdefault("FERNET_KEY", "dev-only-fallback-key-do-not-use-in-prod-a")
os.environ.setdefault("APP_SECRET", "dev-only-fallback-secret")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{DB_PATH}")

from app.services.schema_parser import schema_from_dict
from app.services.relation_candidate import generate_candidates, normalize_relationship_direction

conn = sqlite3.connect(DB_PATH)
for pid, pname in [(3, "教师管理系统"), (4, "学生管理系统")]:
    cur = conn.cursor()
    sid_row = cur.execute("SELECT id FROM schema_snapshots WHERE project_id=? ORDER BY version DESC LIMIT 1", (pid,)).fetchone()
    if not sid_row:
        print(f"[pid={pid} {pname}] NO SNAPSHOT"); continue
    raw = cur.execute("SELECT snapshot_data FROM schema_snapshots WHERE id=?", sid_row).fetchone()[0]
    snap_json = raw if isinstance(raw, dict) else json.loads(raw)
    existing_keys = set()
    for r in cur.execute("""
    SELECT LOWER(COALESCE(source_table,'')), LOWER(COALESCE(source_column,'')),
           LOWER(COALESCE(target_table,'')), LOWER(COALESCE(target_column,''))
    FROM relationships WHERE project_id = ?
    """, (pid,)).fetchall():
        existing_keys.add(tuple(r))

    schema = schema_from_dict(snap_json)
    cands = generate_candidates(schema)
    total = len(cands)
    uncovered = 0
    covered = 0
    print(f"\n===== [{pid} {pname}] existing_rels={len(existing_keys)} rule_total={total} =====")
    for c in cands:
        st, sc, tt, tc, card = normalize_relationship_direction(
            c.source_table, c.source_column, c.target_table, c.target_column, c.cardinality
        )
        key = (st.lower(), sc.lower(), tt.lower(), tc.lower())
        if key in existing_keys:
            covered += 1
            print(f"  ✅ COVERED: {st}.{sc} <-> {tt}.{tc}  [{card}]")
        else:
            uncovered += 1
            print(f"  ❌ UNCOVERED: {st}.{sc} <-> {tt}.{tc}  [{card}] score={c.confidence_score:.2f}")
    shortcut = (total > 0 and uncovered == 0)
    print(f"  -> covered={covered}/{total} uncovered={uncovered} WILL_SKIP_LLM={shortcut}")
conn.close()
