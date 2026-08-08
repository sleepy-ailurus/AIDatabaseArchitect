"""Relationship management router.

Lists relationships (explicit + AI inferred + manual), allows confirming /
rejecting AI suggestions, and creating manual relationships.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Relationship, SchemaColumn, SchemaSnapshot, SchemaTable
from app.schemas import RelationshipCreate, RelationshipOut, RelationshipUpdate
from app.services.schema_parser import is_type_compatible

router = APIRouter(prefix="/api", tags=["relationships"])

_CARDINALITY_DISPLAY = {
    "many-to-one": "N : 1",
    "one-to-many": "1 : N",
    "one-to-one": "1 : 1",
    "many-to-many": "N : N",
    "1:1": "1 : 1",
    "1:N": "1 : N",
    "N:N": "N : N",
}


def _column_type(db: Session, project_id: int, table_name: str, column_name: str) -> str | None:
    """Look up a column's data type from the latest snapshot for a project."""
    snapshot = (
        db.query(SchemaSnapshot)
        .filter(SchemaSnapshot.project_id == project_id)
        .order_by(SchemaSnapshot.version.desc())
        .first()
    )
    if not snapshot:
        return None
    table = (
        db.query(SchemaTable)
        .filter(SchemaTable.snapshot_id == snapshot.id, SchemaTable.table_name == table_name)
        .first()
    )
    if not table:
        return None
    col = (
        db.query(SchemaColumn)
        .filter(SchemaColumn.table_id == table.id, SchemaColumn.column_name == column_name)
        .first()
    )
    return col.data_type if col else None


def _enrich(rel: Relationship, db: Session) -> RelationshipOut:
    src_type = _column_type(db, rel.project_id, rel.source_table, rel.source_column)
    tgt_type = _column_type(db, rel.project_id, rel.target_table, rel.target_column)
    type_match = None
    if src_type and tgt_type:
        type_match = is_type_compatible(src_type, tgt_type)
    return RelationshipOut(
        id=rel.id,
        project_id=rel.project_id,
        source_table=rel.source_table,
        source_column=rel.source_column,
        target_table=rel.target_table,
        target_column=rel.target_column,
        cardinality=rel.cardinality,
        confidence=rel.confidence,
        source_type=rel.source_type,
        status=rel.status,
        reason=rel.reason,
        constraint_name=rel.constraint_name,
        created_at=rel.created_at,
        cardinality_display=_CARDINALITY_DISPLAY.get(rel.cardinality, rel.cardinality),
        source_data_type=src_type,
        target_data_type=tgt_type,
        type_match=type_match,
    )


@router.get("/projects/{project_id}/relationships", response_model=list[RelationshipOut])
def list_relationships(
    project_id: int,
    source_type: str | None = None,
    status_filter: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Relationship).filter(Relationship.project_id == project_id)
    if source_type:
        query = query.filter(Relationship.source_type == source_type)
    if status_filter:
        query = query.filter(Relationship.status == status_filter)
    rels = query.order_by(Relationship.confidence.desc(), Relationship.id.asc()).all()
    return [_enrich(r, db) for r in rels]


@router.post(
    "/projects/{project_id}/relationships",
    response_model=RelationshipOut,
    status_code=status.HTTP_201_CREATED,
)
def create_relationship(project_id: int, payload: RelationshipCreate, db: Session = Depends(get_db)):
    rel = Relationship(
        project_id=project_id,
        source_table=payload.source_table,
        source_column=payload.source_column or "",
        target_table=payload.target_table,
        target_column=payload.target_column or "",
        cardinality=payload.cardinality,
        confidence=payload.confidence,
        source_type=payload.source_type,
        status=payload.status,
        reason=payload.reason,
        constraint_name=payload.constraint_name,
    )
    db.add(rel)
    db.commit()
    db.refresh(rel)
    return _enrich(rel, db)


@router.patch("/relationships/{relationship_id}", response_model=RelationshipOut)
def update_relationship(relationship_id: int, payload: RelationshipUpdate, db: Session = Depends(get_db)):
    rel = db.get(Relationship, relationship_id)
    if not rel:
        raise HTTPException(status_code=404, detail="关系不存在")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(rel, key, value)
    db.commit()
    db.refresh(rel)
    return _enrich(rel, db)


@router.delete("/relationships/{relationship_id}", response_model=dict)
def delete_relationship(relationship_id: int, db: Session = Depends(get_db)):
    rel = db.get(Relationship, relationship_id)
    if not rel:
        raise HTTPException(status_code=404, detail="关系不存在")
    db.delete(rel)
    db.commit()
    return {"message": "关系已删除", "id": relationship_id}


@router.post("/relationships/{relationship_id}/confirm", response_model=RelationshipOut)
def confirm_relationship(relationship_id: int, db: Session = Depends(get_db)):
    rel = db.get(Relationship, relationship_id)
    if not rel:
        raise HTTPException(status_code=404, detail="关系不存在")
    rel.status = "confirmed"
    rel.source_type = "manual"
    db.commit()
    db.refresh(rel)
    return _enrich(rel, db)


@router.post("/relationships/{relationship_id}/reject", response_model=RelationshipOut)
def reject_relationship(relationship_id: int, db: Session = Depends(get_db)):
    rel = db.get(Relationship, relationship_id)
    if not rel:
        raise HTTPException(status_code=404, detail="关系不存在")
    rel.status = "rejected"
    db.commit()
    db.refresh(rel)
    return _enrich(rel, db)
