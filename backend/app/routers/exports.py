"""Document export router - generates Markdown design docs from a project's schema."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DocumentExport, Project, Relationship, SchemaSnapshot
from app.schemas import ExportCreate, ExportOut
from app.services.markdown_export import generate_markdown
from app.services.schema_parser import ParsedColumn, ParsedSchema, ParsedTable

router = APIRouter(prefix="/api", tags=["exports"])


def _reconstruct_schema(snapshot: SchemaSnapshot) -> ParsedSchema:
    data = snapshot.snapshot_data or {}
    schema = ParsedSchema(
        database_name=data.get("database_name", ""),
        db_version=data.get("db_version"),
    )
    for t in data.get("tables", []):
        ptable = ParsedTable(
            name=t.get("name", ""),
            comment=t.get("comment"),
            engine=t.get("engine"),
        )
        for c in t.get("columns", []):
            ptable.columns.append(
                ParsedColumn(
                    name=c.get("name", ""),
                    data_type=c.get("data_type", ""),
                    length=c.get("length"),
                    nullable=c.get("nullable", True),
                    default_value=c.get("default_value"),
                    is_primary_key=c.get("is_primary_key", False),
                    is_unique=c.get("is_unique", False),
                    comment=c.get("comment"),
                )
            )
        ptable.indexes = t.get("indexes", []) or []
        ptable.foreign_keys = t.get("foreign_keys", []) or []
        schema.tables.append(ptable)
    return schema


@router.post(
    "/projects/{project_id}/exports",
    response_model=ExportOut,
    status_code=status.HTTP_201_CREATED,
)
def create_export(project_id: int, payload: ExportCreate, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    snapshot = (
        db.query(SchemaSnapshot)
        .filter(SchemaSnapshot.project_id == project_id)
        .order_by(SchemaSnapshot.version.desc())
        .first()
    )
    if not snapshot:
        raise HTTPException(status_code=400, detail="该项目尚无 Schema 快照，无法导出")

    schema = _reconstruct_schema(snapshot)
    rels = (
        db.query(Relationship)
        .filter(Relationship.project_id == project_id)
        .order_by(Relationship.confidence.desc())
        .all()
    )
    rel_dicts = [
        {
            "source_table": r.source_table,
            "source_column": r.source_column,
            "target_table": r.target_table,
            "target_column": r.target_column,
            "cardinality": r.cardinality,
            "confidence": r.confidence,
            "source_type": r.source_type,
            "status": r.status,
            "reason": r.reason or [],
            "constraint_name": r.constraint_name,
        }
        for r in rels
    ]

    content = generate_markdown(
        schema=schema,
        relationships=rel_dicts,
        project_name=project.name,
        project_description=project.description,
    )

    export = DocumentExport(
        project_id=project_id,
        format=payload.format,
        content=content,
    )
    db.add(export)
    db.commit()
    db.refresh(export)
    return export


@router.get("/exports/{export_id}", response_model=ExportOut)
def get_export(export_id: int, db: Session = Depends(get_db)):
    export = db.get(DocumentExport, export_id)
    if not export:
        raise HTTPException(status_code=404, detail="导出记录不存在")
    return export


@router.get("/projects/{project_id}/exports", response_model=list[ExportOut])
def list_exports(project_id: int, db: Session = Depends(get_db)):
    return (
        db.query(DocumentExport)
        .filter(DocumentExport.project_id == project_id)
        .order_by(DocumentExport.created_at.desc())
        .all()
    )


@router.get("/exports/{export_id}/download", response_class=PlainTextResponse)
def download_export(export_id: int, db: Session = Depends(get_db)):
    export = db.get(DocumentExport, export_id)
    if not export:
        raise HTTPException(status_code=404, detail="导出记录不存在")
    filename = f"export_{export.id}.md"
    return PlainTextResponse(
        content=export.content,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post(
    "/projects/{project_id}/exports/preview",
    response_model=dict,
)
def preview_export(project_id: int, payload: ExportCreate, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    snapshot = (
        db.query(SchemaSnapshot)
        .filter(SchemaSnapshot.project_id == project_id)
        .order_by(SchemaSnapshot.version.desc())
        .first()
    )
    if not snapshot:
        raise HTTPException(status_code=400, detail="该项目尚无 Schema 快照")

    schema = _reconstruct_schema(snapshot)
    rels = (
        db.query(Relationship)
        .filter(Relationship.project_id == project_id)
        .order_by(Relationship.confidence.desc())
        .all()
    )
    rel_dicts = [
        {
            "source_table": r.source_table,
            "source_column": r.source_column,
            "target_table": r.target_table,
            "target_column": r.target_column,
            "cardinality": r.cardinality,
            "confidence": r.confidence,
            "source_type": r.source_type,
            "status": r.status,
            "reason": r.reason or [],
        }
        for r in rels
    ]

    content = generate_markdown(
        schema=schema,
        relationships=rel_dicts,
        project_name=project.name,
        project_description=project.description,
    )

    table_count = len(snapshot.snapshot_data.get("tables", [])) if snapshot.snapshot_data else 0
    rel_count = len(rels)
    ai_rel_count = sum(1 for r in rels if r.source_type == "ai_suggestion")

    return {
        "content": content,
        "format": payload.format,
        "stats": {
            "table_count": table_count,
            "relation_count": rel_count,
            "ai_relation_count": ai_rel_count,
            "field_count": sum(
                len(t.get("columns", []))
                for t in (snapshot.snapshot_data or {}).get("tables", [])
            ),
        },
        "project_name": project.name,
    }
