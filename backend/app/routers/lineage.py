"""SQL lineage / impact analysis router (feature 7)."""
from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Project, SchemaSnapshot
from app.schemas import LineageAnalyze, LineageImpact
from app.services.lineage import analyze_sql_lineage, compute_impact
from app.services.schema_parser import schema_from_dict

router = APIRouter(prefix="/api", tags=["lineage"])


def _schema(db: Session, project_id: int):
    snapshot = (
        db.query(SchemaSnapshot)
        .filter(SchemaSnapshot.project_id == project_id)
        .order_by(SchemaSnapshot.version.desc())
        .first()
    )
    if not snapshot or not snapshot.snapshot_data:
        raise HTTPException(status_code=400, detail="该项目尚无 Schema 快照，请先同步或导入")
    return schema_from_dict(snapshot.snapshot_data)


@router.post("/projects/{project_id}/lineage/analyze", response_model=dict)
def analyze_lineage(
    project_id: int,
    payload: LineageAnalyze = Body(...),
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    schema = _schema(db, project_id)
    return analyze_sql_lineage(payload.sql_text, schema)


@router.post("/projects/{project_id}/lineage/impact", response_model=dict)
def impact(
    project_id: int,
    payload: LineageImpact = Body(...),
    db: Session = Depends(get_db),
):
    """Impact analysis requires a previous analyze result in the payload context."""
    # For stateless operation the frontend computes impact locally; this endpoint
    # validates the table exists and returns an empty baseline.
    schema = _schema(db, project_id)
    known = {t.name for t in schema.tables}
    if payload.table not in known:
        raise HTTPException(status_code=404, detail="表不存在于当前 Schema")
    return {"table": payload.table, "dependent_queries": [], "downstream_tables": []}
