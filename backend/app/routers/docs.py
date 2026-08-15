"""Course design / graduation design document export router (feature 11)."""
from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ConceptModel, Project, Relationship, SchemaSnapshot
from app.schemas import DesignDocRequest
from app.services.course_doc import build_markdown, build_word
from app.services.schema_parser import schema_from_dict

router = APIRouter(prefix="/api", tags=["design-doc"])


@router.post("/projects/{project_id}/design-doc/export")
def export_design_doc(
    project_id: int,
    format: str = Query(default="markdown", pattern="^(markdown|word)$"),
    payload: DesignDocRequest = Body(default=DesignDocRequest()),
    db: Session = Depends(get_db),
):
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

    rels = db.query(Relationship).filter(Relationship.project_id == project_id).all()
    relationships = [
        {
            "source_table": r.source_table,
            "source_column": r.source_column,
            "target_table": r.target_table,
            "target_column": r.target_column,
            "cardinality": r.cardinality,
            "source_type": r.source_type,
            "status": r.status,
        }
        for r in rels
    ]

    concept_model = None
    model = (
        db.query(ConceptModel)
        .filter(ConceptModel.project_id == project_id)
        .order_by(ConceptModel.id.desc())
        .first()
    )
    if model and model.model_data:
        concept_model = model.model_data

    kwargs = dict(
        project_name=project.name,
        project_description=project.description,
        schema=schema,
        relationships=relationships,
        concept_model=concept_model,
        author=payload.author,
        student_id=payload.student_id,
    )
    filename = f"design-doc-{project_id}"
    if format == "word":
        content = build_word(**kwargs)
        media = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        filename += ".docx"
    else:
        content = build_markdown(**kwargs).encode("utf-8")
        media = "text/markdown; charset=utf-8"
        filename += ".md"

    return Response(
        content=content,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
