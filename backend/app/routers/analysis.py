"""Analysis task router - orchestrates the AI relation-analysis workflow.

Workflow (LangGraph-backed, see app/services/workflow.py):
  schema_load -> normalizer -> candidate_gen ->
       [llm_agent | skip_llm] -> result_validator ->
       confidence_classifier -> persist_suggestions -> END

The analysis runs in a FastAPI background task so the create endpoint returns
immediately with a pending task; the GET endpoint reports progress.
"""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.models import AnalysisTask, LLMConfig, Project, Relationship, SchemaSnapshot
from app.schemas import AnalysisTaskCreate, AnalysisTaskOut
from app.services.llm_service import settings_from_config
from app.services.workflow import run_analysis_workflow

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


@router.post("/analysis-tasks/{task_id}/cancel", response_model=AnalysisTaskOut)
def cancel_analysis_task(task_id: int, db: Session = Depends(get_db)):
    task = db.get(AnalysisTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="分析任务不存在")
    if task.status in ("completed", "failed", "cancelled"):
        # Idempotent: the task already reached a terminal state. Returning the
        # task with 200 keeps the frontend cancel flow simple and avoids a
        # confusing 400 error when the user clicks cancel after a slow run
        # already finished/failed server-side.
        db.refresh(task)
        return task
    task.status = "cancelled"
    task.error = "用户取消了分析任务"
    db.commit()
    db.refresh(task)
    return task


# ---------------------------------------------------------------------------
# Background worker (orchestrated via LangGraph)
# ---------------------------------------------------------------------------
def _run_analysis(task_id: int, project_id: int, llm_config_id: int | None, run_llm: bool) -> None:
    db = SessionLocal()
    try:
        task = db.get(AnalysisTask, task_id)
        if not task:
            return

        task.status = "parsing"
        task.progress = 5
        db.commit()

        # Clear old AI suggestions before starting a fresh analysis.
        # Keep database constraints and user-created manual edges intact.
        deleted = (
            db.query(Relationship)
            .filter(
                Relationship.project_id == project_id,
                Relationship.source_type == "ai_suggestion",
            )
            .delete(synchronize_session=False)
        )
        if deleted:
            db.commit()

        # Also clear saved ER model so the canvas rebuilds from fresh data.
        from app.models import ERModel
        models = db.query(ERModel).filter(ERModel.project_id == project_id).all()
        for m in models:
            m.model_data = None
        if models:
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

        llm_settings = None
        if run_llm and llm_config_id:
            llm_config = db.get(LLMConfig, llm_config_id)
            if not llm_config:
                task.status = "failed"
                task.error = "LLM 配置不存在"
                db.commit()
                return
            llm_settings = settings_from_config(llm_config)

        existing_keys = {
            (
                r.source_table.lower(),
                r.source_column.lower(),
                r.target_table.lower(),
                r.target_column.lower(),
            )
            for r in db.query(Relationship).filter(Relationship.project_id == project_id).all()
        }
        snapshot_data = snapshot.snapshot_data

        # --- Pre-check (rule heuristic): skip LLM entirely when explicit FKs
        # already cover every discoverable logical relation. This is the case
        # the user raised: a project with 4 explicit FKs across 5 tables where
        # rule-based column-name matching finds zero new candidates; running
        # the LLM over it would burn tokens and still return zero suggestions.
        rule_total: int | None = None
        rule_uncovered: int | None = None
        try:
            from app.services.schema_parser import schema_from_dict
            from app.services.relation_candidate import (
                _extract_hint,
                generate_candidates,
                normalize_relationship_direction,
            )

            parsed_schema = schema_from_dict(snapshot_data)
            rule_candidates = generate_candidates(parsed_schema)
            rule_total = len(rule_candidates)
            rule_uncovered = 0
            for c in rule_candidates:
                st, sc, tt, tc, _card = normalize_relationship_direction(
                    c.source_table,
                    c.source_column,
                    c.target_table,
                    c.target_column,
                    c.cardinality,
                )
                key = (st.lower(), sc.lower(), tt.lower(), tc.lower())
                if key in existing_keys:
                    continue
                rule_uncovered += 1
        except Exception:
            # If pre-check fails for any reason, behave as if we couldn't pre-check
            # and let the full workflow continue below (fail-safe).
            rule_total = None
            rule_uncovered = None

        schema_table_names = {t.name.lower() for t in parsed_schema.tables}
        covered_tables: set[str] = set()
        for st, _sc, tt, _tc in existing_keys:
            covered_tables.add(st)
            covered_tables.add(tt)
        covered_tables &= schema_table_names
        table_count = len(schema_table_names)

        # A rule-uncovered column still worth an LLM discovery pass: the rules
        # matched some candidates (all already covered) but other reference-like
        # columns (xxx_id / xxx_code / ...) remain unconnected, or no rule
        # candidates were generated at all (abbreviations, semantic columns).
        # Only when every reference-like column already participates in an
        # existing relationship is the schema genuinely "full coverage" — in that
        # case both the rules and a free-form LLM call would only restate what we
        # already have, so we skip to save tokens.
        all_ref_columns_covered = True
        for t in parsed_schema.tables:
            for c in t.columns:
                if c.is_primary_key:
                    continue
                if _extract_hint(c.name) is None:
                    continue
                covered_col = any(
                    (t.name.lower() == st or t.name.lower() == tt)
                    and c.name.lower() in (sc, tc)
                    for st, sc, tt, tc in existing_keys
                )
                if not covered_col:
                    all_ref_columns_covered = False
                    break
            if not all_ref_columns_covered:
                break

        rules_exhausted = (rule_total is not None and rule_total > 0 and rule_uncovered == 0) or (
            rule_total is not None and rule_total == 0 and all_ref_columns_covered
        )

        # Fast path: the naming-convention coverage is truly exhaustive AND every
        # table already participates in some relationship. Skip the LLM call.
        if (
            rules_exhausted
            and table_count > 0
            and len(covered_tables) >= table_count
        ):
            db.close()
            sdb = SessionLocal()
            try:
                t = sdb.get(AnalysisTask, task_id)
                if t:
                    t.status = "completed"
                    t.progress = 100
                    t.error = None
                    t.result = {
                        "candidate_count": rule_total,
                        "suggestion_count": 0,
                        "used_llm": False,
                        "node_log": [
                            f"pre-check: rule candidates = {rule_total}",
                            f"pre-check: rule_uncovered = 0 — existing FKs already cover every rule-discoverable relation",
                            "workflow/LLM skipped (saved tokens & latency)",
                        ],
                        "skipped_reason": "fk_coverage_full",
                    }
                    sdb.commit()
            finally:
                sdb.close()
            return

        # Close the long-living session before invoking the workflow; nodes
        # create their own sessions via SessionLocal. This keeps the task-row
        # updates isolated from relationship writes.
        db.close()

        def progress_cb(status: str, pct: int, error: str | None) -> None:
            sdb = SessionLocal()
            try:
                t = sdb.get(AnalysisTask, task_id)
                if not t:
                    return
                if t.status == "cancelled":
                    sdb.close()
                    raise RuntimeError("Task cancelled by user")
                t.status = status or t.status
                t.progress = pct
                if error and status == "failed":
                    t.error = error
                sdb.commit()
            finally:
                sdb.close()

        summary = run_analysis_workflow(
            project_id=project_id,
            snapshot_data=snapshot_data,
            llm_settings=llm_settings,
            run_llm=run_llm,
            existing_keys=existing_keys,
            db_session_factory=SessionLocal,
            task_id=task_id,
            progress=progress_cb,
        )

        # Final status write.
        sdb = SessionLocal()
        try:
            t = sdb.get(AnalysisTask, task_id)
            if not t:
                return
            if t.status == "cancelled":
                # User cancelled while the workflow was finishing; never
                # overwrite the cancelled state with a late result.
                return
            if summary.get("error"):
                t.status = "failed"
                t.error = summary["error"]
                t.progress = t.progress or 0
            else:
                t.status = "completed"
                t.progress = 100
                t.error = None
                t.result = {
                    "candidate_count": summary.get("candidate_count", 0),
                    "suggestion_count": summary.get("suggestion_count", 0),
                    "filtered_existing_count": summary.get("filtered_existing_count", 0),
                    "used_llm": summary.get("used_llm", False),
                    "node_log": summary.get("node_log") or [],
                }
                project = sdb.get(Project, project_id)
                if project:
                    project.status = "analyzed"
            sdb.commit()
        finally:
            sdb.close()
    except Exception as exc:
        try:
            sdb = SessionLocal()
            task = sdb.get(AnalysisTask, task_id)
            if task and task.status != "cancelled":
                task.status = "failed"
                task.error = f"分析任务异常: {exc}"
                sdb.commit()
        finally:
            sdb.close()
    finally:
        # Best-effort cleanup: ensure the original session handle is closed.
        try:
            db.close()
        except Exception:
            pass
