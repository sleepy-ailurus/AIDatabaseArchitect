"""Smart test data generator router (feature 8)."""
from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DatabaseConnection, Project, SchemaSnapshot
from app.schemas import TestDataGenerate
from app.services import crypto
from app.services.data_generator import execute_sql, generate_insert_sql
from app.services.schema_parser import schema_from_dict

router = APIRouter(prefix="/api", tags=["test-data"])


@router.post("/projects/{project_id}/test-data/generate", response_model=dict)
def generate_test_data(
    project_id: int,
    payload: TestDataGenerate = Body(default=TestDataGenerate()),
    db: Session = Depends(get_db),
):
    """Generate schema-aware test data (INSERT SQL), optionally write it to the DB."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    snapshot = (
        db.query(SchemaSnapshot)
        .filter(SchemaSnapshot.project_id == project_id)
        .order_by(SchemaSnapshot.version.desc())
        .first()
    )
    if not snapshot or not snapshot.snapshot_data:
        raise HTTPException(status_code=400, detail="该项目尚无 Schema 快照，请先同步或导入")

    schema = schema_from_dict(snapshot.snapshot_data)
    conn = (
        db.query(DatabaseConnection)
        .filter(DatabaseConnection.project_id == project_id)
        .order_by(DatabaseConnection.id.desc())
        .first()
    )
    db_type = conn.db_type if conn else "mysql"
    result = generate_insert_sql(schema, payload.rows_per_table, db_type=db_type)

    executed = 0
    error = None
    if payload.execute:
        if not conn:
            raise HTTPException(status_code=400, detail="该项目未配置数据库连接，无法直接写入")
        from sqlalchemy import create_engine

        password = crypto.decrypt(conn.password_encrypted)
        ssl_config = conn.ssl_config or {}
        from app.services.schema_parser import build_db_url

        url, connect_args, ca_file = build_db_url(
            str(conn.db_type),
            conn.host,
            conn.port,
            conn.database_name,
            conn.username,
            password,
            bool(ssl_config.get("enabled")),
            conn.timeout,
            ssl_config.get("ca"),
        )
        engine = create_engine(url, connect_args=connect_args, pool_pre_ping=True)
        try:
            outcome = execute_sql(engine, result["sql"])
            executed = outcome["executed"]
            error = outcome.get("error")
        finally:
            engine.dispose()

    return {
        "sql": result["sql"],
        "row_counts": result["row_counts"],
        "total_rows": sum(result["row_counts"].values()),
        "executed": executed,
        "error": error,
    }
