"""Business-domain clustering router (feature 9)."""
from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DomainCluster, LLMConfig, Project, Relationship, SchemaSnapshot
from app.schemas import DomainAnalyze, DomainOut
from app.services.domain_cluster import analyze_domains
from app.services.llm_service import settings_from_config
from app.services.schema_parser import schema_from_dict

router = APIRouter(prefix="/api", tags=["domains"])


def _relationships(db: Session, project_id: int) -> list[dict]:
    rels = db.query(Relationship).filter(Relationship.project_id == project_id).all()
    return [
        {
            "source_table": r.source_table,
            "target_table": r.target_table,
            "source_type": r.source_type,
            "status": r.status,
        }
        for r in rels
    ]


def _to_out(cluster: DomainCluster) -> DomainOut:
    return DomainOut(
        cluster_index=cluster.cluster_index,
        name=cluster.name,
        description=cluster.description,
        tables=cluster.tables or [],
    )


@router.post("/projects/{project_id}/domains/analyze", response_model=list[DomainOut])
def analyze(
    project_id: int,
    payload: DomainAnalyze = Body(default=DomainAnalyze()),
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

    llm_settings = None
    if payload.use_ai_names:
        config = None
        if payload.llm_config_id:
            config = db.get(LLMConfig, payload.llm_config_id)
            if not config:
                raise HTTPException(status_code=404, detail="LLM 配置不存在")
        else:
            config = (
                db.query(LLMConfig)
                .filter(LLMConfig.is_default.is_(True))
                .order_by(LLMConfig.id.asc())
                .first()
            ) or db.query(LLMConfig).order_by(LLMConfig.id.asc()).first()
        if config:
            llm_settings = settings_from_config(config)

    schema = schema_from_dict(snapshot.snapshot_data)
    clusters = analyze_domains(
        schema,
        _relationships(db, project_id),
        use_ai_names=payload.use_ai_names,
        llm_settings=llm_settings,
        lang=payload.lang,
    )

    db.query(DomainCluster).filter(DomainCluster.project_id == project_id).delete()
    for c in clusters:
        db.add(
            DomainCluster(
                project_id=project_id,
                cluster_index=c["cluster_index"],
                name=c["name"],
                description=c.get("description"),
                tables=c["tables"],
            )
        )
    db.commit()
    return clusters


@router.get("/projects/{project_id}/domains", response_model=list[DomainOut])
def list_domains(project_id: int, db: Session = Depends(get_db)):
    """Return stored clusters; compute deterministically on the fly if none stored."""
    rows = (
        db.query(DomainCluster)
        .filter(DomainCluster.project_id == project_id)
        .order_by(DomainCluster.cluster_index)
        .all()
    )
    if rows:
        return [_to_out(r) for r in rows]
    snapshot = (
        db.query(SchemaSnapshot)
        .filter(SchemaSnapshot.project_id == project_id)
        .order_by(SchemaSnapshot.version.desc())
        .first()
    )
    if not snapshot or not snapshot.snapshot_data:
        return []
    schema = schema_from_dict(snapshot.snapshot_data)
    clusters = analyze_domains(schema, _relationships(db, project_id))
    return [
        {
            "cluster_index": c["cluster_index"],
            "name": c["name"],
            "description": c.get("description"),
            "tables": c["tables"],
        }
        for c in clusters
    ]
