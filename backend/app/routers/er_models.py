"""ER model router - save/load models with node positions and version history."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ERModel, ERModelVersion, Project
from app.schemas import ERModelData, ERModelOut, ERModelVersionOut

router = APIRouter(prefix="/api", tags=["er-models"])


@router.get("/projects/{project_id}/er-models", response_model=ERModelOut | None)
def get_er_model(project_id: int, db: Session = Depends(get_db)):
    """Return the latest ER model for a project (if any)."""
    model = (
        db.query(ERModel)
        .filter(ERModel.project_id == project_id)
        .order_by(ERModel.id.desc())
        .first()
    )
    if not model:
        return None
    return model


@router.put("/projects/{project_id}/er-models", response_model=ERModelOut)
def save_er_model(project_id: int, payload: ERModelData, db: Session = Depends(get_db)):
    """Create or update the ER model for a project."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    model = (
        db.query(ERModel)
        .filter(ERModel.project_id == project_id)
        .order_by(ERModel.id.desc())
        .first()
    )
    model_data = {
        "nodes": payload.nodes,
        "edges": payload.edges,
        "viewport": payload.viewport,
    }
    if model:
        model.model_data = model_data
    else:
        model = ERModel(project_id=project_id, model_data=model_data)
        db.add(model)
    db.commit()
    db.refresh(model)
    return model


@router.post(
    "/projects/{project_id}/er-models/versions",
    response_model=ERModelVersionOut,
    status_code=status.HTTP_201_CREATED,
)
def save_er_model_version(project_id: int, db: Session = Depends(get_db)):
    """Snapshot the current ER model as a versioned backup."""
    model = (
        db.query(ERModel)
        .filter(ERModel.project_id == project_id)
        .order_by(ERModel.id.desc())
        .first()
    )
    if not model:
        raise HTTPException(status_code=404, detail="该项目尚无 ER 模型，无法保存版本")

    last_version = (
        db.query(ERModelVersion)
        .filter(ERModelVersion.model_id == model.id)
        .order_by(ERModelVersion.version_number.desc())
        .first()
    )
    next_version = (last_version.version_number + 1) if last_version else 1

    version = ERModelVersion(
        model_id=model.id,
        version_data=model.model_data,
        version_number=next_version,
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    return version


@router.get("/projects/{project_id}/er-models/versions", response_model=list[ERModelVersionOut])
def list_er_model_versions(project_id: int, db: Session = Depends(get_db)):
    model = (
        db.query(ERModel)
        .filter(ERModel.project_id == project_id)
        .order_by(ERModel.id.desc())
        .first()
    )
    if not model:
        return []
    versions = (
        db.query(ERModelVersion)
        .filter(ERModelVersion.model_id == model.id)
        .order_by(ERModelVersion.version_number.desc())
        .all()
    )
    return versions


@router.get("/er-models/versions/{version_id}", response_model=ERModelVersionOut)
def get_er_model_version(version_id: int, db: Session = Depends(get_db)):
    version = db.get(ERModelVersion, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="版本不存在")
    return version
