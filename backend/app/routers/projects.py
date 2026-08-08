"""Project management router - CRUD for analysis projects."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DatabaseConnection, Project, Relationship, SchemaSnapshot, SchemaTable
from app.schemas import ProjectCreate, ProjectOut, ProjectUpdate

router = APIRouter(prefix="/api", tags=["projects"])


def _enrich(p: Project, db: Session) -> ProjectOut:
    table_count = (
        db.query(SchemaTable)
        .join(SchemaSnapshot, SchemaTable.snapshot_id == SchemaSnapshot.id)
        .filter(SchemaSnapshot.project_id == p.id)
        .count()
    )
    rel_count = db.query(Relationship).filter(Relationship.project_id == p.id).count()
    suggestion_count = (
        db.query(Relationship)
        .filter(Relationship.project_id == p.id)
        .filter(Relationship.source_type == "ai_suggestion")
        .count()
    )
    connection = (
        db.query(DatabaseConnection)
        .filter(DatabaseConnection.project_id == p.id)
        .order_by(DatabaseConnection.id.desc())
        .first()
    )
    return ProjectOut(
        id=p.id,
        name=p.name,
        description=p.description,
        status=p.status,
        created_at=p.created_at,
        updated_at=p.updated_at,
        tables=table_count,
        relations=rel_count,
        suggestions=suggestion_count,
        db_type=connection.db_type if connection else None,
    )


@router.post("/projects", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    project = Project(name=payload.name, description=payload.description, status="created")
    db.add(project)
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"创建项目失败: {exc}") from exc
    db.refresh(project)
    return _enrich(project, db)


@router.get("/projects", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    projects = db.query(Project).order_by(Project.updated_at.desc()).all()
    return [_enrich(p, db) for p in projects]


@router.get("/projects/stats", response_model=dict)
def get_project_stats(db: Session = Depends(get_db)):
    projects = db.query(Project).all()
    total_projects = len(projects)

    total_tables = 0
    total_relations = 0
    ai_suggestions = 0

    for p in projects:
        table_count = (
            db.query(SchemaTable)
            .join(SchemaSnapshot, SchemaTable.snapshot_id == SchemaSnapshot.id)
            .filter(SchemaSnapshot.project_id == p.id)
            .count()
        )
        total_tables += table_count

        rel_count = db.query(Relationship).filter(Relationship.project_id == p.id).count()
        total_relations += rel_count

        sug_count = (
            db.query(Relationship)
            .filter(Relationship.project_id == p.id)
            .filter(Relationship.source_type == "ai_suggestion")
            .count()
        )
        ai_suggestions += sug_count

    return {
        "total_projects": total_projects,
        "total_tables": total_tables,
        "total_relations": total_relations,
        "ai_suggestions": ai_suggestions,
    }


@router.get("/projects/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return _enrich(project, db)


@router.patch("/projects/{project_id}", response_model=ProjectOut)
def update_project(project_id: int, payload: ProjectUpdate, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(project, key, value)
    db.commit()
    db.refresh(project)
    return _enrich(project, db)


@router.delete("/projects/{project_id}", response_model=dict)
def delete_project(project_id: int, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    db.delete(project)
    db.commit()
    return {"message": "项目已删除", "id": project_id}
