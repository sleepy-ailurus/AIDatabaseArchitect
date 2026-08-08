"""Analysis task router - orchestrates the AI relation-analysis workflow.

Workflow:
  pending -> parsing -> analyzing -> validating -> completed
                                  --> failed
                                  --> cancelled

The analysis runs in a FastAPI background task so the create endpoint returns
immediately with a pending task; the GET endpoint reports progress.
"""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.models import AnalysisTask, LLMConfig, Project, Relationship, SchemaSnapshot
from app.schemas import AnalysisTaskCreate, AnalysisTaskOut
from app.services.llm_service import LLMError, analyze_candidates, settings_from_config
from app.services.relation_candidate import generate_candidates
from app.services.schema_parser import schema_from_dict

router = APIRouter(prefix="/api", tags=["analysis"])


@router.post(
    "/projects/{project_id}/analysis-tasks",
    response_model=AnalysisTaskOut,
    status_code=status.HTTP_201_CREATED,
)
def create_analysis_task(
    project_id: int,
    payload: AnalysisTaskCreate,
    background_tasks: BackgroundTasks,
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
    if not snapshot:
        raise HTTPException(status_code=400, detail="该项目尚无 Schema 快照，请先同步")

    llm_config = None
    if payload.run_llm:
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

    task = AnalysisTask(
        project_id=project_id,
        status="pending",
        progress=0,
        llm_config_id=llm_config.id if llm_config else None,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    background_tasks.add_task(
        _run_analysis,
        task_id=task.id,
        project_id=project_id,
        llm_config_id=llm_config.id if llm_config else None,
        run_llm=payload.run_llm and llm_config is not None,
    )
    return task


@router.get("/analysis-tasks/{task_id}", response_model=AnalysisTaskOut)
def get_analysis_task(task_id: int, db: Session = Depends(get_db)):
    task = db.get(AnalysisTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="分析任务不存在")
    return task


@router.get("/projects/{project_id}/analysis-tasks", response_model=list[AnalysisTaskOut])
def list_analysis_tasks(project_id: int, db: Session = Depends(get_db)):
    return (
        db.query(AnalysisTask)
        .filter(AnalysisTask.project_id == project_id)
        .order_by(AnalysisTask.created_at.desc())
        .all()
    )


@router.get("/projects/{project_id}/analysis-tasks/latest", response_model=AnalysisTaskOut | None)
def get_latest_analysis(project_id: int, db: Session = Depends(get_db)):
    task = (
        db.query(AnalysisTask)
        .filter(AnalysisTask.project_id == project_id)
        .order_by(AnalysisTask.created_at.desc())
        .first()
    )
    return task


# ---------------------------------------------------------------------------
# Background worker
# ---------------------------------------------------------------------------
def _run_analysis(task_id: int, project_id: int, llm_config_id: int | None, run_llm: bool) -> None:
    db = SessionLocal()
    try:
        task = db.get(AnalysisTask, task_id)
        if not task:
            return

        # --- parsing ---
        task.status = "parsing"
        task.progress = 10
        db.commit()

        snapshot = (
            db.query(SchemaSnapshot)
            .filter(SchemaSnapshot.project_id == project_id)
            .order_by(SchemaSnapshot.version.desc())
            .first()
        )
        if not snapshot or not snapshot.snapshot_data:
            task.status = "failed"
            task.error = "未找到可用的 Schema 快照"
            db.commit()
            return

        schema = schema_from_dict(snapshot.snapshot_data)

        # --- analyzing (rule-based candidate generation) ---
        task.status = "analyzing"
        task.progress = 40
        db.commit()

        candidates = generate_candidates(schema)

        existing_keys = {
            (
                r.source_table.lower(),
                r.source_column.lower(),
                r.target_table.lower(),
                r.target_column.lower(),
            )
            for r in db.query(Relationship).filter(Relationship.project_id == project_id).all()
        }

        suggestion_count = 0

        if run_llm and llm_config_id:
            llm_config = db.get(LLMConfig, llm_config_id)
            if not llm_config:
                task.status = "failed"
                task.error = "LLM 配置不存在"
                db.commit()
                return

            # --- validating (LLM analysis) ---
            task.status = "validating"
            task.progress = 70
            db.commit()

            try:
                settings = settings_from_config(llm_config)
                results = analyze_candidates(schema, candidates, settings)
            except LLMError as exc:
                task.status = "failed"
                task.error = str(exc)
                db.commit()
                return
            except Exception as exc:
                task.status = "failed"
                task.error = f"LLM 调用异常: {exc}"
                db.commit()
                return

            for res in results:
                if not res.valid:
                    continue
                key = (
                    res.source_table.lower(),
                    res.source_column.lower(),
                    res.target_table.lower(),
                    res.target_column.lower(),
                )
                if key in existing_keys:
                    continue
                existing_keys.add(key)
                reasons = list(res.reason) or []
                if res.risks:
                    reasons.append("风险: " + "; ".join(res.risks))
                db.add(
                    Relationship(
                        project_id=project_id,
                        source_table=res.source_table,
                        source_column=res.source_column,
                        target_table=res.target_table,
                        target_column=res.target_column,
                        cardinality=res.cardinality,
                        confidence=res.confidence,
                        source_type="ai_suggestion",
                        status="suggested",
                        reason=reasons,
                    )
                )
                suggestion_count += 1
        else:
            # No LLM: persist rule-based candidates as ai_suggestion directly.
            for cand in candidates:
                key = (
                    cand.source_table.lower(),
                    cand.source_column.lower(),
                    cand.target_table.lower(),
                    cand.target_column.lower(),
                )
                if key in existing_keys:
                    continue
                existing_keys.add(key)
                db.add(
                    Relationship(
                        project_id=project_id,
                        source_table=cand.source_table,
                        source_column=cand.source_column,
                        target_table=cand.target_table,
                        target_column=cand.target_column,
                        cardinality=cand.cardinality,
                        confidence=cand.confidence,
                        source_type="ai_suggestion",
                        status="suggested",
                        reason=cand.reason,
                    )
                )
                suggestion_count += 1

        project = db.get(Project, project_id)
        if project:
            project.status = "analyzed"

        task.status = "completed"
        task.progress = 100
        task.result = {
            "candidate_count": len(candidates),
            "suggestion_count": suggestion_count,
            "used_llm": run_llm and llm_config_id is not None,
        }
        db.commit()
    except Exception as exc:
        db.rollback()
        try:
            task = db.get(AnalysisTask, task_id)
            if task:
                task.status = "failed"
                task.error = f"分析任务异常: {exc}"
                db.commit()
        except Exception:
            pass
    finally:
        db.close()
