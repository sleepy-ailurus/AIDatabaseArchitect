"""Offline schema import router - paste DDL or upload DBML, no database needed."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Project
from app.schemas import SchemaImportRequest, SchemaSyncResult
from app.services.import_parser import ImportParseError, parse_schema_source
from app.services.schema_persist import persist_schema_snapshot

router = APIRouter(prefix="/api", tags=["schema-import"])


def _preview_payload(schema) -> dict:
    return {
        "success": True,
        "table_count": len(schema.tables),
        "column_count": sum(len(t.columns) for t in schema.tables),
        "relationship_count": sum(len(t.foreign_keys) for t in schema.tables),
        "tables": [
            {
                "name": t.name,
                "comment": t.comment,
                "engine": t.engine,
                "columns": [
                    {
                        "name": c.name,
                        "data_type": c.data_type,
                        "length": c.length,
                        "nullable": c.nullable,
                        "is_primary_key": c.is_primary_key,
                        "is_unique": c.is_unique,
                        "comment": c.comment,
                    }
                    for c in t.columns
                ],
                "foreign_keys": t.foreign_keys,
            }
            for t in schema.tables
        ],
    }


@router.post("/projects/{project_id}/schema/import-preview", response_model=dict)
def preview_import(project_id: int, payload: SchemaImportRequest, db: Session = Depends(get_db)):
    """Dry-run parse: returns the tables that would be imported, without saving."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    try:
        schema = parse_schema_source(payload.source, payload.content, db_type=payload.db_type)
    except ImportParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"解析失败: {exc}") from exc
    return _preview_payload(schema)


@router.post("/projects/{project_id}/schema/import", response_model=SchemaSyncResult)
def import_schema(project_id: int, payload: SchemaImportRequest, db: Session = Depends(get_db)):
    """Parse DDL/DBML and persist as a new schema snapshot (same shape as DB sync)."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    try:
        schema = parse_schema_source(payload.source, payload.content, db_type=payload.db_type)
    except ImportParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"解析失败: {exc}") from exc

    snapshot, relationship_count = persist_schema_snapshot(db, project_id, schema)
    project.status = "schema_synced"
    db.commit()

    return SchemaSyncResult(
        success=True,
        message=f"导入成功：{len(schema.tables)} 张表，{relationship_count} 条显式外键",
        snapshot_id=snapshot.id,
        table_count=len(schema.tables),
        relationship_count=relationship_count,
    )
