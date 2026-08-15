"""AI comment suggestions + data dictionary export router (feature 3)."""
from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    CommentSuggestion,
    DatabaseConnection,
    LLMConfig,
    Project,
    SchemaSnapshot,
)
from app.schemas import (
    CommentApply,
    CommentBatchUpdate,
    CommentGenerate,
    CommentSuggestionOut,
    CommentUpdate,
)
from app.services import crypto
from app.services.comment_service import (
    build_writeback_sql,
    generate_comment_suggestions,
)
from app.services.dictionary_export import (
    export_excel,
    export_markdown,
    export_word,
)
from app.services.llm_service import settings_from_config
from app.services.schema_parser import schema_from_dict

router = APIRouter(prefix="/api", tags=["comments"])


def _get_snapshot(db: Session, project_id: int) -> SchemaSnapshot:
    snapshot = (
        db.query(SchemaSnapshot)
        .filter(SchemaSnapshot.project_id == project_id)
        .order_by(SchemaSnapshot.version.desc())
        .first()
    )
    if not snapshot or not snapshot.snapshot_data:
        raise HTTPException(status_code=400, detail="该项目尚无 Schema 快照，请先同步或导入")
    return snapshot


def _resolve_llm(db: Session, llm_config_id: int | None) -> LLMConfig:
    if llm_config_id:
        config = db.get(LLMConfig, llm_config_id)
        if not config:
            raise HTTPException(status_code=404, detail="LLM 配置不存在")
        return config
    config = (
        db.query(LLMConfig)
        .filter(LLMConfig.is_default.is_(True))
        .order_by(LLMConfig.id.asc())
        .first()
    ) or db.query(LLMConfig).order_by(LLMConfig.id.asc()).first()
    if not config:
        raise HTTPException(status_code=400, detail="请先配置 LLM")
    return config


@router.post(
    "/projects/{project_id}/comment-suggestions/generate",
    response_model=dict,
)
def generate_suggestions(
    project_id: int,
    payload: CommentGenerate = Body(default=CommentGenerate()),
    db: Session = Depends(get_db),
):
    """Generate AI comment suggestions for tables/columns missing comments."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    snapshot = _get_snapshot(db, project_id)
    config = _resolve_llm(db, payload.llm_config_id)

    schema = schema_from_dict(snapshot.snapshot_data)
    result = generate_comment_suggestions(schema, settings_from_config(config))

    # Clear previous suggestions before persisting fresh ones.
    db.query(CommentSuggestion).filter(CommentSuggestion.project_id == project_id).delete()
    for item in result["tables"]:
        db.add(
            CommentSuggestion(
                project_id=project_id,
                table_name=item["name"],
                column_name=None,
                target_type="table",
                suggested_comment=item["comment"],
                status="suggested",
            )
        )
    for item in result["columns"]:
        db.add(
            CommentSuggestion(
                project_id=project_id,
                table_name=item["table"],
                column_name=item["column"],
                target_type="column",
                suggested_comment=item["comment"],
                status="suggested",
            )
        )
    db.commit()
    return {
        "success": True,
        "table_count": len(result["tables"]),
        "column_count": len(result["columns"]),
        "errors": result["errors"],
    }


@router.get(
    "/projects/{project_id}/comment-suggestions",
    response_model=list[CommentSuggestionOut],
)
def list_suggestions(
    project_id: int,
    status: str | None = None,
    target_type: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(CommentSuggestion).filter(CommentSuggestion.project_id == project_id)
    if status:
        query = query.filter(CommentSuggestion.status == status)
    if target_type:
        query = query.filter(CommentSuggestion.target_type == target_type)
    return query.order_by(CommentSuggestion.target_type, CommentSuggestion.table_name).all()


@router.patch("/comment-suggestions/{suggestion_id}", response_model=CommentSuggestionOut)
def update_suggestion(suggestion_id: int, payload: CommentUpdate, db: Session = Depends(get_db)):
    row = db.get(CommentSuggestion, suggestion_id)
    if not row:
        raise HTTPException(status_code=404, detail="建议不存在")
    if payload.status not in ("suggested", "accepted", "rejected"):
        raise HTTPException(status_code=400, detail="无效的状态")
    row.status = payload.status
    db.commit()
    db.refresh(row)
    return row


@router.post(
    "/projects/{project_id}/comment-suggestions/batch",
    response_model=dict,
)
def batch_update(
    project_id: int,
    payload: CommentBatchUpdate,
    db: Session = Depends(get_db),
):
    if payload.status not in ("suggested", "accepted", "rejected"):
        raise HTTPException(status_code=400, detail="无效的状态")
    rows = (
        db.query(CommentSuggestion)
        .filter(
            CommentSuggestion.project_id == project_id,
            CommentSuggestion.id.in_(payload.ids),
        )
        .all()
    )
    for row in rows:
        row.status = payload.status
    db.commit()
    return {"updated": len(rows)}


@router.post("/projects/{project_id}/comment-suggestions/apply", response_model=dict)
def apply_suggestions(
    project_id: int,
    payload: CommentApply = Body(default=CommentApply()),
    db: Session = Depends(get_db),
):
    """Build write-back SQL for accepted suggestions; optionally execute it."""
    snapshot = _get_snapshot(db, project_id)
    schema = schema_from_dict(snapshot.snapshot_data)
    accepted = (
        db.query(CommentSuggestion)
        .filter(
            CommentSuggestion.project_id == project_id,
            CommentSuggestion.status == "accepted",
        )
        .all()
    )
    if not accepted:
        raise HTTPException(status_code=400, detail="没有已接受的注释建议")

    conn = (
        db.query(DatabaseConnection)
        .filter(DatabaseConnection.project_id == project_id)
        .order_by(DatabaseConnection.id.desc())
        .first()
    )
    db_type = conn.db_type if conn else "mysql"
    stmts = build_writeback_sql(
        schema,
        [
            {
                "target_type": r.target_type,
                "table_name": r.table_name,
                "column_name": r.column_name,
                "suggested_comment": r.suggested_comment,
            }
            for r in accepted
        ],
        db_type=db_type,
    )

    executed = 0
    errors: list[str] = []
    if payload.execute:
        if not conn:
            raise HTTPException(status_code=400, detail="该项目未配置数据库连接，无法执行写回")
        password = crypto.decrypt(conn.password_encrypted)
        from sqlalchemy import create_engine, text

        url, connect_args, ca_file = __import__(
            "app.services.schema_parser", fromlist=["build_db_url"]
        ).build_db_url(
            str(conn.db_type),
            conn.host,
            conn.port,
            conn.database_name,
            conn.username,
            password,
            bool(conn.ssl_config and conn.ssl_config.get("enabled")),
            conn.timeout,
            conn.ssl_config.get("ca") if conn.ssl_config else None,
        )
        engine = create_engine(url, connect_args=connect_args, pool_pre_ping=True)
        try:
            with engine.begin() as tx:
                for stmt in stmts:
                    tx.execute(text(stmt))
                    executed += 1
        except Exception as exc:
            errors.append(str(exc))
        finally:
            engine.dispose()

    # Mark applied suggestions as applied.
    for row in accepted:
        row.status = "applied"
    db.commit()
    return {"sql": stmts, "statement_count": len(stmts), "executed": executed, "errors": errors}


@router.get("/projects/{project_id}/dictionary/export")
def export_dictionary(
    project_id: int,
    format: str = Query(default="markdown", pattern="^(markdown|excel|word)$"),
    db: Session = Depends(get_db),
):
    """Export the data dictionary (Markdown / Excel / Word / PDF)."""
    snapshot = _get_snapshot(db, project_id)
    schema = schema_from_dict(snapshot.snapshot_data)
    accepted = (
        db.query(CommentSuggestion)
        .filter(
            CommentSuggestion.project_id == project_id,
            CommentSuggestion.status.in_(("accepted", "applied")),
        )
        .all()
    )
    accepted_dicts = [
        {
            "target_type": r.target_type,
            "table_name": r.table_name,
            "column_name": r.column_name,
            "suggested_comment": r.suggested_comment,
        }
        for r in accepted
    ]

    filename = f"data-dictionary-{project_id}"
    if format == "excel":
        content = export_excel(schema, accepted_dicts)
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename += ".xlsx"
    elif format == "word":
        content = export_word(schema, accepted_dicts)
        media = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        filename += ".docx"
    else:
        content = export_markdown(schema, accepted_dicts).encode("utf-8")
        media = "text/markdown; charset=utf-8"
        filename += ".md"

    return Response(
        content=content,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
