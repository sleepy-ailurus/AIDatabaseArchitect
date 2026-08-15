"""Sensitive data identifier router - scan, review, report (feature 10)."""
from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    DatabaseConnection,
    Project,
    SchemaSnapshot,
    SensitiveField,
)
from app.schemas import SensitiveFieldOut, SensitiveScanRequest, SensitiveUpdate
from app.services import crypto
from app.services.schema_parser import schema_from_dict
from app.services.sensitive_detector import (
    build_report,
    detect_sensitive_fields,
    sample_validate,
)

router = APIRouter(prefix="/api", tags=["sensitive"])


@router.post("/projects/{project_id}/sensitive-scan", response_model=dict)
def scan_sensitive(
    project_id: int,
    payload: SensitiveScanRequest = Body(default=SensitiveScanRequest()),
    db: Session = Depends(get_db),
):
    """Detect sensitive/PII fields; optionally validate via read-only sampling."""
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
    findings = detect_sensitive_fields(schema)

    # Optional read-only sampling validation against the live database.
    engine = None
    if payload.include_sampling:
        conn = (
            db.query(DatabaseConnection)
            .filter(DatabaseConnection.project_id == project_id)
            .order_by(DatabaseConnection.id.desc())
            .first()
        )
        if conn:
            from sqlalchemy import create_engine

            password = crypto.decrypt(conn.password_encrypted)
            ssl_config = conn.ssl_config or {}
            from app.services.schema_parser import build_db_url

            url, connect_args, ca_file = build_db_url(
                str(conn.db_type),
                conn.host,
                conn.port,
                conn.database_name,
                conn.username,
                password,
                bool(ssl_config.get("enabled")),
                conn.timeout,
                ssl_config.get("ca"),
            )
            engine = create_engine(url, connect_args=connect_args, pool_pre_ping=True)

    for f in findings:
        if engine is not None:
            result = sample_validate(
                engine,
                f["table_name"],
                f["column_name"],
                payload.sample_size,
            )
            f["sample_hits"] = result["sample_hits"]
            f["sample_total"] = result["sample_total"]
            f["confidence"] = round(
                max(0.0, min(1.0, f["confidence"] + result["confidence_delta"])), 3
            )
        f.pop("gdpr_special", None)
        f.pop("pipi_sensitive", None)

    if engine is not None:
        engine.dispose()

    # Persist (replace previous scan results).
    db.query(SensitiveField).filter(SensitiveField.project_id == project_id).delete()
    for f in findings:
        db.add(
            SensitiveField(
                project_id=project_id,
                table_name=f["table_name"],
                column_name=f["column_name"],
                category=f["category"],
                category_label=f["category_label"],
                risk_level=f["risk_level"],
                confidence=f["confidence"],
                matched_reason=f.get("matched_reason"),
                sample_hits=f.get("sample_hits"),
                sample_total=f.get("sample_total"),
                status="detected",
            )
        )
    db.commit()

    return {
        "success": True,
        "field_count": len(findings),
        "sampled": engine is not None or bool(payload.include_sampling),
    }


@router.get("/projects/{project_id}/sensitive-fields", response_model=list[SensitiveFieldOut])
def list_sensitive_fields(
    project_id: int,
    risk_level: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(SensitiveField).filter(SensitiveField.project_id == project_id)
    if risk_level:
        query = query.filter(SensitiveField.risk_level == risk_level)
    if status:
        query = query.filter(SensitiveField.status == status)
    return query.order_by(SensitiveField.risk_level, SensitiveField.table_name).all()


@router.patch("/sensitive-fields/{field_id}", response_model=SensitiveFieldOut)
def update_field(field_id: int, payload: SensitiveUpdate, db: Session = Depends(get_db)):
    row = db.get(SensitiveField, field_id)
    if not row:
        raise HTTPException(status_code=404, detail="记录不存在")
    if payload.status not in ("detected", "confirmed", "false_positive", "mitigated"):
        raise HTTPException(status_code=400, detail="无效的状态")
    row.status = payload.status
    db.commit()
    db.refresh(row)
    return row


@router.get("/projects/{project_id}/sensitive-report")
def export_report(project_id: int, db: Session = Depends(get_db)):
    """Export the compliance report as Markdown."""
    rows = (
        db.query(SensitiveField)
        .filter(SensitiveField.project_id == project_id)
        .order_by(SensitiveField.risk_level, SensitiveField.table_name)
        .all()
    )
    findings = [
        {
            "table_name": r.table_name,
            "column_name": r.column_name,
            "category_label": r.category_label,
            "risk_level": r.risk_level,
            "confidence": r.confidence,
            "matched_reason": r.matched_reason,
            "sample_hits": r.sample_hits,
            "sample_total": r.sample_total,
        }
        for r in rows
    ]
    content = build_report(findings)
    return Response(
        content=content.encode("utf-8"),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="sensitive-report.md"'},
    )
