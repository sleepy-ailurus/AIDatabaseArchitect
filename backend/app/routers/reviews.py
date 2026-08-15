"""Schema review router - rule lint + optional AI architecture review (feature 5)."""
from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import LLMConfig, Project, ReviewReport, SchemaSnapshot
from app.schemas import ReviewCreate, ReviewOut
from app.services.ai_review import ai_review_schema
from app.services.llm_service import settings_from_config
from app.services.schema_lint import run_lint, summarize_findings
from app.services.schema_parser import schema_from_dict

router = APIRouter(prefix="/api", tags=["reviews"])


@router.post("/projects/{project_id}/reviews", response_model=ReviewOut)
def create_review(
    project_id: int,
    payload: ReviewCreate = Body(default=ReviewCreate()),
    db: Session = Depends(get_db),
):
    """Run rule-based lint + optional AI review and persist the report."""
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
    lint_findings = run_lint(schema)

    ai_findings: list[dict] = []
    used_ai = False
    if payload.run_ai:
        llm_config = None
        if payload.llm_config_id:
            llm_config = db.get(LLMConfig, payload.llm_config_id)
            if not llm_config:
                raise HTTPException(status_code=404, detail="LLM 配置不存在")
        else:
            llm_config = (
                db.query(LLMConfig)
                .filter(LLMConfig.is_default.is_(True))
                .order_by(LLMConfig.id.asc())
                .first()
            ) or db.query(LLMConfig).order_by(LLMConfig.id.asc()).first()
        if llm_config:
            used_ai = True
            ai_findings = ai_review_schema(
                schema,
                lint_findings,
                settings_from_config(llm_config),
            )

    summary = summarize_findings(lint_findings)
    summary["ai_findings"] = len(ai_findings)
    report = ReviewReport(
        project_id=project_id,
        lint_findings=lint_findings,
        ai_findings=ai_findings or None,
        summary=summary,
        used_ai=used_ai,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


@router.get("/projects/{project_id}/reviews/latest", response_model=ReviewOut | None)
def get_latest_review(project_id: int, db: Session = Depends(get_db)):
    report = (
        db.query(ReviewReport)
        .filter(ReviewReport.project_id == project_id)
        .order_by(ReviewReport.id.desc())
        .first()
    )
    return report


@router.get("/projects/{project_id}/reviews", response_model=list[ReviewOut])
def list_reviews(project_id: int, db: Session = Depends(get_db)):
    return (
        db.query(ReviewReport)
        .filter(ReviewReport.project_id == project_id)
        .order_by(ReviewReport.id.desc())
        .all()
    )
