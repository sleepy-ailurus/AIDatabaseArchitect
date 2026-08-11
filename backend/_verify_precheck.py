import sys, os, sqlite3, json

BACKEND_DIR = r"C:\Users\Tby\Desktop\AIDatabaseArchitect\backend"
DB_PATH = os.path.join(BACKEND_DIR, "app.db")
sys.path.insert(0, BACKEND_DIR)
os.chdir(BACKEND_DIR)

# load env vars expected by config (only secret key)
os.environ.setdefault("FERNET_KEY", "dev-only-fallback-key-do-not-use-in-prod-a")
os.environ.setdefault("APP_SECRET", "dev-only-fallback-secret")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{DB_PATH}")

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Project 4 (学生)
pid = 4
sid = cur.execute("SELECT id FROM schema_snapshots WHERE project_id=? ORDER BY version DESC LIMIT 1", (pid,)).fetchone()[0]
raw = cur.execute("SELECT snapshot_data FROM schema_snapshots WHERE id=?", (sid,)).fetchone()[0]
snap_json = raw if isinstance(raw, dict) else json.loads(raw)

existing_keys = set()
for r in cur.execute("""
SELECT LOWER(COALESCE(source_table,'')), LOWER(COALESCE(source_column,'')),
       LOWER(COALESCE(target_table,'')), LOWER(COALESCE(target_column,''))
FROM relationships WHERE project_id = ?
""", (pid,)).fetchall():
    existing_keys.add(tuple(r))
print(f"[Project {pid} 学生系统] existing_keys = {len(existing_keys)}")
conn.close()

from app.services.schema_parser import schema_from_dict
from app.services.relation_candidate import generate_candidates, normalize_relationship_direction

schema = schema_from_dict(snap_json)
cands = generate_candidates(schema)
print(f"rule candidates total: {len(cands)}")
uncovered = 0
covered = 0
for c in cands:
    st, sc, tt, tc, _card = normalize_relationship_direction(
        c.source_table, c.source_column, c.target_table, c.target_column
    )
    key = (st.lower(), sc.lower(), tt.lower(), tc.lower())
    if key in existing_keys:
        covered += 1
        print(f"  ✅ COVERED: {st}.{sc}  <->  {tt}.{tc} (conf_score={c.confidence_score:.2f})")
    else:
        uncovered += 1
        print(f"  ❌ UNCOVERED: {st}.{sc}  <->  {tt}.{tc} (conf_score={c.confidence_score:.2f})")
print(f"\ncovered={covered} / total={len(cands)}")
print(f"uncovered={uncovered}  -> Shortcut trigger? {uncovered == 0}")
