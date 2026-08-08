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
    DatabaseConnection,
    Project,
    Relationship,
    SchemaColumn,
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
from app.services.schema_parser import SchemaParseError, parse_schema

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
    ssl_enabled = bool(conn.ssl_config and conn.ssl_config.get("enabled"))

    try:
        schema = parse_schema(
            host=conn.host,
            port=conn.port,
            database=conn.database_name,
            username=conn.username,
            password=password,
            ssl=ssl_enabled,
            timeout=conn.timeout,
        )
    except SchemaParseError as exc:
        raise HTTPException(status_code=400, detail=exc.detail or exc.reason) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Schema 解析失败: {exc}") from exc

    # Determine the next snapshot version for this project.
    last_version = (
        db.query(SchemaSnapshot)
        .filter(SchemaSnapshot.project_id == project_id)
        .order_by(SchemaSnapshot.version.desc())
        .first()
    )
    next_version = (last_version.version + 1) if last_version else 1

    snapshot = SchemaSnapshot(
        project_id=project_id,
        snapshot_data=schema.to_dict(),
        version=next_version,
    )
    db.add(snapshot)
    db.flush()

    for t in schema.tables:
        table_row = SchemaTable(
            snapshot_id=snapshot.id,
            table_name=t.name,
            comment=t.comment,
            engine=t.engine,
        )
        db.add(table_row)
        db.flush()
        for c in t.columns:
            db.add(
                SchemaColumn(
                    table_id=table_row.id,
                    column_name=c.name,
                    data_type=c.data_type,
                    length=c.length,
                    nullable=c.nullable,
                    default_value=c.default_value,
                    is_primary_key=c.is_primary_key,
                    is_unique=c.is_unique,
                    comment=c.comment,
                )
            )

    # Persist explicit foreign-key relationships (database_constraint).
    relationship_count = 0
    for t in schema.tables:
        for fk in t.foreign_keys:
            source_col = fk.get("source_column")
            target_table = fk.get("target_table")
            target_col = fk.get("target_column")
            if not (source_col and target_table and target_col):
                continue
            # Avoid duplicating an already-confirmed constraint relationship.
            existing = (
                db.query(Relationship)
                .filter(
                    Relationship.project_id == project_id,
                    Relationship.source_table == t.name,
                    Relationship.source_column == source_col,
                    Relationship.target_table == target_table,
                    Relationship.target_column == target_col,
                    Relationship.source_type == "database_constraint",
                )
                .first()
            )
            if existing:
                continue
            db.add(
                Relationship(
                    project_id=project_id,
                    source_table=t.name,
                    source_column=source_col,
                    target_table=target_table,
                    target_column=target_col,
                    cardinality="many-to-one",
                    confidence=1.0,
                    source_type="database_constraint",
                    status="confirmed",
                    reason=["数据库显式外键约束"],
                    constraint_name=fk.get("name"),
                )
            )
            relationship_count += 1

    project.status = "schema_synced"
    db.commit()
    db.refresh(snapshot)

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
    out: list[TableOut] = []
    for t in tables:
        cols = sorted(t.columns, key=lambda c: (not c.is_primary_key, c.id))
        out.append(
            TableOut(
                id=t.id,
                table_name=t.table_name,
                comment=t.comment,
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
                        comment=c.comment,
                    )
                    for c in cols
                ],
            )
        )
    return out
