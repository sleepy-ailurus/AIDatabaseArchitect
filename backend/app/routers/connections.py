"""Database connection management router - test and persist MySQL configs."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DatabaseConnection, Project
from app.schemas import ConnectionCreate, ConnectionOut, ConnectionTest, ConnectionTestResult
from app.services import crypto
from app.services.schema_parser import test_connection as parse_test_connection

router = APIRouter(prefix="/api", tags=["database-connections"])


def _to_out(conn: DatabaseConnection) -> ConnectionOut:
    return ConnectionOut(
        id=conn.id,
        project_id=conn.project_id,
        db_type=conn.db_type,
        host=conn.host,
        port=conn.port,
        database_name=conn.database_name,
        username=conn.username,
        ssl_config=conn.ssl_config,
        timeout=conn.timeout,
        created_at=conn.created_at,
        has_password=bool(conn.password_encrypted),
    )


@router.post("/database-connections/test", response_model=ConnectionTestResult)
def test_db_connection(payload: ConnectionTest):
    """Test a MySQL/PostgreSQL connection without persisting it."""
    ssl_enabled = bool(payload.ssl_config and payload.ssl_config.enabled)
    ca = payload.ssl_config.ca if payload.ssl_config else None
    result = parse_test_connection(
        db_type=str(payload.db_type),
        host=str(payload.host),
        port=int(payload.port),
        database=str(payload.database_name),
        username=str(payload.username),
        password=payload.password,
        ssl=ssl_enabled,
        timeout=int(payload.timeout),
        ca=ca,
    )
    return ConnectionTestResult(**result)


@router.post("/database-connections", response_model=ConnectionOut, status_code=status.HTTP_201_CREATED)
def create_connection(payload: ConnectionCreate, db: Session = Depends(get_db)):
    project = db.get(Project, payload.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    ssl_dict = payload.ssl_config.model_dump() if payload.ssl_config else None
    password_encrypted = crypto.encrypt(payload.password) if payload.save_credentials and payload.password else None

    conn = DatabaseConnection(
        project_id=payload.project_id,
        db_type=str(payload.db_type),
        host=str(payload.host),
        port=int(payload.port),
        database_name=str(payload.database_name),
        username=str(payload.username),
        password_encrypted=password_encrypted,
        ssl_config=ssl_dict,
        timeout=int(payload.timeout),
    )
    db.add(conn)
    db.commit()
    db.refresh(conn)
    return _to_out(conn)


@router.delete("/database-connections/{connection_id}", response_model=dict)
def delete_connection(connection_id: int, db: Session = Depends(get_db)):
    conn = db.get(DatabaseConnection, connection_id)
    if not conn:
        raise HTTPException(status_code=404, detail="连接配置不存在")
    db.delete(conn)
    db.commit()
    return {"message": "连接配置已删除", "id": connection_id}


@router.get("/projects/{project_id}/database-connection", response_model=ConnectionOut | None)
def get_project_connection(project_id: int, db: Session = Depends(get_db)):
    """Return the latest connection config for a project (password never exposed)."""
    conn = (
        db.query(DatabaseConnection)
        .filter(DatabaseConnection.project_id == project_id)
        .order_by(DatabaseConnection.id.desc())
        .first()
    )
    if not conn:
        return None
    return _to_out(conn)
