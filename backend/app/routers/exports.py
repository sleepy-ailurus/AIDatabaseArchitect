"""Document export router - generates Markdown design docs from a project's schema."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DocumentExport, Project, Relationship, SchemaSnapshot, SchemaTable
from app.schemas import ExportCreate, ExportOut
from app.services.markdown_export import generate_markdown
from app.services.schema_parser import ParsedColumn, ParsedSchema, ParsedTable

router = APIRouter(prefix="/api", tags=["exports"])


def _resolve_table_refs(
    relationships: list[dict], snapshot: SchemaSnapshot, db: Session
) -> list[dict]:
    """Resolve source_table/target_table from node IDs to actual table names.

    Early ER model editor saved node IDs (e.g. "3") as source_table instead
    of the real table name (e.g. "sys_department").  This helper builds an
    id->name map from the SchemaTable rows belonging to the snapshot so
    that both legacy and new records produce correct Mermaid output.
    """
    id_to_name: dict[str, str] = {}
    rows = (
        db.query(SchemaTable.id, SchemaTable.table_name)
        .filter(SchemaTable.snapshot_id == snapshot.id)
        .all()
    )
    for tid, tname in rows:
        id_to_name[str(tid)] = tname

    resolved: list[dict] = []
    for r in relationships:
        src = r.get("source_table", "")
        tgt = r.get("target_table", "")
        src_resolved = id_to_name.get(str(src), src)
        tgt_resolved = id_to_name.get(str(tgt), tgt)
        entry = dict(r)
        entry["source_table"] = src_resolved
        entry["target_table"] = tgt_resolved
        resolved.append(entry)
    return resolved


def _snapshot_constraint_relationships(snapshot: SchemaSnapshot) -> list[dict]:
    """Build explicit FK relationships directly from the latest schema snapshot."""
    data = snapshot.snapshot_data or {}
    relationships: list[dict] = []
    for table in data.get("tables", []):
        source_table = table.get("name", "")
        for fk in table.get("foreign_keys", []) or []:
            source_column = fk.get("source_column")
            target_table = fk.get("target_table")
            target_column = fk.get("target_column")
            if not (source_table and source_column and target_table and target_column):
                continue
            relationships.append(
                {
                    "source_table": source_table,
                    "source_column": source_column,
                    "target_table": target_table,
                    "target_column": target_column,
                    "cardinality": "many-to-one",
                    "confidence": 1.0,
                    "source_type": "database_constraint",
                    "status": "confirmed",
                    "reason": ["数据库显式外键约束"],
                    "constraint_name": fk.get("constraint_name") or fk.get("name"),
                }
            )
    return relationships


def _build_export_relationships(project_id: int, snapshot: SchemaSnapshot, db: Session) -> list[dict]:
    """Merge persisted relationships with explicit FKs from snapshot for export."""
    rels = (
        db.query(Relationship)
        .filter(Relationship.project_id == project_id)
        .order_by(Relationship.confidence.desc())
        .all()
    )
    resolved = _resolve_table_refs(
        [
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
        ],
        snapshot,
        db,
    )

    merged = list(resolved)
    existing_keys = {
        (
            str(r.get("source_table", "")),
            str(r.get("source_column", "")),
            str(r.get("target_table", "")),
            str(r.get("target_column", "")),
            str(r.get("source_type", "")),
        )
        for r in resolved
    }
    for r in _snapshot_constraint_relationships(snapshot):
        key = (
            str(r.get("source_table", "")),
            str(r.get("source_column", "")),
            str(r.get("target_table", "")),
            str(r.get("target_column", "")),
            str(r.get("source_type", "")),
        )
        if key in existing_keys:
            continue
        merged.append(r)
        existing_keys.add(key)
    return merged


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
    rel_dicts = _build_export_relationships(project_id, snapshot, db)

    content = generate_markdown(
        schema=schema,
        relationships=rel_dicts,
        project_name=project.name,
        project_description=project.description,
        sections=payload.sections,
        include_ai=payload.include_ai,
        expand_columns=payload.expand_columns,
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
    rel_dicts = _build_export_relationships(project_id, snapshot, db)

    content = generate_markdown(
        schema=schema,
        relationships=rel_dicts,
        project_name=project.name,
        project_description=project.description,
        sections=payload.sections,
        include_ai=payload.include_ai,
        expand_columns=payload.expand_columns,
    )

    table_count = len(snapshot.snapshot_data.get("tables", [])) if snapshot.snapshot_data else 0
    ai_rel_count = sum(1 for r in rels if r.source_type == "ai_suggestion")

    return {
        "content": content,
        "format": payload.format,
        "stats": {
            "table_count": table_count,
            "relation_count": len(rel_dicts),
            "ai_relation_count": ai_rel_count,
            "field_count": sum(
                len(t.get("columns", []))
                for t in (snapshot.snapshot_data or {}).get("tables", [])
            ),
        },
        "project_name": project.name,
    }
