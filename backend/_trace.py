import sys, os, json
BACKEND_DIR = r"C:\Users\Tby\Desktop\AIDatabaseArchitect\backend"
DB_PATH = os.path.join(BACKEND_DIR, "app.db")
sys.path.insert(0, BACKEND_DIR)
os.chdir(BACKEND_DIR)
os.environ.setdefault("FERNET_KEY", "dev-only-fallback-key-do-not-use-in-prod-a")
os.environ.setdefault("APP_SECRET", "dev-only-fallback-secret")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{DB_PATH}")

import sqlite3
from app.services.schema_parser import schema_from_dict
from app.services.relation_candidate import generate_candidates, _extract_hint, _table_name_matches_hint, _target_column_matches_hint

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
sid_row = cur.execute("SELECT id FROM schema_snapshots WHERE project_id=4 ORDER BY version DESC LIMIT 1").fetchone()
raw = cur.execute("SELECT snapshot_data FROM schema_snapshots WHERE id=?", sid_row).fetchone()[0]
snap_json = raw if isinstance(raw, dict) else json.loads(raw)
schema = schema_from_dict(snap_json)
conn.close()

print("=== Student schema tables & their columns ===")
for t in schema.tables:
    print(f"\nTable: {t.name}")
    for c in t.columns:
        flags = []
        if c.is_primary_key: flags.append("PK")
        if c.is_unique: flags.append("UK")
        fks = t.foreign_keys or []
        print(f"  {c.name:20s} {c.data_type:10s} {' '.join(flags)}", end="")
        if fks:
            for fk in fks:
                print(f"  FK-> {fk}", end="")
        print()

# Now trace the matching logic for dept_id -> department
print("\n=== Tracing dept_id matching ===")
col_name = "dept_id"
hint = _extract_hint(col_name)
print(f"extract_hint({col_name}) = {hint}")

for t in schema.tables:
    match = _table_name_matches_hint(t.name, hint)
    print(f"  _table_name_matches_hint({t.name}, '{hint}') = {match}")
    if match:
        for c in t.columns:
            pk = "PK" if c.is_primary_key else ""
            ok = _target_column_matches_hint(c.name, hint)
            print(f"    _target_column_matches_hint({c.name}, '{hint}') = {ok}  [{pk}]")

print("\n=== Tracing stu_id matching ===")
hint = _extract_hint("stu_id")
for t in schema.tables:
    match = _table_name_matches_hint(t.name, hint)
    print(f"  _table_name_matches_hint({t.name}, '{hint}') = {match}")

print("\n=== generate_candidates output ===")
cands = generate_candidates(schema)
print(f"Total: {len(cands)}")
for c in cands:
    print(f"  {c.source_table}.{c.source_column} -> {c.target_table}.{c.target_column} (conf={c.confidence})")
