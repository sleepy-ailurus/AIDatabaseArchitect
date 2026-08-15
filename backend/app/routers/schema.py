"""Schema sync & inspection router.

Reads the latest database connection for a project, connects to the user's
MySQL, parses the schema into a snapshot (tables/columns/indexes/foreign keys),
and persists explicit foreign-key relationships.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    CommentSuggestion,
    DatabaseConnection,
    Project,
    SchemaSnapshot,
    SchemaTable,
)
from app.schemas import (
    ColumnOut,
    SchemaSyncResult,
    SnapshotOut,
    TableOut,
)
from app.services import crypto
from app.services.schema_persist import persist_schema_snapshot
from app.services.schema_parser import SchemaParseError, parse_schema
from app.services.schema_diff import diff_from_snapshots

router = APIRouter(prefix="/api", tags=["schema"])


def _get_connection(db: Session, project_id: int) -> DatabaseConnection:
    conn = (
        db.query(DatabaseConnection)
        .filter(DatabaseConnection.project_id == project_id)
        .order_by(DatabaseConnection.id.desc())
        .first()
    )
    if not conn:
        raise HTTPException(status_code=404, detail="该项目尚未配置数据库连接")
    return conn


@router.post(
    "/projects/{project_id}/schema/sync",
    response_model=SchemaSyncResult,
    status_code=status.HTTP_200_OK,
)
def sync_schema(project_id: int, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    conn = _get_connection(db, project_id)

    password = crypto.decrypt(conn.password_encrypted)
    ssl_config = conn.ssl_config or {}
    ssl_enabled = bool(ssl_config.get("enabled"))
    ca = ssl_config.get("ca")

    try:
        schema = parse_schema(
            db_type=str(conn.db_type),
            host=conn.host,
            port=conn.port,
            database=conn.database_name,
            username=conn.username,
            password=password,
            ssl=ssl_enabled,
            timeout=conn.timeout,
            ca=ca,
        )
    except SchemaParseError as exc:
        raise HTTPException(status_code=400, detail=exc.detail or exc.reason) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Schema 解析失败: {exc}") from exc

    snapshot, relationship_count = persist_schema_snapshot(db, project_id, schema)

    project.status = "schema_synced"
    db.commit()

    return SchemaSyncResult(
        success=True,
        message=f"同步成功：{len(schema.tables)} 张表，{relationship_count} 条显式外键",
        snapshot_id=snapshot.id,
        table_count=len(schema.tables),
        relationship_count=relationship_count,
    )


@router.get("/projects/{project_id}/schema/snapshots", response_model=list[SnapshotOut])
def list_snapshots(project_id: int, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    snapshots = (
        db.query(SchemaSnapshot)
        .filter(SchemaSnapshot.project_id == project_id)
        .order_by(SchemaSnapshot.version.desc())
        .all()
    )
    result = []
    for s in snapshots:
        table_count = (
            s.snapshot_data.get("tables", []) if isinstance(s.snapshot_data, dict) else []
        )
        result.append(
            SnapshotOut(
                id=s.id,
                project_id=s.project_id,
                version=s.version,
                created_at=s.created_at,
                table_count=len(table_count),
            )
        )
    return result


@router.get("/projects/{project_id}/schema/diff", response_model=dict)
def schema_diff(
    project_id: int,
    from_version: int | None = None,
    to_version: int | None = None,
    db: Session = Depends(get_db),
):
    """Compare two schema snapshots and return a structured change report.

    Defaults to the latest two snapshots when versions are omitted.
    """
    snapshots = (
        db.query(SchemaSnapshot)
        .filter(SchemaSnapshot.project_id == project_id)
        .order_by(SchemaSnapshot.version.desc())
        .all()
    )
    if len(snapshots) < 2:
        raise HTTPException(status_code=400, detail="至少需要两个 Schema 快照才能对比")

    by_version = {s.version: s for s in snapshots}
    versions = sorted(by_version.keys())
    to_v = to_version if to_version is not None else versions[-1]
    from_v = from_version if from_version is not None else versions[-2]
    if from_v not in by_version or to_v not in by_version:
        raise HTTPException(status_code=404, detail="快照版本不存在")
    if from_v == to_v:
        raise HTTPException(status_code=400, detail="请选择两个不同的快照版本")
    if from_v > to_v:
        from_v, to_v = to_v, from_v

    old = by_version[from_v].snapshot_data or {}
    new = by_version[to_v].snapshot_data or {}
    diff = diff_from_snapshots(old, new)
    diff["from_version"] = from_v
    diff["to_version"] = to_v
    return diff


@router.get("/projects/{project_id}/schema/tables", response_model=list[TableOut])
def list_tables(project_id: int, snapshot_id: int | None = None, db: Session = Depends(get_db)):
    """Return tables (with columns) for the latest or a specified snapshot."""
    if snapshot_id:
        snapshot = db.get(SchemaSnapshot, snapshot_id)
        if not snapshot or snapshot.project_id != project_id:
            raise HTTPException(status_code=404, detail="快照不存在")
    else:
        snapshot = (
            db.query(SchemaSnapshot)
            .filter(SchemaSnapshot.project_id == project_id)
            .order_by(SchemaSnapshot.version.desc())
            .first()
        )
        if not snapshot:
            return []

    tables = (
        db.query(SchemaTable)
        .filter(SchemaTable.snapshot_id == snapshot.id)
        .order_by(SchemaTable.table_name)
        .all()
    )
    # Merge confirmed comment suggestions into the returned columns so the ER
    # canvas / detail panels show the AI-confirmed comments without requiring a
    # write-back to the live database.
    suggestion_map: dict[tuple, str] = {}
    suggestions = (
        db.query(CommentSuggestion)
        .filter(
            CommentSuggestion.project_id == project_id,
            CommentSuggestion.status.in_(("accepted", "applied")),
        )
        .all()
    )
    for s in suggestions:
        if s.target_type == "table":
            suggestion_map[("table", s.table_name)] = s.suggested_comment
        else:
            suggestion_map[("column", s.table_name, s.column_name or "")] = s.suggested_comment

    out: list[TableOut] = []
    for t in tables:
        cols = sorted(t.columns, key=lambda c: (not c.is_primary_key, c.id))
        out.append(
            TableOut(
                id=t.id,
                table_name=t.table_name,
                comment=suggestion_map.get(("table", t.table_name)) or t.comment,
                engine=t.engine,
                columns=[
                    ColumnOut(
                        id=c.id,
                        column_name=c.column_name,
                        data_type=c.data_type,
                        length=c.length,
                        nullable=c.nullable,
                        default_value=c.default_value,
                        is_primary_key=c.is_primary_key,
                        is_unique=c.is_unique,
                        comment=suggestion_map.get(("column", t.table_name, c.column_name)) or c.comment,
                    )
                    for c in cols
                ],
            )
        )
    return out
