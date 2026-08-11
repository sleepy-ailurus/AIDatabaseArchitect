"""LangGraph-based Agent Workflow for AI relation analysis.

Workflow topology (see ai_sql_完整版.md §7):

    schema_load_node
        └─► normalizer_node
              └─► candidate_gen_node
                    └─► (run_llm ? relation_analysis_agent_node : skip_llm_node)
                           └─► result_validator_node
                                 └─► confidence_classifier_node
                                       └─► persist_suggestions_node

The orchestration is NOT fully autonomous. Instead:
- *Schema Parser / Normalizer / Candidate Generator* are pure-programmatic nodes
  with deterministic output.
- *Relation Analysis Agent* is the only LLM-powered node, whose output is
  bounded to the candidate list (the LLM cannot invent relationships outside
  the candidate set) and is validated by a Pydantic-style schema checker.
- *Confidence Classifier* routes results to `auto_suggested` or
  `manual_review_required` buckets, but everything still passes through a
  human-confirmation step on the frontend.
- *Persist Suggestions* writes valid relationships as `ai_suggestion / suggested`
  rows so they show up in the ER editor's "AI Suggestions" panel.

Progress callbacks are routed to the caller via an optional on_progress hook
so the AnalysisTask row's status/progress columns stay in sync with the graph.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any, Callable, TypedDict

from langgraph.graph import END, START, StateGraph

from app.services.llm_service import (
    LLMError,
    LLMSettings,
    analyze_candidates,
)
from app.services.relation_candidate import (
    CandidateRelation,
    candidate_to_dict,
    generate_candidates,
    normalize_relationship_direction,
)
from app.services.schema_parser import ParsedSchema, schema_from_dict


# ---------------------------------------------------------------------------
# State definition
# ---------------------------------------------------------------------------
class WorkflowState(TypedDict, total=False):
    """State passed between LangGraph nodes.

    Fields are optional so nodes can emit only deltas; LangGraph merges them
    into the latest snapshot.
    """

    # --- inputs (set by caller) ---
    project_id: int
    snapshot_data: dict | None
    llm_settings: LLMSettings | None
    run_llm: bool
    existing_keys: set[tuple[str, str, str, str]]

    # --- intermediate outputs ---
    raw_schema: ParsedSchema | None
    schema: ParsedSchema | None
    candidates: list[CandidateRelation]
    llm_results: list[dict]  # list of LLMRelationResult-like dicts

    # --- post validation ---
    validated_results: list[dict]
    high_confidence: list[dict]
    manual_review: list[dict]

    # --- summary ---
    node_log: list[str]
    error: str | None
    candidate_count: int
    suggestion_count: int
    used_llm: bool


# ---------------------------------------------------------------------------
# Progress callback type
# ---------------------------------------------------------------------------
ProgressCb = Callable[[str, int, str | None], None]
#     ProgressCb(status, progress_pct, error_message)


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------
def _log(state: WorkflowState, message: str) -> WorkflowState:
    log = list(state.get("node_log") or [])
    log.append(message)
    return {"node_log": log}


def schema_load_node(state: WorkflowState, progress: ProgressCb | None = None) -> WorkflowState:
    """Load snapshot_data dict into a ParsedSchema object."""
    progress and progress("parsing", 10, None)
    snap = state.get("snapshot_data") or {}
    try:
        schema = schema_from_dict(snap)
    except Exception as exc:
        if progress:
            progress("failed", 10, f"Schema 解析失败: {exc}")
        return {"error": f"Schema 解析失败: {exc}", **_log(state, "schema_load FAILED")}

    table_count = len(schema.tables)
    col_count = sum(len(t.columns) for t in schema.tables)
    out = {
        "raw_schema": schema,
        "schema": schema,
        **_log(state, f"schema_load OK: {table_count} tables, {col_count} columns"),
    }
    return out


def normalizer_node(state: WorkflowState, progress: ProgressCb | None = None) -> WorkflowState:
    """Normalize table/column names (already lower-cased for comparison inside
    ParsedSchema; here we simply propagate schema and compute some lightweight
    statistics so downstream nodes can treat schema as authoritative)."""
    progress and progress("parsing", 20, None)
    schema = state.get("schema") or state.get("raw_schema")
    if schema is None:
        if progress:
            progress("failed", 20, "Schema 未加载，无法归一化")
        return {"error": "Schema 未加载", **_log(state, "normalizer FAILED")}
    # Currently schema is already in canonical form after schema_from_dict.
    # If we later support PostgreSQL schemas / cross-schema lookups this is
    # where the cross-schema prefix should be attached.
    return {"schema": schema, **_log(state, "normalizer OK")}


def candidate_gen_node(state: WorkflowState, progress: ProgressCb | None = None) -> WorkflowState:
    """Run rule-based candidate generator."""
    progress and progress("analyzing", 40, None)
    schema = state.get("schema")
    if schema is None:
        if progress:
            progress("failed", 40, "Schema 未加载，无法生成候选")
        return {"error": "Schema 未加载", **_log(state, "candidate_gen FAILED")}
    candidates = generate_candidates(schema)
    return {
        "candidates": candidates,
        "candidate_count": len(candidates),
        **_log(state, f"candidate_gen OK: {len(candidates)} candidates"),
    }


def relation_analysis_agent_node(
    state: WorkflowState, progress: ProgressCb | None = None
) -> WorkflowState:
    """Core LLM agent node.

    Calls analyze_candidates() which sends the schema + candidate list to the
    LLM. The LLM is *not* free-form: it only marks pre-existing candidates
    as valid / invalid and assigns confidence/reason/risks. Output is
    structurally validated inside analyze_candidates() itself.
    """
    progress and progress("validating", 70, None)
    candidates = state.get("candidates") or []
    schema = state.get("schema")
    settings = state.get("llm_settings")

    if not schema or not settings:
        # Should have been gated by caller, but fail softly.
        if progress:
            progress("failed", 70, "Schema 或 LLM 配置缺失")
        return {
            "error": "Schema 或 LLM 配置缺失",
            **_log(state, "relation_analysis_agent FAILED: missing inputs"),
        }

    try:
        results = analyze_candidates(schema, candidates, settings)
    except LLMError as exc:
        if progress:
            progress("failed", 70, str(exc))
        return {
            "error": str(exc),
            **_log(state, f"relation_analysis_agent LLMError: {exc}"),
        }
    except Exception as exc:
        if progress:
            progress("failed", 70, f"LLM 调用异常: {exc}")
        return {
            "error": f"LLM 调用异常: {exc}",
            **_log(state, f"relation_analysis_agent Exception: {exc}"),
        }

    out = [_result_to_dict(r) for r in results]
    return {
        "llm_results": out,
        **_log(state, f"relation_analysis_agent OK: {len(out)} results"),
    }


def skip_llm_node(state: WorkflowState, progress: ProgressCb | None = None) -> WorkflowState:
    """Fallback branch when run_llm=False: translate candidates directly into
    pseudo-result dicts so the validator/classifier/persist pipeline stays
    uniform."""
    candidates = state.get("candidates") or []
    pseudo = []
    for c in candidates:
        pseudo.append(
            {
                "source_table": c.source_table,
                "source_column": c.source_column,
                "target_table": c.target_table,
                "target_column": c.target_column,
                "cardinality": c.cardinality,
                "confidence": c.confidence,
                "reason": list(c.reason) if c.reason else [],
                "risks": [],
                "valid": True,
                "validation_error": None,
            }
        )
    return {
        "llm_results": pseudo,
        **_log(state, f"skip_llm OK: {len(pseudo)} candidates passed through"),
    }


def result_validator_node(state: WorkflowState, progress: ProgressCb | None = None) -> WorkflowState:
    """Apply programmatic validation *after* LLM output has been produced.

    Inside analyze_candidates() we already run the same checks, but because
    skip_llm_node feeds rule-only candidates in we duplicate the guard here
    to ensure the uniform pipeline.
    """
    schema = state.get("schema")
    results = state.get("llm_results") or []

    validated: list[dict] = []
    filtered_existing = 0
    for r in results:
        if not r.get("valid"):
            continue
        key = (
            (r.get("source_table") or "").lower(),
            (r.get("source_column") or "").lower(),
            (r.get("target_table") or "").lower(),
            (r.get("target_column") or "").lower(),
        )
        if key in state.get("existing_keys", set()):
            filtered_existing += 1
            continue
        # Ensure referenced tables/columns exist in schema (cheap belt+suspenders
        # for skip_llm path).
        if schema is not None and not _ref_exists_in_schema(schema, r):
            continue
        validated.append(r)

    return {
        "validated_results": validated,
        "filtered_existing_count": filtered_existing,
        **_log(state, f"result_validator OK: {len(validated)} passed, {filtered_existing} already existed"),
    }


def confidence_classifier_node(state: WorkflowState, progress: ProgressCb | None = None) -> WorkflowState:
    """Split validated results into high-confidence (0.85+) and manual-review
    buckets. Thresholds are per §4.5.3 in the md doc.
    """
    validated = state.get("validated_results") or []
    high: list[dict] = []
    manual: list[dict] = []
    for r in validated:
        conf = float(r.get("confidence") or 0.0)
        if conf >= 0.85:
            high.append(r)
        else:
            manual.append(r)
    return {
        "high_confidence": high,
        "manual_review": manual,
        **_log(
            state,
            f"confidence_classifier OK: high={len(high)}, manual_review={len(manual)}",
        ),
    }


def persist_suggestions_node(
    state: WorkflowState,
    db_session_factory: Callable[[], Any],
    progress: ProgressCb | None = None,
) -> WorkflowState:
    """Write AI-suggested relationships into the `relationships` table.

    Both high-confidence and manual-review items are saved with
    source_type='ai_suggestion' and status='suggested' so users can confirm
    / reject them in the ER editor. Confidence is preserved.
    """
    progress and progress("validating", 90, None)
    project_id = state.get("project_id")
    high = state.get("high_confidence") or []
    manual = state.get("manual_review") or []
    all_results = [*high, *manual]

    seen: set[tuple[str, str, str, str]] = set(state.get("existing_keys") or set())
    written = 0
    db = db_session_factory()
    try:
        from app.models import Relationship

        for r in all_results:
            st, sc, tt, tc, card = normalize_relationship_direction(
                r.get("source_table") or "",
                r.get("source_column") or "",
                r.get("target_table") or "",
                r.get("target_column") or "",
                r.get("cardinality") or "many-to-one",
            )
            key = (st.lower(), sc.lower(), tt.lower(), tc.lower())
            if key in seen:
                continue
            seen.add(key)
            reasons = list(r.get("reason") or [])
            risks = r.get("risks") or []
            if risks:
                reasons.append("风险: " + "; ".join(risks))
            db.add(
                Relationship(
                    project_id=project_id,
                    source_table=st,
                    source_column=sc,
                    target_table=tt,
                    target_column=tc,
                    cardinality=card,
                    confidence=float(r.get("confidence") or 0.0),
                    source_type="ai_suggestion",
                    status="suggested",
                    reason=reasons or None,
                )
            )
            written += 1
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    if progress:
        progress("completed", 100, None)
    return {
        "suggestion_count": written,
        "used_llm": bool(state.get("run_llm")),
        **_log(state, f"persist_suggestions OK: {written} rows written"),
    }


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------
def _result_to_dict(res: Any) -> dict:
    """Convert LLMRelationResult dataclass → JSON-serializable dict."""
    if hasattr(res, "__dataclass_fields__"):
        return asdict(res)
    if isinstance(res, dict):
        return res
    # Last resort: try common attributes.
    return {
        "source_table": getattr(res, "source_table", None),
        "source_column": getattr(res, "source_column", None),
        "target_table": getattr(res, "target_table", None),
        "target_column": getattr(res, "target_column", None),
        "cardinality": getattr(res, "cardinality", None),
        "confidence": getattr(res, "confidence", None),
        "reason": list(getattr(res, "reason", []) or []),
        "risks": list(getattr(res, "risks", []) or []),
        "valid": getattr(res, "valid", True),
        "validation_error": getattr(res, "validation_error", None),
    }


def _ref_exists_in_schema(schema: ParsedSchema, result: dict) -> bool:
    src = next(
        (t for t in schema.tables if t.name.lower() == (result.get("source_table") or "").lower()),
        None,
    )
    tgt = next(
        (t for t in schema.tables if t.name.lower() == (result.get("target_table") or "").lower()),
        None,
    )
    if not src or not tgt:
        return False
    src_cols = {c.name.lower() for c in src.columns}
    tgt_cols = {c.name.lower() for c in tgt.columns}
    return (
        (result.get("source_column") or "").lower() in src_cols
        and (result.get("target_column") or "").lower() in tgt_cols
    )


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------
def _conditional_branch(state: WorkflowState) -> str:
    return "llm_agent" if state.get("run_llm") and state.get("llm_settings") else "skip_llm"


def build_workflow(
    db_session_factory: Callable[[], Any],
    progress: ProgressCb | None = None,
):
    """Construct a compiled LangGraph workflow.

    db_session_factory is bound at build time so persist_suggestions_node can
    obtain a DB session without leaking state into the graph.
    """
    builder = StateGraph(WorkflowState)

    builder.add_node(
        "schema_load",
        lambda state: schema_load_node(state, progress),
    )
    builder.add_node(
        "normalizer",
        lambda state: normalizer_node(state, progress),
    )
    builder.add_node(
        "candidate_gen",
        lambda state: candidate_gen_node(state, progress),
    )
    builder.add_node(
        "llm_agent",
        lambda state: relation_analysis_agent_node(state, progress),
    )
    builder.add_node(
        "skip_llm",
        lambda state: skip_llm_node(state, progress),
    )
    builder.add_node(
        "result_validator",
        lambda state: result_validator_node(state, progress),
    )
    builder.add_node(
        "confidence_classifier",
        lambda state: confidence_classifier_node(state, progress),
    )
    builder.add_node(
        "persist_suggestions",
        lambda state: persist_suggestions_node(state, db_session_factory, progress),
    )

    builder.add_edge(START, "schema_load")
    builder.add_edge("schema_load", "normalizer")
    builder.add_edge("normalizer", "candidate_gen")
    builder.add_conditional_edges(
        "candidate_gen",
        _conditional_branch,
        {"llm_agent": "llm_agent", "skip_llm": "skip_llm"},
    )
    builder.add_edge("llm_agent", "result_validator")
    builder.add_edge("skip_llm", "result_validator")
    builder.add_edge("result_validator", "confidence_classifier")
    builder.add_edge("confidence_classifier", "persist_suggestions")
    builder.add_edge("persist_suggestions", END)

    return builder.compile()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def run_analysis_workflow(
    *,
    project_id: int,
    snapshot_data: dict,
    llm_settings: LLMSettings | None,
    run_llm: bool,
    existing_keys: set[tuple[str, str, str, str]],
    db_session_factory: Callable[[], Any],
    progress: ProgressCb | None = None,
) -> dict:
    """Execute the full LangGraph workflow end-to-end.

    Returns a summary dict with keys { error, candidate_count, suggestion_count,
    used_llm, node_log }.
    """
    app = build_workflow(db_session_factory, progress)
    initial_state: WorkflowState = {
        "project_id": project_id,
        "snapshot_data": snapshot_data,
        "llm_settings": llm_settings,
        "run_llm": run_llm and llm_settings is not None,
        "existing_keys": existing_keys,
        "node_log": [],
    }
    final = app.invoke(initial_state)
    summary = {
        "error": final.get("error"),
        "candidate_count": final.get("candidate_count", 0),
        "suggestion_count": final.get("suggestion_count", 0),
        "filtered_existing_count": final.get("filtered_existing_count", 0),
        "used_llm": bool(final.get("used_llm")),
        "node_log": final.get("node_log") or [],
    }
    return summary
