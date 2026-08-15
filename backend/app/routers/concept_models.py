"""ER concept model router - convert physical schema to Chen-notation concept model."""
from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ConceptModel, LLMConfig, Project, Relationship, SchemaSnapshot
from app.schemas import ConceptModelConvert, ConceptModelData, ConceptModelOut
from app.services.concept_model import (
    apply_concept_positions,
    build_concept_model_from_snapshot,
    count_stats,
)
from app.services.llm_service import settings_from_config

router = APIRouter(prefix="/api", tags=["concept-models"])


def _latest_snapshot(db: Session, project_id: int) -> SchemaSnapshot | None:
    return (
        db.query(SchemaSnapshot)
        .filter(SchemaSnapshot.project_id == project_id)
        .order_by(SchemaSnapshot.version.desc())
        .first()
    )


def _relationships(db: Session, project_id: int) -> list[dict]:
    rels = db.query(Relationship).filter(Relationship.project_id == project_id).all()
    return [
        {
            "source_table": r.source_table,
            "source_column": r.source_column,
            "target_table": r.target_table,
            "target_column": r.target_column,
            "cardinality": r.cardinality,
            "confidence": r.confidence,
            "source_type": r.source_type,
            "status": r.status,
        }
        for r in rels
    ]


def _store_model(db: Session, project_id: int, model_data: dict) -> ConceptModel:
    model = (
        db.query(ConceptModel)
        .filter(ConceptModel.project_id == project_id)
        .order_by(ConceptModel.id.desc())
        .first()
    )
    if model:
        model.model_data = model_data
    else:
        model = ConceptModel(project_id=project_id, model_data=model_data)
        db.add(model)
    db.commit()
    db.refresh(model)
    return model


@router.get("/projects/{project_id}/concept-model", response_model=ConceptModelOut | None)
def get_concept_model(project_id: int, db: Session = Depends(get_db)):
    """Return the stored concept model for a project (if any)."""
    model = (
        db.query(ConceptModel)
        .filter(ConceptModel.project_id == project_id)
        .order_by(ConceptModel.id.desc())
        .first()
    )
    return model


@router.post(
    "/projects/{project_id}/concept-model/convert",
    response_model=ConceptModelOut,
)
def convert_concept_model(
    project_id: int,
    payload: ConceptModelConvert = Body(default=ConceptModelConvert()),
    db: Session = Depends(get_db),
):
    """Convert the latest physical snapshot + relationships into a concept model."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    snapshot = _latest_snapshot(db, project_id)
    if not snapshot or not snapshot.snapshot_data:
        raise HTTPException(status_code=400, detail="该项目尚无 Schema 快照，请先同步或导入")

    llm_settings = None
    if payload.use_ai_names:
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
            llm_settings = settings_from_config(llm_config)

    model_data = build_concept_model_from_snapshot(
        snapshot.snapshot_data,
        _relationships(db, project_id),
        use_ai_names=payload.use_ai_names,
        llm_settings=llm_settings,
    )
    return _store_model(db, project_id, model_data)


@router.put("/projects/{project_id}/concept-model", response_model=ConceptModelOut)
def save_concept_model(
    project_id: int,
    payload: ConceptModelData,
    db: Session = Depends(get_db),
):
    """Save an edited concept model (positions, renamed relations, ...)."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    model_data = {
        "entities": payload.entities,
        "relations": payload.relations,
        "viewport": payload.viewport,
    }
    return _store_model(db, project_id, model_data)


@router.post("/projects/{project_id}/concept-model/positions", response_model=dict)
def save_concept_positions(
    project_id: int,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
):
    """Merge dragged node positions into the stored concept model (lightweight save)."""
    model = (
        db.query(ConceptModel)
        .filter(ConceptModel.project_id == project_id)
        .order_by(ConceptModel.id.desc())
        .first()
    )
    if not model or not model.model_data:
        raise HTTPException(status_code=404, detail="暂无概念模型，请先转换")
    positions = payload.get("positions") or {}
    model.model_data = apply_concept_positions(model.model_data, positions)
    if payload.get("viewport"):
        model.model_data["viewport"] = payload["viewport"]
    db.commit()
    db.refresh(model)
    return {"ok": True, "stats": count_stats(model.model_data)}
